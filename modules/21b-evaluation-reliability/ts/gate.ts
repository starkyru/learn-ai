/**
 * gate.ts — enforceable offline release gate: pure core (Module 21b).
 * Port of gate.py; the release evidence is byte-identical to the Python one.
 *
 * No filesystem-locating `import.meta` here, so it loads cleanly under jest and
 * tsx. The CLI wrapper `gate-cli.ts` resolves the fixtures dir and exits with
 * the right code.
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { buildAgreementReport } from "./agreement.js";
import {
  evaluateVariant,
  loadJson,
  validateAnswerFixtures,
  type VariantReport,
  variantCaseScores,
} from "./answer-eval.js";
import {
  type BenchCase,
  buildReport,
  evaluateSplit,
  type MethodMetrics,
  type Report,
  type ReportManifest,
  serializeCanonical,
  serializeReport,
} from "./benchmark.js";
import {
  configFromManifest,
  type Chunk,
  type Manifest,
  type Method,
  METHODS,
  RetrievalIndex,
} from "./retrieval.js";
import { compareVariants } from "./uncertainty.js";

// Retrieval quality metrics a floor may gate on (NOT report metadata like
// num_cases / num_failures, which would pass a [0,1] floor without measuring
// retrieval quality).
const QUALITY_METRICS = new Set(["recall_at_k", "mrr", "ndcg_at_k"]);

export interface ReleasePolicy {
  retrieval_floor: {
    split: string;
    method: string;
    metric: string;
    k: number;
    floor: number;
  };
  answer_floors: {
    variant: string;
    groundedness: number;
    citation_validity: number;
    completeness: number;
    task_success: number;
  };
  comparison: {
    baseline: string;
    candidate: string;
    practical_threshold: number;
    require_improvement?: boolean;
  };
  bootstrap: { iterations: number; seed: number; alpha: number };
  /** Ignored: golden-drift enforcement is MANDATORY and cannot be disabled. */
  check_golden_drift?: boolean;
}

export interface GateOutcome {
  ok: boolean;
  violations: string[];
  report: Record<string, unknown>;
}

type ManifestFile = Manifest & ReportManifest & { relevant_threshold?: number };

// Policy floor key -> answer-report metric key.
const FLOOR_METRICS: Record<string, keyof VariantReport["metrics"]> = {
  groundedness: "groundedness",
  citation_validity: "citation_validity",
  completeness: "completeness",
  task_success: "task_success_rate",
};

function retrievalReport(fixturesDir: string, split: string, k: number): Report {
  const manifest = loadJson<ManifestFile>(fixturesDir, "manifest.json");
  const rubric = loadJson<{ relevant_threshold: number }>(fixturesDir, "rubrics.json");
  const corpus = loadJson<{ chunks: Chunk[] }>(fixturesDir, "corpus.json");
  const cases = loadJson<{ cases: BenchCase[] }>(
    fixturesDir,
    `cases_${split}.json`,
  ).cases;
  const index = new RetrievalIndex(corpus.chunks, configFromManifest(manifest));
  const result = evaluateSplit(index, cases, k, rubric.relevant_threshold);
  return buildReport(
    split,
    k,
    manifest,
    result,
    cases.length,
    rubric.relevant_threshold,
  );
}

function agreementReport(
  fixturesDir: string,
  variantReports: Record<string, VariantReport>,
): ReturnType<typeof buildAgreementReport> {
  const judge = loadJson<{ judge_model: string; prompt_version: string }>(
    fixturesDir,
    "judge.json",
  );
  const human = loadJson<{ labels: Record<string, Record<string, number>> }>(
    fixturesDir,
    "human_labels.json",
  ).labels;
  const variant = Object.keys(human)[0];
  const report = variantReports[variant] ?? evaluateVariant(fixturesDir, variant);
  const judgeLabels: Record<string, number> = {};
  for (const c of Object.keys(human[variant]))
    judgeLabels[c] = report.per_case[c].task_success;
  return buildAgreementReport(
    variant,
    judgeLabels,
    human[variant],
    judge.judge_model,
    judge.prompt_version,
  );
}

