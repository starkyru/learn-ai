/**
 * Task 3 🟡 — Chunking strategies.
 *
 * What you'll learn:
 *   - Why chunk size dramatically affects retrieval quality
 *   - Fixed-size chunking: simple but can split sentences mid-thought
 *   - Sentence-based chunking: respects natural boundaries
 *   - Overlapping chunks: ensures context at boundaries isn't lost
 *   - How to eyeball quality differences with the same query
 *
 * How to run:
 *   pnpm tsx modules/04-embeddings-vectors/ts/03-chunking-strategies.ts
 *
 * The harness embeds a long-ish document three ways and shows which
 * strategy retrieves the best chunk for a given query.
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Sample long document (works without data/corpus/ present)
// ---------------------------------------------------------------------------

const LONG_DOC = `
Embeddings and Vector Spaces

An embedding is a learned mapping from a discrete object — a word, a sentence,
an image, a user — into a continuous vector space. The key property is that
semantically similar objects land close together. When you embed the sentences
"The cat sat on the mat" and "A feline rested on the rug", their vectors will
be much closer than either is to "The stock market fell sharply today".

How are embeddings trained? Modern text embeddings come from transformer models
fine-tuned on contrastive objectives. In contrastive learning, the model is
shown pairs of similar and dissimilar sentences and trained to minimise the
distance between similar pairs while maximising it for dissimilar ones. This
process — sometimes called metric learning — shapes the geometry of the space.

Cosine similarity is the standard metric. Given two vectors a and b, cosine
similarity equals dot(a, b) divided by (|a| * |b|). Because embedding models
typically L2-normalise their outputs, |a| = |b| = 1 and cosine reduces to the
plain dot product. Values range from -1 (opposite) through 0 (orthogonal) to 1
(identical).

Approximate Nearest Neighbour search (ANN) solves the scaling problem. Brute-
force comparison is O(n*d) per query — for one million 1536-dimensional vectors
that is 1.5 billion multiplications. ANN algorithms like HNSW (Hierarchical
Navigable Small World) build a graph structure at index time so queries touch
only a small fraction of vectors. The trade-off: a small probability of missing
the true nearest neighbour. In practice the recall@k is above 99 % at typical
settings, which is more than good enough for RAG workloads.

Chunking is the practice of splitting a long document into smaller passages
before embedding. This matters because embedding models have a fixed token
limit (usually 256–512 tokens) and the quality of the embedding degrades when
you stuff too much text in. Well-chosen chunk boundaries also mean the retrieved
chunk is coherent and self-contained. Common strategies include fixed-size
chunking (split every N tokens), sentence-based chunking (split on sentence
boundaries), and overlapping chunking (each chunk shares some tokens with the
next to avoid losing context at the boundary).

Hybrid search combines dense retrieval (vectors) with sparse retrieval (keyword
matching via BM25 or TF-IDF). The intuition is simple: dense retrieval excels
at semantic / paraphrase queries ("feline" matching "cat") while BM25 excels at
exact-match queries (model names, product codes, rare terms). Reciprocal Rank
Fusion (RRF) is a simple, effective way to merge the two ranked lists without
needing to calibrate scores across different scales.
`.trim();

// ---------------------------------------------------------------------------
// Chunking strategies — implement each one
// ---------------------------------------------------------------------------

/**
 * Fixed-size chunker.
 *
 * Split text into chunks of roughly `chunkSize` characters.
 * No overlap. Split at word boundaries (don't cut inside a word).
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   Walk through the text. When you've accumulated >= chunkSize characters,
 *   find the next space and cut there. Push the accumulated chunk and start
 *   fresh.
 *
 * Edge cases to handle:
 *   - The last chunk may be shorter than chunkSize.
 *   - Strip leading/trailing whitespace from each chunk.
 */
export function fixedSizeChunker(text: string, chunkSize: number = 300): string[] {
  // TODO: implement fixed-size chunking.
  //
  // Hint: one approach — split on whitespace into words, then accumulate words
  // until adding the next word would exceed chunkSize. Push the accumulated
  // chunk and start fresh.
  throw new Error("TODO: implement fixedSizeChunker()");
}

