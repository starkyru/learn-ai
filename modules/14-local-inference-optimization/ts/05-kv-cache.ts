/**
 * Task 5 🔴 — KV cache intuition: cached vs uncached autoregressive loop.
 *
 * What you'll learn:
 *   - Why attention is O(n²) in key computations without caching, O(n) with it
 *   - The concrete computational savings the KV cache provides
 *   - How a toy autoregressive loop mirrors real transformer generation
 *
 * The toy model:
 *   - A fixed random embedding matrix (E[tokenId] = DIM-dimensional vector)
 *   - A fixed random key projection matrix W_k ∈ ℝ^{DIM × DIM}
 *   - "Attention" = dot products of the new token's query with all past keys
 *   - NO learning — the weights are fixed. This is about the generation loop.
 *
 * Two modes:
 *   UNCACHED: at step t, recompute ALL t key vectors from scratch.
 *   CACHED:   at step t, extend the cache with only the NEW token's key.
 *
 * Computation count:
 *   Uncached total: 1 + 2 + ... + N = N*(N+1)/2
 *   Cached total:   N  (one key per step)
 *   For N=100: 5,050 vs 100 — 50× fewer key computations.
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/05-kv-cache.ts
 *
 * The harness is RUNNABLE. You implement the TODO sections.
 */

// ---------------------------------------------------------------------------
// Toy model constants
// ---------------------------------------------------------------------------

const DIM = 64;
const VOCAB_SIZE = 100;
const SEQ_LEN = 100;

// Seeded PRNG (Mulberry32) for reproducible matrices
function makePrng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s += 0x6d2b79f5;
    let x = s;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

function randnMatrix(rows: number, cols: number, prng: () => number): number[][] {
  return Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => {
      const u = Math.max(prng(), 1e-10);
      const v = prng();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }),
  );
}

function randInts(n: number, max: number, prng: () => number): number[] {
  return Array.from({ length: n }, () => Math.floor(prng() * max));
}

const _prng = makePrng(42);
const EMBED_MATRIX = randnMatrix(VOCAB_SIZE, DIM, _prng); // [VOCAB_SIZE × DIM]
const W_K = randnMatrix(DIM, DIM, _prng);                 // [DIM × DIM]
const W_Q = randnMatrix(DIM, DIM, _prng);                 // [DIM × DIM]
const TOKENS = randInts(SEQ_LEN, VOCAB_SIZE, _prng);      // [SEQ_LEN]

// ---------------------------------------------------------------------------
// Matrix / vector utilities (provided — do not modify)
// ---------------------------------------------------------------------------

/** Matrix-vector multiply: M [rows×cols] @ v [cols] → [rows] */
function matvec(M: number[][], v: number[]): number[] {
  return M.map((row) => row.reduce((s, m, j) => s + m * v[j], 0));
}

/** Dot product of two equal-length vectors */
function dot(a: number[], b: number[]): number {
  return a.reduce((s, v, i) => s + v * b[i], 0);
}

/** Softmax over a 1D array */
function softmax(scores: number[]): number[] {
  const max = Math.max(...scores);
  const exp = scores.map((s) => Math.exp(s - max));
  const sum = exp.reduce((a, b) => a + b, 0);
  return exp.map((e) => e / sum);
}

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

/**
 * Return the embedding for `tokenId`.
 *
 * TODO: return EMBED_MATRIX[tokenId].
 */
function embed(tokenId: number): number[] {
  // TODO: implement embed
  throw new Error("TODO: implement embed()");
}

/**
 * Compute the key vector for `tokenId`.
 *
 * Formula: k = W_K @ embed(tokenId)
 *
 * TODO: return matvec(W_K, embed(tokenId)).
 */
function computeKey(tokenId: number): number[] {
  // TODO: implement computeKey
  throw new Error("TODO: implement computeKey()");
}

/**
 * Compute the query vector for `tokenId`.
 *
 * Formula: q = W_Q @ embed(tokenId)
 *
 * TODO: return matvec(W_Q, embed(tokenId)).
 */
function computeQuery(tokenId: number): number[] {
  // TODO: implement computeQuery
  throw new Error("TODO: implement computeQuery()");
}

// ---------------------------------------------------------------------------
// Attention — uncached
// ---------------------------------------------------------------------------

/**
 * Compute attention for `newTokenId` by recomputing ALL past key vectors.
 *
 * This is the NAIVE approach: at step t, we compute t+1 keys from scratch.
 *
 * Returns [attentionOutput, keyComputations].
 *
 * TODO:
 *   1. Compute query = computeQuery(newTokenId).
 *   2. Compute key for every token in [...tokensSoFar, newTokenId].
 *      keyComputations = tokensSoFar.length + 1.
 *   3. Build K as the array of key vectors.
 *   4. scores = K.map(k => dot(k, query))
 *   5. weights = softmax(scores)
 *   6. attentionOutput = elementwise sum of weights[i] * K[i]
 *   7. Return [attentionOutput, keyComputations].
 */