export function releaseEvidence(
  fixturesDir: string,
  policy: ReleasePolicy,
): Record<string, unknown> {
  const rf = policy.retrieval_floor;
  const report = retrievalReport(fixturesDir, rf.split, rf.k);
  const observedRetrieval =
    report.metrics[rf.method as Method][rf.metric as keyof MethodMetrics];

  const cp = policy.comparison;
  const bp = policy.bootstrap;
  const af = policy.answer_floors;
  const caseIds = loadJson<{ cases: string[] }>(fixturesDir, "answers.json").cases;
  const baselineReport = evaluateVariant(fixturesDir, cp.baseline);
  const candidateReport = evaluateVariant(fixturesDir, cp.candidate);

  const answerFloorResults: Record<
    string,
    { floor: number; observed: number; passed: boolean }
  > = {};
  for (const [floorKey, metricKey] of Object.entries(FLOOR_METRICS)) {
    const floor = af[floorKey as keyof typeof af] as number;
    const observed = candidateReport.metrics[metricKey];
    answerFloorResults[floorKey] = { floor, observed, passed: observed >= floor };
  }

  const comparison = compareVariants(
    variantCaseScores(baselineReport, caseIds),
    variantCaseScores(candidateReport, caseIds),
    cp.practical_threshold,
    bp.iterations,
    bp.seed,
    bp.alpha,
  );
  const agreement = agreementReport(fixturesDir, {
    [cp.baseline]: baselineReport,
    [cp.candidate]: candidateReport,
  });

  return {
    retrieval_floor: {
      split: rf.split,
      method: rf.method,
      metric: rf.metric,
      k: rf.k,
      floor: rf.floor,
      observed: observedRetrieval,
      passed: observedRetrieval >= rf.floor,
    },
    answer_floors: {
      variant: af.variant,
      candidate: cp.candidate,
      ...answerFloorResults,
    },
    comparison: {
      baseline: cp.baseline,
      candidate: cp.candidate,
      require_improvement: Boolean(cp.require_improvement),
      ...comparison,
    },
    agreement,
  };
}

