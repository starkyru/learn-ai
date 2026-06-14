/**
 * Task 5 — Prompt eval harness 🟡
 *
 * What this teaches:
 *   - Prompt engineering without measurement is guessing. A tiny eval harness
 *     turns "I think prompt A is better" into "prompt A scores 80%, prompt B
 *     scores 60% on this dataset."
 *   - The dataset is eval_dataset.json (10 labelled sentiment examples).
 *   - You define two or more prompt variants, run each on the full dataset,
 *     and print a comparison table. Pick the winner with numbers.
 *   - This is the same principle behind large-scale LLM evals — just smaller.
 *
 * Dataset: ../eval_dataset.json
 *
 * How to run:
 *   pnpm tsx modules/03-prompting/ts/05-eval-harness.ts
 */

import { getProvider } from "@learn-ai/llm-core";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

// ---------------------------------------------------------------------------
// Load dataset
// ---------------------------------------------------------------------------
interface DataPoint {
  id: string;
  input: string;
  label: string;
}

const DATASET: DataPoint[] = JSON.parse(
  readFileSync(join(__dirname, "..", "eval_dataset.json"), "utf-8"),
);

// ---------------------------------------------------------------------------
// TODO 1: Define at least TWO prompt variants for the same task (sentiment
//         classification). Vary the instruction style, persona, output format
//         instruction, or example count. Be deliberate — form a hypothesis
//         about which will score higher BEFORE running.
//         Examples of things to vary:
//           - "Respond with one word" vs "Answer: <label>" format
//           - No examples vs 1 example
//           - Terse system prompt vs detailed system prompt
// ---------------------------------------------------------------------------
interface PromptVariant {
  name: string;
  buildPrompt: (input: string) => { role: string; content: string }[];
}

const VARIANTS: PromptVariant[] = [
  {
    name: "variant-A: minimal",
    buildPrompt: (input) => [
      { role: "system", content: "Classify sentiment as positive, negative, or neutral. One word only." },
      { role: "user", content: input },
    ],
  },
  {
    name: "variant-B: TODO — define your second variant",
    buildPrompt: (input) => [
      // TODO: try a different instruction style. E.g.:
      // { role: "system", content: "You are a customer review analyst..." },
      // { role: "user", content: `Review: "${input}"\nSentiment:` },
      { role: "user", content: `TODO — implement variant B. Input: ${input}` },
    ],
  },
  // TODO (stretch): add a variant-C with a few-shot example
];

// ---------------------------------------------------------------------------
// TODO 2: Implement parseOutput.
//         Same as task 4: extract the label from the raw model output.
//         Normalise: lowercase, trim, remove non-alpha characters.
//         Return the cleaned string (don't throw — just return whatever comes
//         back so you can see where the model deviates in the eval table).
// ---------------------------------------------------------------------------
function parseOutput(raw: string): string {
  // TODO: implement — return the cleaned label string
  return raw.trim().toLowerCase().replace(/[^a-z]/g, "");
}

// ---------------------------------------------------------------------------
// TODO 3: Implement evalVariant.
//         Run the given variant on every DataPoint in DATASET.
//         For each point:
//           - Call llm.chat(variant.buildPrompt(point.input) as any).
//           - Parse the output.
//           - Compare (case-insensitive) to point.label.
//           - Record result.
//         Return an array of per-sample results plus the overall accuracy.
// ---------------------------------------------------------------------------
interface SampleResult {
  id: string;
  input: string;
  expected: string;
  predicted: string;
  correct: boolean;
}

interface EvalResult {
  variantName: string;
  samples: SampleResult[];
  accuracy: number;
}

async function evalVariant(variant: PromptVariant): Promise<EvalResult> {
  const llm = getProvider();
  const samples: SampleResult[] = [];

  for (const point of DATASET) {
    // TODO: call the LLM and record the result
    // const messages = variant.buildPrompt(point.input);
    // const result = await llm.chat(messages as any);
    // const predicted = parseOutput(result.text);
    // const correct = predicted === point.label.toLowerCase();
    // samples.push({ id: point.id, input: point.input, expected: point.label, predicted, correct });

    // Placeholder until implemented:
    samples.push({ id: point.id, input: point.input, expected: point.label, predicted: "TODO", correct: false });
  }

  const accuracy = samples.filter(s => s.correct).length / samples.length;
  return { variantName: variant.name, samples, accuracy };
}

// ---------------------------------------------------------------------------
// TODO 4: Print results in a readable table.
//         For each variant: accuracy percentage, then per-sample rows showing
//         input (truncated), expected, predicted, and ✓ or ✗.
//         Finally, print a summary row comparing all variants.
// ---------------------------------------------------------------------------
function printResults(results: EvalResult[]): void {
  for (const r of results) {
    console.log(`\n=== ${r.variantName} ===`);
    console.log(`Accuracy: ${(r.accuracy * 100).toFixed(0)}% (${r.samples.filter(s => s.correct).length}/${r.samples.length})\n`);
    console.log("ID".padEnd(12) + "Expected".padEnd(12) + "Predicted".padEnd(12) + "OK?  " + "Input");
    console.log("-".repeat(80));
    for (const s of r.samples) {
      const ok = s.correct ? "✓" : "✗";
      const truncated = s.input.length > 35 ? s.input.slice(0, 32) + "..." : s.input;
      console.log(s.id.padEnd(12) + s.expected.padEnd(12) + s.predicted.padEnd(12) + ok.padEnd(5) + truncated);
    }
  }

  // Summary comparison
  console.log("\n=== Summary ===");
  console.log("Variant".padEnd(35) + "Accuracy");
  console.log("-".repeat(45));
  for (const r of results.sort((a, b) => b.accuracy - a.accuracy)) {
    console.log(r.variantName.padEnd(35) + `${(r.accuracy * 100).toFixed(0)}%`);
  }
}

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}`);
  console.log(`Dataset: ${DATASET.length} examples`);
  console.log(`Variants: ${VARIANTS.length}\n`);

  // -------------------------------------------------------------------------
  // TODO 5: Run eval for each variant and collect results.
  //         Tip: run them in parallel with Promise.all to save time:
  //           const results = await Promise.all(VARIANTS.map(evalVariant));
  //         Then call printResults(results).
  // -------------------------------------------------------------------------

  // const results = await Promise.all(VARIANTS.map(evalVariant));
  // printResults(results);

  // Placeholder until implemented:
  console.log("TODO: implement the eval loop above and call printResults.");
  const placeholderResults = await Promise.all(VARIANTS.map(evalVariant));
  printResults(placeholderResults);
}

main().catch(console.error);
