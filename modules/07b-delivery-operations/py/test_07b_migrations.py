"""Tests for the numbered SQL migration runner (Python side)."""

from __future__ import annotations

import math
import sqlite3
import threading
import time

import pytest
from m07b_service import migrations as migrations_module
from m07b_service.db import REQUIRED_TABLES, connect
from m07b_service.migrations import (
    MigrationLockError,
    _default_lock_timeout_s,
    _normalize_lock_timeout_s,
    _split_statements,
    applied_versions,
    apply_pending,
    check_ready,
    discover,
    rollback,
)

# The exact tables the initial migration must create (excludes the runner's own
# schema_migrations bookkeeping table).
_EXPECTED_TABLES = {
    "tenants",
    "users",
    "documents",
    "chunks",
    "ingest_jobs",
    "idempotency_keys",
    "audit_events",
}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    # pragma_table_info() is the table-valued form of the PRAGMA, so the table
    # name can be BOUND (no identifier interpolation / SQL injection).
    rows = conn.execute("SELECT name FROM pragma_table_info(?)", (table,)).fetchall()
    return {row[0] for row in rows}


def test_migrate_from_empty_creates_the_full_schema(tmp_path):
    db_path = str(tmp_path / "empty.sqlite")
    applied = apply_pending(db_path)
    assert applied == ["0001_init"]

    conn = connect(db_path)
    try:
        tables = _tables(conn)
        assert _EXPECTED_TABLES.issubset(tables)
        assert "schema_migrations" in tables
        # REQUIRED_TABLES (used by readiness) matches the created schema.
        assert REQUIRED_TABLES == frozenset(_EXPECTED_TABLES)
        # Spot-check the tenant-scoping + shape of a couple of tables.
        assert _columns(conn, "users") == {
            "id",
            "tenant_id",
            "email",
            "role",
            "created_at",
        }
        assert "tenant_id" in _columns(conn, "chunks")
        assert _columns(conn, "idempotency_keys") == {
            "key",
            "scope",
            "tenant_id",
            "result_ref",
            "created_at",
        }
        assert applied_versions(conn) == ["0001_init"]
    finally:
        conn.close()


def test_apply_is_idempotent(tmp_path):
    db_path = str(tmp_path / "idempotent.sqlite")
    first = apply_pending(db_path)
    assert first == ["0001_init"]

    # Second run applies nothing and does not error or duplicate rows.
    second = apply_pending(db_path)
    assert second == []

    conn = connect(db_path)
    try:
        assert applied_versions(conn) == ["0001_init"]
        (count,) = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
        assert count == 1
    finally:
        conn.close()


def test_rollback_then_reapply(tmp_path):
    db_path = str(tmp_path / "rollback.sqlite")
    apply_pending(db_path)

    rolled_back = rollback(db_path)
    assert rolled_back == ["0001_init"]

    conn = connect(db_path)
    try:
        # The schema is gone (only the empty bookkeeping table remains).
        assert _tables(conn) == {"schema_migrations"}
        assert applied_versions(conn) == []
    finally:
        conn.close()

    # Re-applying after a rollback rebuilds the full schema.
    reapplied = apply_pending(db_path)
    assert reapplied == ["0001_init"]
    conn = connect(db_path)
    try:
        assert _EXPECTED_TABLES.issubset(_tables(conn))
    finally:
        conn.close()


def test_split_statements_respects_strings_and_trigger_bodies():
    # A `;` inside a string literal AND inside a CREATE TRIGGER body must NOT
    # split the statement — otherwise both would raise raw SQLite parse errors.
    sql = (
        "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT DEFAULT 'a; b');\n"
        "CREATE TRIGGER bump AFTER INSERT ON notes BEGIN\n"
        "  UPDATE notes SET body = 'x; y' WHERE id = NEW.id;\n"
        "END;\n"
    )
    statements = _split_statements(sql)
    assert len(statements) == 2  # table + trigger, not split on the inner ';'
    assert statements[0].startswith("CREATE TABLE")
    assert statements[1].startswith("CREATE TRIGGER")


