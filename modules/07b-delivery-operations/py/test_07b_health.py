"""Tests for /healthz (liveness) and /readyz (readiness reflects the MIGRATED DB)."""

from __future__ import annotations

import os
import stat
import time

from fastapi.testclient import TestClient
from m07b_service.app import create_app
from m07b_service.db import connect
from m07b_service.migrations import apply_pending


def test_healthz_is_always_200_when_process_is_up(make_settings):
    app = create_app(make_settings())
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_503_when_db_is_unmigrated(make_settings):
    # A reachable-but-unmigrated DB (no schema) is NOT ready.
    app = create_app(make_settings())
    with TestClient(app) as client:
        response = client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"db": "error"}}


def test_readyz_is_200_after_migration(make_settings, tmp_path):
    db_path = str(tmp_path / "ready.sqlite")
    apply_pending(db_path)  # create the schema
    app = create_app(make_settings(db_path=db_path))
    with TestClient(app) as client:
        response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"db": "ok"}}


def test_readyz_returns_503_while_datastore_unavailable(make_settings):
    # A path under a directory that does not exist cannot be opened by SQLite.
    app = create_app(make_settings(db_path="/no_such_dir_07b/service.sqlite"))
    with TestClient(app) as client:
        ready = client.get("/readyz")
        live = client.get("/healthz")
    assert ready.status_code == 503
    assert ready.json() == {"status": "not_ready", "checks": {"db": "error"}}
    # Liveness must stay independent of the failing dependency.
    assert live.status_code == 200


def test_readyz_503_when_db_is_read_only(make_settings, tmp_path):
    # A migrated but READ-ONLY DB must report 503 (the write probe catches it —
    # a name/column check alone would wrongly pass).
    data_dir = tmp_path / "ro"
    data_dir.mkdir()
    db_path = str(data_dir / "ro.sqlite")
    apply_pending(db_path)  # fully migrated first

    os.chmod(db_path, stat.S_IRUSR | stat.S_IRGRP)  # read-only file
    os.chmod(data_dir, stat.S_IRUSR | stat.S_IXUSR)  # read-only dir (no journal)
    try:
        app = create_app(make_settings(db_path=db_path))
        with TestClient(app) as client:
            response = client.get("/readyz")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "checks": {"db": "error"}}
    finally:
        os.chmod(data_dir, 0o755)  # restore so tmp cleanup can remove it
        os.chmod(db_path, 0o644)


def test_readyz_toggles_with_migration(make_settings, tmp_path):
    # Prove readiness genuinely follows the schema: same code, migrate flips it.
    db_path = str(tmp_path / "toggle.sqlite")
    app = create_app(make_settings(db_path=db_path))
    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 503  # unmigrated
        apply_pending(db_path)
        assert client.get("/readyz").status_code == 200  # migrated


def test_readyz_reflects_the_default_relative_data_dir(make_settings, tmp_path, monkeypatch):
    # Reproduce the container's default: the RELATIVE db path resolved against the
    # working directory. Without a "data/" dir the datastore cannot open -> 503;
    # once the dir exists AND migrations run -> 200.
    monkeypatch.chdir(tmp_path)
    default_db = "data/07b-service.sqlite"

    missing = create_app(make_settings(db_path=default_db))
    with TestClient(missing) as client:
        assert client.get("/readyz").status_code == 503

    (tmp_path / "data").mkdir()
    apply_pending(default_db)
    ready = create_app(make_settings(db_path=default_db))
    with TestClient(ready) as client:
        assert client.get("/readyz").status_code == 200


def test_readyz_does_not_block_when_write_lock_held(make_settings, tmp_path):
    # A held write lock must not stall the readiness probe for ~5 s: the probe is
    # non-blocking (busy_timeout=0), so it returns 503 fast.
    db_path = str(tmp_path / "block.sqlite")
    apply_pending(db_path)
    holder = connect(db_path)
    holder.execute("BEGIN IMMEDIATE")  # hold the write lock
    try:
        app = create_app(make_settings(db_path=db_path))
        with TestClient(app) as client:
            start = time.monotonic()
            response = client.get("/readyz")
            elapsed = time.monotonic() - start
        assert response.status_code == 503  # write probe cannot get the lock
        assert elapsed < 2.0  # returned fast, did NOT block on the 5 s busy timeout
    finally:
        holder.execute("ROLLBACK")
        holder.close()
