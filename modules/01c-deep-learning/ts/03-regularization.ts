/**
 * Task 3 🟡 — REGULARISATION: inverted dropout, batchnorm, L2 weight decay (plain TS).
 *
 * What you'll learn:
 *   - Why a high-capacity net overfits (train acc ≫ test acc) on small noisy data.
 *   - Inverted dropout: randomly drop neurons at train time, scale to keep the mean,
 *     do nothing at test time.
 *   - Batch normalisation: normalise each feature to mean 0 / var 1, then rescale.
 *   - L2 weight decay: add (λ/2)·ΣW² to the loss → an extra λ·W term in each gradient.
 *
 * The math (README §3 explains each step in plain English):
 *
 *   Inverted dropout (train):  mask ~ Bernoulli(1-p);  out = (x * mask) / (1 - p)
 *   Inverted dropout (test):   out = x                       (identity)
 *
 *   Batchnorm forward:
 *     μ  = mean(x over batch)          σ² = var(x over batch)     (per feature)
 *     x̂  = (x - μ) / sqrt(σ² + ε)
 *     out = γ · x̂ + β                  (with γ=1, β=0 → mean 0, var 1)
 *
 *   L2:  L_total = L_data + (λ/2)·ΣW²  →  ∂/∂W = λ·W  (added to the data gradient)
 *
 * The dataset, the 2-layer MLP, backprop, and the training loop are provided. You
 * implement dropoutForward, batchnormForward, and l2Grad.
 *
 * How to run:
 *   pnpm tsx modules/01c-deep-learning/ts/03-regularization.ts
 *
 * No math library — plain number[] / number[][] arrays.
 */

// ---------------------------------------------------------------------------
// The three regularisers — implement these
// ---------------------------------------------------------------------------

/**
 * Inverted dropout on a matrix (N×D).
 *
 * Training: for each element draw keep ~ Bernoulli(1-p); zero the dropped units
 * and divide the survivors by (1-p) so the expected sum is unchanged. That scaling
 * is why test time is a plain identity.
 * Test: return x unchanged.
 *
 * TODO: implement.
 *   - If not training, return `x` unchanged.
 *   - Otherwise let keep = 1 - p. Map over every element: with probability `keep`
 *     (draw `rng()` and compare) keep it but divide by `keep`; otherwise zero it.
 *   - Return a NEW matrix (use `.map`), don't mutate the input.
 */
function dropoutForward(
  x: number[][],
  p: number,
  training: boolean,
  rng: () => number,
): number[][] {
  throw new Error("TODO: implement dropoutForward()");
}

/**
 * Batch normalisation forward pass (per-feature, over the batch axis = rows).
 *
 *   μ_j   = mean over rows of column j
 *   var_j = variance over rows of column j          (population variance, /N)
 *   x̂     = (x - μ) / sqrt(var + eps)
 *   out   = gamma * x̂ + beta
 *
 * With gamma=1, beta=0 the OUTPUT has per-feature mean ≈ 0 and var ≈ 1.
 *
 * TODO: implement the four steps in the formula above.
 *   - For each COLUMN j (a feature), compute the mean over the N rows and the
 *     population variance (divide the summed squared deviations by N, not N-1).
 *   - Return a new matrix: for each entry, normalise with that column's mean and
 *     sqrt(var + eps), then apply the per-feature `gamma[j]` scale and `beta[j]` shift.
 */
function batchnormForward(
  x: number[][],
  gamma: number[],
  beta: number[],
  eps = 1e-5,
): number[][] {
  throw new Error("TODO: implement batchnormForward()");
}

/**
 * Gradient contribution of the L2 penalty (λ/2)·ΣW²  →  λ·W (element-wise).
 * Returned matrix is ADDED onto the data gradient of the same weight matrix.
 *
 * TODO: return a new matrix the same shape as W holding the elementwise derivative
 *       of the (λ/2)·ΣW² penalty w.r.t. each weight.
 */
function l2Grad(W: number[][], lam: number): number[][] {
  throw new Error("TODO: implement l2Grad()");
}

