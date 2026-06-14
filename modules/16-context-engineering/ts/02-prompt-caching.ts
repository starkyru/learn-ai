/**
 * Task 2 — Prompt caching 🟢
 *
 * What this teaches:
 *   - Large, repeated prefixes (a long system prompt, a document, tool definitions)
 *     normally re-charge the full input cost on every API call.
 *   - Prompt caching avoids this: the provider stores the KV-cache of a prefix and
 *     re-uses it on subsequent calls, charging a fraction of the normal rate.
 *   - Measuring cache hits via the usage field confirms the saving is real.
 *
 * Beyond the abstraction:
 *   llm-core's chat() does not expose caching parameters. This task uses the
 *   Anthropic and/or OpenAI SDKs directly. That is intentional — it teaches where
 *   the abstraction breaks and why dropping to the raw SDK is sometimes necessary.
 *
 * Environment variables:
 *   ANTHROPIC_API_KEY — required for the Anthropic path
 *   ANTHROPIC_MODEL   — model to use (default: claude-opus-4-8)
 *   OPENAI_API_KEY    — required for the OpenAI path
 *   OPENAI_CHAT_MODEL — model to use (default: gpt-4o-mini)
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/02-prompt-caching.ts
 */

import "dotenv/config";

// ---------------------------------------------------------------------------
// A large "document" that forms the cacheable prefix (> 1024 tokens).
// ---------------------------------------------------------------------------
const LARGE_DOCUMENT = `
# The Complete Guide to Retrieval-Augmented Generation

## Chapter 1: Introduction

Retrieval-Augmented Generation (RAG) is a paradigm for enhancing large language models
by grounding their responses in retrieved external knowledge rather than relying solely
on information encoded in their parameters during training.

The core insight is simple: language models are excellent at reasoning and language
generation, but their knowledge is frozen at training time. RAG decouples knowledge
storage (a searchable document store) from reasoning (the LLM), allowing the system
to access up-to-date, domain-specific, or private information without expensive fine-tuning.

## Chapter 2: Architecture

A typical RAG system consists of three subsystems:

### 2.1 The Indexing Pipeline
Documents are ingested, cleaned, split into chunks, embedded into dense vectors using an
embedding model, and stored in a vector database. The embedding model maps text into a
high-dimensional space where semantic similarity corresponds to geometric proximity.

Common chunking strategies:
- Fixed-size chunking: split every N characters (simple but may cut sentences).
- Sentence-boundary chunking: split at sentence ends to preserve linguistic units.
- Semantic chunking: split when the semantic similarity between adjacent sentences drops
  below a threshold.
- Hierarchical chunking: store both small (precise) and large (context-rich) chunks.

### 2.2 The Retrieval Engine
At query time, the user's query is embedded with the same model used during indexing.
The top-K nearest vectors are retrieved from the database, typically using Approximate
Nearest Neighbour (ANN) algorithms such as HNSW or IVF.

Retrieval can be improved with:
- Hybrid search: combine dense (vector) and sparse (BM25 keyword) retrieval using
  Reciprocal Rank Fusion (RRF) to merge the two ranked lists.
- Re-ranking: apply a cross-encoder model to the top-K results to re-order them.
- Query expansion: generate multiple paraphrases of the user's query.
- HyDE: ask the LLM to generate a hypothetical answer, embed that, and use it as query.

### 2.3 The Generation Stage
The retrieved chunks are formatted into a context section of the prompt and passed to
the LLM along with the original query. The model generates an answer grounded in the
provided context.

## Chapter 3: Evaluation

RAG systems require specialised evaluation metrics: Faithfulness, Answer Relevance,
Context Precision, and Context Recall. Automated tools include RAGAS, TruLens, and DeepEval.

## Chapter 4: Production Concerns

Deploying RAG at scale: stale indexes, latency, context window management,
chunk boundary artefacts, and security (prompt injection via retrieved content).
`.trim();

const QUESTIONS = [
  "What is HyDE and how does it improve retrieval?",
  "Name three production challenges mentioned in the document.",
];

interface CallStats {
  callNumber: number;
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  latencyMs: number;
}

