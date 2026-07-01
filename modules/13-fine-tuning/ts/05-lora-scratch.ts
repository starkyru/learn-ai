/**
 * Task 5 🔴 — Understand LoRA: implement the low-rank update from scratch.
 *
 * What you'll learn:
 *   - The LoRA math at the level of matrix algebra (no magic, no framework)
 *   - Why B·A starts at zero (B initialised to zeros, A random)
 *   - Exactly how many parameters LoRA saves vs full fine-tuning
 *   - Numerical verification that (W + B@A)@x equals W@x + B@(A@x)
 *
 * No ML framework. Only plain TypeScript arrays (number[][]).
 *
 * The math:
 *   A weight update ΔW ∈ ℝ^{d_out × d_in} has d_out * d_in parameters.
 *   LoRA represents it as ΔW = B · A  where:
 *     B ∈ ℝ^{d_out × r}   (r << d_out)
 *     A ∈ ℝ^{r  × d_in}   (r << d_in)
 *
 *   B is initialised to zero.  So at the start of training, ΔW = 0 and the
 *   model's output is unchanged — a safe, stable starting point.
 *
 *   A is initialised with small random values (normal(0, 0.01)).
 *
 *   At inference:
 *     output = W @ x + B @ (A @ x)   ← LoRA correction added to base output
 *
 *   Parameter savings for d=4096, r=16:
 *     Full   : 4096² = 16,777,216
 *     LoRA   : 16 * (4096 + 4096) = 131,072  → ~128× fewer params
 *
 * How to run:
 *   pnpm tsx modules/13-fine-tuning/ts/05-lora-scratch.ts
 *
 * The harness is RUNNABLE. You implement the marked TODO sections.
 */

// ---------------------------------------------------------------------------
// Matrix utilities (provided — do not modify)
// ---------------------------------------------------------------------------

/** Matrix-vector multiply: M [rows×cols] @ v [cols] → result [rows] */
function matvec(M: number[][], v: number[]): number[] {
  const rows = M.length;
  const cols = M[0].length;
  const out = new Array<number>(rows).fill(0);
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      out[i] += M[i][j] * v[j];
    }
  }
  return out;
}

/** Matrix-matrix multiply: A [r×c] @ B [c×p] → result [r×p] */
function matmul(A: number[][], B: number[][]): number[][] {
  const r = A.length;
  const c = A[0].length;
  const p = B[0].length;
  const out: number[][] = Array.from({ length: r }, () => new Array<number>(p).fill(0));
  for (let i = 0; i < r; i++) {
    for (let k = 0; k < c; k++) {
      for (let j = 0; j < p; j++) {
        out[i][j] += A[i][k] * B[k][j];
      }
    }
  }
  return out;
}

/** Matrix add element-wise: A + B (same shape) */
function matadd(A: number[][], B: number[][]): number[][] {
  return A.map((row, i) => row.map((v, j) => v + B[i][j]));
}

/** Vector add element-wise */
function vecadd(a: number[], b: number[]): number[] {
  return a.map((v, i) => v + b[i]);
}

// Simple seeded PRNG (Mulberry32)
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

// Box-Muller transform for normal samples
function randnMatrix(rows: number, cols: number, std: number, seed: number): number[][] {
  const rng = makePrng(seed);
  return Array.from({ length: rows }, () =>
    Array.from({ length: cols }, () => {
      const u = Math.max(rng(), 1e-10);
      const v = rng();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * std;
    }),
  );
}

function zerosMatrix(rows: number, cols: number): number[][] {
  return Array.from({ length: rows }, () => new Array<number>(cols).fill(0));
}

// ---------------------------------------------------------------------------
// LoRA initialisation
// ---------------------------------------------------------------------------

interface LoraAdapter {
  A: number[][]; // [r × d_in]
  B: number[][]; // [d_out × r]
}

/**
 * Initialise LoRA adapter matrices A and B.
 *
 * A : shape [r, dIn]   — random normal, std=0.01
 * B : shape [dOut, r]  — zeros
 *
 * B = 0 means the LoRA correction is zero at init, keeping training stable.
 * A is non-zero so gradients flow immediately.
 *
 * TODO:
 *   1. Build A as an [r × dIn] matrix of small normal samples (std ~0.01) —
 *      the randnMatrix(rows, cols, std, seed) helper does this.
 *   2. Build B as an [dOut × r] all-zeros matrix (the zerosMatrix helper).
 *   3. Return the adapter { A, B }.
 */
function loraInit(dOut: number, dIn: number, r: number, seed = 42): LoraAdapter {
  // TODO: implement loraInit
  throw new Error("TODO: implement loraInit()");
}

// ---------------------------------------------------------------------------
// LoRA forward pass
// ---------------------------------------------------------------------------

/**
 * Compute the LoRA-adapted output.
 *
 * output = W @ x + B @ (A @ x)
 *        = (W + B @ A) @ x    ← same result, different order
 *
 * TODO:
 *   Build the result from matrix-vector products (the matvec helper) and
 *   vecadd. Compute the base projection W @ x, then the correction in the
 *   efficient order — A @ x first (length-r), then B @ that — and add them.
 */
