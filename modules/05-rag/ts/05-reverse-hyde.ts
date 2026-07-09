/**
 * Task 5 🟡 — Reverse HyDE (index-time question generation).
 *
 * What you'll learn:
 *   - Forward HyDE (Task 2) fixed the query side: turn the QUESTION into a
 *     hypothetical ANSWER so it lands in answer-space before retrieving.
 *   - Reverse HyDE fixes the INDEX side instead: at index time, ask the LLM for
 *     the questions each chunk would answer, embed THOSE questions, and store
 *     them pointing back at the chunk. Now a real user question is compared
 *     question-to-question — the same surface form — which closes the
 *     query/answer embedding gap without any per-query LLM call.
 *   - The trade-off vs forward HyDE: reverse pays once at index time (LLM calls
 *     × chunks) and adds nothing to query latency; forward pays one LLM call on
 *     every query. Reverse also stores several vectors per chunk.
 *
 * How to run:
 *   pnpm tsx modules/05-rag/ts/05-reverse-hyde.ts
 *
 * Needs an embedding provider (LLM_PROVIDER=openai|ollama|nvidia|lmstudio|gemini;
 * NOT anthropic — it has no embed()). Also uses chat() to generate questions.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Corpus + helpers (same shape as Task 2)
// ---------------------------------------------------------------------------

interface Chunk {
  id: string;
  text: string;
  source: string;
}
interface RetrievedChunk extends Chunk {
  score: number;
}
interface QuestionEntry {
  chunk: Chunk;
  question: string;
  vector: number[];
}

const CORPUS_DOCS = [
  {
    source: "hnsw",
    text: `HNSW builds a multi-layer proximity graph. Each node links to nearby nodes at several granularities; search starts coarse at the top layer and greedily descends to finer layers. This makes approximate nearest-neighbour search run in nearly logarithmic time with recall@10 above 99%.`,
  },
  {
    source: "cosine",
    text: `The angle between two vectors, computed as dot(a,b) divided by the product of their magnitudes, ranges from -1 to 1. Because most embedding models L2-normalise their output, this reduces to a plain dot product. It is the default way to compare two pieces of text once embedded.`,
  },
  {
    source: "chunking",
    text: `Splitting a long document into shorter passages before embedding keeps each vector focused. Fixed-size cuts every N characters; sentence-based groups N sentences; overlapping adds a stride so neighbours share tokens and no context is lost at a boundary.`,
  },
  {
    source: "reranking",
    text: `A second-stage step: first retrieve a broad candidate set with a fast dense retriever, then rescore each candidate with a slower cross-encoder that reads the query and passage together. It consistently lifts precision at the top ranks.`,
  },
  {
    source: "faithfulness",
    text: `To check whether a generated answer is grounded, decompose it into individual claims and verify each against the retrieved context. The fraction of claims supported by the context is the faithfulness score; unsupported claims signal hallucination.`,
  },
];

function cosine(a: number[], b: number[]): number {
  let dot = 0,
    magA = 0,
    magB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    magA += a[i] * a[i];
    magB += b[i] * b[i];
  }
  const d = Math.sqrt(magA) * Math.sqrt(magB);
  return d === 0 ? 0 : dot / d;
}

function chunksFromDocs(docs: typeof CORPUS_DOCS): Chunk[] {
  return docs.map((d) => ({ id: d.source, text: d.text, source: d.source }));
}

// ---------------------------------------------------------------------------
// Reverse HyDE index — one entry per generated question, all pointing at a chunk
// ---------------------------------------------------------------------------

/**
 * Ask the LLM for `n` distinct questions that `chunk` answers.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build a ChatMessage[]: a system message casting the model as a question
 *      generator, and a user message asking for exactly `n` short, distinct
 *      questions this passage would answer — one per line, no numbering
 *      (interpolate chunk.text and n).
 *   2. Call provider.chat(messages, { temperature: ..., maxTokens: ... }); a
 *      little temperature helps produce varied questions.
 *   3. Split result.text into lines, trim whitespace and any leading
 *      bullets/numbers, drop blanks, return up to n questions.
 */
