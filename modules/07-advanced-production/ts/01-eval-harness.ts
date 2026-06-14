/**
 * Task 1 — Eval harness + LLM-as-judge 🟡
 *
 * What this teaches:
 *   - You can't improve what you can't measure. An eval harness runs your
 *     system over a fixed test set and grades each output.
 *   - LLM-as-judge: instead of hand-writing rubrics with regex, you ask a
 *     second LLM call to score the output against a rubric. This is how
 *     production teams evaluate open-ended generation quality.
 *   - Aggregating pass rates and average scores lets you track regressions
 *     and improvements across model/prompt changes.
 *
 * How to run:
 *   pnpm tsx modules/07-advanced-production/ts/01-eval-harness.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Test cases — each has an input and a grading rubric
// ---------------------------------------------------------------------------

interface TestCase {
  id: string;
  input: string;        // the user question to feed to the system
  rubric: string;       // what a good answer should contain / accomplish
}

// TODO 1: Add at least 5 test cases that cover different quality dimensions:
//   - factual accuracy (does the answer contain the right fact?)
//   - instruction following (does it do what was asked?)
//   - conciseness (does it stay within a length limit?)
//   - safety (does it refuse an inappropriate request?)
const TEST_CASES: TestCase[] = [
  {
    id: "tc-01",
    input: "What is the capital of France?",
    rubric: "The answer must mention Paris as the capital of France.",
  },
  {
    id: "tc-02",
    input: "Explain recursion in one sentence.",
    rubric:
      "The answer must be a single sentence and capture the self-referential nature of recursion.",
  },
  // TODO: add 3+ more test cases
];

// ---------------------------------------------------------------------------
// System under test — the LLM pipeline being evaluated
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT =
  "You are a concise, accurate assistant. Answer in as few words as possible.";

async function runSystem(userInput: string): Promise<string> {
  const llm = getProvider();

  // TODO 2: Call llm.chat() with SYSTEM_PROMPT + the user input.
  //         Return the result text.

  throw new Error("TODO: implement runSystem");
}

// ---------------------------------------------------------------------------
// LLM-as-judge
// ---------------------------------------------------------------------------

interface JudgeScore {
  score: number;        // 0–10
  pass: boolean;        // score >= PASS_THRESHOLD
  reasoning: string;   // one sentence explaining the score
}

const PASS_THRESHOLD = 7;

const JUDGE_SYSTEM_PROMPT = `You are an impartial evaluator. You will receive:
  - A user question
  - The rubric (criteria for a good answer)
  - The system's actual answer

Score the answer from 0 to 10 based on how well it satisfies the rubric.
Respond ONLY in this JSON format (no prose, no markdown fences):
{"score": <0-10>, "pass": <true|false>, "reasoning": "<one sentence>"}

pass is true if score >= ${PASS_THRESHOLD}.`;

async function judgeOutput(
  question: string,
  rubric: string,
  answer: string
): Promise<JudgeScore> {
  const llm = getProvider();

  // TODO 3: Build a user message with the question, rubric, and answer clearly
  //         labelled. Call llm.chat() with JUDGE_SYSTEM_PROMPT. Parse the JSON
  //         response into a JudgeScore. Handle parse errors gracefully (return
  //         score 0 with a "parse error" reasoning).

  throw new Error("TODO: implement judgeOutput");
}

// ---------------------------------------------------------------------------
// Harness — runs all test cases and aggregates results
// ---------------------------------------------------------------------------

interface EvalResult {
  testCase: TestCase;
  answer: string;
  score: JudgeScore;
  latencyMs: number;
}

async function runEval(): Promise<void> {
  const llm = getProvider();
  console.log(`\nEval harness | provider: ${llm.name} / ${llm.chatModel}`);
  console.log(`Test cases: ${TEST_CASES.length}\n`);
  console.log("=".repeat(70));

  const results: EvalResult[] = [];

  for (const tc of TEST_CASES) {
    const t0 = performance.now();

    // TODO 4: Call runSystem(tc.input) to get the answer.
    //         Call judgeOutput(tc.input, tc.rubric, answer) to score it.
    //         Record latency = performance.now() - t0.
    //         Print a one-line summary per test case:
    //           [tc-01] PASS 8/10  "What is the capital of France?"  (142 ms)

    console.log(`TODO: run test case ${tc.id}`);
  }

  // TODO 5: After all test cases, print a summary:
  //   - Pass rate: X/Y (Z%)
  //   - Average score: N.N / 10
  //   - Average latency: N ms
  //   - List any FAIL cases with their reasoning

  console.log("\n--- Summary ---");
  console.log("TODO: aggregate and print results.");
}

runEval().catch(console.error);
