/**
 * Task 3 🔴 — A full pre-LN transformer DECODER block, FROM SCRATCH (plain arrays).
 *
 * What you'll learn:
 *   - LayerNorm: normalize each row to mean 0 / variance 1, then scale+shift (γ, β).
 *     (Unlike BatchNorm, it normalizes across FEATURES per token — batch-size agnostic.)
 *   - GELU: the smooth activation used in GPT-family models (tanh approximation).
 *   - The position-wise feed-forward network (FFN): Linear -> GELU -> Linear, applied
 *     identically to every position, usually widening to 4× dModel in the middle.
 *   - The pre-LN residual block that GPT-2 and friends actually use:
 *         x = x + MHA(LN1(x), causal)      // attention sublayer + residual
 *         x = x + FFN(LN2(x))              // feed-forward sublayer + residual
 *     "Pre-LN" = normalize the INPUT to each sublayer; the residual path stays clean.
 *
 * The math (README derives each step in plain English):
 *
 *   LayerNorm, per row x (length d):
 *     mu   = mean(x)
 *     var  = mean((x - mu)^2)
 *     xhat = (x - mu) / sqrt(var + eps)
 *     out  = gamma * xhat + beta           (gamma, beta length d; elementwise)
 *
 *   GELU (tanh approximation):
 *     gelu(x) = 0.5 * x * (1 + tanh( sqrt(2/pi) * (x + 0.044715 * x^3) ))
 *
 *   FFN:
 *     h = gelu(x @ W1 + b1)                (x: (n,d) -> (n, dFf))
 *     y = h @ W2 + b2                      ((n, dFf) -> (n, d))
 *
 * No external math library. Plain number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/01d-transformer/ts/03-decoder-block.ts
 */

type Matrix = number[][];

const NEG_INF = -1e9;

// ---------------------------------------------------------------------------
// Matrix helpers (provided)
// ---------------------------------------------------------------------------

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

function transpose(A: Matrix): Matrix {
  return A[0].map((_, j) => A.map((row) => row[j]));
}

function sliceCols(A: Matrix, start: number, end: number): Matrix {
  return A.map((row) => row.slice(start, end));
}

function concatCols(mats: Matrix[]): Matrix {
  const rows = mats[0].length;
  const out: Matrix = [];
  for (let i = 0; i < rows; i++) out.push(mats.flatMap((m) => m[i]));
  return out;
}

function addMat(A: Matrix, B: Matrix): Matrix {
  return A.map((row, i) => row.map((v, j) => v + B[i][j]));
}

/** Add a bias vector to each row. */
function addBiasRow(A: Matrix, b: number[]): Matrix {
  return A.map((row) => row.map((v, j) => v + b[j]));
}

// ---------------------------------------------------------------------------
// Attention helpers (provided — from Task 1, self-contained)
// ---------------------------------------------------------------------------

function scaledDotProductAttention(
  Q: Matrix,
  K: Matrix,
  V: Matrix,
  mask: Matrix | null,
): Matrix {
  const dK = K[0].length;
  const scale = Math.sqrt(dK);
  const scores = matMul(Q, transpose(K)).map((row) => row.map((v) => v / scale));
  if (mask)
    for (let i = 0; i < scores.length; i++)
      for (let j = 0; j < scores[0].length; j++) scores[i][j] += mask[i][j];
  const weights = scores.map((row) => {
    const rowMax = Math.max(...row);
    const exps = row.map((v) => Math.exp(v - rowMax));
    const sum = exps.reduce((a, b) => a + b, 0);
    return exps.map((e) => e / sum);
  });
  return matMul(weights, V);
}

function causalMask(n: number): Matrix {
  return Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (j > i ? NEG_INF : 0)),
  );
}

function multiHeadAttention(
  X: Matrix,
  Wq: Matrix,
  Wk: Matrix,
  Wv: Matrix,
  Wo: Matrix,
  numHeads: number,
  mask: Matrix | null,
): Matrix {
  const dModel = X[0].length;
  const dK = dModel / numHeads;
  const Q = matMul(X, Wq),
    K = matMul(X, Wk),
    V = matMul(X, Wv);
  const heads: Matrix[] = [];
  for (let h = 0; h < numHeads; h++) {
    const s = h * dK,
      e = s + dK;
    heads.push(
      scaledDotProductAttention(
        sliceCols(Q, s, e),
        sliceCols(K, s, e),
        sliceCols(V, s, e),
        mask,
      ),
    );
  }
  return matMul(concatCols(heads), Wo);
}

