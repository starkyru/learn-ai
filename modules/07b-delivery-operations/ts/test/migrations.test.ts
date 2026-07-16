/** Tests for the numbered SQL migration runner (node:sqlite). */

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { performance } from "node:perf_hooks";
import { setTimeout as delay } from "node:timers/promises";

import { openDb, REQUIRED_TABLES, tableNames } from "../src/db.js";
import {
  appliedVersions,
  applyPending,
  checkReady,
  defaultLockTimeoutMs,
  discover,
  LOCK_TIMEOUT_BOUNDS,
  MigrationLockError,
  normalizeLockTimeoutMs,
  rollback,
} from "../src/migrations.js";

const EXPECTED_TABLES = [
  "tenants",
  "users",
  "documents",
  "chunks",
  "ingest_jobs",
  "idempotency_keys",
  "audit_events",
];

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-mig-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

function columns(dbPath: string, table: string): Set<string> {
  const db = openDb(dbPath);
  try {
    // pragma_table_info() is the table-valued form, so the table name is BOUND
    // (no identifier interpolation / SQL injection).
    const rows = db.prepare("SELECT name FROM pragma_table_info(?)").all(table);
    return new Set(rows.map((row) => String(row.name)));
  } finally {
    db.close();
  }
}

test("migrate from empty creates the full schema", () => {
  const dbPath = join(dir, "empty.sqlite");
  expect(applyPending(dbPath)).toEqual(["0001_init"]);

  const db = openDb(dbPath);
  try {
    const names = tableNames(db);
    for (const table of EXPECTED_TABLES) expect(names.has(table)).toBe(true);
    expect(names.has("schema_migrations")).toBe(true);
    // REQUIRED_TABLES (used by readiness) matches the created schema.
    expect([...REQUIRED_TABLES].sort()).toEqual([...EXPECTED_TABLES].sort());
    expect(appliedVersions(db)).toEqual(["0001_init"]);
  } finally {
    db.close();
  }

  expect(columns(dbPath, "users")).toEqual(
    new Set(["id", "tenant_id", "email", "role", "created_at"]),
  );
  expect(columns(dbPath, "chunks").has("tenant_id")).toBe(true);
  expect(columns(dbPath, "idempotency_keys")).toEqual(
    new Set(["key", "scope", "tenant_id", "result_ref", "created_at"]),
  );
});

test("apply is idempotent", () => {
  const dbPath = join(dir, "idempotent.sqlite");
  expect(applyPending(dbPath)).toEqual(["0001_init"]);
  // Second run applies nothing and does not error or duplicate rows.
  expect(applyPending(dbPath)).toEqual([]);

  const db = openDb(dbPath);
  try {
    expect(appliedVersions(db)).toEqual(["0001_init"]);
    const row = db.prepare("SELECT COUNT(*) AS c FROM schema_migrations").get();
    expect(Number(row?.c)).toBe(1);
  } finally {
    db.close();
  }
});

test("rollback then reapply", () => {
  const dbPath = join(dir, "rollback.sqlite");
  applyPending(dbPath);

  expect(rollback(dbPath)).toEqual(["0001_init"]);

  const db = openDb(dbPath);
  try {
    // The schema is gone (only the empty bookkeeping table remains).
    expect([...tableNames(db)]).toEqual(["schema_migrations"]);
    expect(appliedVersions(db)).toEqual([]);
  } finally {
    db.close();
  }

  // Re-applying after a rollback rebuilds the full schema.
  expect(applyPending(dbPath)).toEqual(["0001_init"]);
  const db2 = openDb(dbPath);
  try {
    const names = tableNames(db2);
    for (const table of EXPECTED_TABLES) expect(names.has(table)).toBe(true);
  } finally {
    db2.close();
  }
});

function writeMigrations(records: Record<string, string>): string {
  const migDir = mkdtempSync(join(dir, "custom-"));
  for (const [name, sql] of Object.entries(records)) {
    writeFileSync(join(migDir, name), sql);
  }
  return migDir;
}

