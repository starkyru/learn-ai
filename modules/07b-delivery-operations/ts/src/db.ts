/**
 * Datastore access primitives (node:sqlite).
 *
 * Uses Node's built-in `node:sqlite` (`DatabaseSync`) — zero-dependency and no
 * native build step (unlike better-sqlite3, whose prebuilt binary does not load
 * on this env's Node). `node:sqlite` is unflagged on Node >= 24, which the
 * Dockerfile/CI pin.
 *
 * The readiness probe (which verifies the migrated schema — versions, a column
 * fingerprint, and write capability) lives in `migrations.ts` (`checkReady`).
 */

import { DatabaseSync } from "node:sqlite";

export const REQUIRED_TABLES = [
  "tenants",
  "users",
  "documents",
  "chunks",
  "ingest_jobs",
  "idempotency_keys",
  "audit_events",
] as const;

export const SCHEMA_MIGRATIONS_TABLE = "schema_migrations";

// Key columns per table — a fingerprint used by readiness so a same-named but
// structurally-incompatible table cannot pass as "migrated".
export const REQUIRED_COLUMNS: Record<string, readonly string[]> = {
  tenants: ["id", "name"],
  users: ["id", "tenant_id", "email", "role"],
  documents: ["id", "tenant_id", "title"],
  chunks: ["id", "tenant_id", "document_id", "ordinal", "content"],
  ingest_jobs: ["id", "tenant_id", "status", "retries"],
  idempotency_keys: ["key", "scope", "tenant_id"],
  audit_events: ["id", "action", "request_id"],
};

// Required foreign keys, each canonicalised as "refTable|fromA>toA,...|onDelete"
// (column pairs sorted). Readiness fingerprints EVERY expected tenant FK — the
// direct `*.tenant_id -> tenants(id)` keys AND the composite `(tenant_id,
// document_id) -> documents(tenant_id, id)` keys — INCLUDING the on-delete
// action, so a DB recreated without any of them (or with the wrong cascade)
// cannot pass as ready.
const TENANT_FK = "tenants|tenant_id>id|CASCADE";
const DOC_COMPOSITE_FK = "documents|document_id>id,tenant_id>tenant_id|CASCADE";
export const REQUIRED_FOREIGN_KEYS: Record<string, readonly string[]> = {
  users: [TENANT_FK],
  documents: [TENANT_FK],
  chunks: [TENANT_FK, DOC_COMPOSITE_FK],
  ingest_jobs: [TENANT_FK, DOC_COMPOSITE_FK],
  idempotency_keys: [TENANT_FK],
  audit_events: ["tenants|tenant_id>id|SET NULL"],
};

// Parent UNIQUE keys the composite FKs reference (sorted column list), required
// so those FKs are valid at write time (else inserts fail with a mismatch).
export const REQUIRED_UNIQUE_KEYS: Record<string, string> = {
  documents: "id,tenant_id",
};

// tenant_id must be NOT NULL on these tenant-scoped tables (no orphan rows) ...
export const NOT_NULL_TENANT_TABLES = [
  "users",
  "documents",
  "chunks",
  "ingest_jobs",
  "idempotency_keys",
] as const;
// ... and NULLABLE on these (system / unauthenticated audit events).
export const NULLABLE_TENANT_TABLES = ["audit_events"] as const;

/** Open a SQLite connection with foreign keys enforced + a busy timeout floor. */
export function openDb(path: string): DatabaseSync {
  const db = new DatabaseSync(path);
  db.exec("PRAGMA foreign_keys = ON");
  db.exec("PRAGMA busy_timeout = 5000");
  return db;
}

export function tableNames(db: DatabaseSync): Set<string> {
  const rows = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all();
  return new Set(rows.map((row) => String(row.name)));
}

export function columnNames(db: DatabaseSync, table: string): Set<string> {
  // pragma_table_info() is the table-valued form, so the table name is BOUND
  // (no identifier interpolation / SQL injection).
  const rows = db.prepare("SELECT name FROM pragma_table_info(?)").all(table);
  return new Set(rows.map((row) => String(row.name)));
}

/** Each FK on `table`, canonicalised as "refTable|fromA>toA,...|onDelete". */
export function foreignKeys(db: DatabaseSync, table: string): Set<string> {
  const rows = db
    .prepare(
      'SELECT id, "table", "from", "to", on_delete FROM pragma_foreign_key_list(?)',
    )
    .all(table);
  // Composite FKs span multiple rows sharing an `id`; group them.
  const grouped = new Map<
    number,
    { refTable: string; pairs: string[]; onDelete: string }
  >();
  for (const row of rows) {
    const id = Number(row.id);
    const entry = grouped.get(id) ?? {
      refTable: String(row.table),
      pairs: [],
      onDelete: String(row.on_delete),
    };
    entry.pairs.push(`${String(row.from)}>${String(row.to)}`);
    grouped.set(id, entry);
  }
  const out = new Set<string>();
  for (const { refTable, pairs, onDelete } of grouped.values()) {
    out.add(`${refTable}|${pairs.sort().join(",")}|${onDelete}`);
  }
  return out;
}

/** The sorted column-list ("a,b,c") of every UNIQUE index (incl. PK) on `table`. */
export function uniqueColumnSets(db: DatabaseSync, table: string): Set<string> {
  const out = new Set<string>();
  const indexes = db
    .prepare('SELECT name, "unique" FROM pragma_index_list(?)')
    .all(table);
  for (const index of indexes) {
    if (Number(index.unique) !== 1) continue;
    const columns = db
      .prepare("SELECT name FROM pragma_index_info(?)")
      .all(String(index.name))
      .map((row) => String(row.name))
      .sort();
    out.add(columns.join(","));
  }
  return out;
}

/** The columns declared NOT NULL on `table`. */
export function notNullColumns(db: DatabaseSync, table: string): Set<string> {
  const rows = db
    .prepare('SELECT name, "notnull" FROM pragma_table_info(?)')
    .all(table);
  return new Set(
    rows.filter((row) => Number(row.notnull) === 1).map((row) => String(row.name)),
  );
}
