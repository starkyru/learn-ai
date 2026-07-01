/**
 * Task 1 🟡 — Linear regression: the normal equation AND gradient descent.
 *
 * What you'll learn:
 *   - The closed-form "normal equation" solution: w = (XᵀX)^{-1} Xᵀy
 *   - How to solve it via a linear-system solve (never form the inverse)
 *   - Gradient descent for MSE: the same answer, found iteratively
 *   - R² (coefficient of determination) as a scale-free goodness-of-fit score
 *
 * The math (README derives each step):
 *
 *   Model:            ŷ = X w         (bias absorbed as a column of 1s in X)
 *   Loss (MSE):       L(w) = (1/N) · ||X w - y||²
 *   Gradient of MSE:  ∇L  = (2/N) · Xᵀ (X w - y)
 *   Setting ∇L = 0 :  XᵀX w = Xᵀ y   →   the "normal equation"
 *
 *   Gradient-descent update:   w ← w - lr · ∇L
 *
 *   R²:   1 - SS_res / SS_tot
 *
 * A Gaussian-elimination `solve(A, b)` is PROVIDED in the harness. You implement
 * the four core functions using plain arrays only (no math libraries):
 * normalEquation (assemble XᵀX and Xᵀy, then call solve), predict, mseLoss,
 * gradientStep. Everything else is provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01b-ml-foundations/ts/01-linear-regression.ts
 */

const SEED = 7;
const N = 200; // samples
const D = 3; // real features (a bias column is prepended → design matrix is N×(D+1))

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG + Box-Muller for reproducible Gaussians
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // Numerical Recipes LCG
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296; // uniform in [0, 1)
  };
}