function loraForward(
  x: number[],
  W: number[][],
  A: number[][],
  B: number[][],
): number[] {
  // TODO: implement loraForward
  throw new Error("TODO: implement loraForward()");
}

// ---------------------------------------------------------------------------
// Parameter counting
// ---------------------------------------------------------------------------

/**
 * Return parameter counts for full fine-tuning vs LoRA.
 *
 * Returns { full: dOut * dIn, lora: r * (dIn + dOut) }
 *
 * TODO: implement the two formulas.
 */
function countParams(dOut: number, dIn: number, r: number): { full: number; lora: number } {
  // TODO: implement countParams
  throw new Error("TODO: implement countParams()");
}

// ---------------------------------------------------------------------------
// Numerical equivalence check
// ---------------------------------------------------------------------------

/**
 * Check that (W + B@A) @ x  equals  W@x + B@(A@x) to within `tol`.
 *
 * TODO:
 *   1. Compute the merged-way output: form (W + B@A) with matadd/matmul, then
 *      apply it to x with matvec.
 *   2. Compute the factored-way output — that's exactly what loraForward does.
 *   3. Find the largest absolute element-wise difference between the two.
 *   4. Return whether that max difference is below tol.
 */
function verifyEquivalence(
  W: number[][],
  A: number[][],
  B: number[][],
  x: number[],
  tol = 1e-9,
): boolean {
  // TODO: implement verifyEquivalence
  throw new Error("TODO: implement verifyEquivalence()");
}

/**
 * Verify that a freshly initialised LoRA adapter contributes zero correction.
 *
 * Because B = 0, B @ (A @ x) must be the zero vector.
 *
 * TODO:
 *   1. Compute just the LoRA correction term, B @ (A @ x), via nested matvec.
 *   2. Return whether every element of that correction is exactly zero.
 */
function verifyZeroAtInit(A: number[][], B: number[][], x: number[]): boolean {
  // TODO: implement verifyZeroAtInit
  throw new Error("TODO: implement verifyZeroAtInit()");
}

// ---------------------------------------------------------------------------
// Parameter savings table
// ---------------------------------------------------------------------------

/**
 * Print a table of full vs LoRA parameter counts for typical model sizes.
 *
 * Rows: d = 512, 1024, 2048, 4096
 * Cols: r = 4, 8, 16, 64
 *
 * Format per row:
 *   d=512   r=4    full=262,144   lora=4,096   savings=64.0x
 *
 * TODO: implement using countParams().
 */
function paramSavingsTable(): void {
  const dims = [512, 1024, 2048, 4096];
  const ranks = [4, 8, 16, 64];
  // TODO: implement paramSavingsTable
  throw new Error("TODO: implement paramSavingsTable()");
}

// ---------------------------------------------------------------------------
// Harness — RUNNABLE, do not modify
// ---------------------------------------------------------------------------

function main() {
  console.log("=".repeat(60));
  console.log("LoRA FROM SCRATCH (TypeScript)");
  console.log("=".repeat(60));

  const dOut = 64;
  const dIn = 64;
  const r = 8;

  // Frozen pre-trained weight and input
  const W = randnMatrix(dOut, dIn, 1.0, 0);
  const x = randnMatrix(1, dIn, 1.0, 1)[0];

  console.log(`\n1. Initialising LoRA (dOut=${dOut}, dIn=${dIn}, r=${r})...`);
  const { A, B } = loraInit(dOut, dIn, r, 42);
  console.log(`   A shape: [${A.length}, ${A[0].length}], B shape: [${B.length}, ${B[0].length}]`);
  const bIsZero = B.every((row) => row.every((v) => v === 0));
  console.log(`   B is all zeros: ${bIsZero}`);

  console.log("\n2. Checking zero-at-init property...");
  const zeroOk = verifyZeroAtInit(A, B, x);
  console.log(`   LoRA correction is zero at init: ${zeroOk}`);
  if (!zeroOk) throw new Error("B should be zeros so LoRA correction is zero at init!");

  console.log("\n3. Forward pass...");
  const out = loraForward(x, W, A, B);
  const norm = Math.sqrt(out.reduce((s, v) => s + v * v, 0));
  console.log(`   Output length: ${out.length}, norm: ${norm.toFixed(4)}`);

  console.log("\n4. Numerical equivalence check...");
  const eqOk = verifyEquivalence(W, A, B, x);
  console.log(`   (W + B@A)@x  ==  W@x + B@(A@x): ${eqOk}`);
  if (!eqOk) throw new Error("Equivalence check failed!");

  console.log("\n5. Parameter savings:");
  const params = countParams(dOut, dIn, r);
  console.log(`   Full fine-tune: ${params.full.toLocaleString()} params`);
  console.log(`   LoRA (r=${r}):    ${params.lora.toLocaleString()} params`);
  console.log(`   Savings: ${(params.full / params.lora).toFixed(1)}x`);

  console.log("\n6. Parameter savings table:");
  paramSavingsTable();

  console.log("\nAll checks passed!");
}

main();