// ---------------------------------------------------------------------------
// Seeded RNG + Gaussian (deterministic)
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gaussianFactory(rng: () => number): (mean: number, std: number) => number {
  return (mean, std) => {
    const u1 = Math.max(rng(), 1e-12);
    const u2 = rng();
    return mean + std * Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Matrix helpers (number[][]) — complete
// ---------------------------------------------------------------------------

function matMul(A: number[][], B: number[][]): number[][] {
  const N = A.length,
    K = A[0].length,
    M = B[0].length;
  const C = Array.from({ length: N }, () => new Array(M).fill(0) as number[]);
  for (let i = 0; i < N; i++)
    for (let k = 0; k < K; k++) {
      const aik = A[i][k];
      for (let j = 0; j < M; j++) C[i][j] += aik * B[k][j];
    }
  return C;
}
function transpose(A: number[][]): number[][] {
  const N = A.length,
    M = A[0].length;
  const T = Array.from({ length: M }, () => new Array(N).fill(0) as number[]);
  for (let i = 0; i < N; i++) for (let j = 0; j < M; j++) T[j][i] = A[i][j];
  return T;
}
function addRowVec(Z: number[][], b: number[]): number[][] {
  return Z.map((row) => row.map((v, j) => v + b[j]));
}
function sigmoidScalar(z: number): number {
  return 1 / (1 + Math.exp(-z));
}

// ---------------------------------------------------------------------------
// Small NOISY dataset that a big net will overfit (complete)
// ---------------------------------------------------------------------------

function makeNoisyDataset(
  n = 90,
  dim = 60,
  nInformative = 3,
  seed = 0,
): { X: number[][]; y: number[] } {
  const rng = makeRng(seed);
  const gauss = gaussianFactory(rng);
  const X: number[][] = Array.from({ length: n }, () =>
    Array.from({ length: dim }, () => gauss(0, 1)),
  );
  const wTrue = new Array(dim).fill(0) as number[];
  // Only the first nInformative dims carry signal; the rest are pure noise.
  for (let j = 0; j < nInformative; j++) wTrue[j] = gauss(0, 1.5);
  const y = X.map((row) =>
    row.reduce((acc, v, j) => acc + v * wTrue[j], 0) > 0 ? 1 : 0,
  );
  return { X, y };
}

function split(
  X: number[][],
  y: number[],
  testN = 30,
): { XTrain: number[][]; XTest: number[][]; yTrain: number[]; yTest: number[] } {
  const cut = X.length - testN;
  return {
    XTrain: X.slice(0, cut),
    XTest: X.slice(cut),
    yTrain: y.slice(0, cut),
    yTest: y.slice(cut),
  };
}

// ---------------------------------------------------------------------------
// 2-layer MLP with dropout + batchnorm + L2 (complete — uses your functions)
// ---------------------------------------------------------------------------

class RegularizedMLP {
  W1: number[][];
  b1: number[];
  W2: number[][];
  b2: number[];
  gamma: number[];
  beta: number[];
  private useBnEval = false;

  constructor(
    nIn: number,
    private nHidden: number,
    seed = 0,
  ) {
    const rng = makeRng(seed);
    const gauss = gaussianFactory(rng);
    const s1 = Math.sqrt(2.0 / nIn);
    const s2 = Math.sqrt(2.0 / nHidden);
    this.W1 = Array.from({ length: nIn }, () =>
      Array.from({ length: nHidden }, () => gauss(0, s1)),
    );
    this.b1 = new Array(nHidden).fill(0);
    this.W2 = Array.from({ length: nHidden }, () => [gauss(0, s2)]);
    this.b2 = [0];
    this.gamma = new Array(nHidden).fill(1);
    this.beta = new Array(nHidden).fill(0);
  }

  forward(
    X: number[][],
    training: boolean,
    dropoutP: number,
    useBn: boolean,
    rng: () => number,
  ): { X: number[][]; bn: number[][]; a1Drop: number[][]; p: number[][] } {
    const z1 = addRowVec(matMul(X, this.W1), this.b1);
    const bn = useBn ? batchnormForward(z1, this.gamma, this.beta) : z1;
    const a1 = bn.map((row) => row.map((v) => Math.max(0, v)));
    const a1Drop = dropoutP > 0 ? dropoutForward(a1, dropoutP, training, rng) : a1;
    const z2 = addRowVec(matMul(a1Drop, this.W2), this.b2);
    const p = z2.map((row) => [sigmoidScalar(row[0])]);
    return { X, bn, a1Drop, p };
  }

  trainStep(
    X: number[][],
    y: number[],
    lr: number,
    dropoutP: number,
    useBn: boolean,
    lam: number,
    rng: () => number,
  ): void {
    const { bn, a1Drop, p } = this.forward(X, true, dropoutP, useBn, rng);
    const N = X.length;
    const dz2 = p.map((row, i) => [(row[0] - y[i]) / N]);
    const dW2data = matMul(transpose(a1Drop), dz2);
    const dW2reg = l2Grad(this.W2, lam);
    const dW2 = dW2data.map((row, i) => row.map((v, j) => v + dW2reg[i][j]));
    const db2 = [dz2.reduce((acc, r) => acc + r[0], 0)];
    const da1raw = matMul(dz2, transpose(this.W2)); // (N,H)
    const da1 = da1raw.map((row, i) => row.map((v, j) => v * (bn[i][j] > 0 ? 1 : 0))); // relu grad
    const dW1data = matMul(transpose(X), da1);
    const dW1reg = l2Grad(this.W1, lam);
    const dW1 = dW1data.map((row, i) => row.map((v, j) => v + dW1reg[i][j]));
    const db1 = new Array(this.nHidden).fill(0) as number[];
    for (let i = 0; i < N; i++)
      for (let j = 0; j < this.nHidden; j++) db1[j] += da1[i][j];
    // SGD update
    for (let i = 0; i < this.W1.length; i++)
      for (let j = 0; j < this.nHidden; j++) this.W1[i][j] -= lr * dW1[i][j];
    for (let j = 0; j < this.nHidden; j++) this.b1[j] -= lr * db1[j];
    for (let i = 0; i < this.nHidden; i++) this.W2[i][0] -= lr * dW2[i][0];
    this.b2[0] -= lr * db2[0];
  }

  setBnEval(useBn: boolean): void {
    this.useBnEval = useBn;
  }

  accuracy(X: number[][], y: number[]): number {
    const p = this.forward(X, false, 0.0, this.useBnEval, makeRng(0)).p;
    let correct = 0;
    for (let i = 0; i < y.length; i++) if ((p[i][0] > 0.5 ? 1 : 0) === y[i]) correct++;
    return correct / y.length;
  }
}

function train(
  model: RegularizedMLP,
  XTrain: number[][],
  yTrain: number[],
  epochs: number,
  lr: number,
  dropoutP: number,
  useBn: boolean,
  lam: number,
  seed = 0,
): void {
  const rng = makeRng(seed);
  model.setBnEval(useBn);
  for (let e = 0; e < epochs; e++)
    model.trainStep(XTrain, yTrain, lr, dropoutP, useBn, lam, rng);
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main() {
  console.log("\n=== Task 3: regularisation (dropout / batchnorm / L2) ===\n");

  // ── Batchnorm sanity check ─────────────────────────────────────────────────
  console.log("[1/2] Batchnorm output statistics (want mean≈0, var≈1):");
  const rng = makeRng(1);
  const gauss = gaussianFactory(rng);
  const x = Array.from({ length: 64 }, () =>
    Array.from({ length: 8 }, () => gauss(5.0, 3.0)),
  );
  const gamma = new Array(8).fill(1);
  const beta = new Array(8).fill(0);
  const out = batchnormForward(x, gamma, beta);
  const D = 8,
    N = out.length;
  let maxAbsMean = 0,
    maxVarErr = 0;
  for (let j = 0; j < D; j++) {
    let mean = 0;
    for (let i = 0; i < N; i++) mean += out[i][j];
    mean /= N;
    let v = 0;
    for (let i = 0; i < N; i++) v += (out[i][j] - mean) ** 2;
    v /= N;
    maxAbsMean = Math.max(maxAbsMean, Math.abs(mean));
    maxVarErr = Math.max(maxVarErr, Math.abs(v - 1));
  }
  console.log(
    `    max |per-feature mean| = ${maxAbsMean.toExponential(2)}   (want < 1e-6)`,
  );
  console.log(
    `    max |per-feature var-1| = ${maxVarErr.toExponential(2)}   (want < 1e-3)`,
  );
  const bnOk = maxAbsMean < 1e-6 && maxVarErr < 1e-3;
  console.log(`    batchnorm normalises correctly: ${bnOk}`);

  // ── Overfitting vs regularisation ──────────────────────────────────────────
  console.log("\n[2/2] Generalisation gap: no-reg vs dropout+L2 (same split & seed):");
  const { X, y } = makeNoisyDataset(90, 60, 3, 0);
  const { XTrain, XTest, yTrain, yTest } = split(X, y, 30);

  // Baseline: high-capacity net, NO regularisation → memorises train set.
  const m0 = new RegularizedMLP(60, 64, 42);
  train(m0, XTrain, yTrain, 1500, 0.3, 0.0, false, 0.0);
  const tr0 = m0.accuracy(XTrain, yTrain),
    te0 = m0.accuracy(XTest, yTest);
  const gap0 = tr0 - te0;

  // Regularised: same architecture/seed, WITH dropout + L2.
  const m1 = new RegularizedMLP(60, 64, 42);
  train(m1, XTrain, yTrain, 1500, 0.3, 0.2, false, 1e-2);
  const tr1 = m1.accuracy(XTrain, yTrain),
    te1 = m1.accuracy(XTest, yTest);
  const gap1 = tr1 - te1;

  const pct = (v: number) => `${(v * 100).toFixed(2)}%`;
  console.log(
    `    no reg      : train ${pct(tr0)}  test ${pct(te0)}  gap ${pct(gap0)}`,
  );
  console.log(
    `    dropout+L2  : train ${pct(tr1)}  test ${pct(te1)}  gap ${pct(gap1)}`,
  );
  console.log(`\n  Regularisation shrank the generalisation gap: ${gap1 < gap0}`);
  console.log(`  (${pct(gap0)} → ${pct(gap1)})`);
}

main();

export {};
