/**
 * Task 4 🔴 — Multinomial logistic regression FROM SCRATCH (plain arrays, no ML lib).
 *
 * What you'll learn:
 *   - The softmax function: turning raw scores into a probability distribution
 *   - Cross-entropy loss: the standard loss for classification
 *   - Gradient descent: how the weight matrix updates to minimise loss
 *   - Why the gradient of softmax + cross-entropy is elegantly simple
 *
 * The math (README explains each step in plain English):
 *
 *   Forward pass:
 *     z = X @ W + b           (linear layer: batch of scores, shape [N, C])
 *     p = softmax(z)          (probabilities, each row sums to 1)
 *     L = crossEntropy(p, y)  (scalar loss)
 *
 *   Backward pass:
 *     dL/dz = p - oneHot(y)   (elegant: error is predicted probs minus true probs)
 *     dL/dW = Xᵀ @ dL/dz / N
 *     dL/db = mean(dL/dz, axis=0)
 *
 *   Update:
 *     W -= lr * dL/dW
 *     b -= lr * dL/db
 *
 * No external math library. Plain number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/08-classification/ts/04-logistic-scratch.ts
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { getProvider } from "@learn-ai/llm-core";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const LABEL_NAMES = ["technology", "science", "business", "sports", "health", "politics"];
const NUM_CLASSES = LABEL_NAMES.length;

// ---------------------------------------------------------------------------
// Dataset loading
// ---------------------------------------------------------------------------

interface DataItem {
  id: number;
  text: string;
  label: string;
}

function loadDataset(): DataItem[] {
  const path = join(__dirname, "../data/texts.json");
  return JSON.parse(readFileSync(path, "utf-8")) as DataItem[];
}

// ---------------------------------------------------------------------------
// Matrix helpers (plain 2-D arrays: number[][])
// ---------------------------------------------------------------------------

/** Create an N×M matrix filled with zeros. */
function zeros(rows: number, cols: number): number[][] {
  return Array.from({ length: rows }, () => new Array(cols).fill(0) as number[]);
}

/** Matrix multiply: A (N×K) @ B (K×M) → C (N×M). */
function matMul(A: number[][], B: number[][]): number[][] {
  const N = A.length, K = A[0].length, M = B[0].length;
  const C = zeros(N, M);
  for (let i = 0; i < N; i++)
    for (let k = 0; k < K; k++)
      for (let j = 0; j < M; j++)
        C[i][j] += A[i][k] * B[k][j];
  return C;
}

/** Transpose: A (N×M) → Aᵀ (M×N). */
function transpose(A: number[][]): number[][] {
  const N = A.length, M = A[0].length;
  const T = zeros(M, N);
  for (let i = 0; i < N; i++)
    for (let j = 0; j < M; j++)
      T[j][i] = A[i][j];
  return T;
}

/** Add bias vector b (length C) to each row of matrix Z (N×C). */
function addBias(Z: number[][], b: number[]): number[][] {
  return Z.map((row) => row.map((v, j) => v + b[j]));
}

// ---------------------------------------------------------------------------
// Softmax and cross-entropy — implement these
// ---------------------------------------------------------------------------

/**
 * Softmax over each row of a 2-D array.
 *
 * softmax(z)_j = exp(z_j) / sum_k(exp(z_k))
 *
 * Numerically stable: subtract the row-max before exp().
 *
 * TODO: implement row-wise. For each row of Z:
 *   - Find the row's max (`Math.max(...row)`) and subtract it from every entry
 *     before exponentiating — that keeps `Math.exp` from overflowing.
 *   - Exponentiate the shifted values, then divide each by the row's total so the
 *     row sums to 1. Return a new matrix of the same shape.
 */
function softmax(Z: number[][]): number[][] {
  // TODO: implement row-wise numerically stable softmax
  throw new Error("TODO: implement softmax()");
}

/**
 * Mean cross-entropy loss over a batch.
 *
 * L = -1/N * sum_i( log( probs[i][y[i]] ) )
 *
 * probs[i][y[i]] is the predicted probability for the TRUE class of sample i.
 * Clip to 1e-12 to avoid log(0).
 *
 * TODO: implement.
 */
function crossEntropyLoss(probs: number[][], y: number[]): number {
  // TODO: implement
  throw new Error("TODO: implement crossEntropyLoss()");
}

// ---------------------------------------------------------------------------
// Logistic regression model
// ---------------------------------------------------------------------------

