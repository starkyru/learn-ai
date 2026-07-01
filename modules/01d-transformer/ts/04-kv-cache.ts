/**
 * Task 4 🟡 — The KV cache: why generation isn't O(n^2) per token (plain arrays).
 *
 * What you'll learn:
 *   - How autoregressive decoding actually works: tokens are produced ONE AT A TIME,
 *     each attending over everything generated so far.
 *   - The naive way recomputes keys and values for the ENTIRE prefix at every step —
 *     O(n^2) key/value projections over a length-n generation. Wasteful: the keys and
 *     values for old tokens never change.
 *   - The KV cache stores each token's key and value ONCE. At step t you project only
 *     the new token's q, k, v, APPEND its k, v to the cache, and attend the single new
 *     query over ALL cached keys/values. That's O(n) projections total.
 *
 * This is the module's most-asked interview topic: "explain the KV cache and attention
 * masking." You will prove the cached path yields IDENTICAL logits to naive recompute.
 *
 * The math (single-head causal self-attention):
 *
 *   At step t (0-based), with the prefix x[0..t] already known:
 *     qT      = xT @ Wq                          (this token's query)
 *     kI      = xI @ Wk,  vI = xI @ Wv           for every i <= t
 *     scores  = qT · kI / sqrt(d)  for i in 0..t
 *     weights = softmax(scores)
 *     context = sum_i weights_i * vI
 *     logits  = context @ Wo
 *
 *   Naive:  recompute every kI, vI (i in 0..t) from scratch at each step t.
 *   Cached: kI, vI for i < t were computed earlier and stored; only kT, vT are new.
 *
 * No external math library. Plain number[] / number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/01d-transformer/ts/04-kv-cache.ts
 */

type Matrix = number[][];

// ---------------------------------------------------------------------------
// Vector/matrix helpers (provided)
// ---------------------------------------------------------------------------

/** Vector (length K) times matrix (K×M) -> vector (length M). */
function vecMatMul(v: number[], M: Matrix): number[] {
  const K = M.length,
    N = M[0].length;
  const out = new Array(N).fill(0) as number[];
  for (let k = 0; k < K; k++) {
    const vk = v[k];
    for (let j = 0; j < N; j++) out[j] += vk * M[k][j];
  }
  return out;
}

function dot(a: number[], b: number[]): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

