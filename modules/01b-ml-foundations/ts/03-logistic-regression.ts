/**
 * Task 3 🟡 — Binary logistic regression with gradient descent + L2 regularisation.
 *
 * What you'll learn:
 *   - The sigmoid: squashing a real-valued score into a probability in (0, 1)
 *   - Binary cross-entropy (log loss): the right loss for probabilistic classifiers
 *   - The logistic-regression gradient (structurally identical to linear regression)
 *   - L2 regularisation on the weights (but never on the bias)
 *
 * The math (README derives each step):
 *
 *   Score / logit:   z = X w      (X has a bias column, so w[0] is the intercept)
 *   Sigmoid:         σ(z) = 1 / (1 + e^{-z})       → probability of class 1
 *   Prediction:      ŷ = 1 if σ(z) ≥ 0.5 else 0
 *
 *   Binary cross-entropy (averaged over the batch):
 *      L = -1/N · Σ [ y·log(p) + (1-y)·log(1-p) ]      where p = σ(Xw)
 *   (clip p to [ε, 1-ε] so log never sees 0)
 *
 *   Gradient:  ∇L = Xᵀ (σ(Xw) - y) / N        (+ L2 term)
 *   L2 adds (λ/N)·w to the gradient — but with the bias entry zeroed out.
 *
 * You implement sigmoid, bceLoss, the gradient/step, and predictProba/predict,
 * using plain arrays only. Everything else — data, split, training loop, the
 * ||w|| comparison across λ — is provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01b-ml-foundations/ts/03-logistic-regression.ts
 */

const SEED = 3;
const N_PER_CLASS = 150;

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
// Synthetic data: two 2-D Gaussians (provided)
// ---------------------------------------------------------------------------

/** Two well-separated blobs → linearly separable binary problem. */
function makeData(): { X: number[][]; y: number[] } {
  const g = makeGaussian(SEED);
  const rows: number[][] = [];
  const y: number[] = [];
  for (let i = 0; i < N_PER_CLASS; i++) {
    rows.push([-2.0 + g(), -2.0 + g()]);
    y.push(0);
  }
  for (let i = 0; i < N_PER_CLASS; i++) {
    rows.push([2.0 + g(), 2.0 + g()]);
    y.push(1);
  }
  return { X: rows, y };
}

/** Prepend a column of 1s so w[0] is the intercept. */
function addBiasColumn(X: number[][]): number[][] {
  return X.map((row) => [1, ...row]);
}

/** Seeded permutation for the split. */
function permutation(n: number, seed: number): number[] {
  const rng = makeRng(seed);
  const p = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [p[i], p[j]] = [p[j], p[i]];
  }
  return p;
}

