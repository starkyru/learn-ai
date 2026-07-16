/**
 * Helper CLI for the concurrency (TOCTOU) test — NOT a test file itself.
 * Runs the real `applyPending` in a separate process and prints the applied
 * versions as JSON, so the test can launch two of these at once.
 *
 * Usage: tsx test/_apply_cli.ts <dbPath> [migrationsDir]
 */

import { applyPending } from "../src/migrations.js";

const [dbPath, migrationsDir] = process.argv.slice(2);
if (!dbPath) {
  process.stderr.write("usage: _apply_cli.ts <dbPath> [migrationsDir]\n");
  process.exit(2);
}
const applied = applyPending(dbPath, migrationsDir || undefined);
process.stdout.write(JSON.stringify(applied));
