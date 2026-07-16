"""Tests for identity, RBAC, tenant-safe retrieval, and audit (T2.3)."""

from __future__ import annotations

from conftest import (
    CHUNK_A_MARKER,
    CHUNK_B_MARKER,
    OPERATOR_A,
    RETRIEVAL_QUERY,
    TENANT_A,
    TENANT_B,
    VIEWER_A,
    bearer,
)
from fastapi.testclient import TestClient
from m07b_service.app import REQUEST_ID_HEADER, create_app
from m07b_service.db import connect
from m07b_service.retrieval import retrieve


def _audit_rows(db_path):
    conn = connect(db_path)
    try:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT actor, tenant_id, action, decision, request_id FROM audit_events "
                "ORDER BY created_at, id"
            )
        ]
    finally:
        conn.close()


def _document_count(db_path, tenant_id):
    conn = connect(db_path)
    try:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
        return count
    finally:
        conn.close()


# ── Authentication (401) ────────────────────────────────────────────────────


def test_unauthenticated_ask_returns_401_and_never_reaches_the_provider(
    seeded_settings, make_provider
):
    provider = make_provider()
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "launch"})  # no Authorization
    assert response.status_code == 401
    # Enforcement is BEFORE retrieval/generation: the provider was never called.
    assert provider.calls == []


def test_invalid_token_returns_401(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "launch"}, headers=bearer("ghost-user"))
    assert response.status_code == 401


def test_auth_runs_before_body_validation(seeded_settings, make_provider):
    # The body ({"question": ""}) would earn a 422 on its own; proving 401 here
    # shows the authenticate dependency gates BEFORE body validation.
    provider = make_provider()
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": ""})  # invalid body, no token
    assert response.status_code == 401  # auth first — NOT the 422 the body would earn
    assert provider.calls == []


def test_authenticated_ask_succeeds(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider("HELLO"))
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "launch"}, headers=bearer(VIEWER_A))
    assert response.status_code == 200
    assert response.json()["answer"] == "HELLO"


# ── 401 vs 403 are distinct ─────────────────────────────────────────────────


def test_401_and_403_are_distinct_on_documents(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        unauth = client.post("/documents", json={"title": "x"})  # no token -> 401
        forbidden = client.post(
            "/documents", json={"title": "x"}, headers=bearer(VIEWER_A)
        )  # viewer -> 403
    assert unauth.status_code == 401
    assert forbidden.status_code == 403
    assert unauth.status_code != forbidden.status_code


# ── RBAC (viewer denied, operator allowed) ──────────────────────────────────


def test_viewer_cannot_create_document_and_none_is_written(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    before = _document_count(seeded_settings.db_path, TENANT_A)
    with TestClient(app) as client:
        response = client.post("/documents", json={"title": "viewer-doc"}, headers=bearer(VIEWER_A))
    assert response.status_code == 403
    # The role check gates the WRITE, not just the response: no document created.
    assert _document_count(seeded_settings.db_path, TENANT_A) == before


def test_operator_can_create_document_in_own_tenant(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    before = _document_count(seeded_settings.db_path, TENANT_A)
    with TestClient(app) as client:
        response = client.post(
            "/documents", json={"title": "operator-doc"}, headers=bearer(OPERATOR_A)
        )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert _document_count(seeded_settings.db_path, TENANT_A) == before + 1
    # The new document belongs to the OPERATOR's tenant.
    conn = connect(seeded_settings.db_path)
    try:
        (tenant_id,) = conn.execute(
            "SELECT tenant_id FROM documents WHERE id = ?", (body["id"],)
        ).fetchone()
    finally:
        conn.close()
    assert tenant_id == TENANT_A


# ── Tenant-safe retrieval (load-bearing) ────────────────────────────────────


def test_retrieve_is_tenant_scoped_both_directions(seeded_settings):
    # Direct unit test of the retrieval filter. Both chunks match "launch".
    tenant_a = retrieve(seeded_settings.db_path, TENANT_A, RETRIEVAL_QUERY)
    tenant_b = retrieve(seeded_settings.db_path, TENANT_B, RETRIEVAL_QUERY)

    a_content = " ".join(c.content for c in tenant_a)
    b_content = " ".join(c.content for c in tenant_b)
    # Tenant A sees its own marker and NONE of tenant B's.
    assert CHUNK_A_MARKER in a_content
    assert CHUNK_B_MARKER not in a_content
    # ...and vice versa (discriminating in both directions).
    assert CHUNK_B_MARKER in b_content
    assert CHUNK_A_MARKER not in b_content


def test_ask_only_uses_the_callers_tenant_context(seeded_settings, make_provider):
    # A tenant-A caller's /ask must give the provider tenant A's chunk, never B's,
    # even though tenant B has a chunk matching the same query.
    provider = make_provider()
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": RETRIEVAL_QUERY}, headers=bearer(VIEWER_A))
    assert response.status_code == 200
    assert len(provider.calls) == 1
    system = next(m.content for m in provider.calls[0] if m.role == "system")
    assert CHUNK_A_MARKER in system  # tenant A's chunk was retrieved
    assert CHUNK_B_MARKER not in system  # tenant B's matching chunk was NOT


# ── Audit ───────────────────────────────────────────────────────────────────


def test_audit_records_allow_for_ask_without_sensitive_content(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        client.post(
            "/ask",
            json={"question": f"tell me about {RETRIEVAL_QUERY} SENSITIVE-QUESTION"},
            headers={**bearer(VIEWER_A), REQUEST_ID_HEADER: "rid-ask"},
        )
    rows = _audit_rows(seeded_settings.db_path)
    allow = [r for r in rows if r["decision"] == "allow" and r["action"] == "POST /ask"]
    assert len(allow) == 1
    assert allow[0]["actor"] == VIEWER_A
    assert allow[0]["tenant_id"] == TENANT_A
    assert allow[0]["request_id"] == "rid-ask"
    # The audit records who/what/decision — never the question content.
    for value in allow[0].values():
        assert "SENSITIVE-QUESTION" not in str(value)


def test_audit_records_deny_for_forbidden_write(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        client.post(
            "/documents",
            json={"title": "nope"},
            headers={**bearer(VIEWER_A), REQUEST_ID_HEADER: "rid-deny"},
        )
    rows = _audit_rows(seeded_settings.db_path)
    deny = [r for r in rows if r["decision"] == "deny" and r["action"] == "POST /documents"]
    assert len(deny) == 1
    assert deny[0]["actor"] == VIEWER_A
    assert deny[0]["tenant_id"] == TENANT_A
    assert deny[0]["request_id"] == "rid-deny"


def test_audit_records_deny_for_unauthenticated(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        client.post("/ask", json={"question": "hi"}, headers={REQUEST_ID_HEADER: "rid-401"})
    rows = _audit_rows(seeded_settings.db_path)
    deny = [r for r in rows if r["decision"] == "deny" and r["request_id"] == "rid-401"]
    assert len(deny) == 1
    assert deny[0]["actor"] is None  # unknown caller
    assert deny[0]["tenant_id"] is None
    assert deny[0]["action"] == "POST /ask"