// ---------------------------------------------------------------------------
// Core functions — implement these
// ---------------------------------------------------------------------------

/**
 * Row-wise layer normalization.
 *
 * For each row (a token's feature vector):
 *   mu   = mean over the row
 *   var  = mean of (x - mu)^2 over the row     (population variance)
 *   xhat = (x - mu) / sqrt(var + eps)
 *   out  = gamma * xhat + beta                 (elementwise; gamma, beta length d)
 *
 * With gamma=1, beta=0 each output row has mean ~0 and variance ~1.
 *
 * TODO: implement. For each row independently: compute its mean, then its population
 * variance (the mean of the squared deviations from that mean — no n-1 correction).
 * Normalise each entry with (value - mean) / Math.sqrt(variance + eps), then apply
 * the affine scale-and-shift per column using gamma[j] and beta[j]. Return the
 * resulting matrix.
 */
function layerNorm(x: Matrix, gamma: number[], beta: number[], eps = 1e-5): Matrix {
  // TODO: implement layer norm
  throw new Error("TODO: implement layerNorm()");
}

/**
 * GELU activation (tanh approximation), applied elementwise.
 *
 *   gelu(x) = 0.5 * x * (1 + tanh( sqrt(2/pi) * (x + 0.044715 * x^3) ))
 *
 * TODO: implement using the formula above (Math.tanh, Math.sqrt, Math.PI).
 */
function gelu(x: Matrix): Matrix {
  // TODO: implement gelu
  throw new Error("TODO: implement gelu()");
}

/**
 * Position-wise feed-forward network: Linear -> GELU -> Linear.
 *
 *   h = gelu(x @ W1 + b1)     // (n, d) -> (n, dFf)
 *   y = h @ W2 + b2           // (n, dFf) -> (n, d)
 *
 * TODO: implement the two linear layers (matMul + addBiasRow) with gelu() between.
 */
function ffn(x: Matrix, W1: Matrix, b1: number[], W2: Matrix, b2: number[]): Matrix {
  // TODO: implement feed-forward network
  throw new Error("TODO: implement ffn()");
}

// ---------------------------------------------------------------------------
// Transformer decoder block
// ---------------------------------------------------------------------------

interface BlockParams {
  Wq: Matrix;
  Wk: Matrix;
  Wv: Matrix;
  Wo: Matrix;
  gamma1: number[];
  beta1: number[];
  gamma2: number[];
  beta2: number[];
  W1: Matrix;
  b1: number[];
  W2: Matrix;
  b2: number[];
}

class TransformerBlock {
  constructor(
    private p: BlockParams,
    private numHeads: number,
  ) {}

  /**
   * Run one pre-LN decoder block over x of shape (n × dModel).
   *
   * TODO: implement the two pre-LN sublayers (build a causalMask from x.length first):
   *   - Attention sublayer: layerNorm the input with gamma1/beta1, feed that through
   *     multiHeadAttention (Wq/Wk/Wv/Wo, this.numHeads, the mask), then addMat the
   *     result back onto x (the residual connection).
   *   - Feed-forward sublayer: layerNorm the running x with gamma2/beta2, feed that
   *     through ffn (W1/b1/W2/b2), then addMat it back onto x.
   *   - Return the updated x. Both sublayers follow x = x + sublayer(LN(x)); the
   *     residual path itself is never normalised.
   */
  forward(x: Matrix): Matrix {
    // TODO: implement the pre-LN decoder block
    throw new Error("TODO: implement TransformerBlock.forward()");
  }
}

// ---------------------------------------------------------------------------
// Harness — complete, do not edit
// ---------------------------------------------------------------------------

