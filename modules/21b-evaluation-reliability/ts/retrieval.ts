/**
 * retrieval.ts — deterministic, offline retrieval methods for Module 21b.
 *
 * A byte-for-byte port of the Python `retrieval.py`. Three methods are compared
 * on identical cases:
 *
 * - `dense`    — cosine over a seedless character-trigram hashing "embedding"
 *                (a deterministic, offline stand-in for a real embedder).
 * - `bm25`     — Okapi BM25 with a non-negative (Lucene-style) idf, from scratch.
 * - `hybrid`   — Reciprocal Rank Fusion (RRF) of the dense and BM25 rankings.
 * - `reranked` — a deterministic lexical-overlap reranker over the hybrid head.
 *
 * Every method returns the FULL corpus ranked, with a stable tie-break (score
 * descending, then chunk id ascending), so a query yields identical rankings on
 * every run. FNV-1a hashing over UTF-8 bytes matches the Python implementation,
 * so the two languages produce the same dense vectors.
 */

const TOKEN_SPLIT = /[^a-z0-9]+/;
const FNV_OFFSET = 0x811c9dc5; // 2166136261
const FNV_PRIME = 0x01000193; // 16777619

export interface Chunk {
  id: string;
  text: string;
}

export const METHODS = ["dense", "bm25", "hybrid", "reranked"] as const;
export type Method = (typeof METHODS)[number];

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .split(TOKEN_SPLIT)
    .filter((tok) => tok.length > 0);
}

/**
 * Deterministic 32-bit FNV-1a hash over the UTF-8 bytes of `text`. Not a salted
 * hash, so the embedding is stable across processes and matches the Python port.
 */
export function fnv1a32(text: string): number {
  let h = FNV_OFFSET;
  const bytes = new TextEncoder().encode(text);
  for (const byte of bytes) {
    h ^= byte;
    h = Math.imul(h, FNV_PRIME) >>> 0;
  }
  return h >>> 0;
}

function charNgrams(token: string, n: number): string[] {
  const padded = `#${token}#`;
  if (padded.length < n) return [padded];
  const grams: string[] = [];
  for (let i = 0; i <= padded.length - n; i += 1) {
    grams.push(padded.slice(i, i + n));
  }
  return grams;
}

export interface RetrievalConfig {
  embedDim: number;
  embedNgram: number;
  bm25K1: number;
  bm25B: number;
  rrfK: number;
  rerankCandidates: number;
  rerankPhraseWeight: number;
}

export interface Manifest {
  embedder: { dim: number; ngram: number };
  bm25: { k1: number; b: number };
  hybrid: { rrf_k: number };
  reranker: { candidates: number; phrase_weight: number };
  [key: string]: unknown;
}

export function configFromManifest(manifest: Manifest): RetrievalConfig {
  return {
    embedDim: manifest.embedder.dim,
    embedNgram: manifest.embedder.ngram,
    bm25K1: manifest.bm25.k1,
    bm25B: manifest.bm25.b,
    rrfK: manifest.hybrid.rrf_k,
    rerankCandidates: manifest.reranker.candidates,
    rerankPhraseWeight: manifest.reranker.phrase_weight,
  };
}

/** Signed feature-hashing embedding over padded character n-grams, L2-normalised. */
export function embed(text: string, dim: number, ngram: number): number[] {
  const vec = new Array<number>(dim).fill(0);
  for (const token of tokenize(text)) {
    for (const gram of charNgrams(token, ngram)) {
      const index = fnv1a32(gram) % dim;
      const sign = (fnv1a32(`s:${gram}`) & 1) === 0 ? 1 : -1;
      vec[index] += sign;
    }
  }
  let norm = 0;
  for (const x of vec) norm += x * x;
  norm = Math.sqrt(norm);
  if (norm === 0) return vec;
  return vec.map((x) => x / norm);
}

function dot(a: readonly number[], b: readonly number[]): number {
  let total = 0;
  for (let i = 0; i < a.length; i += 1) total += a[i] * b[i];
  return total;
}

/** Rank ids by score descending, breaking ties by id ascending. */
function rankByScore(scores: ReadonlyMap<string, number>): string[] {
  return [...scores.keys()].sort((a, b) => {
    const diff = (scores.get(b) ?? 0) - (scores.get(a) ?? 0);
    if (diff !== 0) return diff;
    return a < b ? -1 : a > b ? 1 : 0;
  });
}

// Encode an adjacent-token bigram with a separator that `tokenize` (which emits
// only [a-z0-9]+ runs) can never produce, so distinct bigrams cannot collide:
// bigramKey("do", "g") !== bigramKey("d", "og"). Without a separator both would
// stringify to "dog" and inflate the reranker with a false phrase-match hit.
const BIGRAM_SEP = " ";

function bigramKey(a: string, b: string): string {
  return `${a}${BIGRAM_SEP}${b}`;
}

/** Collision-free set of adjacent-token bigrams (parity with Python `bigram_set`). */
export function bigramSet(tokens: readonly string[]): Set<string> {
  const set = new Set<string>();
  for (let i = 0; i + 1 < tokens.length; i += 1) {
    set.add(bigramKey(tokens[i], tokens[i + 1]));
  }
  return set;
}

export class RetrievalIndex {
  readonly ids: string[];
  readonly config: RetrievalConfig;
  private readonly texts = new Map<string, string>();
  private readonly embeddings = new Map<string, number[]>();
  private readonly docLen = new Map<string, number>();
  private readonly tokenSet = new Map<string, Set<string>>();
  private readonly bigrams = new Map<string, Set<string>>();
  private readonly tf = new Map<string, Map<string, number>>();
  private readonly idf = new Map<string, number>();
  private readonly avgdl: number;

