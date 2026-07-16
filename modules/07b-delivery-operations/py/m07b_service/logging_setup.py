"""Structured (JSON) logging with correlation IDs and secret redaction.

Three independent safeguards keep credentials out of the logs:

1. Secrets live in the config as ``SecretStr`` and are simply never logged —
   the app logs :meth:`Settings.redacted_summary`, which never extracts them.
2. Every structured field passes through :func:`_redact`, so even if a
   credential-shaped key (``authorization``, ``api_key``, ``token`` …) is handed
   to the logger by mistake, its value is masked before it reaches the sink.
3. As a final net, every emitted line is scrubbed of any *registered* secret
   substring (:func:`register_secret`). This catches a secret that leaked into a
   free-text ``msg`` or an exception traceback — places :func:`_redact` (which
   only touches structured field VALUES) cannot reach.

.. important::
   Never interpolate a secret into the log ``msg`` (e.g. via an f-string). The
   key-based :func:`_redact` does not see ``msg``; only the registered-secret
   scrub does, and only for values you actually registered. Prefer structured
   fields with credential-shaped names.

The request/correlation id is stored in a :class:`~contextvars.ContextVar`, so
any log line emitted while handling a request automatically carries it — no need
to thread the id through every call.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, TextIO

from pydantic import SecretStr

from .config import PROVIDER_CREDENTIAL_ENV_VARS

LOGGER_NAME = "m07b"

# The correlation id for the request currently being handled (if any).
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Field names whose values must never appear verbatim in a log line.
_REDACT_KEYS = frozenset(
    {
        "authorization",
        "api_key",
        "apikey",
        "provider_api_key",
        "password",
        "secret",
        "token",
        "x-api-key",
    }
)
_REDACTED = "[REDACTED]"

# Known secret substrings to scrub from ANY emitted text (msg, exception,
# serialized fields). Populated at startup via register_secret(); the values are
# held only in this private set and are never themselves logged.
_secret_registry: set[str] = set()


def register_secret(value: SecretStr | str | None) -> None:
    """Register a secret value so it is scrubbed from every future log line."""
    if value is None:
        return
    raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
    if raw:
        _secret_registry.add(raw)


def register_provider_credentials(env: Mapping[str, str] | None = None) -> None:
    """Register every provider credential present in the environment.

    ``llm_core`` reads these keys (``OPENAI_API_KEY`` etc.) directly from the
    environment, bypassing our config, so they must be registered separately —
    otherwise a provider SDK error containing one would print verbatim.
    """
    source: Mapping[str, str] = os.environ if env is None else env
    for name in PROVIDER_CREDENTIAL_ENV_VARS:
        register_secret(source.get(name))


def clear_secrets() -> None:
    """Drop all registered secrets (used to isolate tests)."""
    _secret_registry.clear()


def _scrub_secrets(text: str) -> str:
    """Replace every registered secret substring with the redaction marker."""
    for secret in _secret_registry:
        if secret in text:
            text = text.replace(secret, _REDACTED)
    return text


def _redact(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Mask credential-shaped keys, recursing through nested dicts AND lists."""
    return {key: _redact_value(key, value) for key, value in fields.items()}


def _redact_value(key: str, value: Any) -> Any:
    if key.lower() in _REDACT_KEYS:
        return _REDACTED
    if isinstance(value, Mapping):
        return {k: _redact_value(k, v) for k, v in value.items()}
    # Recurse into sequences (but not strings/bytes) so a credential nested in a
    # list — e.g. {"items": [{"api_key": "..."}]} — is still masked.
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_value(key, item) for item in value]
    return value


class JsonLogFormatter(logging.Formatter):
    """Render a log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id is not None:
            payload["request_id"] = request_id

        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, Mapping):
            payload.update(_redact(extra))

        if record.exc_info:
            # formatException output is free text (module paths, arg reprs) that
            # _redact never sees, so it must go through the secret scrub too.
            payload["exc"] = self.formatException(record.exc_info)

        # Final net: scrub any registered secret from the whole serialized line
        # (covers msg, the exception traceback, and any field value).
        return _scrub_secrets(json.dumps(payload, default=str))


def configure_logging(level: str = "INFO", *, stream: TextIO | None = None) -> logging.Logger:
    """Configure and return the service logger.

    Idempotent: re-running replaces the handler set (so repeated app builds in a
    test session don't stack duplicate handlers) and clears the secret registry
    for the fresh configuration. ``stream`` lets a test capture output;
    production leaves it as ``stdout``.
    """
    clear_secrets()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    # Replace handlers rather than append — avoids duplicate lines / leaks across
    # repeated create_app() calls. We only ever wrap stdout or an in-memory
    # buffer, so there is no OS handle to close here.
    logger.handlers.clear()

    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, level: int, msg: str, /, **fields: Any) -> None:
    """Emit a structured event. Extra keyword fields are JSON-serialised."""
    logger.log(level, msg, extra={"extra_fields": fields})