/** Numerically-stable softmax over a vector. Provided. */
function softmax(z: number[]): number[] {
  const m = Math.max(...z);
  const e = z.map((v) => Math.exp(v - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / s);
}

// ---------------------------------------------------------------------------
// Naive path (provided): recompute the whole prefix every step.
// ---------------------------------------------------------------------------

/**
 * Naive causal decoding: at each step t, RE-PROJECT keys/values for the whole
 * prefix x[0..t] from scratch, then attend.
 *
 * Returns { logits (n × dOut), kvOps }. kvOps counts key-projection operations,
 * one per row projected through Wk; for length-n this is 1+2+...+n = n(n+1)/2.
 *
 * This function is COMPLETE and serves as the ground truth.
 */
function decodeNaive(
  X: Matrix,
  Wq: Matrix,
  Wk: Matrix,
  Wv: Matrix,
  Wo: Matrix,
): { logits: Matrix; kvOps: number } {
  const n = X.length;
  const dK = Wq[0].length;
  const scale = Math.sqrt(dK);
  const logits: Matrix = [];
  let kvOps = 0;

  for (let t = 0; t <= n - 1; t++) {
    const qT = vecMatMul(X[t], Wq); // just the new token's query
    const K: Matrix = [];
    const V: Matrix = [];
    for (let i = 0; i <= t; i++) {
      K.push(vecMatMul(X[i], Wk)); // RE-PROJECTED every step
      V.push(vecMatMul(X[i], Wv));
      kvOps += 1; // projected one more key row this step
    }
    const scores = K.map((kI) => dot(qT, kI) / scale);
    const weights = softmax(scores);
    const context = new Array(V[0].length).fill(0) as number[];
    for (let i = 0; i <= t; i++)
      for (let d = 0; d < context.length; d++) context[d] += weights[i] * V[i][d];
    logits.push(vecMatMul(context, Wo));
  }

  return { logits, kvOps };
}

// ---------------------------------------------------------------------------
// Cached path — implement this
// ---------------------------------------------------------------------------

/**
 * Incremental causal decoding with a KV cache.
 *
 * Maintain a growing list of cached keys and values. At each step t:
 *   - project ONLY the new token X[t] into qT, kT, vT
 *   - APPEND kT, vT to the cache
 *   - attend qT over ALL cached keys/values (the causal prefix, for free)
 *
 * Returns { logits (n × dOut), kvOps }. Must match decodeNaive's logits exactly.
 * With the cache you project exactly ONE new key per step, so kvOps === n.
 *
 * TODO: implement.
 *   1. const dK = Wq[0].length; const scale = Math.sqrt(dK);
 *      const Kcache: Matrix = []; const Vcache: Matrix = [];
 *      const logits: Matrix = []; let kvOps = 0;
 *   2. for (let t = 0; t < X.length; t++):
 *        const qT = vecMatMul(X[t], Wq);
 *        const kT = vecMatMul(X[t], Wk);   // ONE key projection
 *        const vT = vecMatMul(X[t], Wv);
 *        kvOps += 1;
 *        Kcache.push(kT); Vcache.push(vT); // old entries reused, not recomputed
 *        const scores  = Kcache.map(kI => dot(qT, kI) / scale);
 *        const weights = softmax(scores);
 *        const context = zeros(dV); accumulate weights[i]*Vcache[i]
 *        logits.push(vecMatMul(context, Wo));
 *   3. return { logits, kvOps };
 */
function decodeWithCache(
  X: Matrix,
  Wq: Matrix,
  Wk: Matrix,
  Wv: Matrix,
  Wo: Matrix,
): { logits: Matrix; kvOps: number } {
  // TODO: implement incremental decoding with a KV cache
  throw new Error("TODO: implement decodeWithCache()");
}

// ---------------------------------------------------------------------------
// Harness — complete, do not edit
// ---------------------------------------------------------------------------

function seededWeights(rows: number, cols: number, seed: number): Matrix {
  let s = seed >>> 0;
  const scale = 1.0 / Math.sqrt(rows);
  const unif = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const gauss = () => {
    const u1 = unif() + 1e-12;
    const u2 = unif();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * scale;
  };
  return Array.from({ length: rows }, () => Array.from({ length: cols }, gauss));
}

function maxAbsDiff(a: number[], b: number[]): number {
  let m = 0;
  for (let i = 0; i < a.length; i++) m = Math.max(m, Math.abs(a[i] - b[i]));
  return m;
}

function main(): void {
  const n = 7,
    d = 8,
    dK = 8,
    dOut = 8;
  const X = seededWeights(n, d, 100);
  const Wq = seededWeights(d, dK, 1);
  const Wk = seededWeights(d, dK, 2);
  const Wv = seededWeights(d, dK, 3);
  const Wo = seededWeights(dK, dOut, 4);

  console.log("=".repeat(66));
  console.log("Task 4 — KV cache: incremental decoding vs naive recompute");
  console.log("=".repeat(66));
  console.log(`  sequence length n=${n}  d=${d}  dK=${dK}\n`);

  const naive = decodeNaive(X, Wq, Wk, Wv, Wo);
  const cached = decodeWithCache(X, Wq, Wk, Wv, Wo);

  // ── Check 1: identical per-step logits ──────────────────────────────────────
  let perStepOk = true;
  console.log("[1] Per-step logit agreement (naive vs cached):");
  for (let t = 0; t < n; t++) {
    const diff = maxAbsDiff(naive.logits[t], cached.logits[t]);
    const same = diff < 1e-5;
    perStepOk = perStepOk && same;
    console.log(`    step ${t}: match=${same}  max|Δ|=${diff.toExponential(2)}`);
  }
  console.log(`    all steps identical: ${perStepOk}\n`);

  // ── Check 2: op-count comparison ────────────────────────────────────────────
  const expectedNaive = (n * (n + 1)) / 2;
  console.log("[2] Key-projection operation counts:");
  console.log(
    `    naive  (recompute prefix each step): ${naive.kvOps}   expected n(n+1)/2 = ${expectedNaive}`,
  );
  console.log(
    `    cached (one new key per step)      : ${cached.kvOps}   expected n = ${n}`,
  );
  const opsOk = naive.kvOps === expectedNaive && cached.kvOps === n;
  const speedup = naive.kvOps / Math.max(cached.kvOps, 1);
  console.log(
    `    cache saves ${naive.kvOps - cached.kvOps} projections (${speedup.toFixed(1)}x fewer)\n`,
  );

  console.assert(perStepOk, "cached logits must equal naive logits at every step");
  console.assert(opsOk, "op counts must be n (cached) and n(n+1)/2 (naive)");
  if (perStepOk && opsOk) console.log("All checks passed. ✅");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
