/**
 * Task 2 🔴 — Bias–variance tradeoff, k-fold CV, and ridge regularisation.
 *
 * What you'll learn:
 *   - Why train error and generalisation error diverge (the U-curve)
 *   - Bias vs variance: underfitting (high bias) vs overfitting (high variance)
 *   - k-fold cross-validation as an honest estimate of generalisation error
 *   - Ridge (L2) regularisation: shrink weights to trade a little bias for a lot
 *     less variance — WITHOUT regularising the intercept
 *
 * The math (README derives each step):
 *
 *   Polynomial features:  for a scalar x, φ(x) = [1, x, x², …, x^d]  (degree d).
 *
 *   Ordinary least squares:   w = (ΦᵀΦ)^{-1} Φᵀ y
 *   Ridge (L2) least squares: w = (ΦᵀΦ + λ R)^{-1} Φᵀ y
 *       where R = identity but with R[0][0] = 0 so the bias column (the "1"s)
 *       is NOT penalised.
 *
 *   Bias–variance:  low degree → high bias (underfit); high degree → high
 *   variance (fits noise). CV MSE traces a U as degree grows.
 *
 * A Gaussian-elimination `solve(A, b)` is PROVIDED. You implement three
 * functions with plain arrays only: kfoldIndices, ridgeFit (assemble the
 * regularised system, then call solve), cvScore. Everything else is provided.
 *
 * How to run:
 *   pnpm tsx modules/01b-ml-foundations/ts/02-bias-variance.ts
 */

const SEED = 11;
const N = 60; // samples
const NOISE_STD = 0.6;
const MAX_DEGREE = 12;
const K_FOLDS = 5;

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG + Box-Muller
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function makeGaussian(seed: number): () => number {
  const u = makeRng(seed);
  return () => {
    const u1 = u() + 1e-12;
    const u2 = u();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Linear-algebra helpers (provided)
// ---------------------------------------------------------------------------

function matMul(A: number[][], B: number[][]): number[][] {
  const n = A.length,
    k = A[0].length,
    m = B[0].length;
  const C = Array.from({ length: n }, () => new Array(m).fill(0) as number[]);
  for (let i = 0; i < n; i++)
    for (let p = 0; p < k; p++)
      for (let j = 0; j < m; j++) C[i][j] += A[i][p] * B[p][j];
  return C;
}

function matVec(A: number[][], v: number[]): number[] {
  return A.map((row) => row.reduce((acc, a, j) => acc + a * v[j], 0));
}

function transpose(A: number[][]): number[][] {
  const n = A.length,
    m = A[0].length;
  const T = Array.from({ length: m }, () => new Array(n).fill(0) as number[]);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) T[j][i] = A[i][j];
  return T;
}

/** Solve A x = b (A is K×K) via Gaussian elimination with partial pivoting. */
function solve(A: number[][], b: number[]): number[] {
  const n = A.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col++) {
    let pivot = col;
    for (let r = col + 1; r < n; r++)
      if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    [M[col], M[pivot]] = [M[pivot], M[col]];
    const piv = M[col][col];
    if (Math.abs(piv) < 1e-12) throw new Error("Matrix is singular");
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const factor = M[r][col] / piv;
      for (let c = col; c <= n; c++) M[r][c] -= factor * M[col][c];
    }
  }
  return M.map((row, i) => row[n] / row[i]);
}

// ---------------------------------------------------------------------------
// Synthetic data: a true cubic + noise (provided)
// ---------------------------------------------------------------------------

function trueFunction(x: number): number {
  return 0.5 * x ** 3 - 1.0 * x ** 2 + 0.5 * x + 2.0;
}

function makeData(): { x: number[]; y: number[] } {
  const u = makeRng(SEED);
  const g = makeGaussian(SEED + 99);
  const x = Array.from({ length: N }, () => -3.0 + 6.0 * u()).sort((a, b) => a - b);
  const y = x.map((xi) => trueFunction(xi) + NOISE_STD * g());
  return { x, y };
}

// ---------------------------------------------------------------------------
// Polynomial features + prediction (provided)
// ---------------------------------------------------------------------------

/** Design matrix Φ with columns [1, x, x², …, x^degree]. Shape: (x.length, degree+1). */
function polyFeatures(x: number[], degree: number): number[][] {
  return x.map((xi) => {
    const row = new Array(degree + 1);
    for (let p = 0; p <= degree; p++) row[p] = xi ** p;
    return row;
  });
}