function makeGaussian(seed: number): () => number {
  const u = makeRng(seed);
  return () => {
    // Box-Muller: two uniforms → one standard normal
    const u1 = u() + 1e-12;
    const u2 = u();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Matrix / vector helpers (provided)
// ---------------------------------------------------------------------------

/** A (N×K) @ B (K×M) → (N×M). */
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

/** A (N×M) @ v (M) → (N). */
function matVec(A: number[][], v: number[]): number[] {
  return A.map((row) => row.reduce((acc, a, j) => acc + a * v[j], 0));
}

/** Transpose A (N×M) → (M×N). */
function transpose(A: number[][]): number[][] {
  const n = A.length,
    m = A[0].length;
  const T = Array.from({ length: m }, () => new Array(n).fill(0) as number[]);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) T[j][i] = A[i][j];
  return T;
}

/**
 * Solve the linear system A x = b for x via Gaussian elimination with partial
 * pivoting. A is (K×K), b is (K). Returns x of length K. (Provided so you don't
 * have to build a solver from scratch — your job is to ASSEMBLE the system.)
 */
function solve(A: number[][], b: number[]): number[] {
  const n = A.length;
  // Build an augmented copy [A | b].
  const M = A.map((row, i) => [...row, b[i]]);
  for (let col = 0; col < n; col++) {
    // Partial pivot: find the row with the largest magnitude in this column.
    let pivot = col;
    for (let r = col + 1; r < n; r++) {
      if (Math.abs(M[r][col]) > Math.abs(M[pivot][col])) pivot = r;
    }
    [M[col], M[pivot]] = [M[pivot], M[col]];
    const piv = M[col][col];
    if (Math.abs(piv) < 1e-12) throw new Error("Matrix is singular");
    // Eliminate this column from every other row.
    for (let r = 0; r < n; r++) {
      if (r === col) continue;
      const factor = M[r][col] / piv;
      for (let c = col; c <= n; c++) M[r][c] -= factor * M[col][c];
    }
  }
  // Back-substitute (matrix is now diagonal).
  return M.map((row, i) => row[n] / row[i]);
}

// ---------------------------------------------------------------------------
// Synthetic data (provided)
// ---------------------------------------------------------------------------

function makeData(): { Xraw: number[][]; y: number[]; wTrue: number[]; bTrue: number } {
  const g = makeGaussian(SEED);
  const Xraw = Array.from({ length: N }, () => Array.from({ length: D }, () => g()));
  const wTrue = [2.0, -3.0, 0.5];
  const bTrue = 4.0;
  const noise = makeGaussian(SEED + 99);
  const y = Xraw.map(
    (row) => row.reduce((acc, x, j) => acc + x * wTrue[j], bTrue) + 0.5 * noise(),
  );
  return { Xraw, y, wTrue, bTrue };
}

/** Zero-mean, unit-variance per column. */
function standardize(X: number[][]): number[][] {
  const cols = X[0].length;
  const mean = new Array(cols).fill(0);
  const std = new Array(cols).fill(0);
  for (const row of X) for (let j = 0; j < cols; j++) mean[j] += row[j] / X.length;
  for (const row of X)
    for (let j = 0; j < cols; j++) std[j] += (row[j] - mean[j]) ** 2 / X.length;
  for (let j = 0; j < cols; j++) std[j] = Math.sqrt(std[j]) || 1;
  return X.map((row) => row.map((v, j) => (v - mean[j]) / std[j]));
}

/** Prepend a column of 1s so w[0] is the intercept. */
function addBiasColumn(X: number[][]): number[][] {
  return X.map((row) => [1, ...row]);
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Closed-form least squares: w = (XᵀX)^{-1} Xᵀ y.
 *
 * Never invert a matrix. Instead assemble the system (XᵀX) w = Xᵀy and call
 * the provided solve(A, b).
 *
 * X already includes the bias column (N×(D+1)); the returned w has length D+1,
 * with w[0] the intercept.
 *
 * TODO: implement.
 *   1. const Xt = transpose(X);         // (D+1)×N
 *   2. const A  = matMul(Xt, X);        // (D+1)×(D+1)  == XᵀX
 *   3. const bb = matVec(Xt, y);        // (D+1)        == Xᵀy
 *   4. return solve(A, bb);
 */
function normalEquation(X: number[][], y: number[]): number[] {
  // TODO: assemble XᵀX and Xᵀy, then call solve()
  throw new Error("TODO: implement normalEquation()");
}

/**
 * Linear prediction: ŷ = X @ w. X includes the bias column.
 *
 * TODO: implement (return matVec(X, w)).
 */
function predict(X: number[][], w: number[]): number[] {
  // TODO: implement the linear prediction
  throw new Error("TODO: implement predict()");
}

/**
 * Mean squared error: L = (1/N) · Σ (ŷ_i - y_i)².
 *
 * TODO: implement.
 *   1. const yhat = predict(X, w);
 *   2. sum the squared residuals (yhat[i] - y[i])²
 *   3. return the sum divided by N
 */
function mseLoss(X: number[][], y: number[], w: number[]): number {
  // TODO: implement mean squared error
  throw new Error("TODO: implement mseLoss()");
}

/**
 * One gradient-descent step for MSE.
 *
 * Gradient:   ∇L = (2/N) · Xᵀ (X w - y)
 * Update:     w_new = w - lr · ∇L
 *
 * Return a NEW weight array (do not mutate the input; the loop reassigns w).
 *
 * TODO: implement.
 *   1. const n = X.length;
 *   2. const resid = predict(X, w).map((p, i) => p - y[i]);   // length N
 *   3. const grad  = matVec(transpose(X), resid).map(g => (2 / n) * g); // length D+1
 *   4. return w.map((wj, j) => wj - lr * grad[j]);
 */
function gradientStep(X: number[][], y: number[], w: number[], lr: number): number[] {
  // TODO: implement one gradient-descent update
  throw new Error("TODO: implement gradientStep()");
}

// ---------------------------------------------------------------------------
// R² (provided — uses your predict())
// ---------------------------------------------------------------------------

function rSquared(X: number[][], y: number[], w: number[]): number {
  const yhat = predict(X, w);
  const yMean = y.reduce((a, b) => a + b, 0) / y.length;
  let ssRes = 0;
  let ssTot = 0;
  for (let i = 0; i < y.length; i++) {
    ssRes += (y[i] - yhat[i]) ** 2;
    ssTot += (y[i] - yMean) ** 2;
  }
  return 1 - ssRes / ssTot;
}

// ---------------------------------------------------------------------------
// Harness (provided)
// ---------------------------------------------------------------------------

function round(v: number[], places = 4): number[] {
  const f = 10 ** places;
  return v.map((x) => Math.round(x * f) / f);
}

function main(): void {
  console.log("Task 1 — Linear regression: normal equation vs gradient descent\n");

  const { Xraw, y, wTrue, bTrue } = makeData();
  console.log(`  Data: N=${N}, D=${D}`);
  console.log(`  True weights: [${wTrue}]   True bias: ${bTrue}`);

  const X = addBiasColumn(standardize(Xraw));
  console.log(`  Design matrix (with bias col): ${X.length}×${X[0].length}\n`);

  // ── Closed form ────────────────────────────────────────────────────────────
  console.log("[1/2] Normal equation (closed form)...");
  const wNormal = normalEquation(X, y);
  console.log(`  wNormal = [${round(wNormal)}]`);
  console.log(`  MSE     = ${mseLoss(X, y, wNormal).toFixed(4)}`);
  console.log(`  R²      = ${rSquared(X, y, wNormal).toFixed(4)}\n`);

  // ── Gradient descent ───────────────────────────────────────────────────────
  console.log("[2/2] Gradient descent...");
  const gInit = makeGaussian(SEED);
  let wGd = Array.from({ length: X[0].length }, () => 0.1 * gInit());
  const lr = 0.1;
  const epochs = 300;

  const lossHistory: number[] = [];
  for (let epoch = 0; epoch < epochs; epoch++) {
    lossHistory.push(mseLoss(X, y, wGd));
    wGd = gradientStep(X, y, wGd, lr);
  }

  const finalLoss = mseLoss(X, y, wGd);

  // Monotone over first 30 epochs?
  const first30 = lossHistory.slice(0, 30);
  let monotonic = true;
  for (let i = 0; i < first30.length - 1; i++) {
    if (first30[i + 1] > first30[i] + 1e-9) monotonic = false;
  }

  // Distance to the closed-form optimum.
  let dist = 0;
  for (let j = 0; j < wGd.length; j++) dist += (wGd[j] - wNormal[j]) ** 2;
  dist = Math.sqrt(dist);
  const r2Gd = rSquared(X, y, wGd);

  for (const e of [1, 10, 50, 150, epochs]) {
    console.log(
      `  epoch ${String(e).padStart(4)}: MSE=${lossHistory[e - 1].toFixed(4)}`,
    );
  }
  console.log(`\n  wGd      = [${round(wGd)}]`);
  console.log(`  final MSE (GD)          = ${finalLoss.toFixed(4)}`);
  console.log(`  ||wGd - wNormal||       = ${dist.toFixed(4)}`);
  console.log(`  R² (GD)                 = ${r2Gd.toFixed(4)}`);
  console.log(`  loss monotone (first 30)= ${monotonic}`);

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okConverge = dist < 0.1;
  const okMonotone = monotonic;
  const okR2 = r2Gd > 0.9;
  console.log(
    `  [${okConverge ? "x" : " "}] GD converges to normal eq  (||Δw|| = ${dist.toFixed(4)} < 0.1)`,
  );
  console.log(
    `  [${okMonotone ? "x" : " "}] MSE decreases monotonically over first 30 epochs`,
  );
  console.log(`  [${okR2 ? "x" : " "}] R² > 0.9  (R² = ${r2Gd.toFixed(4)})`);

  if (okConverge && okMonotone && okR2) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