function checkDrift(fixturesDir: string): {
  goldenDrift: { checked: boolean; drifted: boolean };
  violations: string[];
} {
  const committed = loadJson<ReleasePolicy>(fixturesDir, "release_policy.json");
  const violations: string[] = [];
  const goldenDir = join(fixturesDir, "golden");

  const rf = committed.retrieval_floor;
  const retrievalGolden = join(goldenDir, `report_${rf.split}_k${rf.k}.golden`);
  if (
    serializeReport(retrievalReport(fixturesDir, rf.split, rf.k)) !==
    readFileSync(retrievalGolden, "utf-8")
  ) {
    violations.push(`retrieval report drifted from report_${rf.split}_k${rf.k}.golden`);
  }

  const cp = committed.comparison;
  for (const variant of [...new Set([cp.baseline, cp.candidate])].sort()) {
    const goldenPath = join(goldenDir, `answer_report_${variant}.golden`);
    if (
      serializeCanonical(evaluateVariant(fixturesDir, variant)) !==
      readFileSync(goldenPath, "utf-8")
    ) {
      violations.push(`answer report drifted from answer_report_${variant}.golden`);
    }
  }

  const evidenceGolden = join(goldenDir, "release_report.golden");
  if (
    serializeCanonical(releaseEvidence(fixturesDir, committed)) !==
    readFileSync(evidenceGolden, "utf-8")
  ) {
    violations.push("release evidence drifted from release_report.golden");
  }

  return { goldenDrift: { checked: true, drifted: violations.length > 0 }, violations };
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** Reject a malformed/no-op policy (baseline == candidate, threshold 0, ...)
 * BEFORE evaluation, so it cannot yield a spurious "promote". */
export function validatePolicy(policy: ReleasePolicy): void {
  const cp = policy.comparison;
  if (cp.baseline === cp.candidate) {
    throw new Error("comparison.baseline and candidate must be distinct");
  }
  if (!isFiniteNumber(cp.practical_threshold) || cp.practical_threshold <= 0) {
    throw new Error("comparison.practical_threshold must be a finite number > 0");
  }

  // Retrieval selectors: gate on HELD-OUT data with a supported method and a
  // QUALITY metric (never the tuning split or report metadata).
  const rf = policy.retrieval_floor;
  if (rf.split !== "heldout") {
    throw new Error("retrieval_floor.split must be 'heldout' (not a tuning split)");
  }
  if (!Number.isInteger(rf.k) || rf.k <= 0) {
    throw new Error("retrieval_floor.k must be a positive integer");
  }
  if (!(METHODS as readonly string[]).includes(rf.method)) {
    throw new Error(
      `retrieval_floor.method must be one of ${[...METHODS].sort().join(", ")}`,
    );
  }
  if (!QUALITY_METRICS.has(rf.metric)) {
    throw new Error(
      `retrieval_floor.metric must be one of ${[...QUALITY_METRICS].sort().join(", ")}`,
    );
  }

  const floors: Array<[string, unknown]> = [
    ["retrieval_floor.floor", policy.retrieval_floor.floor],
  ];
  for (const k of Object.keys(FLOOR_METRICS)) {
    floors.push([
      `answer_floors.${k}`,
      policy.answer_floors[k as keyof typeof policy.answer_floors],
    ]);
  }
  for (const [name, floor] of floors) {
    if (!isFiniteNumber(floor) || floor < 0 || floor > 1) {
      throw new Error(`${name} must be a finite number in [0, 1]`);
    }
  }
  const bp = policy.bootstrap;
  if (!Number.isInteger(bp.iterations) || bp.iterations <= 0) {
    throw new Error("bootstrap.iterations must be a positive integer");
  }
  if (!isFiniteNumber(bp.alpha) || bp.alpha <= 0 || bp.alpha >= 1) {
    throw new Error("bootstrap.alpha must be a number in (0, 1)");
  }
  if (!Number.isInteger(bp.seed) || bp.seed < 0 || bp.seed > 0xffffffff) {
    throw new Error("bootstrap.seed must be an integer in [0, 2**32 - 1]");
  }
}

const CONTRACT_KEYS = [
  "retrieval_floor",
  "answer_floors",
  "comparison",
  "bootstrap",
] as const;

/** Canonical digest of the release-contract fields of a policy. */
export function policyDigest(policy: ReleasePolicy): string {
  const contract: Record<string, unknown> = {};
  for (const k of CONTRACT_KEYS) contract[k] = policy[k];
  return serializeCanonical(contract);
}

/** Bind the runtime policy to the committed release_policy.json: a runtime
 * policy that differs (e.g. an unpinned candidate variant) is rejected. */
export function requireCommittedPolicy(
  fixturesDir: string,
  policy: ReleasePolicy,
): void {
  const committed = loadJson<ReleasePolicy>(fixturesDir, "release_policy.json");
  if (policyDigest(policy) !== policyDigest(committed)) {
    throw new Error(
      "runtime policy does not match the committed release_policy.json " +
        "(commit a new policy + goldens to change the release contract)",
    );
  }
}

/** Floor / config / verdict violations (no drift, no policy binding). */
export function evaluatePolicy(
  policy: ReleasePolicy,
  evidence: Record<string, unknown>,
): string[] {
  const violations: string[] = [];
  const cp = policy.comparison;
  const af = policy.answer_floors;
  if (af.variant !== cp.candidate) {
    violations.push(
      `answer_floors.variant ${af.variant} != comparison.candidate ${cp.candidate}`,
    );
  }
  const rfe = evidence.retrieval_floor as {
    method: string;
    metric: string;
    floor: number;
    observed: number;
    passed: boolean;
  };
  if (!rfe.passed) {
    violations.push(
      `retrieval floor breached: ${rfe.method}.${rfe.metric} ${rfe.observed.toFixed(4)} < ${rfe.floor}`,
    );
  }
  const floors = evidence.answer_floors as Record<
    string,
    { floor: number; observed: number; passed: boolean }
  >;
  for (const floorKey of Object.keys(FLOOR_METRICS)) {
    const fr = floors[floorKey];
    if (!fr.passed) {
      violations.push(
        `answer floor breached: ${cp.candidate}.${floorKey} ${fr.observed.toFixed(4)} < ${fr.floor}`,
      );
    }
  }
  const comparison = evidence.comparison as { verdict: string };
  if (cp.require_improvement && comparison.verdict !== "promote") {
    violations.push(
      `improvement required but comparison verdict is ${comparison.verdict}`,
    );
  }
  return violations;
}

export function buildReleaseReport(
  fixturesDir: string,
  policy: ReleasePolicy,
): GateOutcome {
  // Gate 0: reject a malformed/no-op policy, an unpinned runtime policy, or a
  // malformed answer fixture BEFORE any evaluation.
  validatePolicy(policy);
  requireCommittedPolicy(fixturesDir, policy);
  validateAnswerFixtures(fixturesDir);

  const evidence = releaseEvidence(fixturesDir, policy);
  const violations = evaluatePolicy(policy, evidence);

  // Golden-drift enforcement is MANDATORY for a release-gate run: it cannot be
  // disabled by policy (that would let a consistently-doctored answer pass).
  const drift = checkDrift(fixturesDir);
  const goldenDrift = drift.goldenDrift;
  violations.push(...drift.violations);

  const report: Record<string, unknown> = {
    ...evidence,
    golden_drift: goldenDrift,
    gate: { ok: violations.length === 0, violations },
  };
  return { ok: violations.length === 0, violations, report };
}

export function runGate(
  fixturesDir: string,
  policy: ReleasePolicy,
  outDir?: string,
): GateOutcome {
  const outcome = buildReleaseReport(fixturesDir, policy);
  if (outDir !== undefined) {
    mkdirSync(outDir, { recursive: true });
    writeFileSync(
      join(outDir, "release_report.json"),
      serializeCanonical(outcome.report),
      "utf-8",
    );
  }
  return outcome;
}