/**
 * Sentence-based chunker.
 *
 * Split text into chunks where each chunk contains `sentencesPerChunk`
 * consecutive sentences.
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   1. Split text into sentences. A simple heuristic: split on /[.!?]\s+/
 *      (punctuation followed by whitespace). This is imperfect for abbreviations
 *      but fine for our corpus.
 *   2. Group sentences into windows of `sentencesPerChunk`.
 *   3. Join each group with a space.
 */
export function sentenceChunker(text: string, sentencesPerChunk: number = 3): string[] {
  // TODO: implement sentence-based chunking.
  //
  // Hint: text.split(/(?<=[.!?])\s+/) is a lookbehind split — it keeps the
  // punctuation with the preceding sentence. Fall back to a simple split if
  // lookbehind isn't available.
  throw new Error("TODO: implement sentenceChunker()");
}

/**
 * Overlapping chunker.
 *
 * Like fixedSizeChunker, but each chunk overlaps the previous one by
 * `overlap` characters. This ensures that context at a boundary isn't lost.
 *
 * TODO: implement this function.
 *
 * Algorithm (word-level version):
 *   Same word accumulation as fixedSizeChunker, but after pushing a chunk,
 *   rewind by `overlap` words rather than starting at 0.
 *
 * Example: chunkSize=200, overlap=50 → chunk 2 starts 50 chars before chunk 1 ended.
 */
export function overlappingChunker(
  text: string,
  chunkSize: number = 300,
  overlap: number = 100
): string[] {
  // TODO: implement overlapping chunking.
  //
  // One approach: split into words, advance by a window that steps forward
  // by (chunkSize / avgWordLen - overlapWords) each time.
  // Simpler: just work with character slices and find the nearest space.
  throw new Error("TODO: implement overlappingChunker()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function retrieveWithStrategy(
  name: string,
  chunks: string[],
  queryText: string,
  queryVec: number[]
): Promise<void> {
  // Simple cosine: we inline a tiny version here so this file is self-contained.
  function cosine(a: number[], b: number[]): number {
    let dot = 0, magA = 0, magB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i] * b[i];
      magA += a[i] * a[i];
      magB += b[i] * b[i];
    }
    const denom = Math.sqrt(magA) * Math.sqrt(magB);
    return denom === 0 ? 0 : dot / denom;
  }

  const provider = getProvider();
  const embedResult = await provider.embed(chunks);
  const scores = embedResult.vectors.map((v, i) => ({ i, score: cosine(queryVec, v), text: chunks[i] }));
  scores.sort((a, b) => b.score - a.score);

  const top = scores[0];
  console.log(`  [${name}] ${chunks.length} chunks | best score=${top.score.toFixed(4)}`);
  console.log(`    Top chunk (${top.text.length} chars): "${top.text.slice(0, 120)}..."`);
}

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} | embed model: ${provider.embedModel}\n`);

  const query = "How does cosine similarity work with normalised embeddings?";
  const [qVec] = (await provider.embed([query])).vectors;

  console.log(`Query: "${query}"\n`);

  const fixed = fixedSizeChunker(LONG_DOC, 300);
  const sentence = sentenceChunker(LONG_DOC, 3);
  const overlapping = overlappingChunker(LONG_DOC, 300, 100);

  await retrieveWithStrategy("fixed-size  ", fixed, query, qVec);
  await retrieveWithStrategy("sentence    ", sentence, query, qVec);
  await retrieveWithStrategy("overlapping ", overlapping, query, qVec);

  console.log("\n--- Chunk counts ---");
  console.log(`  fixed-size:   ${fixed.length} chunks`);
  console.log(`  sentence:     ${sentence.length} chunks`);
  console.log(`  overlapping:  ${overlapping.length} chunks`);
  console.log();
  console.log("Reflection questions:");
  console.log("  1. Which strategy retrieved the most relevant passage?");
  console.log("  2. Are there queries where fixed-size wins? Where does it fail?");
  console.log("  3. What's the storage cost of overlapping vs. the quality gain?");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
