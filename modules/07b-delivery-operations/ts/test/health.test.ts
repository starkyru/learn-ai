/** /healthz (liveness) and /readyz (readiness reflects the MIGRATED database). */

import { chmodSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { buildApp } from "../src/app.js";
import { openDb } from "../src/db.js";
import { applyPending } from "../src/migrations.js";
import { discardSink, makeConfig } from "./fakes.js";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-health-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

test("healthz is 200 with {status: ok} when the process is up", async () => {
  const app = buildApp({
    config: makeConfig(join(dir, "a.sqlite")),
    logSink: discardSink,
  });
  const res = await app.inject({ method: "GET", url: "/healthz" });
  await app.close();

  expect(res.statusCode).toBe(200);
  expect(res.json()).toEqual({ status: "ok" });
});

test("readyz is 503 while the DB is unmigrated", async () => {
  const app = buildApp({
    config: makeConfig(join(dir, "unmigrated.sqlite")),
    logSink: discardSink,
  });
  const res = await app.inject({ method: "GET", url: "/readyz" });
  await app.close();

  expect(res.statusCode).toBe(503);
  expect(res.json()).toEqual({ status: "not_ready", checks: { db: "error" } });
});

test("readyz is 200 after migration", async () => {
  const dbPath = join(dir, "migrated.sqlite");
  applyPending(dbPath); // create the schema
  const app = buildApp({ config: makeConfig(dbPath), logSink: discardSink });
  const res = await app.inject({ method: "GET", url: "/readyz" });
  await app.close();

  expect(res.statusCode).toBe(200);
  expect(res.json()).toEqual({ status: "ready", checks: { db: "ok" } });
});

test("readyz is 503 for a migrated but READ-ONLY DB", async () => {
  // The write probe catches a read-only DB that a name/column check would pass.
  const roDir = join(dir, "ro");
  mkdirSync(roDir);
  const dbPath = join(roDir, "ro.sqlite");
  applyPending(dbPath); // fully migrated first

  chmodSync(dbPath, 0o444); // read-only file
  chmodSync(roDir, 0o555); // read-only dir (no journal can be created)
  try {
    const app = buildApp({ config: makeConfig(dbPath), logSink: discardSink });
    const res = await app.inject({ method: "GET", url: "/readyz" });
    await app.close();
    expect(res.statusCode).toBe(503);
    expect(res.json()).toEqual({ status: "not_ready", checks: { db: "error" } });
  } finally {
    chmodSync(roDir, 0o755); // restore so afterAll cleanup can remove it
    chmodSync(dbPath, 0o644);
  }
});

test("readyz is 503 while the datastore is unavailable; healthz stays 200", async () => {
  const app = buildApp({
    config: makeConfig("/no_such_dir_07b_ts/x.sqlite"),
    logSink: discardSink,
  });
  const ready = await app.inject({ method: "GET", url: "/readyz" });
  const live = await app.inject({ method: "GET", url: "/healthz" });
  await app.close();

  expect(ready.statusCode).toBe(503);
  expect(ready.json()).toEqual({ status: "not_ready", checks: { db: "error" } });
  // Liveness must stay independent of the failing dependency.
  expect(live.statusCode).toBe(200);
});

test("readyz toggles with migration: same code, migrating flips it to ready", async () => {
  const dbPath = join(dir, "toggle.sqlite");
  const app = buildApp({ config: makeConfig(dbPath), logSink: discardSink });
  const before = await app.inject({ method: "GET", url: "/readyz" });
  expect(before.statusCode).toBe(503); // unmigrated

  applyPending(dbPath);
  const after = await app.inject({ method: "GET", url: "/readyz" });
  await app.close();
  expect(after.statusCode).toBe(200); // migrated
});

test("readyz reflects the default relative data dir (the container default)", async () => {
  // Reproduce the container's default: the RELATIVE dbPath resolved against the
  // working directory. Without a "data/" dir the datastore cannot open -> 503;
  // once the dir exists AND migrations run -> 200.
  const cwd = process.cwd();
  const sandbox = mkdtempSync(join(tmpdir(), "m07b-ts-realdir-"));
  try {
    process.chdir(sandbox);
    const missing = buildApp({
      config: makeConfig("data/07b-service.sqlite"),
      logSink: discardSink,
    });
    const before = await missing.inject({ method: "GET", url: "/readyz" });
    await missing.close();
    expect(before.statusCode).toBe(503);

    mkdirSync(join(sandbox, "data"));
    applyPending("data/07b-service.sqlite");
    const ready = buildApp({
      config: makeConfig("data/07b-service.sqlite"),
      logSink: discardSink,
    });
    const after = await ready.inject({ method: "GET", url: "/readyz" });
    await ready.close();
    expect(after.statusCode).toBe(200);
  } finally {
    process.chdir(cwd);
    rmSync(sandbox, { recursive: true, force: true });
  }
});

test("readyz does not block the event loop when a write lock is held", async () => {
  // The readiness probe is non-blocking (busy_timeout=0): with a held write lock
  // it returns 503 FAST instead of stalling the single-threaded event loop for
  // ~5 s (which, with node:sqlite's synchronous API, would otherwise deadlock).
  const dbPath = join(dir, "block.sqlite");
  applyPending(dbPath);
  const holder = openDb(dbPath);
  holder.exec("BEGIN IMMEDIATE"); // hold the write lock
  try {
    const app = buildApp({ config: makeConfig(dbPath), logSink: discardSink });
    const start = Date.now();
    const res = await app.inject({ method: "GET", url: "/readyz" });
    const elapsed = Date.now() - start;
    await app.close();

    expect(res.statusCode).toBe(503); // write probe cannot get the lock
    expect(elapsed).toBeLessThan(2000); // fast — did not block on the busy timeout
  } finally {
    holder.exec("ROLLBACK");
    holder.close();
  }
});