function predict(Phi: number[][], w: number[]): number[] {
  return matVec(Phi, w);
}

function mse(yTrue: number[], yPred: number[]): number {
  let s = 0;
  for (let i = 0; i < yTrue.length; i++) s += (yTrue[i] - yPred[i]) ** 2;
  return s / yTrue.length;
}

function norm(v: number[]): number {
  return Math.sqrt(v.reduce((acc, x) => acc + x * x, 0));
}

// ---------------------------------------------------------------------------
// Seeded permutation of 0..n-1 (provided — deterministic Fisher-Yates)
// ---------------------------------------------------------------------------

function permutation(n: number, seed: number): number[] {
  const rng = makeRng(seed);
  const p = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [p[i], p[j]] = [p[j], p[i]];
  }
  return p;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Split indices 0..n-1 into k folds of (nearly) equal size.
 *
 * Use the provided permutation(n, SEED) to shuffle, then chop into k contiguous
 * chunks. Return an array of k index arrays.
 *
 * TODO: implement.
 *   - Shuffle 0..n-1 with the provided permutation(n, SEED).
 *   - Split that permutation into k near-equal contiguous chunks (fold f spans
 *     roughly indices f·n/k .. (f+1)·n/k) and return the array of folds.
 */
function kfoldIndices(n: number, k: number): number[][] {
  // TODO: implement the k-fold index split
  throw new Error("TODO: implement kfoldIndices()");
}

/**
 * Ridge (L2-regularised) least squares.
 *
 * w = (ΦᵀΦ + λ R)^{-1} Φᵀ y
 *
 * R is the identity EXCEPT R[0][0] = 0, so the bias/intercept column (column 0
 * of Φ) is NOT penalised. lam === 0 recovers ordinary least squares. Assemble
 * the system and call the provided solve() — never invert a matrix.
 *
 * TODO: implement using transpose/matMul/matVec/solve.
 *   - Build the coefficient matrix ΦᵀΦ, then add λ to each diagonal entry
 *     EXCEPT [0][0] (the intercept column is not penalised).
 *   - Assemble the right-hand side Φᵀy, solve the system, and return the weights.
 */
function ridgeFit(Phi: number[][], y: number[], lam: number): number[] {
  // TODO: implement ridge regression via solve()
  throw new Error("TODO: implement ridgeFit()");
}

/**
 * k-fold cross-validated MSE for a given polynomial degree and ridge lambda.
 *
 * For each fold f:
 *   - the validation set is fold f
 *   - the training set is every OTHER fold concatenated
 *   - build polyFeatures on TRAIN x, ridgeFit, score MSE on VAL
 * Return the mean of the k validation MSEs.
 *
 * TODO: implement.
 *   - Get the folds from kfoldIndices(x.length, k).
 *   - For each fold f: it is the validation set; the training indices are every
 *     OTHER fold flattened together.
 *   - Gather the train x/y, ridgeFit on polyFeatures(degree) with lam, then
 *     score mse() on the validation x/y via predict().
 *   - Return the mean of the per-fold validation MSEs.
 */
function cvScore(
  x: number[],
  y: number[],
  degree: number,
  lam: number,
  k = K_FOLDS,
): number {
  // TODO: implement k-fold CV scoring
  throw new Error("TODO: implement cvScore()");
}