function printStats(stats: CallStats, provider: string): void {
  console.log(
    `  Call #${stats.callNumber}: ` +
    `input=${String(stats.inputTokens).padStart(5)}  ` +
    `cache_read=${String(stats.cacheReadTokens).padStart(5)}  ` +
    `cache_write=${String(stats.cacheWriteTokens).padStart(5)}  ` +
    `output=${String(stats.outputTokens).padStart(4)}  ` +
    `latency=${stats.latencyMs.toFixed(0)}ms`
  );
}

// ---------------------------------------------------------------------------
// TODO 1: Implement demoAnthropicCaching.
//         Use the @anthropic-ai/sdk directly.
//
//         For caching, the system message must be sent as a content block with
//         cache_control. Example:
//
//         const response = await client.beta.messages.create({
//           model: process.env.ANTHROPIC_MODEL ?? "claude-opus-4-8",
//           max_tokens: 512,
//           system: [
//             {
//               type: "text",
//               text: LARGE_DOCUMENT,
//               cache_control: { type: "ephemeral" },
//             },
//           ],
//           messages: [{ role: "user", content: question }],
//           betas: ["prompt-caching-2024-07-31"],
//         });
//
//         Read usage.cache_read_input_tokens and usage.cache_creation_input_tokens.
//         Make two calls; on the second call cache_read_input_tokens > 0.
// ---------------------------------------------------------------------------
async function demoAnthropicCaching(): Promise<void> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.log("  ANTHROPIC_API_KEY not set — skipping Anthropic demo.");
    return;
  }

  // TODO: implement
  // import Anthropic from "@anthropic-ai/sdk";
  // const client = new Anthropic({ apiKey });
  // const model = process.env.ANTHROPIC_MODEL ?? "claude-opus-4-8";
  // for (let i = 0; i < QUESTIONS.length; i++) {
  //   const start = performance.now();
  //   const response = await client.beta.messages.create({ ... });
  //   const latencyMs = performance.now() - start;
  //   const usage = response.usage;
  //   printStats({ callNumber: i + 1, ..., latencyMs }, "anthropic");
  // }
  throw new Error("TODO: implement demoAnthropicCaching");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement demoOpenAICaching.
//         OpenAI caches automatically for inputs > 1024 tokens — no extra params needed.
//
//         Use the openai SDK:
//         const response = await client.chat.completions.create({
//           model: process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini",
//           messages: [
//             { role: "system", content: LARGE_DOCUMENT },
//             { role: "user", content: question },
//           ],
//         });
//
//         Read response.usage?.prompt_tokens_details?.cached_tokens to confirm hits.
//         Make two calls; on the second call cached_tokens > 0.
// ---------------------------------------------------------------------------
async function demoOpenAICaching(): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.log("  OPENAI_API_KEY not set — skipping OpenAI demo.");
    return;
  }

  // TODO: implement
  // import OpenAI from "openai";
  // const client = new OpenAI({ apiKey });
  // const model = process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini";
  // for (let i = 0; i < QUESTIONS.length; i++) { ... }
  throw new Error("TODO: implement demoOpenAICaching");
}

async function main() {
  console.log("=== Task 2: Prompt Caching ===\n");
  console.log(`Large document: ${LARGE_DOCUMENT.length} chars`);
  console.log(`Questions: ${JSON.stringify(QUESTIONS)}\n`);

  console.log("--- Anthropic (cache_control breakpoints) ---");
  try {
    await demoAnthropicCaching();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.log(`  ${msg.startsWith("TODO") ? msg : "ERROR: " + msg}`);
  }

  console.log();
  console.log("--- OpenAI (automatic caching) ---");
  try {
    await demoOpenAICaching();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.log(`  ${msg.startsWith("TODO") ? msg : "ERROR: " + msg}`);
  }

  console.log();
  console.log("Observation:");
  console.log("  On the first call: cacheReadTokens = 0, cacheWriteTokens > 0.");
  console.log("  On the second call: cacheReadTokens > 0, cost is lower.");
  console.log("  Cache TTL is ~5 minutes for Anthropic — re-run quickly to see the hit.");
  console.log("  OpenAI caching is automatic; the same input bytes reuse the cache.");
}

main().catch(console.error);
