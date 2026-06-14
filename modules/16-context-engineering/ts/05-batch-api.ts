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
// TODO 1: Implement runAnthropicBatch.
//         Use the @anthropic-ai/sdk Message Batches API.
//
//         Steps:
//         1. Build an array of request objects:
//            { custom_id: item.id, params: { model, max_tokens: 10, system: ..., messages: [...] } }
//         2. Submit: const batch = await client.beta.messages.batches.create({ requests });
//         3. Poll: await client.beta.messages.batches.retrieve(batch.id)
//            until .processing_status === "ended".
//         4. Stream results: for await (const result of client.beta.messages.batches.results(batch.id))
//            extract result.result.message.content[0].text
//         5. Print custom_id and result text for each request.
//
//         Example skeleton:
//           import Anthropic from "@anthropic-ai/sdk";
//           const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
//           const batch = await client.beta.messages.batches.create({ requests: [...] });
//           // poll loop...
//           for await (const item of client.beta.messages.batches.results(batch.id)) { ... }
// ---------------------------------------------------------------------------
async function runAnthropicBatch(): Promise<void> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.log("  ANTHROPIC_API_KEY not set — skipping Anthropic batch demo.");
    return;
  }

  // TODO: implement
  // import Anthropic from "@anthropic-ai/sdk";
  // const client = new Anthropic({ apiKey });
  // const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5"; // use haiku for low cost
  // const requests = BATCH_INPUTS.map((item) => ({
  //   custom_id: item.id,
  //   params: {
  //     model,
  //     max_tokens: 10,
  //     system: CLASSIFY_SYSTEM,
  //     messages: [{ role: "user", content: item.text }],
  //   },
  // }));
  // const batch = await client.beta.messages.batches.create({ requests });
  // console.log(`  Batch submitted: id=${batch.id}`);
  // // ... poll and collect results
  throw new Error("TODO: implement runAnthropicBatch");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement runOpenAIBatch.
//         Use the openai SDK Batch API.
//
//         Steps:
//         1. Build a JSONL string where each line is:
//            { custom_id, method: "POST", url: "/v1/chat/completions", body: { model, messages, max_tokens: 10 } }
//         2. Write to a temp file; upload: const fileObj = await client.files.create({ file, purpose: "batch" }).
//         3. Submit: const batch = await client.batches.create({ input_file_id, endpoint, completion_window: "24h" }).
//         4. Poll: await client.batches.retrieve(batch.id) until .status === "completed".
//         5. Download output: const content = await client.files.content(batch.output_file_id).
//         6. Parse each JSONL line; print custom_id and response message content.
//
//         Example skeleton:
//           import OpenAI from "openai";
//           const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
//           const lines = BATCH_INPUTS.map((item) => JSON.stringify({ custom_id: item.id, ... }));
//           const tmp = path.join(os.tmpdir(), "batch_input.jsonl");
//           fs.writeFileSync(tmp, lines.join("\n"));
//           const fileObj = await client.files.create({ file: fs.createReadStream(tmp), purpose: "batch" });
//           const batch = await client.batches.create({ input_file_id: fileObj.id, endpoint: "/v1/chat/completions", completion_window: "24h" });
// ---------------------------------------------------------------------------
async function runOpenAIBatch(): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.log("  OPENAI_API_KEY not set — skipping OpenAI batch demo.");
    return;
  }

  // TODO: implement
  // import OpenAI from "openai";
  // const client = new OpenAI({ apiKey });
  // const model = process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini";
  // ...
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
