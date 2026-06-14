/**
 * Task 2 — Test-time compute without a reasoning model 🟡
 *
 * What this teaches:
 *   - You don't need a special reasoning model to get better answers — you can
 *     spend more compute at inference time using a standard model and these techniques:
 *       * Self-consistency: sample the same CoT prompt N times, majority-vote the final answer.
 *       * Best-of-N + verifier: sample N answers, score with a cheap verifier, pick the best.
 *   - Accuracy rises with N — but so does cost. The verifier is the key to efficiency.
 *   - Implementing these by hand teaches you exactly what "test-time compute" means.
 *
 * How to run:
 *   pnpm tsx modules/15-reasoning-test-time-compute/ts/02-test-time-compute.ts
 */

import "dotenv/config";
import { getProvider, ChatMessage, ChatOptions } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Test problems with verifiable answers.
// ---------------------------------------------------------------------------
const PROBLEMS = [
  {
    question: "What is 17 × 24? Show your working.",
    answer: "408",
  },
  {
    question:
      "A bat and a ball cost $1.10 in total. " +
      "The bat costs $1.00 more than the ball. " +
      "How much does the ball cost? Give the answer in cents.",
    answer: "5",
  },
  {
    question:
      "If you have a 3-litre jug and a 5-litre jug, how do you measure " +
      "exactly 4 litres of water? List the steps.",
    answer: "4",
  },
];

const N_SAMPLES = 3;

const COT_SYSTEM =
  "You are a careful problem solver. " +
  "Think step by step, then end your response with: " +
  "'Final answer: <your answer>'";

interface RunStats {
  strategy: string;
  correct: number;
  total: number;
  inputTokens: number;
  outputTokens: number;
}

// ---------------------------------------------------------------------------
// TODO 1: Implement extractFinalAnswer.
//         Parse "Final answer: X" from the CoT response.
//         Strip punctuation and whitespace from the extracted value.
//         Fall back to the last non-empty line if the pattern is not found.
// ---------------------------------------------------------------------------
function extractFinalAnswer(text: string): string {
  // const match = text.match(/[Ff]inal answer[:\s]+(.+)/);
  // if (match) return match[1].trim().replace(/[.,!?]+$/, "");
  // return text.trim().split("\n").filter(Boolean).at(-1)?.trim() ?? text.trim();

  // TODO: implement properly
  return text.trim().split("\n").filter(Boolean).at(-1)?.trim() ?? text.trim();
}

