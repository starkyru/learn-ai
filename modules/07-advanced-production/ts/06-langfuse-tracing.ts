/**
 * Task 6 — Langfuse: production tracing 🟡
 *
 * What this teaches:
 *   - Task 2 hand-rolled a JSONL tracer. Great for intuition, but in a real
 *     service you don't want to build (and babysit) your own dashboards, session
 *     grouping, cost roll-ups, and alerting. Langfuse (https://langfuse.com) is
 *     the industry-standard, open-source LLM-observability platform that gives
 *     you all of that — you just instrument your calls.
 *   - The core Langfuse vocabulary:
 *       * trace       — one end-to-end request/workflow ("answer the user").
 *       * generation  — one LLM call inside a trace, with input, output, model,
 *                       token usage, and cost. A trace can hold many generations.
 *       * session     — a group of traces that belong together (a conversation,
 *                       a user's day of usage) inspected as one unit.
 *     You'll see these exact concepts in the hosted UI once you add keys.
 *   - The lesson is tracer-AGNOSTIC instrumentation: write your app once against
 *     a small `Tracer` interface, then pick the backend (hosted Langfuse or a
 *     local print-only tracer) at runtime. `tracedChat` never knows which one.
 *
 * Offline-friendly by design:
 *   - With NO Langfuse keys set, this runs a `LocalTracer` that prints an
 *     indented trace tree to stdout — no account, no network. Set
 *     LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY to send the same data to the UI.
 *   - It also survives having NO LLM running: if the provider is unavailable it
 *     falls back to a deterministic fake ChatResult so the tracing path still runs.
 *
 * How to run:
 *   pnpm add langfuse@^3.0.0           # from modules/07-advanced-production/ts
 *   # Offline (LocalTracer, prints a trace tree):
 *   pnpm tsx modules/07-advanced-production/ts/06-langfuse-tracing.ts
 *   # (Optional) hosted UI — get free keys at https://cloud.langfuse.com:
 *   export LANGFUSE_PUBLIC_KEY=pk-lf-...
 *   export LANGFUSE_SECRET_KEY=sk-lf-...
 *   pnpm tsx modules/07-advanced-production/ts/06-langfuse-tracing.ts
 */

import { getProvider, ChatMessage, ChatResult, LLMProvider } from "@learn-ai/llm-core";
import * as crypto from "node:crypto";

// ---------------------------------------------------------------------------
// Cost table — approximate cost per 1M tokens (USD). Same idea as Task 2.
// ---------------------------------------------------------------------------

const COST_PER_1M_TOKENS: Record<string, { input: number; output: number }> = {
  "gpt-4o-mini": { input: 0.15, output: 0.6 },
  "gpt-4o": { input: 2.5, output: 10.0 },
  "claude-haiku-4-5": { input: 0.25, output: 1.25 },
  "claude-opus-4-8": { input: 15.0, output: 75.0 },
  // Ollama / local models: 0 cost
};

function estimateCost(
  model: string,
  inputTokens?: number,
  outputTokens?: number,
): number | undefined {
  // TODO 1 (same formula as Task 2):
  //   - Look up `model` in COST_PER_1M_TOKENS.
  //   - If found AND both token counts are defined, return:
  //         (inputTokens  / 1_000_000) * costs.input
  //       + (outputTokens / 1_000_000) * costs.output
  //   - Otherwise return undefined (unknown/local model, or missing tokens).
  throw new Error("TODO 1: implement estimateCost (see Task 2)");
}

// ---------------------------------------------------------------------------
// The Tracer interface — application code depends ONLY on this.
// Two implementations below: LangfuseTracer (real) and LocalTracer (offline).
// ---------------------------------------------------------------------------

interface GenerationRecord {
  name: string;
  model: string;
  input: string;
  output: string;
  inputTokens?: number;
  outputTokens?: number;
  latencyMs: number;
  costUsd?: number;
}

interface Tracer {
  startTrace(name: string, sessionId: string): void;
  generation(rec: GenerationRecord): void;
  endTrace(): void;
  flush(): Promise<void>;
}

// ---------------------------------------------------------------------------
// LangfuseTracer — the REAL backend (used only when keys are present).
// This body is PROVIDED COMPLETE so you see correct v3 SDK usage.
// ---------------------------------------------------------------------------