test("a migration with a trigger and string semicolons applies cleanly", () => {
  const migDir = writeMigrations({
    "0001_trig.up.sql":
      "CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT DEFAULT 'a; b', bumped INTEGER DEFAULT 0);\n" +
      "CREATE TRIGGER bump AFTER INSERT ON notes BEGIN\n" +
      "  UPDATE notes SET bumped = 1 WHERE id = NEW.id;\n" +
      "END;\n",
  });
  const dbPath = join(dir, "trig.sqlite");
  expect(applyPending(dbPath, migDir)).toEqual(["0001_trig"]);

  const db = openDb(dbPath);
  try {
    db.exec("INSERT INTO notes (id) VALUES (1)");
    const row = db.prepare("SELECT body, bumped FROM notes WHERE id = 1").get();
    expect(String(row?.body)).toBe("a; b"); // string default with inner ';' survived
    expect(Number(row?.bumped)).toBe(1); // the trigger (body has ';') fired
  } finally {
    db.close();
  }
});

test("a failed migration leaves no partial schema and no version row", () => {
  const migDir = writeMigrations({
    // 2nd statement fails (duplicate table) — the whole migration rolls back.
    "0001_bad.up.sql":
      "CREATE TABLE keep_me (id TEXT);\nCREATE TABLE keep_me (id TEXT);\n",
  });
  const dbPath = join(dir, "bad.sqlite");
  expect(() => applyPending(dbPath, migDir)).toThrow();

  const db = openDb(dbPath);
  try {
    expect(tableNames(db).has("keep_me")).toBe(false); // first statement rolled back too
    expect(appliedVersions(db)).toEqual([]); // no version recorded
  } finally {
    db.close();
  }
});

test("foreign keys are enforced (rejects a bad tenant_id)", () => {
  const dbPath = join(dir, "fk.sqlite");
  applyPending(dbPath);

  const db = openDb(dbPath); // openDb sets PRAGMA foreign_keys = ON
  try {
    const insert = db.prepare(
      "INSERT INTO users (id, tenant_id, email) VALUES (?, ?, ?)",
    );
    expect(() => insert.run("u1", "no-such-tenant", "a@b.c")).toThrow(/FOREIGN KEY/i);
  } finally {
    db.close();
  }
});

test("discover throws on a missing directory", () => {
  expect(() => discover("/no/such/migrations/dir")).toThrow();
});

function raceApply(dbPath: string): Promise<{ status: number | null; stdout: string }> {
  return new Promise((resolve) => {
    const child = spawn("pnpm", ["exec", "tsx", "test/_apply_cli.ts", dbPath], {
      cwd: join(__dirname, ".."),
      env: process.env,
    });
    let stdout = "";
    child.stdout.on("data", (chunk) => (stdout += chunk));
    child.on("close", (status) => resolve({ status, stdout }));
  });
}

test("concurrent runners do not crash the loser", async () => {
  // Two separate processes race applyPending on a fresh DB. BEGIN IMMEDIATE +
  // the busy timeout must serialise them: both exit 0, exactly one applies.
  const dbPath = join(dir, "race.sqlite");
  const [a, b] = await Promise.all([raceApply(dbPath), raceApply(dbPath)]);

  expect(a.status).toBe(0);
  expect(b.status).toBe(0);
  const applied = [
    ...(JSON.parse(a.stdout || "[]") as string[]),
    ...(JSON.parse(b.stdout || "[]") as string[]),
  ];
  expect(applied.filter((v) => v === "0001_init").length).toBe(1);

  const db = openDb(dbPath);
  try {
    expect(appliedVersions(db)).toEqual(["0001_init"]); // one bookkeeping row
  } finally {
    db.close();
  }
}, 60_000);