def test_migration_with_trigger_and_string_semicolons_applies(tmp_path):
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    (mig_dir / "0001_trig.up.sql").write_text(
        "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT DEFAULT 'a; b', bumped INTEGER DEFAULT 0);\n"
        "CREATE TRIGGER bump AFTER INSERT ON notes BEGIN\n"
        "  UPDATE notes SET bumped = 1 WHERE id = NEW.id;\n"
        "END;\n"
    )
    db_path = str(tmp_path / "trig.sqlite")
    assert apply_pending(db_path, str(mig_dir)) == ["0001_trig"]

    conn = connect(db_path)
    try:
        conn.execute("INSERT INTO notes (id) VALUES (1)")
        row = conn.execute("SELECT body, bumped FROM notes WHERE id = 1").fetchone()
        assert row[0] == "a; b"  # string default with an inner ';' survived
        assert row[1] == 1  # the trigger (whose body has ';') fired
    finally:
        conn.close()


def test_failed_migration_leaves_no_partial_schema(tmp_path):
    mig_dir = tmp_path / "migrations"
    mig_dir.mkdir()
    # The 2nd statement fails (duplicate table) — the whole migration must roll
    # back: no partial table AND no schema_migrations row.
    (mig_dir / "0001_bad.up.sql").write_text(
        "CREATE TABLE keep_me (id TEXT);\nCREATE TABLE keep_me (id TEXT);\n"
    )
    db_path = str(tmp_path / "bad.sqlite")
    with pytest.raises(sqlite3.OperationalError):
        apply_pending(db_path, str(mig_dir))

    conn = connect(db_path)
    try:
        assert "keep_me" not in _tables(conn)  # first statement rolled back too
        assert applied_versions(conn) == []  # no version recorded
    finally:
        conn.close()


def test_foreign_keys_enforced_rejects_bad_tenant(tmp_path):
    db_path = str(tmp_path / "fk.sqlite")
    apply_pending(db_path)

    conn = connect(db_path)  # connect() sets PRAGMA foreign_keys = ON
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
                ("u1", "no-such-tenant", "a@b.c"),
            )
    finally:
        conn.close()


def test_discover_raises_on_missing_dir():
    # Fail-loud on a wrong MIGRATIONS_DIR (parity with the TS readdirSync throw).
    with pytest.raises(FileNotFoundError):
        discover("/no/such/migrations/dir")


def test_concurrent_apply_does_not_crash_the_loser(tmp_path):
    # Several runners race on a fresh DB. BEGIN IMMEDIATE + the busy timeout must
    # serialise them: exactly one applies the migration, the rest are clean
    # no-ops (no "table already exists" crash, no duplicate row).
    db_path = str(tmp_path / "race.sqlite")
    results: dict[str, list[str]] = {}
    errors: dict[str, str] = {}

    def worker(name: str) -> None:
        try:
            results[name] = apply_pending(db_path)
        except Exception as exc:  # noqa: BLE001 - capture any crash for the assert
            errors[name] = repr(exc)

    threads = [threading.Thread(target=worker, args=(f"r{i}",)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == {}, errors  # no runner crashed
    all_applied = [v for applied in results.values() for v in applied]
    assert all_applied.count("0001_init") == 1  # applied exactly once

    conn = connect(db_path)
    try:
        assert applied_versions(conn) == ["0001_init"]
        (count,) = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()
        assert count == 1  # no duplicate bookkeeping row
    finally:
        conn.close()


def test_composite_fk_blocks_cross_tenant_document_reference(tmp_path):
    # A child row must not attach a document owned by a DIFFERENT tenant.
    db_path = str(tmp_path / "tenant.sqlite")
    apply_pending(db_path)
    conn = connect(db_path)
    try:
        conn.execute("INSERT INTO tenants (id, name) VALUES ('A', 'Ten A'), ('B', 'Ten B')")
        conn.execute("INSERT INTO documents (id, tenant_id, title) VALUES ('doc1', 'A', 'A doc')")

        # Same-tenant references succeed.
        conn.execute(
            "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) "
            "VALUES ('c1', 'A', 'doc1', 0, 'x')"
        )
        conn.execute(
            "INSERT INTO ingest_jobs (id, tenant_id, document_id) VALUES ('j1', 'A', 'doc1')"
        )
        # A job with no document is allowed (nullable).
        conn.execute("INSERT INTO ingest_jobs (id, tenant_id) VALUES ('j0', 'B')")

        # Cross-tenant references (tenant B -> A's document) are rejected. Use a
        # distinct ordinal so the composite FK, not the UNIQUE index, is what
        # rejects it; assert the message is specifically a FOREIGN KEY failure.
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) "
                "VALUES ('c2', 'B', 'doc1', 1, 'x')"
            )
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                "INSERT INTO ingest_jobs (id, tenant_id, document_id) VALUES ('j2', 'B', 'doc1')"
            )
    finally:
        conn.close()


