"""ASGI-server entrypoint: ``uvicorn m07b_service.asgi:app``.

Importing this module builds the app via the shared safe launcher
(:func:`m07b_service.app.build_app_from_env`), which installs the JSON logger +
credential scrubber FIRST. On a startup failure it logs a SCRUBBED
``startup_failed`` event and raises a generic :class:`~m07b_service.app.StartupError`
— so the exception the ASGI server prints at import time carries no
credential-bearing message or original traceback.

``python -m m07b_service`` (see :mod:`m07b_service.__main__`) is equivalent and
additionally controls the process exit code; the Dockerfile uses it.
"""

from __future__ import annotations

from .app import build_app_from_env

app = build_app_from_env()