class LogisticRegressionScratch {
  W: number[][];  // shape: D × C
  b: number[];    // shape: C

  constructor(
    private nFeatures: number,
    private nClasses: number,
    private lr: number = 0.1,
  ) {
    // Xavier initialisation
    const scale = Math.sqrt(2.0 / (nFeatures + nClasses));
    // Seeded pseudo-random with a simple LCG for reproducibility
    let seed = 42;
    const rand = () => {
      seed = (seed * 1664525 + 1013904223) & 0x7fffffff;
      // Box-Muller transform for Gaussian
      const u1 = (seed & 0xffff) / 0x10000 + 1e-10;
      seed = (seed * 1664525 + 1013904223) & 0x7fffffff;
      const u2 = (seed & 0xffff) / 0x10000;
      return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * scale;
    };

    this.W = Array.from({ length: nFeatures }, () =>
      Array.from({ length: nClasses }, () => rand()),
    );
    this.b = new Array(nClasses).fill(0) as number[];
  }

  /** Forward pass: compute softmax probabilities. Shape: (N, C). */
  forward(X: number[][]): number[][] {
    /**
     * TODO: compute the linear scores then squash them.
     *   - Multiply X by this.W with `matMul`, add the bias with `addBias`, and pass
     *     the resulting (N, C) score matrix through `softmax`. Return the probs.
     */
    throw new Error("TODO: implement forward()");
  }

  /** Compute cross-entropy loss on a batch. */
  loss(X: number[][], y: number[]): number {
    return crossEntropyLoss(this.forward(X), y);
  }

  /**
   * Compute gradients and update W and b.
   *
   * Forward:
   *   probs = forward(X)                      shape: (N, C)
   *   loss  = crossEntropy(probs, y)          scalar
   *
   * Backward:
   *   dZ    = probs - oneHot(y)               shape: (N, C)
   *   dW    = Xᵀ @ dZ / N                    shape: (D, C)
   *   db    = mean(dZ, axis=0)               shape: (C,)
   *
   * Update:
   *   W[d][c] -= lr * dW[d][c]   for all d, c
   *   b[c]    -= lr * db[c]      for all c
   *
   * Return the loss (for logging).
   *
   * TODO: implement this method — translate the math above into array ops.
   *   - Forward pass (this.forward) to get probs, and compute the loss with
   *     crossEntropyLoss so you can return it at the end.
   *   - Build dZ from the dL/dz formula: start from probs and, for each sample i,
   *     subtract 1 in the true-class column y[i] (that's probs - oneHot(y)).
   *   - Turn dZ into dW and db using the formulas above — dW uses `matMul` on the
   *     transpose of X and is scaled by 1/N; db is the per-column mean of dZ.
   *   - Subtract lr * gradient from this.W (element-wise) and this.b, then return
   *     the loss.
   */
  gradientStep(X: number[][], y: number[]): number {
    // TODO: implement gradient step
    throw new Error("TODO: implement gradientStep()");
  }

  /** Return predicted class index for each row of X. */
  predict(X: number[][]): number[] {
    const probs = this.forward(X);
    return probs.map((row) => row.indexOf(Math.max(...row)));
  }

  /** Fraction of correct predictions. */
  accuracy(X: number[][], y: number[]): number {
    const preds = this.predict(X);
    return preds.filter((p, i) => p === y[i]).length / y.length;
  }
}

// ---------------------------------------------------------------------------
// Stratified train/test split
// ---------------------------------------------------------------------------

function trainTestSplit(
  X: number[][],
  y: number[],
  testFraction = 0.2,
): { XTrain: number[][]; XTest: number[][]; yTrain: number[]; yTest: number[] } {
  const groups: Record<number, number[]> = {};
  for (let i = 0; i < y.length; i++) {
    (groups[y[i]] ??= []).push(i);
  }
  const trainIdx: number[] = [], testIdx: number[] = [];
  for (const indices of Object.values(groups)) {
    const nTest = Math.max(1, Math.round(indices.length * testFraction));
    testIdx.push(...indices.slice(0, nTest));
    trainIdx.push(...indices.slice(nTest));
  }
  return {
    XTrain: trainIdx.map((i) => X[i]),
    XTest: testIdx.map((i) => X[i]),
    yTrain: trainIdx.map((i) => y[i]),
    yTest: testIdx.map((i) => y[i]),
  };
}

// ---------------------------------------------------------------------------
// Training loop (complete — you don't need to edit this)
// ---------------------------------------------------------------------------