def test_migration_lock_deadline_raises_clear_error(tmp_path):
    # When another runner holds the write lock past the deadline, we get a clear
    # MigrationLockError — NOT a raw SQLITE_BUSY crash.
    db_path = str(tmp_path / "locked.sqlite")
    acquired = threading.Event()
    release = threading.Event()

    def holder() -> None:
        conn = connect(db_path)
        conn.execute("BEGIN IMMEDIATE")
        acquired.set()
        release.wait(timeout=5)
        conn.execute("ROLLBACK")
        conn.close()

    holder_thread = threading.Thread(target=holder)
    holder_thread.start()
    assert acquired.wait(timeout=2)
    try:
        with pytest.raises(MigrationLockError):
            apply_pending(db_path, lock_timeout_s=0.3)
    finally:
        release.set()
        holder_thread.join()


def test_migration_retries_and_succeeds_when_lock_released(tmp_path):
    # A runner blocked past the busy_timeout RETRIES and still succeeds once the
    # holder releases (before the deadline).
    db_path = str(tmp_path / "retry.sqlite")
    acquired = threading.Event()

    def holder() -> None:
        conn = connect(db_path)
        conn.execute("BEGIN IMMEDIATE")
        acquired.set()
        time.sleep(0.3)  # hold longer than the 50 ms per-attempt busy_timeout
        conn.execute("ROLLBACK")
        conn.close()

    holder_thread = threading.Thread(target=holder)
    holder_thread.start()
    assert acquired.wait(timeout=2)

    applied = apply_pending(db_path, lock_timeout_s=5.0)  # retries, then succeeds
    holder_thread.join()
    assert applied == ["0001_init"]


# Values that must all normalise to the bounded 30 s default (never nan/inf/
# overflow). "1e306" (out-of-range) and "1000" (> the 300 s cap) are the round-5
# additions that a plain finite/positive check would have let through.
_BAD_TIMEOUTS = ["nan", "inf", "-inf", "Infinity", "0", "-5", "notanumber", "", "1e306", "1000"]


@pytest.mark.parametrize("bad_value", _BAD_TIMEOUTS)
def test_env_lock_timeout_rejects_bad_values(bad_value, monkeypatch):
    monkeypatch.setenv("MIGRATION_LOCK_TIMEOUT_S", bad_value)
    value = _default_lock_timeout_s()
    assert math.isfinite(value)
    assert value == 30.0


@pytest.mark.parametrize(
    "bad_value", [float("nan"), float("inf"), 0, -5, 1e306, 1000, "1e306", None]
)
def test_normalize_lock_timeout_bounds_every_bad_value(bad_value):
    # The single normalizer used for BOTH the env var and explicit overrides.
    value = _normalize_lock_timeout_s(bad_value)
    assert math.isfinite(value) and 0 < value <= 300.0
    assert value == 30.0


