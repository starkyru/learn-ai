/**
 * Task 2 — Experiments  🟡
 *
 * What this teaches:
 *   - Systematic prompt/model experimentation is the core LLMOps workflow.
 *     You shouldn't tweak prompts and *hope* things improve — you measure.
 *   - Every run is stored with metadata (model, prompt version, timestamp)
 *     so you can replay, diff, and compare across time.
 *   - A simple winner-selection function turns numeric scores into decisions.
 *
 * How to run:
 *   pnpm tsx modules/21-llmops-eval/ts/02-experiments.ts
 *   pnpm tsx modules/21-llmops-eval/ts/02-experiments.ts --prompt-version v2
 *   pnpm tsx modules/21-llmops-eval/ts/02-experiments.ts \
 *       --compare results/run_A.json results/run_B.json
 */

import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider, ChatOptions } from "@learn-ai/llm-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const DATA_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/data");
const RESULTS_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/results");
const EVAL_SET_PATH = resolve(DATA_DIR, "eval_set_v1.json");

// ---------------------------------------------------------------------------
// Prompt variants
// ---------------------------------------------------------------------------

const PROMPT_VARIANTS: Record<string, string> = {
  v1: "You are a helpful assistant. Answer the user's question using ONLY the provided context. If the context does not contain the answer, say 'I don't know'.\n\nContext:\n{context}",
  v2: "You are a precise technical assistant. Answer in one or two sentences. Use ONLY the following context — do not add outside knowledge.\n\nContext:\n{context}\n\nIf the answer is not in the context, reply exactly: 'Not found in context.'",
  v3: "Answer the question based solely on the context below. Be concise. Quote the relevant part of the context in your answer.\n\nContext:\n{context}",
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RunMetadata {
  run_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  timestamp: string;
  eval_version: string;
}

interface CaseOutput {
  id: string;
  question: string;
  output: string;
  score: number;
  latency_ms: number;
}

interface ExperimentRun {
  metadata: RunMetadata;
  scores: number[];
  avg_score: number;
  pass_rate: number;
  avg_latency_ms: number;
  raw_cases: CaseOutput[];
}

interface EvalCase {
  id: string;
  question: string;
  context: string;
  reference_answer: string;
  graders: string[];
  rubric: string;
}

// ---------------------------------------------------------------------------
// Step 1 — Load eval set
// ---------------------------------------------------------------------------

/**
 * Load eval_set_v1.json and return its cases.
 *
 * TODO 1: readFileSync + JSON.parse; return data.cases as EvalCase[].
 */
function loadEvalSet(path: string): EvalCase[] {
  // TODO: implement loadEvalSet
  throw new Error("TODO: implement loadEvalSet");
}

// ---------------------------------------------------------------------------
// Step 2 — Single-case runner
// ---------------------------------------------------------------------------

/**
 * Run one case through the provider and return [answer, latency_ms].
 *
 * TODO 2a: Format systemPrompt by replacing {context} with evalCase.context.
 * TODO 2b: Call provider.chat([systemMsg, userMsg], { temperature: 0 }).
 * TODO 2c: Measure latency with Date.now().
 * Return [result.text, latency_ms].
 */
async function runOne(
  evalCase: EvalCase,
  systemPromptTemplate: string,
  provider: ReturnType<typeof getProvider>,
): Promise<[string, number]> {
  // TODO: implement runOne
  throw new Error("TODO: implement runOne");
}

// ---------------------------------------------------------------------------
// Step 3 — Quick scorer
// ---------------------------------------------------------------------------

/**
 * Return 1.0 if key tokens from reference_answer appear in output, else 0.0.
 *
 * TODO 3: Split reference_answer on whitespace, filter token.length > 3.
 *         Pass if any token appears in output.toLowerCase().
 */
function quickScore(output: string, evalCase: EvalCase): number {
  // TODO: implement quickScore
  throw new Error("TODO: implement quickScore");
}

// ---------------------------------------------------------------------------
// Step 4 — Run an experiment
// ---------------------------------------------------------------------------

/**
 * Run the full eval set for one prompt+model variant.
 *
 * TODO 4a: Build RunMetadata.
 * TODO 4b: Get prompt template from PROMPT_VARIANTS[promptVersion].
 * TODO 4c: For each case, runOne() + quickScore().
 * TODO 4d: Compute avg_score, pass_rate (>= 0.5), avg_latency_ms.
 * Return ExperimentRun.
 */
async function runExperiment(
  promptVersion: string,
  provider: ReturnType<typeof getProvider>,
  cases: EvalCase[],
): Promise<ExperimentRun> {
  // TODO: implement runExperiment
  throw new Error("TODO: implement runExperiment");
}

// ---------------------------------------------------------------------------
// Step 5 — Persist run
// ---------------------------------------------------------------------------

/**
 * Save an ExperimentRun as JSON to RESULTS_DIR.
 *
 * TODO 5a: mkdirSync(RESULTS_DIR, { recursive: true }).
 * TODO 5b: Filename: run_{timestamp}_{promptVersion}_{model}.json
 * TODO 5c: JSON.stringify + writeFileSync.
 * Return the output path.
 */
function saveRun(run: ExperimentRun): string {
  // TODO: implement saveRun
  throw new Error("TODO: implement saveRun");
}

// ---------------------------------------------------------------------------
// Step 6 — Compare and pick a winner
// ---------------------------------------------------------------------------

/**
 * Print a side-by-side comparison and declare a winner.
 *
 * TODO 6a: Print a table of run_id, model, prompt_version, avg_score, pass_rate, latency.
 * TODO 6b: Winner = higher avg_score (ties: lower latency).
 * TODO 6c: Print the winner.
 */
function compareRuns(runA: ExperimentRun, runB: ExperimentRun): void {
  // TODO: implement compareRuns
  throw new Error("TODO: implement compareRuns");
}

function loadRunFromFile(path: string): ExperimentRun {
  // TODO: readFileSync + JSON.parse
  throw new Error("TODO: implement loadRunFromFile");
}

// ---------------------------------------------------------------------------
// CLI arg parsing (minimal, no deps)
// ---------------------------------------------------------------------------

function parseArgs(): { promptVersion: string; compare: [string, string] | null } {
  const args = process.argv.slice(2);
  let promptVersion = "v1";
  let compare: [string, string] | null = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--prompt-version" && args[i + 1]) promptVersion = args[++i];
    if (args[i] === "--compare" && args[i + 1] && args[i + 2]) {
      compare = [args[++i], args[++i]];
    }
  }
  return { promptVersion, compare };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const { promptVersion, compare } = parseArgs();

  if (compare) {
    const runA = loadRunFromFile(compare[0]);
    const runB = loadRunFromFile(compare[1]);
    compareRuns(runA, runB);
    return;
  }

  const provider = getProvider();
  console.log(`Provider: ${provider.name}  model: ${provider.chatModel}`);
  console.log(`Prompt version: ${promptVersion}\n`);

  const cases = loadEvalSet(EVAL_SET_PATH);
  const run = await runExperiment(promptVersion, provider, cases);
  const path = saveRun(run);

  console.log(`\nRun: ${run.metadata.run_id}`);
  console.log(`Avg score:   ${run.avg_score.toFixed(2)}`);
  console.log(`Pass rate:   ${(run.pass_rate * 100).toFixed(1)}%`);
  console.log(`Avg latency: ${run.avg_latency_ms.toFixed(0)} ms`);
  console.log(`\nSaved to: ${path}`);
}

main().catch((e) => { console.error(e); process.exit(1); });
