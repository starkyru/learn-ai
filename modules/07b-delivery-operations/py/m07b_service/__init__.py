"""Module 07b — reference AI service (Python / FastAPI).

A small, production-shaped service that fronts the provider-agnostic
``llm_core`` client. It demonstrates the delivery invariants Module 07b
teaches: config validation at startup, structured logs with correlation IDs,
liveness/readiness probes, and a non-root container — all without hardcoding a
model provider.

The pieces are deliberately separated so later tasks can extend them:

* :mod:`m07b_service.config`  — typed, fail-fast configuration from the env.
* :mod:`m07b_service.logging_setup` — JSON logging + request-id redaction.
* :mod:`m07b_service.db` — datastore readiness probe (T2.2 adds the schema).
* :mod:`m07b_service.provider` — the ``llm_core`` seam.
* :mod:`m07b_service.app` — the FastAPI app factory (auth seam for T2.3).
* :mod:`m07b_service.asgi` — the production entrypoint uvicorn imports.
"""

from __future__ import annotations

from .app import bootstrap, create_app
from .config import ConfigError, Settings, load_settings

__all__ = ["create_app", "bootstrap", "load_settings", "Settings", "ConfigError"]
