/**
 * attention.ts — scaled dot-product self-attention (Task 3, 🔴 STUB).
 *
 * What it teaches:
 *   The single most important operation in a transformer. You'll implement
 *       Attention(Q, K, V) = softmax( (Q · Kᵀ) / √dₖ ) · V
 *   using plain number[][] arrays (no math library). See README Concept 3 for
 *   the full derivation. Fill in the TODOs; the scaffold below checks your work.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/01-fundamentals/ts/attention.ts
 */

type Matrix = number[][];

/** Matrix multiply: (m×k) · (k×n) -> (m×n). Provided for you. */
function matmul(a: Matrix, b: Matrix): Matrix {
  const m = a.length;
  const k = b.length;
  const n = b[0].length;
  const out: Matrix = Array.from({ length: m }, () => new Array(n).fill(0));
  for (let i = 0; i < m; i++) {
    for (let p = 0; p < k; p++) {
      const aip = a[i][p];
      for (let j = 0; j < n; j++) out[i][j] += aip * b[p][j];
    }
  }
  return out;
}

/** Transpose a matrix. Provided for you. */
function transpose(a: Matrix): Matrix {
  return a[0].map((_, j) => a.map((row) => row[j]));
}

/**
 * Row-wise softmax: each row becomes a probability distribution summing to 1.
 *
 * TODO:
 *   For each row:
 *     1. Find the row max; subtract it from every element BEFORE exp (numerical
 *        stability — same result, no overflow).
 *     2. Exponentiate each element.
 *     3. Divide each element by the row's sum of exponentials.
 */
function softmaxRows(_x: Matrix): Matrix {
  throw new Error("Implement row-wise softmax — see the docstring TODOs.");
}

/**
 * Scaled dot-product attention.
 *
 * @param Q queries, shape (n × dₖ)
 * @param K keys,    shape (n × dₖ)
 * @param V values,  shape (n × dᵥ)
 * @returns { weights (n×n, each row sums to 1), output (n×dᵥ) }
 *
 * TODO:
 *   1. dK = Q[0].length.
 *   2. scores = matmul(Q, transpose(K))          // (n × n)
 *   3. divide every score by Math.sqrt(dK)        // the "scaled" part
 *   4. weights = softmaxRows(scores)
 *   5. output = matmul(weights, V)                // (n × dᵥ)
 *   6. return { weights, output }
 */
function attention(_Q: Matrix, _K: Matrix, _V: Matrix): { weights: Matrix; output: Matrix } {
  throw new Error("Implement scaled dot-product attention — see the TODOs.");
}

function randMatrix(rows: number, cols: number, seed: number): Matrix {
  // Tiny deterministic PRNG (mulberry32) so the demo is reproducible.
  let s = seed >>> 0;
  const rnd = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296 - 0.5;
  };
  return Array.from({ length: rows }, () => Array.from({ length: cols }, rnd));
}

function main(): void {
  const seqLen = 4;
  const dK = 8;
  const dV = 8;
  const Q = randMatrix(seqLen, dK, 1);
  const K = randMatrix(seqLen, dK, 2);
  const V = randMatrix(seqLen, dV, 3);

  const { weights, output } = attention(Q, K, V);

  console.log("Attention weights (each row should sum to 1):");
  for (const row of weights) console.log(row.map((w) => w.toFixed(3)).join("  "));

  const rowSums = weights.map((row) => row.reduce((a, b) => a + b, 0));
  console.log("\nRow sums:", rowSums.map((s) => s.toFixed(6)));
  console.log(`\nOutput shape: ${output.length} x ${output[0].length} (expected ${seqLen} x ${dV})`);

  console.assert(weights.length === seqLen && weights[0].length === seqLen, "weights must be n x n");
  console.assert(output.length === seqLen && output[0].length === dV, "output must be n x d_v");
  console.assert(
    rowSums.every((s) => Math.abs(s - 1) < 1e-9),
    "each weight row must sum to 1",
  );
  console.log("\nAll checks passed. ✅");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