  constructor(chunks: readonly Chunk[], config: RetrievalConfig) {
    this.config = config;
    this.ids = chunks.map((c) => c.id);
    for (const chunk of chunks) this.texts.set(chunk.id, chunk.text);

    const df = new Map<string, number>();
    let totalLen = 0;
    for (const cid of this.ids) {
      const text = this.texts.get(cid) ?? "";
      this.embeddings.set(cid, embed(text, config.embedDim, config.embedNgram));

      const toks = tokenize(text);
      this.docLen.set(cid, toks.length);
      totalLen += toks.length;
      this.tokenSet.set(cid, new Set(toks));

      this.bigrams.set(cid, bigramSet(toks));

      const counts = new Map<string, number>();
      for (const tok of toks) counts.set(tok, (counts.get(tok) ?? 0) + 1);
      this.tf.set(cid, counts);
      for (const term of counts.keys()) df.set(term, (df.get(term) ?? 0) + 1);
    }

    const nDocs = this.ids.length;
    this.avgdl = nDocs > 0 ? totalLen / nDocs : 0;
    // Non-negative (Lucene-style) idf: ln(1 + (N - df + 0.5) / (df + 0.5)).
    for (const [term, freq] of df) {
      this.idf.set(term, Math.log(1.0 + (nDocs - freq + 0.5) / (freq + 0.5)));
    }
  }

  denseScores(query: string): Map<string, number> {
    const q = embed(query, this.config.embedDim, this.config.embedNgram);
    const scores = new Map<string, number>();
    for (const cid of this.ids) scores.set(cid, dot(q, this.embeddings.get(cid) ?? []));
    return scores;
  }

  bm25Scores(query: string): Map<string, number> {
    const qTerms = tokenize(query);
    const { bm25K1: k1, bm25B: b } = this.config;
    const scores = new Map<string, number>();
    for (const cid of this.ids) {
      const tf = this.tf.get(cid) ?? new Map<string, number>();
      const dl = this.docLen.get(cid) ?? 0;
      const denomLen = this.avgdl > 0 ? k1 * (1.0 - b + (b * dl) / this.avgdl) : k1;
      let score = 0.0;
      for (const term of qTerms) {
        const freq = tf.get(term) ?? 0;
        if (freq === 0) continue;
        const idf = this.idf.get(term) ?? 0.0;
        score += (idf * (freq * (k1 + 1.0))) / (freq + denomLen);
      }
      scores.set(cid, score);
    }
    return scores;
  }

  dense(query: string): string[] {
    return rankByScore(this.denseScores(query));
  }

  bm25(query: string): string[] {
    return rankByScore(this.bm25Scores(query));
  }

  hybrid(query: string): string[] {
    const denseRank = new Map<string, number>();
    this.dense(query).forEach((cid, i) => denseRank.set(cid, i + 1));
    const bm25Rank = new Map<string, number>();
    this.bm25(query).forEach((cid, i) => bm25Rank.set(cid, i + 1));

    const rrfK = this.config.rrfK;
    const fused = new Map<string, number>();
    for (const cid of this.ids) {
      const rd = denseRank.get(cid) ?? this.ids.length;
      const rb = bm25Rank.get(cid) ?? this.ids.length;
      fused.set(cid, 1.0 / (rrfK + rd) + 1.0 / (rrfK + rb));
    }
    return rankByScore(fused);
  }

  reranked(query: string): string[] {
    const hybrid = this.hybrid(query);
    const m = this.config.rerankCandidates;
    const head = hybrid.slice(0, m);
    const tail = hybrid.slice(m);

    const qTerms = tokenize(query);
    const qSet = new Set(qTerms);
    const qBigrams = bigramSet(qTerms);
    const weight = this.config.rerankPhraseWeight;

    const rerankScore = (cid: string): number => {
      if (qSet.size === 0) return 0.0;
      const tokens = this.tokenSet.get(cid) ?? new Set<string>();
      let covered = 0;
      for (const term of qSet) if (tokens.has(term)) covered += 1;
      const coverage = covered / qSet.size;
      const docBigrams = this.bigrams.get(cid) ?? new Set<string>();
      let phraseHits = 0;
      for (const bg of qBigrams) if (docBigrams.has(bg)) phraseHits += 1;
      return coverage + weight * phraseHits;
    };

    const hybridRank = new Map<string, number>();
    head.forEach((cid, i) => hybridRank.set(cid, i));
    const reordered = [...head].sort((a, b) => {
      const diff = rerankScore(b) - rerankScore(a);
      if (diff !== 0) return diff;
      const ra = hybridRank.get(a) ?? 0;
      const rb = hybridRank.get(b) ?? 0;
      if (ra !== rb) return ra - rb;
      return a < b ? -1 : a > b ? 1 : 0;
    });
    return [...reordered, ...tail];
  }

  rank(method: Method, query: string): string[] {
    switch (method) {
      case "dense":
        return this.dense(query);
      case "bm25":
        return this.bm25(query);
      case "hybrid":
        return this.hybrid(query);
      case "reranked":
        return this.reranked(query);
      default: {
        const exhaustive: never = method;
        throw new Error(`unknown retrieval method: ${String(exhaustive)}`);
      }
    }
  }
}
