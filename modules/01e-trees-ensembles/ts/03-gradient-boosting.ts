/**
 * Task 3 🔴 — Gradient boosting (least squares) with decision stumps.
 *
 * What you'll learn:
 *   - Boosting = building a strong model as a SUM of weak ones, each trained
 *     to fix what the running sum still gets wrong.
 *   - For squared-error loss the "what's still wrong" is literally the
 *     residual y - F(x) — and the residual IS the negative gradient of the
 *     loss w.r.t. the model's outputs. Boosting is gradient descent in
 *     function space.
 *   - The learning rate (shrinkage) ν: smaller steps, more rounds, better
 *     generalisation.
 *   - Early stopping: train MSE falls forever, validation MSE traces a
 *     U-curve — you stop at its bottom.
 *
 * The math (README derives each step):
 *
 *   Model after m rounds:      F_m(x) = F_0 + ν · Σ_{k=1..m} h_k(x),  F_0 = ȳ
 *   Squared-error loss:        L = ½ Σ_i (y_i - F(x_i))²
 *   Its negative gradient:     -∂L/∂F(x_i) = y_i - F(x_i)   ← the residual!
 *   Each round:                h_m = fitStump(x, y - F_{m-1});
 *                              F_m = F_{m-1} + ν·h_m
 *
 *   A regression STUMP is the weakest tree: one threshold t, two leaf
 *   values —
 *       h(x) = mean(r | x ≤ t)  if x ≤ t   else   mean(r | x > t)
 *   The best t minimises the two-sided SSE:
 *       SSE(t) = Σ_{x≤t} (r - meanLeft)² + Σ_{x>t} (r - meanRight)²
 *
 * You implement: fitStump and boost (including recording per-round train/val
 * MSE and picking the best round by validation MSE — early stopping). The
 * noisy 1-D sinusoid data, stumpPredict, the truncated-model predictor, and
 * the harness are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01e-trees-ensembles/ts/03-gradient-boosting.ts
 */

const SEED = 33;
const N_TRAIN = 80;
const N_VAL = 150;
const NOISE_STD = 0.35;
const N_ROUNDS = 500;
const LR = 0.3; // shrinkage ν

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
// Synthetic data + stump evaluation (provided — do not edit)
// ---------------------------------------------------------------------------

/** A stump: one threshold, two leaf values. */
type Stump = { threshold: number; leftValue: number; rightValue: number };

/**
 * 1-D regression:  y = sin(2x) + ε,  x uniform in [-3, 3],  ε ~ N(0, 0.35²).
 * A small train set (80 points) so that enough boosting rounds visibly
 * overfit.
 */
function makeData(): {
  xTrain: number[];
  yTrain: number[];
  xVal: number[];
  yVal: number[];
} {
  const u = makeRng(SEED);
  const g = makeGaussian(SEED + 99);
  const x = Array.from({ length: N_TRAIN + N_VAL }, () => -3 + 6 * u());
  const y = x.map((xi) => Math.sin(2 * xi) + NOISE_STD * g());
  return {
    xTrain: x.slice(0, N_TRAIN),
    yTrain: y.slice(0, N_TRAIN),
    xVal: x.slice(N_TRAIN),
    yVal: y.slice(N_TRAIN),
  };
}

/** Evaluate a stump on every point: leftValue where x ≤ threshold, else rightValue. */
function stumpPredict(stump: Stump, x: number[]): number[] {
  return x.map((xi) => (xi <= stump.threshold ? stump.leftValue : stump.rightValue));
}

/** Evaluate the boosted model truncated at n rounds: F0 + lr·Σ_{k<n} h_k(x). */
function boostedPredict(
  f0: number,
  stumps: Stump[],
  x: number[],
  lr: number,
  n: number,
): number[] {
  const F = x.map(() => f0);
  for (let k = 0; k < n; k++) {
    const h = stumpPredict(stumps[k], x);
    for (let i = 0; i < F.length; i++) F[i] += lr * h[i];
  }
  return F;
}

