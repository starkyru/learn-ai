/**
 * gate.test.ts — the enforceable release gate (exit-code behavior is the crux).
 * Mirrors test_gate.py, including an adversarial false-green test per finding.
 */

import { spawnSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { loadJson, makeFakeJudge, promptHash } from "./answer-eval.js";
import { serializeCanonical } from "./benchmark.js";
import {
  buildReleaseReport,
  evaluatePolicy,
  releaseEvidence,
  type ReleasePolicy,
  runGate,
} from "./gate.js";

const FX = join(__dirname, "..", "fixtures");
const GATE_CLI = join(__dirname, "gate-cli.ts");

function policy(): ReleasePolicy {
  return structuredClone(loadJson<ReleasePolicy>(FX, "release_policy.json"));
}

/** Floor/config/verdict violations for a crafted policy (bypasses the policy
 * binding, which is tested separately). */
function violationsOf(p: ReleasePolicy): string[] {
  return evaluatePolicy(p, releaseEvidence(FX, p) as Record<string, unknown>);
}

/** Copy the fixtures to a fresh temp dir so mutation tests never touch the
 * shared fixtures (jest runs test files in parallel workers). */
function copyFixtures(): string {
  const dir = mkdtempSync(join(tmpdir(), "m21b-fx-"));
  cpSync(FX, dir, { recursive: true });
  return dir;
}

function promptHashFor(
  fx: string,
  variant: string,
  cid: string,
  answerText: string,
): string {
  const cases = loadJson<{ cases: Array<{ id: string; query: string }> }>(
    fx,
    "cases_heldout.json",
  );
  const query = new Map(cases.cases.map((c) => [c.id, c.query])).get(cid) ?? "";
  const user = makeFakeJudge(fx).buildMessages(variant, cid, query, answerText)[1]
    .content;
  return promptHash(user);
}

// --- Baseline ----------------------------------------------------------------

test("passes on the real policy", () => {
  const outcome = buildReleaseReport(FX, policy());
  expect(outcome.ok).toBe(true);
  expect(outcome.violations).toEqual([]);
  expect((outcome.report.comparison as { verdict: string }).verdict).toBe(
    "inconclusive",
  );
});

test("release evidence byte-matches the golden (comparison CI + kappa pinned)", () => {
  const outcome = buildReleaseReport(FX, policy());
  const evidence = { ...outcome.report } as Record<string, unknown>;
  delete evidence.golden_drift;
  delete evidence.gate;
  const golden = readFileSync(join(FX, "golden", "release_report.golden"), "utf-8");
  expect(serializeCanonical(evidence)).toBe(golden);
});

// --- [high] no-op / malformed policy rejected --------------------------------

test("rejects a no-op policy (baseline == candidate)", () => {
  const p = policy();
  p.comparison.baseline = "variant_b";
  p.comparison.candidate = "variant_b";
  p.comparison.practical_threshold = 0;
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

test("rejects an out-of-range floor", () => {
  const p = policy();
  p.answer_floors.groundedness = 1.5;
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

test("rejects a bad bootstrap alpha", () => {
  const p = policy();
  p.bootstrap.alpha = 1.0;
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

// --- [high] retrieval selectors pinned (held-out + quality metric) -----------

test("rejects the dev (tuning) split", () => {
  const p = policy();
  p.retrieval_floor.split = "dev";
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

test("rejects a report-metadata metric (num_cases)", () => {
  const p = policy();
  p.retrieval_floor.metric = "num_cases";
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

test("rejects an unknown retrieval method", () => {
  const p = policy();
  p.retrieval_floor.method = "bogus";
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

// --- [high] golden-drift enforcement cannot be disabled by policy ------------

test("enforces drift even when the opt-out is requested", () => {
  const fx = copyFixtures();
  const golden = join(fx, "golden", "report_heldout_k5.golden");
  writeFileSync(golden, `${readFileSync(golden, "utf-8")}  \n`, "utf-8");
  const p = policy();
  p.check_golden_drift = false; // ignored: drift is mandatory
  const outcome = buildReleaseReport(fx, p);
  expect(outcome.ok).toBe(false);
  expect(outcome.violations.some((v) => v.includes("drifted"))).toBe(true);
});

// --- [high] candidate / config mismatch --------------------------------------

test("fails on candidate/floor-variant mismatch", () => {
  const p = policy();
  p.comparison.baseline = "variant_b";
  p.comparison.candidate = "variant_a";
  p.answer_floors = {
    variant: "variant_b",
    groundedness: 0,
    citation_validity: 0,
    completeness: 0,
    task_success: 0,
  };
  expect(violationsOf(p).some((v) => v.includes("!= comparison.candidate"))).toBe(true);
});

// --- [high] independent floors ----------------------------------------------

test("fails when citation_validity is below floor though groundedness passes", () => {
  const p = policy();
  p.comparison.baseline = "variant_b";
  p.comparison.candidate = "variant_a";
  p.answer_floors = {
    variant: "variant_a",
    groundedness: 0.5,
    citation_validity: 0.9,
    completeness: 0.5,
    task_success: 0.5,
  };
  const v = violationsOf(p);
  expect(v.some((x) => x.includes("citation_validity"))).toBe(true);
  expect(v.some((x) => x.includes("groundedness"))).toBe(false);
});

test("fails when task_success is below floor", () => {
  const p = policy();
  p.comparison.baseline = "variant_b";
  p.comparison.candidate = "variant_a";
  p.answer_floors = {
    variant: "variant_a",
    groundedness: 0.5,
    citation_validity: 0.5,
    completeness: 0.5,
    task_success: 0.9,
  };
  expect(violationsOf(p).some((x) => x.includes("task_success"))).toBe(true);
});

// --- [high] judge verdict bound to the evaluated answer content --------------

test("rejects a tampered answer with a smuggled canned entry", () => {
  const fx = copyFixtures();
  const answersPath = join(fx, "answers.json");
  const judgePath = join(fx, "judge.json");
  const data = JSON.parse(readFileSync(answersPath, "utf-8"));
  const newText = "smuggled tampered candidate answer";
  data.variants.variant_b["hold-13"].answer_text = newText;
  writeFileSync(answersPath, JSON.stringify(data), "utf-8");
  const jd = JSON.parse(readFileSync(judgePath, "utf-8"));
  jd.canned[promptHashFor(fx, "variant_b", "hold-13", newText)] = 1; // add, keep old
  writeFileSync(judgePath, JSON.stringify(jd), "utf-8");
  // Exact-coverage validation: the old hold-13 hash is now an EXTRA canned key.
  expect(() => buildReleaseReport(fx, policy())).toThrow();
});

test("fails on a consistently tampered answer via golden drift", () => {
  const fx = copyFixtures();
  const answersPath = join(fx, "answers.json");
  const judgePath = join(fx, "judge.json");
  const data = JSON.parse(readFileSync(answersPath, "utf-8"));
  const oldText = data.variants.variant_b["hold-13"].answer_text;
  const newText = "consistently tampered candidate answer";
  data.variants.variant_b["hold-13"].answer_text = newText;
  writeFileSync(answersPath, JSON.stringify(data), "utf-8");
  const jd = JSON.parse(readFileSync(judgePath, "utf-8"));
  const oldHash = promptHashFor(fx, "variant_b", "hold-13", oldText);
  delete jd.canned[oldHash];
  jd.canned[promptHashFor(fx, "variant_b", "hold-13", newText)] = 1; // consistent replace
  writeFileSync(judgePath, JSON.stringify(jd), "utf-8");
  const outcome = buildReleaseReport(fx, policy());
  expect(outcome.ok).toBe(false);
  expect(outcome.violations.some((v) => v.includes("answer report drifted"))).toBe(
    true,
  );
});

// --- [high] runtime golden drift over ALL committed artifacts ---------------

test.each([
  ["report_heldout_k5.golden", "retrieval report drifted"],
  ["answer_report_variant_b.golden", "answer report drifted"],
  ["release_report.golden", "release evidence drifted"],
])("fails on %s corruption at runtime", (file, needle) => {
  const fx = copyFixtures();
  const golden = join(fx, "golden", file);
  writeFileSync(golden, `${readFileSync(golden, "utf-8")}  \n`, "utf-8");
  const outcome = buildReleaseReport(fx, policy());
  expect(outcome.ok).toBe(false);
  expect(outcome.violations.some((v) => v.includes(needle))).toBe(true);
});

// --- [high] answer-fixture provenance validated before evaluation -----------

test("fails on a dropped answer case", () => {
  const fx = copyFixtures();
  const answersPath = join(fx, "answers.json");
  const data = JSON.parse(readFileSync(answersPath, "utf-8"));
  delete data.variants.variant_b["hold-22"];
  writeFileSync(answersPath, JSON.stringify(data), "utf-8");
  expect(() => buildReleaseReport(fx, policy())).toThrow();
});

test("fails on a duplicated answer case", () => {
  const fx = copyFixtures();
  const answersPath = join(fx, "answers.json");
  const data = JSON.parse(readFileSync(answersPath, "utf-8"));
  data.cases.push("hold-01");
  writeFileSync(answersPath, JSON.stringify(data), "utf-8");
  expect(() => buildReleaseReport(fx, policy())).toThrow();
});

// --- floor / improvement logic (via evaluatePolicy) -------------------------

test("fails when the retrieval floor is breached", () => {
  const p = policy();
  p.retrieval_floor.floor = 0.99;
  expect(violationsOf(p).some((v) => v.includes("retrieval floor breached"))).toBe(
    true,
  );
});

test("fails when improvement is required but the comparison is inconclusive", () => {
  const p = policy();
  p.comparison.require_improvement = true;
  expect(violationsOf(p).some((v) => v.includes("improvement required"))).toBe(true);
});

// --- [high] runtime policy bound to the committed contract -------------------

test("rejects an unpinned candidate (variant_c has no committed golden)", () => {
  const p = policy();
  p.comparison.candidate = "variant_c";
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

test("rejects a runtime floor change (differs from committed contract)", () => {
  const p = policy();
  p.retrieval_floor.floor = 0.5;
  expect(() => buildReleaseReport(FX, p)).toThrow();
});

// --- [high] bootstrap seed validated ----------------------------------------

test.each([["not-a-seed"], [3.5], [-1], [0x100000000]])(
  "rejects a bad bootstrap seed %p",
  (badSeed) => {
    const p = policy();
    (p.bootstrap as { seed: unknown }).seed = badSeed;
    expect(() => buildReleaseReport(FX, p)).toThrow();
  },
);

test("CLI exits 0 on pass", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-gate-ts-"));
  const proc = spawnSync("pnpm", ["exec", "tsx", GATE_CLI, "--out", out], {
    encoding: "utf-8",
  });
  expect(proc.status).toBe(0);
}, 60000);

test("CLI exits nonzero on a breached floor", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-gate-ts-"));
  const p = policy();
  p.retrieval_floor.floor = 0.99;
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

test("CLI exits nonzero on a no-op policy", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-gate-ts-"));
  const p = policy();
  p.comparison.baseline = "variant_b";
  p.comparison.candidate = "variant_b";
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
  expect(proc.stdout).toContain("rejected");
}, 60000);

test.each([["not-a-seed"], [3.5], [0x100000000]])(
  "CLI exits nonzero on a bad seed %p",
  (badSeed) => {
    const out = mkdtempSync(join(tmpdir(), "m21b-gate-ts-"));
    const p = policy();
    (p.bootstrap as { seed: unknown }).seed = badSeed;
    const policyPath = join(out, "policy.json");
    writeFileSync(policyPath, JSON.stringify(p), "utf-8");
    const proc = spawnSync(
      "pnpm",
      ["exec", "tsx", GATE_CLI, "--policy", policyPath, "--out", out],
      { encoding: "utf-8" },
    );
    expect(proc.status).not.toBe(0);
  },
  60000,
);

test("runGate writes release_report.json", () => {
  const out = mkdtempSync(join(tmpdir(), "m21b-gate-ts-"));
  runGate(FX, policy(), out);
  expect(readFileSync(join(out, "release_report.json"), "utf-8")).toContain(
    '"verdict"',
  );
});
