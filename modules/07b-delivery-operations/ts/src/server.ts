/**
 * Production entrypoint.  Run with:  pnpm --filter @learn-ai/m07b-service start
 *
 * A JSON logger + credential scrubber are installed BEFORE any config/provider
 * init, so a startup failure is logged sanitised (never a raw stack, which could
 * contain a credential, to stderr) and the process exits non-zero before binding
 * a port. Fails fast on a missing/invalid config variable AND on a missing
 * provider credential (the eager provider build inside `bootstrap`).
 */

import { bootstrap } from "./app.js";
import { type Config, loadConfig, PROVIDER_CREDENTIAL_ENV_VARS } from "./config.js";
import { indexDocument, JobWorker } from "./jobs.js";
import { createLogger } from "./logging.js";
import { applyPending } from "./migrations.js";

async function main(): Promise<void> {
  // Redacting logger first: register provider creds so any startup error that
  // mentions one is scrubbed before it is written.
  const logger = createLogger();
  for (const name of PROVIDER_CREDENTIAL_ENV_VARS)
    logger.registerSecret(process.env[name]);

  let config: Config;
  try {
    config = loadConfig();
    logger.registerSecret(config.providerApiKey);
  } catch (err) {
    logger.error("startup_failed", {
      error: err instanceof Error ? err.message : String(err),
    });
    // Set the code and return (rather than process.exit) so the buffered log is
    // flushed before the process exits with a non-zero status.
    process.exitCode = 1;
    return;
  }

  try {
    // Apply pending schema migrations at startup so /readyz reflects a real,
    // migrated database. Idempotent — a no-op when already up to date.
    const applied = applyPending(config.dbPath, config.migrationsDir);
    logger.info("migrations_applied", { versions: applied });
    // Eager provider build → a missing credential crashes here, not on /ask.
    const app = await bootstrap({ config });
    // Start the durable-ingestion worker HERE (the production path only) — not in
    // buildApp, so request tests stay deterministic and timer-free and drive
    // drain() themselves. Stop it on close so no poll timer leaks.
    const worker = new JobWorker(config.dbPath, indexDocument(config.dbPath));
    worker.start();
    app.addHook("onClose", async () => worker.stop());
    await app.listen({ host: "0.0.0.0", port: config.port });
  } catch (err) {
    logger.error("startup_failed", {
      error: err instanceof Error ? err.message : String(err),
    });
    process.exitCode = 1;
  }
}

void main();
