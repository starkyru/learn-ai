/**
 * Task 1 🟢 — LLM zero-shot and few-shot classification.
 *
 * What you'll learn:
 *   - How to turn an LLM into a classifier with a single prompt
 *   - How zero-shot (no examples) differs from few-shot (a handful of examples)
 *   - Robust label parsing: what to do when the model says "Technology" vs "technology"
 *   - The cost/latency trade-off vs. a trained classifier
 *
 * Key insight: LLMs are already trained on human text, so they "understand" labels
 * like "technology" or "sports" without any task-specific training data. Few-shot
 * examples narrow their interpretation and reduce format errors.
 *
 * How to run:
 *   pnpm tsx modules/08-classification/ts/01-llm-classifier.ts
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Labels and dataset
// ---------------------------------------------------------------------------

const LABELS = ["technology", "science", "business", "sports", "health", "politics"] as const;
type Label = (typeof LABELS)[number];

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

interface DataItem {
  id: number;
  text: string;
  label: Label;
}

function loadDataset(): DataItem[] {
  const path = join(__dirname, "../data/texts.json");
  return JSON.parse(readFileSync(path, "utf-8")) as DataItem[];
}

// ---------------------------------------------------------------------------
// Label parsing — robust against model formatting variations
// ---------------------------------------------------------------------------

/**
 * Extract a clean label from the model's raw response.
 *
 * The model might return:
 *   - "technology"           → exact match
 *   - "Technology"           → case difference
 *   - "Label: technology"    → wrapped in a key
 *   - "The answer is sports" → embedded in prose
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Lowercase and trim the raw string.
 *   2. Check if any valid label appears as a substring — return the first match.
 *   3. If nothing matches, return null.
 */
function parseLabel(raw: string, validLabels: readonly string[]): string | null {
  // TODO: implement robust label extraction
  throw new Error("TODO: implement parseLabel()");
}

// ---------------------------------------------------------------------------
// Zero-shot classifier
// ---------------------------------------------------------------------------

/**
 * Build a zero-shot classification prompt.
 *
 * Zero-shot means: no examples — just a task description and the label set.
 *
 * TODO: craft a prompt that:
 *   1. Tells the model it is a text classifier.
 *   2. Lists the valid labels exactly (join with ", ").
 *   3. Instructs it to reply with ONLY the label (no explanation).
 *   4. Presents the text to classify.
 */
function buildZeroShotPrompt(text: string, labels: readonly string[]): string {
  // TODO: return the formatted prompt string
  throw new Error("TODO: implement buildZeroShotPrompt()");
}

async function classifyZeroShot(
  text: string,
  provider: ReturnType<typeof getProvider>,
  labels: readonly string[] = LABELS,
): Promise<string | null> {
  /**
   * TODO:
   *   1. Build the prompt with buildZeroShotPrompt().
   *   2. Call provider.chat() with temperature: 0 for deterministic output.
   *   3. Parse with parseLabel().
   *   4. Return the label or null.
   */
  throw new Error("TODO: implement classifyZeroShot()");
}

// ---------------------------------------------------------------------------
// Few-shot classifier
// ---------------------------------------------------------------------------

const FEW_SHOT_EXAMPLES: [string, string][] = [
  ["NASA launched a new space telescope to study distant galaxies.", "science"],
  ["The central bank cut interest rates amid recession fears.", "business"],
  ["The striker scored a hat-trick in the cup final.", "sports"],
  ["Eating more fibre reduces cholesterol and improves gut health.", "health"],
  ["The new legislation restricts campaign finance donations.", "politics"],
  ["Engineers demonstrated a chip that runs on ambient light alone.", "technology"],
];

/**
 * Build a few-shot classification prompt.
 *
 * TODO: craft a prompt that:
 *   1. Describes the task and valid labels (same as zero-shot).
 *   2. Shows each [exampleText, label] pair in a clear, consistent format —
 *      e.g. a line for the text and a line for its label, repeated per example.
 *   3. Ends with the query text in that SAME layout but with the label line left
 *      blank, so the model completes it. Reuse the exact field labels/delimiters
 *      you chose for the examples.
 */
function buildFewShotPrompt(
  text: string,
  examples: [string, string][],
  labels: readonly string[],
): string {
  // TODO: return the formatted prompt string
  throw new Error("TODO: implement buildFewShotPrompt()");
}

async function classifyFewShot(
  text: string,
  provider: ReturnType<typeof getProvider>,
  examples: [string, string][] = FEW_SHOT_EXAMPLES,
  labels: readonly string[] = LABELS,
): Promise<string | null> {
  /**
   * TODO: same structure as classifyZeroShot() but use buildFewShotPrompt().
   */
  throw new Error("TODO: implement classifyFewShot()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (chat model: ${provider.chatModel})`);

  const dataset = loadDataset();

  // Run on first 10 examples only (LLM calls are slow/costly for full set)
  const sample = dataset.slice(0, 10);

  console.log("\n" + "=".repeat(70));
  console.log("ZERO-SHOT CLASSIFICATION");
  console.log("=".repeat(70));
  let zeroCorrect = 0;
  for (const item of sample) {
    const pred = await classifyZeroShot(item.text, provider);
    const correct = pred === item.label;
    if (correct) zeroCorrect++;
    const mark = correct ? "✓" : "✗";
    console.log(
      `  [${mark}] true=${item.label.padEnd(12)} pred=${String(pred).padEnd(12)} | ${item.text.slice(0, 60)}...`,
    );
  }
  console.log(`\n  Zero-shot accuracy: ${zeroCorrect}/${sample.length}`);

  console.log("\n" + "=".repeat(70));
  console.log("FEW-SHOT CLASSIFICATION");
  console.log("=".repeat(70));
  let fewCorrect = 0;
  for (const item of sample) {
    const pred = await classifyFewShot(item.text, provider);
    const correct = pred === item.label;
    if (correct) fewCorrect++;
    const mark = correct ? "✓" : "✗";
    console.log(
      `  [${mark}] true=${item.label.padEnd(12)} pred=${String(pred).padEnd(12)} | ${item.text.slice(0, 60)}...`,
    );
  }
  console.log(`\n  Few-shot accuracy: ${fewCorrect}/${sample.length}`);

  console.log("\n" + "=".repeat(70));
  console.log("REFLECTION");
  console.log("=".repeat(70));
  console.log("  Did few-shot improve accuracy? Which categories are hardest?");
  console.log("  Notice the latency — each call goes to the network.");
  console.log("  In Task 3 we compare this to a trained classifier on the full set.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
