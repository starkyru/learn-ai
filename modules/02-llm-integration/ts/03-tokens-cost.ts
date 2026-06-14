/**
 * Task 3 — Tokens & cost 🟡
 *
 * What this teaches:
 *   - LLMs don't see words, they see tokens (sub-word pieces). Knowing
 *     how many tokens a text costs lets you stay within context windows
 *     and predict API spend.
 *   - Context window = max (input + output) tokens a model can handle.
 *     Exceeding it truncates or errors; managing it is YOUR job.
 *   - Cost = (input_tokens * price_in) + (output_tokens * price_out).
 *     Prices differ wildly between models — this exercise makes it concrete.
 *
 * Dependencies (already in package.json):
 *   @dqbd/tiktoken  — a WASM port of OpenAI's tiktoken, works in Node.
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/03-tokens-cost.ts
 */

import { getProvider } from "@learn-ai/llm-core";
// TODO: uncomment once you understand what these do
// import { get_encoding } from "@dqbd/tiktoken";

// ---------------------------------------------------------------------------
// Price table — $ per 1 000 000 tokens (as of mid-2025; check current prices).
// Add or update rows as you learn about new models.
// ---------------------------------------------------------------------------
const PRICE_TABLE: Record<string, { inputPer1M: number; outputPer1M: number; contextK: number }> = {
  "gpt-4o-mini":          { inputPer1M: 0.15,   outputPer1M: 0.60,   contextK: 128 },
  "gpt-4o":               { inputPer1M: 5.00,   outputPer1M: 15.00,  contextK: 128 },
  "claude-haiku-4-5":     { inputPer1M: 0.80,   outputPer1M: 4.00,   contextK: 200 },
  "claude-opus-4-8":      { inputPer1M: 15.00,  outputPer1M: 75.00,  contextK: 200 },
  "llama3.2":             { inputPer1M: 0.00,   outputPer1M: 0.00,   contextK: 128 },
};

const SAMPLE_TEXT = `
Retrieval-Augmented Generation (RAG) is a technique that improves large language
model outputs by retrieving relevant documents from an external knowledge base before
generating a response. Unlike pure parametric models that rely solely on weights
learned during training, RAG systems can incorporate up-to-date or domain-specific
information at inference time. This makes them particularly useful for question
answering, enterprise search, and chatbots that need factual grounding.
`.trim();

// ---------------------------------------------------------------------------
// TODO 1: Implement countTokens using tiktoken.
//         `get_encoding("cl100k_base")` returns an encoder. Call `.encode(text)`
//         to get a Uint32Array of token ids; its `.length` is the token count.
//         Remember to call `.free()` on the encoder when done to avoid WASM leaks.
// ---------------------------------------------------------------------------
function countTokens(text: string): number {
  // const enc = get_encoding("cl100k_base");
  // const tokens = enc.encode(text);
  // enc.free();
  // return tokens.length;

  // Rough fallback until you implement the above:
  return Math.ceil(text.split(/\s+/).length * 1.3);
}

// ---------------------------------------------------------------------------
// TODO 2: Implement estimateCost.
//         Look up the model in PRICE_TABLE. If not found, return null.
//         Cost formula:  (inputTokens / 1_000_000) * inputPer1M
//                      + (outputTokens / 1_000_000) * outputPer1M
// ---------------------------------------------------------------------------
function estimateCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
): { cost: number; contextK: number } | null {
  // TODO: implement
  return null;
}

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);

  // ---------------------------------------------------------------------------
  // TODO 3: Count tokens in SAMPLE_TEXT and print the result alongside the
  //         raw character count. Notice that token count < char count but
  //         > word count — tokens are sub-word units.
  // ---------------------------------------------------------------------------
  const tokenCount = countTokens(SAMPLE_TEXT);
  console.log("--- token counting ---");
  console.log(`Characters : ${SAMPLE_TEXT.length}`);
  console.log(`Words      : ${SAMPLE_TEXT.split(/\s+/).length}`);
  console.log(`Tokens     : ${tokenCount} (TODO: use tiktoken)`);

  // ---------------------------------------------------------------------------
  // TODO 4: Make a real API call and use the `usage` field from ChatResult to
  //         get exact provider token counts. Compare against your tiktoken
  //         estimate — how close are they?
  // ---------------------------------------------------------------------------
  console.log("\n--- real API call ---");
  const prompt = "Summarise this in one sentence: " + SAMPLE_TEXT;
  // const result = await llm.chat([{ role: "user", content: prompt }]);
  // console.log(`Response: ${result.text}`);
  // console.log(`Provider says — input: ${result.usage?.inputTokens}, output: ${result.usage?.outputTokens}`);
  // console.log(`Tiktoken estimate — input: ${countTokens(prompt)}`);
  console.log("TODO: make the real API call above.");

  // ---------------------------------------------------------------------------
  // TODO 5: Estimate cost for a few models and print a comparison table.
  //         Format: model | input tok | output tok | cost ($)
  // ---------------------------------------------------------------------------
  console.log("\n--- cost comparison ---");
  const exampleInput = 500;
  const exampleOutput = 200;
  console.log(`Assuming ${exampleInput} input tokens, ${exampleOutput} output tokens:\n`);
  console.log("Model".padEnd(24) + "Context".padEnd(12) + "Est. cost");
  console.log("-".repeat(50));
  for (const [model, info] of Object.entries(PRICE_TABLE)) {
    const cost = estimateCost(model, exampleInput, exampleOutput);
    const costStr = cost ? `$${cost.cost.toFixed(6)}` : "TODO";
    const ctxStr = `${info.contextK}K`;
    console.log(model.padEnd(24) + ctxStr.padEnd(12) + costStr);
  }

  // ---------------------------------------------------------------------------
  // TODO 6 (stretch): Write a function that, given a target budget in dollars
  //         and a model, computes how many "turns" (assume avg 500 input +
  //         200 output tokens per turn) you can afford. Print results for
  //         each model in the table.
  // ---------------------------------------------------------------------------
}

main().catch(console.error);
