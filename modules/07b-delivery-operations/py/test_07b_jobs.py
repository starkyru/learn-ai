"""Unit tests for the durable ingestion job queue (Task 3), offline + base-deps.

These exercise the REAL queue code (``m07b_service.jobs``) against a real migrated
SQLite database — the only injected thing is the job HANDLER (the side-effect
boundary), so idempotency, atomic claim, bounded retry, and the dead-letter path
are all driven deterministically. No FastAPI import here, so this file runs under
base deps (unlike the ``test_07b_*`` app tests guarded in conftest).
"""

from __future__ import annotations

import threading
import time

import pytest
from m07b_service.db import connect
from m07b_service.jobs import (
    DEAD,
    PENDING,
    SUCCEEDED,
    IngestJob,
    JobWorker,
    dead_letters,
    drain,
    enqueue,
    get_job,
    index_document,
    list_jobs,
    process_next,
    requeue,
)
from m07b_service.migrations import apply_pending
from m07b_service.retrieval import create_document, retrieve

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


@pytest.fixture
def svc(make_settings):
    """A migrated db with two tenants (no jobs yet) — real Settings, real schema."""
    settings = make_settings()
    apply_pending(settings.db_path)
    conn = connect(settings.db_path)
    try:
        conn.executemany(
            "INSERT INTO tenants (id, name) VALUES (?, ?)",
            [(TENANT_A, "Tenant A"), (TENANT_B, "Tenant B")],
        )
    finally:
        conn.close()
    return settings


class RecordingHandler:
    """Records the jobs it ran; optionally fails the first ``fail_times`` attempts."""

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.seen: list[str] = []

    def __call__(self, job: IngestJob) -> None:
        self.seen.append(job.id)
        if len(self.seen) <= self.fail_times:
            raise RuntimeError("transient failure")


def _always_fail(job: IngestJob) -> None:
    raise RuntimeError("permanent failure")


# ── enqueue + idempotency ───────────────────────────────────────────────────


def test_enqueue_creates_a_pending_job(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A)
    assert result.created is True
    job = get_job(svc.db_path, TENANT_A, result.job_id)
    assert job is not None
    assert job.status == PENDING
    assert job.retries == 0


def test_enqueue_is_idempotent_per_key(svc):
    first = enqueue(svc.db_path, tenant_id=TENANT_A, idempotency_key="k1")
    second = enqueue(svc.db_path, tenant_id=TENANT_A, idempotency_key="k1")
    assert first.created is True
    assert second.created is False
    assert second.job_id == first.job_id  # same job, not a duplicate
    assert len(list_jobs(svc.db_path, TENANT_A)) == 1


def test_same_key_different_tenant_is_a_distinct_job(svc):
    a = enqueue(svc.db_path, tenant_id=TENANT_A, idempotency_key="shared")
    b = enqueue(svc.db_path, tenant_id=TENANT_B, idempotency_key="shared")
    # The key is scoped per tenant, so the same string is two independent jobs.
    assert b.created is True
    assert b.job_id != a.job_id


def test_enqueue_without_key_creates_distinct_jobs(svc):
    a = enqueue(svc.db_path, tenant_id=TENANT_A)
    b = enqueue(svc.db_path, tenant_id=TENANT_A)
    assert a.job_id != b.job_id
    assert len(list_jobs(svc.db_path, TENANT_A)) == 2


def test_get_job_is_tenant_scoped(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A)
    # Another tenant cannot read the job even with the exact id.
    assert get_job(svc.db_path, TENANT_B, result.job_id) is None


# ── claim + process ─────────────────────────────────────────────────────────


def test_process_next_on_empty_queue_returns_none(svc):
    assert process_next(svc.db_path, RecordingHandler()) is None


def test_process_next_success_marks_succeeded(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A)
    handler = RecordingHandler()
    settled = process_next(svc.db_path, handler)
    assert settled is not None
    assert settled.status == SUCCEEDED
    assert handler.seen == [result.job_id]  # ran exactly once, on this job


def test_drain_runs_each_job_exactly_once(svc):
    a = enqueue(svc.db_path, tenant_id=TENANT_A)
    b = enqueue(svc.db_path, tenant_id=TENANT_A)
    handler = RecordingHandler()
    attempts = drain(svc.db_path, handler)
    assert attempts == 2
    assert sorted(handler.seen) == sorted([a.job_id, b.job_id])
    assert get_job(svc.db_path, TENANT_A, a.job_id).status == SUCCEEDED
    assert get_job(svc.db_path, TENANT_A, b.job_id).status == SUCCEEDED


# ── retry + dead-letter ─────────────────────────────────────────────────────


