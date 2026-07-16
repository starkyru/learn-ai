/**
 * Helper CLI for the lock-retry test — NOT a test file itself.
 * Acquires the migration write lock, signals readiness by creating a file, holds
 * the lock for the given duration, then releases. Lets a test start a runner that
 * must RETRY while this process holds the lock.
 *
 * Usage: tsx test/_hold_lock_cli.ts <dbPath> <holdMs> <readyFile>
 */

import { writeFileSync } from "node:fs";

import { openDb } from "../src/db.js";

const [dbPath, holdMsRaw, readyFile] = process.argv.slice(2);
if (!dbPath || !holdMsRaw || !readyFile) {
  process.stderr.write("usage: _hold_lock_cli.ts <dbPath> <holdMs> <readyFile>\n");
  process.exit(2);
}

const db = openDb(dbPath);
db.exec("BEGIN IMMEDIATE"); // take the write lock
writeFileSync(readyFile, "ready"); // signal that the lock is held
// Block synchronously for holdMs, then release.
Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, Number(holdMsRaw));
db.exec("ROLLBACK");
db.close();