test("defaultLockTimeoutMs rejects non-finite/invalid/overflowing env, falls back to 30 s", () => {
  // Parity with the Python fix. "1e306" is the round-5 overflow case: it is
  // finite+positive but * 1000 would be Infinity — it must fall back to 30 s
  // (never become an infinite deadline). "1000" (> 300 s cap) also falls back.
  const original = process.env.MIGRATION_LOCK_TIMEOUT_S;
  try {
    for (const bad of [
      "nan",
      "Infinity",
      "-Infinity",
      "0",
      "-5",
      "notanumber",
      "",
      "1e306",
      "1000",
    ]) {
      process.env.MIGRATION_LOCK_TIMEOUT_S = bad;
      const value = defaultLockTimeoutMs();
      expect(Number.isFinite(value)).toBe(true);
      expect(value).toBe(30_000);
    }
    process.env.MIGRATION_LOCK_TIMEOUT_S = "12.5";
    expect(defaultLockTimeoutMs()).toBe(12_500);
    delete process.env.MIGRATION_LOCK_TIMEOUT_S;
    expect(defaultLockTimeoutMs()).toBe(30_000);
  } finally {
    if (original === undefined) delete process.env.MIGRATION_LOCK_TIMEOUT_S;
    else process.env.MIGRATION_LOCK_TIMEOUT_S = original;
  }
});

test("normalizeLockTimeoutMs bounds every bad override value", () => {
  // The single normalizer for explicit lockTimeoutMs overrides. Each bad value
  // must yield the FINITE, bounded 30 s default — including 1e306 and Infinity
  // (which must NOT stay Infinity).
  for (const bad of [NaN, Infinity, -Infinity, 0, -5, 1e306, 400_000, undefined]) {
    const value = normalizeLockTimeoutMs(bad);
    expect(Number.isFinite(value)).toBe(true);
    expect(value).toBeGreaterThan(0);
    expect(value).toBeLessThanOrEqual(LOCK_TIMEOUT_BOUNDS.maxMs);
    expect(value).toBe(30_000);
  }
  expect(normalizeLockTimeoutMs(5_000)).toBe(5_000); // a normal value passes through
  expect(normalizeLockTimeoutMs(LOCK_TIMEOUT_BOUNDS.maxMs)).toBe(
    LOCK_TIMEOUT_BOUNDS.maxMs,
  );
});

test("a bad override does not hang applyPending under a held lock (MigrationLockError)", () => {
  // End-to-end through the PUBLIC api with a HELD write lock: a bad override
  // (NaN, Infinity, 1e306, 0, negative) must produce a BOUNDED wait ending in a
  // clear MigrationLockError. Shrink the bounds so the bounded wait is fast.
  const dbPath = join(dir, "badoverride.sqlite");
  const holder = openDb(dbPath);
  holder.exec("BEGIN IMMEDIATE");
  const savedDefault = LOCK_TIMEOUT_BOUNDS.defaultMs;
  const savedMax = LOCK_TIMEOUT_BOUNDS.maxMs;
  LOCK_TIMEOUT_BOUNDS.defaultMs = 150;
  LOCK_TIMEOUT_BOUNDS.maxMs = 150;
  try {
    for (const bad of [NaN, Infinity, 1e306, 0, -5]) {
      const started = Date.now();
      expect(() => applyPending(dbPath, undefined, bad)).toThrow(MigrationLockError);
      expect(Date.now() - started).toBeLessThan(3_000); // bounded, did not hang
    }
  } finally {
    LOCK_TIMEOUT_BOUNDS.defaultMs = savedDefault;
    LOCK_TIMEOUT_BOUNDS.maxMs = savedMax;
    holder.exec("ROLLBACK");
    holder.close();
  }
});

test("the migration lock deadline raises a clear MigrationLockError", () => {
  // Another connection holds the write lock past the deadline -> a clear error,
  // NOT a raw SQLITE_BUSY crash.
  const dbPath = join(dir, "deadline.sqlite");
  const holder = openDb(dbPath);
  holder.exec("BEGIN IMMEDIATE");
  try {
    expect(() => applyPending(dbPath, undefined, 200)).toThrow(MigrationLockError);
  } finally {
    holder.exec("ROLLBACK");
    holder.close();
  }
});

