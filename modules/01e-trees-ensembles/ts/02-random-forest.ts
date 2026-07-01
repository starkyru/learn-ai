/**
 * Task 2 🟡 — Bagging → random forest.
 *
 * What you'll learn:
 *   - Bootstrap sampling: draw n indices WITH replacement — each resample
 *     leaves out ≈ 36.8% of the rows (the fraction of unique rows → 1 - 1/e
 *     ≈ 63.2%).
 *   - Bagging: train one tree per bootstrap, average (majority-vote) their
 *     predictions — averaging B noisy estimators divides the uncorrelated
 *     part of their variance by B.
 *   - The random-forest trick: at EVERY split, consider only a random subset
 *     of maxFeatures features, so the trees stop all making the same greedy
 *     first split and become decorrelated — which is what makes the
 *     averaging work.
 *
 * The math (README derives each step):
 *
 *   Unique-fraction of a bootstrap:  P(row i never drawn in n tries)
 *       = (1 - 1/n)^n → e⁻¹ ≈ 0.368,  so  unique ≈ 63.2% of rows.
 *
 *   Variance of an average of B estimators with variance σ² and pairwise
 *   correlation ρ:
 *       Var( (1/B) Σ f_b ) = ρσ² + (1-ρ)σ²/B
 *   Bagging shrinks the second term; feature subsampling shrinks ρ — the
 *   first.
 *
 * You implement: bootstrapSample, trainForest, forestPredict. A full
 * single-tree trainer that accepts maxFeatures (the per-split feature
 * sampler), the dataset (2 signal + 3 pure-noise features), and the harness
 * comparing individual trees vs the ensemble vs a single deep-tree baseline
 * are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01e-trees-ensembles/ts/02-random-forest.ts
 */

const SEED = 21;
const N = 520; // total samples (first N_TRAIN train, rest test)
const N_TRAIN = 370;
const NOISE_FLIP = 0.1;
const N_TREES = 25;
const MAX_FEATURES = 2; // features considered per split (out of 5)

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
// Tree node type + synthetic data (provided — do not edit)
// ---------------------------------------------------------------------------

type TreeNode =
  | { leaf: true; prediction: number }
  | {
      leaf: false;
      feature: number;
      threshold: number;
      left: TreeNode;
      right: TreeNode;
    };

/**
 * 5 features: x0, x1 carry the signal (the offset-XOR pattern from Task 1);
 * x2..x4 are pure Gaussian noise — bait for an overfitting deep tree.
 * NOISE_FLIP of the labels are flipped.
 */
function makeData(): {
  XTrain: number[][];
  yTrain: number[];
  XTest: number[][];
  yTest: number[];
} {
  const u = makeRng(SEED);
  const g = makeGaussian(SEED + 50);
  const X = Array.from({ length: N }, () => [
    -3 + 6 * u(),
    -3 + 6 * u(),
    g(),
    g(),
    g(),
  ]);
  const flip = makeRng(SEED + 99);
  const y = X.map((row) => {
    const label = row[0] > 0.8 !== row[1] > -0.7 ? 1 : 0;
    return flip() < NOISE_FLIP ? 1 - label : label;
  });
  return {
    XTrain: X.slice(0, N_TRAIN),
    yTrain: y.slice(0, N_TRAIN),
    XTest: X.slice(N_TRAIN),
    yTest: y.slice(N_TRAIN),
  };
}

// ---------------------------------------------------------------------------
// Single-tree trainer (provided — do not edit)
//
// The same CART you built in Task 1, with ONE addition: if maxFeatures is
// set, each split only scans a random subset of that many features (drawn
// with the rng) — the random-forest decorrelation trick.
// ---------------------------------------------------------------------------

function giniImpurity(y: number[]): number {
  if (y.length === 0) return 0;
  let ones = 0;
  for (const v of y) ones += v;
  const p1 = ones / y.length;
  return 1 - ((1 - p1) ** 2 + p1 ** 2);
}

function majorityClass(y: number[]): number {
  let ones = 0;
  for (const v of y) ones += v;
  return ones * 2 > y.length ? 1 : 0;
}

