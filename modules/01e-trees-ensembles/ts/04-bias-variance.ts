/**
 * Task 4 🟢 — Empirical bias–variance decomposition of tree models.
 *
 * What you'll learn:
 *   - The decomposition from Module 01b — E[(y - ŷ)²] = bias² + variance +
 *     noise — measured EMPIRICALLY: train the same model class on M
 *     independently resampled training sets and watch how its predictions
 *     scatter.
 *   - Why a stump is a high-BIAS model (too rigid to bend with the data)
 *     while a deep tree is a high-VARIANCE model (bends with every noise
 *     wiggle).
 *   - Why bagging works: averaging bootstrapped deep trees slashes variance
 *     while barely touching bias — the whole reason random forests exist.
 *
 * The math (README derives each step):
 *
 *   Fix a test point x with clean target f(x). Train M models on M resampled
 *   training sets; call their predictions ŷ_1 … ŷ_M and their mean ȳ̂(x).
 *
 *       bias²(x)    = ( ȳ̂(x) - f(x) )²
 *       variance(x) = (1/M) Σ_m ( ŷ_m(x) - ȳ̂(x) )²
 *
 *   Average both over the test points to get one bias² and one variance per
 *   model class. Against NOISY test labels y = f(x) + ε, ε ~ N(0, σ²):
 *
 *       E[ (y - ŷ)² ]  =  bias²  +  variance  +  σ²
 *       →  bias² + variance  ≈  expected MSE − σ²    (the harness checks it)
 *
 * You implement ONE function: empiricalBiasVariance(predictions, yTrue) —
 * the decomposition math itself. Everything else — the data machinery, a
 * compact regression-tree trainer, the three model classes (stump / deep
 * tree / bagged deep trees), and the comparison table — is provided and
 * runnable.
 *
 * How to run:
 *   pnpm tsx modules/01e-trees-ensembles/ts/04-bias-variance.ts
 */

const SEED = 42;
const M = 60; // number of resampled training sets (→ M trained models per class)
const N_TRAIN = 60; // points per training set
const N_TEST = 200; // fixed test grid
const NOISE_STD = 0.3; // σ of the label noise
const N_BAG = 20; // bootstrapped trees per bagged model

/** The clean target function the noisy data is drawn around. */
function fTrue(x: number): number {
  return Math.sin(2 * x);
}

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG + Box-Muller for reproducible randomness
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
// Regression-tree trainer (provided — do not edit)
//
// A compact CART for 1-D regression: splits minimise the two-sided SSE of
// the residuals around each side's mean; leaves predict the mean.
// maxDepth=1 gives a stump; maxDepth=null grows until pure/exhausted.
// ---------------------------------------------------------------------------

type RegNode =
  | { leaf: true; value: number }
  | { leaf: false; threshold: number; left: RegNode; right: RegNode };

function mean(v: number[]): number {
  return v.reduce((a, b) => a + b, 0) / v.length;
}

function sse(v: number[]): number {
  const m = mean(v);
  let s = 0;
  for (const x of v) s += (x - m) ** 2;
  return s;
}

function trainRegTree(
  x: number[],
  y: number[],
  depth: number,
  maxDepth: number | null,
  minSamplesLeaf: number,
): RegNode {
  const leaf = (): RegNode => ({ leaf: true, value: mean(y) });
  if ((maxDepth !== null && depth >= maxDepth) || y.length < 2 * minSamplesLeaf)
    return leaf();
  const vals = Array.from(new Set(x)).sort((a, b) => a - b);
  if (vals.length < 2) return leaf();
  const parentSse = sse(y);
  let bestSse = parentSse - 1e-12;
  let bestT: number | null = null;
  for (let k = 0; k < vals.length - 1; k++) {
    const t = (vals[k] + vals[k + 1]) / 2;
    const yL: number[] = [];
    const yR: number[] = [];
    for (let i = 0; i < x.length; i++) (x[i] <= t ? yL : yR).push(y[i]);
    if (yL.length < minSamplesLeaf || yR.length < minSamplesLeaf) continue;
    const s = sse(yL) + sse(yR);
    if (s < bestSse) {
      bestSse = s;
      bestT = t;
    }
  }
  if (bestT === null) return leaf();
  const xL: number[] = [];
  const yL: number[] = [];
  const xR: number[] = [];
  const yR: number[] = [];
  for (let i = 0; i < x.length; i++) {
    if (x[i] <= bestT) {
      xL.push(x[i]);
      yL.push(y[i]);
    } else {
      xR.push(x[i]);
      yR.push(y[i]);
    }
  }
  return {
    leaf: false,
    threshold: bestT,
    left: trainRegTree(xL, yL, depth + 1, maxDepth, minSamplesLeaf),
    right: trainRegTree(xR, yR, depth + 1, maxDepth, minSamplesLeaf),
  };
}

