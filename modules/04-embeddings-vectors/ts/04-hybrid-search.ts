/**
 * Task 4 🟡 — Hybrid search: BM25 + dense embeddings via Reciprocal Rank Fusion.
 *
 * What you'll learn:
 *   - Why dense retrieval alone fails on rare/exact terms (e.g. "HNSW", "BM25")
 *   - Why BM25 alone fails on semantic paraphrase queries
 *   - How Reciprocal Rank Fusion (RRF) merges two ranked lists robustly
 *   - Why "hybrid" consistently outperforms either approach alone
 *
 * How to run:
 *   pnpm tsx modules/04-embeddings-vectors/ts/04-hybrid-search.ts
 *
 * NOTE on BM25 in TypeScript:
 *   There is no widely-used, well-maintained BM25 npm package.
 *   We implement a minimal BM25 here from scratch (~50 lines).
 *   If you want a library option, see: https://www.npmjs.com/package/okapibm25
 *
 * RRF formula: score(d) = Σ_r  1 / (k + rank_r(d))
 *   where k=60 is a smoothing constant and the sum is over each ranker r.
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Corpus
// ---------------------------------------------------------------------------

interface Document {
  id: string;
  text: string;
}

const CORPUS: Document[] = [
  { id: "doc-1", text: "Embeddings are dense vector representations of text that capture semantic meaning." },
  { id: "doc-2", text: "Cosine similarity measures the angle between two vectors, ignoring their magnitude." },
  { id: "doc-3", text: "HNSW is a graph-based approximate nearest neighbour index with excellent recall and speed." },
  { id: "doc-4", text: "BM25 is a classic keyword-based ranking function used in search engines like Elasticsearch." },
  { id: "doc-5", text: "Retrieval-Augmented Generation (RAG) combines a retriever with a language model generator." },
  { id: "doc-6", text: "Chunking splits long documents into smaller passages before embedding for better recall." },
  { id: "doc-7", text: "Reciprocal Rank Fusion merges multiple ranked lists by summing 1/(k+rank) per document." },
  { id: "doc-8", text: "Sparse retrieval uses term frequency and inverted document frequency (TF-IDF) signals." },
  { id: "doc-9", text: "Large language models predict the next token using attention over a context window." },
  { id: "doc-10", text: "Hybrid search combines dense and sparse retrieval for consistently better results." },
];

// ---------------------------------------------------------------------------
// Minimal BM25 implementation (scratch — no library)
// ---------------------------------------------------------------------------

/**
 * Tokenise a string into lowercase words (strip punctuation).
 */
function tokenise(text: string): string[] {
  return text.toLowerCase().replace(/[^a-z0-9\s]/g, "").split(/\s+/).filter(Boolean);
}

/**
 * BM25 scorer.
 *
 * Parameters follow the classic Robertson et al. paper:
 *   k1 = 1.5  (term frequency saturation)
 *   b  = 0.75 (length normalisation)
 *
 * score(q, d) = Σ_t IDF(t) * (tf(t,d) * (k1+1)) / (tf(t,d) + k1*(1-b+b*|d|/avgdl))
 *
 * where IDF(t) = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
 */
class BM25 {
  private k1 = 1.5;
  private b = 0.75;
  private docs: string[][];          // tokenised documents
  private avgdl: number;             // average document length in tokens
  private df: Map<string, number>;   // document frequency per term
  private N: number;                 // number of documents

  constructor(docs: Document[]) {
    this.docs = docs.map((d) => tokenise(d.text));
    this.N = this.docs.length;
    this.avgdl = this.docs.reduce((s, d) => s + d.length, 0) / this.N;

    // Build document frequency table
    this.df = new Map();
    for (const tokens of this.docs) {
      for (const term of new Set(tokens)) {
        this.df.set(term, (this.df.get(term) ?? 0) + 1);
      }
    }
  }