function attentionUncached(
  tokensSoFar: number[],
  newTokenId: number,
): [number[], number] {
  // TODO: implement attentionUncached
  throw new Error("TODO: implement attentionUncached()");
}

// ---------------------------------------------------------------------------
// Attention — cached
// ---------------------------------------------------------------------------

/**
 * Compute attention for `newTokenId` using the KV cache.
 *
 * Past keys are already in kvCache. Compute only 1 new key.
 *
 * Returns [attentionOutput, updatedKvCache, keyComputations].
 * keyComputations is always 1.
 *
 * TODO:
 *   1. query = computeQuery(newTokenId).
 *   2. newKey = computeKey(newTokenId).  ← 1 computation
 *   3. updatedCache = [...kvCache, newKey].
 *   4. scores = updatedCache.map(k => dot(k, query))
 *   5. weights = softmax(scores)
 *   6. attentionOutput = weighted sum of cache keys.
 *   7. Return [attentionOutput, updatedCache, 1].
 */
function attentionCached(
  kvCache: number[][],
  newTokenId: number,
): [number[], number[][], number] {
  // TODO: implement attentionCached
  throw new Error("TODO: implement attentionCached()");
}

// ---------------------------------------------------------------------------
// Full generation loops
// ---------------------------------------------------------------------------

/**
 * Run the full generation loop WITHOUT KV cache.
 *
 * Returns [elapsedMs, totalKeyComputations].
 *
 * TODO:
 *   1. Record start = performance.now().
 *   2. totalKeyComps = 0.
 *   3. For t from 1 to tokens.length - 1:
 *        [_, comps] = attentionUncached(tokens.slice(0, t), tokens[t])
 *        totalKeyComps += comps
 *   4. Return [performance.now() - start, totalKeyComps].
 */
function generateUncached(tokens: number[]): [number, number] {
  // TODO: implement generateUncached
  throw new Error("TODO: implement generateUncached()");
}

/**
 * Run the full generation loop WITH KV cache.
 *
 * Returns [elapsedMs, totalKeyComputations].
 *
 * TODO:
 *   1. Record start = performance.now().
 *   2. kvCache = [], totalKeyComps = 0.
 *   3. For each token in tokens:
 *        [_, kvCache, comps] = attentionCached(kvCache, token)
 *        totalKeyComps += comps
 *   4. Return [performance.now() - start, totalKeyComps].
 */
function generateCached(tokens: number[]): [number, number] {
  // TODO: implement generateCached
  throw new Error("TODO: implement generateCached()");
}

// ---------------------------------------------------------------------------
// Speedup measurement
// ---------------------------------------------------------------------------

/**
 * Generate the sequence twice and report the speedup.
 *
 * TODO:
 *   1. Run generateUncached(tokens) and generateCached(tokens).
 *   2. Print a table:
 *        Mode        | Key computations | Time (ms) | Speedup
 *        Uncached    | 5050             | 234.1     | 1.0×
 *        Cached      | 100              | 12.3      | 19.0×
 *   3. Assert uncached total == N*(N+1)/2 and cached total == N.
 */
function measureSpeedup(tokens: number[]): void {
  const n = tokens.length;
  const expectedUncached = (n * (n + 1)) / 2;
  const expectedCached = n;
  // TODO: implement measureSpeedup
  throw new Error("TODO: implement measureSpeedup()");
}

// ---------------------------------------------------------------------------
// Harness — RUNNABLE, do not modify
// ---------------------------------------------------------------------------

function main() {
  console.log("=".repeat(60));
  console.log("KV CACHE INTUITION (TypeScript)");
  console.log("=".repeat(60));

  console.log(`\nSequence length : ${SEQ_LEN}`);
  console.log(`Embedding dim   : ${DIM}`);
  console.log(
    `Expected uncached key computations: ${((SEQ_LEN * (SEQ_LEN + 1)) / 2).toLocaleString()}`,
  );
  console.log(`Expected cached key computations  : ${SEQ_LEN}`);
  console.log(
    `Theoretical savings: ${((SEQ_LEN * (SEQ_LEN + 1)) / 2 / SEQ_LEN).toFixed(1)}× fewer`,
  );

  console.log("\nRunning uncached and cached loops...");
  measureSpeedup(TOKENS);

  console.log(
    "\nKey insight: in a real transformer, each 'key computation' is a full",
    "\nmatrix multiply (token embedding × Wk). For a 7B model with 32 attention",
    "\nheads × 128-dim keys × 4096-dim embeddings, this is ~17M FLOPs per token.",
    "\nCaching saves all of that for past tokens.",
    "\n",
    "\nWhy context length is quadratic without KV cache:",
    "\n  At step t: O(t) key computations",
    "\n  Total for N steps: O(N²)",
    "\nWith KV cache:",
    "\n  Key computations: O(1) per step → O(N) total",
    "\n  Attention dot products still O(t) per step, but these are reads, not writes.",
  );
}

main();
