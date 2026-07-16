"""Tests for POST /ask with an injected fake provider.

``/ask`` is a protected endpoint (T2.3): every request needs a valid bearer
token, and validation (413/422) is only reached once authenticated. The tests
below authenticate as a seeded viewer; the pre-auth body-size cap (413) is the
exception — it rejects before routing, so it needs neither token nor seed.
"""

from __future__ import annotations

import time
from collections.abc import Iterable

from conftest import VIEWER_A, bearer, seed_identity
from fastapi.testclient import TestClient
from llm_core import ChatMessage, ChatOptions, ChatResult
from m07b_service.app import REQUEST_ID_HEADER, create_app


class SlowProvider:
    """A provider whose chat blocks past the request deadline."""

    name = "slow"
    chat_model = "slow-chat"

    def __init__(self, delay_s: float) -> None:
        self.delay_s = delay_s

    def chat(
        self, messages: Iterable[ChatMessage], options: ChatOptions | None = None
    ) -> ChatResult:
        time.sleep(self.delay_s)
        return ChatResult(text="late", model=self.chat_model)


class FailingProvider:
    """A provider that always raises, to drive the retry + circuit-breaker paths."""

    name = "failing"
    chat_model = "failing-chat"

    def __init__(self) -> None:
        self.calls = 0

    def chat(
        self, messages: Iterable[ChatMessage], options: ChatOptions | None = None
    ) -> ChatResult:
        self.calls += 1
        raise RuntimeError("provider down")


def test_ask_returns_provider_answer_and_echoes_request_id(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider("HELLO-FROM-FAKE"))
    with TestClient(app) as client:
        response = client.post(
            "/ask",
            json={"question": "what is 07b about?"},
            headers={**bearer(VIEWER_A), REQUEST_ID_HEADER: "req-abc-123"},
        )

    assert response.status_code == 200
    assert response.json() == {"answer": "HELLO-FROM-FAKE", "request_id": "req-abc-123"}
    # The inbound correlation id is echoed on the response header too.
    assert response.headers[REQUEST_ID_HEADER] == "req-abc-123"


def test_ask_generates_a_request_id_when_none_supplied(seeded_settings, make_provider):
    app = create_app(seeded_settings, provider=make_provider("X"))
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "hi"}, headers=bearer(VIEWER_A))
    assert response.status_code == 200
    generated = response.json()["request_id"]
    assert generated  # non-empty
    assert response.headers[REQUEST_ID_HEADER] == generated


def test_ask_actually_calls_the_provider_with_the_question(seeded_settings, make_provider):
    provider = make_provider("Y")
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        client.post("/ask", json={"question": "unique-question-marker"}, headers=bearer(VIEWER_A))
    # Prove the real request path reached the provider with our input.
    assert len(provider.calls) == 1
    user_contents = [m.content for m in provider.calls[0] if m.role == "user"]
    assert user_contents == ["unique-question-marker"]


def test_ask_rejects_empty_question_with_422(seeded_settings, make_provider):
    provider = make_provider("Z")
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": ""}, headers=bearer(VIEWER_A))
    assert response.status_code == 422
    # A rejected request must not have reached the provider.
    assert provider.calls == []


def test_ask_rejects_oversized_question_with_422(seeded_settings, make_provider):
    provider = make_provider("Z")
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        # 4001 chars > max_length (4000); the body is small enough to pass the cap.
        response = client.post("/ask", json={"question": "a" * 4001}, headers=bearer(VIEWER_A))
    assert response.status_code == 422
    assert provider.calls == []


def test_ask_rejects_oversized_body_with_413(make_settings, make_provider):
    # The body-size cap rejects BEFORE routing/auth, so no token or seed is needed.
    provider = make_provider("Z")
    app = create_app(make_settings(), provider=provider)
    with TestClient(app) as client:
        # ~70 KB body exceeds the 64 KB cap; rejected before parsing/validation.
        response = client.post("/ask", json={"question": "a" * 70_000})
    assert response.status_code == 413
    assert provider.calls == []


def test_ask_rejects_unknown_body_fields_with_422(seeded_settings, make_provider):
    provider = make_provider("Z")
    app = create_app(seeded_settings, provider=provider)
    with TestClient(app) as client:
        response = client.post(
            "/ask", json={"question": "hi", "role": "admin"}, headers=bearer(VIEWER_A)
        )
    assert response.status_code == 422  # AskRequest uses extra="forbid"
    assert provider.calls == []


def test_ask_rejects_chunked_oversized_body_with_413(make_settings, make_provider):
    # Pre-auth body-size cap again — chunked transfer with no Content-Length.
    provider = make_provider("Z")
    app = create_app(make_settings(), provider=provider)

    def chunks():
        # A streaming body => chunked transfer, so NO Content-Length header. The
        # byte cap must still trigger (it counts bytes off the ASGI stream).
        yield b'{"question":"' + b"a" * 70_000 + b'"}'

    with TestClient(app) as client:
        response = client.post(
            "/ask", content=chunks(), headers={"content-type": "application/json"}
        )
    assert response.status_code == 413
    assert provider.calls == []


# ── Reliability envelope at the HTTP boundary (Task 3) ──────────────────────


def test_ask_slow_provider_returns_bounded_504(make_settings):
    # A provider slower than the per-request deadline yields a bounded, generic
    # 504 — never a raw provider detail and never an unbounded hang.
    settings = make_settings(request_timeout_s=0.1, provider_max_retries=0)
    seed_identity(settings.db_path)
    app = create_app(settings, provider=SlowProvider(delay_s=1.0))
    with TestClient(app) as client:
        response = client.post("/ask", json={"question": "hi"}, headers=bearer(VIEWER_A))
    assert response.status_code == 504
    assert response.json()["detail"] == "Gateway Timeout"  # canonical reason, no raw detail


def test_ask_rate_limited_identity_returns_429(make_settings, make_provider):
    settings = make_settings(rate_limit_per_minute=1)
    seed_identity(settings.db_path)
    app = create_app(settings, provider=make_provider("ok"))
    with TestClient(app) as client:
        first = client.post("/ask", json={"question": "one"}, headers=bearer(VIEWER_A))
        second = client.post("/ask", json={"question": "two"}, headers=bearer(VIEWER_A))
    assert first.status_code == 200
    assert second.status_code == 429  # per-identity budget exhausted in the window


def test_ask_provider_outage_opens_circuit(make_settings):
    # First failing call surfaces a 502 and trips the breaker (threshold 1); the
    # next call fast-fails 503 WITHOUT reaching the provider.
    settings = make_settings(circuit_failure_threshold=1, provider_max_retries=0)
    seed_identity(settings.db_path)
    provider = FailingProvider()
    app = create_app(settings, provider=provider)
    with TestClient(app) as client:
        first = client.post("/ask", json={"question": "one"}, headers=bearer(VIEWER_A))
        second = client.post("/ask", json={"question": "two"}, headers=bearer(VIEWER_A))
    assert first.status_code == 502  # provider failed -> upstream error
    assert second.status_code == 503  # circuit now open -> fast fail
    assert provider.calls == 1  # the open circuit did not call the provider again