function pickFeatures(
  rng: () => number,
  d: number,
  maxFeatures: number | null,
): number[] {
  const all = Array.from({ length: d }, (_, j) => j);
  if (maxFeatures === null || maxFeatures >= d) return all;
  // Partial Fisher-Yates shuffle: the first maxFeatures entries are a
  // uniform random subset without replacement.
  for (let i = 0; i < maxFeatures; i++) {
    const j = i + Math.floor(rng() * (d - i));
    [all[i], all[j]] = [all[j], all[i]];
  }
  return all.slice(0, maxFeatures);
}

function bestSplitOf(
  X: number[][],
  y: number[],
  rng: () => number,
  maxFeatures: number | null,
): { feature: number; threshold: number } | null {
  const n = y.length;
  const features = pickFeatures(rng, X[0].length, maxFeatures);
  let best: { feature: number; threshold: number } | null = null;
  let bestScore = giniImpurity(y) - 1e-12;
  for (const j of features) {
    const vals = Array.from(new Set(X.map((row) => row[j]))).sort((a, b) => a - b);
    for (let k = 0; k < vals.length - 1; k++) {
      const t = (vals[k] + vals[k + 1]) / 2;
      const yLeft: number[] = [];
      const yRight: number[] = [];
      for (let i = 0; i < n; i++) (X[i][j] <= t ? yLeft : yRight).push(y[i]);
      if (yLeft.length === 0 || yRight.length === 0) continue;
      const score =
        (yLeft.length * giniImpurity(yLeft) + yRight.length * giniImpurity(yRight)) / n;
      if (score < bestScore) {
        bestScore = score;
        best = { feature: j, threshold: t };
      }
    }
  }
  return best;
}

/** Grow an unlimited-depth CART tree; same node objects as Task 1. */
function trainTree(
  X: number[][],
  y: number[],
  rng: () => number,
  maxFeatures: number | null,
): TreeNode {
  if (giniImpurity(y) === 0) return { leaf: true, prediction: majorityClass(y) };
  const split = bestSplitOf(X, y, rng, maxFeatures);
  if (split === null) return { leaf: true, prediction: majorityClass(y) };
  const XL: number[][] = [];
  const yL: number[] = [];
  const XR: number[][] = [];
  const yR: number[] = [];
  for (let i = 0; i < y.length; i++) {
    if (X[i][split.feature] <= split.threshold) {
      XL.push(X[i]);
      yL.push(y[i]);
    } else {
      XR.push(X[i]);
      yR.push(y[i]);
    }
  }
  return {
    leaf: false,
    feature: split.feature,
    threshold: split.threshold,
    left: trainTree(XL, yL, rng, maxFeatures),
    right: trainTree(XR, yR, rng, maxFeatures),
  };
}

