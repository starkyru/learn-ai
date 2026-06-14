/**
 * Task 2 🟡 — Better retrieval: reranking + HyDE.
 *
 * What you'll learn:
 *   - Why two-stage retrieval (retrieve-then-rerank) improves precision
 *   - How LLM-based reranking works (prompt the model to judge relevance)
 *   - HyDE: generate a hypothetical answer and embed THAT to retrieve
 *   - When each technique helps and when it adds latency without benefit
 *
 * How to run:
 *   pnpm tsx modules/05-rag/ts/02-better-retrieval.ts
 *
 * This file builds on the index from task 1. The corpus and index-building
 * helpers are copied here so the file runs standalone.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Shared corpus + index helpers (identical to task 1)
// ---------------------------------------------------------------------------

interface Chunk { id: string; text: string; source: string; }
interface RetrievedChunk extends Chunk { score: number; }
interface VectorEntry { chunk: Chunk; vector: number[]; }

const CORPUS_DOCS = [
  { source: "embeddings-guide", text: `Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space, even if they use different words. Embedding models are trained using contrastive learning — similar pairs are pulled together and dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and 1536 (OpenAI ada-002).` },
  { source: "similarity-metrics", text: `Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude.` },
  { source: "ann-algorithms", text: `Approximate Nearest Neighbour (ANN) algorithms speed up similarity search from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable Small World) is the most popular: it builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer (coarse) and greedily descends to the bottom layer (fine). Typical recall@10 is above 99% with index build time measured in seconds for millions of vectors.` },
  { source: "chunking-strategies", text: `Chunking splits a long document into shorter passages before embedding. Embedding models have a token limit (usually 256–512 tokens) and quality degrades when you exceed it. Fixed-size chunking splits every N characters at word boundaries. Sentence-based chunking groups N consecutive sentences. Overlapping chunking adds a stride so consecutive chunks share some tokens — this prevents losing context that falls at a boundary.` },
  { source: "rag-overview", text: `Retrieval-Augmented Generation (RAG) combines a retriever with a large language model. The pipeline: (1) at index time, chunk documents and embed each chunk; (2) at query time, embed the question, retrieve the top-k most similar chunks, stuff them into a prompt, and ask the LLM to answer based only on the provided context.` },
  { source: "reranking", text: `Reranking is a second-stage retrieval step. First retrieve a broad set of candidates (top-50) with a fast dense retriever. Then score each candidate with a more powerful but slower cross-encoder model that jointly encodes the query and passage. Reranking consistently improves precision@k because the cross-encoder sees the query and passage together.` },
  { source: "hyde", text: `HyDE (Hypothetical Document Embeddings) is a query reformulation technique. Instead of embedding the raw question, generate a hypothetical answer using the LLM, then embed that. The hypothesis lives in the same semantic space as real answers, so retrieval tends to find better matches. HyDE works best when the question and the expected answer have very different surface forms.` },
  { source: "rag-evaluation", text: `RAG evaluation uses LLM-as-judge to score three dimensions: (1) Faithfulness — is every claim in the answer grounded in the retrieved context? (2) Context relevance — are the retrieved chunks actually relevant to the question? (3) Answer relevance — does the answer address the question? A common finding: high retrieval recall but low faithfulness means the LLM is hallucinating despite having the right context.` },
];

function chunkDocuments(docs: typeof CORPUS_DOCS, wordsPerChunk = 80): Chunk[] {
  const chunks: Chunk[] = [];
  for (const doc of docs) {
    const words = doc.text.split(/\s+/).filter(Boolean);
    let i = 0, idx = 0;
    while (i < words.length) {
      chunks.push({
        id: `${doc.source}-chunk-${idx}`,
        text: words.slice(i, i + wordsPerChunk).join(" "),
        source: doc.source,
      });
      i += wordsPerChunk;
      idx++;
    }
  }
  return chunks;
}

function cosine(a: number[], b: number[]): number {
  let dot = 0, magA = 0, magB = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i]*b[i]; magA += a[i]*a[i]; magB += b[i]*b[i]; }
  const d = Math.sqrt(magA) * Math.sqrt(magB);
  return d === 0 ? 0 : dot / d;
}

async function buildIndex(chunks: Chunk[], provider: ReturnType<typeof getProvider>): Promise<VectorEntry[]> {
  const texts = chunks.map((c) => c.text);
  const { vectors } = await provider.embed(texts);
  return chunks.map((c, i) => ({ chunk: c, vector: vectors[i] }));
}

function retrieveTopK(queryVec: number[], index: VectorEntry[], k: number): RetrievedChunk[] {
  return index
    .map((e) => ({ ...e.chunk, score: cosine(queryVec, e.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}

// ---------------------------------------------------------------------------
// Technique 1: LLM Reranker
// ---------------------------------------------------------------------------

/**
 * Rerank a list of retrieved chunks using the LLM as a judge.
 *
 * What: Ask the LLM to score each chunk for relevance to the question
 *       (0–10). Sort by score. Return top k.
 *
 * Why: The bi-encoder used at retrieval time encodes query and passage
 *      independently. A cross-encoder (or LLM reranker) sees both together,
 *      giving it much better understanding of relevance. The trade-off is
 *      latency — we call the LLM once per candidate chunk.
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   For each chunk, call provider.chat() with a prompt like:
 *     "Rate the relevance of the following passage to the question on a
 *      scale of 0–10. Reply with ONLY the integer score.
 *      Question: {question}
 *      Passage: {chunk.text}"
 *   Parse the integer from the response.
 *   Sort descending by score. Return top k.
 *
 * Hint: use parseInt(result.text.trim(), 10). Guard against NaN.
 */
