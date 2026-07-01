/**
 * Task 2 🟡 — Sinusoidal positional encoding, and why order matters (plain arrays).
 *
 * What you'll learn:
 *   - Self-attention alone is PERMUTATION-EQUIVARIANT: shuffle the input tokens and
 *     the outputs shuffle the same way. The mechanism has no idea what ORDER the
 *     tokens came in. "dog bites man" and "man bites dog" would be indistinguishable.
 *   - Positional encoding fixes this by adding a unique, position-dependent vector
 *     to each token's embedding BEFORE attention. Now the input to attention differs
 *     by more than a permutation, so the outputs genuinely differ.
 *
 * The math (README derives this in plain English):
 *
 *   For position pos (0-based) and dimension index i (0-based), with model dim d:
 *     PE[pos][2i]   = sin( pos / 10000^(2i/d) )
 *     PE[pos][2i+1] = cos( pos / 10000^(2i/d) )
 *
 *   Even columns get a sine, odd columns get a cosine, and the wavelength grows
 *   geometrically across the dimension axis. Every position gets a distinct
 *   fingerprint; nearby positions have higher dot-product than far ones.
 *
 * No external math library. Plain number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/01d-transformer/ts/02-positional-encoding.ts
 */

type Matrix = number[][];

// ---------------------------------------------------------------------------
// Core function — implement this
// ---------------------------------------------------------------------------

/**
 * Build the (maxLen × dModel) sinusoidal positional-encoding table.
 *
 *   PE[pos][2i]   = sin( pos / 10000^(2i/dModel) )
 *   PE[pos][2i+1] = cos( pos / 10000^(2i/dModel) )
 *
 * dModel is assumed even. Every value lies in [-1, 1] (sin/cos range).
 *
 * TODO: implement. Build a maxLen × dModel array. For each position pos and each
 * paired index i (0 .. dModel/2 - 1), compute the divisor 10000 raised to
 * (2*i / dModel) and the angle pos / divisor. Write Math.sin(angle) into the EVEN
 * column (2*i) and Math.cos(angle) into the ODD column (2*i + 1). Return the table.
 */
function sinusoidalEncoding(maxLen: number, dModel: number): Matrix {
  // TODO: implement sinusoidal positional encoding
  throw new Error("TODO: implement sinusoidalEncoding()");
}

// ---------------------------------------------------------------------------
// Attention (provided — from Task 1, self-contained here)
// ---------------------------------------------------------------------------

/** Plain self-attention SDPA(X, X, X) — output only. Provided. */
function selfAttention(X: Matrix): Matrix {
  const n = X.length,
    dK = X[0].length;
  const scale = Math.sqrt(dK);
  const out: Matrix = [];
  for (let i = 0; i < n; i++) {
    // scores of query i against every key j
    const scores = new Array(n).fill(0) as number[];
    for (let j = 0; j < n; j++) {
      let dot = 0;
      for (let d = 0; d < dK; d++) dot += X[i][d] * X[j][d];
      scores[j] = dot / scale;
    }
    // stable softmax
    const rowMax = Math.max(...scores);
    const exps = scores.map((s) => Math.exp(s - rowMax));
    const sum = exps.reduce((a, b) => a + b, 0);
    const w = exps.map((e) => e / sum);
    // weighted sum of value rows (V == X here)
    const o = new Array(dK).fill(0) as number[];
    for (let j = 0; j < n; j++) for (let d = 0; d < dK; d++) o[d] += w[j] * X[j][d];
    out.push(o);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Harness — complete, do not edit
// ---------------------------------------------------------------------------

function seededMatrix(rows: number, cols: number, seed: number): Matrix {
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
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
  return Array.from({ length: rows }, () => Array.from({ length: cols }, gauss));
}

/** Deterministic permutation of [0..n) from a seed (Fisher-Yates). */
function seededPermutation(n: number, seed: number): number[] {
  const perm = Array.from({ length: n }, (_, i) => i);
  let s = seed >>> 0;
  const rnd = () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff;
    return s / 0x7fffffff;
  };
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [perm[i], perm[j]] = [perm[j], perm[i]];
  }
  return perm;
}