  /**
   * Score all documents against a query and return ranked list.
   *
   * TODO: implement this method.
   *
   * Steps:
   *   1. Tokenise the query.
   *   2. For each document, sum BM25 term scores over query tokens.
   *   3. Return array of { id, score } sorted descending by score.
   *
   * IDF(t) = Math.log((this.N - df + 0.5) / (df + 0.5) + 1)
   * TF score = (tf * (this.k1 + 1)) / (tf + this.k1 * (1 - this.b + this.b * docLen / this.avgdl))
   * where tf = count of term t in doc, df = this.df.get(t) ?? 0
   */
  rank(query: string, docs: Document[]): Array<{ id: string; score: number }> {
    const qTerms = tokenise(query);
    // TODO: for each doc i in this.docs:
    //   - compute term frequency map for the doc tokens
    //   - for each query term: look up tf and df, compute IDF * TF score, accumulate
    //   - push { id: docs[i].id, score: accumulated } to results
    // Sort descending and return.
    throw new Error("TODO: implement BM25.rank()");
  }
}

// ---------------------------------------------------------------------------
// Dense retrieval helper (reuse your cosine from task 1)
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

function denseRank(
  queryVec: number[],
  docVecs: number[][],
  docs: Document[]
): Array<{ id: string; score: number }> {
  return docs
    .map((d, i) => ({ id: d.id, score: cosine(queryVec, docVecs[i]) }))
    .sort((a, b) => b.score - a.score);
}

// ---------------------------------------------------------------------------
// Reciprocal Rank Fusion
// ---------------------------------------------------------------------------

/**
 * Merge two ranked lists using Reciprocal Rank Fusion.
 *
 * RRF score for doc d = Σ_ranker  1 / (k + rank(d, ranker))
 * where rank is 1-indexed.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Assign each document its 1-indexed rank in both lists.
 *   2. For each unique doc id, sum 1/(k+rank) across all lists.
 *      Use rank = Infinity (or a large number) for docs absent from a list.
 *   3. Sort descending by fused score.
 */
export function reciprocalRankFusion(
  rankedLists: Array<Array<{ id: string; score: number }>>,
  k: number = 60
): Array<{ id: string; fusedScore: number }> {
  // TODO: implement RRF.
  //
  // Tip: build a Map<id, fusedScore> initialised to 0.
  // For each list, enumerate with index (0-based), so rank = index + 1.
  // Add 1 / (k + rank) to the map for each id.
  // Finally sort the map entries by fusedScore descending.
  throw new Error("TODO: implement reciprocalRankFusion()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function search(
  label: string,
  ranked: Array<{ id: string; score: number }>,
  topK: number = 3
) {
  console.log(`\n  ${label}`);
  for (const r of ranked.slice(0, topK)) {
    const doc = CORPUS.find((d) => d.id === r.id)!;
    console.log(`    [${r.score.toFixed(4)}] ${r.id}: ${doc.text.slice(0, 70)}...`);
  }
}

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} | embed model: ${provider.embedModel}\n`);

  // ── Index ─────────────────────────────────────────────────────────────────
  const { vectors: docVecs } = await provider.embed(CORPUS.map((d) => d.text));
  const bm25 = new BM25(CORPUS);

  // ── Queries ───────────────────────────────────────────────────────────────
  const queries = [
    // Semantic query — dense should excel; BM25 may miss if exact words differ
    "How do I find similar vectors quickly?",
    // Exact-term query — BM25 should excel; dense may dilute with near-synonyms
    "BM25 keyword ranking function",
    // Hybrid test — both signals contribute
    "What algorithm merges ranked lists from different retrieval methods?",
  ];

  for (const q of queries) {
    console.log(`\nQuery: "${q}"`);

    const [qVec] = (await provider.embed([q])).vectors;

    const denseResults = denseRank(qVec, docVecs, CORPUS);
    const bm25Results = bm25.rank(q, CORPUS);
    const hybridResults = reciprocalRankFusion([denseResults, bm25Results]);

    await search("Dense only", denseResults);
    await search("BM25 only ", bm25Results);
    console.log("\n  Hybrid (RRF)");
    for (const r of hybridResults.slice(0, 3)) {
      const doc = CORPUS.find((d) => d.id === r.id)!;
      console.log(`    [rrf=${r.fusedScore.toFixed(4)}] ${r.id}: ${doc.text.slice(0, 70)}...`);
    }
  }

  console.log("\n--- Reflection ---");
  console.log("  Does BM25 find 'BM25' docs that dense retrieval might rank lower?");
  console.log("  Does dense retrieval handle paraphrase queries that BM25 misses?");
  console.log("  Is hybrid always better, or are there cases where it isn't?");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
