/**
 * Numbered SQL migration runner (TypeScript side, node:sqlite).
 *
 * Consumes the SAME `.sql` files as the Python runner (the module's
 * `migrations/` directory): each migration is a pair `NNNN_name.up.sql` /
 * `NNNN_name.down.sql`. Applied versions are recorded in `schema_migrations`.
 *
 * - `applyPending` is idempotent — applies only migrations not yet recorded;
 *   re-running is a no-op.
 * - `rollback` runs the latest applied migration's `.down.sql` and removes its
 *   `schema_migrations` row.
 *
 * Concurrency: both take a write lock with `BEGIN IMMEDIATE` *before* reading
 * `schema_migrations` (and `openDb` sets a busy timeout), so a second runner
 * blocks until the first commits and then finds nothing to do — closing the
 * read-decide-apply (TOCTOU) window.
 *
 * Each migration file is executed as a whole via `db.exec(...)` inside the
 * transaction: `node:sqlite` runs multi-statement scripts natively, so a `;`
 * inside a string literal or a `CREATE TRIGGER ... BEGIN ... END;` body is not a
 * problem, and it is atomic under the surrounding transaction. Every *value*
 * written to `schema_migrations` is parameterised.
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { performance } from "node:perf_hooks";
import type { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

import {
  columnNames,
  foreignKeys,
  NOT_NULL_TENANT_TABLES,
  notNullColumns,
  NULLABLE_TENANT_TABLES,
  openDb,
  REQUIRED_COLUMNS,
  REQUIRED_FOREIGN_KEYS,
  REQUIRED_TABLES,
  REQUIRED_UNIQUE_KEYS,
  SCHEMA_MIGRATIONS_TABLE,
  tableNames,
  uniqueColumnSets,
} from "./db.js";

/** Raised when the migration write lock cannot be acquired within the deadline. */
export class MigrationLockError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MigrationLockError";
  }
}

// Bounds for the migration lock timeout. `maxMs` is a sensible cap so no value
// can produce an effectively-infinite deadline (or overflow to Infinity when
// scaling seconds -> ms). Exposed as a mutable object so tests can shorten it.
export const LOCK_TIMEOUT_BOUNDS = { defaultMs: 30_000, maxMs: 300_000 };

/**
 * Coerce a millisecond timeout to a FINITE, positive, bounded value. The SINGLE
 * choke point for every explicit `lockTimeoutMs` override. A NaN/Infinity,
 * non-positive, or out-of-range (> max) value falls back to the default — so the
 * lock-acquire loop can never receive an infinite deadline. Mirrors Python.
 */
export function normalizeLockTimeoutMs(ms: number | undefined): number {
  if (
    ms === undefined ||
    !Number.isFinite(ms) ||
    ms <= 0 ||
    ms > LOCK_TIMEOUT_BOUNDS.maxMs
  ) {
    return LOCK_TIMEOUT_BOUNDS.defaultMs;
  }
  return ms;
}

/**
 * Read `MIGRATION_LOCK_TIMEOUT_S` (seconds) as a normalized timeout in ms. The
 * SECONDS are bounds-checked BEFORE the `* 1000` scaling, so a huge value can
 * never overflow to Infinity — it just falls back to the default.
 */
export function defaultLockTimeoutMs(): number {
  const seconds = Number(process.env.MIGRATION_LOCK_TIMEOUT_S);
  const maxSeconds = LOCK_TIMEOUT_BOUNDS.maxMs / 1000;
  if (!Number.isFinite(seconds) || seconds <= 0 || seconds > maxSeconds) {
    return LOCK_TIMEOUT_BOUNDS.defaultMs;
  }
  return seconds * 1000;
}

