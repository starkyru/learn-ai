"""Real-entrypoint startup test: fail fast when a provider credential is missing.

Unlike the bootstrap unit test (which injects a failing factory), this runs the
actual ``python -m m07b_service`` entrypoint in a subprocess with a real provider
selected and its key UNSET. A missing key must fail BEFORE any network call, so
the process exits non-zero quickly, binds no port, and prints no raw traceback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PY_DIR = Path(__file__).resolve().parent


def test_entrypoint_fails_fast_without_provider_credential(tmp_path):
    env = {
        **os.environ,
        "SERVICE_ENV": "development",
        "LLM_PROVIDER": "openai",  # requires OPENAI_API_KEY
        "PORT": "8199",
        "DB_PATH": str(tmp_path / "db.sqlite"),
    }
    env.pop("OPENAI_API_KEY", None)  # the missing credential

    proc = subprocess.run(
        [sys.executable, "-m", "m07b_service"],
        cwd=str(_PY_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Fails fast (nonzero) — it never reached uvicorn.run / bound a port.
    assert proc.returncode != 0
    # The failure was handled by our redacting logger, not dumped as a raw crash.
    assert "Traceback" not in proc.stderr
    assert "startup_failed" in proc.stdout


def test_asgi_import_does_not_leak_original_startup_error(tmp_path):
    # `uvicorn m07b_service.asgi:app` imports this module. A startup failure must
    # raise a GENERIC error — the original llm_core message (distinctively
    # "Copy .env.example ...") must NOT reach stderr, only the scrubbed
    # startup_failed event (to stdout).
    env = {
        **os.environ,
        "SERVICE_ENV": "development",
        "LLM_PROVIDER": "openai",
        "DB_PATH": str(tmp_path / "db.sqlite"),
    }
    env.pop("OPENAI_API_KEY", None)

    proc = subprocess.run(
        [sys.executable, "-c", "import m07b_service.asgi"],
        cwd=str(_PY_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode != 0
    assert "startup_failed" in proc.stdout  # scrubbed event emitted
    # The original, unguarded error text must NOT surface on stderr.
    assert "Copy .env.example" not in proc.stderr
