"""Numbered SQL migration runner (Python side).

Consumes the SAME ``.sql`` files as the TypeScript runner (under the module's
``migrations/`` directory): each migration is a pair ``NNNN_name.up.sql`` /
``NNNN_name.down.sql``. Applied versions are recorded in ``schema_migrations``.

* ``apply_pending`` is idempotent — it applies only migrations not yet recorded,
  and re-running it is a no-op.
* ``rollback`` runs the most-recently-applied migration's ``.down.sql`` and
  removes its ``schema_migrations`` row.

Concurrency: both ``apply_pending`` and ``rollback`` take a write lock with
``BEGIN IMMEDIATE`` *before* reading ``schema_migrations`` and set a
``busy_timeout``, so a second runner blocks until the first commits and then
finds nothing to do — closing the read-decide-apply (TOCTOU) window. (Still,
avoid running two runners against the same ``DB_PATH`` on a filesystem without
reliable SQLite locking, e.g. some network mounts.)

Statements are split with SQLite's own ``complete_statement`` (so a ``;`` inside
a string literal or a ``CREATE TRIGGER ... BEGIN ... END;`` body does not split
the statement) and executed one at a time inside the transaction. Every *value*
written to ``schema_migrations`` is parameterised.
"""

from __future__ import annotations

import math
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .db import (
    NOT_NULL_TENANT_TABLES,
    NULLABLE_TENANT_TABLES,
    REQUIRED_COLUMNS,
    REQUIRED_FOREIGN_KEYS,
    REQUIRED_TABLES,
    REQUIRED_UNIQUE_KEYS,
    SCHEMA_MIGRATIONS_TABLE,
    column_names,
    connect,
    foreign_keys,
    not_null_columns,
    table_names,
    unique_column_sets,
)

_UP_SUFFIX = ".up.sql"
_DOWN_SUFFIX = ".down.sql"
# Per-attempt lock wait (short, so BEGIN IMMEDIATE fails fast and we can retry).
_LOCK_BUSY_MS = 50
_DEFAULT_LOCK_TIMEOUT_S = 30.0
# A sensible upper bound: anything larger is treated as invalid, so no value can
# produce an effectively-infinite deadline (or overflow when scaled to ms).
_MAX_LOCK_TIMEOUT_S = 300.0


def _normalize_lock_timeout_s(value: float | str | None) -> float:
    """Coerce a lock timeout to a FINITE, positive, bounded number of seconds.

    The SINGLE choke point for BOTH the ``MIGRATION_LOCK_TIMEOUT_S`` env var and
    every explicit ``lock_timeout_s`` override. A ``None``, non-finite
    (``nan``/``inf``), non-positive, malformed, or out-of-range (> the max) value
    falls back to the 30 s default — so the lock-acquire loop can never receive a
    NaN/infinite deadline and retry forever. Mirrors the TypeScript runner.
    """
    if value is None:
        return _DEFAULT_LOCK_TIMEOUT_S
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return _DEFAULT_LOCK_TIMEOUT_S
    if not math.isfinite(seconds) or seconds <= 0 or seconds > _MAX_LOCK_TIMEOUT_S:
        return _DEFAULT_LOCK_TIMEOUT_S
    return seconds


def _resolve_lock_timeout_s(override: float | None) -> float:
    """Normalize an explicit override, or the env var when no override is given."""
    source = override if override is not None else os.getenv("MIGRATION_LOCK_TIMEOUT_S")
    return _normalize_lock_timeout_s(source)


def _default_lock_timeout_s() -> float:
    """The normalized env-var timeout (used when no override is passed)."""
    return _normalize_lock_timeout_s(os.getenv("MIGRATION_LOCK_TIMEOUT_S"))


class MigrationLockError(RuntimeError):
    """Raised when the migration write lock cannot be acquired within the deadline."""


def default_migrations_dir() -> Path:
    """The shared ``migrations/`` dir, from ``MIGRATIONS_DIR`` or module-relative."""
    override = os.getenv("MIGRATIONS_DIR")
    if override:
        return Path(override)
    # py/m07b_service/migrations.py -> parents[2] == the module root.
    return Path(__file__).resolve().parents[2] / "migrations"