async function generateQuestions(
  chunk: Chunk,
  provider: ReturnType<typeof getProvider>,
  n = 3,
): Promise<string[]> {
  throw new Error("TODO: implement generateQuestions()");
}

/**
 * For each chunk, generate questions and embed each one.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. For every chunk, call generateQuestions(chunk, provider, n).
 *   2. Collect ALL questions across all chunks and embed them in ONE
 *      provider.embed([...]) call (batching keeps it fast/cheap).
 *   3. Build one QuestionEntry { chunk, question, vector } per question, keeping
 *      each question aligned with its chunk and its vector (mind the ordering).
 *
 * Hint: Promise.all over chunks to generate questions concurrently, then flatten.
 */
async function buildReverseHydeIndex(
  chunks: Chunk[],
  provider: ReturnType<typeof getProvider>,
  n = 3,
): Promise<QuestionEntry[]> {
  throw new Error("TODO: implement buildReverseHydeIndex()");
}

/**
 * Retrieve chunks by matching the query against generated questions.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Embed the incoming question with provider.embed([question]).
 *   2. Score every QuestionEntry by cosine(queryVec, entry.vector).
 *   3. Collapse to chunks: a chunk's score is its BEST-matching question's score
 *      (a chunk can own several question entries — keep the max, don't
 *      double-count).
 *   4. Return the top-k chunks as RetrievedChunk sorted by score descending.
 */
async function retrieveReverseHyde(
  question: string,
  index: QuestionEntry[],
  provider: ReturnType<typeof getProvider>,
  k = 3,
): Promise<RetrievedChunk[]> {
  throw new Error("TODO: implement retrieveReverseHyde()");
}

// ---------------------------------------------------------------------------
// Baseline: embed the chunk text directly (naive retrieval from Task 1)
// ---------------------------------------------------------------------------

async function retrieveBaseline(
  question: string,
  chunks: Chunk[],
  chunkVectors: number[][],
  provider: ReturnType<typeof getProvider>,
  k = 3,
): Promise<RetrievedChunk[]> {
  const [qv] = (await provider.embed([question])).vectors;
  return chunks
    .map((c, i) => ({ ...c, score: cosine(qv, chunkVectors[i]) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}\n`);

  const chunks = chunksFromDocs(CORPUS_DOCS);
  const chunkVectors = (await provider.embed(chunks.map((c) => c.text))).vectors;

  console.log("Building reverse-HyDE index (generating questions per chunk)…");
  const index = await buildReverseHydeIndex(chunks, provider, 3);
  console.log(`  ${chunks.length} chunks → ${index.length} question vectors\n`);

  // Deliberately phrased far from the chunk wording, to stress the query/answer gap.
  const questions = [
    "Why can I search a huge vector set so quickly?",
    "How do I tell if the model made something up?",
  ];

  for (const q of questions) {
    console.log(`\nQuestion: "${q}"`);

    console.log("  [Baseline] embed question vs chunk text:");
    for (const r of await retrieveBaseline(q, chunks, chunkVectors, provider, 3)) {
      console.log(`    [${r.score.toFixed(4)}] ${r.id}: ${r.text.slice(0, 60)}…`);
    }

    console.log("  [Reverse HyDE] embed question vs generated questions:");
    for (const r of await retrieveReverseHyde(q, index, provider, 3)) {
      console.log(`    [${r.score.toFixed(4)}] ${r.id}: ${r.text.slice(0, 60)}…`);
    }
  }

  console.log("\nReflection:");
  console.log(
    "  1. Did reverse HyDE rank the intended chunk higher than the baseline?",
  );
  console.log("  2. Forward HyDE (Task 2) vs reverse: which adds per-query latency?");
  console.log("  3. What's the storage cost of N question vectors per chunk?");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
