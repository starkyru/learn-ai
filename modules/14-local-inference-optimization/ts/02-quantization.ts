/**
 * Task 2 🟡 — Quantization: size vs speed vs quality.
 *
 * What you'll learn:
 *   - What quantization is and why it matters for local inference
 *   - The fp32 → fp16 → int8 → int4 (GGUF Q4) ladder and tradeoffs
 *   - How to measure speed and quality differences between quant levels
 *   - The memory footprint reduction at each step
 *
 * We compare two Ollama models: llama3.2:1b (smaller) vs llama3.2 (larger).
 * To compare true quant levels, pull Q4 and Q8 variants of the same model:
 *   ollama pull qwen2.5:7b-instruct-q4_K_M
 *   ollama pull qwen2.5:7b-instruct-q8_0
 * Then update MODEL_A/MODEL_B below.
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/02-quantization.ts
 */

import { OpenAICompatibleProvider, type LLMProvider } from "@learn-ai/llm-core";

const MODEL_A = "llama3.2:1b"; // smaller / faster
const MODEL_B = "llama3.2"; // larger / slower / better quality

const OLLAMA_BASE_URL = "http://localhost:11434";

const BENCHMARK_PROMPT =
  "In two concise paragraphs, explain the difference between machine learning " +
  "and deep learning. Give one concrete example application for each.";

const JUDGE_PROMPT_TEMPLATE = (response: string) =>
  `Rate the following response on coherence and factual accuracy on a scale of 1-5.\n` +
  `Respond with ONLY a single digit.\n\nResponse:\n${response}`;

interface ModelInfo {
  parameter_size: string;
  quantization: string;
  family: string;
}

interface TimedResult {
  text: string;
  tokensOut: number;
  elapsedS: number;
  tokensPerS: number;
}

// ---------------------------------------------------------------------------
// Model info
// ---------------------------------------------------------------------------

/**
 * Query the Ollama /api/show endpoint and return model metadata.
 *
 * Returns { parameter_size, quantization, family }.
 *
 * TODO:
 *   1. POST to OLLAMA_BASE_URL + "/api/show" with a JSON body naming the model
 *      ({ name: modelName }). Use the global fetch() (Node 18+).
 *   2. Await response.json().
 *   3. The fields you need live under data.details: the quantization level, the
 *      family, and the parameter size. Read each, defaulting to "unknown".
 *   4. Return the ModelInfo ({ parameter_size, quantization, family }).
 *   5. On any error, return every field as "unknown".
 */
async function getModelInfo(modelName: string): Promise<ModelInfo> {
  // TODO: implement getModelInfo
  throw new Error("TODO: implement getModelInfo()");
}

// ---------------------------------------------------------------------------
// Timed prompt
// ---------------------------------------------------------------------------

/**
 * Run `prompt` against `modelName` via Ollama and measure speed.
 *
 * Returns { text, tokensOut, elapsedS, tokensPerS }.
 *
 * TODO:
 *   1. Construct an OpenAICompatibleProvider pointed at Ollama's OpenAI-shim
 *      endpoint (OLLAMA_BASE_URL + "/v1"), with chatModel set to modelName.
 *      The apiKey can be any placeholder; set an embedModel too.
 *   2. Time a single provider.chat() call with performance.now() before/after
 *      (one "user" message, options with a bounded maxTokens).
 *   3. Return the TimedResult (text / tokensOut / elapsedS / tokensPerS).
 */
async function runTimedPrompt(modelName: string, prompt: string): Promise<TimedResult> {
  // TODO: implement runTimedPrompt
  throw new Error("TODO: implement runTimedPrompt()");
}

// ---------------------------------------------------------------------------
// Quality scoring
// ---------------------------------------------------------------------------

/**
 * Ask a judge provider to score `responseText` on 1–5.
 *
 * TODO:
 *   1. Create a default provider for the judge.
 *   2. Call provider.chat() with the judge prompt.
 *   3. Parse the first digit in the response. Fallback to 3.
 */
async function scoreQuality(
  responseText: string,
  judgeProvider: LLMProvider,
): Promise<number> {
  // TODO: implement scoreQuality
  throw new Error("TODO: implement scoreQuality()");
}

// ---------------------------------------------------------------------------
// Comparison table
// ---------------------------------------------------------------------------

interface ComparisonRow {
  model: string;
  quantization: string;
  parameter_size: string;
  tokensPerS: number;
  qualityScore: number;
}

/**
 * Print a formatted table comparing models.
 *
 * Columns: Model | Quant | Params | Tokens/sec | Quality(1-5)
 *
 * TODO:
 *   1. Print a header row (padEnd for alignment).
 *   2. Print each row.
 */
function printComparisonTable(results: ComparisonRow[]): void {
  // TODO: implement printComparisonTable
  throw new Error("TODO: implement printComparisonTable()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  console.log("Quantization comparison: measuring size vs speed vs quality");
  console.log("=".repeat(60));

  const { getProvider } = await import("@learn-ai/llm-core");
  const judgeProvider = getProvider();

  const results: ComparisonRow[] = [];

  for (const modelName of [MODEL_A, MODEL_B]) {
    console.log(`\nBenchmarking ${modelName}...`);

    const info = await getModelInfo(modelName);
    console.log(`  Params: ${info.parameter_size}, Quant: ${info.quantization}`);

    try {
      const timed = await runTimedPrompt(modelName, BENCHMARK_PROMPT);
      console.log(`  Tokens/sec: ${timed.tokensPerS.toFixed(1)}`);
      console.log(`  Response preview: ${timed.text.slice(0, 80)}...`);

      const quality = await scoreQuality(timed.text, judgeProvider);
      console.log(`  Quality score: ${quality}/5`);

      results.push({
        model: modelName,
        quantization: info.quantization,
        parameter_size: info.parameter_size,
        tokensPerS: timed.tokensPerS,
        qualityScore: quality,
      });
    } catch (e) {
      console.log(`  SKIPPED: ${e}`);
      console.log(`  (Run: ollama pull ${modelName})`);
    }
  }

  if (results.length > 0) {
    console.log("\n" + "=".repeat(60));
    printComparisonTable(results);
  }

  console.log(
    "\nKey takeaway: quantization reduces size and increases speed with a",
    "\nsmall quality penalty. Q4 models often get within 5% of Q8 quality",
    "\nat 1/2 the memory footprint and noticeably higher tokens/sec.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
