/**
 * Task 1 🔴 — A decision tree (CART) from scratch.
 *
 * What you'll learn:
 *   - Gini impurity: how "mixed" a set of labels is, and why a split that
 *     lowers the weighted impurity of its children is a good split.
 *   - Greedy recursive partitioning (CART): scan every feature and every
 *     midpoint threshold, take the best split, recurse — no gradient anywhere.
 *   - Why an unlimited-depth tree memorises the training set (train accuracy
 *     → 1) while its test accuracy lags — the overfitting gap made visible.
 *   - How maxDepth / minSamplesLeaf act as the tree's regularisers.
 *
 * The math (README derives each step):
 *
 *   Gini impurity of a label set y (classes c, class proportions p_c):
 *       G(y) = 1 - Σ_c p_c²
 *       pure node (one class)      → G = 0
 *       balanced binary (50/50)    → G = 0.5   (the binary maximum)
 *
 *   Quality of a split of y into (yLeft, yRight), sizes nL and nR:
 *       G_split = (nL · G(yLeft) + nR · G(yRight)) / (nL + nR)
 *   Best split = the (feature, threshold) minimising G_split. Only accept it
 *   if G_split < G(y) (positive "Gini gain").
 *
 *   Candidate thresholds for a feature = midpoints between consecutive SORTED
 *   UNIQUE values of that feature — no other threshold changes the partition.
 *
 * You implement the four core functions: gini, bestSplit, buildTree, and
 * predictOne (plain arrays only — no math libraries). The dataset (a noisy
 * XOR-quadrant pattern no linear model can solve), train/test split,
 * vectorised predict, and the depth-limited-vs-unlimited comparison harness
 * are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01e-trees-ensembles/ts/01-decision-tree.ts
 */

const SEED = 11;
const N = 500; // total samples (first N_TRAIN train, rest test)
const N_TRAIN = 350;
const NOISE_FLIP = 0.1; // fraction of labels flipped at random

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
 * 2-D points uniform in [-3, 3]²; the true label is an offset XOR of the two
 * coordinates:  y = (x0 > 0.8) XOR (x1 > -0.7)  — a nonlinear checkerboard
 * quadrant pattern. Then NOISE_FLIP of the labels are flipped, so a perfect
 * memoriser of the training set CANNOT be perfect on the test set.
 */