/** Block the current thread for `ms` (node:sqlite is synchronous). */
function sleepSync(ms: number): void {
  if (ms <= 0) return;
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function isBusy(err: unknown): boolean {
  const e = err as { errcode?: number; message?: string };
  if (e?.errcode === 5) return true; // SQLITE_BUSY
  const message = String(e?.message ?? err).toLowerCase();
  return message.includes("locked") || message.includes("busy");
}

/**
 * Take the write lock (`BEGIN IMMEDIATE`), retrying while another runner holds
 * it until `timeoutMs` elapses. A `SQLITE_BUSY` is retryable; only the deadline
 * turns it into a clear `MigrationLockError` (never a raw crash / restart loop).
 *
 * The deadline is derived and checked with `performance.now()` — a MONOTONIC
 * clock (like Python's `time.monotonic()`), NOT the wall clock (`Date.now()`).
 * A backward system-clock adjustment can't grow `remaining` and extend the wait
 * past the (normalized, capped) timeout.
 */
function acquireLock(db: DatabaseSync, timeoutMs: number): void {
  db.exec("PRAGMA busy_timeout = 50"); // short per-attempt wait; we retry
  const deadline = performance.now() + timeoutMs;
  let delay = 20;
  for (;;) {
    try {
      db.exec("BEGIN IMMEDIATE");
      return;
    } catch (err) {
      if (!isBusy(err)) throw err;
      const remaining = deadline - performance.now();
      if (remaining <= 0) {
        throw new MigrationLockError(
          `could not acquire the migration write lock within ${timeoutMs} ms ` +
            "(another runner is holding it)",
        );
      }
      sleepSync(Math.min(delay, remaining));
      delay = Math.min(delay * 2, 500);
    }
  }
}

const UP_SUFFIX = ".up.sql";
const DOWN_SUFFIX = ".down.sql";

interface Migration {
  version: string;
  upPath: string;
  downPath: string | null;
}

export function defaultMigrationsDir(): string {
  const override = process.env.MIGRATIONS_DIR;
  if (override) return override;
  // Resolve relative to THIS file (ts/src/migrations.ts) -> ../../migrations.
  // `import.meta.url` works under both tsx (ESM) and jest (swc), unlike
  // `__dirname`, which is undefined in ESM.
  const here = dirname(fileURLToPath(import.meta.url));
  return join(here, "..", "..", "migrations");
}

export function discover(migrationsDir?: string): Migration[] {
  // readdirSync throws ENOENT on a missing dir (fail-loud, matching Python).
  const root = migrationsDir ?? defaultMigrationsDir();
  return readdirSync(root)
    .filter((name) => name.endsWith(UP_SUFFIX))
    .sort()
    .map((upName) => {
      const version = upName.slice(0, -UP_SUFFIX.length);
      const downPath = join(root, `${version}${DOWN_SUFFIX}`);
      return {
        version,
        upPath: join(root, upName),
        downPath: existsSync(downPath) ? downPath : null,
      };
    });
}

function ensureBookkeeping(db: DatabaseSync): void {
  db.exec(
    "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)",
  );
}

export function appliedVersions(db: DatabaseSync): string[] {
  ensureBookkeeping(db);
  const rows = db
    .prepare("SELECT version FROM schema_migrations ORDER BY version")
    .all();
  return rows.map((row) => String(row.version));
}

function inImmediateTransaction(
  db: DatabaseSync,
  lockTimeoutMs: number,
  work: () => void,
): void {
  // Take the write lock up front (with retry) so concurrent runners serialise
  // and a slow first runner doesn't crash the loser (TOCTOU + BUSY safe).
  acquireLock(db, lockTimeoutMs);
  try {
    work();
    db.exec("COMMIT");
  } catch (err) {
    db.exec("ROLLBACK");
    throw err;
  }
}

/** Apply every not-yet-applied migration in order. Returns versions applied. */
export function applyPending(
  path: string,
  migrationsDir?: string,
  lockTimeoutMs?: number,
): string[] {
  // Normalize the override (or fall back to the env var), so the retry loop
  // never sees a NaN / infinite / overflowing deadline.
  const timeoutMs =
    lockTimeoutMs === undefined
      ? defaultLockTimeoutMs()
      : normalizeLockTimeoutMs(lockTimeoutMs);
  const migrations = discover(migrationsDir);
  const db = openDb(path);
  const applied: string[] = [];
  try {
    inImmediateTransaction(db, timeoutMs, () => {
      const done = new Set(appliedVersions(db));
      for (const migration of migrations) {
        if (done.has(migration.version)) continue;
        db.exec(readFileSync(migration.upPath, "utf8")); // whole file, atomic
        db.prepare(
          "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
        ).run(migration.version, new Date().toISOString());
        applied.push(migration.version);
      }
    });
    return applied;
  } finally {
    db.close();
  }
}

/** Roll back the `steps` most-recently-applied migrations. Returns them. */
export function rollback(
  path: string,
  migrationsDir?: string,
  steps = 1,
  lockTimeoutMs?: number,
): string[] {
  const timeoutMs =
    lockTimeoutMs === undefined
      ? defaultLockTimeoutMs()
      : normalizeLockTimeoutMs(lockTimeoutMs);
  const byVersion = new Map(discover(migrationsDir).map((m) => [m.version, m]));
  const db = openDb(path);
  const rolledBack: string[] = [];
  try {
    inImmediateTransaction(db, timeoutMs, () => {
      for (let i = 0; i < steps; i++) {
        const applied = appliedVersions(db);
        if (applied.length === 0) break;
        const version = applied[applied.length - 1];
        const migration = byVersion.get(version);
        if (!migration || migration.downPath === null) {
          throw new Error(`No down migration for applied version ${version}`);
        }
        db.exec(readFileSync(migration.downPath, "utf8"));
        db.prepare("DELETE FROM schema_migrations WHERE version = ?").run(version);
        rolledBack.push(version);
      }
    });
    return rolledBack;
  } finally {
    db.close();
  }
}

/**
 * Readiness: the DB is present, migrated, schema-compatible, AND writable.
 *
 * Stronger than a table-name check — a read-only DB, a DB missing/with an extra
 * migration, or same-named-but-incompatible tables (wrong columns, or missing
 * the tenant-integrity foreign keys) must NOT report ready. Verifies: every
 * required table + `schema_migrations`; each table's key columns (fingerprint);
 * the required foreign keys (so cross-tenant references stay impossible even
 * after a restore/recreate); that `schema_migrations` records EXACTLY the
 * discovered version set (no missing, no unknown/stale rows); and write
 * capability (`BEGIN IMMEDIATE` + `CREATE TABLE` + `ROLLBACK` — an
 * advisory-lock-only `BEGIN IMMEDIATE` does not detect a read-only file).
 *
 * The probe is NON-BLOCKING (`busy_timeout = 0`): if a migration currently holds
 * the write lock, it returns false fast rather than stalling the event loop.
 */
export function checkReady(path: string, migrationsDir?: string): boolean {
  let db: DatabaseSync | undefined;
  try {
    db = openDb(path);
    db.exec("PRAGMA busy_timeout = 0"); // never block the request event loop
    const names = tableNames(db);
    if (!names.has(SCHEMA_MIGRATIONS_TABLE)) return false;
    if (!REQUIRED_TABLES.every((table) => names.has(table))) return false;

    for (const [table, columns] of Object.entries(REQUIRED_COLUMNS)) {
      const existing = columnNames(db, table);
      if (!columns.every((column) => existing.has(column))) return false;
    }

    for (const [table, requiredFks] of Object.entries(REQUIRED_FOREIGN_KEYS)) {
      const present = foreignKeys(db, table);
      if (!requiredFks.every((fk) => present.has(fk))) return false;
    }

    for (const [table, uniqueCols] of Object.entries(REQUIRED_UNIQUE_KEYS)) {
      if (!uniqueColumnSets(db, table).has(uniqueCols)) return false;
    }

    for (const table of NOT_NULL_TENANT_TABLES) {
      if (!notNullColumns(db, table).has("tenant_id")) return false;
    }
    for (const table of NULLABLE_TENANT_TABLES) {
      if (notNullColumns(db, table).has("tenant_id")) return false;
    }

    const applied = db
      .prepare("SELECT version FROM schema_migrations")
      .all()
      .map((r) => String(r.version))
      .sort();
    const expected = discover(migrationsDir).map((m) => m.version); // already sorted
    if (
      applied.length !== expected.length ||
      !applied.every((v, i) => v === expected[i])
    ) {
      return false; // EXACT set + order (no missing, no unknown)
    }

    db.exec("BEGIN IMMEDIATE");
    db.exec("CREATE TABLE _readyz_write_probe (x)");
    db.exec("ROLLBACK");
    return true;
  } catch {
    try {
      db?.exec("ROLLBACK");
    } catch {
      // no active transaction — ignore
    }
    return false;
  } finally {
    db?.close();
  }
}
