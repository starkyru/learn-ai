/**
 * Task 1 🟢 — Decide: prompt vs fine-tune.
 *
 * What you'll learn:
 *   - A structured decision framework for when fine-tuning pays off
 *   - How to approximate fine-tuning via few-shot prompting
 *   - LLM-as-judge: using one LLM call to score another's output
 *
 * Key insight: few-shot is the cheapest approximation of fine-tuning. If
 * few-shot meets your quality bar, fine-tuning is probably not worth the
 * cost and complexity. Fine-tune when you have 100+ consistent examples,
 * a stable task, and need consistent format without per-call token overhead.
 *
 * How to run:
 *   pnpm tsx modules/13-fine-tuning/ts/01-decide.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Sample task: rewrite casual emails as formal business emails
// ---------------------------------------------------------------------------

const FEW_SHOT_EXAMPLES: [string, string][] = [
  [
    "hey can u send me the report asap thx",
    "Dear colleague, could you please send me the report at your earliest convenience? Thank you.",
  ],
  [
    "gonna be late to the meeting srry",
    "I apologise for the inconvenience, but I will be arriving to the meeting slightly late.",
  ],
  [
    "wtf is going on with the server its been down for hours",
    "I am writing to flag a critical issue: the server has been unavailable for several hours and requires immediate attention.",
  ],
  [
    "can we reschedule tmrw? something came up",
    "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen.",
  ],
  [
    "the numbers look good lmk if u need anything else",
    "The figures appear satisfactory. Please do not hesitate to reach out should you require any further information.",
  ],
];

const TEST_INPUTS = [
  "yo where is my invoice?? i need it now",
  "fyi the client is kinda unhappy with our progress",
  "can u double check the contract before we sign",
  "just wanted to say great work on the presentation!!",
  "heads up the deadline got moved to friday",
];

// ---------------------------------------------------------------------------
// Approach 1: system-prompt baseline
// ---------------------------------------------------------------------------

/**
 * Rewrite `text` as a formal business email using a system prompt only.
 *
 * TODO:
 *   1. Build a system message instructing the model to rewrite casual text as
 *      formal business English, preserving the meaning.
 *   2. Add a user message with `text`.
 *   3. Call provider.chat() with temperature: 0.2.
 *   4. Return result.text.trim().
 */
async function promptBaseline(
  text: string,
  provider: ReturnType<typeof getProvider>,
): Promise<string> {
  // TODO: implement promptBaseline
  throw new Error("TODO: implement promptBaseline()");
}

// ---------------------------------------------------------------------------
// Approach 2: mock fine-tuned (few-shot approximation)
// ---------------------------------------------------------------------------

/**
 * Rewrite `text` as a formal email using 5 (input, output) few-shot examples.
 *
 * TODO:
 *   1. Build a system message explaining the task.
 *   2. For each [informal, formal] pair in FEW_SHOT_EXAMPLES, add:
 *        { role: "user", content: informal }
 *        { role: "assistant", content: formal }
 *   3. Add a final { role: "user", content: text } query.
 *   4. Call provider.chat() with temperature: 0.
 *   5. Return result.text.trim().
 */
async function mockFineTuned(
  text: string,
  provider: ReturnType<typeof getProvider>,
): Promise<string> {
  // TODO: implement mockFineTuned
  throw new Error("TODO: implement mockFineTuned()");
}

// ---------------------------------------------------------------------------
// Evaluation: LLM-as-judge formality scorer
// ---------------------------------------------------------------------------

/**
 * Ask the LLM to rate the formality of `text` on a 1–5 scale.
 *
 * 1 = very informal / casual
 * 5 = highly formal business English
 *
 * TODO:
 *   1. Build a prompt asking the model to rate formality.
 *      Tell it to respond with ONLY a single digit (1–5).
 *   2. Call provider.chat() with temperature: 0.
 *   3. Find the first digit character in the response, return as number.
 *      Fallback to 3 if parsing fails.
 */
async function scoreFormality(
  text: string,
  provider: ReturnType<typeof getProvider>,
): Promise<number> {
  // TODO: implement scoreFormality
  throw new Error("TODO: implement scoreFormality()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const DECISION_GUIDE = `
WHEN TO FINE-TUNE (vs just prompting / adding examples)
=========================================================

Fine-tune when ALL of the following are true:
  1. You have 100+ high-quality, consistent (prompt, completion) pairs.
  2. The task definition is stable — it won't change monthly.
  3. You need the behaviour in EVERY call without few-shot token overhead.
  4. Output format must be extremely consistent.

Stick with prompting / few-shot when:
  - You have < 50 examples (fine-tune will overfit).
  - The task / labels change often.
  - You're still exploring — fine-tuning locks you in.
  - Few-shot already meets your quality bar (it often does!).

Use RAG instead when:
  - The model needs external/up-to-date facts, not a new SKILL.
  - Your "training data" is actually a document corpus.
`;

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (model: ${provider.chatModel})`);
  console.log(DECISION_GUIDE);

  console.log("=".repeat(70));
  console.log("COMPARISON TABLE — formality scores (1=casual, 5=formal)");
  console.log("=".repeat(70));
  console.log(`${"INPUT".padEnd(40)} ${"BASELINE".padStart(9)} ${"FEW-SHOT".padStart(9)}`);
  console.log("-".repeat(70));

  for (const raw of TEST_INPUTS) {
    const baselineOut = await promptBaseline(raw, provider);
    const fewshotOut = await mockFineTuned(raw, provider);
    const baselineScore = await scoreFormality(baselineOut, provider);
    const fewshotScore = await scoreFormality(fewshotOut, provider);
    const short = raw.length > 38 ? raw.slice(0, 37) + "…" : raw;
    console.log(`${short.padEnd(40)} ${String(baselineScore).padStart(9)} ${String(fewshotScore).padStart(9)}`);
  }

  console.log("-".repeat(70));
  console.log(
    "\nReflection: if few-shot scores are similar to baseline, don't bother fine-tuning.",
    "\nIf few-shot clearly wins, that gap is what a real fine-tune would lock in permanently.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
