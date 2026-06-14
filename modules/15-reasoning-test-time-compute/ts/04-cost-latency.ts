/**
 * Task 4 — Cost / latency of reasoning strategies 🟢
 *
 * What this teaches:
 *   - Making the test-time compute trade-off concrete: measure tokens used, wall time,
 *     and accuracy for each strategy on a fixed benchmark.
 *   - Estimated cost lets you compare "accuracy per dollar" and find the sweet spot.
 *   - This is the culminating exercise for the module — pull everything together.
 *
 * How to run:
 *   pnpm tsx modules/15-reasoning-test-time-compute/ts/04-cost-latency.ts
 *
 * Note: strategies that call Tasks 1–3 will throw if not yet implemented — those
 *       rows are skipped gracefully.
 */

import "dotenv/config";
import { getProvider, ChatMessage, ChatOptions } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Price table — $ per 1,000,000 tokens (update as prices change).
// ---------------------------------------------------------------------------
const PRICE_TABLE: Record<string, { inputPer1M: number; outputPer1M: number }> = {
  "gpt-4o-mini":       { inputPer1M: 0.15,  outputPer1M: 0.60 },
  "gpt-4o":            { inputPer1M: 5.00,  outputPer1M: 15.00 },
  "o4-mini":           { inputPer1M: 1.10,  outputPer1M: 4.40 },
  "claude-opus-4-8":   { inputPer1M: 15.00, outputPer1M: 75.00 },
  "claude-haiku-4-5":  { inputPer1M: 0.80,  outputPer1M: 4.00 },
  default:             { inputPer1M: 0.50,  outputPer1M: 1.50 },
};

// ---------------------------------------------------------------------------
// Benchmark problems (fixed set — fair comparison across strategies).
// ---------------------------------------------------------------------------
const BENCHMARK = [
  { question: "What is 23 × 47? Show your working.", answer: "1081" },
  {
    question:
      "A snail climbs 3 metres up a wall each day and slips back 2 metres " +
      "each night. The wall is 10 metres tall. How many days to reach the top?",
    answer: "8",
  },
  {
    question:
      "Alice is taller than Bob. Bob is taller than Carol. " +
      "Is Alice taller than Carol? Give only YES or NO and one sentence of reasoning.",
    answer: "yes",
  },
];

interface BenchmarkResult {
  strategy: string;
  model: string;
  correct: number;
  total: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  totalLatencyMs: number;
}

function estimatedCost(r: BenchmarkResult): number {
  const prices = PRICE_TABLE[r.model] ?? PRICE_TABLE["default"];
  return (
    (r.totalInputTokens / 1_000_000) * prices.inputPer1M +
    (r.totalOutputTokens / 1_000_000) * prices.outputPer1M
  );
}

function accuracyPerDollar(r: BenchmarkResult): number {
  const cost = estimatedCost(r);
  if (cost === 0) return Infinity;
  return (r.correct / r.total) / cost;
}

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------
const COT_SYSTEM = "Think step by step. End with 'Final answer: <answer>'";

function extractFinalAnswer(text: string): string {
  const match = text.match(/[Ff]inal answer[:\s]+(.+)/);
  if (match) return match[1].trim().replace(/[.,!?]+$/, "");
  return text.trim().split("\n").filter(Boolean).at(-1)?.trim() ?? text.trim();
}

function isCorrect(answer: string, expected: string): boolean {
  return answer.toLowerCase().includes(expected.toLowerCase());
}

function emptyResult(strategy: string, model: string): BenchmarkResult {
  return { strategy, model, correct: 0, total: 0, totalInputTokens: 0, totalOutputTokens: 0, totalLatencyMs: 0 };
}

// ---------------------------------------------------------------------------
// TODO 1: Implement runZeroShot(benchmark).
//         One chat call per problem, no CoT, temperature=0.
//         Record tokens and latency.
// ---------------------------------------------------------------------------
async function runZeroShot(
  benchmark: typeof BENCHMARK,
): Promise<BenchmarkResult> {
  const llm = getProvider();
  const result = emptyResult("zero-shot", llm.chatModel);
  for (const p of benchmark) {
    // TODO: call llm.chat, record usage and latency, check correctness
    result.total += 1;
  }
  return result;
}

// ---------------------------------------------------------------------------
// TODO 2: Implement runCoT(benchmark).
//         One CoT call at temperature=0 per problem. Extract final answer.
// ---------------------------------------------------------------------------
async function runCoT(benchmark: typeof BENCHMARK): Promise<BenchmarkResult> {
  const llm = getProvider();
  const result = emptyResult("CoT (single)", llm.chatModel);
  for (const p of benchmark) {
    // TODO: call llm.chat with CoT system prompt, record usage and latency
    result.total += 1;
  }
  return result;
}