def test_normalize_lock_timeout_keeps_a_valid_value():
    assert _normalize_lock_timeout_s(12.5) == 12.5
    assert _normalize_lock_timeout_s("12.5") == 12.5
    assert _normalize_lock_timeout_s(300.0) == 300.0  # exactly the cap is allowed


def test_lock_timeout_default_when_unset(monkeypatch):
    monkeypatch.delenv("MIGRATION_LOCK_TIMEOUT_S", raising=False)
    assert _default_lock_timeout_s() == 30.0


@pytest.mark.parametrize(
    "kind, bad",
    [
        ("override", float("nan")),
        ("override", float("inf")),
        ("override", 0),
        ("override", -5),
        ("override", 1e306),
        ("env", "nan"),
        ("env", "inf"),
        ("env", "1e306"),
    ],
)
def test_bad_timeout_never_hangs_under_held_lock(kind, bad, tmp_path, monkeypatch):
    # End-to-end through the PUBLIC api with a HELD write lock: a bad override OR
    # env value must produce a BOUNDED wait ending in MigrationLockError, never an
    # infinite hang. We shrink the default/cap so the bounded wait is fast.
    monkeypatch.setattr(migrations_module, "_DEFAULT_LOCK_TIMEOUT_S", 0.2)
    monkeypatch.setattr(migrations_module, "_MAX_LOCK_TIMEOUT_S", 0.2)
    if kind == "env":
        monkeypatch.setenv("MIGRATION_LOCK_TIMEOUT_S", bad)

    db_path = str(tmp_path / "held.sqlite")
    acquired = threading.Event()
    release = threading.Event()

    def holder() -> None:
        conn = connect(db_path)
        conn.execute("BEGIN IMMEDIATE")
        acquired.set()
        release.wait(timeout=5)
        conn.execute("ROLLBACK")
        conn.close()

    holder_thread = threading.Thread(target=holder)
    holder_thread.start()
    assert acquired.wait(timeout=2)
    try:
        started = time.monotonic()
        with pytest.raises(MigrationLockError):
            if kind == "override":
                apply_pending(db_path, lock_timeout_s=bad)
            else:
                apply_pending(db_path)  # uses the (bad) env value
        assert time.monotonic() - started < 2.0  # bounded, did not hang
    finally:
        release.set()
        holder_thread.join()


def test_check_ready_true_for_migrated_writable_db(tmp_path):
    db_path = str(tmp_path / "ready.sqlite")
    apply_pending(db_path)
    assert check_ready(db_path) is True


def test_check_ready_false_when_a_migration_version_is_missing(tmp_path):
    db_path = str(tmp_path / "missing_version.sqlite")
    apply_pending(db_path)
    conn = connect(db_path)
    try:
        conn.execute("DELETE FROM schema_migrations")  # schema present, version gone
    finally:
        conn.close()
    assert check_ready(db_path) is False


def test_check_ready_false_when_a_table_lacks_a_key_column(tmp_path):
    # Same table NAMES but 'users' lacks tenant_id — the fingerprint must reject it.
    db_path = str(tmp_path / "frag.sqlite")
    conn = connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
        conn.execute("INSERT INTO schema_migrations VALUES ('0001_init', 'x')")
        conn.execute("CREATE TABLE tenants (id TEXT, name TEXT)")
        conn.execute("CREATE TABLE users (id TEXT, email TEXT, role TEXT)")  # no tenant_id
        conn.execute("CREATE TABLE documents (id TEXT, tenant_id TEXT, title TEXT)")
        conn.execute(
            "CREATE TABLE chunks (id TEXT, tenant_id TEXT, document_id TEXT, ordinal INTEGER, content TEXT)"
        )
        conn.execute(
            "CREATE TABLE ingest_jobs (id TEXT, tenant_id TEXT, status TEXT, retries INTEGER)"
        )
        conn.execute("CREATE TABLE idempotency_keys (key TEXT, scope TEXT, tenant_id TEXT)")
        conn.execute("CREATE TABLE audit_events (id TEXT, action TEXT, request_id TEXT)")
    finally:
        conn.close()
    assert check_ready(db_path) is False