@dataclass(frozen=True)
class Migration:
    version: str
    up_path: Path
    down_path: Path | None


def discover(migrations_dir: str | Path | None = None) -> list[Migration]:
    """Return migrations sorted by their numeric/lexical version prefix.

    Fails loudly (like the TS ``readdirSync``) if the directory does not exist,
    so a misconfigured ``MIGRATIONS_DIR`` surfaces at startup instead of silently
    applying zero migrations and leaving ``/readyz`` stuck at 503.
    """
    root = Path(migrations_dir) if migrations_dir is not None else default_migrations_dir()
    if not root.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {root}")
    migrations: list[Migration] = []
    for up_path in sorted(root.glob(f"*{_UP_SUFFIX}")):
        version = up_path.name[: -len(_UP_SUFFIX)]
        down_path = up_path.with_name(f"{version}{_DOWN_SUFFIX}")
        migrations.append(
            Migration(
                version=version,
                up_path=up_path,
                down_path=down_path if down_path.exists() else None,
            )
        )
    return migrations


def _split_statements(sql: str) -> list[str]:
    """Split SQL into complete statements using SQLite's own completeness check.

    ``sqlite3.complete_statement`` understands string literals AND compound
    statements (a ``CREATE TRIGGER`` body is not complete until ``END;``), so a
    ``;`` inside either does not split. Fragments that are only whitespace /
    semicolons (e.g. the empty tail after a trailing ``;``) are dropped.
    """
    statements: list[str] = []
    buffer = ""
    for fragment in sql.split(";"):
        buffer += fragment
        candidate = buffer + ";"
        if sqlite3.complete_statement(candidate):
            if candidate.strip(" \t\r\n;"):  # has real content, not just ;/space
                statements.append(candidate.strip())
            buffer = ""
        else:
            # The ``;`` was inside a string / trigger body — keep accumulating.
            buffer += ";"
    if buffer.strip(" \t\r\n;"):
        statements.append(buffer.strip())
    return statements


def _is_busy(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "lock" in message or "busy" in message


def _acquire_lock(conn: sqlite3.Connection, timeout_s: float) -> None:
    """Take the write lock (``BEGIN IMMEDIATE``), retrying while another runner
    holds it, until ``timeout_s`` elapses. A ``SQLITE_BUSY`` is retryable; only
    the deadline turns it into a clear :class:`MigrationLockError` (never a raw
    crash / restart loop).
    """
    conn.execute("PRAGMA busy_timeout = 50")  # short per-attempt wait; we retry
    deadline = time.monotonic() + timeout_s
    delay = 0.02
    while True:
        try:
            conn.execute("BEGIN IMMEDIATE")
            return
        except sqlite3.OperationalError as exc:
            if not _is_busy(exc):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MigrationLockError(
                    f"could not acquire the migration write lock within {timeout_s}s "
                    "(another runner is holding it)"
                ) from exc
            time.sleep(min(delay, remaining))
            delay = min(delay * 2, 0.5)


def _ensure_bookkeeping(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version TEXT PRIMARY KEY,"
        " applied_at TEXT NOT NULL"
        ")"
    )


def applied_versions(conn: sqlite3.Connection) -> list[str]:
    _ensure_bookkeeping(conn)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return [row[0] for row in rows]


def apply_pending(
    path: str,
    migrations_dir: str | Path | None = None,
    *,
    lock_timeout_s: float | None = None,
) -> list[str]:
    """Apply every not-yet-applied migration in order. Returns versions applied.

    The whole read-decide-apply cycle runs inside ONE ``BEGIN IMMEDIATE``
    transaction (acquired with retry/backoff up to ``lock_timeout_s``), so
    concurrent runners serialise and a partial run rolls back entirely (no
    partial schema, no orphan ``schema_migrations`` row). The timeout — from the
    override OR the env var — is always normalized to a finite, bounded value.
    """
    lock_timeout_s = _resolve_lock_timeout_s(lock_timeout_s)
    migrations = discover(migrations_dir)
    conn = connect(path)
    newly_applied: list[str] = []
    try:
        _acquire_lock(conn, lock_timeout_s)  # write lock BEFORE reading state
        try:
            done = set(applied_versions(conn))
            for migration in migrations:
                if migration.version in done:
                    continue
                for statement in _split_statements(migration.up_path.read_text()):
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (migration.version, datetime.now(timezone.utc).isoformat()),
                )
                newly_applied.append(migration.version)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return newly_applied
    finally:
        conn.close()


