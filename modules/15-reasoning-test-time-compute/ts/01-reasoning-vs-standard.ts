/**
 * Task 1 — Reasoning vs standard model 🟢
 *
 * What this teaches:
 *   - Reasoning / extended-thinking models spend extra compute at inference time
 *     before producing visible output. This costs more but often yields better
 *     correctness on hard multi-step problems.
 *   - You will measure the difference concretely: answer quality, token counts,
 *     and wall-clock latency.
 *   - This file goes BEYOND llm-core because extended thinking and OpenAI reasoning
 *     models require provider-specific SDK parameters the abstraction does not expose.
 *     That is intentional: the leak teaches you where the abstraction breaks.
 *
 * Environment variables:
 *   OPENAI_API_KEY          — required for the OpenAI path
 *   OPENAI_CHAT_MODEL       — standard model (default: gpt-4o-mini)
 *   OPENAI_REASONING_MODEL  — reasoning model (default: o4-mini)
 *   ANTHROPIC_API_KEY       — required for the Anthropic extended-thinking path
 *   ANTHROPIC_MODEL         — base model (default: claude-opus-4-8)
 *
 * How to run:
 *   pnpm tsx modules/15-reasoning-test-time-compute/ts/01-reasoning-vs-standard.ts
 */

import "dotenv/config";
import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Test problems — hard enough that extra reasoning helps.
// ---------------------------------------------------------------------------
const PROBLEMS = [
  {
    id: "math",
    question:
      "A farmer has 17 sheep. All but 9 die. How many sheep are left? " +
      "Now, separately: if it takes 1.5 hours to boil 1 egg, how long does " +
      "it take to boil 3 eggs simultaneously in the same pot? " +
      "Give both answers and explain your reasoning.",
    expectedContains: ["9", "1.5"],
  },
  {
    id: "logic",
    question:
      "A doctor has a brother who is a lawyer. The lawyer's sister is a " +
      "surgeon. The surgeon has no siblings. How is this possible? " +
      "Explain step by step.",
    expectedContains: ["doctor"],
  },
  {
    id: "multi-step",
    question:
      "Alice, Bob, and Carol each have some apples. Alice has twice as many " +
      "as Bob. Carol has 3 fewer than Alice. Together they have 29 apples. " +
      "How many does each person have?",
    expectedContains: [],
  },
];

interface ModelResult {
  model: string;
  strategy: string;
  answer: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
}

// ---------------------------------------------------------------------------
// TODO 1: Implement callStandard.
//         Use getProvider("openai") from llm-core with the standard chat model.
//         Record start/end time for latency; return a ModelResult.
//         Hint: result.usage has inputTokens and outputTokens.
// ---------------------------------------------------------------------------
async function callStandard(question: string): Promise<ModelResult> {
  // const llm = getProvider("openai");
  // const start = performance.now();
  // const result = await llm.chat([{ role: "user", content: question }]);
  // const latencyMs = performance.now() - start;
  // return {
  //   model: result.model,
  //   strategy: "standard",
  //   answer: result.text,
  //   inputTokens: result.usage?.inputTokens ?? 0,
  //   outputTokens: result.usage?.outputTokens ?? 0,
  //   latencyMs,
  // };
  throw new Error("TODO: implement callStandard");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement callReasoningOpenAI.
//         Use the openai SDK directly (NOT llm-core) so you can pass
//         `reasoning_effort` and `max_completion_tokens`.
//
//         Key differences from a standard call:
//         - model: process.env.OPENAI_REASONING_MODEL ?? "o4-mini"
//         - Use max_completion_tokens instead of max_tokens
//         - Pass reasoning_effort: "medium" (or "high" for harder problems)
//         - usage.completion_tokens_details shows reasoning vs visible tokens
//
//         Example skeleton:
//           import OpenAI from "openai";
//           const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
//           const response = await client.chat.completions.create({
//             model: "o4-mini",
//             messages: [{ role: "user", content: question }],
//             max_completion_tokens: 4096,
//             reasoning_effort: "medium",
//           });
// ---------------------------------------------------------------------------
async function callReasoningOpenAI(question: string): Promise<ModelResult> {
  throw new Error("TODO: implement callReasoningOpenAI");
}

// ---------------------------------------------------------------------------
// TODO 3 (alternative): Implement callReasoningAnthropic.
//         Use the anthropic SDK with extended thinking enabled.
//         This is a beta feature — pass betas: ["interleaved-thinking-2025-05-14"].
//
//         Key parameters:
//         - thinking: { type: "enabled", budget_tokens: 5000 }
//         - The response.content array contains ThinkingBlock and TextBlock items.
//         - Filter for blocks with type === "text" for the visible answer.
//         - Filter for blocks with type === "thinking" to display reasoning.
//
//         Example skeleton:
//           import Anthropic from "@anthropic-ai/sdk";
//           const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
//           const response = await client.beta.messages.create({
//             model: process.env.ANTHROPIC_MODEL ?? "claude-opus-4-8",
//             max_tokens: 8000,
//             thinking: { type: "enabled", budget_tokens: 5000 },
//             betas: ["interleaved-thinking-2025-05-14"],
//             messages: [{ role: "user", content: question }],
//           });
// ---------------------------------------------------------------------------
async function callReasoningAnthropic(question: string): Promise<ModelResult> {
  throw new Error("TODO: implement callReasoningAnthropic");
}

function printRow(label: string, r: ModelResult): void {
  const truncated = r.answer.replace(/\n/g, " ").slice(0, 60) + "...";
  console.log(
    `  ${label.padEnd(18)} | ${r.model.padEnd(20)} | ${r.latencyMs.toFixed(0).padStart(6)} ms` +
    ` | in=${String(r.inputTokens).padStart(5)} out=${String(r.outputTokens).padStart(5)}` +
    ` | ${truncated}`
  );
}

async function main() {
  console.log("=== Task 1: Reasoning vs Standard Model ===\n");
  console.log(
    "Strategy".padEnd(18) + " | " +
    "Model".padEnd(20) + " | " +
    "Latency".padStart(9) + " | " +
    "Tokens".padEnd(22) + " | Answer (truncated)"
  );
  console.log("-".repeat(100));

  for (const problem of PROBLEMS) {
    console.log(`\nProblem [${problem.id}]: ${problem.question.slice(0, 80)}...`);

    // -------------------------------------------------------------------------
    // TODO 4: Call callStandard and one of the reasoning implementations.
    //         Wrap each in try/catch so a missing API key doesn't crash the script.
    // -------------------------------------------------------------------------

    try {
      const std = await callStandard(problem.question);
      printRow("standard", std);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ${"standard".padEnd(18)} | ${msg.startsWith("TODO") ? "(not yet implemented)" : "ERROR: " + msg}`);
    }

    try {
      const reasoning = await callReasoningOpenAI(problem.question);
      printRow("reasoning (openai)", reasoning);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      console.log(`  ${"reasoning (openai)".padEnd(18)} | ${msg.startsWith("TODO") ? "(not yet implemented)" : "ERROR: " + msg}`);
    }

    // -------------------------------------------------------------------------
    // TODO 5 (stretch): Check whether the answer contains the expected keywords
    //         from problem.expectedContains. Print a checkmark or cross.
    // -------------------------------------------------------------------------
  }

  console.log();
  console.log("Observation: note how reasoning models trade latency + tokens for accuracy.");
  console.log("On simple problems the overhead is rarely worth it.");
}

main().catch(console.error);
