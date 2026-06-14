/**
 * Task 2 — Observability 🟢
 *
 * What this teaches:
 *   - Every LLM call in production should emit a structured log entry so you
 *     can answer: what was sent, what came back, how long it took, and how
 *     much it cost.
 *   - JSONL (newline-delimited JSON) is a simple, queryable format for logs —
 *     easy to write, easy to stream into tools like Langfuse or Datadog.
 *   - Wrapping your provider in a thin observability layer keeps the logging
 *     logic out of your application code.
 *   - In production, use Langfuse (open-source) or OpenTelemetry for richer
 *     distributed tracing, session grouping, and dashboards.
 *
 * How to run:
 *   pnpm tsx modules/07-advanced-production/ts/02-observability.ts
 *   # Then inspect the log:
 *   cat modules/07-advanced-production/llm-calls.jsonl
 */

import { getProvider, ChatMessage, ChatOptions, ChatResult } from "@learn-ai/llm-core";
import * as fs from "node:fs";
import * as path from "node:path";
import * as crypto from "node:crypto";

// ---------------------------------------------------------------------------
// Cost table — approximate cost per 1M tokens (USD), update as needed
// ---------------------------------------------------------------------------

const COST_PER_1M_TOKENS: Record<string, { input: number; output: number }> = {
  "gpt-4o-mini":        { input: 0.15,  output: 0.60 },
  "gpt-4o":             { input: 2.50,  output: 10.00 },
  "claude-haiku-4-5":   { input: 0.25,  output: 1.25 },
  "claude-opus-4-8":    { input: 15.00, output: 75.00 },
  // Ollama / local models: 0 cost
};

// ---------------------------------------------------------------------------
// Log entry schema
// ---------------------------------------------------------------------------

interface LLMCallLog {
  id: string;
  timestamp: string;
  provider: string;
  model: string;
  messages: ChatMessage[];
  options?: ChatOptions;
  responseText: string;
  inputTokens?: number;
  outputTokens?: number;
  latencyMs: number;
  estimatedCostUsd?: number;
  error?: string;
}

// ---------------------------------------------------------------------------
// JSONL logger
// ---------------------------------------------------------------------------

const LOG_PATH = path.join(
  process.cwd(),
  "modules/07-advanced-production/llm-calls.jsonl"
);

function appendLog(entry: LLMCallLog): void {
  // TODO 1: Serialize entry to JSON and append it + "\n" to LOG_PATH.
  //         Use fs.appendFileSync(LOG_PATH, JSON.stringify(entry) + "\n").
  throw new Error("TODO: implement appendLog");
}

// ---------------------------------------------------------------------------
// Cost estimator
// ---------------------------------------------------------------------------

function estimateCost(
  model: string,
  inputTokens?: number,
  outputTokens?: number
): number | undefined {
  // TODO 2: Look up the model in COST_PER_1M_TOKENS.
  //         If found and both token counts exist, compute:
  //           (inputTokens / 1_000_000) * costs.input
  //         + (outputTokens / 1_000_000) * costs.output
  //         Return undefined if model not found or tokens are missing.
  throw new Error("TODO: implement estimateCost");
}

// ---------------------------------------------------------------------------
// Observing wrapper — wraps any LLM call and logs it
// ---------------------------------------------------------------------------

async function observedChat(
  messages: ChatMessage[],
  options?: ChatOptions
): Promise<ChatResult> {
  const provider = getProvider();
  const id = crypto.randomUUID();
  const t0 = performance.now();

  // TODO 3: Try to call provider.chat(messages, options).
  //         On success, build an LLMCallLog with all fields populated.
  //         On error, build a log entry with error: e.message, responseText: "".
  //         Always call appendLog() and always re-throw errors after logging.
  //         Return the ChatResult on success.
  //
  // Hint: wrap in try/catch/finally — appendLog in finally so it always runs.

  throw new Error("TODO: implement observedChat");
}

// ---------------------------------------------------------------------------
// Main — make several calls and inspect the log
// ---------------------------------------------------------------------------

async function main() {
  console.log(`Logging LLM calls to: ${LOG_PATH}\n`);

  const questions = [
    "What is 12 * 34?",
    "Name the three laws of thermodynamics in one sentence each.",
    "What is the capital of Japan?",
  ];

  for (const q of questions) {
    console.log(`Q: ${q}`);
    try {
      const result = await observedChat([{ role: "user", content: q }]);
      console.log(`A: ${result.text.slice(0, 80)}...\n`);
    } catch (e) {
      console.error(`Error: ${e}`);
    }
  }

  // TODO 4: Read LOG_PATH and pretty-print a summary of each logged call:
  //   - id, model, latencyMs, inputTokens, outputTokens, estimatedCostUsd
  //   Then print the total estimated cost for this session.

  console.log("\n--- Log summary ---");
  console.log("TODO: read and summarise the JSONL log.");

  // TODO 5 (stretch): Add a runningTotals tracker that accumulates token counts
  //         and costs across multiple calls and prints a session summary at the end.
  //         Note: in production, use Langfuse (https://langfuse.com) or an
  //         OpenTelemetry exporter for dashboards, alerts, and session grouping.
}

main().catch(console.error);
