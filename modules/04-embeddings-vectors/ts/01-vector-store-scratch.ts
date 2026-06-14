/**
 * Task 1 🔴 — Build a vector store FROM SCRATCH (no vector DB library).
 *
 * What you'll learn:
 *   - What a vector is and how embeddings represent meaning as numbers
 *   - How cosine similarity works (dot product of unit vectors)
 *   - How to do brute-force top-k nearest-neighbour search
 *   - Why real ANN indexes (HNSW, IVF) exist — they solve the O(n·d) cost here
 *
 * How to run:
 *   pnpm tsx modules/04-embeddings-vectors/ts/01-vector-store-scratch.ts
 *
 * The harness at the bottom embeds a small corpus and queries it.
 * Your job: fill in the three TODO sections.
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Document {
  id: string;
  text: string;
  metadata?: Record<string, unknown>;
}

interface SearchResult {
  id: string;
  score: number;    // cosine similarity: 1 = identical, 0 = orthogonal, -1 = opposite
  text: string;
  metadata?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// VectorStore — implement the three methods marked TODO
// ---------------------------------------------------------------------------

class VectorStore {
  /** Internal storage: list of (id, vector, metadata). */
  private entries: Array<{ id: string; vector: number[]; text: string; metadata?: Record<string, unknown> }> = [];

  /**
   * Add a document with its pre-computed embedding vector.
   * Called once per document at index time.
   */
  add(id: string, vector: number[], text: string, metadata?: Record<string, unknown>): void {
    // TODO: push { id, vector, text, metadata } into this.entries.
    // One line. Easy warmup — but think about what happens if `id` already exists.
    throw new Error("TODO: implement add()");
  }

  /**
   * Compute cosine similarity between two equal-length vectors.
   *
   * cosine(a, b) = dot(a, b) / (|a| * |b|)
   *
   * Key insight: embedding models typically L2-normalise their output, which
   * means |a| = |b| = 1, so cosine simplifies to plain dot product. But
   * implement the full formula so it works even when vectors aren't normalised.
   *
   * Returns a value in [-1, 1]. Higher = more similar.
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) {
      throw new Error(`Vector length mismatch: ${a.length} vs ${b.length}`);
    }

    // TODO: implement cosine similarity.
    //
    // Steps:
    //   1. Compute the dot product: sum of a[i] * b[i] for all i.
    //   2. Compute |a|: sqrt of sum of a[i]^2.
    //   3. Compute |b|: sqrt of sum of b[i]^2.
    //   4. Guard against zero vectors (return 0 if either magnitude is 0).
    //   5. Return dot / (magA * magB).
    //
    // Hint: a single pass over the vectors can compute all three sums at once.
    throw new Error("TODO: implement cosineSimilarity()");
  }

  /**
   * Return the top-k most similar entries to `queryVector`.
   *
   * This is BRUTE-FORCE: we compare the query against every stored vector.
   * That's O(n·d) per query where n = # docs and d = dimension (e.g. 768).
   * Fine for hundreds of docs; painfully slow for millions — which is exactly
   * why real systems use ANN indexes.
   */
  query(queryVector: number[], k: number = 3): SearchResult[] {
    // TODO: implement brute-force top-k search.
    //
    // Steps:
    //   1. For each entry in this.entries, compute cosineSimilarity(queryVector, entry.vector).
    //   2. Build an array of { id, score, text, metadata } objects.
    //   3. Sort descending by score.
    //   4. Return the first k elements.
    //
    // Tip: Array.prototype.sort is in-place; sort a copy or map first.
    throw new Error("TODO: implement query()");
  }

  /** How many documents are stored? */
  size(): number {
    return this.entries.length;
  }
}

// ---------------------------------------------------------------------------
// Inline fallback corpus (used if data/corpus/ is absent)
// ---------------------------------------------------------------------------

const FALLBACK_CORPUS: Document[] = [
  {
    id: "doc-1",
    text: "Embeddings are dense vector representations of text that capture semantic meaning.",
    metadata: { source: "fallback", topic: "embeddings" },
  },
  {
    id: "doc-2",
    text: "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
    metadata: { source: "fallback", topic: "similarity" },
  },
  {
    id: "doc-3",
    text: "A neural network is composed of layers of interconnected nodes called neurons.",
    metadata: { source: "fallback", topic: "neural networks" },
  },
  {
    id: "doc-4",
    text: "Retrieval-Augmented Generation (RAG) combines search with text generation.",
    metadata: { source: "fallback", topic: "rag" },
  },
  {
    id: "doc-5",
    text: "Approximate nearest neighbour algorithms trade a little accuracy for huge speed gains.",
    metadata: { source: "fallback", topic: "ann" },
  },
  {
    id: "doc-6",
    text: "Large language models are trained to predict the next token in a sequence.",
    metadata: { source: "fallback", topic: "llm" },
  },
  {
    id: "doc-7",
    text: "Chunking splits long documents into smaller pieces before indexing.",
    metadata: { source: "fallback", topic: "chunking" },
  },
  {
    id: "doc-8",
    text: "BM25 is a classic keyword-based ranking function used in search engines.",
    metadata: { source: "fallback", topic: "bm25" },
  },
];

// ---------------------------------------------------------------------------
// Harness — runs when you execute this file
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (embed model: ${provider.embedModel})`);

  // ── Step 1: Embed the corpus ──────────────────────────────────────────────
  console.log("\n[1/3] Embedding corpus documents...");

  const corpus = FALLBACK_CORPUS;
  const texts = corpus.map((d) => d.text);

  const embedResult = await provider.embed(texts);
  console.log(
    `  Embedded ${texts.length} documents → vectors of dimension ${embedResult.vectors[0].length}`
  );

  // ── Step 2: Index into VectorStore ───────────────────────────────────────
  console.log("\n[2/3] Indexing into VectorStore...");
  const store = new VectorStore();

  for (let i = 0; i < corpus.length; i++) {
    store.add(corpus[i].id, embedResult.vectors[i], corpus[i].text, corpus[i].metadata);
  }
  console.log(`  Indexed ${store.size()} documents.`);

  // ── Step 3: Query ─────────────────────────────────────────────────────────
  const queries = [
    "How do I measure text similarity?",
    "What is a neural network?",
    "How does retrieval-augmented generation work?",
  ];

  console.log("\n[3/3] Querying...\n");
  for (const q of queries) {
    const qEmbed = await provider.embed([q]);
    const results = store.query(qEmbed.vectors[0], 3);

    console.log(`Query: "${q}"`);
    for (const r of results) {
      console.log(`  [score=${r.score.toFixed(4)}] ${r.id}: ${r.text.slice(0, 80)}...`);
    }
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
