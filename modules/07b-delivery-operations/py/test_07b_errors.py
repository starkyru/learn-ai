"""Tests that error responses never leak raw input, provider details, or secrets."""

from __future__ import annotations

import io
from collections.abc import Iterable, Iterator

from conftest import VIEWER_A, bearer, seed_identity
from fastapi import HTTPException
from fastapi.testclient import TestClient
from llm_core import ChatMessage, ChatOptions, ChatResult
from m07b_service.app import REQUEST_ID_HEADER, create_app


class _RaisingProvider:
    """A fake provider whose chat() raises — models a provider SDK failure."""

    name = "fake"
    chat_model = "fake-chat"
    embed_model = "fake-embed"

    def __init__(self, message: str) -> None:
        self.message = message

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        raise RuntimeError(self.message)

    def chat_stream(self, messages, options=None) -> Iterator[str]:  # pragma: no cover
        yield ""

    def embed(self, input: list[str]):  # noqa: A002 - protocol name
        raise NotImplementedError


def test_validation_error_response_omits_raw_input(seeded_settings, make_provider):
    # Authenticated (auth runs before body validation), so validation is reached.
    app = create_app(seeded_settings, provider=make_provider())
    with TestClient(app) as client:
        # An unknown field carrying a secret-looking value.
        resp = client.post(
            "/ask",
            json={"question": "", "leaked": "SENTINEL-INPUT-abc"},
            headers=bearer(VIEWER_A),
        )

    assert resp.status_code == 422
    # Generic body: no echoed input value, only a request id.
    assert resp.json() == {
        "detail": "invalid request",
        "request_id": resp.headers[REQUEST_ID_HEADER],
    }
    assert "SENTINEL-INPUT-abc" not in resp.text


def test_provider_exception_returns_bounded_502_without_leaking(make_settings, monkeypatch):
    # A real provider credential in the environment (llm_core reads this directly).
    monkeypatch.setenv("OPENAI_API_KEY", "FAKE-OPENAI-KEY-xyz")
    buffer = io.StringIO()
    # No retries here so a raising provider is called once (keeps the test fast);
    # the reliability envelope maps a provider failure to an UPSTREAM error (502).
    settings = make_settings(provider_max_retries=0)
    seed_identity(settings.db_path)
    provider = _RaisingProvider("upstream 401 using key FAKE-OPENAI-KEY-xyz")
    app = create_app(settings, provider=provider, log_stream=buffer)

    with TestClient(app) as client:
        resp = client.post(
            "/ask",
            json={"question": "hi"},
            headers={**bearer(VIEWER_A), REQUEST_ID_HEADER: "rid-err"},
        )

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Bad Gateway", "request_id": "rid-err"}
    assert resp.headers[REQUEST_ID_HEADER] == "rid-err"
    # Neither the provider message nor the credential reaches the response OR logs.
    logs = buffer.getvalue()
    for sink in (resp.text, logs):
        assert "upstream 401" not in sink
        assert "FAKE-OPENAI-KEY-xyz" not in sink
    # A bounded observability event names the failure MODE, not the raw cause.
    assert "provider_call_failed" in logs
    assert "ProviderUnavailable" in logs


class _HttpRaisingProvider:
    """A fake provider that raises HTTPException with a sensitive detail."""

    name = "fake"
    chat_model = "fake-chat"
    embed_model = "fake-embed"

    def chat(self, messages, options=None) -> ChatResult:
        raise HTTPException(status_code=502, detail="SENTINEL-SECRET-detail")

    def chat_stream(self, messages, options=None) -> Iterator[str]:  # pragma: no cover
        yield ""

    def embed(self, input: list[str]):  # noqa: A002 - protocol name
        raise NotImplementedError


def test_http_exception_detail_is_not_leaked(make_settings):
    # A provider/adapter raising HTTPException(detail=...) is a provider failure:
    # the reliability envelope maps it to a bounded 502 and its sensitive detail
    # is dropped (FastAPI's default would return it verbatim).
    buffer = io.StringIO()
    settings = make_settings(provider_max_retries=0)
    seed_identity(settings.db_path)
    app = create_app(settings, provider=_HttpRaisingProvider(), log_stream=buffer)

    with TestClient(app) as client:
        resp = client.post(
            "/ask",
            json={"question": "hi"},
            headers={**bearer(VIEWER_A), REQUEST_ID_HEADER: "rid-h"},
        )

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Bad Gateway", "request_id": "rid-h"}
    assert "SENTINEL-SECRET-detail" not in resp.text
    # The raw detail is absent from the logs too (we log only the failure mode).
    logs = buffer.getvalue()
    assert "SENTINEL-SECRET-detail" not in logs
    assert "provider_call_failed" in logs
