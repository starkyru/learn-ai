"""Tests for the durable-job HTTP surface: POST /jobs and GET /jobs/{id} (Task 3).

Enqueue is operator-only and tenant-scoped; status inspection is open to any
authenticated caller but only within their tenant. Processing is driven here by
calling the real queue's ``drain`` directly (the app does NOT run the background
worker in tests — that is production-only — so the request path stays
deterministic). The only faked boundary is the LLM provider.
"""

from __future__ import annotations

from conftest import OPERATOR_A, VIEWER_A, VIEWER_B, bearer
from fastapi.testclient import TestClient
from m07b_service.app import create_app
from m07b_service.db import connect
from m07b_service.jobs import drain, index_document


def _fresh_document(client: TestClient, title: str) -> str:
    """Create a document as operator A via the real endpoint; return its id."""
    response = client.post("/documents", json={"title": title}, headers=bearer(OPERATOR_A))
    assert response.status_code == 201
    return response.json()["id"]


def test_create_app_does_not_start_a_background_worker(seeded_settings, make_provider):
    # The worker is production-only (build_app_from_env), so a test app leaves no
    # thread running and enqueued jobs wait for an explicit drain.
    app = create_app(seeded_settings, provider=make_provider())
    assert not hasattr(app.state, "job_worker")


def test_enqueue_requires_operator(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        unauth = client.post("/jobs", json={"document_id": "doc-a1"})
        viewer = client.post("/jobs", json={"document_id": "doc-a1"}, headers=bearer(VIEWER_A))
    assert unauth.status_code == 401  # no token
    assert viewer.status_code == 403  # authenticated but not an operator


def test_enqueue_unknown_or_cross_tenant_document_is_404(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        missing = client.post(
            "/jobs", json={"document_id": "no-such-doc"}, headers=bearer(OPERATOR_A)
        )
        # doc-b1 belongs to tenant B; operator A must not enqueue against it.
        cross = client.post("/jobs", json={"document_id": "doc-b1"}, headers=bearer(OPERATOR_A))
    assert missing.status_code == 404
    assert cross.status_code == 404


def test_enqueue_accepts_and_job_is_inspectable(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        doc_id = _fresh_document(client, "launch notes")
        enq = client.post("/jobs", json={"document_id": doc_id}, headers=bearer(OPERATOR_A))
        assert enq.status_code == 202  # accepted for background processing
        job_id = enq.json()["job_id"]
        assert enq.json()["status"] == "pending"
        # Any authenticated caller in the tenant can inspect it.
        status = client.get(f"/jobs/{job_id}", headers=bearer(VIEWER_A))
    assert status.status_code == 200
    body = status.json()
    assert body["id"] == job_id
    assert body["document_id"] == doc_id
    assert body["status"] == "pending"


def test_enqueue_is_idempotent_with_key_and_yields_one_effect(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        doc_id = _fresh_document(client, "idem doc")
        headers = {**bearer(OPERATOR_A), "Idempotency-Key": "req-77"}
        first = client.post("/jobs", json={"document_id": doc_id}, headers=headers)
        second = client.post("/jobs", json={"document_id": doc_id}, headers=headers)
        assert first.status_code == 202  # first creates the job
        assert second.status_code == 200  # replay: no new job
        assert second.json()["job_id"] == first.json()["job_id"]

        # Process the queue, then confirm exactly one effect (one chunk) despite
        # the repeated request.
        drain(seeded_settings.db_path, index_document(seeded_settings.db_path))
        done = client.get(f"/jobs/{first.json()['job_id']}", headers=bearer(OPERATOR_A))
    assert done.json()["status"] == "succeeded"

    conn = connect(seeded_settings.db_path)
    try:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchone()
    finally:
        conn.close()
    assert count == 1


def test_job_status_is_tenant_scoped(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        doc_id = _fresh_document(client, "tenant A only")
        enq = client.post("/jobs", json={"document_id": doc_id}, headers=bearer(OPERATOR_A))
        job_id = enq.json()["job_id"]
        # Tenant B viewer must not see tenant A's job — a 404, not a status leak.
        cross = client.get(f"/jobs/{job_id}", headers=bearer(VIEWER_B))
    assert cross.status_code == 404