test("a backward wall-clock jump does not extend the lock wait past the deadline", () => {
  // The runner derives its deadline from a MONOTONIC clock, so a backward
  // system-clock (Date.now) adjustment mid-wait cannot grow `remaining` and
  // extend the wait. We stub Date.now to leap backward on every read: with the
  // old wall-clock code this loops effectively forever; with performance.now()
  // it still times out at the 200 ms deadline. Elapsed is measured with the
  // real (unstubbed) monotonic clock.
  const dbPath = join(dir, "clockjump.sqlite");
  const holder = openDb(dbPath);
  holder.exec("BEGIN IMMEDIATE");
  let tick = 0;
  const dateNowSpy = jest
    .spyOn(Date, "now")
    .mockImplementation(() => 1e12 - tick++ * 3_600_000); // jumps 1h backward each read
  const start = performance.now();
  try {
    expect(() => applyPending(dbPath, undefined, 200)).toThrow(MigrationLockError);
    expect(performance.now() - start).toBeLessThan(5_000); // bounded, did not hang
  } finally {
    dateNowSpy.mockRestore();
    holder.exec("ROLLBACK");
    holder.close();
  }
}, 15_000);

test("a runner blocked past the busy_timeout retries and still succeeds", async () => {
  // A separate process holds the lock for 400 ms (> the 50 ms per-attempt busy
  // timeout); applyPending must RETRY and succeed once the holder releases.
  const dbPath = join(dir, "retrywin.sqlite");
  const readyFile = join(dir, "retrywin.ready");
  const holder = spawn(
    "pnpm",
    ["exec", "tsx", "test/_hold_lock_cli.ts", dbPath, "400", readyFile],
    { cwd: join(__dirname, ".."), env: process.env },
  );
  try {
    for (let i = 0; i < 200 && !existsSync(readyFile); i++) await delay(25);
    expect(existsSync(readyFile)).toBe(true); // holder acquired the lock

    const applied = applyPending(dbPath, undefined, 5000); // retries, succeeds
    expect(applied).toEqual(["0001_init"]);
  } finally {
    await new Promise((resolve) => holder.on("close", resolve));
  }
}, 60_000);

test("composite FK blocks a cross-tenant document reference", () => {
  const dbPath = join(dir, "tenant.sqlite");
  applyPending(dbPath);
  const db = openDb(dbPath);
  try {
    db.exec("INSERT INTO tenants (id, name) VALUES ('A', 'Ten A'), ('B', 'Ten B')");
    db.exec(
      "INSERT INTO documents (id, tenant_id, title) VALUES ('doc1', 'A', 'A doc')",
    );

    // Same-tenant references succeed.
    db.exec(
      "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) VALUES ('c1', 'A', 'doc1', 0, 'x')",
    );
    db.exec(
      "INSERT INTO ingest_jobs (id, tenant_id, document_id) VALUES ('j1', 'A', 'doc1')",
    );
    db.exec("INSERT INTO ingest_jobs (id, tenant_id) VALUES ('j0', 'B')"); // null doc OK

    // Cross-tenant references (tenant B -> A's document) are rejected. (Use a
    // distinct ordinal so the composite FK, not the UNIQUE index, is what fires.)
    expect(() =>
      db.exec(
        "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) VALUES ('c2', 'B', 'doc1', 1, 'x')",
      ),
    ).toThrow(/FOREIGN KEY/i);
    expect(() =>
      db.exec(
        "INSERT INTO ingest_jobs (id, tenant_id, document_id) VALUES ('j2', 'B', 'doc1')",
      ),
    ).toThrow(/FOREIGN KEY/i);
  } finally {
    db.close();
  }
});

