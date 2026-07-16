/**
 * gate-cli.ts — CLI entry for the release gate.
 *
 * Resolves the fixtures dir, loads the policy, runs the gate, writes
 * release_report.json, and EXITS NONZERO on a policy violation. Offline and
 * deterministic.
 *
 *   pnpm tsx modules/21b-evaluation-reliability/ts/gate-cli.ts
 *   pnpm tsx modules/21b-evaluation-reliability/ts/gate-cli.ts --policy <path> --out <dir>
 */

import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { loadJson } from "./answer-eval.js";
import { type ReleasePolicy, runGate } from "./gate.js";

function parseArgs(argv: readonly string[]): { policy?: string; out?: string } {
  const args: { policy?: string; out?: string } = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--policy") args.policy = argv[(i += 1)];
    else if (argv[i] === "--out") args.out = argv[(i += 1)];
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return args;
}

function main(): void {
  const fixturesDir = join(dirname(fileURLToPath(import.meta.url)), "..", "fixtures");
  const args = parseArgs(process.argv.slice(2));
  const policy: ReleasePolicy = args.policy
    ? (JSON.parse(readFileSync(args.policy, "utf-8")) as ReleasePolicy)
    : loadJson<ReleasePolicy>(fixturesDir, "release_policy.json");
  const outDir = args.out ?? mkdtempSync(join(tmpdir(), "m21b-gate-"));
  let outcome;
  try {
    outcome = runGate(fixturesDir, policy, outDir);
  } catch (error) {
    // Malformed policy or fixture -> the gate rejects the release.
    process.stdout.write(
      `release gate: FAIL  (rejected: ${(error as Error).message})\n`,
    );
    process.exit(1);
  }

  const verdict = (outcome.report.comparison as { verdict: string }).verdict;
  process.stdout.write(
    `release gate: ${outcome.ok ? "PASS" : "FAIL"}  (comparison verdict: ${verdict})\n`,
  );
  for (const violation of outcome.violations) {
    process.stdout.write(`  - violation: ${violation}\n`);
  }
  process.stdout.write(
    `release_report written to: ${join(outDir, "release_report.json")}\n`,
  );
  process.exit(outcome.ok ? 0 : 1);
}

main();
