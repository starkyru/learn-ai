/**
 * Task 1 🔴 — Multi-head self-attention with causal masking (plain arrays, no ML lib).
 *
 * What you'll learn:
 *   - Scaled dot-product attention: the core operation of every transformer
 *   - Why we divide by sqrt(dK) (keeps softmax gradients healthy)
 *   - Causal masking: how a decoder is stopped from "seeing the future"
 *   - Multi-head attention: split dModel into h independent subspaces, attend
 *     in each, concatenate, then project back
 *
 * The math (README derives each step in plain English):
 *
 *   Scaled dot-product attention, for queries Q, keys K, values V:
 *     scores  = Q @ Kᵀ / sqrt(dK)          shape (nQ, nK)
 *     scores  = scores + mask               mask is 0 or -inf per entry
 *     weights = softmax(scores)             row-wise, each row sums to 1
 *     output  = weights @ V                 shape (nQ, dV)
 *
 *   Causal mask (additive form): an (n, n) matrix that is 0 on and below the
 *   diagonal and -inf above it. Adding it before softmax drives the weight on
 *   every "future" position j > i to exactly 0.
 *
 *   Multi-head attention with h heads and model dim dModel (dK = dModel / h):
 *     project X -> Q, K, V ; split into h heads ; attend per head ;
 *     concatenate the head outputs ; apply output projection Wo.
 *
 * No external math library. Plain number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/01d-transformer/ts/01-attention.ts
 */

type Matrix = number[][];

const NEG_INF = -1e9; // a large negative number; "-inf" for masking purposes

// ---------------------------------------------------------------------------
// Matrix helpers (provided for you)
// ---------------------------------------------------------------------------

/** Matrix multiply: A (m×k) @ B (k×n) -> (m×n). */
function matMul(A: Matrix, B: Matrix): Matrix {
  const m = A.length,
    k = B.length,
    n = B[0].length;
  const out: Matrix = Array.from({ length: m }, () => new Array(n).fill(0) as number[]);
  for (let i = 0; i < m; i++)
    for (let p = 0; p < k; p++) {
      const aip = A[i][p];
      for (let j = 0; j < n; j++) out[i][j] += aip * B[p][j];
    }
  return out;
}

/** Transpose a matrix (n×m) -> (m×n). */
function transpose(A: Matrix): Matrix {
  return A[0].map((_, j) => A.map((row) => row[j]));
}

/** Slice columns [start, end) of every row. */
function sliceCols(A: Matrix, start: number, end: number): Matrix {
  return A.map((row) => row.slice(start, end));
}

/** Concatenate matrices side by side (same row count). */
function concatCols(mats: Matrix[]): Matrix {
  const rows = mats[0].length;
  const out: Matrix = [];
  for (let i = 0; i < rows; i++) {
    out.push(mats.flatMap((m) => m[i]));
  }
  return out;
}

// ---------------------------------------------------------------------------
// Core functions — implement these
// ---------------------------------------------------------------------------

/**
 * Scaled dot-product attention.
 *
 * @param Q queries, shape (nQ × dK)
 * @param K keys,    shape (nK × dK)
 * @param V values,  shape (nK × dV)
 * @param mask optional additive mask (nQ × nK): entries 0 (keep) or NEG_INF (block),
 *             added to the scores BEFORE softmax.
 * @returns { weights (nQ×nK, each row sums to 1), output (nQ×dV) }
 *
 * The softmax must be numerically stable: subtract the per-row max before exp().
 *
 * TODO: implement. Steps:
 *   - Form scores = matMul(Q, transpose(K)) and scale every entry by dividing by
 *     Math.sqrt(dK) (dK = K[0].length).
 *   - If a mask was passed, add its entries onto the scores (it blocks positions
 *     before the softmax).
 *   - Turn each score row into a probability distribution with a numerically-stable
 *     softmax: subtract that row's max before Math.exp, then divide by the row's sum
 *     so the row totals 1.
 *   - output = matMul(weights, V).
 *   - Return the { weights, output } object.
 */
function scaledDotProductAttention(
  Q: Matrix,
  K: Matrix,
  V: Matrix,
  mask: Matrix | null = null,
): { weights: Matrix; output: Matrix } {
  // TODO: implement scaled dot-product attention
  throw new Error("TODO: implement scaledDotProductAttention()");
}

/**
 * Build an (n × n) additive causal mask.
 *
 * Entry [i][j] is:
 *   0        if j <= i   (position i may attend to position j)
 *   NEG_INF  if j >  i   (position i must NOT attend to a future position)
 *
 * TODO: implement.
 *   Build an n×n array; for each i, j set NEG_INF when j > i, else 0.
 */
function causalMask(n: number): Matrix {
  // TODO: implement causal mask
  throw new Error("TODO: implement causalMask()");
}

