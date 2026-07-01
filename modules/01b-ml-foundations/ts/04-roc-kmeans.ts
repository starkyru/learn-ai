/**
 * Task 4 🟢 — Ranking metrics (ROC/AUC) and clustering (k-means) from scratch.
 *
 * What you'll learn:
 *   Part A — ROC curves and AUC:
 *     - A classifier outputs SCORES, not just labels; a threshold turns scores
 *       into decisions. Sweeping the threshold traces the ROC curve.
 *     - TPR (recall) vs FPR at every threshold; AUC summarises the whole curve.
 *     - AUC = P(a random positive scores higher than a random negative). It is
 *       threshold-free, which is why interviewers love it.
 *
 *   Part B — k-means (Lloyd's algorithm):
 *     - Unsupervised clustering: no labels, just group points by proximity.
 *     - Alternate: (1) assign each point to its nearest centroid, (2) move each
 *       centroid to the mean of its assigned points. Repeat until stable.
 *     - Inertia (within-cluster sum of squared distances) never increases.
 *
 * The math (README derives each step):
 *
 *   ROC:  at threshold t, predict positive iff score ≥ t.
 *         TPR(t) = TP / (TP + FN)     FPR(t) = FP / (FP + TN)
 *   AUC:  area under the (FPR, TPR) curve via the trapezoidal rule:
 *         AUC = Σ (fpr[i+1] - fpr[i]) · (tpr[i+1] + tpr[i]) / 2
 *
 *   k-means:
 *         assign:  cluster(x) = argmin_k ||x - c_k||²
 *         update:  c_k = mean of all x assigned to k
 *         inertia: Σ_i ||x_i - c_{assign(i)}||²
 *
 * You implement: rocCurve, auc, assignClusters, updateCentroids, inertia — plain
 * arrays only. Everything else is provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01b-ml-foundations/ts/04-roc-kmeans.ts
 */

const SEED = 5;

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

// ===========================================================================
// PART A — ROC / AUC  (YOU implement rocCurve and auc)
// ===========================================================================

/**
 * Compute the ROC curve by sweeping every threshold.
 *
 * Args:
 *   scores : the classifier's confidence that each item is positive
 *   labels : ground truth in {0, 1}
 *
 * Returns { fpr, tpr }: parallel arrays. The curve starts at (0, 0) and ends at
 * (1, 1).
 *
 * Method:
 *   1. Sort item INDICES by score DESCENDING (highest score first).
 *   2. P = count of positives, Nn = count of negatives.
 *   3. Start at (FPR=0, TPR=0). Walk the sorted order; on each positive admitted
 *      tp += 1, on each negative fp += 1; after each step push (fp/Nn, tp/P).
 *
 * TODO: implement.
 *   1. const order = labels.map((_, i) => i).sort((a, b) => scores[b] - scores[a]);
 *   2. const P = labels.filter(l => l === 1).length;
 *      const Nn = labels.filter(l => l === 0).length;
 *   3. let tp = 0, fp = 0;
 *      const fpr = [0], tpr = [0];
 *      for (const i of order) {
 *        if (labels[i] === 1) tp++; else fp++;
 *        tpr.push(tp / P);
 *        fpr.push(fp / Nn);
 *      }
 *   4. return { fpr, tpr };
 */
function rocCurve(
  scores: number[],
  labels: number[],
): { fpr: number[]; tpr: number[] } {
  // TODO: implement the ROC sweep
  throw new Error("TODO: implement rocCurve()");
}

/**
 * Area under the ROC curve via the trapezoidal rule.
 *
 * AUC = Σ_i (fpr[i+1] - fpr[i]) · (tpr[i+1] + tpr[i]) / 2
 *
 * TODO: implement.
 *   let area = 0;
 *   for (let i = 0; i < fpr.length - 1; i++) {
 *     area += (fpr[i + 1] - fpr[i]) * (tpr[i + 1] + tpr[i]) / 2;
 *   }
 *   return area;
 */
function auc(fpr: number[], tpr: number[]): number {
  // TODO: implement the trapezoidal AUC
  throw new Error("TODO: implement auc()");
}

// ===========================================================================
// PART B — k-means  (YOU implement assignClusters, updateCentroids, inertia)
// ===========================================================================

/** Squared Euclidean distance between two equal-length points. */
function sqDist(a: number[], b: number[]): number {
  let s = 0;
  for (let d = 0; d < a.length; d++) s += (a[d] - b[d]) ** 2;
  return s;
}

/**
 * Assign each point to its nearest centroid (by squared Euclidean distance).
 *
 * Returns an array of length X.length: the cluster index of each point.
 *
 * TODO: implement.
 *   return X.map((x) => {
 *     let best = 0, bestD = Infinity;
 *     for (let j = 0; j < centroids.length; j++) {
 *       const d = sqDist(x, centroids[j]);   // sqDist is provided above
 *       if (d < bestD) { bestD = d; best = j; }
 *     }
 *     return best;
 *   });
 */
