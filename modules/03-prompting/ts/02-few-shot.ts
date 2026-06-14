/**
 * Task 2 — Few-shot vs zero-shot 🟡
 *
 * What this teaches:
 *   - Zero-shot: just the task description — the model must generalise from
 *     its training alone.
 *   - Few-shot: task description + k labelled examples before the actual
 *     input — the model "reads the pattern" from them.
 *   - In general, more examples → better accuracy BUT: more tokens, more
 *     cost, and diminishing returns beyond ~5-10 examples.
 *   - The quality of examples matters more than quantity. One well-chosen
 *     example can outperform three mediocre ones.
 *
 * How to run:
 *   pnpm tsx modules/03-prompting/ts/02-few-shot.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Task: sentiment classification (positive / negative / neutral).
// We deliberately pick a simple task so you can evaluate accuracy by eye.
// ---------------------------------------------------------------------------

const TEST_INPUTS = [
  "I love this product! Works exactly as described.",
  "Absolute garbage. Broke after one day.",
  "It's fine. Does what it says.",
  "Incredible quality. Will buy again.",
  "Disappointed. Not worth the price.",
];

// ---------------------------------------------------------------------------
// TODO 1: Define the few-shot examples.
//         Each example is a {input, label} pair. These will be injected into
//         the prompt as user/assistant pairs (the standard few-shot format).
//         Start with ONE example and then try THREE — do you see a difference?
// ---------------------------------------------------------------------------
const FEW_SHOT_EXAMPLES = [
  // { input: "...", label: "positive" },
  // { input: "...", label: "negative" },
  // { input: "...", label: "neutral" },
];

// ---------------------------------------------------------------------------
// TODO 2: Implement buildZeroShotMessages.
//         Return a messages array with:
//           - system: "You are a sentiment classifier. Respond with exactly one
//             word: positive, negative, or neutral."
//           - user: the input text
//         No examples.
// ---------------------------------------------------------------------------
function buildZeroShotMessages(input: string) {
  // TODO: return [{ role: "system", content: "..." }, { role: "user", content: input }]
  return [] as { role: string; content: string }[];
}

// ---------------------------------------------------------------------------
// TODO 3: Implement buildFewShotMessages.
//         Build messages with the same system prompt, then insert the examples
//         as alternating user/assistant pairs before the final user message.
//         Structure:
//           system
//           user: example1.input
//           assistant: example1.label
//           user: example2.input  (if k >= 2)
//           assistant: example2.label
//           ...
//           user: input  ← the actual query
// ---------------------------------------------------------------------------
function buildFewShotMessages(input: string, examples: typeof FEW_SHOT_EXAMPLES) {
  // TODO: implement
  return [] as { role: string; content: string }[];
}

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);
  console.log("Comparing zero-shot vs few-shot sentiment classification\n");
  console.log("Input".padEnd(55) + "0-shot".padEnd(12) + "1-shot".padEnd(12) + "3-shot");
  console.log("-".repeat(90));

  for (const input of TEST_INPUTS) {
    // -------------------------------------------------------------------------
    // TODO 4: For each input, make three calls:
    //   - Zero-shot (no examples)
    //   - One-shot (first example from FEW_SHOT_EXAMPLES)
    //   - Three-shot (first three examples)
    //   Trim whitespace and lowercase the result.
    //   Print all three results in a table row.
    // -------------------------------------------------------------------------

    // const zeroShot = await llm.chat(buildZeroShotMessages(input) as any);
    // const oneShot  = await llm.chat(buildFewShotMessages(input, FEW_SHOT_EXAMPLES.slice(0, 1)) as any);
    // const threeShot = await llm.chat(buildFewShotMessages(input, FEW_SHOT_EXAMPLES.slice(0, 3)) as any);
    // const truncated = input.length > 50 ? input.slice(0, 47) + "..." : input;
    // console.log(truncated.padEnd(55) + zeroShot.text.trim().padEnd(12) + oneShot.text.trim().padEnd(12) + threeShot.text.trim());

    const truncated = input.length > 50 ? input.slice(0, 47) + "..." : input;
    console.log(truncated.padEnd(55) + "TODO".padEnd(12) + "TODO".padEnd(12) + "TODO");
  }

  console.log(`
Observations:
- Do the results differ between 0-shot and 3-shot?
- Does the model follow the "one word only" instruction in all cases?
- Which examples were most effective?
(Fill in your observations here after running)
`);

  // -------------------------------------------------------------------------
  // TODO 5 (stretch): Count tokens for each variant and compute the cost
  //         increase of adding examples. At what point does few-shot become
  //         too expensive for your use case?
  // -------------------------------------------------------------------------
}

main().catch(console.error);
