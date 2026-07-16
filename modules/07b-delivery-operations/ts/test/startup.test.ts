/** Real-entrypoint startup test: fail fast when a provider credential is missing.
 *
 * Runs the actual `server.ts` entrypoint in a subprocess with a real provider
 * selected and its key UNSET. A missing key must fail BEFORE any network call,
 * so the process exits non-zero quickly, binds no port, and logs the failure via
 * the redacting logger (not a raw uncaught crash).
 */

import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

test("entrypoint fails fast without a provider credential", () => {
  const dir = mkdtempSync(join(tmpdir(), "m07b-ts-startup-"));
  const tsDir = join(__dirname, ".."); // the @learn-ai/m07b-service package dir

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    SERVICE_ENV: "development",
    LLM_PROVIDER: "openai", // requires OPENAI_API_KEY
    PORT: "8198",
    DB_PATH: join(dir, "db.sqlite"),
  };
  delete env.OPENAI_API_KEY; // the missing credential

  const res = spawnSync("pnpm", ["exec", "tsx", "src/server.ts"], {
    cwd: tsDir,
    env,
    encoding: "utf8",
    timeout: 60_000,
  });
  rmSync(dir, { recursive: true, force: true });

  // Fails fast (nonzero) — it never bound a port.
  expect(res.status).not.toBe(0);
  // The failure was handled by our redacting logger, not an uncaught crash.
  expect(res.stdout).toContain("startup_failed");
}, 60_000);
