/**
 * Task 1 🟢 — Naive RAG end-to-end.
 *
 * The full RAG pipeline in one file:
 *   corpus → chunk → embed → store → retrieve → prompt → answer with citations
 *
 * What you'll learn:
 *   - The five stages of RAG: load, chunk, embed, retrieve, generate
 *   - How to inject retrieved context into a prompt (context stuffing)
 *   - How to ask the LLM to cite which chunk each claim came from
 *   - Where naive RAG fails (task 2 improves it)
 *
 * How to run:
 *   pnpm tsx modules/05-rag/ts/01-naive-rag.ts
 *
 * This file is intentionally self-contained with an inline corpus so it
 * runs even if data/corpus/ is absent.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Chunk {
  id: string;
  text: string;
  source: string;   // e.g. "doc-1", "file.txt"
}

interface RetrievedChunk extends Chunk {
  score: number;
}

interface RAGAnswer {
  answer: string;
  chunks: RetrievedChunk[];   // the chunks that were stuffed into the prompt
}

// ---------------------------------------------------------------------------
// Inline corpus (fallback if data/corpus/ is absent)
// ---------------------------------------------------------------------------

const CORPUS_DOCS = [
  {
    source: "embeddings-guide",
    text: `Embeddings are dense vector representations that capture semantic meaning.
Two texts that mean similar things will have vectors that are close together in
the embedding space, even if they use different words. Embedding models are
trained using contrastive learning — similar pairs are pulled together and
dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and
1536 (OpenAI ada-002).`,
  },
  {
    source: "similarity-metrics",
    text: `Cosine similarity is the standard metric for comparing text embeddings.
It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors.
Because most embedding models L2-normalise their output, cosine reduces to a
plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean
distance is another option but is sensitive to vector magnitude.`,
  },
  {
    source: "ann-algorithms",
    text: `Approximate Nearest Neighbour (ANN) algorithms speed up similarity search
from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable Small
World) is the most popular: it builds a multi-layer graph where each node is
connected to nearby nodes at multiple granularities. At query time, search starts
at the top layer (coarse) and greedily descends to the bottom layer (fine). Typical
recall@10 is above 99 % with index build time measured in seconds for millions of
vectors.`,
  },
  {
    source: "chunking-strategies",
    text: `Chunking splits a long document into shorter passages before embedding.
Embedding models have a token limit (usually 256–512 tokens) and quality degrades
when you exceed it. Fixed-size chunking splits every N characters at word
boundaries. Sentence-based chunking groups N consecutive sentences. Overlapping
chunking adds a stride so consecutive chunks share some tokens — this prevents
losing context that falls at a boundary. Typical production settings: chunk_size=512
tokens, overlap=64 tokens.`,
  },
  {
    source: "rag-overview",
    text: `Retrieval-Augmented Generation (RAG) combines a retriever with a large
language model. The pipeline: (1) at index time, chunk documents and embed each
chunk; (2) at query time, embed the question, retrieve the top-k most similar
chunks, stuff them into a prompt, and ask the LLM to answer based only on the
provided context. RAG reduces hallucination because the model is constrained to
what was retrieved. The quality of RAG depends heavily on retrieval recall — if the
right chunk is not retrieved, the model cannot produce a correct answer.`,
  },
  {
    source: "reranking",
    text: `Reranking is a second-stage retrieval step. First retrieve a broad set of
candidates (top-50) with a fast dense retriever. Then score each candidate with a
more powerful but slower cross-encoder model that jointly encodes the query and
passage. Reranking consistently improves precision@k because the cross-encoder
sees the query and passage together, unlike the bi-encoder used in the first stage
which encodes them separately.`,
  },
  {
    source: "hyde",
    text: `HyDE (Hypothetical Document Embeddings) is a query reformulation technique.
Instead of embedding the raw question, generate a hypothetical answer using the LLM,
then embed that. The hypothesis lives in the same semantic space as real answers, so
retrieval tends to find better matches. HyDE works best when the question and the
expected answer have very different surface forms.`,
  },
  {
    source: "rag-evaluation",
    text: `RAG evaluation uses LLM-as-judge to score three dimensions: (1) Faithfulness
— is every claim in the answer grounded in the retrieved context? (2) Context
relevance — are the retrieved chunks actually relevant to the question? (3) Answer
relevance — does the answer address the question? The RAGAS framework automates
these checks. A common finding: high retrieval recall but low faithfulness means
the LLM is hallucinating despite having the right context.`,
  },
];

// ---------------------------------------------------------------------------
// Stage 1: Chunk
// ---------------------------------------------------------------------------

/**
 * Simple fixed-size word-based chunker.
 *
 * TODO: implement this function.
 *
 * Split each document's text into chunks of ~`wordsPerChunk` words.
 * Return an array of Chunk objects with:
 *   id:     `${source}-chunk-${index}` (0-based)
 *   text:   the chunk text (join words back with spaces)
 *   source: the document source string
 *
 * Algorithm: split text on whitespace, accumulate words until you hit
 * wordsPerChunk, then push a chunk and start fresh. The index in the id
 * resets to 0 for each doc.
 */
