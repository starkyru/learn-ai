/**
 * Task 1 🟡 — Contextual Retrieval (Anthropic, 2024).
 *
 * What you'll learn:
 *   - Why a chunk that's clear to a human can be invisible to a retriever
 *   - How prepending LLM-generated context BEFORE embedding fixes it
 *   - That the text you EMBED and the text you SHOW the generator can differ
 *
 * How to run:
 *   LLM_PROVIDER=openai pnpm tsx modules/05b-advanced-rag/ts/01-contextual-retrieval.ts
 *   (any provider with embeddings: openai / ollama / nvidia / lmstudio — NOT anthropic)
 *
 * The harness builds two indexes — naive (raw chunks) and contextual (chunk +
 * generated context) — and compares retrieval. Fill in the two TODO functions.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

type Provider = ReturnType<typeof getProvider>;

// ---------------------------------------------------------------------------
// Corpus — each chunk is deliberately "context-poor" on its own.
// ---------------------------------------------------------------------------

interface Document {
  id: string;
  title: string;
  text: string;
}
interface Chunk {
  id: string;
  docId: string;
  text: string;
} // ORIGINAL chunk text
interface IndexEntry {
  chunk: Chunk;
  embedText: string;
  vector: number[];
}

const DOCUMENTS: Document[] = [
  {
    id: "claude-card",
    title: "Claude 3.5 Sonnet model card (2024)",
    text:
      "Claude 3.5 Sonnet is Anthropic's mid-tier model released in 2024. " +
      "It was evaluated on a suite of academic benchmarks. " +
      "It scored 88.7% on the MMLU knowledge benchmark. " +
      "On graduate-level reasoning (GPQA) it reached 59.4%. " +
      "The model runs at roughly twice the speed of the previous Opus model.",
  },
  {
    id: "acme-q3",
    title: "Acme Corp Q3 2024 earnings report",
    text:
      "Acme Corp reported its third-quarter 2024 results in October. " +
      "Revenue rose to 4.2 billion dollars for the quarter. " +
      "It grew 3% year over year, slower than the prior quarter. " +
      "The cloud division was the main driver of the increase. " +
      "Management guided to flat growth in the fourth quarter.",
  },
  {
    id: "hnsw-note",
    title: "Note on approximate nearest neighbour search",
    text:
      "HNSW is a graph-based index for vector similarity search. " +
      "It builds a multi-layer navigable small-world graph. " +
      "Queries start at a coarse top layer and descend greedily. " +
      "Recall above 99% is typical at production settings.",
  },
];

function chunkDocument(doc: Document): Chunk[] {
  // One sentence per chunk — small enough to be genuinely context-poor.
  const sentences = doc.text
    .split(". ")
    .map((s) => s.trim())
    .filter(Boolean);
  return sentences.map((s, i) => ({
    id: `${doc.id}-${i}`,
    docId: doc.id,
    text: s.endsWith(".") ? s : s + ".",
  }));
}

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

function retrieve(
  queryVec: number[],
  index: IndexEntry[],
  k: number,
): { entry: IndexEntry; score: number }[] {
  return index
    .map((entry) => ({ entry, score: cosine(queryVec, entry.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}

async function buildNaiveIndex(
  chunks: Chunk[],
  provider: Provider,
): Promise<IndexEntry[]> {
  // Baseline: embed the raw chunk text. Provided for comparison.
  const { vectors } = await provider.embed(chunks.map((c) => c.text));
  return chunks.map((c, i) => ({ chunk: c, embedText: c.text, vector: vectors[i] }));
}

// ---------------------------------------------------------------------------
// TODO 1: situate a chunk inside its document
// ---------------------------------------------------------------------------

/**
 * Return a short (1–2 sentence) context that locates `chunkText` inside
 * `documentText` — naming the document's subject and entities the chunk only
 * refers to by pronoun.
 *
 * TODO: implement this.
 *
 * Steps:
 *   - Build a `ChatMessage[]`: a system message instructing the model to write a
 *     1-2 sentence context that situates a chunk in its document (name the document's
 *     subject and any entity the chunk only refers to indirectly; do NOT repeat the
 *     chunk; output only the context), and a user message that presents the full
 *     `documentText` and the `chunkText` (e.g. wrapped in <document>/<chunk> tags).
 *   - Call `provider.chat(messages, { temperature: 0, maxTokens: ... })` (short cap,
 *     it's only 1-2 sentences).
 *   - Return the reply text, trimmed.
 */
async function situateChunk(
  documentText: string,
  chunkText: string,
  provider: Provider,
): Promise<string> {
  // TODO: implement situateChunk().
  throw new Error("TODO: implement situateChunk()");
}

// ---------------------------------------------------------------------------
// TODO 2: build the contextual index
// ---------------------------------------------------------------------------

/**
 * For each chunk: generate its context, prepend it, embed the AUGMENTED text —
 * but keep the ORIGINAL chunk text in the entry.
 *
 * TODO: implement this.
 *
 * Steps:
 *   1. Build a Map docId -> document text.
 *   2. For each chunk, call situateChunk() with its document text, then prepend that
 *      generated context to the original chunk text to form the augmented text (do
 *      these in parallel with Promise.all).
 *   3. Embed ALL augmented texts in ONE provider.embed([...]) call.
 *   4. Return entries: { chunk, embedText: augmented, vector } — embedText is the
 *      augmented text, but chunk.text stays the original.
 */
async function buildContextualIndex(
  chunks: Chunk[],
  documents: Document[],
  provider: Provider,
): Promise<IndexEntry[]> {
  // TODO: implement buildContextualIndex().
  throw new Error("TODO: implement buildContextualIndex()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const QUERIES = [
  "How much did Acme's revenue grow?", // answer chunk says only "It grew 3%..."
  "What did Claude 3.5 Sonnet score on MMLU?", // answer chunk says only "It scored 88.7%..."
  "How does HNSW search vectors quickly?", // naming-rich already; both should do fine
];

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} (embed: ${provider.embedModel})\n`);

  const chunks = DOCUMENTS.flatMap(chunkDocument);
  console.log(`Corpus: ${DOCUMENTS.length} documents → ${chunks.length} chunks\n`);

  console.log("Building naive index (raw chunks)...");
  const naive = await buildNaiveIndex(chunks, provider);

  console.log("Building contextual index (chunk + generated context)...");
  const contextual = await buildContextualIndex(chunks, DOCUMENTS, provider);

  for (const q of QUERIES) {
    const [qvec] = (await provider.embed([q])).vectors;
    console.log(`\nQuery: "${q}"`);
    for (const [label, idx] of [
      ["naive     ", naive],
      ["contextual", contextual],
    ] as const) {
      const { entry, score } = retrieve(qvec, idx, 1)[0];
      console.log(
        `  [${label}] top1 score=${score.toFixed(4)}  ${entry.chunk.id}: ${entry.chunk.text.slice(0, 60)}`,
      );
    }
  }

  console.log(
    "\nReflection: on the context-poor queries (Acme, Claude), the contextual " +
      "index should rank the right chunk higher — its embedding carries the " +
      "nouns the bare chunk omitted.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