function seededMatrix(rows: number, cols: number, scale: number, seed: number): Matrix {
  let s = seed >>> 0;
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

function makeBlockParams(dModel: number, dFf: number, seed: number): BlockParams {
  const sAttn = 1.0 / Math.sqrt(dModel);
  const sFf = 1.0 / Math.sqrt(dModel);
  const sFf2 = 1.0 / Math.sqrt(dFf);
  return {
    Wq: seededMatrix(dModel, dModel, sAttn, seed + 1),
    Wk: seededMatrix(dModel, dModel, sAttn, seed + 2),
    Wv: seededMatrix(dModel, dModel, sAttn, seed + 3),
    Wo: seededMatrix(dModel, dModel, sAttn, seed + 4),
    gamma1: new Array(dModel).fill(1) as number[],
    beta1: new Array(dModel).fill(0) as number[],
    gamma2: new Array(dModel).fill(1) as number[],
    beta2: new Array(dModel).fill(0) as number[],
    W1: seededMatrix(dModel, dFf, sFf, seed + 5),
    b1: new Array(dFf).fill(0) as number[],
    W2: seededMatrix(dFf, dModel, sFf2, seed + 6),
    b2: new Array(dModel).fill(0) as number[],
  };
}

function mean(a: number[]): number {
  return a.reduce((x, y) => x + y, 0) / a.length;
}
function variance(a: number[]): number {
  const m = mean(a);
  return mean(a.map((v) => (v - m) ** 2));
}
function round(x: number, d = 3): number {
  const f = 10 ** d;
  return Math.round(x * f) / f;
}

function main(): void {
  const n = 5,
    dModel = 16,
    dFf = 64,
    numHeads = 4,
    numLayers = 3;

  console.log("=".repeat(66));
  console.log("Task 3 — Pre-LN transformer decoder block");
  console.log("=".repeat(66));
  console.log(
    `  n=${n}  dModel=${dModel}  dFf=${dFf}  heads=${numHeads}  layers=${numLayers}\n`,
  );

  // ── Check 1: layerNorm produces mean 0 / var 1 per row (before gamma/beta) ───
  // deliberately off-center input: scale 3, shift 5
  const x = seededMatrix(n, dModel, 3.0, 55).map((row) => row.map((v) => v + 5.0));
  const ones = new Array(dModel).fill(1) as number[];
  const zeros = new Array(dModel).fill(0) as number[];
  const normed = layerNorm(x, ones, zeros);
  const rowMeans = normed.map(mean);
  const rowVars = normed.map(variance);
  console.log(
    "[1] LayerNorm row means:",
    rowMeans.map((v) => round(v, 6)),
  );
  console.log(
    "    LayerNorm row vars :",
    rowVars.map((v) => round(v, 6)),
  );
  const meanOk = rowMeans.every((v) => Math.abs(v) < 1e-6);
  const varOk = rowVars.every((v) => Math.abs(v - 1) < 1e-5);
  console.log(`    mean ~ 0: ${meanOk}   var ~ 1: ${varOk}\n`);

  // ── Check 2: one block preserves shape ──────────────────────────────────────
  const params = Array.from({ length: numLayers }, (_, i) =>
    makeBlockParams(dModel, dFf, 100 + i * 10),
  );
  const x0 = seededMatrix(n, dModel, 1.0, 200);
  const y0 = new TransformerBlock(params[0], numHeads).forward(x0);
  const shapeOk = y0.length === n && y0[0].length === dModel;
  console.log(
    `[2] One block: input ${x0.length}x${x0[0].length} -> output ${y0.length}x${y0[0].length}   shape preserved: ${shapeOk}\n`,
  );

  // ── Check 3: stack N=3 blocks; output finite ────────────────────────────────
  let h = seededMatrix(n, dModel, 1.0, 300);
  for (let i = 0; i < numLayers; i++)
    h = new TransformerBlock(params[i], numHeads).forward(h);
  const finiteOk = h.every((row) => row.every((v) => Number.isFinite(v)));
  console.log(
    `[3] Stacked ${numLayers} blocks: output shape ${h.length}x${h[0].length}`,
  );
  console.log(`    all outputs finite: ${finiteOk}`);
  console.log(
    `    output row-0 (rounded): ${h[0].map((v) => round(v, 3)).join(", ")}\n`,
  );

  console.assert(meanOk, "LayerNorm rows must have mean ~ 0");
  console.assert(varOk, "LayerNorm rows must have variance ~ 1");
  console.assert(shapeOk, "a block must preserve input shape");
  console.assert(finiteOk, "stacked blocks must output finite numbers");
  if (meanOk && varOk && shapeOk && finiteOk) console.log("All checks passed. ✅");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