// ---------------------------------------------------------------------------
// TODO 2: Implement majorityVote.
//         Given an array of answer strings, return the most common one.
//         Normalise: lowercase, trim, remove trailing punctuation.
// ---------------------------------------------------------------------------
function majorityVote(answers: string[]): string {
  // TODO: implement
  const normalised = answers.map((a) => a.toLowerCase().trim().replace(/[.,!?]+$/, ""));
  const counts = new Map<string, number>();
  for (const a of normalised) counts.set(a, (counts.get(a) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

// ---------------------------------------------------------------------------
// TODO 3: Implement singleShot.
//         One CoT call at temperature=0. Return [answer, inputTokens, outputTokens].
// ---------------------------------------------------------------------------
async function singleShot(question: string): Promise<[string, number, number]> {
  // const llm = getProvider();
  // const result = await llm.chat(
  //   [{ role: "system", content: COT_SYSTEM }, { role: "user", content: question }],
  //   { temperature: 0 },
  // );
  // const answer = extractFinalAnswer(result.text);
  // return [answer, result.usage?.inputTokens ?? 0, result.usage?.outputTokens ?? 0];
  throw new Error("TODO: implement singleShot");
}

// ---------------------------------------------------------------------------
// TODO 4: Implement selfConsistency.
//         Sample `n` CoT completions at temperature=0.8.
//         Extract the final answer from each.
//         Return [majorityVote(answers), totalInputTokens, totalOutputTokens].
// ---------------------------------------------------------------------------
async function selfConsistency(
  question: string,
  n: number = N_SAMPLES,
): Promise<[string, number, number]> {
  // const llm = getProvider();
  // const answers: string[] = [];
  // let inTok = 0, outTok = 0;
  // for (let i = 0; i < n; i++) {
  //   const result = await llm.chat(
  //     [{ role: "system", content: COT_SYSTEM }, { role: "user", content: question }],
  //     { temperature: 0.8 },
  //   );
  //   answers.push(extractFinalAnswer(result.text));
  //   inTok += result.usage?.inputTokens ?? 0;
  //   outTok += result.usage?.outputTokens ?? 0;
  // }
  // return [majorityVote(answers), inTok, outTok];
  throw new Error("TODO: implement selfConsistency");
}

// ---------------------------------------------------------------------------
// TODO 5: Implement verify.
//         Ask the model: "Is '<answer>' the correct answer to '<question>'?
//         Reply with only YES or NO."
//         Return true if the model responds with YES.
// ---------------------------------------------------------------------------
async function verify(question: string, answer: string): Promise<boolean> {
  // const llm = getProvider();
  // const prompt =
  //   `Question: ${question}\nProposed answer: ${answer}\n` +
  //   "Is this answer correct? Reply with only YES or NO.";
  // const result = await llm.chat([{ role: "user", content: prompt }], { temperature: 0 });
  // return result.text.trim().toUpperCase().startsWith("YES");
  throw new Error("TODO: implement verify");
}

// ---------------------------------------------------------------------------
// TODO 6: Implement bestOfN.
//         Sample `n` CoT answers at temperature=0.8.
//         Run verify() on each in order; return the first approved answer.
//         If none are approved, fall back to majorityVote of all candidates.
//         Return [answer, totalInputTokens, totalOutputTokens].
// ---------------------------------------------------------------------------
async function bestOfN(
  question: string,
  n: number = N_SAMPLES,
): Promise<[string, number, number]> {
  throw new Error("TODO: implement bestOfN");
}

function isCorrect(answer: string, expected: string): boolean {
  return answer.toLowerCase().includes(expected.toLowerCase());
}

async function main() {
  console.log("=== Task 2: Test-Time Compute (no reasoning model) ===\n");

  const strategies: RunStats[] = [
    { strategy: "single-shot CoT", correct: 0, total: 0, inputTokens: 0, outputTokens: 0 },
    { strategy: `self-consistency (N=${N_SAMPLES})`, correct: 0, total: 0, inputTokens: 0, outputTokens: 0 },
    { strategy: `best-of-N (N=${N_SAMPLES})`, correct: 0, total: 0, inputTokens: 0, outputTokens: 0 },
  ];

  for (const problem of PROBLEMS) {
    console.log(`Q: ${problem.question.slice(0, 70)}... (expected: ${problem.answer})`);

    // -------------------------------------------------------------------------
    // TODO 7: For each problem, call singleShot, selfConsistency, and bestOfN.
    //         Update the corresponding RunStats.
    //         Wrap each in try/catch so a not-yet-implemented strategy prints a placeholder.
    // -------------------------------------------------------------------------

    const fns = [
      async () => singleShot(problem.question),
      async () => selfConsistency(problem.question, N_SAMPLES),
      async () => bestOfN(problem.question, N_SAMPLES),
    ];

    for (let i = 0; i < fns.length; i++) {
      const stats = strategies[i];
      try {
        const [answer, inTok, outTok] = await fns[i]();
        const correct = isCorrect(answer, problem.answer);
        stats.correct += correct ? 1 : 0;
        stats.total += 1;
        stats.inputTokens += inTok;
        stats.outputTokens += outTok;
        const mark = correct ? "✓" : "✗";
        console.log(
          `  [${stats.strategy.padEnd(28)}] ${mark}  answer=${JSON.stringify(answer).padEnd(30)}  tokens=${inTok + outTok}`
        );
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        console.log(`  [${stats.strategy.padEnd(28)}] ${msg.startsWith("TODO") ? "TODO: not yet implemented" : "ERROR: " + msg}`);
      }
    }
    console.log();
  }

  // -------------------------------------------------------------------------
  // TODO 8: Print a summary table: strategy | correct/total | accuracy | total tokens.
  // -------------------------------------------------------------------------
  console.log("\n--- Summary ---");
  console.log(
    "Strategy".padEnd(32) + "Correct".padStart(9) + "Accuracy".padStart(11) + "Total tokens".padStart(15)
  );
  console.log("-".repeat(70));
  for (const s of strategies) {
    const totalTok = s.inputTokens + s.outputTokens;
    const accStr = s.total > 0 ? `${Math.round((s.correct / s.total) * 100)}%` : "n/a";
    const correctStr = s.total > 0 ? `${s.correct}/${s.total}` : "n/a";
    console.log(
      s.strategy.padEnd(32) + correctStr.padStart(9) + accStr.padStart(11) + String(totalTok).padStart(15)
    );
  }

  console.log();
  console.log(
    "Observation: accuracy should rise with N, but so does token cost.\n" +
    "The verifier in best-of-N is the key to spending wisely."
  );
}

main().catch(console.error);
