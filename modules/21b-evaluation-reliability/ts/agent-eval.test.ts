/**
 * agent-eval.test.ts — trajectory evaluator (exact, discriminating).
 * Mirrors test_agent_eval.py; the crux is the unauthorised-side-effect test.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  buildAgentReport,
  evaluateTrajectory,
  hasUnapprovedSideEffect,
  loadScenarios,
} from "./agent-eval.js";
import { serializeCanonical } from "./benchmark.js";

const FX = join(__dirname, "..", "fixtures");

function result(scenarioId: string) {
  return evaluateTrajectory(scenarioId, loadScenarios(FX).scenarios[scenarioId]);
}

test("correct trajectory is clean", () => {
  const r = result("correct");
  expect(r.task_success).toBe(true);
  expect(r.policy_compliant).toBe(true);
  expect(r.violations).toEqual([]);
  expect(r.effects.length).toBe(1);
  expect(r.tool_argument_accuracy).toBe(1.0);
});

test("unauthorised side effect fails despite a correct answer", () => {
  // LOAD-BEARING: correct answer, but an unauthorised email -> not compliant.
  const r = result("unauthorised_side_effect");
  expect(r.task_success).toBe(true); // the answer IS correct
  expect(r.policy_compliant).toBe(false);
  const types = new Set(r.violations.map((v) => v.type));
  expect(types.has("unauthorised_tool")).toBe(true);
  expect(types.has("final_state_mismatch")).toBe(true);
  expect(hasUnapprovedSideEffect(r)).toBe(true);
});

test("missing approval is a violation (email still sent)", () => {
  const r = result("missing_approval");
  expect(r.policy_compliant).toBe(false);
  expect(r.violations.some((v) => v.type === "missing_approval")).toBe(true);
  expect(r.effects.length).toBe(1);
});

test("wrong arguments lower accuracy and flag a violation", () => {
  const r = result("wrong_arguments");
  expect(r.policy_compliant).toBe(false);
  expect(r.violations.some((v) => v.type === "wrong_arguments")).toBe(true);
  expect(r.tool_argument_accuracy).toBe(0.5);
});

test("exceeds max steps terminates bounded", () => {
  const r = result("exceeds_max_steps");
  expect(r.policy_compliant).toBe(false);
  expect(r.violations.some((v) => v.type === "exceeded_max_steps")).toBe(true);
  expect(r.step_count).toBe(2);
});

test("retry on transient failure is clean", () => {
  const r = result("retry_on_transient_failure");
  expect(r.task_success).toBe(true);
  expect(r.policy_compliant).toBe(true);
  expect(r.effects.length).toBe(1);
});

test("duplicate request is idempotent (one effect)", () => {
  const r = result("duplicate_request");
  expect(r.policy_compliant).toBe(true);
  expect(r.effects.length).toBe(1);
});

test("non-idempotent duplicate is caught", () => {
  const r = result("non_idempotent_duplicate");
  expect(r.policy_compliant).toBe(false);
  expect(r.effects.length).toBe(2);
  expect(r.violations.some((v) => v.type === "final_state_mismatch")).toBe(true);
});

test("timeout handled safely", () => {
  const r = result("timeout");
  expect(r.policy_compliant).toBe(true);
  expect(r.effects.length).toBe(0);
  expect(r.latency).toBe(5);
});

test("metrics reported separately", () => {
  const r = result("correct");
  for (const key of [
    "task_success",
    "policy_compliant",
    "tool_argument_accuracy",
    "step_count",
    "latency",
    "cost",
  ] as const) {
    expect(r[key]).toBeDefined();
  }
  expect(r.cost).toBe(3);
  expect(r.step_count).toBe(2);
});

test("agent report byte-matches golden", () => {
  const golden = readFileSync(join(FX, "golden", "agent_report.golden"), "utf-8");
  expect(serializeCanonical(buildAgentReport(FX))).toBe(golden);
});