test("checkReady is true for a migrated writable DB, false when a version is missing", () => {
  const dbPath = join(dir, "cr.sqlite");
  applyPending(dbPath);
  expect(checkReady(dbPath)).toBe(true);

  const db = openDb(dbPath);
  try {
    db.exec("DELETE FROM schema_migrations"); // schema present, version gone
  } finally {
    db.close();
  }
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when a required table lacks a key column", () => {
  const dbPath = join(dir, "frag.sqlite");
  const db = openDb(dbPath);
  try {
    db.exec(
      "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)",
    );
    db.exec("INSERT INTO schema_migrations VALUES ('0001_init', 'x')");
    db.exec("CREATE TABLE tenants (id TEXT, name TEXT)");
    db.exec("CREATE TABLE users (id TEXT, email TEXT, role TEXT)"); // no tenant_id
    db.exec("CREATE TABLE documents (id TEXT, tenant_id TEXT, title TEXT)");
    db.exec(
      "CREATE TABLE chunks (id TEXT, tenant_id TEXT, document_id TEXT, ordinal INTEGER, content TEXT)",
    );
    db.exec(
      "CREATE TABLE ingest_jobs (id TEXT, tenant_id TEXT, status TEXT, retries INTEGER)",
    );
    db.exec("CREATE TABLE idempotency_keys (key TEXT, scope TEXT, tenant_id TEXT)");
    db.exec("CREATE TABLE audit_events (id TEXT, action TEXT, request_id TEXT)");
  } finally {
    db.close();
  }
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when the composite FK is removed", () => {
  // Same COLUMNS but WITHOUT the (tenant_id, document_id) composite FK -> not
  // ready (otherwise cross-tenant references would be possible).
  const dbPath = join(dir, "nofk.sqlite");
  const db = openDb(dbPath);
  try {
    db.exec(
      "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)",
    );
    db.exec("INSERT INTO schema_migrations VALUES ('0001_init', 'x')");
    db.exec("CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT)");
    db.exec("CREATE TABLE users (id TEXT, tenant_id TEXT, email TEXT, role TEXT)");
    db.exec(
      "CREATE TABLE documents (id TEXT PRIMARY KEY, tenant_id TEXT, title TEXT, UNIQUE (tenant_id, id))",
    );
    // Right columns, but no composite FK on chunks/ingest_jobs.
    db.exec(
      "CREATE TABLE chunks (id TEXT, tenant_id TEXT, document_id TEXT, ordinal INTEGER, content TEXT)",
    );
    db.exec(
      "CREATE TABLE ingest_jobs (id TEXT, tenant_id TEXT, document_id TEXT, status TEXT, retries INTEGER)",
    );
    db.exec("CREATE TABLE idempotency_keys (key TEXT, scope TEXT, tenant_id TEXT)");
    db.exec(
      "CREATE TABLE audit_events (id TEXT, tenant_id TEXT, action TEXT, request_id TEXT)",
    );
  } finally {
    db.close();
  }
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false with an unknown/stale migration version", () => {
  const dbPath = join(dir, "extraver.sqlite");
  applyPending(dbPath);
  const db = openDb(dbPath);
  try {
    db.exec(
      "INSERT INTO schema_migrations (version, applied_at) VALUES ('9999_unknown', 'x')",
    );
  } finally {
    db.close();
  }
  expect(checkReady(dbPath)).toBe(false); // applied must EXACTLY match discovered
});

test("audit_events tenant_id is a nullable FK with ON DELETE SET NULL", () => {
  const dbPath = join(dir, "audit.sqlite");
  applyPending(dbPath);
  const db = openDb(dbPath);
  try {
    db.exec("INSERT INTO tenants (id, name) VALUES ('A', 'Ten A')");
    // NULL (system event) and a valid tenant both succeed.
    db.exec(
      "INSERT INTO audit_events (id, tenant_id, action) VALUES ('e0', NULL, 'boot')",
    );
    db.exec(
      "INSERT INTO audit_events (id, tenant_id, action) VALUES ('e1', 'A', 'login')",
    );
    // A non-existent tenant id is rejected.
    expect(() =>
      db.exec(
        "INSERT INTO audit_events (id, tenant_id, action) VALUES ('e2', 'ghost', 'x')",
      ),
    ).toThrow(/FOREIGN KEY/i);
    // Deleting the tenant NULLs the audit row's tenant_id (the trail survives).
    db.exec("DELETE FROM tenants WHERE id = 'A'");
    const row = db.prepare("SELECT tenant_id FROM audit_events WHERE id = 'e1'").get();
    expect(row?.tenant_id).toBeNull();
  } finally {
    db.close();
  }
});

