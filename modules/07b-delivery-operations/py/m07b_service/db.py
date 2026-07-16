"""Datastore access primitives.

Connections enforce foreign keys and use row access. The readiness probe (which
verifies the *migrated* schema — versions, a column fingerprint, and write
capability) lives in :mod:`m07b_service.migrations` (``check_ready``).
"""

from __future__ import annotations

import sqlite3

# Tables created by the initial migration. Readiness requires all of them plus
# the migration runner's bookkeeping table.
REQUIRED_TABLES = frozenset(
    {
        "tenants",
        "users",
        "documents",
        "chunks",
        "ingest_jobs",
        "idempotency_keys",
        "audit_events",
    }
)
SCHEMA_MIGRATIONS_TABLE = "schema_migrations"

# Key columns per table — a fingerprint used by readiness so a same-named but
# structurally-incompatible table cannot pass as "migrated".
REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "tenants": frozenset({"id", "name"}),
    "users": frozenset({"id", "tenant_id", "email", "role"}),
    "documents": frozenset({"id", "tenant_id", "title"}),
    "chunks": frozenset({"id", "tenant_id", "document_id", "ordinal", "content"}),
    "ingest_jobs": frozenset({"id", "tenant_id", "status", "retries"}),
    "idempotency_keys": frozenset({"key", "scope", "tenant_id"}),
    "audit_events": frozenset({"id", "action", "request_id"}),
}

# Required foreign keys. Each descriptor is
# (referenced_table, {(from_col, to_col), ...}, on_delete_action); each table
# maps to the SET of FKs it must declare. Readiness fingerprints EVERY expected
# tenant FK — the direct ``*.tenant_id -> tenants(id)`` keys AND the composite
# ``(tenant_id, document_id) -> documents(tenant_id, id)`` keys — including the
# ON DELETE action, so a restored schema missing any of them (or with the wrong
# cascade behaviour) cannot pass as ready.
FkSpec = tuple[str, frozenset[tuple[str, str]], str]
_TENANT_FK: FkSpec = ("tenants", frozenset({("tenant_id", "id")}), "CASCADE")
_DOC_COMPOSITE_FK: FkSpec = (
    "documents",
    frozenset({("tenant_id", "tenant_id"), ("document_id", "id")}),
    "CASCADE",
)
_AUDIT_TENANT_FK: FkSpec = ("tenants", frozenset({("tenant_id", "id")}), "SET NULL")
REQUIRED_FOREIGN_KEYS: dict[str, frozenset[FkSpec]] = {
    "users": frozenset({_TENANT_FK}),
    "documents": frozenset({_TENANT_FK}),
    "chunks": frozenset({_TENANT_FK, _DOC_COMPOSITE_FK}),
    "ingest_jobs": frozenset({_TENANT_FK, _DOC_COMPOSITE_FK}),
    "idempotency_keys": frozenset({_TENANT_FK}),
    "audit_events": frozenset({_AUDIT_TENANT_FK}),
}

# Parent UNIQUE keys the composite FKs reference — required so those FKs are
# valid at write time (otherwise inserts fail with a "foreign key mismatch").
REQUIRED_UNIQUE_KEYS: dict[str, frozenset[str]] = {
    "documents": frozenset({"tenant_id", "id"}),
}

# tenant_id must be NOT NULL on these tenant-scoped tables (no orphan rows) ...
NOT_NULL_TENANT_TABLES = frozenset(
    {"users", "documents", "chunks", "ingest_jobs", "idempotency_keys"}
)
# ... and NULLABLE on these (system / unauthenticated audit events).
NULLABLE_TENANT_TABLES = frozenset({"audit_events"})


def connect(path: str) -> sqlite3.Connection:
    """Open a SQLite connection with row access + foreign keys enforced.

    ``isolation_level=None`` puts the connection in autocommit mode so the
    migration runner can manage explicit transactions itself. ``timeout=5.0``
    sets SQLite's busy timeout (5 s) as a floor for the lock wait.
    """
    conn = sqlite3.connect(path, isolation_level=None, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    # pragma_table_info() is the table-valued form, so the table name is BOUND
    # (no identifier interpolation / SQL injection).
    rows = conn.execute("SELECT name FROM pragma_table_info(?)", (table,)).fetchall()
    return {row[0] for row in rows}


def foreign_keys(conn: sqlite3.Connection, table: str) -> set[FkSpec]:
    """Return each FK on ``table`` as (referenced_table, {(from, to)...}, on_delete).

    Composite FKs span multiple ``pragma_foreign_key_list`` rows sharing an
    ``id``; we group by ``id`` and collapse the (from, to) column pairs. The
    ``on_delete`` action is the same for every row of a given FK.
    """
    rows = conn.execute(
        'SELECT id, "table", "from", "to", on_delete FROM pragma_foreign_key_list(?)',
        (table,),
    ).fetchall()
    grouped: dict[int, dict] = {}
    for row in rows:
        entry = grouped.setdefault(
            row["id"], {"table": row["table"], "pairs": set(), "on_delete": row["on_delete"]}
        )
        entry["pairs"].add((row["from"], row["to"]))
    return {
        (entry["table"], frozenset(entry["pairs"]), entry["on_delete"])
        for entry in grouped.values()
    }


def unique_column_sets(conn: sqlite3.Connection, table: str) -> set[frozenset[str]]:
    """Return the column set of every UNIQUE index (incl. PK) on ``table``."""
    result: set[frozenset[str]] = set()
    for index in conn.execute('SELECT name, "unique" FROM pragma_index_list(?)', (table,)):
        if index["unique"]:
            columns = {
                row["name"]
                for row in conn.execute("SELECT name FROM pragma_index_info(?)", (index["name"],))
            }
            result.add(frozenset(columns))
    return result


def not_null_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """Return the columns declared NOT NULL on ``table``."""
    rows = conn.execute('SELECT name, "notnull" FROM pragma_table_info(?)', (table,)).fetchall()
    return {row["name"] for row in rows if row["notnull"]}