class LangfuseTracer implements Tracer {
  // Typed loosely so the offline path never has to import the SDK.
  private client: any;
  private trace: any;

  constructor() {
    // Lazy require so `pnpm tsx` works offline without the package present.
    const { Langfuse } = require("langfuse");
    this.client = new Langfuse({
      publicKey: process.env.LANGFUSE_PUBLIC_KEY,
      secretKey: process.env.LANGFUSE_SECRET_KEY,
      baseUrl: process.env.LANGFUSE_HOST ?? "https://cloud.langfuse.com",
    });
  }

  startTrace(name: string, sessionId: string): void {
    // A trace groups all generations for one workflow; sessionId groups traces
    // into a session in the hosted UI.
    this.trace = this.client.trace({
      name,
      sessionId,
      input: { sessionId },
    });
  }

  generation(rec: GenerationRecord): void {
    // One 'generation' observation per LLM call. usageDetails / costDetails are
    // what power Langfuse's token + cost dashboards.
    const usageDetails: Record<string, number> = {};
    if (rec.inputTokens !== undefined) usageDetails.input = rec.inputTokens;
    if (rec.outputTokens !== undefined) usageDetails.output = rec.outputTokens;

    const gen = this.trace.generation({
      name: rec.name,
      model: rec.model,
      input: rec.input,
      output: rec.output,
      usageDetails,
      costDetails: rec.costUsd !== undefined ? { total: rec.costUsd } : undefined,
      metadata: { latencyMs: rec.latencyMs },
    });
    gen.end();
  }

  endTrace(): void {
    // Nothing to close explicitly; the trace is finalised on flush.
  }

  async flush(): Promise<void> {
    // Langfuse batches network sends; flush before the process exits.
    await this.client.flushAsync();
  }
}

// ---------------------------------------------------------------------------
// LocalTracer — offline fallback. Prints an indented trace tree. No network.
// ---------------------------------------------------------------------------

class LocalTracer implements Tracer {
  private name = "";
  private sessionId = "";
  records: GenerationRecord[] = [];

  startTrace(name: string, sessionId: string): void {
    this.name = name;
    this.sessionId = sessionId;
    this.records = [];
    console.log(`\n[trace] ${name}  (session=${sessionId})`);
  }

  generation(rec: GenerationRecord): void {
    // TODO 3: Record `rec` on this.records so endTrace() can total the costs,
    // then print ONE indented line for this generation. Use this exact format so
    // the tree stays readable (the header above is already printed):
    //
    //   console.log(
    //     `  └─ generation '${rec.name}'  model=${rec.model}  ` +
    //       `latency=${rec.latencyMs.toFixed(0)}ms  ` +
    //       `tokens(in/out)=${rec.inputTokens}/${rec.outputTokens}  ` +
    //       `cost=${fmtCost(rec.costUsd)}`,
    //   );
    //   console.log(`       in : ${JSON.stringify(rec.input.slice(0, 60))}`);
    //   console.log(`       out: ${JSON.stringify(rec.output.slice(0, 60))}`);
    throw new Error("TODO 3: record + print this generation (see comment)");
  }

  endTrace(): void {
    const total = this.records.reduce((sum, r) => sum + (r.costUsd ?? 0), 0);
    console.log(
      `[trace end] ${this.name}  generations=${this.records.length}  ` +
        `trace_cost=${fmtCost(total)}`,
    );
  }

  async flush(): Promise<void> {
    // Nothing to flush — LocalTracer prints synchronously.
  }
}

function fmtCost(cost?: number): string {
  return cost !== undefined ? `$${cost.toFixed(6)}` : "n/a";
}

// ---------------------------------------------------------------------------
// tracedChat — wraps provider.chat() and records a generation on ANY tracer.
// ---------------------------------------------------------------------------