def rollback(
    path: str,
    migrations_dir: str | Path | None = None,
    *,
    steps: int = 1,
    lock_timeout_s: float | None = None,
) -> list[str]:
    """Roll back the ``steps`` most-recently-applied migrations. Returns them."""
    lock_timeout_s = _resolve_lock_timeout_s(lock_timeout_s)
    migrations = {m.version: m for m in discover(migrations_dir)}
    conn = connect(path)
    rolled_back: list[str] = []
    try:
        _acquire_lock(conn, lock_timeout_s)
        try:
            for _ in range(steps):
                applied = applied_versions(conn)
                if not applied:
                    break
                version = applied[-1]  # most recent
                migration = migrations.get(version)
                if migration is None or migration.down_path is None:
                    raise RuntimeError(f"No down migration for applied version {version!r}")
                for statement in _split_statements(migration.down_path.read_text()):
                    conn.execute(statement)
                conn.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                rolled_back.append(version)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return rolled_back
    finally:
        conn.close()


def check_ready(path: str, migrations_dir: str | Path | None = None) -> bool:
    """Readiness: the DB is present, migrated, schema-compatible, AND writable.

    Stronger than a table-name check — a read-only DB, a DB missing/with an extra
    migration, or same-named-but-incompatible tables (wrong columns, or missing
    the tenant-integrity foreign keys) must NOT report ready. It verifies:

    * every required table + ``schema_migrations`` exists,
    * each table has its key columns (a schema fingerprint),
    * the required foreign keys are present (so cross-tenant references stay
      impossible even after a restore/recreate),
    * ``schema_migrations`` records EXACTLY the discovered version set (no missing
      and no unknown/stale rows), and
    * the DB is writable (a ``BEGIN IMMEDIATE`` + ``CREATE TABLE`` + ``ROLLBACK``
      probe — an advisory-lock-only ``BEGIN IMMEDIATE`` does not detect a
      read-only file, so the probe issues a real (rolled-back) write).

    The probe is NON-BLOCKING (``busy_timeout = 0``): if a migration currently
    holds the write lock, it returns False fast rather than stalling the caller.
    """
    conn: sqlite3.Connection | None = None
    try:
        conn = connect(path)
        conn.execute("PRAGMA busy_timeout = 0")  # never block a readiness probe
        names = table_names(conn)
        if SCHEMA_MIGRATIONS_TABLE not in names or not REQUIRED_TABLES.issubset(names):
            return False
        for table, columns in REQUIRED_COLUMNS.items():
            if not columns.issubset(column_names(conn, table)):
                return False
        for table, required_fks in REQUIRED_FOREIGN_KEYS.items():
            if not required_fks.issubset(foreign_keys(conn, table)):
                return False
        for table, unique_cols in REQUIRED_UNIQUE_KEYS.items():
            if unique_cols not in unique_column_sets(conn, table):
                return False
        for table in NOT_NULL_TENANT_TABLES:
            if "tenant_id" not in not_null_columns(conn, table):
                return False
        for table in NULLABLE_TENANT_TABLES:
            if "tenant_id" in not_null_columns(conn, table):
                return False
        applied = sorted(row[0] for row in conn.execute("SELECT version FROM schema_migrations"))
        expected = [migration.version for migration in discover(migrations_dir)]
        if applied != expected:  # EXACT set + order (no missing, no unknown)
            return False
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("CREATE TABLE _readyz_write_probe (x)")
        conn.execute("ROLLBACK")
        return True
    except (sqlite3.Error, OSError):
        if conn is not None:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        return False
    finally:
        if conn is not None:
            conn.close()
