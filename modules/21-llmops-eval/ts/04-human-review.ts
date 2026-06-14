/**
 * Task 4 — Human review + feedback loop  🟡
 *
 * What this teaches:
 *   - Low-confidence outputs (LLM-judge score below threshold) go to a review
 *     queue so humans can label them.
 *   - Human labels close the loop: approved outputs become new golden eval cases.
 *   - The queue is a JSONL file for easy portability.
 *
 * How to run:
 *   pnpm tsx modules/21-llmops-eval/ts/04-human-review.ts --write-queue
 *   pnpm tsx modules/21-llmops-eval/ts/04-human-review.ts --label
 *   pnpm tsx modules/21-llmops-eval/ts/04-human-review.ts --merge
 *   pnpm tsx modules/21-llmops-eval/ts/04-human-review.ts --demo
 */

import {
  readFileSync,
  writeFileSync,
  appendFileSync,
  mkdirSync,
} from "node:fs";
import * as readline from "node:readline";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider } from "@learn-ai/llm-core";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, "../../../");
const DATA_DIR = resolve(REPO_ROOT, "modules/21-llmops-eval/data");
const REVIEW_QUEUE_PATH = resolve(DATA_DIR, "review_queue.jsonl");
const EVAL_SET_PATH = resolve(DATA_DIR, "eval_set_v1.json");

const CONFIDENCE_THRESHOLD = 0.75;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QueueItem {
  item_id: string;
  case_id: string;
  question: string;
  context: string;
  system_output: string;
  judge_score: number;
  judge_reason: string;
  queued_at: string;
  human_label: string | null;
  human_note: string | null;
  labelled_at: string | null;
  promoted: boolean;
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
// Step 1 — Judge output
// ---------------------------------------------------------------------------

/**
 * Score output with an LLM-as-judge. Return [score_0_1, reason].
 *
 * TODO 1a: Build a judge prompt with question, rubric, output.
 *          Ask for JSON: {"score": <0-10>, "reason": "<string>"}.
 * TODO 1b: provider.chat() with temperature 0.
 * TODO 1c: Parse JSON; normalise score /10. Default 0 on error.
 * Return [normalised_score, reason].
 */
async function judgeOutput(
  question: string,
  output: string,
  rubric: string,
  provider: ReturnType<typeof getProvider>,
): Promise<[number, string]> {
  // TODO: implement judgeOutput
  throw new Error("TODO: implement judgeOutput");
}

/**
 * Run a mini eval and collect low-confidence outputs.
 *
 * TODO 2a: For each case, call provider.chat() with context-stuffed prompt.
 * TODO 2b: judgeOutput().
 * TODO 2c: If judge_score < CONFIDENCE_THRESHOLD, create a QueueItem.
 * Return QueueItem[].
 */
async function runAndQueue(
  cases: EvalCase[],
  provider: ReturnType<typeof getProvider>,
): Promise<QueueItem[]> {
  // TODO: implement runAndQueue
  throw new Error("TODO: implement runAndQueue");
}

// ---------------------------------------------------------------------------
// Step 2 — Write queue
// ---------------------------------------------------------------------------

/**
 * Append QueueItems to REVIEW_QUEUE_PATH as JSONL.
 *
 * TODO 3a: mkdirSync(DATA_DIR, { recursive: true }).
 * TODO 3b: appendFileSync with JSON.stringify(item) + '\n' for each item.
 */
function writeQueue(items: QueueItem[]): void {
  // TODO: implement writeQueue
  throw new Error("TODO: implement writeQueue");
}

// ---------------------------------------------------------------------------
// Step 3 — Interactive labelling
// ---------------------------------------------------------------------------

/**
 * Present each unlabelled item and collect a human label.
 *
 * TODO 4a: Read + parse REVIEW_QUEUE_PATH.
 * TODO 4b: Skip already-labelled items.
 * TODO 4c: Display question, system_output, judge_score.
 * TODO 4d: Prompt: "Label [correct/incorrect/partial/skip]: "
 * TODO 4e: Update and rewrite the JSONL.
 *
 * Hint: use readline.createInterface for stdin.
 */
async function labelQueueInteractive(): Promise<void> {
  // TODO: implement labelQueueInteractive
  throw new Error("TODO: implement labelQueueInteractive");
}

// ---------------------------------------------------------------------------
// Step 4 — Merge labels back into eval set
// ---------------------------------------------------------------------------

/**
 * Promote 'correct' labels into the versioned eval set.
 *
 * TODO 5a: Load REVIEW_QUEUE_PATH; filter human_label=='correct' && !promoted.
 * TODO 5b: Load EVAL_SET_PATH.
 * TODO 5c: Add a new case for each approved item (id='hq_<item_id>').
 * TODO 5d: Bump the patch version.
 * TODO 5e: Write updated eval set.
 * TODO 5f: Mark promoted=true; rewrite queue.
 */
function mergeLabelsIntoEvalSet(): void {
  // TODO: implement mergeLabelsIntoEvalSet
  throw new Error("TODO: implement mergeLabelsIntoEvalSet");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

function parseArgs(): { writeQueue: boolean; label: boolean; merge: boolean; demo: boolean } {
  const argv = process.argv.slice(2);
  return {
    writeQueue: argv.includes("--write-queue"),
    label: argv.includes("--label"),
    merge: argv.includes("--merge"),
    demo: argv.includes("--demo"),
  };
}

async function main(): Promise<void> {
  const args = parseArgs();

  if (!args.writeQueue && !args.label && !args.merge && !args.demo) {
    console.log("Usage: 04-human-review.ts [--write-queue] [--label] [--merge] [--demo]");
    process.exit(1);
  }

  if (args.writeQueue || args.demo) {
    const provider = getProvider();
    const data = JSON.parse(readFileSync(EVAL_SET_PATH, "utf8"));
    const items = await runAndQueue(data.cases as EvalCase[], provider);
    writeQueue(items);
    console.log(`Queued ${items.length} items for review.`);
  }

  if (args.label || args.demo) {
    await labelQueueInteractive();
  }

  if (args.merge || args.demo) {
    mergeLabelsIntoEvalSet();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