async function llmRerank(
  question: string,
  candidates: RetrievedChunk[],
  provider: ReturnType<typeof getProvider>,
  k: number = 3
): Promise<RetrievedChunk[]> {
  // TODO: implement LLM reranking.
  //
  // For cost efficiency, make the calls in parallel:
  //   const scores = await Promise.all(candidates.map(async (chunk) => {
  //     const messages: ChatMessage[] = [...];
  //     const result = await provider.chat(messages, { temperature: 0, maxTokens: 5 });
  //     const score = parseInt(result.text.trim(), 10);
  //     return { ...chunk, score: isNaN(score) ? 0 : score };
  //   }));
  //   return scores.sort((a, b) => b.score - a.score).slice(0, k);
  throw new Error("TODO: implement llmRerank()");
}

// ---------------------------------------------------------------------------
// Technique 2: HyDE (Hypothetical Document Embeddings)
// ---------------------------------------------------------------------------

/**
 * Query rewriting via HyDE.
 *
 * What: Generate a hypothetical answer to the question, then embed THAT
 *       instead of the raw question.
 *
 * Why: The question "What is HNSW?" lives in question-space. Real corpus
 *      chunks live in answer-space. The gap causes retrieval to sometimes
 *      miss the right chunk. A hypothetical answer is already in answer-space,
 *      so its embedding is closer to the real answer chunks.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Ask the LLM: "Write a short, factual paragraph that would be a
 *      good answer to this question. Be concise (2–3 sentences).
 *      Question: {question}"
 *   2. Embed the generated hypothesis.
 *   3. Return the embedding vector (number[]).
 */
async function hydeQueryVector(
  question: string,
  provider: ReturnType<typeof getProvider>
): Promise<number[]> {
  // TODO: implement HyDE.
  throw new Error("TODO: implement hydeQueryVector()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}`);

  // Build index once
  const chunks = chunkDocuments(CORPUS_DOCS, 80);
  const index = await buildIndex(chunks, provider);
  console.log(`Index: ${index.length} chunks\n`);

  const questions = [
    "How does HNSW achieve fast approximate nearest neighbour search?",
    "What is HyDE and why does it improve retrieval quality?",
  ];

  for (const q of questions) {
    console.log(`\nQuestion: "${q}"`);
    const [rawVec] = (await provider.embed([q])).vectors;

    // ── Standard retrieval (top-8 candidates, then rerank to top-3) ─────────
    console.log("\n  [Standard] retrieve top-8 → rerank to top-3");
    const candidates = retrieveTopK(rawVec, index, 8);
    const reranked = await llmRerank(q, candidates, provider, 3);
    for (const r of reranked) {
      console.log(`    [score=${r.score.toFixed(2)}] ${r.id}: ${r.text.slice(0, 70)}...`);
    }

    // ── HyDE retrieval ───────────────────────────────────────────────────────
    console.log("\n  [HyDE] generate hypothesis → embed → retrieve top-3");
    const hydeVec = await hydeQueryVector(q, provider);
    const hydeResults = retrieveTopK(hydeVec, index, 3);
    for (const r of hydeResults) {
      console.log(`    [score=${r.score.toFixed(4)}] ${r.id}: ${r.text.slice(0, 70)}...`);
    }

    console.log("\n  Reflection: Do HyDE and reranking surface different chunks?");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