/** Stratified 80/20 train/test split. */
function stratifiedSplit(
  X: number[][],
  y: number[],
  testFraction = 0.2,
): { XTrain: number[][]; XTest: number[][]; yTrain: number[]; yTest: number[] } {
  const groups: Record<number, number[]> = {};
  for (let i = 0; i < y.length; i++) (groups[y[i]] ??= []).push(i);
  const trainIdx: number[] = [];
  const testIdx: number[] = [];
  for (const key of Object.keys(groups)) {
    const idx = groups[Number(key)];
    // shuffle within class deterministically
    const perm = permutation(idx.length, SEED + Number(key));
    const shuffled = perm.map((p) => idx[p]);
    const nTest = Math.max(1, Math.floor(shuffled.length * testFraction));
    testIdx.push(...shuffled.slice(0, nTest));
    trainIdx.push(...shuffled.slice(nTest));
  }
  return {
    XTrain: trainIdx.map((i) => X[i]),
    XTest: testIdx.map((i) => X[i]),
    yTrain: trainIdx.map((i) => y[i]),
    yTest: testIdx.map((i) => y[i]),
  };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Logistic sigmoid applied element-wise to a vector: σ(z) = 1 / (1 + e^{-z}).
 *
 * Clamp z to [-500, 500] before exp to avoid Infinity for very negative z.
 *
 * TODO: implement.
 *   return z.map(v => {
 *     const c = Math.max(-500, Math.min(500, v));
 *     return 1 / (1 + Math.exp(-c));
 *   });
 */
function sigmoid(z: number[]): number[] {
  // TODO: implement the sigmoid
  throw new Error("TODO: implement sigmoid()");
}

/**
 * Mean binary cross-entropy (log loss).
 *
 * L = -1/N · Σ [ y·log(p) + (1-y)·log(1-p) ]
 *
 * Clip each p to [1e-12, 1 - 1e-12] so log never sees 0 or 1.
 *
 * TODO: implement.
 *   1. accumulate, for each i:
 *        const pi = Math.max(1e-12, Math.min(1 - 1e-12, p[i]));
 *        sum += y[i] * Math.log(pi) + (1 - y[i]) * Math.log(1 - pi);
 *   2. return -sum / p.length;
 */
function bceLoss(p: number[], y: number[]): number {
  // TODO: implement binary cross-entropy
  throw new Error("TODO: implement bceLoss()");
}

class LogisticRegression {
  w: number[]; // length = nFeatures (includes bias at index 0)

  constructor(
    nFeatures: number,
    private lr = 0.1,
    private lam = 0.0,
  ) {
    this.w = new Array(nFeatures).fill(0);
  }

  private score(X: number[][]): number[] {
    // linear score z = X @ w
    return X.map((row) => row.reduce((acc, xj, j) => acc + xj * this.w[j], 0));
  }

  /**
   * Return P(class = 1 | x) = σ(X w) for each row of X.
   *
   * TODO: implement (apply sigmoid to the linear score of each row).
   *   return sigmoid(this.score(X));   // this.score(X) is provided above
   */
  predictProba(X: number[][]): number[] {
    // TODO: implement predictProba
    throw new Error("TODO: implement predictProba()");
  }

  /** 0/1 predictions by thresholding predictProba at `threshold`. */
  predict(X: number[][], threshold = 0.5): number[] {
    return this.predictProba(X).map((p) => (p >= threshold ? 1 : 0));
  }

  loss(X: number[][], y: number[]): number {
    return bceLoss(this.predictProba(X), y);
  }

  /**
   * One full-batch gradient-descent update. Returns the (pre-update) BCE loss.
   *
   * Forward:  p = σ(X w)
   * Gradient: grad[j] = (1/N) Σ_i X[i][j] · (p[i] - y[i])   (+ L2 term)
   * L2:       add (lam/N)·w[j] to grad[j] for j ≥ 1 (skip the bias, j=0).
   * Update:   w[j] -= lr · grad[j]
   *
   * TODO: implement.
   *   1. const N = X.length;
   *   2. const p = this.predictProba(X);
   *   3. const loss = bceLoss(p, y);
   *   4. const err = p.map((pi, i) => pi - y[i]);           // length N
   *   5. const D = this.w.length;
   *      const grad = new Array(D).fill(0);
   *      for (let j = 0; j < D; j++) {
   *        let g = 0;
   *        for (let i = 0; i < N; i++) g += X[i][j] * err[i];
   *        g /= N;
   *        if (j >= 1) g += (this.lam / N) * this.w[j];      // L2, not on bias
   *        grad[j] = g;
   *      }
   *   6. for (let j = 0; j < D; j++) this.w[j] -= this.lr * grad[j];
   *   7. return loss;
   */
  gradientStep(X: number[][], y: number[]): number {
    // TODO: implement the gradient step
    throw new Error("TODO: implement gradientStep()");
  }

  accuracy(X: number[][], y: number[]): number {
    const preds = this.predict(X);
    return preds.filter((pi, i) => pi === y[i]).length / y.length;
  }
}

// ---------------------------------------------------------------------------
// Training loop (provided). Pass printEvery=0 to train silently.
// ---------------------------------------------------------------------------

function train(
  model: LogisticRegression,
  X: number[][],
  y: number[],
  epochs = 200,
  printEvery = 40,
): number[] {
  const history: number[] = [];
  for (let epoch = 0; epoch < epochs; epoch++) {
    const loss = model.gradientStep(X, y);
    history.push(loss);
    if (printEvery && ((epoch + 1) % printEvery === 0 || epoch === 0)) {
      console.log(
        `  epoch ${String(epoch + 1).padStart(4)}/${epochs}  loss=${loss.toFixed(4)}`,
      );
    }
  }
  return history;
}

function normTail(w: number[]): number {
  // ||w|| excluding the bias (index 0) — the part L2 controls
  let s = 0;
  for (let j = 1; j < w.length; j++) s += w[j] * w[j];
  return Math.sqrt(s);
}

// ---------------------------------------------------------------------------
// Harness (provided)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 3 — Binary logistic regression with gradient descent + L2\n");

  const { X: Xraw, y } = makeData();
  const X = addBiasColumn(Xraw);
  const { XTrain, XTest, yTrain, yTest } = stratifiedSplit(X, y);
  console.log(
    `  Data: ${X.length} samples, 2 classes.  Train ${yTrain.length}  Test ${yTest.length}\n`,
  );

  // ── Train a plain model (no regularisation) ────────────────────────────────
  console.log("[1/2] Training (λ=0)...");
  const model = new LogisticRegression(X[0].length, 0.5, 0.0);
  console.log(`  Initial train loss: ${model.loss(XTrain, yTrain).toFixed(4)}`);
  const history = train(model, XTrain, yTrain, 200, 40);

  const trainAcc = model.accuracy(XTrain, yTrain);
  const testAcc = model.accuracy(XTest, yTest);
  console.log(`\n  Train accuracy: ${(trainAcc * 100).toFixed(2)}%`);
  console.log(`  Test accuracy:  ${(testAcc * 100).toFixed(2)}%`);

  const first30 = history.slice(0, 30);
  let monotonic = true;
  for (let i = 0; i < first30.length - 1; i++)
    if (first30[i + 1] > first30[i] + 1e-9) monotonic = false;
  console.log(`  Loss monotone over first 30 epochs: ${monotonic}\n`);

  // ── L2 sweep: larger λ → smaller ||w|| ─────────────────────────────────────
  console.log("[2/2] L2 regularisation sweep (larger λ should shrink ||w||):\n");
  console.log(
    `  ${"lambda".padStart(8)} | ${"train acc".padStart(9)} | ${"||w[1:]||".padStart(10)}`,
  );
  console.log(`  ${"-".repeat(8)}-+-${"-".repeat(9)}-+-${"-".repeat(10)}`);

  const lambdas = [0.0, 1.0, 10.0, 50.0];
  const weightNorms: number[] = [];
  for (const lam of lambdas) {
    const m = new LogisticRegression(X[0].length, 0.5, lam);
    train(m, XTrain, yTrain, 200, 0); // silent
    const wn = normTail(m.w);
    weightNorms.push(wn);
    console.log(
      `  ${lam.toFixed(1).padStart(8)} | ${(m.accuracy(XTrain, yTrain) * 100).toFixed(2).padStart(8)}% | ${wn.toFixed(4).padStart(10)}`,
    );
  }

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okAcc = trainAcc >= 0.95;
  const okMonotone = monotonic;
  let okL2 = true;
  for (let i = 0; i < weightNorms.length - 1; i++)
    if (weightNorms[i + 1] >= weightNorms[i]) okL2 = false;

  console.log(
    `  [${okAcc ? "x" : " "}] Train accuracy ≥ 0.95  (got ${(trainAcc * 100).toFixed(2)}%)`,
  );
  console.log(
    `  [${okMonotone ? "x" : " "}] BCE loss decreases monotonically over first 30 epochs`,
  );
  console.log(
    `  [${okL2 ? "x" : " "}] Larger λ yields smaller ||w||  (norms: [${weightNorms.map((w) => w.toFixed(3)).join(", ")}])`,
  );

  if (okAcc && okMonotone && okL2) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