// ---------------------------------------------------------------------------
// TODO 3: Implement runSelfConsistency(benchmark, n=3).
//         N samples at temperature=0.8, majority vote per problem.
// ---------------------------------------------------------------------------
async function runSelfConsistency(
  benchmark: typeof BENCHMARK,
  n = 3,
): Promise<BenchmarkResult> {
  const llm = getProvider();
  const result = emptyResult(`self-consistency (N=${n})`, llm.chatModel);
  for (const p of benchmark) {
    // TODO: sample N times, majority vote, record aggregate tokens and latency
    result.total += 1;
  }
  return result;
}

// ---------------------------------------------------------------------------
// TODO 4: Implement runSelfRefine(benchmark, iterations=2).
//         Draft → critique → revise loop. Score the final revision.
// ---------------------------------------------------------------------------
async function runSelfRefine(
  benchmark: typeof BENCHMARK,
  iterations = 2,
): Promise<BenchmarkResult> {
  const llm = getProvider();
  const result = emptyResult(`self-refine (${iterations} iter)`, llm.chatModel);
  for (const p of benchmark) {
    // TODO: implement the refine loop, score final answer
    result.total += 1;
  }
  return result;
}

// ---------------------------------------------------------------------------
// TODO 5 (stretch): Implement runReasoningModel(benchmark).
//         Call OpenAI o4-mini or Anthropic extended thinking directly via SDK.
//         Use the correct model name so the price lookup works.
// ---------------------------------------------------------------------------
async function runReasoningModel(
  benchmark: typeof BENCHMARK,
): Promise<BenchmarkResult> {
  const result = emptyResult("reasoning model", "o4-mini");
  for (const p of benchmark) {
    result.total += 1;
  }
  return result;
}

function printTable(results: BenchmarkResult[]): void {
  const sorted = [...results].sort((a, b) => estimatedCost(a) - estimatedCost(b));
  console.log(
    "\n" +
    "Strategy".padEnd(30) + "Model".padEnd(20) + "Acc".padStart(6) +
    "In tok".padStart(9) + "Out tok".padStart(9) +
    "Latency ms".padStart(12) + "Est. cost $".padStart(13) + "Acc/$".padStart(11)
  );
  console.log("-".repeat(110));
  for (const r of sorted) {
    if (r.total === 0) continue;
    const acc = `${Math.round((r.correct / r.total) * 100)}%`;
    const cost = estimatedCost(r);
    const apd = cost > 0 ? accuracyPerDollar(r).toFixed(1) : "inf";
    console.log(
      r.strategy.padEnd(30) +
      r.model.padEnd(20) +
      acc.padStart(6) +
      String(r.totalInputTokens).padStart(9) +
      String(r.totalOutputTokens).padStart(9) +
      r.totalLatencyMs.toFixed(0).padStart(12) +
      cost.toFixed(6).padStart(13) +
      apd.padStart(11)
    );
  }

  const valid = sorted.filter((r) => r.total > 0 && estimatedCost(r) > 0);
  if (valid.length > 0) {
    const best = valid.reduce((a, b) =>
      accuracyPerDollar(a) >= accuracyPerDollar(b) ? a : b
    );
    console.log(`\nSweet spot (best accuracy per $): "${best.strategy}"`);
  }
}

async function main() {
  console.log("=== Task 4: Cost / Latency of Reasoning Strategies ===");
  console.log(`Benchmark: ${BENCHMARK.length} problems\n`);

  // -------------------------------------------------------------------------
  // TODO 6: Call each run* function and collect results.
  //         Wrap each in try/catch — errors should skip gracefully.
  // -------------------------------------------------------------------------

  const strategies = [
    () => runZeroShot(BENCHMARK),
    () => runCoT(BENCHMARK),
    () => runSelfConsistency(BENCHMARK, 3),
    () => runSelfRefine(BENCHMARK, 2),
    () => runReasoningModel(BENCHMARK),
  ];

  const results: BenchmarkResult[] = [];
  for (const fn of strategies) {
    try {
      const r = await fn();
      results.push(r);
      const status = r.total > 0 ? `${r.correct}/${r.total}` : "skipped";
      console.log(`  ${r.strategy.padEnd(30)} done (${status})`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ERROR running strategy: ${msg}`);
    }
  }

  printTable(results);

  console.log(
    "\nObservation: the 'sweet spot' balances accuracy and cost.\n" +
    "For cheap/simple tasks zero-shot wins. For high-stakes tasks\n" +
    "the reasoning model (or self-consistency-5) is worth the premium."
  );
}

main().catch(console.error);
