/**
 * Data-subject rights demo (Module 20b, Task 2).
 *
 * Seeds one synthetic subject across every store, then: EXPORTS a manifest of
 * all copies -> ERASES (hard-delete where allowed, tombstone where a retention
 * exception applies, with a reviewer) -> exports again to show what remains ->
 * PURGES a past-retention record. Every action is structured-logged.
 * Deterministic and offline.
 *
 * Run it:
 *   pnpm tsx modules/20b-governance-privacy/ts/rights-demo.ts
 *
 * Not legal advice — see the module README.
 */

import {
  buildDefaultEngine,
  RightsEngine,
  seedSyntheticSubject,
  STORE_HUMAN_REVIEW,
} from "./rights.js";

const SUBJECT = "subj_0007";
const ACTOR = "privacy-service";
const REVIEWER = "legal-team";

function printManifest(engine: RightsEngine, label: string): void {
  const manifest = engine.export(SUBJECT, { actor: ACTOR });
  console.log(`\n${label} — ${manifest.copies.length} copies:`);
  const sorted = [...manifest.copies].sort((a, b) =>
    `${a.store}${a.recordId}`.localeCompare(`${b.store}${b.recordId}`),
  );
  for (const copy of sorted) {
    const flag = copy.tombstoned ? " (TOMBSTONE)" : "";
    console.log(
      `  ${copy.store.padEnd(13)} ${copy.location.padEnd(28)} ${copy.recordId}${flag}`,
    );
  }
}

function main(): void {
  const engine = buildDefaultEngine({
    sink: (entry) => console.log(JSON.stringify(entry)),
  });
  seedSyntheticSubject(engine, SUBJECT, { createdAt: 0 });

  printManifest(engine, "EXPORT (before erasure)");

  const report = engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });
  console.log("\nERASE outcomes:");
  for (const outcome of report.outcomes) {
    const rev = outcome.reviewer ? ` reviewer=${outcome.reviewer}` : "";
    console.log(
      `  ${outcome.store.padEnd(13)} ${outcome.result.padEnd(13)} x${outcome.count}${rev}`,
    );
  }

  printManifest(engine, "EXPORT (after erasure)");
  console.log(
    "  ^ hard-delete stores are gone; " +
      STORE_HUMAN_REVIEW +
      " keeps a TOMBSTONE under a documented retention exception — id + reason, " +
      "no raw content.",
  );

  const purged = engine.purgeExpired(1_000_000, { actor: ACTOR });
  console.log(`\nPURGE (retention expiry) at now=1_000_000: ${JSON.stringify(purged)}`);

  console.log(`\nAudit log holds ${engine.auditLog.length} records.`);
}

const invokedPath = process.argv[1] ?? "";
if (invokedPath.endsWith("rights-demo.ts") || invokedPath.endsWith("rights-demo.js")) {
  main();
}
