/**
 * Task 1 — Token budgeting 🟢
 *
 * What this teaches:
 *   - LLMs process tokens, not characters or words. Knowing the exact token count
 *     before sending a request lets you stay within context limits and predict cost.
 *   - When a document is too long to fit in the context window, you must choose a
 *     truncation strategy: keep the start (head), the end (tail), or sacrifice the
 *     middle while preserving both ends (middle-out).
 *   - Each strategy has different recall properties — which part you keep matters.
 *
 * Dependencies (already in package.json):
 *   @dqbd/tiktoken — a WASM port of OpenAI's tiktoken. Remember to call .free() on
 *                    the encoder to avoid WASM memory leaks.
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/01-token-budgeting.ts
 */

import "dotenv/config";
// TODO: uncomment once you understand what these do
// import { get_encoding } from "@dqbd/tiktoken";

// ---------------------------------------------------------------------------
// A long sample text to experiment with.
// ---------------------------------------------------------------------------
const SAMPLE_TEXT = `
Retrieval-Augmented Generation (RAG) is a technique that improves large language model
outputs by retrieving relevant documents from an external knowledge base before generating
a response. Unlike pure parametric models that rely solely on weights learned during
training, RAG systems can incorporate up-to-date or domain-specific information at
inference time. This makes them particularly useful for question answering, enterprise
search, and chatbots that need factual grounding.

The core RAG pipeline consists of three stages. First, during indexing, documents are
split into chunks and embedded into dense vectors using an embedding model. These vectors
are stored in a vector database such as Chroma, Qdrant, or Pinecone. Second, during
retrieval, the user's query is embedded with the same model, and the top-K most similar
chunks are retrieved via approximate nearest-neighbour search. Third, during generation,
the retrieved chunks are prepended to the prompt (often in a "context" section) and the
language model generates an answer conditioned on both the query and the retrieved text.

A number of refinements improve basic RAG. Hybrid search combines dense vector similarity
with sparse keyword search (BM25), which helps for queries with rare or technical terms.
Re-ranking uses a cross-encoder model to re-score the top-K retrieved chunks and reorder
them before passing to the generator. Query expansion generates multiple paraphrases of
the user's question to broaden retrieval coverage. Reciprocal Rank Fusion merges result
lists from multiple retrievers without requiring score calibration.

Evaluating RAG pipelines requires specialised metrics. Faithfulness measures whether the
generated answer is grounded in the retrieved context (no hallucinations). Answer relevance
measures whether the answer actually addresses the question. Context precision and recall
measure whether the right chunks were retrieved. Tools such as RAGAS and TruLens automate
these evaluations on labelled datasets.

Production RAG systems face additional challenges: stale indexes (documents change but
embeddings don't), chunk boundary artefacts (a sentence split mid-concept loses meaning),
retrieval latency (embedding + ANN search adds hundreds of milliseconds), and context
window management (20 retrieved chunks × 300 tokens each = 6000 tokens of context, which
can crowd out reasoning space). Careful engineering of chunk size, overlap, and retrieval
count is required to balance quality and cost.
`.trim();

const MAX_TOKEN_BUDGET = 200; // tight budget to make truncation interesting

// ---------------------------------------------------------------------------
// TODO 1: Implement countTokens using @dqbd/tiktoken (uncomment the import above).
//         - Get an encoder via get_encoding for the "cl100k_base" encoding
//           (GPT-4 / GPT-3.5 tokeniser).
//         - Encode the text and return the number of token ids.
//         - IMPORTANT: call .free() on the encoder before returning, or the WASM
//           encoder leaks memory on every call.
// ---------------------------------------------------------------------------
function countTokens(text: string): number {
  // TODO: implement with @dqbd/tiktoken

  // Rough fallback until you implement the above:
  return Math.ceil(text.split(/\s+/).length * 1.3);
}