/** Predict every row of X with one tree. */
function treePredict(tree: TreeNode, X: number[][]): number[] {
  return X.map((x) => {
    let node = tree;
    while (!node.leaf)
      node = x[node.feature] <= node.threshold ? node.left : node.right;
    return node.prediction;
  });
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * Draw a bootstrap sample: n indices from {0, …, n-1} WITH replacement.
 *
 * Returns an array of n integer indices (duplicates expected — that's the
 * point; ≈ 63.2% of the rows appear at least once).
 *
 * TODO: implement — n draws of Math.floor(rng() * n).
 */
function bootstrapSample(rng: () => number, n: number): number[] {
  // TODO: implement the bootstrap draw
  throw new Error("TODO: implement bootstrapSample()");
}

/**
 * Train a random forest: nTrees CART trees, EACH on its own bootstrap sample
 * of the rows, EACH restricted to maxFeatures random features per split (the
 * provided trainTree handles that part — just pass it through).
 *
 * Returns the array of nTrees TreeNode roots.
 *
 * TODO: implement.
 *   1. For each of the nTrees rounds, draw indices with your bootstrapSample
 *      and gather the corresponding rows of X and entries of y.
 *   2. Train a tree on that resample with the provided trainTree (forward
 *      rng and maxFeatures), and collect it.
 *   3. Return the array of trees.
 */
function trainForest(
  X: number[][],
  y: number[],
  rng: () => number,
  nTrees: number,
  maxFeatures: number | null,
): TreeNode[] {
  // TODO: implement the bootstrap-then-train loop
  throw new Error("TODO: implement trainForest()");
}

/**
 * Majority vote of the forest: predict X with every tree (treePredict),
 * then, per sample, output the class most trees chose.
 *
 * With binary {0,1} labels the vote reduces to: mean over trees ≥ 0.5 → 1.
 * (N_TREES is odd, so there are no exact ties.)
 *
 * Returns an array of X.length {0, 1} predictions.
 *
 * TODO: implement.
 *   1. Collect every tree's treePredict(tree, X) (an nTrees × N array).
 *   2. Take the per-sample vote per the rule above and return it.
 */
function forestPredict(trees: TreeNode[], X: number[][]): number[] {
  // TODO: implement the majority vote
  throw new Error("TODO: implement forestPredict()");
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function acc(pred: number[], y: number[]): number {
  let correct = 0;
  for (let i = 0; i < y.length; i++) if (pred[i] === y[i]) correct++;
  return correct / y.length;
}

function main(): void {
  console.log("Task 2 — Bagging → random forest\n");

  const { XTrain, yTrain, XTest, yTest } = makeData();
  console.log(`  Data: ${yTrain.length} train / ${yTest.length} test, 5 features`);
  console.log(`  (2 signal + 3 pure noise), ${NOISE_FLIP * 100}% label noise\n`);

  // ── Bootstrap statistics ───────────────────────────────────────────────────
  console.log("[1/3] Bootstrap sampling (63.2% unique)...");
  let rng = makeRng(SEED);
  const n = yTrain.length;
  const uniqueFracs: number[] = [];
  let allHaveDups = true;
  for (let s = 0; s < 20; s++) {
    const idx = bootstrapSample(rng, n);
    const uniq = new Set(idx).size;
    uniqueFracs.push(uniq / n);
    if (uniq === n) allHaveDups = false;
  }
  const meanUnique = uniqueFracs.reduce((a, b) => a + b, 0) / uniqueFracs.length;
  console.log(
    `  20 bootstraps of n=${n}: mean unique fraction = ${meanUnique.toFixed(4)}`,
  );
  console.log(
    `  (theory: 1 - 1/e ≈ 0.6321) — every sample has duplicates: ${allHaveDups}\n`,
  );

  // ── Baseline: one deep tree on everything ──────────────────────────────────
  console.log("[2/3] Baseline: single deep tree (all rows, all features)...");
  rng = makeRng(SEED);
  const baseline = trainTree(XTrain, yTrain, rng, null);
  const baseTrain = acc(treePredict(baseline, XTrain), yTrain);
  const baseTest = acc(treePredict(baseline, XTest), yTest);
  console.log(
    `  train acc = ${baseTrain.toFixed(4)}   test acc = ${baseTest.toFixed(4)}\n`,
  );

  // ── The forest ─────────────────────────────────────────────────────────────
  console.log(`[3/3] Random forest (${N_TREES} trees, maxFeatures=${MAX_FEATURES})...`);
  rng = makeRng(SEED);
  const forest = trainForest(XTrain, yTrain, rng, N_TREES, MAX_FEATURES);
  const treeAccs = forest.map((t) => acc(treePredict(t, XTest), yTest));
  const ensTest = acc(forestPredict(forest, XTest), yTest);
  const meanTreeAcc = treeAccs.reduce((a, b) => a + b, 0) / treeAccs.length;
  console.log(
    `  individual tree test accs (first 8): [${treeAccs
      .slice(0, 8)
      .map((a) => a.toFixed(3))
      .join(", ")}]`,
  );
  console.log(
    `  individual: mean = ${meanTreeAcc.toFixed(4)}  ` +
      `min = ${Math.min(...treeAccs).toFixed(4)}  max = ${Math.max(...treeAccs).toFixed(4)}`,
  );
  console.log(`  ensemble (majority vote) test acc = ${ensTest.toFixed(4)}`);

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okBoot = allHaveDups && meanUnique >= 0.55 && meanUnique <= 0.72;
  const okVsMean = ensTest >= meanTreeAcc;
  const okVsBase = ensTest >= baseTest;
  console.log(
    `  [${okBoot ? "x" : " "}] bootstraps have duplicates; unique fraction ≈ 0.632 (got ${meanUnique.toFixed(4)})`,
  );
  console.log(
    `  [${okVsMean ? "x" : " "}] ensemble ≥ mean individual tree  (${ensTest.toFixed(4)} ≥ ${meanTreeAcc.toFixed(4)})`,
  );
  console.log(
    `  [${okVsBase ? "x" : " "}] ensemble ≥ single deep-tree baseline  (${ensTest.toFixed(4)} ≥ ${baseTest.toFixed(4)})`,
  );

  if (okBoot && okVsMean && okVsBase) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