def test_check_ready_false_when_composite_fk_removed(tmp_path):
    # A same-COLUMN schema but WITHOUT the (tenant_id, document_id) composite FK
    # must not pass — otherwise cross-tenant references would be possible.
    db_path = str(tmp_path / "nofk.sqlite")
    conn = connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
        conn.execute("INSERT INTO schema_migrations VALUES ('0001_init', 'x')")
        conn.execute("CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT)")
        conn.execute("CREATE TABLE users (id TEXT, tenant_id TEXT, email TEXT, role TEXT)")
        conn.execute(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, tenant_id TEXT, title TEXT, UNIQUE (tenant_id, id))"
        )
        # Right columns, but NO composite foreign key on chunks/ingest_jobs.
        conn.execute(
            "CREATE TABLE chunks (id TEXT, tenant_id TEXT, document_id TEXT, ordinal INTEGER, content TEXT)"
        )
        conn.execute(
            "CREATE TABLE ingest_jobs (id TEXT, tenant_id TEXT, document_id TEXT, status TEXT, retries INTEGER)"
        )
        conn.execute("CREATE TABLE idempotency_keys (key TEXT, scope TEXT, tenant_id TEXT)")
        conn.execute(
            "CREATE TABLE audit_events (id TEXT, tenant_id TEXT, action TEXT, request_id TEXT)"
        )
    finally:
        conn.close()
    assert check_ready(db_path) is False


def test_check_ready_false_with_an_unknown_migration_version(tmp_path):
    # An EXTRA/stale version row (e.g. from another migration dir or a newer
    # schema) must make readiness fail — applied must EXACTLY match discovered.
    db_path = str(tmp_path / "extra_version.sqlite")
    apply_pending(db_path)
    conn = connect(db_path)
    try:
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES ('9999_unknown', 'x')"
        )
    finally:
        conn.close()
    assert check_ready(db_path) is False


def test_audit_events_tenant_fk(tmp_path):
    db_path = str(tmp_path / "audit.sqlite")
    apply_pending(db_path)
    conn = connect(db_path)
    try:
        conn.execute("INSERT INTO tenants (id, name) VALUES ('A', 'Ten A')")
        # NULL tenant (system event) and a valid tenant both succeed.
        conn.execute("INSERT INTO audit_events (id, tenant_id, action) VALUES ('e0', NULL, 'boot')")
        conn.execute("INSERT INTO audit_events (id, tenant_id, action) VALUES ('e1', 'A', 'login')")
        # A non-existent tenant id is rejected.
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                "INSERT INTO audit_events (id, tenant_id, action) VALUES ('e2', 'ghost', 'x')"
            )
        # Deleting the tenant NULLs the audit row's tenant_id (the trail survives).
        conn.execute("DELETE FROM tenants WHERE id = 'A'")
        row = conn.execute("SELECT tenant_id FROM audit_events WHERE id = 'e1'").fetchone()
        assert row[0] is None
    finally:
        conn.close()


# A hand-built, correct baseline schema; each readiness test tweaks ONE table's
# DDL to prove that specific constraint is what readiness enforces.
_BASELINE_SCHEMA: dict[str, str] = {
    "tenants": "CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL)",
    "users": (
        "CREATE TABLE users (id TEXT PRIMARY KEY, "
        "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, "
        "email TEXT, role TEXT)"
    ),
    "documents": (
        "CREATE TABLE documents (id TEXT PRIMARY KEY, "
        "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, "
        "title TEXT, UNIQUE (tenant_id, id))"
    ),
    "chunks": (
        "CREATE TABLE chunks (id TEXT PRIMARY KEY, "
        "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, "
        "document_id TEXT NOT NULL, ordinal INTEGER, content TEXT, "
        "FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id) ON DELETE CASCADE)"
    ),
    "ingest_jobs": (
        "CREATE TABLE ingest_jobs (id TEXT PRIMARY KEY, "
        "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, "
        "document_id TEXT, status TEXT, retries INTEGER, "
        "FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id) ON DELETE CASCADE)"
    ),
    "idempotency_keys": (
        "CREATE TABLE idempotency_keys (key TEXT, scope TEXT, "
        "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, "
        "PRIMARY KEY (tenant_id, scope, key))"
    ),
    "audit_events": (
        "CREATE TABLE audit_events (id TEXT PRIMARY KEY, "
        "tenant_id TEXT REFERENCES tenants (id) ON DELETE SET NULL, "
        "action TEXT, request_id TEXT)"
    ),
}


