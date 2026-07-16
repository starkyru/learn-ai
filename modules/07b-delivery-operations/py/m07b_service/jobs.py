"""Durable background ingestion jobs (Task 3, the queue half).

An LLM service does its slow, fallible work — chunking + embedding a document —
OUT of the request path, in a durable queue, so a request returns immediately and
the work survives a process restart. This module is that queue, backed by the
``ingest_jobs`` and ``idempotency_keys`` tables the initial migration already
defines. It composes four production concerns:

  * IDEMPOTENCY  — enqueuing the same logical work twice (same key) creates ONE
    job, so a retried client request produces one effect.
  * ATOMIC CLAIM — a worker transitions exactly one ``pending`` job to
    ``running`` under ``BEGIN IMMEDIATE``, so two workers never run the same job.
  * BOUNDED RETRY — a failed attempt is re-queued until ``max_retries`` is spent.
  * DEAD-LETTER  — an exhausted job lands in ``dead`` for inspection and manual
    requeue, instead of retrying forever or vanishing.

Delivery is AT-LEAST-ONCE (a crash after the side effect but before the status
write replays the job), so the reference handler (:func:`index_document`) is
IDEMPOTENT — its write is an ``INSERT OR IGNORE`` on the ``UNIQUE(document_id,
ordinal)`` key — making the observable effect effectively-once.

The handler is the injected side-effect boundary (like the provider elsewhere):
tests pass a recording/failing handler to drive every path deterministically,
and production passes :func:`index_document`. Timestamps come from SQLite's
``datetime('now')``, so no clock is threaded through here.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from .db import connect

# Scope namespacing the idempotency keys this module owns, so an ingest key can
# never collide with a key some other subsystem stores in the shared table.
IDEMPOTENCY_SCOPE = "ingest_job"

# Total attempts allowed for a job = 1 initial + ``max_retries`` retries. Matches
# the ``ingest_jobs.max_retries`` column default so an enqueue that omits it lands
# on the same budget as a raw INSERT.
DEFAULT_MAX_RETRIES = 5

# Cap the stored failure detail so a pathological exception message cannot bloat
# the row. It is operational text (e.g. "document X not found"); the handler must
# never surface a credential in an exception (the indexing handler touches no
# provider secret).
_MAX_ERROR_CHARS = 500

# A hard backstop on drain() so a mis-implemented handler that never settles a job
# cannot spin forever. Real runs terminate far below this: each failed attempt
# spends one retry, so a job reaches ``dead`` in at most max_retries + 1 attempts.
_DRAIN_ITERATION_CAP = 10_000

PENDING = "pending"
RUNNING = "running"
SUCCEEDED = "succeeded"
DEAD = "dead"


class JobError(RuntimeError):
    """Raise from a handler to mark the attempt failed (any exception also works)."""


@dataclass(frozen=True)
class IngestJob:
    """A row of ``ingest_jobs`` — an immutable snapshot at read time."""

    id: str
    tenant_id: str
    document_id: str | None
    status: str
    retries: int
    max_retries: int
    last_error: str | None
    created_at: str
    updated_at: str


# A handler runs the actual work for one job; it returns None on success and
# RAISES on failure. It must be idempotent (delivery is at-least-once).
JobHandler = Callable[[IngestJob], None]

_COLUMNS = (
    "id, tenant_id, document_id, status, retries, max_retries, last_error, created_at, updated_at"
)


def _row_to_job(row) -> IngestJob:
    return IngestJob(
        id=row["id"],
        tenant_id=row["tenant_id"],
        document_id=row["document_id"],
        status=row["status"],
        retries=row["retries"],
        max_retries=row["max_retries"],
        last_error=row["last_error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@dataclass(frozen=True)
class EnqueueResult:
    """Outcome of :func:`enqueue`. ``created`` is False on an idempotent replay."""

    job_id: str
    created: bool


def enqueue(
    db_path: str,
    *,
    tenant_id: str,
    document_id: str | None = None,
    idempotency_key: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> EnqueueResult:
    """Enqueue an ingestion job; idempotent per ``(tenant_id, idempotency_key)``.

    With an ``idempotency_key``, a second enqueue for the same tenant+key returns
    the FIRST job's id and ``created=False`` — no duplicate job. The whole
    check-then-insert runs under ``BEGIN IMMEDIATE``, so two concurrent enqueues
    with the same key serialise (the second sees the first's key row); the
    ``idempotency_keys`` primary key is the backstop. ``document_id``, when given,
    must belong to ``tenant_id`` — the composite foreign key enforces it.
    """
    job_id = str(uuid4())
    conn = connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        if idempotency_key is not None:
            existing = conn.execute(
                "SELECT result_ref FROM idempotency_keys "
                "WHERE tenant_id = ? AND scope = ? AND key = ?",
                (tenant_id, IDEMPOTENCY_SCOPE, idempotency_key),
            ).fetchone()
            if existing is not None:
                conn.execute("ROLLBACK")
                return EnqueueResult(job_id=existing["result_ref"], created=False)
            conn.execute(
                "INSERT INTO idempotency_keys (key, scope, tenant_id, result_ref) "
                "VALUES (?, ?, ?, ?)",
                (idempotency_key, IDEMPOTENCY_SCOPE, tenant_id, job_id),
            )
        conn.execute(
            "INSERT INTO ingest_jobs (id, tenant_id, document_id, status, max_retries) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (job_id, tenant_id, document_id, max_retries),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return EnqueueResult(job_id=job_id, created=True)


def get_job(db_path: str, tenant_id: str, job_id: str) -> IngestJob | None:
    """Return the job if it exists IN ``tenant_id`` — else None (tenant-scoped)."""
    conn = connect(db_path)
    try:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM ingest_jobs WHERE tenant_id = ? AND id = ?",
            (tenant_id, job_id),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_job(row) if row is not None else None


def list_jobs(
    db_path: str, tenant_id: str, *, status: str | None = None, limit: int = 100
) -> list[IngestJob]:
    """List jobs in ``tenant_id`` (optionally filtered by status), newest first."""
    conn = connect(db_path)
    try:
        if status is None:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM ingest_jobs WHERE tenant_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM ingest_jobs WHERE tenant_id = ? AND status = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (tenant_id, status, limit),
            ).fetchall()
    finally:
        conn.close()
    return [_row_to_job(row) for row in rows]


def dead_letters(db_path: str, tenant_id: str, *, limit: int = 100) -> list[IngestJob]:
    """The dead-letter view: jobs in ``tenant_id`` that exhausted their retries."""
    return list_jobs(db_path, tenant_id, status=DEAD, limit=limit)


def requeue(db_path: str, tenant_id: str, job_id: str) -> bool:
    """Move a DEAD job back to ``pending`` (retries reset). Returns True if it moved.

    Only a dead job is requeued — the ``status = 'dead'`` predicate makes this a
    no-op (returns False) for a pending/running/succeeded job, so requeue cannot
    resurrect an in-flight or already-done job.
    """
    conn = connect(db_path)
    try:
        cur = conn.execute(
            "UPDATE ingest_jobs SET status = 'pending', retries = 0, last_error = NULL, "
            "updated_at = datetime('now') "
            "WHERE tenant_id = ? AND id = ? AND status = 'dead'",
            (tenant_id, job_id),
        )
        return cur.rowcount > 0
    finally:
        conn.close()


def _claim_next(db_path: str) -> IngestJob | None:
    """Atomically transition the oldest ``pending`` job to ``running`` and return it.

    ``BEGIN IMMEDIATE`` takes the write lock up front so two workers cannot select
    the same row; the ``AND status = 'pending'`` guard on the UPDATE is a second
    line of defence. Returns None when nothing is claimable.
    """
    conn = connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM ingest_jobs WHERE status = 'pending' "
            "ORDER BY created_at, id LIMIT 1"
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            return None
        conn.execute(
            "UPDATE ingest_jobs SET status = 'running', updated_at = datetime('now') "
            "WHERE id = ? AND status = 'pending'",
            (row["id"],),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return _row_to_job(row)


def _settle_success(db_path: str, job_id: str) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE ingest_jobs SET status = 'succeeded', last_error = NULL, "
            "updated_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
    finally:
        conn.close()


def _settle_failure(db_path: str, job: IngestJob, error: str) -> None:
    """Record a failed attempt: re-queue if retries remain, else dead-letter."""
    retries = job.retries + 1
    status = PENDING if retries <= job.max_retries else DEAD
    conn = connect(db_path)
    try:
        conn.execute(
            "UPDATE ingest_jobs SET status = ?, retries = ?, last_error = ?, "
            "updated_at = datetime('now') WHERE id = ?",
            (status, retries, error[:_MAX_ERROR_CHARS], job.id),
        )
    finally:
        conn.close()


def process_next(db_path: str, handler: JobHandler) -> IngestJob | None:
    """Claim and run ONE job. Returns the job's post-run snapshot, or None if idle.

    On a handler exception the attempt is counted and the job is re-queued
    (``pending``) or dead-lettered (``dead``); a handler failure never propagates
    out of here, so a worker loop keeps draining. The returned snapshot reflects
    the settled state (succeeded / pending / dead).
    """
    job = _claim_next(db_path)
    if job is None:
        return None
    try:
        handler(job)
    except Exception as exc:  # noqa: BLE001 - a failed attempt is data, not a crash
        _settle_failure(db_path, job, str(exc))
    else:
        _settle_success(db_path, job.id)
    # Re-read so the caller observes the terminal/re-queued row, not the claim.
    return get_job(db_path, job.tenant_id, job.id)


def drain(db_path: str, handler: JobHandler) -> int:
    """Run attempts until the queue has no claimable job. Returns attempts run.

    Each iteration is one claim+run; a re-queued job is retried on a later
    iteration of the SAME drain, so a transiently-failing job settles here rather
    than lingering. Bounded by ``_DRAIN_ITERATION_CAP`` as a backstop only.
    """
    attempts = 0
    while attempts < _DRAIN_ITERATION_CAP:
        if process_next(db_path, handler) is None:
            break
        attempts += 1
    return attempts


def index_document(db_path: str) -> JobHandler:
    """The reference indexing handler: chunk a document's title into ``chunks``.

    A deliberately naive stand-in for real chunk+embed (see Module 05): it writes
    ONE chunk whose content is the document title. The deterministic chunk id and
    ``INSERT OR IGNORE`` on the ``UNIQUE(document_id, ordinal)`` key make it
    idempotent, so replaying the job after a crash never double-writes — the
    at-least-once queue becomes effectively-once. Raises when the document is
    missing so the job retries / dead-letters rather than silently no-op'ing.
    """

    def handler(job: IngestJob) -> None:
        if job.document_id is None:
            return
        conn = connect(db_path)
        try:
            row = conn.execute(
                "SELECT title FROM documents WHERE tenant_id = ? AND id = ?",
                (job.tenant_id, job.document_id),
            ).fetchone()
            if row is None:
                raise JobError(f"document {job.document_id} not found for tenant")
            conn.execute(
                "INSERT OR IGNORE INTO chunks "
                "(id, tenant_id, document_id, ordinal, content) VALUES (?, ?, ?, ?, ?)",
                (f"{job.document_id}:0", job.tenant_id, job.document_id, 0, row["title"]),
            )
        finally:
            conn.close()

    return handler


class JobWorker:
    """A background thread that drains the queue, for the running service.

    Not started by ``create_app`` (so request tests stay deterministic and
    thread-free); the production launcher starts it and stops it on shutdown.
    Tests drive :func:`drain` directly. The stop signal doubles as the idle sleep,
    so ``stop()`` interrupts an idle wait immediately — a clean, prompt shutdown
    with no busy-poll and no leaked thread.
    """

    def __init__(self, db_path: str, handler: JobHandler, *, poll_interval_s: float = 1.0) -> None:
        self._db_path = db_path
        self._handler = handler
        self._poll_interval_s = poll_interval_s
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="m07b-ingest-worker", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            processed = drain(self._db_path, self._handler)
            if processed == 0:
                # Idle: sleep on the stop event so shutdown wakes us at once.
                self._stop.wait(self._poll_interval_s)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