// A hand-built, correct baseline schema; each readiness test tweaks ONE table's
// DDL to prove that specific constraint is what readiness enforces.
const BASELINE_SCHEMA: Record<string, string> = {
  tenants: "CREATE TABLE tenants (id TEXT PRIMARY KEY, name TEXT NOT NULL)",
  users:
    "CREATE TABLE users (id TEXT PRIMARY KEY, " +
    "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, email TEXT, role TEXT)",
  documents:
    "CREATE TABLE documents (id TEXT PRIMARY KEY, " +
    "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, title TEXT, " +
    "UNIQUE (tenant_id, id))",
  chunks:
    "CREATE TABLE chunks (id TEXT PRIMARY KEY, " +
    "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, " +
    "document_id TEXT NOT NULL, ordinal INTEGER, content TEXT, " +
    "FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id) ON DELETE CASCADE)",
  ingest_jobs:
    "CREATE TABLE ingest_jobs (id TEXT PRIMARY KEY, " +
    "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, " +
    "document_id TEXT, status TEXT, retries INTEGER, " +
    "FOREIGN KEY (tenant_id, document_id) REFERENCES documents (tenant_id, id) ON DELETE CASCADE)",
  idempotency_keys:
    "CREATE TABLE idempotency_keys (key TEXT, scope TEXT, " +
    "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, " +
    "PRIMARY KEY (tenant_id, scope, key))",
  audit_events:
    "CREATE TABLE audit_events (id TEXT PRIMARY KEY, " +
    "tenant_id TEXT REFERENCES tenants (id) ON DELETE SET NULL, action TEXT, request_id TEXT)",
};

function buildSchema(dbPath: string, overrides: Record<string, string> = {}): void {
  const schema = { ...BASELINE_SCHEMA, ...overrides };
  const db = openDb(dbPath);
  try {
    db.exec(
      "CREATE TABLE schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT)",
    );
    db.exec("INSERT INTO schema_migrations VALUES ('0001_init', 'x')");
    for (const ddl of Object.values(schema)) db.exec(ddl);
  } finally {
    db.close();
  }
}

test("checkReady is true for the hand-built baseline schema", () => {
  // Sanity: the baseline harness produces a schema readiness accepts, so a
  // failing variant below is caused by the ONE constraint it removes.
  const dbPath = join(dir, "baseline.sqlite");
  buildSchema(dbPath);
  expect(checkReady(dbPath)).toBe(true);
});

test("checkReady is false when the direct documents.tenant_id FK is missing", () => {
  const dbPath = join(dir, "nodocfk.sqlite");
  buildSchema(dbPath, {
    documents:
      "CREATE TABLE documents (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, title TEXT, " +
      "UNIQUE (tenant_id, id))",
  });
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when the parent UNIQUE (tenant_id, id) is missing", () => {
  const dbPath = join(dir, "nounique.sqlite");
  buildSchema(dbPath, {
    documents:
      "CREATE TABLE documents (id TEXT PRIMARY KEY, " +
      "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE CASCADE, title TEXT)",
  });
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when a tenant_id column is nullable", () => {
  const dbPath = join(dir, "nullable.sqlite");
  buildSchema(dbPath, {
    users:
      "CREATE TABLE users (id TEXT PRIMARY KEY, " +
      "tenant_id TEXT REFERENCES tenants (id) ON DELETE CASCADE, email TEXT, role TEXT)",
  });
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when audit_events.tenant_id is NOT NULL", () => {
  const dbPath = join(dir, "auditnn.sqlite");
  buildSchema(dbPath, {
    audit_events:
      "CREATE TABLE audit_events (id TEXT PRIMARY KEY, " +
      "tenant_id TEXT NOT NULL REFERENCES tenants (id) ON DELETE SET NULL, action TEXT, request_id TEXT)",
  });
  expect(checkReady(dbPath)).toBe(false);
});

test("checkReady is false when audit_events uses the wrong ON DELETE action", () => {
  const dbPath = join(dir, "auditcascade.sqlite");
  buildSchema(dbPath, {
    audit_events:
      "CREATE TABLE audit_events (id TEXT PRIMARY KEY, " +
      "tenant_id TEXT REFERENCES tenants (id) ON DELETE CASCADE, action TEXT, request_id TEXT)",
  });
  expect(checkReady(dbPath)).toBe(false);
});
