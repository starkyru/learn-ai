/**
 * agent-gate.ts — deterministic agent-safety release gate: pure core (Task 4).
 * Port of agent_gate.py; the gate evidence is byte-identical to the Python one.
 *
 * No `import.meta` here, so it loads under jest and tsx; `agent-gate-cli.ts`
 * resolves the fixtures dir and exits with the right code.
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import {
  buildAgentReport,
  evaluateTrajectory,
  loadScenarios,
  scenarioIds,
} from "./agent-eval.js";
import { serializeCanonical } from "./benchmark.js";

export interface AgentGatePolicy {
  candidate_scenarios: string[];
  task_success_floor: number;
}

export interface GateOutcome {
  ok: boolean;
  violations: string[];
  report: Record<string, unknown>;
}

export function validateGatePolicy(fixturesDir: string, policy: AgentGatePolicy): void {
  const known = new Set(scenarioIds(fixturesDir));
  const candidates = policy.candidate_scenarios;
  if (!Array.isArray(candidates) || candidates.length === 0) {
    throw new Error("candidate_scenarios must be a non-empty list");
  }
  if (new Set(candidates).size !== candidates.length) {
    throw new Error("candidate_scenarios has duplicates");
  }
  const unknown = candidates.filter((c) => !known.has(c));
  if (unknown.length > 0) {
    throw new Error(
      `candidate_scenarios references unknown scenarios: ${unknown.join(", ")}`,
    );
  }
  const floor = policy.task_success_floor;
  if (typeof floor !== "number" || !Number.isFinite(floor) || floor < 0 || floor > 1) {
    throw new Error("task_success_floor must be a number in [0, 1]");
  }
}

export function gateEvidence(
  fixturesDir: string,
  policy: AgentGatePolicy,
): Record<string, unknown> {
  const scenarios = loadScenarios(fixturesDir).scenarios;
  const candidates = [...policy.candidate_scenarios].sort();
  const perScenario: Record<string, unknown> = {};
  for (const sid of candidates) {
    const r = evaluateTrajectory(sid, scenarios[sid]);
    perScenario[sid] = {
      task_success: r.task_success,
      policy_compliant: r.policy_compliant,
      tool_argument_accuracy: r.tool_argument_accuracy,
      step_count: r.step_count,
      latency: r.latency,
      cost: r.cost,
      violation_types: [...new Set(r.violations.map((v) => v.type))].sort(),
    };
  }
  const n = candidates.length || 1;
  const get = (sid: string) => perScenario[sid] as Record<string, number>;
  const metrics = {
    task_success_rate:
      candidates.reduce((a, s) => a + Number(get(s).task_success), 0) / n,
    policy_compliance_rate:
      candidates.reduce((a, s) => a + Number(get(s).policy_compliant), 0) / n,
    total_cost: candidates.reduce((a, s) => a + get(s).cost, 0),
    total_latency: candidates.reduce((a, s) => a + get(s).latency, 0),
    total_steps: candidates.reduce((a, s) => a + get(s).step_count, 0),
  };
  return { candidates: perScenario, metrics };
}

export function evaluateGate(
  policy: AgentGatePolicy,
  evidence: Record<string, unknown>,
): string[] {
  // The policy-compliance check is UNCONDITIONAL: a policy-violating candidate
  // ALWAYS fails the gate (it cannot be disabled by policy).
  const violations: string[] = [];
  const candidates = [...policy.candidate_scenarios].sort();
  const perScenario = evidence.candidates as Record<
    string,
    { policy_compliant: boolean; violation_types: string[] }
  >;
  for (const sid of candidates) {
    const entry = perScenario[sid];
    if (!entry.policy_compliant) {
      violations.push(
        `${sid}: policy violation ${JSON.stringify(entry.violation_types)}`,
      );
    }
  }
  const metrics = evidence.metrics as { task_success_rate: number };
  if (metrics.task_success_rate < policy.task_success_floor) {
    violations.push(
      `task_success_rate ${metrics.task_success_rate.toFixed(4)} < floor ${policy.task_success_floor}`,
    );
  }
  return violations;
}

function checkDrift(fixturesDir: string): {
  goldenDrift: { checked: boolean; drifted: boolean };
  violations: string[];
} {
  const golden = join(fixturesDir, "golden", "agent_report.golden");
  const drifted =
    serializeCanonical(buildAgentReport(fixturesDir)) !== readFileSync(golden, "utf-8");
  return {
    goldenDrift: { checked: true, drifted },
    violations: drifted ? ["agent report drifted from agent_report.golden"] : [],
  };
}

export function buildGateReport(
  fixturesDir: string,
  policy: AgentGatePolicy,
): GateOutcome {
  validateGatePolicy(fixturesDir, policy);
  const evidence = gateEvidence(fixturesDir, policy);
  const violations = evaluateGate(policy, evidence);
  const drift = checkDrift(fixturesDir);
  violations.push(...drift.violations);
  const report: Record<string, unknown> = {
    ...evidence,
    golden_drift: drift.goldenDrift,
    gate: { ok: violations.length === 0, violations },
  };
  return { ok: violations.length === 0, violations, report };
}

export function runGate(
  fixturesDir: string,
  policy: AgentGatePolicy,
  outDir?: string,
): GateOutcome {
  const outcome = buildGateReport(fixturesDir, policy);
  if (outDir !== undefined) {
    mkdirSync(outDir, { recursive: true });
    writeFileSync(
      join(outDir, "agent_gate_report.json"),
      serializeCanonical(outcome.report),
      "utf-8",
    );
  }
  return outcome;
}
