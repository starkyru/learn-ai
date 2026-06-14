/**
 * Task 3 — Self-refine / reflection 🟡
 *
 * What this teaches:
 *   - Draft → critique → revise is a three-turn loop that mimics how a human
 *     reviews their own work. Each iteration uses the model to judge AND improve
 *     its own previous output.
 *   - Even a single round of self-refinement frequently improves factual accuracy,
 *     completeness, and clarity on open-ended tasks.
 *   - Multiple iterations converge quickly: the marginal gain from iteration 3 is
 *     usually not worth iteration 2's cost. Measure, don't assume.
 *
 * How to run:
 *   pnpm tsx modules/15-reasoning-test-time-compute/ts/03-self-refine.ts
 */

import "dotenv/config";
import { getProvider, ChatMessage, ChatOptions } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Tasks to refine — open-ended so there is real room for improvement.
// ---------------------------------------------------------------------------
const TASKS = [
  {
    id: "explain",
    prompt:
      "Explain how a transformer attention mechanism works to a software " +
      "engineer who has not studied machine learning. Use an analogy.",
  },
  {
    id: "plan",
    prompt:
      "Write a brief 5-step plan for launching a personal blog in 2025, " +
      "including tools, audience strategy, and monetisation.",
  },
];

const MAX_ITERATIONS = 2;

const CRITIQUE_SYSTEM =
  "You are a critical reviewer. Read the task and the draft answer below.\n" +
  "List 3–5 specific issues, gaps, or inaccuracies in the draft. " +
  "Be concrete — do not say 'it could be clearer'; say exactly what is unclear and why.\n" +
  "Format your response as a numbered list.";

const REVISE_SYSTEM =
  "You are a skilled writer. You will receive a task, a draft answer, and a critique.\n" +
  "Produce a revised answer that directly addresses every point in the critique. " +
  "Your revision should be complete and self-contained — do not reference the critique in your output.";

// ---------------------------------------------------------------------------
// TODO 1: Implement draft(taskPrompt).
//         Generate an initial answer to the task. Use temperature=0.7 so the
//         output is natural but not overly conservative.
//         Return the text of the draft.
// ---------------------------------------------------------------------------
async function draft(taskPrompt: string): Promise<string> {
  // const llm = getProvider();
  // const result = await llm.chat(
  //   [{ role: "user", content: taskPrompt }],
  //   { temperature: 0.7 },
  // );
  // return result.text;
  throw new Error("TODO: implement draft()");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement critique(taskPrompt, draftText).
//         Send a message with the critique system prompt + the task + the draft.
//         Return the critique text.
//         Use temperature=0 to keep the critique factual and repeatable.
// ---------------------------------------------------------------------------
async function critique(taskPrompt: string, draftText: string): Promise<string> {
  // const llm = getProvider();
  // const result = await llm.chat(
  //   [
  //     { role: "system", content: CRITIQUE_SYSTEM },
  //     { role: "user", content: `Task: ${taskPrompt}\n\nDraft answer:\n${draftText}` },
  //   ],
  //   { temperature: 0 },
  // );
  // return result.text;
  throw new Error("TODO: implement critique()");
}

// ---------------------------------------------------------------------------
// TODO 3: Implement revise(taskPrompt, draftText, critiqueText).
//         Send a message with the revise system prompt + task + draft + critique.
//         Return the revised text.
// ---------------------------------------------------------------------------
async function revise(
  taskPrompt: string,
  draftText: string,
  critiqueText: string,
): Promise<string> {
  // const llm = getProvider();
  // const result = await llm.chat(
  //   [
  //     { role: "system", content: REVISE_SYSTEM },
  //     {
  //       role: "user",
  //       content:
  //         `Task: ${taskPrompt}\n\n` +
  //         `Draft answer:\n${draftText}\n\n` +
  //         `Critique:\n${critiqueText}`,
  //     },
  //   ],
  //   { temperature: 0.3 },
  // );
  // return result.text;
  throw new Error("TODO: implement revise()");
}

// ---------------------------------------------------------------------------
// TODO 4: Implement compare(original, final).
//         A simple heuristic: length change, unique new words, changed at all.
//         Return an object. Replace with an LLM-as-judge call if you like.
// ---------------------------------------------------------------------------
function compare(
  original: string,
  final: string,
): { lengthDelta: number; newUniqueWords: number; changed: boolean } {
  // TODO: implement
  const lengthDelta = final.length - original.length;
  const originalWords = new Set(original.toLowerCase().split(/\s+/));
  const finalWords = new Set(final.toLowerCase().split(/\s+/));
  const newUniqueWords = [...finalWords].filter((w) => !originalWords.has(w)).length;
  return { lengthDelta, newUniqueWords, changed: original.trim() !== final.trim() };
}

function divider(label: string): void {
  console.log(`\n${"=".repeat(10)} ${label} ${"=".repeat(10)}`);
}

async function main() {
  console.log("=== Task 3: Self-Refine / Reflection ===\n");

  for (const task of TASKS) {
    console.log(`\nTask [${task.id}]: ${task.prompt}\n`);

    // -------------------------------------------------------------------------
    // TODO 5: Run the draft → critique → revise loop.
    //         1. Generate initial draft.
    //         2. For each iteration: critique the current draft, then revise it.
    //         3. Print each step so the reader can see the improvement.
    // -------------------------------------------------------------------------

    try {
      divider("DRAFT");
      let current = await draft(task.prompt);
      const original = current;
      console.log(current);

      for (let i = 1; i <= MAX_ITERATIONS; i++) {
        divider(`CRITIQUE (iteration ${i})`);
        const crit = await critique(task.prompt, current);
        console.log(crit);

        divider(`REVISION (iteration ${i})`);
        current = await revise(task.prompt, current, crit);
        console.log(current);
      }

      // -------------------------------------------------------------------------
      // TODO 6: Print a comparison between the original draft and final revision.
      // -------------------------------------------------------------------------
      divider("COMPARISON");
      const stats = compare(original, current);
      console.log(`  Length change     : ${stats.lengthDelta >= 0 ? "+" : ""}${stats.lengthDelta} chars`);
      console.log(`  New unique words  : ${stats.newUniqueWords}`);
      console.log(`  Changed at all?   : ${stats.changed}`);

    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ${msg}`);
    }

    console.log();
  }

  console.log(
    "Observation: self-refinement tends to add specificity and fix factual gaps.\n" +
    "Two iterations usually capture most of the gain."
  );
}

main().catch(console.error);
