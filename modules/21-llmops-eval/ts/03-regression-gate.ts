/**
 * Task 3 — Regression gate in CI  🟡
 *
 * What this teaches:
 *   - A CI gate fails the build (process.exit(1)) when a key metric drops
 *     below a threshold, preventing regressions from reaching production.
 *   - The same script runs in GitHub Actions and as a pre-push hook.
 *
 * How to run:
 *   pnpm tsx modules/21-llmops-eval/ts/03-regression-gate.ts \
 *       --results modules/21-llmops-eval/results/<run>.json \
 *       --metric avg_score --threshold 0.6
 *
 *   pnpm tsx modules/21-llmops-eval/ts/03-regression-gate.ts \
 *       --run-fresh --metric faithfulness --threshold 0.7
 *
 * Exit codes: 0 = pass, 1 = fail (metric below threshold).
 */

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider } from "@learn-ai/llm-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const DATA_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/data");
const EVAL_SET_PATH = resolve(DATA_DIR, "eval_set_v1.json");

const DEFAULT_THRESHOLDS: Record<string, number> = {
  avg_score: 0.60,
  pass_rate: 0.60,
  faithfulness: 0.70,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ResultsSummary {
  avg_score?: number;
  pass_rate?: number;
  avg_latency_ms?: number;
  faithfulness?: number;
}

interface GraderResult {
  grader: string;
  score: number;
  passed: boolean;
}

interface CaseData {
  grader_results?: GraderResult[];
  [key: string]: unknown;
}

interface ResultsFile {
  summary?: ResultsSummary;
  cases?: CaseData[];
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Step 1 — Load results file
// ---------------------------------------------------------------------------

/**
 * Parse a JSON results file produced by task 1 or 2.
 *
 * TODO 1: Read the file as UTF-8 text and parse the JSON.
 * Throw a descriptive error if the file doesn't exist.
 * Return the parsed object as ResultsFile.
 */
function loadResults(path: string): ResultsFile {
  // TODO: implement loadResults
  throw new Error("TODO: implement loadResults");
}

// ---------------------------------------------------------------------------
// Step 2 — Extract metric
// ---------------------------------------------------------------------------

/**
 * Pull the numeric value of `metric` from the results dict.
 *
 * TODO 2a: Try results.summary?.[metric].
 * TODO 2b: For 'faithfulness', average the llm_judge grader scores
 *          across results.cases.
 * TODO 2c: Throw if the metric can't be found.
 * Return the number.
 */
function extractMetric(results: ResultsFile, metric: string): number {
  // TODO: implement extractMetric
  throw new Error("TODO: implement extractMetric");
}

// ---------------------------------------------------------------------------
// Step 3 — Run fresh eval
// ---------------------------------------------------------------------------

/**
 * Run a quick eval and return a ResultsFile-compatible object.
 *
 * TODO 3a: Load eval set from EVAL_SET_PATH.
 * TODO 3b: For each case, call provider.chat() with context-stuffed prompt.
 * TODO 3c: Score faithfulness via LLM-judge (0–10 → /10).
 * TODO 3d: Return { summary: { avg_score, pass_rate, faithfulness }, cases }.
 */
async function runFreshEval(
  provider: ReturnType<typeof getProvider>,
): Promise<ResultsFile> {
  // TODO: implement runFreshEval
  throw new Error("TODO: implement runFreshEval");
}

// ---------------------------------------------------------------------------
// Step 4 — Gate check
// ---------------------------------------------------------------------------

/**
 * Log pass/fail and return true if value >= threshold.
 *
 * TODO 4: Print one clear line tagged PASS or FAIL that names the metric, its
 *         value, the comparison, and the threshold.
 * Return boolean.
 */
function checkGate(value: number, threshold: number, metric: string): boolean {
  // TODO: implement checkGate
  throw new Error("TODO: implement checkGate");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(): {
  resultsPath: string | null;
  runFresh: boolean;
  metric: string;
  threshold: number | null;
} {
  const argv = process.argv.slice(2);
  let resultsPath: string | null = null;
  let runFresh = false;
  let metric = "avg_score";
  let threshold: number | null = null;

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--results" && argv[i + 1]) resultsPath = argv[++i];
    if (argv[i] === "--run-fresh") runFresh = true;
    if (argv[i] === "--metric" && argv[i + 1]) metric = argv[++i];
    if (argv[i] === "--threshold" && argv[i + 1]) threshold = parseFloat(argv[++i]);
  }
  return { resultsPath, runFresh, metric, threshold };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const { resultsPath, runFresh, metric, threshold: thresholdArg } = parseArgs();
  const threshold = thresholdArg ?? DEFAULT_THRESHOLDS[metric] ?? 0.6;

  let results: ResultsFile;

  if (runFresh) {
    const provider = getProvider();
    console.log(`Running fresh eval with ${provider.name}/${provider.chatModel}...`);
    results = await runFreshEval(provider);
  } else if (resultsPath) {
    results = loadResults(resultsPath);
  } else {
    console.error("Provide --results <path> or --run-fresh.");
    process.exit(1);
  }

  const value = extractMetric(results, metric);
  const passed = checkGate(value, threshold, metric);
  process.exit(passed ? 0 : 1);
}

main().catch((e) => { console.error(e); process.exit(1); });