function makeData(): {
  XTrain: number[][];
  yTrain: number[];
  XTest: number[][];
  yTest: number[];
} {
  const u = makeRng(SEED);
  const X = Array.from({ length: N }, () => [-3 + 6 * u(), -3 + 6 * u()]);
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
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Gini impurity:  G(y) = 1 - Σ_c p_c²  over the class proportions p_c.
 *
 * y is an array of class labels in {0, 1}. Returns a number in [0, 0.5]
 * (0 = pure, 0.5 = 50/50). An empty y should return 0.
 *
 * TODO: implement.
 *   - Handle the empty case first.
 *   - Count each class, turn the counts into proportions, and apply the
 *     formula above.
 */
function gini(y: number[]): number {
  // TODO: implement Gini impurity
  throw new Error("TODO: implement gini()");
}

/**
 * Exhaustive CART split search: scan EVERY feature and EVERY midpoint between
 * consecutive sorted unique values; return the { feature, threshold } whose
 * weighted child Gini  (nL·G_L + nR·G_R) / n  is smallest.
 *
 * A point goes LEFT when  x[feature] <= threshold  (that convention must
 * match predictOne). Skip splits that leave either side with fewer than
 * minSamplesLeaf points. Return null when no split strictly reduces the
 * parent impurity (that node should become a leaf).
 *
 * TODO: implement.
 *   1. Start with best score = gini(y) (a split must beat the parent).
 *   2. For each feature j: collect the sorted unique values of column j
 *      (a Set + numeric sort works); candidate thresholds are the midpoints
 *      of consecutive pairs.
 *   3. For each threshold: partition y by  X[i][j] <= threshold, skip if
 *      either side is smaller than minSamplesLeaf, else compute the weighted
 *      child Gini per the formula and keep the argmin.
 *   4. Return the winning { feature, threshold }, or null if nothing beat
 *      the parent impurity (use a small epsilon like 1e-12).
 */
function bestSplit(
  X: number[][],
  y: number[],
  minSamplesLeaf: number,
): { feature: number; threshold: number } | null {
  // TODO: implement the exhaustive split search
  throw new Error("TODO: implement bestSplit()");
}

/**
 * Recursively grow a CART tree. Nodes are plain objects:
 *
 *   leaf:      { leaf: true,  prediction: <majority class, 0 or 1> }
 *   internal:  { leaf: false, feature, threshold, left, right }
 *
 * Stop and return a leaf when ANY of these hold:
 *   - the node is pure (gini === 0),
 *   - maxDepth is set (non-null) and depth has reached it,
 *   - bestSplit(...) returns null (no impurity-reducing split exists).
 *
 * The leaf prediction is the MAJORITY class of y at that node.
 *
 * TODO: implement.
 *   1. Check the stopping conditions above; on any of them return the leaf
 *      object with the majority class.
 *   2. Otherwise call bestSplit (pass minSamplesLeaf through), partition the
 *      rows (and labels) by  X[i][feature] <= threshold, and recurse on each
 *      side with depth + 1 to fill the internal node's left and right.
 */
function buildTree(
  X: number[][],
  y: number[],
  depth: number,
  maxDepth: number | null,
  minSamplesLeaf: number,
): TreeNode {
  // TODO: implement the recursive tree growth
  throw new Error("TODO: implement buildTree()");
}

/**
 * Route a single sample x down the tree to a leaf and return its prediction.
 *
 * At each internal node go LEFT when  x[node.feature] <= node.threshold
 * (the same convention buildTree used), otherwise right.
 *
 * TODO: implement — walk (loop or recurse) until node.leaf is true, then
 * return that leaf's prediction.
 */
function predictOne(node: TreeNode, x: number[]): number {
  // TODO: implement the tree walk
  throw new Error("TODO: implement predictOne()");
}

// ---------------------------------------------------------------------------
// Helpers (provided — use your predictOne)
// ---------------------------------------------------------------------------

function predict(tree: TreeNode, X: number[][]): number[] {
  return X.map((x) => predictOne(tree, x));
}

function accuracy(tree: TreeNode, X: number[][], y: number[]): number {
  const pred = predict(tree, X);
  let correct = 0;
  for (let i = 0; i < y.length; i++) if (pred[i] === y[i]) correct++;
  return correct / y.length;
}

function treeDepth(node: TreeNode): number {
  if (node.leaf) return 0;
  return 1 + Math.max(treeDepth(node.left), treeDepth(node.right));
}

function countLeaves(node: TreeNode): number {
  if (node.leaf) return 1;
  return countLeaves(node.left) + countLeaves(node.right);
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 1 — Decision tree (CART) from scratch\n");

  // ── Gini sanity checks ─────────────────────────────────────────────────────
  console.log("[1/3] Gini impurity sanity...");
  const gPure = gini([1, 1, 1, 1]);
  const gBalanced = gini([0, 1, 0, 1]);
  console.log(`  gini([1,1,1,1])  = ${gPure.toFixed(4)}   (pure     → expect 0.0)`);
  console.log(
    `  gini([0,1,0,1])  = ${gBalanced.toFixed(4)}   (balanced → expect 0.5)\n`,
  );

  const { XTrain, yTrain, XTest, yTest } = makeData();
  console.log(`  Data: ${yTrain.length} train / ${yTest.length} test, 2 features,`);
  console.log(`  XOR-quadrant boundary, ${NOISE_FLIP * 100}% label noise\n`);

  // ── Unlimited depth: the memoriser ─────────────────────────────────────────
  console.log("[2/3] Unlimited-depth tree (memorises the training set)...");
  const deep = buildTree(XTrain, yTrain, 0, null, 1);
  const deepTrain = accuracy(deep, XTrain, yTrain);
  const deepTest = accuracy(deep, XTest, yTest);
  const deepGap = deepTrain - deepTest;
  console.log(`  depth = ${treeDepth(deep)}, leaves = ${countLeaves(deep)}`);
  console.log(
    `  train acc = ${deepTrain.toFixed(4)}   test acc = ${deepTest.toFixed(4)}`,
  );
  console.log(
    `  overfit gap (train - test) = ${deepGap >= 0 ? "+" : ""}${deepGap.toFixed(4)}\n`,
  );

  // ── Depth-limited: the regularised tree ────────────────────────────────────
  console.log("[3/3] Depth-3 tree (regularised)...");
  const shallow = buildTree(XTrain, yTrain, 0, 3, 5);
  const shTrain = accuracy(shallow, XTrain, yTrain);
  const shTest = accuracy(shallow, XTest, yTest);
  const shGap = shTrain - shTest;
  console.log(`  depth = ${treeDepth(shallow)}, leaves = ${countLeaves(shallow)}`);
  console.log(`  train acc = ${shTrain.toFixed(4)}   test acc = ${shTest.toFixed(4)}`);
  console.log(
    `  overfit gap (train - test) = ${shGap >= 0 ? "+" : ""}${shGap.toFixed(4)}`,
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okGini = Math.abs(gPure) < 1e-12 && Math.abs(gBalanced - 0.5) < 1e-12;
  const okMemorise = deepTrain >= 0.99;
  const okGap = deepGap >= 0.1;
  const okShallow = shGap < deepGap && shTest >= 0.8;
  console.log(`  [${okGini ? "x" : " "}] gini: pure = 0.0, balanced binary = 0.5`);
  console.log(
    `  [${okMemorise ? "x" : " "}] deep tree memorises: train acc ≥ 0.99  (got ${deepTrain.toFixed(4)})`,
  );
  console.log(
    `  [${okGap ? "x" : " "}] deep tree overfits: train - test gap ≥ 0.10  (got +${deepGap.toFixed(4)})`,
  );
  console.log(
    `  [${okShallow ? "x" : " "}] depth-3 tree generalises: smaller gap ` +
      `(+${shGap.toFixed(4)} < +${deepGap.toFixed(4)}) and test acc ≥ 0.80 (got ${shTest.toFixed(4)})`,
  );

  if (okGini && okMemorise && okGap && okShallow) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
