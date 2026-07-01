/**
 * Task 4 🟢 — Citations & attribution.
 *
 * What you'll learn:
 *   - How to structure RAG prompts to enforce per-claim citations
 *   - How to parse and validate citations against the retrieved chunks
 *   - How to surface uncited or unsupported claims to the user
 *   - Why citations matter for trust and debugging
 *
 * How to run:
 *   pnpm tsx modules/05-rag/ts/04-citations.ts
 *
 * Design:
 *   The LLM is asked to output a structured JSON response:
 *     { "claims": [{ "text": "...", "citation": "chunk-id-or-null" }] }
 *   We then validate that every cited chunk-id actually exists in the
 *   retrieved set, and flag claims that have no citation.
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Chunk { id: string; text: string; source: string; }
interface RetrievedChunk extends Chunk { score: number; }
interface VectorEntry { chunk: Chunk; vector: number[]; }

interface Claim {
  text: string;
  citation: string | null;   // chunk id, or null if no citation given
}

interface CitedAnswer {
  claims: Claim[];
  answer: string;               // reconstructed readable answer
  validCitations: string[];     // chunk ids that were cited AND exist
  invalidCitations: string[];   // chunk ids that were cited but don't exist
  uncitedClaims: string[];      // claim texts with no citation
}

// ---------------------------------------------------------------------------
// Shared corpus + index (same as previous tasks)
// ---------------------------------------------------------------------------

const CORPUS_DOCS = [
  { source: "embeddings-guide", text: `Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space, even if they use different words. Embedding models are trained using contrastive learning — similar pairs are pulled together and dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and 1536 (OpenAI ada-002).` },
  { source: "similarity-metrics", text: `Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude.` },
  { source: "ann-algorithms", text: `Approximate Nearest Neighbour (ANN) algorithms speed up similarity search from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable Small World) is the most popular: it builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer and greedily descends. Typical recall@10 is above 99%.` },
  { source: "chunking-strategies", text: `Chunking splits a long document into shorter passages before embedding. Fixed-size chunking splits every N characters at word boundaries. Sentence-based chunking groups N consecutive sentences. Overlapping chunking adds a stride so consecutive chunks share some tokens — this prevents losing context that falls at a boundary.` },
  { source: "rag-overview", text: `Retrieval-Augmented Generation (RAG) combines a retriever with a large language model. The pipeline: chunk documents, embed each chunk, embed the question, retrieve top-k chunks, stuff them into a prompt, and ask the LLM to answer based only on the provided context. RAG reduces hallucination.` },
  { source: "reranking", text: `Reranking is a second-stage retrieval step. First retrieve a broad set of candidates with a fast dense retriever. Then score each with a more powerful cross-encoder that jointly encodes query and passage. Reranking improves precision@k.` },
  { source: "hyde", text: `HyDE (Hypothetical Document Embeddings) generates a hypothetical answer, then embeds that instead of the question. The hypothesis lives in the same semantic space as real answers, improving retrieval for questions with very different surface forms than their answers.` },
  { source: "rag-evaluation", text: `RAG evaluation uses LLM-as-judge for three metrics: Faithfulness (claims grounded in context?), Context relevance (chunks relevant to question?), Answer relevance (answer addresses question?). The RAGAS framework automates these checks.` },
];

function chunkDocuments(docs: typeof CORPUS_DOCS, wordsPerChunk = 80): Chunk[] {
  const chunks: Chunk[] = [];
  for (const doc of docs) {
    const words = doc.text.split(/\s+/).filter(Boolean);
    let i = 0, idx = 0;
    while (i < words.length) {
      chunks.push({ id: `${doc.source}-chunk-${idx}`, text: words.slice(i, i + wordsPerChunk).join(" "), source: doc.source });
      i += wordsPerChunk; idx++;
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
  const { vectors } = await provider.embed(chunks.map((c) => c.text));
  return chunks.map((c, i) => ({ chunk: c, vector: vectors[i] }));
}

function retrieveTopK(queryVec: number[], index: VectorEntry[], k: number): RetrievedChunk[] {
  return index
    .map((e) => ({ ...e.chunk, score: cosine(queryVec, e.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}

// ---------------------------------------------------------------------------
// Citation-aware RAG prompt
// ---------------------------------------------------------------------------

/**
 * Build a prompt that instructs the LLM to output structured JSON claims
 * with per-claim citations.
 *
 * TODO: implement this function.
 *
 * Return a ChatMessage[] of [system, user]:
 *   - System message: instruct the model to answer using ONLY the context,
 *     break its answer into individual factual claims, tag each claim with the
 *     id of the chunk it came from (or null when it can't be grounded), and
 *     output ONLY valid JSON shaped as
 *       { "claims": [{ "text": ..., "citation": <chunk-id or null> }, ...] }
 *   - User message: assemble a context block labelling each chunk with its id
 *     (a "[{id}]\n{text}" section per chunk, blank-line separated), then append
 *     the question.
 */
function buildCitationPrompt(question: string, chunks: RetrievedChunk[]): ChatMessage[] {
  // TODO: implement buildCitationPrompt().
  throw new Error("TODO: implement buildCitationPrompt()");
}

// ---------------------------------------------------------------------------
// Parse + validate citations
// ---------------------------------------------------------------------------

/**
 * Call the LLM, parse the JSON response, and validate citations.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build the prompt with buildCitationPrompt(...) and call
 *      provider.chat(messages, { temperature: 0 }).
 *   2. JSON.parse result.text inside a try/catch; on failure return an empty
 *      CitedAnswer so the harness survives malformed output.
 *   3. Read the "claims" array (each { text, citation }).
 *   4. Compute the id set of the retrieved chunks, then partition claims into:
 *        - validCitations:   non-null citations present in that id set
 *        - invalidCitations: non-null citations absent from it (hallucinated)
 *        - uncitedClaims:    the text of claims whose citation is null
 *   5. Reconstruct a readable answer by joining each claim's text with a
 *      trailing " [citation]" tag (or a " [UNCITED]" marker when null).
 *   6. Return the assembled CitedAnswer.
 */
async function citedRAG(
  question: string,
  chunks: RetrievedChunk[],
  provider: ReturnType<typeof getProvider>
): Promise<CitedAnswer> {
  // TODO: implement citedRAG().
  throw new Error("TODO: implement citedRAG()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}\n`);

  const allChunks = chunkDocuments(CORPUS_DOCS, 80);
  const index = await buildIndex(allChunks, provider);
  console.log(`Index: ${index.length} chunks\n`);

  const questions = [
    "What is cosine similarity and how does it relate to dot product?",
    "Explain the RAG pipeline from chunk to answer.",
    "What is HyDE and how does it improve retrieval?",
  ];

  for (const q of questions) {
    console.log(`Q: ${q}`);
    const [queryVec] = (await provider.embed([q])).vectors;
    const retrieved = retrieveTopK(queryVec, index, 4);
    const { answer, validCitations, invalidCitations, uncitedClaims } = await citedRAG(
      q,
      retrieved,
      provider
    );

    console.log(`A: ${answer}`);
    console.log(`   Valid citations:   ${validCitations.join(", ") || "none"}`);
    if (invalidCitations.length > 0) {
      console.log(`   !! Invalid citations (hallucinated ids): ${invalidCitations.join(", ")}`);
    }
    if (uncitedClaims.length > 0) {
      console.log(`   !! Uncited claims: ${uncitedClaims.length}`);
    }
    console.log();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
