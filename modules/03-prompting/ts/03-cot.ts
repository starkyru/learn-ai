/**
 * Task 3 — Chain-of-thought & self-consistency 🟡
 *
 * What this teaches:
 *   - Chain-of-thought (CoT): ask the model to "think step by step" before
 *     giving the final answer. For reasoning tasks this dramatically improves
 *     accuracy because the model can't skip steps that it would otherwise hide.
 *   - Self-consistency: sample the same CoT prompt N times (temperature > 0)
 *     and majority-vote the final answer. Individual samples may reach the
 *     wrong answer via different reasoning paths; voting averages out noise.
 *   - The trade-off: CoT uses more output tokens (= higher cost) and
 *     self-consistency multiplies that by N. Use sparingly on hard tasks.
 *
 * How to run:
 *   pnpm tsx modules/03-prompting/ts/03-cot.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Sample problems — grade-school math and logical reasoning.
// These are hard enough to benefit from CoT but easy to verify.
// ---------------------------------------------------------------------------
const PROBLEMS = [
  {
    question: "A shop sells apples for $0.50 each and bananas for $0.30 each. " +
      "Alice buys 4 apples and 6 bananas. How much does she pay in total?",
    answer: "3.80",
  },
  {
    question: "If all Bloops are Razzies and all Razzies are Lazzies, " +
      "are all Bloops definitely Lazzies?",
    answer: "yes",
  },
  {
    question: "A train travels 60 km in 45 minutes. What is its speed in km/h?",
    answer: "80",
  },
];

// ---------------------------------------------------------------------------
// TODO 1: Write a zero-shot prompt (no CoT) that asks for only the final answer.
//         Keep it short. The model should respond with JUST the answer, no explanation.
// ---------------------------------------------------------------------------
function buildDirectPrompt(question: string): string {
  // TODO: return a prompt that instructs the model to answer directly.
  // Example: "Answer the following question with only the final answer, no explanation.\n\nQuestion: ..."
  return `TODO: build direct (non-CoT) prompt for: ${question}`;
}

// ---------------------------------------------------------------------------
// TODO 2: Write a chain-of-thought prompt.
//         Include "Let's think step by step" (or a more natural variant).
//         The response should contain reasoning AND a clearly marked final answer.
//         Example format: "... therefore the answer is [ANSWER]."
//         Alternatively: ask for a specific answer line at the end:
//         "At the end, write: Final answer: <your answer>"
// ---------------------------------------------------------------------------
function buildCoTPrompt(question: string): string {
  // TODO: return a CoT prompt.
  return `TODO: build CoT prompt for: ${question}`;
}

// ---------------------------------------------------------------------------
// TODO 3: Implement extractFinalAnswer.
//         Parse the model's CoT response to extract just the final answer.
//         Your extraction logic should match the format you chose in TODO 2.
//         For "Final answer: X" format: /[Ff]inal answer:\s*(.+)/
//         For "the answer is X" format: /the answer is\s*([\d.]+|yes|no)/i
//         Trim whitespace and lowercase the result.
// ---------------------------------------------------------------------------
function extractFinalAnswer(cotResponse: string): string {
  // TODO: implement extraction matching your CoT prompt format
  return cotResponse.trim().split("\n").pop() ?? "";
}

// ---------------------------------------------------------------------------
// TODO 4: Implement majorityVote.
//         Given a list of answers (strings), return the most common one.
//         If there's a tie, return any of the tied answers.
//         Normalise before comparing: lowercase + trim.
// ---------------------------------------------------------------------------
function majorityVote(answers: string[]): string {
  // TODO: implement
  const counts = new Map<string, number>();
  for (const a of answers) {
    const key = a.toLowerCase().trim();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  // return the key with the highest count
  return "TODO";
}

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);

  const N_SAMPLES = 3; // number of self-consistency samples

  for (const { question, answer: expected } of PROBLEMS) {
    console.log(`\nQ: ${question}`);
    console.log(`Expected: ${expected}\n`);

    // -----------------------------------------------------------------------
    // TODO 5: Zero-shot direct answer.
    //         Call llm.chat with the direct prompt. Print result.
    // -----------------------------------------------------------------------
    // const directResult = await llm.chat([{ role: "user", content: buildDirectPrompt(question) }]);
    // console.log(`Direct (0-shot): ${directResult.text.trim()}`);
    console.log("Direct (0-shot): TODO");

    // -----------------------------------------------------------------------
    // TODO 6: Single CoT sample.
    //         Call llm.chat with the CoT prompt at temperature=0 (deterministic).
    //         Extract and print the final answer.
    // -----------------------------------------------------------------------
    // const cotResult = await llm.chat(
    //   [{ role: "user", content: buildCoTPrompt(question) }],
    //   { temperature: 0 }
    // );
    // const cotAnswer = extractFinalAnswer(cotResult.text);
    // console.log(`CoT (single):   ${cotAnswer}`);
    // console.log("Reasoning snippet:", cotResult.text.slice(0, 200) + "...");
    console.log("CoT (single):   TODO");

    // -----------------------------------------------------------------------
    // TODO 7: Self-consistency — sample N_SAMPLES CoT responses at temperature=0.7,
    //         extract each answer, majority vote, print all samples + winner.
    // -----------------------------------------------------------------------
    // const samples: string[] = [];
    // for (let i = 0; i < N_SAMPLES; i++) {
    //   const r = await llm.chat(
    //     [{ role: "user", content: buildCoTPrompt(question) }],
    //     { temperature: 0.7 }
    //   );
    //   samples.push(extractFinalAnswer(r.text));
    // }
    // const winner = majorityVote(samples);
    // console.log(`Self-consistency: samples=${JSON.stringify(samples)}, vote=${winner}`);
    console.log(`Self-consistency (N=${N_SAMPLES}): TODO`);
  }

  // -------------------------------------------------------------------------
  // TODO 8 (stretch): Count total output tokens used by direct vs CoT vs
  //         self-consistency across all problems. CoT is more accurate but at
  //         what token cost? Print a comparison.
  // -------------------------------------------------------------------------
}

main().catch(console.error);
