/**
 * agent-gate.test.ts — the agent-safety release gate (exit code is the crux).
 * Mirrors test_agent_gate.py.
 */

import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { serializeCanonical } from "./benchmark.js";
import {
  type AgentGatePolicy,
  buildGateReport,
  evaluateGate,
  gateEvidence,
  runGate,
} from "./agent-gate.js";

const FX = join(__dirname, "..", "fixtures");
const GATE_CLI = join(__dirname, "agent-gate-cli.ts");

function policy(): AgentGatePolicy {
  return JSON.parse(
    readFileSync(join(FX, "agent_gate_policy.json"), "utf-8"),
  ) as AgentGatePolicy;
}

function copyFixtures(): string {
  const dir = mkdtempSync(join(tmpdir(), "m21b-agent-fx-"));
  cpSync(FX, dir, { recursive: true });
  return dir;
}

test("passes on clean candidates", () => {
  const outcome = buildGateReport(FX, policy());
  expect(outcome.ok).toBe(true);
  expect(outcome.violations).toEqual([]);
});

test("gate evidence byte-matches golden", () => {
  const golden = readFileSync(join(FX, "golden", "agent_gate_report.golden"), "utf-8");
  expect(serializeCanonical(gateEvidence(FX, policy()))).toBe(golden);
});

test("fails on an unauthorised side effect despite a correct answer", () => {
  const p = policy();
  p.candidate_scenarios = ["unauthorised_side_effect"];
  const evidence = gateEvidence(FX, p);
  const violations = evaluateGate(p, evidence);
  expect((evidence.metrics as { task_success_rate: number }).task_success_rate).toBe(
    1.0,
  );
  expect(violations.length).toBeGreaterThan(0);
  expect(violations.some((v) => v.includes("unauthorised_tool"))).toBe(true);
});

test.each([["missing_approval"], ["exceeds_max_steps"], ["non_idempotent_duplicate"]])(
  "fails on the %s candidate",
  (scenario) => {
    const p = policy();
    p.candidate_scenarios = [scenario];
    expect(evaluateGate(p, gateEvidence(FX, p)).length).toBeGreaterThan(0);
  },
);

test("rejects an unknown scenario", () => {
  const p = policy();
  p.candidate_scenarios = ["does_not_exist"];
  expect(() => buildGateReport(FX, p)).toThrow();
});

test("rejects an out-of-range floor", () => {
  const p = policy();
  p.task_success_floor = 1.5;
  expect(() => buildGateReport(FX, p)).toThrow();
});

test("fails on agent report drift", () => {
  const fx = copyFixtures();
  const golden = join(fx, "golden", "agent_report.golden");
  writeFileSync(golden, `${readFileSync(golden, "utf-8")}  \n`, "utf-8");
  const outcome = buildGateReport(fx, policy());
  expect(outcome.ok).toBe(false);
  expect(outcome.violations.some((v) => v.includes("drifted"))).toBe(true);
});

test("CLI exits 0 on pass", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-agent-gate-ts-"));
  const proc = spawnSync("pnpm", ["exec", "tsx", GATE_CLI, "--out", out], {
    encoding: "utf-8",
  });
  expect(proc.status).toBe(0);
}, 60000);

test("CLI exits nonzero on an unsafe candidate", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-agent-gate-ts-"));
  const p = policy();
  p.candidate_scenarios = ["unauthorised_side_effect"];
  const policyPath = join(out, "policy.json");
  writeFileSync(policyPath, JSON.stringify(p), "utf-8");
  const proc = spawnSync(
    "pnpm",
    ["exec", "tsx", GATE_CLI, "--policy", policyPath, "--out", out],
    {
      encoding: "utf-8",
    },
  );
  expect(proc.status).not.toBe(0);
}, 60000);

test("runGate writes agent_gate_report.json", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-agent-gate-ts-"));
  runGate(FX, policy(), out);
  expect(readFileSync(join(out, "agent_gate_report.json"), "utf-8")).toContain(
    '"candidates"',
  );
});
