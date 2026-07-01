/**
 * Task 5 — Batch API 🟢
 *
 * What this teaches:
 *   - The Batch API lets you submit many requests in one API call and receive results
 *     asynchronously (typically within 24 hours). Providers discount the price — often
 *     50 % of the live rate.
 *   - Batching is ideal for: eval pipelines, bulk summarisation, data extraction from
 *     large corpora — any workload where latency doesn't matter.
 *   - This task goes BEYOND llm-core — you must use the provider SDKs directly.
 *
 * Environment variables:
 *   ANTHROPIC_API_KEY — required for the Anthropic Batch API path
 *   OPENAI_API_KEY    — required for the OpenAI Batch API path
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/05-batch-api.ts
 *
 * Note: batch jobs take minutes to hours. The script polls and waits.
 */

import "dotenv/config";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

// ---------------------------------------------------------------------------
// Sample requests — sentiment classification.
// ---------------------------------------------------------------------------
const BATCH_INPUTS = [
  { id: "req-1", text: "The product exceeded all my expectations. Absolutely love it!" },
  { id: "req-2", text: "Terrible experience. The item arrived broken and support was unhelpful." },
  { id: "req-3", text: "It is what it is. Does the job but nothing special." },
  { id: "req-4", text: "Genuinely impressed by the build quality and fast delivery." },
  { id: "req-5", text: "Would not recommend. The instructions were incomprehensible." },
];

const CLASSIFY_SYSTEM =
  "Classify the sentiment of the following text as exactly one of: " +
  "positive, negative, or neutral. Reply with only the single word.";

const POLL_INTERVAL_MS = 10_000;
const MAX_POLL_ATTEMPTS = 60;

// ---------------------------------------------------------------------------
// TODO 1: Implement runAnthropicBatch using the @anthropic-ai/sdk Message Batches API.
//         Construct an Anthropic client from apiKey; read the model from
//         ANTHROPIC_MODEL (a cheap Haiku model is a good default for a classification
//         batch). Conceptual steps:
//         1. Map BATCH_INPUTS into one request object per item, each carrying a unique
//            `custom_id` (reuse item.id) and a `params` object holding model, a small
//            max_tokens, `system: CLASSIFY_SYSTEM`, and a one-user-message array with
//            the item's text.
//         2. Submit them with `client.beta.messages.batches.create({ requests })`.
//         3. Poll `client.beta.messages.batches.retrieve(batch.id)` on an interval
//            (use POLL_INTERVAL_MS / MAX_POLL_ATTEMPTS) until processing_status is
//            "ended".
//         4. Stream outputs with `for await (... of
//            client.beta.messages.batches.results(batch.id))` — the classification text
//            lives on the first content block of each result's message.
//         5. Print each result's custom_id alongside that text.
// ---------------------------------------------------------------------------
async function runAnthropicBatch(): Promise<void> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.log("  ANTHROPIC_API_KEY not set — skipping Anthropic batch demo.");
    return;
  }

  // TODO: implement (import Anthropic from "@anthropic-ai/sdk")
  throw new Error("TODO: implement runAnthropicBatch");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement runOpenAIBatch using the openai SDK Batch API.
//         Construct an OpenAI client from apiKey; read the model from
//         OPENAI_CHAT_MODEL. Unlike Anthropic, OpenAI batches are driven through an
//         uploaded JSONL file. Conceptual steps:
//         1. Build a JSONL string — one line per BATCH_INPUTS item. Each line is a
//            request object with `custom_id`, `method` "POST", `url`
//            "/v1/chat/completions", and a `body` holding model, the messages array
//            (system = CLASSIFY_SYSTEM, user = the item text), and a small max_tokens.
//            Write it to a temp file (path.join(os.tmpdir(), ...), fs.writeFileSync).
//         2. Upload it: `client.files.create({ file: fs.createReadStream(tmp),
//            purpose: "batch" })`.
//         3. Submit: `client.batches.create({ input_file_id, endpoint:
//            "/v1/chat/completions", completion_window: "24h" })`.
//         4. Poll `client.batches.retrieve(batch.id)` (POLL_INTERVAL_MS /
//            MAX_POLL_ATTEMPTS) until status is "completed".
//         5. Download results via `client.files.content(batch.output_file_id)`.
//         6. Parse each returned JSONL line; print its custom_id and the response
//            message content.
// ---------------------------------------------------------------------------
async function runOpenAIBatch(): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.log("  OPENAI_API_KEY not set — skipping OpenAI batch demo.");
    return;
  }

  // TODO: implement (import OpenAI from "openai")
  throw new Error("TODO: implement runOpenAIBatch");
}

function estimateSavings(
  nRequests: number,
  avgInputTokens = 100,
  avgOutputTokens = 10,
  inputPricePer1M = 0.15,
  outputPricePer1M = 0.60,
  batchDiscount = 0.50,
): void {
  const liveCost =
    (nRequests * avgInputTokens / 1_000_000) * inputPricePer1M +
    (nRequests * avgOutputTokens / 1_000_000) * outputPricePer1M;
  const batchCost = liveCost * (1 - batchDiscount);
  console.log(`  Workload: ${nRequests} requests × ~${avgInputTokens} in + ${avgOutputTokens} out tokens`);
  console.log(`  Live cost   : $${liveCost.toFixed(6)}`);
  console.log(`  Batch cost  : $${batchCost.toFixed(6)}  (${Math.round(batchDiscount * 100)}% discount)`);
  console.log(`  Saving      : $${(liveCost - batchCost).toFixed(6)}`);
}

async function main() {
  console.log("=== Task 5: Batch API ===\n");
  console.log(`Requests to batch: ${BATCH_INPUTS.length}`);
  for (const item of BATCH_INPUTS) {
    console.log(`  [${item.id}] ${item.text.slice(0, 60)}...`);
  }

  console.log();
  console.log("--- Cost comparison (before running) ---");
  estimateSavings(BATCH_INPUTS.length, 80, 5, 0.15, 0.60, 0.50);

  console.log();
  console.log("--- Anthropic Batch API ---");
  try {
    await runAnthropicBatch();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.log(`  ${msg.startsWith("TODO") ? msg : "ERROR: " + msg}`);
  }

  console.log();
  console.log("--- OpenAI Batch API ---");
  try {
    await runOpenAIBatch();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.log(`  ${msg.startsWith("TODO") ? msg : "ERROR: " + msg}`);
  }

  console.log();
  console.log("Observation:");
  console.log("  Batch API is best when you have hundreds+ of requests and no latency SLA.");
  console.log("  For < 10 requests, the polling overhead outweighs the savings.");
  console.log("  Use live calls when a user is waiting; use batches for offline pipelines.");
}

main().catch(console.error);