async function tracedChat(
  provider: LLMProvider,
  messages: ChatMessage[],
  tracer: Tracer,
  name = "chat",
): Promise<ChatResult> {
  const inputText = messages.length ? messages[messages.length - 1].content : "";
  const t0 = performance.now();

  let result: ChatResult;
  try {
    result = await provider.chat(messages);
  } catch (e) {
    // No live LLM? Fall back to a fake, deterministic result so the tracing
    // path is still exercised. (Real production code would let this throw.)
    result = fakeChatResult(inputText);
  }

  const latencyMs = performance.now() - t0;

  // TODO 2: Record this call on the tracer, then return `result`.
  //   a) Pull token counts from result.usage?.inputTokens / result.usage?.outputTokens
  //      (either may be undefined).
  //   b) const cost = estimateCost(result.model, inTok, outTok);
  //   c) Build a GenerationRecord: { name, model: result.model, input: inputText,
  //        output: result.text, inputTokens: inTok, outputTokens: outTok,
  //        latencyMs, costUsd: cost }.
  //   d) tracer.generation(rec);
  //   e) return result;
  throw new Error("TODO 2: record the generation on the tracer, then return result");
}

function fakeChatResult(question: string): ChatResult {
  // Deterministic stand-in so the demo runs with no LLM and no network.
  const answer = `[offline fake answer] I would answer: ${question}`;
  return {
    text: answer,
    model: "gpt-4o-mini", // a priced model so cost estimation is non-undefined
    usage: {
      inputTokens: Math.max(1, question.split(/\s+/).length),
      outputTokens: Math.max(1, answer.split(/\s+/).length),
    },
  };
}

// ---------------------------------------------------------------------------
// Main — pick a tracer, run a few questions under ONE trace/session, summarise.
// ---------------------------------------------------------------------------

function pickTracer(): { tracer: Tracer; isHosted: boolean } {
  if (process.env.LANGFUSE_PUBLIC_KEY && process.env.LANGFUSE_SECRET_KEY) {
    return { tracer: new LangfuseTracer(), isHosted: true };
  }
  return { tracer: new LocalTracer(), isHosted: false };
}

/** A provider whose chat() always fails, forcing the deterministic fake path. */
function nullProvider(): LLMProvider {
  return {
    name: "none",
    chatModel: "none",
    embedModel: "none",
    async chat(): Promise<ChatResult> {
      throw new Error("no LLM configured");
    },
    async *chatStream() {
      throw new Error("no LLM configured");
    },
    async embed() {
      throw new Error("no LLM configured");
    },
  };
}

async function main() {
  const { tracer, isHosted } = pickTracer();

  if (isHosted) {
    const host = process.env.LANGFUSE_HOST ?? "https://cloud.langfuse.com";
    console.log(`[mode] Langfuse (hosted) — sending traces to ${host}`);
  } else {
    console.log("[mode] LocalTracer (offline) — printing trace tree to stdout.");
    console.log(
      "       Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (get free keys at",
    );
    console.log(
      "       https://cloud.langfuse.com) to send the same data to the hosted UI.",
    );
  }

  let provider: LLMProvider;
  try {
    provider = getProvider();
  } catch {
    provider = nullProvider(); // no provider configured — the fake fallback covers it.
  }

  const sessionId = `daily-qa-${crypto.randomUUID().slice(0, 8)}`;
  const questions = [
    "What is 12 * 34?",
    "Name the capital of Japan.",
    "In one sentence, what is retrieval-augmented generation?",
  ];

  tracer.startTrace("daily-qa", sessionId);

  try {
    let i = 0;
    for (const q of questions) {
      i += 1;
      const result = await tracedChat(
        provider,
        [{ role: "user", content: q }],
        tracer,
        `q${i}`,
      );
      console.log(`Q${i}: ${q}`);
      console.log(`A${i}: ${result.text.slice(0, 80)}`);
    }
  } finally {
    tracer.endTrace();
    await tracer.flush();
  }

  // Session summary (works for LocalTracer; hosted UI shows the same numbers).
  if (tracer instanceof LocalTracer) {
    console.log("\n--- session cost summary ---");
    let total = 0;
    for (const rec of tracer.records) {
      total += rec.costUsd ?? 0;
      console.log(
        `  ${rec.name.padEnd(4)} ${rec.model.padEnd(14)} cost=${fmtCost(rec.costUsd)}`,
      );
    }
    console.log(`  ${"TOTAL".padEnd(4)} ${"".padEnd(14)} cost=${fmtCost(total)}`);
  } else {
    console.log("\nDone — open the Langfuse UI and filter by session:", sessionId);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
