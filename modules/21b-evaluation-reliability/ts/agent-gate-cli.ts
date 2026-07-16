/**
 * agent-gate-cli.ts — CLI entry for the agent-safety release gate.
 *
 * Resolves the fixtures dir, loads the policy, runs the gate, writes
 * agent_gate_report.json, and EXITS NONZERO on any policy-violating trajectory.
 * Offline and deterministic.
 *
 *   pnpm tsx modules/21b-evaluation-reliability/ts/agent-gate-cli.ts
 *   pnpm tsx modules/21b-evaluation-reliability/ts/agent-gate-cli.ts --policy <path> --out <dir>
 */

import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { type AgentGatePolicy, runGate } from "./agent-gate.js";

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
  const policy: AgentGatePolicy = args.policy
    ? (JSON.parse(readFileSync(args.policy, "utf-8")) as AgentGatePolicy)
    : (JSON.parse(
        readFileSync(join(fixturesDir, "agent_gate_policy.json"), "utf-8"),
      ) as AgentGatePolicy);
  const outDir = args.out ?? mkdtempSync(join(tmpdir(), "m21b-agent-gate-"));

  let outcome;
  try {
    outcome = runGate(fixturesDir, policy, outDir);
  } catch (error) {
    process.stdout.write(`agent gate: FAIL  (rejected: ${(error as Error).message})\n`);
    process.exit(1);
  }

  process.stdout.write(`agent gate: ${outcome.ok ? "PASS" : "FAIL"}\n`);
  for (const violation of outcome.violations) {
    process.stdout.write(`  - violation: ${violation}\n`);
  }
  process.stdout.write(
    `agent_gate_report written to: ${join(outDir, "agent_gate_report.json")}\n`,
  );
  process.exit(outcome.ok ? 0 : 1);
}

main();