function mse(pred: number[], y: number[]): number {
  let sum = 0;
  for (let i = 0; i < y.length; i++) sum += (pred[i] - y[i]) ** 2;
  return sum / y.length;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these two
// ---------------------------------------------------------------------------

/**
 * Fit the best single-threshold regression stump to (x, residuals).
 *
 * Candidate thresholds = midpoints between consecutive sorted unique x
 * values. For each threshold t the two leaf values are the MEANS of the
 * residuals on each side (the SSE-optimal constant per side); the stump's
 * score is the summed SSE of both sides. Return the argmin.
 *
 * Returns: { threshold, leftValue, rightValue }.
 *
 * TODO: implement.
 *   1. Sort the unique x values; midpoints of consecutive pairs are the
 *      candidate thresholds.
 *   2. For each t: gather the residuals with x ≤ t and those with x > t,
 *      take each side's mean, and score the split by the two-sided SSE
 *      formula above (midpoints of unique values never empty a side).
 *   3. Track the best { threshold, leftValue, rightValue } and return it.
 */
function fitStump(x: number[], residuals: number[]): Stump {
  // TODO: implement the stump search
  throw new Error("TODO: implement fitStump()");
}

/**
 * Least-squares gradient boosting with stumps + early-stopping pick.
 *
 * Algorithm:
 *   F0 = mean of y (the best constant); running predictions fTrain, fVal
 *   start there. Each round:
 *     1. residuals = y - fTrain          (the negative gradient!)
 *     2. h = fitStump(x, residuals)
 *     3. fTrain += lr · h(x);  fVal += lr · h(xVal)   (stumpPredict)
 *     4. record mse(fTrain, y) and mse(fVal, yVal)
 *   After the loop, the BEST round = the 1-based index of the smallest
 *   recorded validation MSE — that's where early stopping would halt.
 *
 * Returns: { f0, stumps, trainMse, valMse, bestRound }
 *   f0        : number — the initial constant prediction
 *   stumps    : Stump[] of length nRounds
 *   trainMse  : number[] of length nRounds (after each round)
 *   valMse    : number[] of length nRounds
 *   bestRound : number in [1, nRounds] — argmin of valMse, 1-based
 *
 * TODO: implement (follow the numbered algorithm above).
 */
function boost(
  x: number[],
  y: number[],
  xVal: number[],
  yVal: number[],
  nRounds: number,
  lr: number,
): {
  f0: number;
  stumps: Stump[];
  trainMse: number[];
  valMse: number[];
  bestRound: number;
} {
  // TODO: implement the boosting loop + early-stopping pick
  throw new Error("TODO: implement boost()");
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 3 — Gradient boosting (least squares) with stumps\n");

  const { xTrain, yTrain, xVal, yVal } = makeData();
  console.log(
    `  Data: y = sin(2x) + N(0, ${NOISE_STD}²), ${N_TRAIN} train / ${N_VAL} val\n`,
  );

  // ── Baseline: one lonely stump ─────────────────────────────────────────────
  console.log("[1/2] Baseline: a single stump fit to y...");
  const lone = fitStump(xTrain, yTrain);
  const loneVal = mse(stumpPredict(lone, xVal), yVal);
  console.log(
    `  stump: threshold = ${lone.threshold.toFixed(3)}, ` +
      `leaves = (${lone.leftValue.toFixed(3)}, ${lone.rightValue.toFixed(3)})`,
  );
  console.log(`  val MSE = ${loneVal.toFixed(4)}\n`);

  // ── Boosting ───────────────────────────────────────────────────────────────
  console.log(`[2/2] Boosting: ${N_ROUNDS} rounds, lr = ${LR}...`);
  const { f0, stumps, trainMse, valMse, bestRound } = boost(
    xTrain,
    yTrain,
    xVal,
    yVal,
    N_ROUNDS,
    LR,
  );
  console.log(`  F0 (mean of y) = ${f0.toFixed(4)}`);
  for (const r of [1, 5, 20, 50, 100, bestRound, N_ROUNDS]) {
    console.log(
      `  round ${String(r).padStart(4)}: train MSE = ${trainMse[r - 1].toFixed(4)}   ` +
        `val MSE = ${valMse[r - 1].toFixed(4)}`,
    );
  }

  const bestVal = valMse[bestRound - 1];
  const finalVal = valMse[valMse.length - 1];
  const boostedBest = mse(boostedPredict(f0, stumps, xVal, LR, bestRound), yVal);
  let monotone = true;
  for (let i = 0; i < trainMse.length - 1; i++) {
    if (trainMse[i + 1] > trainMse[i] + 1e-9) monotone = false;
  }
  console.log(
    `\n  best round (early stop) = ${bestRound}  (val MSE = ${bestVal.toFixed(4)})`,
  );
  console.log(
    `  final round val MSE     = ${finalVal.toFixed(4)}  (the U-curve turned back up)`,
  );
  console.log(`  train MSE non-increasing = ${monotone}`);

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okMonotone = monotone;
  const okUcurve = bestRound < N_ROUNDS && finalVal > bestVal + 1e-6;
  const okBeatsStump = boostedBest < 0.5 * loneVal;
  console.log(`  [${okMonotone ? "x" : " "}] train MSE non-increasing over all rounds`);
  console.log(
    `  [${okUcurve ? "x" : " "}] val MSE bottoms out BEFORE the last round ` +
      `(round ${bestRound} < ${N_ROUNDS}; U-curve visible)`,
  );
  console.log(
    `  [${okBeatsStump ? "x" : " "}] boosted val MSE ≪ single-stump val MSE ` +
      `(${boostedBest.toFixed(4)} < 0.5 × ${loneVal.toFixed(4)})`,
  );

  if (okMonotone && okUcurve && okBeatsStump) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