// ---------------------------------------------------------------------------
// TODO 2: Implement truncateHead.
//         Keep the FIRST maxTokens tokens; discard the tail.
//         - Encode the text, slice off the leading maxTokens ids, and decode that
//           slice back to text. (enc.decode returns bytes — run it through a
//           TextDecoder to get a string.) Remember enc.free() to avoid the WASM leak.
// ---------------------------------------------------------------------------
function truncateHead(text: string, maxTokens: number): string {
  // TODO: implement with tiktoken (encode -> slice the head -> decode)
  const words = text.split(/\s+/);
  const approx = Math.floor(maxTokens / 1.3);
  return words.slice(0, approx).join(" ");
}

// ---------------------------------------------------------------------------
// TODO 3: Implement truncateTail.
//         Keep the LAST maxTokens tokens; discard the head.
// ---------------------------------------------------------------------------
function truncateTail(text: string, maxTokens: number): string {
  // TODO: implement with tiktoken
  const words = text.split(/\s+/);
  const approx = Math.floor(maxTokens / 1.3);
  return words.slice(-approx).join(" ");
}

// ---------------------------------------------------------------------------
// TODO 4: Implement truncateMiddleOut.
//         Keep the first (maxTokens // 2) tokens AND the last (maxTokens // 2) tokens.
//         Drop everything in the middle.
//         Join the two halves with a "[...TRUNCATED...]" marker.
// ---------------------------------------------------------------------------
function truncateMiddleOut(text: string, maxTokens: number): string {
  // TODO: implement with tiktoken
  const half = Math.floor(maxTokens / 2);
  const head = truncateHead(text, half);
  const tail = truncateTail(text, half);
  return head + "\n\n[...TRUNCATED...]\n\n" + tail;
}

// ---------------------------------------------------------------------------
// TODO 5 (stretch): Implement a smarter sentence-boundary truncation.
//         Instead of cutting mid-token, find the nearest sentence boundary.
// ---------------------------------------------------------------------------
function truncateSentenceBoundary(text: string, maxTokens: number): string {
  throw new Error("TODO: implement sentence-boundary truncation");
}

async function main() {
  console.log("=== Task 1: Token Budgeting ===\n");

  const originalTokens = countTokens(SAMPLE_TEXT);
  console.log(`Original text      : ${SAMPLE_TEXT.length.toString().padStart(6)} chars / ${originalTokens.toString().padStart(5)} tokens`);
  console.log(`Token budget       : ${MAX_TOKEN_BUDGET.toString().padStart(5)} tokens`);
  console.log(`Reduction required : ${Math.max(0, originalTokens - MAX_TOKEN_BUDGET).toString().padStart(5)} tokens\n`);

  // -------------------------------------------------------------------------
  // TODO 6: Apply each strategy and print a results table.
  //         For each strategy: name, result token count, within budget?, what was lost.
  // -------------------------------------------------------------------------

  const strategies: Array<[string, (t: string, m: number) => string, string]> = [
    ["head   (keep start)", truncateHead,        "lost: tail"],
    ["tail   (keep end  )", truncateTail,        "lost: head"],
    ["middle-out         ", truncateMiddleOut,   "lost: middle"],
  ];

  console.log("Strategy".padEnd(30) + "Result tokens".padStart(14) + "Within budget?".padStart(15) + "  Lost");
  console.log("-".repeat(70));

  for (const [name, fn, lost] of strategies) {
    const result = fn(SAMPLE_TEXT, MAX_TOKEN_BUDGET);
    const resultTokens = countTokens(result);
    const within = resultTokens <= MAX_TOKEN_BUDGET ? "yes" : "no  (approx only)";
    console.log(name.padEnd(30) + String(resultTokens).padStart(14) + within.padStart(15) + "  " + lost);
  }

  console.log();
  console.log("Observation:");
  console.log("  head   — best for tasks that need the opening context (introductions, premises).");
  console.log("  tail   — best for tasks that need the latest information (recent events, conclusions).");
  console.log("  middle-out — preserves both ends; middle is least recalled (see lost-in-the-middle, task 4).");

  // -------------------------------------------------------------------------
  // TODO 7 (stretch): Print the first 200 chars of each truncated version so
  //         you can visually inspect what was kept.
  // -------------------------------------------------------------------------
}

main().catch(console.error);
