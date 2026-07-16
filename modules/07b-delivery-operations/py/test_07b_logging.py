"""Tests that logs are structured, carry the correlation id, and never leak secrets."""

from __future__ import annotations

import io
import json

from conftest import VIEWER_A, bearer, seed_identity
from fastapi.testclient import TestClient
from m07b_service.app import REQUEST_ID_HEADER, create_app

SECRET = "SENTINEL-SECRET-do-not-log-9f3a"


def _lines(buffer: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buffer.getvalue().splitlines() if line.strip()]


def test_configured_secret_never_appears_in_logs(make_settings, make_provider):
    buffer = io.StringIO()
    settings = make_settings(provider_api_key=SECRET)
    seed_identity(settings.db_path)  # /ask is protected: authenticate as a viewer
    app = create_app(settings, provider=make_provider(), log_stream=buffer)
    with TestClient(app) as client:
        client.post("/ask", json={"question": "hi"}, headers=bearer(VIEWER_A))

    output = buffer.getvalue()
    # The raw secret must never be emitted, even though the startup log was
    # deliberately handed the secret value under a redacted key.
    assert SECRET not in output
    assert "[REDACTED]" in output


def test_startup_config_event_is_emitted_as_json(make_settings, make_provider):
    buffer = io.StringIO()
    create_app(make_settings(), provider=make_provider(), log_stream=buffer)
    events = _lines(buffer)
    configured = [e for e in events if e.get("msg") == "service_configured"]
    assert len(configured) == 1
    assert configured[0]["provider"] == "ollama"
    assert configured[0]["level"] == "INFO"


def test_request_completed_log_carries_the_request_id(make_settings, make_provider):
    buffer = io.StringIO()
    app = create_app(make_settings(), provider=make_provider(), log_stream=buffer)
    with TestClient(app) as client:
        client.get("/healthz", headers={REQUEST_ID_HEADER: "trace-777"})

    events = _lines(buffer)
    completed = [e for e in events if e.get("msg") == "request_completed"]
    assert len(completed) == 1
    assert completed[0]["request_id"] == "trace-777"
    assert completed[0]["path"] == "/healthz"
    assert completed[0]["status"] == 200