function regTreePredict(tree: RegNode, x: number[]): number[] {
  return x.map((xi) => {
    let node = tree;
    while (!node.leaf) node = xi <= node.threshold ? node.left : node.right;
    return node.value;
  });
}

// ---------------------------------------------------------------------------
// Resampling machinery + the three model classes (provided — do not edit)
// ---------------------------------------------------------------------------

type Rngs = { u: () => number; g: () => number };

/** One fresh draw from the generative process: x ~ U[-3,3], y = f(x) + ε. */
function makeTrainingSet(rngs: Rngs): { x: number[]; y: number[] } {
  const x = Array.from({ length: N_TRAIN }, () => -3 + 6 * rngs.u());
  const y = x.map((xi) => fTrue(xi) + NOISE_STD * rngs.g());
  return { x, y };
}

type FitFn = (rngs: Rngs, x: number[], y: number[], xTest: number[]) => number[];

const fitStumpModel: FitFn = (_rngs, x, y, xTest) =>
  regTreePredict(trainRegTree(x, y, 0, 1, 1), xTest);

const fitDeepModel: FitFn = (_rngs, x, y, xTest) =>
  regTreePredict(trainRegTree(x, y, 0, null, 1), xTest);

/** Average of N_BAG unlimited-depth trees, each on a bootstrap resample. */
const fitBaggedModel: FitFn = (rngs, x, y, xTest) => {
  const preds = xTest.map(() => 0);
  for (let b = 0; b < N_BAG; b++) {
    const idx = Array.from({ length: x.length }, () => Math.floor(rngs.u() * x.length));
    const tree = trainRegTree(
      idx.map((i) => x[i]),
      idx.map((i) => y[i]),
      0,
      null,
      1,
    );
    const p = regTreePredict(tree, xTest);
    for (let i = 0; i < preds.length; i++) preds[i] += p[i];
  }
  return preds.map((p) => p / N_BAG);
};

/** Train on M fresh training sets; stack the M test predictions (M × N_TEST). */
function predictionMatrix(fitFn: FitFn, rngs: Rngs, xTest: number[]): number[][] {
  const rows: number[][] = [];
  for (let m = 0; m < M; m++) {
    const { x, y } = makeTrainingSet(rngs);
    rows.push(fitFn(rngs, x, y, xTest));
  }
  return rows;
}

// ---------------------------------------------------------------------------
// Core function — YOU implement this one
// ---------------------------------------------------------------------------

/**
 * The bias–variance decomposition, computed from data.
 *
 * Args:
 *   predictions : (M × N_test) — row m holds model m's predictions on the
 *                 shared test grid (model m was trained on training set m).
 *   yTrue       : length N_test — the CLEAN targets f(xTest) (no noise).
 *
 * Returns { biasSquared, variance } — two numbers, each averaged over the
 * test points:
 *   1. mean prediction per test point: average the M rows column-wise →
 *      a length-N_test vector ȳ̂.
 *   2. bias² = mean over test points of (ȳ̂ - yTrue)².
 *   3. variance = mean over test points of the variance ACROSS the M models
 *      at that point, i.e. mean over m of (predictions[m] - ȳ̂)²
 *      (population variance — divide by M, not M-1).
 *
 * TODO: implement the three numbered steps above.
 */