function assignClusters(X: number[][], centroids: number[][]): number[] {
  // TODO: implement nearest-centroid assignment
  throw new Error("TODO: implement assignClusters()");
}

/**
 * Recompute each centroid as the mean of the points assigned to it.
 *
 * Returns k centroids. (For this seeded data no cluster goes empty; if one did,
 * leaving it as zeros / its old value is a reasonable fallback.)
 *
 * TODO: implement.
 *   const D = X[0].length;
 *   const sums = Array.from({ length: k }, () => new Array(D).fill(0));
 *   const counts = new Array(k).fill(0);
 *   for (let i = 0; i < X.length; i++) {
 *     const c = assignments[i];
 *     counts[c]++;
 *     for (let d = 0; d < D; d++) sums[c][d] += X[i][d];
 *   }
 *   return sums.map((s, c) => (counts[c] > 0 ? s.map((v) => v / counts[c]) : s));
 */
function updateCentroids(X: number[][], assignments: number[], k: number): number[][] {
  // TODO: implement the centroid update
  throw new Error("TODO: implement updateCentroids()");
}

/**
 * Within-cluster sum of squared distances (the k-means objective).
 *
 * inertia = Σ_i ||x_i - c_{assignments[i]}||²
 *
 * TODO: implement.
 *   let total = 0;
 *   for (let i = 0; i < X.length; i++) total += sqDist(X[i], centroids[assignments[i]]);
 *   return total;
 */
function inertia(X: number[][], centroids: number[][], assignments: number[]): number {
  // TODO: implement the inertia
  throw new Error("TODO: implement inertia()");
}

// ---------------------------------------------------------------------------
// Data + k-means driver (provided — do not edit)
// ---------------------------------------------------------------------------

/** Ground-truth labels + a realistic 'good but imperfect' score for each item. */
function makeScores(): { scores: number[]; labels: number[] } {
  const g = makeGaussian(SEED);
  const labels: number[] = [];
  const scores: number[] = [];
  for (let i = 0; i < 50; i++) {
    labels.push(1);
    scores.push(1.0 + g()); // positives score higher on average
  }
  for (let i = 0; i < 50; i++) {
    labels.push(0);
    scores.push(-1.0 + g());
  }
  return { scores, labels };
}

/** Three well-separated 2-D Gaussian blobs. Returns points + true labels. */
function makeBlobs(): { X: number[][]; trueLabel: number[] } {
  const g = makeGaussian(SEED + 7);
  const centers = [
    [0.0, 0.0],
    [6.0, 6.0],
    [0.0, 6.0],
  ];
  const X: number[][] = [];
  const trueLabel: number[] = [];
  centers.forEach((ctr, cls) => {
    for (let i = 0; i < 60; i++) {
      X.push([ctr[0] + 0.7 * g(), ctr[1] + 0.7 * g()]);
      trueLabel.push(cls);
    }
  });
  return { X, trueLabel };
}

/**
 * Deterministic k-means++-style init (farthest-first traversal): pick a seeded
 * first centre, then each next centre is the point farthest (by squared
 * distance) from the centres chosen so far. This spreads the initial centroids
 * across the blobs and avoids the "two centres land in one blob" local optimum
 * that plain random init can fall into. Returns k distinct point indices.
 */
function chooseInit(X: number[][], k: number, seed: number): number[] {
  const rng = makeRng(seed);
  const first = Math.floor(rng() * X.length);
  const chosen = [first];
  while (chosen.length < k) {
    let bestIdx = 0;
    let bestDist = -1;
    for (let i = 0; i < X.length; i++) {
      if (chosen.includes(i)) continue;
      // distance to the NEAREST already-chosen centre
      let nearest = Infinity;
      for (const c of chosen) nearest = Math.min(nearest, sqDist(X[i], X[c]));
      if (nearest > bestDist) {
        bestDist = nearest;
        bestIdx = i;
      }
    }
    chosen.push(bestIdx);
  }
  return chosen;
}

/** Full Lloyd's algorithm using your assign/update/inertia. Provided. */
function kmeans(
  X: number[][],
  k: number,
  maxIter = 50,
  seed = SEED,
): { centroids: number[][]; assignments: number[]; history: number[] } {
  const initIdx = chooseInit(X, k, seed);
  let centroids = initIdx.map((i) => [...X[i]]);

  let assignments = assignClusters(X, centroids);
  const history = [inertia(X, centroids, assignments)];

  for (let iter = 0; iter < maxIter; iter++) {
    centroids = updateCentroids(X, assignments, k);
    const newAssign = assignClusters(X, centroids);
    history.push(inertia(X, centroids, newAssign));
    const same = newAssign.every((v, i) => v === assignments[i]);
    assignments = newAssign;
    if (same) break;
  }

  return { centroids, assignments, history };
}

