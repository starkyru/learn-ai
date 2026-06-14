/**
 * Task 1 🟢 — Run local models and measure tokens/sec.
 *
 * What you'll learn:
 *   - How to measure tokens per second from any provider call
 *   - What "tokens/sec" means in practice (varies by model size + hardware)
 *   - The different local serving engines and when to use each
 *
 * Default: uses Ollama (set up in module 00). No extra downloads needed.
 *
 * Optional local paths (documented here, not required):
 *   llama.cpp:  brew install llama.cpp
 *   vLLM:       pip install vllm  (Linux + NVIDIA GPU only)
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/01-run-local.ts
 */

import { getProvider } from "@learn-ai/llm-core";

const BENCHMARK_PROMPT =
  "Explain how a transformer model works, focusing on the attention mechanism. " +
  "Be concise but thorough. Cover: tokens, embeddings, self-attention, and the " +
  "feed-forward layer.";

// ---------------------------------------------------------------------------
// Throughput measurement
// ---------------------------------------------------------------------------

interface ThroughputResult {
  text: string;
  tokensOut: number;
  elapsedS: number;
  tokensPerS: number;
  model: string;
}

/**
 * Send `prompt` to `provider` and measure tokens per second.
 *
 * TODO:
 *   1. Record start time: performance.now() (ms).
 *   2. Call provider.chat([{ role: "user", content: prompt }],
 *        { max_tokens: 256 }).
 *   3. Record end time. Compute elapsedS = (end - start) / 1000.
 *   4. Get tokensOut from result.usage.output_tokens ?? 0.
 *   5. Compute tokensPerS = tokensOut / elapsedS (0 if elapsedS === 0).
 *   6. Return the ThroughputResult.
 */
async function measureThroughput(
  prompt: string,
  provider: ReturnType<typeof getProvider>,
): Promise<ThroughputResult> {
  // TODO: implement measureThroughput
  throw new Error("TODO: implement measureThroughput()");
}

/**
 * Run `prompt` nRuns times and report min/max/mean tokens/sec.
 *
 * TODO:
 *   1. Collect results from nRuns calls to measureThroughput().
 *   2. Extract tokensPerS from each (skip if 0).
 *   3. Print model, runs, min/max/mean tokens/sec, and first 100 chars of output.
 */
async function runBenchmark(
  prompt: string,
  provider: ReturnType<typeof getProvider>,
  nRuns = 3,
): Promise<void> {
  // TODO: implement runBenchmark
  throw new Error("TODO: implement runBenchmark()");
}

// ---------------------------------------------------------------------------
// Engine guide
// ---------------------------------------------------------------------------

const ENGINE_TABLE = `
LOCAL SERVING ENGINES — QUICK REFERENCE
========================================

Engine        Use case                    Key features
----------    --------------------------  --------------------------------
Ollama        Local dev, single user      One-command setup, cross-platform,
                                          GGUF models, auto-downloads
llama.cpp     Embedded / edge / CLI       Minimal deps, CPU-first, Metal
                                          GPU on Mac, quantized GGUF
vLLM          High-throughput server      PagedAttention, continuous batching,
              (Linux + NVIDIA GPU)        OpenAI-compatible API, best GPU util
TGI           HuggingFace integration     HF model hub, streaming, Rust server
(Text Gen     Multi-GPU                   Flash Attention, quantization
 Inference)

Decision guide:
  Single user, Mac/Windows/Linux dev  → Ollama
  CPU-only or edge device             → llama.cpp directly
  Serving 100s of concurrent users    → vLLM (Linux + NVIDIA)
  HuggingFace model + streaming UI    → TGI
`;

/**
 * Print the engine reference table.
 *
 * TODO: just console.log(ENGINE_TABLE).
 */
function printEngineGuide(): void {
  // TODO: implement printEngineGuide
  throw new Error("TODO: implement printEngineGuide()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  printEngineGuide();

  console.log("\n" + "=".repeat(60));
  console.log("BENCHMARK");
  console.log("=".repeat(60));

  try {
    const provider = getProvider();
    console.log(`Provider: ${provider.name} | Model: ${provider.chatModel}`);
    console.log(`Prompt: ${BENCHMARK_PROMPT.slice(0, 80)}...\n`);
    await runBenchmark(BENCHMARK_PROMPT, provider, 3);
  } catch (e) {
    console.log(`Provider unavailable (${e})`);
    console.log("Make sure Ollama is running: ollama serve");
    console.log("Then pull a model: ollama pull llama3.2");
  }

  console.log(
    "\nTip: Try different models by setting OLLAMA_CHAT_MODEL=llama3.2:1b",
    "\nand re-running. Smaller models = more tokens/sec.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