function empiricalBiasVariance(
  predictions: number[][],
  yTrue: number[],
): { biasSquared: number; variance: number } {
  // TODO: implement the bias-variance decomposition
  throw new Error("TODO: implement empiricalBiasVariance()");
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 4 — Empirical bias–variance decomposition of tree models\n");
  console.log(
    `  Target f(x) = sin(2x), noise σ = ${NOISE_STD} (σ² = ${(NOISE_STD ** 2).toFixed(3)})`,
  );
  console.log(
    `  ${M} resampled training sets of ${N_TRAIN} points; ${N_TEST} test points\n`,
  );

  const xTest = Array.from({ length: N_TEST }, (_, i) => -3 + (6 * i) / (N_TEST - 1));
  const yTrue = xTest.map(fTrue); // CLEAN targets for the decomposition

  // One independent noisy test-label draw PER model, for the expected-MSE check.
  const noiseG = makeGaussian(SEED + 1);
  const testNoise = Array.from({ length: M }, () =>
    Array.from({ length: N_TEST }, () => NOISE_STD * noiseG()),
  );

  const models: Array<[string, FitFn]> = [
    ["stump (depth 1)", fitStumpModel],
    ["deep tree", fitDeepModel],
    [`bagged deep ×${N_BAG}`, fitBaggedModel],
  ];

  const results = new Map<string, { b: number; v: number; m: number }>();
  console.log(
    `  ${"model".padEnd(18)} ${"bias²".padStart(8)} ${"variance".padStart(9)} ` +
      `${"bias²+var".padStart(10)} ${"expMSE−σ²".padStart(10)}`,
  );
  for (const [name, fitFn] of models) {
    // Same M training sets for every model (fresh rng streams per class).
    const rngs: Rngs = { u: makeRng(SEED), g: makeGaussian(SEED + 7) };
    const preds = predictionMatrix(fitFn, rngs, xTest);
    const { biasSquared, variance } = empiricalBiasVariance(preds, yTrue);
    // Expected MSE against noisy labels y = f(x) + ε (fresh ε per model draw).
    let expMse = 0;
    for (let m = 0; m < M; m++) {
      for (let i = 0; i < N_TEST; i++) {
        expMse += (preds[m][i] - (yTrue[i] + testNoise[m][i])) ** 2 / (M * N_TEST);
      }
    }
    results.set(name, { b: biasSquared, v: variance, m: expMse });
    console.log(
      `  ${name.padEnd(18)} ${biasSquared.toFixed(4).padStart(8)} ` +
        `${variance.toFixed(4).padStart(9)} ${(biasSquared + variance).toFixed(4).padStart(10)} ` +
        `${(expMse - NOISE_STD ** 2).toFixed(4).padStart(10)}`,
    );
  }

  const stump = results.get("stump (depth 1)")!;
  const deep = results.get("deep tree")!;
  const bag = results.get(`bagged deep ×${N_BAG}`)!;

  console.log(
    `\n  bagging cut the deep tree's variance: ${deep.v.toFixed(4)} → ${bag.v.toFixed(4)} ` +
      `(${Math.round((100 * bag.v) / deep.v)}% of it left)`,
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okBias = stump.b > deep.b && stump.b > bag.b;
  const okVar = deep.v > stump.v && deep.v > bag.v;
  const okBag = bag.v < 0.6 * deep.v;
  const tol = 0.03;
  let okDecomp = true;
  for (const { b, v, m } of results.values()) {
    if (Math.abs(b + v - (m - NOISE_STD ** 2)) >= tol) okDecomp = false;
  }
  console.log(
    `  [${okBias ? "x" : " "}] stump has the highest bias²  (${stump.b.toFixed(4)})`,
  );
  console.log(
    `  [${okVar ? "x" : " "}] deep tree has the highest variance  (${deep.v.toFixed(4)})`,
  );
  console.log(
    `  [${okBag ? "x" : " "}] bagging cuts deep-tree variance by >40%  ` +
      `(${bag.v.toFixed(4)} < 0.6 × ${deep.v.toFixed(4)})`,
  );
  console.log(
    `  [${okDecomp ? "x" : " "}] bias² + variance ≈ expected MSE − σ²  ` +
      `(within ±${tol}) for all three models`,
  );

  if (okBias && okVar && okBag && okDecomp) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