function chunkDocuments(
  docs: Array<{ source: string; text: string }>,
  wordsPerChunk: number = 80
): Chunk[] {
  // TODO: implement chunking. Split each doc's text on whitespace, walk the
  // words in steps of wordsPerChunk (slice + join back with spaces), and push
  // one Chunk per slice. Return the flat Chunk[] across all docs.
  throw new Error("TODO: implement chunkDocuments()");
}

// ---------------------------------------------------------------------------
// Stage 2 & 3: Embed + Store (minimal in-memory)
// ---------------------------------------------------------------------------

interface VectorEntry {
  chunk: Chunk;
  vector: number[];
}

/**
 * Embed all chunks and return an index (array of {chunk, vector}).
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Collect chunk.text for every chunk.
 *   2. Call provider.embed(...) once — batch all chunks in a single call.
 *   3. Pair each chunk with its vector (same order) into VectorEntry objects.
 */
async function buildIndex(
  chunks: Chunk[],
  provider: ReturnType<typeof getProvider>
): Promise<VectorEntry[]> {
  // TODO: implement buildIndex().
  throw new Error("TODO: implement buildIndex()");
}

// ---------------------------------------------------------------------------
// Stage 4: Retrieve
// ---------------------------------------------------------------------------

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

/**
 * Retrieve the top-k most similar chunks for a query vector.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Score each entry: cosine(queryVec, entry.vector).
 *   2. Sort descending.
 *   3. Return the first k entries as RetrievedChunk (add .score field).
 */
function retrieve(
  queryVec: number[],
  index: VectorEntry[],
  k: number = 4
): RetrievedChunk[] {
  // TODO: implement retrieve().
  throw new Error("TODO: implement retrieve()");
}

// ---------------------------------------------------------------------------
// Stage 5: Generate with citations
// ---------------------------------------------------------------------------

/**
 * Build a RAG prompt that asks the LLM to answer using ONLY the provided
 * context and to cite which chunk each claim comes from.
 *
 * TODO: implement this function.
 *
 * Return a ChatMessage[] of [system, user]:
 *   - System message: instruct the model to answer using ONLY the provided
 *     context, to append a citation like [chunk-id] after each claim, and to
 *     say so when the context does not contain the answer.
 *   - User message: assemble a context block by labelling each chunk with its
 *     id (a "[{id}]\n{text}" section per chunk, blank-line separated), then
 *     append the question at the end.
 */
function buildRAGPrompt(question: string, chunks: RetrievedChunk[]): ChatMessage[] {
  // TODO: build and return [systemMessage, userMessage].
  throw new Error("TODO: implement buildRAGPrompt()");
}

// ---------------------------------------------------------------------------
// Top-level RAG function
// ---------------------------------------------------------------------------

async function rag(
  question: string,
  index: VectorEntry[],
  provider: ReturnType<typeof getProvider>,
  k: number = 4
): Promise<RAGAnswer> {
  // Embed the question
  const [queryVec] = (await provider.embed([question])).vectors;

  // Retrieve top-k chunks
  const chunks = retrieve(queryVec, index, k);

  // Build prompt and call LLM
  const messages = buildRAGPrompt(question, chunks);
  const result = await provider.chat(messages, { temperature: 0 });

  return { answer: result.text, chunks };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}`);
  console.log(`  Chat model:  ${provider.chatModel}`);
  console.log(`  Embed model: ${provider.embedModel}\n`);

  // ── Build index ───────────────────────────────────────────────────────────
  console.log("[1/2] Building RAG index...");
  const chunks = chunkDocuments(CORPUS_DOCS, 80);
  console.log(`  ${CORPUS_DOCS.length} docs → ${chunks.length} chunks`);

  const index = await buildIndex(chunks, provider);
  console.log(`  Index built with ${index.length} vectors.\n`);

  // ── Answer questions ───────────────────────────────────────────────────────
  const questions = [
    "What is cosine similarity and when should I use it instead of Euclidean distance?",
    "How does HNSW work and what recall can I expect?",
    "What is HyDE and why does it improve retrieval?",
    "How do I evaluate whether my RAG system is faithfully grounding its answers?",
  ];

  console.log("[2/2] Answering questions...\n");
  for (const q of questions) {
    console.log(`Q: ${q}`);
    const { answer, chunks: usedChunks } = await rag(q, index, provider);
    console.log(`A: ${answer}`);
    console.log(`   (Retrieved: ${usedChunks.map((c) => c.id).join(", ")})`);
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