// ---------------------------------------------------------------------------
// Harness (provided)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 4 — ROC/AUC and k-means from scratch\n");

  // ── PART A: ROC / AUC ──────────────────────────────────────────────────────
  console.log("=".repeat(60));
  console.log("PART A — ROC / AUC");
  console.log("=".repeat(60));

  const { scores, labels } = makeScores();

  const perfect = labels.map((l) => l); // score == label → perfect ranking
  const reversedRanker = labels.map((l) => 1 - l); // exactly wrong
  const rg = makeGaussian(SEED + 3);
  const randomRanker = labels.map(() => rg()); // unrelated to labels

  const aucOf = (s: number[]): number => {
    const { fpr, tpr } = rocCurve(s, labels);
    return auc(fpr, tpr);
  };

  const aucPerfect = aucOf(perfect);
  const aucReversed = aucOf(reversedRanker);
  const aucRandom = aucOf(randomRanker);
  const aucReal = aucOf(scores);

  console.log(`\n  AUC (perfect ranker)  = ${aucPerfect.toFixed(3)}   (expect 1.0)`);
  console.log(`  AUC (reversed ranker) = ${aucReversed.toFixed(3)}   (expect 0.0)`);
  console.log(`  AUC (random ranker)   = ${aucRandom.toFixed(3)}   (expect ≈ 0.5)`);
  console.log(
    `  AUC (realistic model) = ${aucReal.toFixed(3)}   (good separation → high)`,
  );

  const { fpr, tpr } = rocCurve(scores, labels);
  console.log(
    `\n  ROC curve has ${fpr.length} points; starts at (${fpr[0].toFixed(1)}, ${tpr[0].toFixed(1)})` +
      ` ends at (${fpr[fpr.length - 1].toFixed(1)}, ${tpr[tpr.length - 1].toFixed(1)}).`,
  );

  // ── PART B: k-means ────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(60));
  console.log("PART B — k-means (Lloyd's algorithm)");
  console.log("=".repeat(60));

  const { X, trueLabel } = makeBlobs();
  const k = 3;
  const { assignments, history } = kmeans(X, k);

  console.log(`\n  Ran k-means (k=${k}) on ${X.length} points in 3 true blobs.`);
  console.log(`  Iterations recorded: ${history.length}`);
  console.log("  Inertia over iterations:");
  history.forEach((val, i) => {
    console.log(
      `    iter ${String(i).padStart(2)}: inertia = ${val.toFixed(2).padStart(10)}`,
    );
  });

  let nonIncreasing = true;
  for (let i = 0; i < history.length - 1; i++)
    if (history[i + 1] > history[i] + 1e-6) nonIncreasing = false;

  // Cluster recovery: each TRUE blob should be dominated by one cluster id.
  const dominantIds: number[] = [];
  let recovered = 0;
  for (let cls = 0; cls < k; cls++) {
    const counts = new Array(k).fill(0);
    let total = 0;
    for (let i = 0; i < trueLabel.length; i++) {
      if (trueLabel[i] === cls) {
        counts[assignments[i]]++;
        total++;
      }
    }
    let best = 0;
    for (let j = 1; j < k; j++) if (counts[j] > counts[best]) best = j;
    dominantIds.push(best);
    if (counts[best] / total >= 0.9) recovered++;
  }
  const distinct = new Set(dominantIds).size === k;

  console.log(`\n  Inertia non-increasing every iteration: ${nonIncreasing}`);
  console.log(`  True blobs cleanly recovered (≥90% one cluster): ${recovered}/${k}`);
  console.log(
    `  Dominant cluster ids per blob: [${dominantIds}]  (distinct: ${distinct})`,
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okPerfect = Math.abs(aucPerfect - 1.0) < 1e-9;
  const okReversed = Math.abs(aucReversed - 0.0) < 1e-9;
  const okRandom = Math.abs(aucRandom - 0.5) < 0.15;
  const okNonInc = nonIncreasing;
  const okRecover = recovered === k && distinct;

  console.log(
    `  [${okPerfect ? "x" : " "}] AUC of perfect ranker == 1.0  (${aucPerfect.toFixed(3)})`,
  );
  console.log(
    `  [${okReversed ? "x" : " "}] AUC of reversed ranker == 0.0  (${aucReversed.toFixed(3)})`,
  );
  console.log(
    `  [${okRandom ? "x" : " "}] AUC of random ranker ≈ 0.5 (±0.15)  (${aucRandom.toFixed(3)})`,
  );
  console.log(
    `  [${okNonInc ? "x" : " "}] k-means inertia non-increasing each iteration`,
  );
  console.log(
    `  [${okRecover ? "x" : " "}] k-means recovers all ${k} blobs (distinct clusters)`,
  );

  if (okPerfect && okReversed && okRandom && okNonInc && okRecover) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
