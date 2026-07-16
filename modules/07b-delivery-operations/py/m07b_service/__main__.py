"""CLI entrypoint: ``python -m m07b_service``.

The redaction-safe way to start the service (used by the Dockerfile). It builds
the app via the shared safe launcher (:func:`m07b_service.app.build_app_from_env`,
which installs the logger + scrubber first and raises a generic error on
failure), then exits non-zero on any startup error — *without* dumping a raw
traceback (which could contain a credential) to stderr, and before binding a
port.
"""

from __future__ import annotations

import sys

from .app import build_app_from_env


def main() -> int:
    try:
        app = build_app_from_env()  # logs a scrubbed startup_failed on failure
    except Exception:
        return 1

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=app.state.settings.port, log_config=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