def test_transient_failure_is_retried_then_succeeds(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A, max_retries=3)
    handler = RecordingHandler(fail_times=2)  # fail twice, then succeed
    attempts = drain(svc.db_path, handler)
    assert attempts == 3  # 2 failed + 1 successful attempt
    job = get_job(svc.db_path, TENANT_A, result.job_id)
    assert job.status == SUCCEEDED
    assert job.retries == 2  # two consumed retries recorded


def test_exhausted_retries_land_in_dead_letter(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A, max_retries=2)
    attempts = drain(svc.db_path, _always_fail)
    assert attempts == 3  # 1 initial + 2 retries, then dead
    job = get_job(svc.db_path, TENANT_A, result.job_id)
    assert job.status == DEAD
    assert job.retries == 3
    assert job.last_error is not None and "permanent failure" in job.last_error
    dead = dead_letters(svc.db_path, TENANT_A)
    assert [d.id for d in dead] == [result.job_id]


def test_zero_retries_dies_on_first_failure(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A, max_retries=0)
    attempts = drain(svc.db_path, _always_fail)
    assert attempts == 1
    job = get_job(svc.db_path, TENANT_A, result.job_id)
    assert job.status == DEAD
    assert job.retries == 1


def test_requeue_revives_a_dead_job_and_it_can_succeed(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A, max_retries=0)
    drain(svc.db_path, _always_fail)  # -> dead
    assert requeue(svc.db_path, TENANT_A, result.job_id) is True
    revived = get_job(svc.db_path, TENANT_A, result.job_id)
    assert revived.status == PENDING
    assert revived.retries == 0
    assert revived.last_error is None
    # A second requeue is a no-op (it is pending now, not dead).
    assert requeue(svc.db_path, TENANT_A, result.job_id) is False
    # And it now processes cleanly.
    drain(svc.db_path, RecordingHandler())
    assert get_job(svc.db_path, TENANT_A, result.job_id).status == SUCCEEDED


def test_requeue_of_a_non_dead_job_returns_false(svc):
    result = enqueue(svc.db_path, tenant_id=TENANT_A)  # pending
    assert requeue(svc.db_path, TENANT_A, result.job_id) is False


# ── the reference indexing handler ──────────────────────────────────────────


def test_index_document_creates_a_retrievable_tenant_scoped_chunk(svc):
    doc_id = create_document(svc.db_path, tenant_id=TENANT_A, title="Launch plan")
    result = enqueue(svc.db_path, tenant_id=TENANT_A, document_id=doc_id)
    drain(svc.db_path, index_document(svc.db_path))
    assert get_job(svc.db_path, TENANT_A, result.job_id).status == SUCCEEDED
    # The indexed chunk is retrievable in-tenant …
    hits = retrieve(svc.db_path, TENANT_A, "Launch")
    assert [h.content for h in hits] == ["Launch plan"]
    # … and never leaks to another tenant.
    assert retrieve(svc.db_path, TENANT_B, "Launch") == []


def test_index_document_is_idempotent_no_double_write(svc):
    doc_id = create_document(svc.db_path, tenant_id=TENANT_A, title="once")
    # Two separate jobs for the SAME document (no idempotency key) both run the
    # handler, but the INSERT OR IGNORE on UNIQUE(document_id, ordinal) means one
    # chunk row, not two — at-least-once delivery becomes effectively-once.
    enqueue(svc.db_path, tenant_id=TENANT_A, document_id=doc_id)
    enqueue(svc.db_path, tenant_id=TENANT_A, document_id=doc_id)
    drain(svc.db_path, index_document(svc.db_path))
    conn = connect(svc.db_path)
    try:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchone()
    finally:
        conn.close()
    assert count == 1


# ── the background worker ───────────────────────────────────────────────────


def test_job_worker_processes_in_background_then_stops_cleanly(svc):
    doc_id = create_document(svc.db_path, tenant_id=TENANT_A, title="bg work")
    ran = threading.Event()
    real = index_document(svc.db_path)

    def handler(job: IngestJob) -> None:
        real(job)  # the actual side effect
        ran.set()

    worker = JobWorker(svc.db_path, handler, poll_interval_s=0.01)
    result = enqueue(svc.db_path, tenant_id=TENANT_A, document_id=doc_id)
    worker.start()
    try:
        assert ran.wait(timeout=2.0), "worker did not process the job"
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if get_job(svc.db_path, TENANT_A, result.job_id).status == SUCCEEDED:
                break
            time.sleep(0.005)
    finally:
        worker.stop()
    assert worker.is_running is False
    assert get_job(svc.db_path, TENANT_A, result.job_id).status == SUCCEEDED