function train(
  model: LogisticRegressionScratch,
  XTrain: number[][],
  yTrain: number[],
  epochs = 200,
  batchSize = 16,
  printEvery = 50,
): number[] {
  const N = yTrain.length;
  const lossHistory: number[] = [];

  for (let epoch = 0; epoch < epochs; epoch++) {
    // Shuffle (deterministic using epoch as seed offset)
    const perm = Array.from({ length: N }, (_, i) => i);
    // Simple Fisher-Yates with seeded rand
    let s = 42 + epoch;
    const lcg = () => { s = (s * 1664525 + 1013904223) & 0x7fffffff; return s / 0x7fffffff; };
    for (let i = N - 1; i > 0; i--) {
      const j = Math.floor(lcg() * (i + 1));
      [perm[i], perm[j]] = [perm[j], perm[i]];
    }

    const Xs = perm.map((i) => XTrain[i]);
    const ys = perm.map((i) => yTrain[i]);

    const batchLosses: number[] = [];
    for (let start = 0; start < N; start += batchSize) {
      const Xb = Xs.slice(start, start + batchSize);
      const yb = ys.slice(start, start + batchSize);
      const loss = model.gradientStep(Xb, yb);
      batchLosses.push(loss);
    }

    const meanLoss = batchLosses.reduce((a, b) => a + b, 0) / batchLosses.length;
    lossHistory.push(meanLoss);

    if ((epoch + 1) % printEvery === 0 || epoch === 0) {
      console.log(`  Epoch ${String(epoch + 1).padStart(4)}/${epochs}  loss=${meanLoss.toFixed(4)}`);
    }
  }

  return lossHistory;
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (embed model: ${provider.embedModel})`);

  // ── Load & embed ──────────────────────────────────────────────────────────
  console.log("\n[1/4] Loading and embedding dataset...");
  const dataset = loadDataset();
  const texts = dataset.map((d) => d.text);
  const labelToIdx = Object.fromEntries(LABEL_NAMES.map((l, i) => [l, i]));
  const y = dataset.map((d) => labelToIdx[d.label]);

  const result = await provider.embed(texts);
  const X = result.vectors;
  console.log(`  X: ${X.length} × ${X[0].length}   y: ${y.length} labels`);

  // ── Train/test split ──────────────────────────────────────────────────────
  console.log("\n[2/4] Stratified 80/20 split...");
  const { XTrain, XTest, yTrain, yTest } = trainTestSplit(X, y);
  console.log(`  Train: ${yTrain.length}  Test: ${yTest.length}`);

  // ── Build model ───────────────────────────────────────────────────────────
  const D = X[0].length;
  console.log(`\n[3/4] Building LogisticRegressionScratch(D=${D}, C=${NUM_CLASSES})...`);
  const model = new LogisticRegressionScratch(D, NUM_CLASSES, 0.5);

  // ── Train ─────────────────────────────────────────────────────────────────
  console.log("\n[4/4] Training with mini-batch gradient descent...");
  console.log(`  Initial train loss: ${model.loss(XTrain, yTrain).toFixed(4)}`);
  console.log(`  Initial train acc:  ${(model.accuracy(XTrain, yTrain) * 100).toFixed(1)}%\n`);

  train(model, XTrain, yTrain, 300, 16, 50);

  // ── Evaluate ──────────────────────────────────────────────────────────────
  const trainAcc = model.accuracy(XTrain, yTrain);
  const testAcc = model.accuracy(XTest, yTest);

  console.log(`\n  Train accuracy : ${(trainAcc * 100).toFixed(1)}%`);
  console.log(`  Test accuracy  : ${(testAcc * 100).toFixed(1)}%`);

  console.log("\n  Per-class test accuracy:");
  const preds = model.predict(XTest);
  for (let c = 0; c < NUM_CLASSES; c++) {
    const idx = yTest.map((v, i) => (v === c ? i : -1)).filter((i) => i >= 0);
    if (idx.length === 0) continue;
    const correct = idx.filter((i) => preds[i] === c).length;
    console.log(`    ${LABEL_NAMES[c].padEnd(12)}: ${(correct / idx.length * 100).toFixed(0)}% (n=${idx.length})`);
  }

  console.log(
    "\n  Reflection: the gradient dZ = probs - oneHot(y) is the beautiful",
    "\n  result of differentiating softmax + cross-entropy jointly.",
    "\n  The model has no hidden layers — it finds a linear decision surface",
    "\n  in the embedding space.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