function applyPerm(X: Matrix, perm: number[]): Matrix {
  return perm.map((i) => X[i]);
}

function addMat(A: Matrix, B: Matrix): Matrix {
  return A.map((row, i) => row.map((v, j) => v + B[i][j]));
}

function allClose(A: Matrix, B: Matrix, atol = 1e-9): boolean {
  if (A.length !== B.length || A[0].length !== B[0].length) return false;
  for (let i = 0; i < A.length; i++)
    for (let j = 0; j < A[0].length; j++)
      if (Math.abs(A[i][j] - B[i][j]) > atol) return false;
  return true;
}

function dot(a: number[], b: number[]): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

function main(): void {
  const n = 6,
    dModel = 16;

  console.log("=".repeat(66));
  console.log("Task 2 — Sinusoidal positional encoding & why order matters");
  console.log("=".repeat(66));

  // ── Build the PE table and inspect it ───────────────────────────────────────
  const pe = sinusoidalEncoding(n, dModel);
  const flat = pe.flat();
  const peMin = Math.min(...flat),
    peMax = Math.max(...flat);
  console.log(
    `\n[shape] PE shape: ${pe.length} x ${pe[0].length}  (expected ${n} x ${dModel})`,
  );
  console.log(
    `[range] PE min=${peMin.toFixed(4)}  max=${peMax.toFixed(4)}  (expected within [-1, 1])`,
  );
  const inRange = peMin >= -1 - 1e-9 && peMax <= 1 + 1e-9;

  // ── Permutation-equivariance experiment ─────────────────────────────────────
  const X = seededMatrix(n, dModel, 7);
  const perm = seededPermutation(n, 3);
  const XPerm = applyPerm(X, perm);

  // (a) WITHOUT positional encoding: out(perm(X)) == perm(out(X)). Order invisible.
  const out = selfAttention(X);
  const outPerm = selfAttention(XPerm);
  const equivariant = allClose(outPerm, applyPerm(out, perm), 1e-9);
  console.log("\n[no PE] attention is permutation-equivariant?");
  console.log(`        out(perm(X)) == perm(out(X)) : ${equivariant}`);

  // (b) WITH positional encoding added before attention (by absolute slot):
  const Xp = addMat(X, pe);
  const XpPerm = addMat(XPerm, pe); // PE added by slot, NOT permuted with tokens
  const outPe = selfAttention(Xp);
  const outPePerm = selfAttention(XpPerm);
  const equivariantWithPe = allClose(outPePerm, applyPerm(outPe, perm), 1e-9);
  console.log("\n[with PE] still permutation-equivariant?");
  console.log(`          out(perm(X)+PE) == perm(out(X+PE)) : ${equivariantWithPe}`);
  console.log("          (should be FALSE — PE breaks the symmetry, encoding order)");

  // ── Locality check ──────────────────────────────────────────────────────────
  const near = dot(pe[0], pe[1]);
  const far = dot(pe[0], pe[n - 1]);
  const localityOk = near > far;
  console.log(`\n[locality] PE[0]·PE[1] (near) = ${near.toFixed(4)}`);
  console.log(`           PE[0]·PE[${n - 1}] (far)  = ${far.toFixed(4)}`);
  console.log(`           near > far : ${localityOk}`);

  console.assert(inRange, "PE values must lie in [-1, 1]");
  console.assert(equivariant, "without PE, attention must be permutation-equivariant");
  console.assert(
    !equivariantWithPe,
    "with PE, the outputs must differ (order encoded)",
  );
  console.assert(
    localityOk,
    "nearby positions must have higher PE dot-product than far ones",
  );
  if (inRange && equivariant && !equivariantWithPe && localityOk)
    console.log("\nAll checks passed. ✅");
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
