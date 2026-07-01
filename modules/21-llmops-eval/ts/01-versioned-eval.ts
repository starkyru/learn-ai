/**
 * Task 1 — Versioned eval set + graders  🟢
 *
 * What this teaches:
 *   - Eval datasets should be versioned (like code) so you can detect
 *     regressions across prompt or model changes.
 *   - Graders form a spectrum: exact/contains (cheap) → LLM-as-judge (smart).
 *   - A runner writes results to a timestamped file for reproducibility.
 *
 * How to run:
 *   pnpm tsx modules/21-llmops-eval/ts/01-versioned-eval.ts
 *   # Results land in: modules/21-llmops-eval/results/
 */

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider, ChatMessage } from "@learn-ai/llm-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const DATA_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/data");
const RESULTS_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/results");
const EVAL_SET_PATH = resolve(DATA_DIR, "eval_set_v1.json");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EvalCase {
  id: string;
  question: string;
  context: string;
  reference_answer: string;
  graders: string[];
  rubric: string;
}

interface GraderResult {
  grader: string;
  score: number;    // 0.0–1.0
  passed: boolean;
  detail?: string;
}

interface CaseResult {
  case_id: string;
  question: string;
  system_output: string;
  latency_ms: number;
  grader_results: GraderResult[];
  overall_score: number;
}

// ---------------------------------------------------------------------------
// Step 1 — Load versioned eval set
// ---------------------------------------------------------------------------

/**
 * Load eval_set_v1.json and return { version, cases }.
 *
 * TODO 1a: Read EVAL_SET_PATH with readFileSync, parse JSON.
 * TODO 1b: Extract `version` (string) and `cases` (array).
 * Return { version: string, cases: EvalCase[] }.
 */
function loadEvalSet(path: string): { version: string; cases: EvalCase[] } {
  // TODO: implement loadEvalSet
  throw new Error("TODO: implement loadEvalSet");
}

// ---------------------------------------------------------------------------
// Step 2 — System under test
// ---------------------------------------------------------------------------

/**
 * Call the LLM with a RAG-style prompt. Returns [answer, latency_ms].
 *
 * TODO 2a: Build a system prompt that instructs the model to answer ONLY
 *          from the provided context.
 * TODO 2b: Call provider.chat() with [systemMsg, userQuestion].
 * TODO 2c: Time the call; compute latency_ms = Date.now() after - before.
 * Return [result.text, latency_ms].
 */
async function runSystem(
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>,
): Promise<[string, number]> {
  // TODO: implement runSystem
  throw new Error("TODO: implement runSystem");
}

// ---------------------------------------------------------------------------
// Step 3 — Graders
// ---------------------------------------------------------------------------

/**
 * Exact-match grader: passes if reference_answer appears verbatim in output.
 *
 * TODO 3a: Decide whether reference_answer appears inside output, ignoring
 *          letter case (normalise both sides before comparing).
 * Return a GraderResult (score 1.0/0.0, passed to match).
 */
function gradeExact(output: string, evalCase: EvalCase): GraderResult {
  // TODO: implement gradeExact
  throw new Error("TODO: implement gradeExact");
}

/**
 * Contains grader: passes if any key token (len > 3) from reference_answer
 * appears in output.
 *
 * TODO 3b: Split reference_answer on whitespace, filter tokens.length > 3.
 *          Pass if at least one token appears in output (case-insensitive).
 * Return a GraderResult.
 */
function gradeContains(output: string, evalCase: EvalCase): GraderResult {
  // TODO: implement gradeContains
  throw new Error("TODO: implement gradeContains");
}

/**
 * LLM-as-judge grader: ask a second LLM to score 0–10.
 *
 * TODO 3c: Build a `ChatMessage[]` for a judge that sees the question, the
 *          rubric, and the output to evaluate, and is told to reply with ONLY a
 *          JSON object carrying an integer score (0–10) and a short reason.
 * TODO 3d: Call provider.chat() with temperature 0 (deterministic grading).
 * TODO 3e: Parse the JSON, normalise the score into 0–1 (divide by the 0–10
 *          range), and treat a score of 7+ as a pass. Handle parse errors
 *          gracefully (fall back to score 0, not passed).
 * Return a GraderResult.
 */
async function gradeLlmJudge(
  output: string,
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>,
): Promise<GraderResult> {
  // TODO: implement gradeLlmJudge
  throw new Error("TODO: implement gradeLlmJudge");
}

async function runGraders(
  output: string,
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>,
): Promise<GraderResult[]> {
  const results: GraderResult[] = [];
  for (const grader of evalCase.graders) {
    if (grader === "exact") results.push(gradeExact(output, evalCase));
    else if (grader === "contains") results.push(gradeContains(output, evalCase));
    else if (grader === "llm_judge") results.push(await gradeLlmJudge(output, evalCase, provider));
  }
  return results;
}

// ---------------------------------------------------------------------------
// Step 4 — Runner
// ---------------------------------------------------------------------------

/**
 * Load eval set, run every case, collect results.
 *
 * TODO 4a: Call loadEvalSet().
 * TODO 4b: For each EvalCase, call runSystem() then runGraders().
 * TODO 4c: Compute overall_score = average of grader scores.
 * TODO 4d: Print progress.
 * Return CaseResult[].
 */
async function runEval(
  evalSetPath: string,
  provider: ReturnType<typeof getProvider>,
): Promise<CaseResult[]> {
  // TODO: implement runEval
  throw new Error("TODO: implement runEval");
}

// ---------------------------------------------------------------------------
// Step 5 — Results writer
// ---------------------------------------------------------------------------

/**
 * Write results to a timestamped JSON file in RESULTS_DIR.
 *
 * TODO 5a: mkdirSync(RESULTS_DIR, { recursive: true }).
 * TODO 5b: Build a results object with:
 *          eval_version, run_at, provider, model, summary, cases.
 * TODO 5c: Write to RESULTS_DIR/run_<timestamp>.json.
 * Return the output path.
 */
function writeResults(
  caseResults: CaseResult[],
  evalVersion: string,
  provider: ReturnType<typeof getProvider>,
): string {
  // TODO: implement writeResults
  throw new Error("TODO: implement writeResults");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const provider = getProvider();
  console.log(`Provider: ${provider.name}  model: ${provider.chatModel}\n`);

  const caseResults = await runEval(EVAL_SET_PATH, provider);

  const scores = caseResults.map((r) => r.overall_score);
  const avg = scores.reduce((a, b) => a + b, 0) / (scores.length || 1);
  const passRate = scores.filter((s) => s >= 0.7).length / (scores.length || 1);
  console.log("\n=== Summary ===");
  console.log(`Cases:      ${caseResults.length}`);
  console.log(`Pass rate:  ${(passRate * 100).toFixed(1)}%`);
  console.log(`Avg score:  ${avg.toFixed(2)}`);

  const outPath = writeResults(caseResults, "1.0.0", provider);
  console.log(`\nResults written to: ${outPath}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