def _build_schema(db_path: str, **overrides: str) -> None:
    schema = {**_BASELINE_SCHEMA, **overrides}
    conn = connect(db_path)
    try:
        conn.execute("CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)")
        conn.execute("INSERT INTO schema_migrations VALUES ('0001_init', 'x')")
        for ddl in schema.values():
            conn.execute(ddl)
    finally:
        conn.close()


def test_check_ready_true_for_the_hand_built_baseline(tmp_path):
    # Sanity: the baseline harness produces a schema readiness accepts, so a
    # failing variant below is caused by the ONE constraint it removes.
    db_path = str(tmp_path / "baseline.sqlite")
    _build_schema(db_path)
    assert check_ready(db_path) is True


def test_check_ready_false_when_direct_tenant_fk_missing(tmp_path):
    # documents keeps its columns + parent UNIQUE but drops the direct
    # tenant_id -> tenants FK (orphan/unknown-tenant documents become possible).
    db_path = str(tmp_path / "nodocfk.sqlite")
    _build_schema(
        db_path,
        documents=(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, "
            "title TEXT, UNIQUE (tenant_id, id))"
        ),
    )
    assert check_ready(db_path) is False


def test_check_ready_false_when_parent_unique_missing(tmp_path):
    # documents lacks the UNIQUE (tenant_id, id) the composite FKs reference.
    db_path = str(tmp_path / "nounique.sqlite")
    _build_schema(
        db_path,
        documents=(
            "CREATE TABLE documents (id TEXT PRIMARY KEY, "
            "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, title TEXT)"
        ),
    )
    assert check_ready(db_path) is False


def test_check_ready_false_when_tenant_column_is_nullable(tmp_path):
    # users.tenant_id must be NOT NULL — a nullable one allows orphan rows.
    db_path = str(tmp_path / "nullable.sqlite")
    _build_schema(
        db_path,
        users=(
            "CREATE TABLE users (id TEXT PRIMARY KEY, "
            "tenant_id TEXT REFERENCES tenants (id) ON DELETE CASCADE, email TEXT, role TEXT)"
        ),
    )
    assert check_ready(db_path) is False


def test_check_ready_false_when_audit_tenant_not_null(tmp_path):
    # audit_events.tenant_id must stay NULLABLE (system events).
    db_path = str(tmp_path / "auditnn.sqlite")
    _build_schema(
        db_path,
        audit_events=(
            "CREATE TABLE audit_events (id TEXT PRIMARY KEY, "
            "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE SET NULL, "
            "action TEXT, request_id TEXT)"
        ),
    )
    assert check_ready(db_path) is False


def test_check_ready_false_when_audit_on_delete_wrong(tmp_path):
    # audit_events.tenant_id must use ON DELETE SET NULL, not CASCADE (a tenant
    # delete would otherwise destroy the audit trail).
    db_path = str(tmp_path / "auditcascade.sqlite")
    _build_schema(
        db_path,
        audit_events=(
            "CREATE TABLE audit_events (id TEXT PRIMARY KEY, "
            "tenant_id TEXT REFERENCES tenants (id) ON DELETE CASCADE, "
            "action TEXT, request_id TEXT)"
        ),
    )
    assert check_ready(db_path) is False