// ---------------------------------------------------------------------------
// Harness (provided)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 2 — Bias–variance, cross-validation, and ridge regularisation\n");

  const { x, y } = makeData();
  console.log(
    `  Data: N=${N}   true function: 0.5x³ - x² + 0.5x + 2   noise σ=${NOISE_STD}\n`,
  );

  // ── Degree sweep: train MSE vs CV MSE (plain OLS, lam=0) ────────────────────
  console.log("[1/2] Degree sweep (plain least squares, no regularisation):\n");
  console.log(
    `  ${"degree".padStart(6)} | ${"train MSE".padStart(10)} | ${"CV MSE".padStart(10)} | ${"||w||".padStart(10)}`,
  );
  console.log(
    `  ${"-".repeat(6)}-+-${"-".repeat(10)}-+-${"-".repeat(10)}-+-${"-".repeat(10)}`,
  );

  const trainMses: number[] = [];
  const cvMses: number[] = [];
  const wNorms: number[] = [];
  for (let degree = 1; degree <= MAX_DEGREE; degree++) {
    const Phi = polyFeatures(x, degree);
    const w = ridgeFit(Phi, y, 0.0);
    const tr = mse(y, predict(Phi, w));
    const cv = cvScore(x, y, degree, 0.0);
    const wn = norm(w);
    trainMses.push(tr);
    cvMses.push(cv);
    wNorms.push(wn);
    console.log(
      `  ${String(degree).padStart(6)} | ${tr.toFixed(4).padStart(10)} | ${cv.toFixed(4).padStart(10)} | ${wn.toFixed(2).padStart(10)}`,
    );
  }

  let bestDegree = 1;
  for (let d = 2; d <= MAX_DEGREE; d++)
    if (cvMses[d - 1] < cvMses[bestDegree - 1]) bestDegree = d;
  console.log(`\n  CV-optimal degree: ${bestDegree}  (lowest CV MSE)`);
  console.log("  Notice: train MSE keeps falling, but CV MSE bottoms out then rises —");
  console.log("  that upswing is overfitting (variance) at high degree.\n");

  // ── Ridge at the overfit degree ────────────────────────────────────────────
  const overfitDegree = MAX_DEGREE;
  console.log(`[2/2] Ridge regularisation at the overfit degree (${overfitDegree}):\n`);
  console.log(
    `  ${"lambda".padStart(10)} | ${"CV MSE".padStart(10)} | ${"||w||".padStart(12)}`,
  );
  console.log(`  ${"-".repeat(10)}-+-${"-".repeat(10)}-+-${"-".repeat(12)}`);

  const PhiOf = polyFeatures(x, overfitDegree);
  const lambdas = [0.0, 0.01, 0.1, 1.0, 10.0];
  const ridgeCv: number[] = [];
  const ridgeWn: number[] = [];
  for (const lam of lambdas) {
    const w = ridgeFit(PhiOf, y, lam);
    const cv = cvScore(x, y, overfitDegree, lam);
    const wn = norm(w);
    ridgeCv.push(cv);
    ridgeWn.push(wn);
    console.log(
      `  ${lam.toFixed(2).padStart(10)} | ${cv.toFixed(4).padStart(10)} | ${wn.toFixed(2).padStart(12)}`,
    );
  }

  // ── Acceptance checks ──────────────────────────────────────────────────────
  const cvPlainDeg12 = cvMses[MAX_DEGREE - 1];
  const trainPlainDeg12 = trainMses[MAX_DEGREE - 1];
  const wnPlainDeg12 = wNorms[MAX_DEGREE - 1];

  let bestRidgeI = 1;
  for (let i = 2; i < ridgeCv.length; i++)
    if (ridgeCv[i] < ridgeCv[bestRidgeI]) bestRidgeI = i;
  const bestRidgeCv = ridgeCv[bestRidgeI];
  const bestRidgeWn = ridgeWn[bestRidgeI];
  const bestRidgeLam = lambdas[bestRidgeI];

  console.log("\nAcceptance:");
  const okDegree = bestDegree >= 2 && bestDegree <= 6;
  const okOverfit = trainPlainDeg12 * 3 < cvPlainDeg12;
  const okRidgeWn = bestRidgeWn < wnPlainDeg12;
  const okRidgeCv = bestRidgeCv < cvPlainDeg12;

  console.log(
    `  [${okDegree ? "x" : " "}] CV-optimal degree in [2, 6]  (got ${bestDegree})`,
  );
  console.log(
    `  [${okOverfit ? "x" : " "}] Degree-12 overfits: train MSE << CV MSE  (${trainPlainDeg12.toFixed(4)} vs ${cvPlainDeg12.toFixed(4)})`,
  );
  console.log(
    `  [${okRidgeWn ? "x" : " "}] Ridge (λ=${bestRidgeLam}) shrinks ||w|| at degree 12  (${bestRidgeWn.toFixed(2)} < ${wnPlainDeg12.toFixed(2)})`,
  );
  console.log(
    `  [${okRidgeCv ? "x" : " "}] Ridge (λ=${bestRidgeLam}) lowers CV MSE at degree 12  (${bestRidgeCv.toFixed(4)} < ${cvPlainDeg12.toFixed(4)})`,
  );

  if (okDegree && okOverfit && okRidgeWn && okRidgeCv) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
