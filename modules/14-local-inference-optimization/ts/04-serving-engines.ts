/**
 * Task 4 🟢 — Serving engines: pick by use case.
 *
 * What you'll learn:
 *   - The concrete tradeoffs between Ollama, llama.cpp, vLLM, and TGI
 *   - A rules-based recommendation function (no ML needed for this decision)
 *   - How to call multiple engines with the same client (OpenAI-compatible APIs)
 *
 * Key insight: all four engines expose the same OpenAI-compatible
 * /v1/chat/completions API. Switching engines is just a baseURL change.
 * The differences are performance characteristics and hardware requirements,
 * not the API shape.
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/04-serving-engines.ts
 */

import { OpenAICompatibleProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Engine reference table
// ---------------------------------------------------------------------------

interface Engine {
  name: string;
  useCase: string;
  keyFeatures: string;
  hardware: string;
  apiCompatible: boolean;
  setup: string;
  keywords: string[];
}

const ENGINES: Engine[] = [
  {
    name: "Ollama",
    useCase: "Local dev, single user, Mac/Windows/Linux",
    keyFeatures: "One-command setup, GGUF auto-download, cross-platform",
    hardware: "CPU or GPU (any)",
    apiCompatible: true,
    setup: "brew install ollama && ollama serve && ollama pull llama3.2",
    keywords: ["local", "laptop", "dev", "single", "user", "easy", "quick", "start"],
  },
  {
    name: "llama.cpp",
    useCase: "Embedded, edge, CLI, CPU-only",
    keyFeatures: "Minimal deps, C++ binary, Metal GPU on Mac, GGUF native",
    hardware: "CPU (Metal GPU on Mac)",
    apiCompatible: true,
    setup: "brew install llama.cpp  # then: llama-server -m model.gguf --port 8080",
    keywords: ["edge", "embedded", "cpu", "minimal", "gguf", "metal", "offline"],
  },
  {
    name: "vLLM",
    useCase: "High-throughput server, 100s of concurrent users",
    keyFeatures: "PagedAttention, continuous batching, best GPU utilisation",
    hardware: "NVIDIA GPU (Linux only)",
    apiCompatible: true,
    setup: "pip install vllm && python -m vllm.entrypoints.openai.api_server --model ...",
    keywords: ["throughput", "concurrent", "scale", "production", "server", "users", "batch", "gpu"],
  },
  {
    name: "TGI (Text Generation Inference)",
    useCase: "HuggingFace model hub + streaming, multi-GPU",
    keyFeatures: "Flash Attention, HF integration, Rust server, quantization",
    hardware: "NVIDIA GPU recommended",
    apiCompatible: true,
    setup: "docker run ghcr.io/huggingface/text-generation-inference --model-id ...",
    keywords: ["huggingface", "hf", "multi-gpu", "streaming", "docker"],
  },
];

// ---------------------------------------------------------------------------
// Engine recommendation
// ---------------------------------------------------------------------------

interface Recommendation {
  engine: string;
  reason: string;
  setup: string;
}

/**
 * Return the best serving engine for the given use-case description.
 *
 * Uses keyword matching against ENGINES — no ML needed here.
 *
 * TODO:
 *   1. Lowercase the useCase string.
 *   2. For each engine, count how many of its keywords appear in the useCase.
 *   3. Return the engine with the highest count. Tie-break: first in list (Ollama).
 *   4. Default to Ollama if no keywords match.
 *   5. Build and return the Recommendation.
 *
 * Examples:
 *   recommendEngine("I need to serve 1000 concurrent users")  → vLLM
 *   recommendEngine("I want to run on my laptop")             → Ollama
 */
function recommendEngine(useCase: string): Recommendation {
  // TODO: implement recommendEngine
  throw new Error("TODO: implement recommendEngine()");
}

// ---------------------------------------------------------------------------
// Run against available engines
// ---------------------------------------------------------------------------

interface EngineConfig {
  name: string;
  baseUrl: string | null;
  model: string;
}

/**
 * Call `prompt` against each configured engine and print responses.
 *
 * TODO:
 *   1. For each engine, if baseUrl is null, print "SKIPPED".
 *   2. Otherwise create an OpenAICompatibleProvider pointing at baseUrl.
 *   3. Call provider.chat() with the prompt.
 *   4. Print: "--- <name> ---\n<response.slice(0,200)>\n".
 *   5. Handle errors gracefully.
 */
async function runAgainstEngines(
  prompt: string,
  enginesConfig: EngineConfig[],
): Promise<void> {
  // TODO: implement runAgainstEngines
  throw new Error("TODO: implement runAgainstEngines()");
}

// ---------------------------------------------------------------------------
// Engine table
// ---------------------------------------------------------------------------

/**
 * Print a formatted table of all four engines.
 *
 * Columns: Engine | Use case | Hardware | Key feature | OpenAI-compatible?
 *
 * TODO: print header, divider, then one row per engine from ENGINES.
 */
function printEngineTable(): void {
  // TODO: implement printEngineTable
  throw new Error("TODO: implement printEngineTable()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  // Engine reference table
  printEngineTable();

  // Recommendation demo
  console.log("\n" + "=".repeat(60));
  console.log("RECOMMENDATION DEMO");
  console.log("=".repeat(60));
  const testCases = [
    "I need to serve 1000 concurrent users in production",
    "I want to run a model locally on my laptop with minimal setup",
    "I'm building an embedded device with no internet access",
    "I need to integrate with a HuggingFace model and multi-GPU server",
  ];
  for (const uc of testCases) {
    const rec = recommendEngine(uc);
    console.log(`\n  Use case: ${uc.slice(0, 60)}`);
    console.log(`  Recommended: ${rec.engine}`);
    console.log(`  Reason: ${rec.reason}`);
  }

  // Live demo
  console.log("\n" + "=".repeat(60));
  console.log("LIVE DEMO (Ollama only — others require separate installation)");
  console.log("=".repeat(60));

  const PROMPT =
    "What is PagedAttention and why does it improve GPU utilisation? One paragraph.";

  const enginesToTry: EngineConfig[] = [
    {
      name: "Ollama (localhost:11434)",
      baseUrl: "http://localhost:11434/v1",
      model: "llama3.2",
    },
    // Add more if running vLLM or TGI locally:
    // { name: "vLLM (localhost:8000)", baseUrl: "http://localhost:8000/v1", model: "..." },
  ];

  await runAgainstEngines(PROMPT, enginesToTry);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