/**
 * Multi-head self-attention.
 *
 * @param X  input, shape (n × dModel)
 * @param Wq @param Wk @param Wv projection weights, each (dModel × dModel)
 * @param Wo output projection, (dModel × dModel)
 * @param numHeads h; must divide dModel evenly. dK = dModel / h.
 * @param mask optional additive mask (n × n), applied inside every head.
 * @returns output, shape (n × dModel)
 *
 * TODO: implement. Steps:
 *   - Compute dK = dModel / numHeads.
 *   - Project X once into Q, K, V (each matMul(X, W...), n×dModel).
 *   - For each head, carve out that head's contiguous block of dK columns from Q, K, V
 *     with sliceCols (head hIdx owns columns hIdx*dK .. hIdx*dK+dK) and run
 *     scaledDotProductAttention on those slices, passing the mask through. Keep only
 *     each head's `output`.
 *   - Stitch the per-head outputs side by side with concatCols to get back to n×dModel.
 *   - Apply the output projection Wo (matMul) to the concatenation and return it.
 */
function multiHeadAttention(
  X: Matrix,
  Wq: Matrix,
  Wk: Matrix,
  Wv: Matrix,
  Wo: Matrix,
  numHeads: number,
  mask: Matrix | null = null,
): Matrix {
  // TODO: implement multi-head attention
  throw new Error("TODO: implement multiHeadAttention()");
}

// ---------------------------------------------------------------------------
// Harness — complete, do not edit
// ---------------------------------------------------------------------------

/** Deterministic Gaussian matrix (mulberry32 + Box-Muller), Xavier-ish scale. */
function seededWeights(rows: number, cols: number, seed: number): Matrix {
  let s = seed >>> 0;
  const scale = 1.0 / Math.sqrt(cols);
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

function identity(n: number): Matrix {
  return Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)),
  );
}

function allClose(A: Matrix, B: Matrix, atol = 1e-9): boolean {
  if (A.length !== B.length || A[0].length !== B[0].length) return false;
  for (let i = 0; i < A.length; i++)
    for (let j = 0; j < A[0].length; j++)
      if (Math.abs(A[i][j] - B[i][j]) > atol) return false;
  return true;
}

function round(x: number, d = 3): number {
  const f = 10 ** d;
  return Math.round(x * f) / f;
}

function main(): void {
  const n = 5,
    dModel = 8,
    h = 4;
  const X = seededWeights(n, dModel, 100);
  const Wq = seededWeights(dModel, dModel, 1);
  const Wk = seededWeights(dModel, dModel, 2);
  const Wv = seededWeights(dModel, dModel, 3);
  const Wo = seededWeights(dModel, dModel, 4);
  const I = identity(dModel);

  console.log("=".repeat(66));
  console.log("Task 1 — Multi-head self-attention with causal masking");
  console.log("=".repeat(66));
  console.log(`  n=${n}  dModel=${dModel}  numHeads=${h}  dK=${dModel / h}\n`);

  // ── Check 1: attention weight rows sum to 1 ─────────────────────────────────
  const Q = seededWeights(n, dModel, 10);
  const K = seededWeights(n, dModel, 11);
  const V = seededWeights(n, dModel, 12);
  const { weights } = scaledDotProductAttention(Q, K, V);
  const rowSums = weights.map((r) => r.reduce((a, b) => a + b, 0));
  console.log(
    "[1] Attention weight row sums:",
    rowSums.map((s) => round(s, 6)),
  );
  const rowsOk = rowSums.every((s) => Math.abs(s - 1) < 1e-6);
  console.log(`    rows sum to 1 (+/-1e-6): ${rowsOk}\n`);

  // ── Check 2: causal mask zeroes out the future ──────────────────────────────
  const mask = causalMask(n);
  const { weights: cweights } = scaledDotProductAttention(Q, K, V, mask);
  let causalOk = true;
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++)
      if (Math.abs(cweights[i][j]) > 1e-9) causalOk = false;
  console.log("[2] Causal attention weights (upper triangle should be all 0):");
  for (const row of cweights)
    console.log("   ", row.map((w) => round(w, 3)).join("  "));
  console.log(`    no attention to future positions (j>i == 0): ${causalOk}\n`);

  // ── Check 3: h=1 multi-head equals single-head SDPA ─────────────────────────
  const mha1 = multiHeadAttention(X, I, I, I, I, 1);
  const { output: sdpaOut } = scaledDotProductAttention(X, X, X);
  const singleOk = allClose(mha1, sdpaOut, 1e-9);
  console.log(`[3] MHA(h=1, identity weights) == single-head SDPA: ${singleOk}\n`);

  // ── Check 4: shapes ─────────────────────────────────────────────────────────
  const out = multiHeadAttention(X, Wq, Wk, Wv, Wo, h, causalMask(n));
  const shapeOk = out.length === n && out[0].length === dModel;
  const finite = out.every((r) => r.every((v) => Number.isFinite(v)));
  console.log(
    `[4] MHA output shape: ${out.length} x ${out[0].length}  (expected ${n} x ${dModel})  ok=${shapeOk}`,
  );
  console.log(`    all outputs finite: ${finite}\n`);

  console.assert(rowsOk, "attention weight rows must sum to 1");
  console.assert(causalOk, "causal mask must zero out attention to future positions");
  console.assert(
    singleOk,
    "MHA with h=1 and identity weights must equal single-head SDPA",
  );
  console.assert(shapeOk, "MHA output shape must be (n, dModel)");
  if (rowsOk && causalOk && singleOk && shapeOk) console.log("All checks passed. ✅");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
