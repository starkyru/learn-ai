/**
 * Task 4 🔴 — DPO (Direct Preference Optimization) from scratch.
 *
 * What you'll learn:
 *   - Why the RLHF objective has a CLOSED-FORM optimal policy, and how
 *     inverting it turns the policy itself into an implicit reward model
 *   - The DPO loss: Bradley–Terry on implicit rewards β·log(π_θ/π_ref) — no
 *     reward model, no RL loop, just a classification-style loss
 *   - The exact gradient of the DPO loss for a tabular softmax policy,
 *     verified against finite differences
 *
 * The math (README derives each step):
 *
 *   RLHF objective:   max_π  E_π[r(y)] − β·KL(π ‖ π_ref)
 *   Closed-form optimum:      π*(y) ∝ π_ref(y) · exp(r(y)/β)
 *   Invert for the reward:    r(y) = β·log(π*(y)/π_ref(y)) + const
 *   Substitute into Bradley–Terry for a pair (y_w chosen, y_l rejected) — the
 *   const cancels — and you get the DPO loss:
 *
 *     m = β·[ (log π_θ(y_w) − log π_ref(y_w)) − (log π_θ(y_l) − log π_ref(y_l)) ]
 *     L = −log σ(m)
 *
 *   Gradient w.r.t. the tabular logits z (π = softmax(z)):
 *     dL/dm = −(1 − σ(m))
 *     ∂log π(y)/∂z_j = 1[j = y] − π(j)          (softmax log-prob gradient)
 *     chain the two through m. (You may notice the −π(j) terms cancel between
 *     the y_w and y_l branches — that's real, and the provided
 *     finite-difference grad check will confirm your formula either way.)
 *
 * You implement the two core functions (dpoLoss, dpoGrad) using plain arrays
 * only (no math libraries). The toy world, the preference sampling, the grad
 * check, the training loop, and the report are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/13b-alignment/ts/04-dpo.ts
 */

const SEED = 44;
const P = 4; // prompts
const K = 6; // candidate responses per prompt
const N_PAIRS = 30; // preference pairs per prompt
const BETA = 0.5; // DPO β (implicit-reward temperature)
const LR = 0.5;
const EPOCHS = 500;

// True reward of each candidate (what the annotators noisily follow).
const TRUE_R = [
  [-1.8, -0.6, 0.2, 0.9, 1.6, -1.1],
  [0.4, -1.5, 1.2, -0.3, 2.0, -0.8],
  [-0.5, 1.8, -1.2, 0.7, -2.0, 1.1],
  [1.4, -0.9, 0.3, -1.6, 0.8, 2.1],
];

// Frozen reference policy logits (slightly non-uniform, as after SFT).
const REF_LOGITS = [
  [0.2, -0.1, 0.0, 0.3, -0.2, 0.1],
  [-0.3, 0.1, 0.2, 0.0, -0.1, 0.2],
  [0.1, 0.0, -0.2, 0.2, 0.1, -0.3],
  [0.0, 0.2, -0.1, 0.1, -0.2, 0.3],
];

type Pair = { yw: number; yl: number };

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG for reproducible uniforms
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
// Provided helpers and data generation  (do not edit)
// ---------------------------------------------------------------------------

/** Stable log-softmax for one row of logits. */
function logSoftmax(logits: number[]): number[] {
  const mx = Math.max(...logits);
  const shifted = logits.map((z) => z - mx);
  const logSum = Math.log(shifted.reduce((acc, z) => acc + Math.exp(z), 0));
  return shifted.map((z) => z - logSum);
}

/** σ(z) with the argument clamped to avoid overflow. */
function sigmoid(z: number): number {
  const c = Math.max(-500, Math.min(500, z));
  return 1 / (1 + Math.exp(-c));
}

/**
 * For each prompt, sample N_PAIRS preference pairs: pick two distinct
 * candidates, then choose the winner with Bradley–Terry probability
 * σ(rTrue(i) − rTrue(j)) — noisy labels, like real annotators.
 *
 * Returns pairs[p] = list of { yw, yl } index pairs.
 */
function makePairs(rng: () => number): Pair[][] {
  const pairs: Pair[][] = [];
  for (let p = 0; p < P; p++) {
    const promptPairs: Pair[] = [];
    for (let n = 0; n < N_PAIRS; n++) {
      const i = Math.floor(rng() * K);
      let j = Math.floor(rng() * (K - 1));
      if (j >= i) j += 1;
      const pIWins = sigmoid(TRUE_R[p][i] - TRUE_R[p][j]);
      if (rng() < pIWins) promptPairs.push({ yw: i, yl: j });
      else promptPairs.push({ yw: j, yl: i });
    }
    pairs.push(promptPairs);
  }
  return pairs;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these two (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * The DPO loss for ONE preference pair, from log-probabilities.
 *
 *   m = β·[ (logpW − refLogpW) − (logpL − refLogpL) ]   (the margin)
 *   L = −log σ(m)
 *
 * Clamp σ(m) to at least 1e-12 before the log. Return L.
 *
 * TODO: implement.
 *   - Assemble the margin m from the four log-probs per the formula.
 *   - Push it through the provided sigmoid, clamp, and return the negative
 *     log.
 */
function dpoLoss(
  logpW: number,
  logpL: number,
  refLogpW: number,
  refLogpL: number,
  beta: number,
): number {
  // TODO: margin m from the four log-probs, then −log σ(m)
  throw new Error("TODO: implement dpoLoss()");
}

/**
 * Analytic gradient of the DPO loss w.r.t. ONE prompt's logits (length K).
 *
 * Steps of the derivation you should reproduce:
 *   π        = softmax(logitsRow)       (logSoftmax is provided)
 *   m        = β·[(log π(yW) − refLogp(yW)) − (log π(yL) − refLogp(yL))]
 *   dL/dm    = −(1 − σ(m))
 *   ∂log π(y)/∂z_j = 1[j = y] − π(j)
 *   ∂L/∂z_j  = dL/dm · β · (∂log π(yW)/∂z_j − ∂log π(yL)/∂z_j)
 *
 * Return the length-K gradient array. The harness's finite-difference grad
 * check will verify it numerically — if the check fails, re-derive.
 *
 * TODO: implement.
 *   - Get the row's log-probs via logSoftmax (π = their exp), compute m and
 *     dL/dm.
 *   - Build the two one-hot-minus-π vectors from the softmax log-prob
 *     gradient formula, take their difference, and scale by dL/dm·β.
 */
function dpoGrad(
  logitsRow: number[],
  refLogpRow: number[],
  yW: number,
  yL: number,
  beta: number,
): number[] {
  // TODO: chain dL/dm through the softmax log-prob gradient for both branches
  throw new Error("TODO: implement dpoGrad()");
}

// ---------------------------------------------------------------------------
// Grad check  (provided — do not edit)
// ---------------------------------------------------------------------------

/**
 * Compare your analytic dpoGrad against a central finite difference of
 * dpoLoss. Returns the max absolute deviation over the K logits.
 */
function gradCheck(
  logitsRow: number[],
  refLogpRow: number[],
  yW: number,
  yL: number,
  beta: number,
): number {
  const analytic = dpoGrad(logitsRow, refLogpRow, yW, yL, beta);
  const eps = 1e-5;
  let maxDev = 0;
  for (let j = 0; j < K; j++) {
    const vals: number[] = [];
    for (const sign of [+1, -1]) {
      const z = [...logitsRow];
      z[j] += sign * eps;
      const logp = logSoftmax(z);
      vals.push(dpoLoss(logp[yW], logp[yL], refLogpRow[yW], refLogpRow[yL], beta));
    }
    const numeric = (vals[0] - vals[1]) / (2 * eps);
    maxDev = Math.max(maxDev, Math.abs(analytic[j] - numeric));
  }
  return maxDev;
}

// ---------------------------------------------------------------------------
// Training + metrics  (provided — do not edit; uses your two functions)
// ---------------------------------------------------------------------------

type Metrics = {
  loss: number;
  pChosen: number;
  pRejected: number;
  margin: number;
  kl: number;
};

/** Mean DPO loss, P(chosen), P(rejected), implicit margin, and KL. */
function batchMetrics(
  logits: number[][],
  refLogp: number[][],
  pairs: Pair[][],
): Metrics {
  const logp = logits.map((row) => logSoftmax(row));
  const pi = logp.map((row) => row.map((v) => Math.exp(v)));
  const losses: number[] = [];
  const pW: number[] = [];
  const pL: number[] = [];
  const margins: number[] = [];
  for (let p = 0; p < P; p++) {
    for (const { yw, yl } of pairs[p]) {
      losses.push(
        dpoLoss(logp[p][yw], logp[p][yl], refLogp[p][yw], refLogp[p][yl], BETA),
      );
      pW.push(pi[p][yw]);
      pL.push(pi[p][yl]);
      margins.push(
        BETA * (logp[p][yw] - refLogp[p][yw] - (logp[p][yl] - refLogp[p][yl])),
      );
    }
  }
  const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / xs.length;
  let kl = 0;
  for (let p = 0; p < P; p++) {
    for (let k = 0; k < K; k++) kl += pi[p][k] * (logp[p][k] - refLogp[p][k]);
  }
  return {
    loss: mean(losses),
    pChosen: mean(pW),
    pRejected: mean(pL),
    margin: mean(margins),
    kl: kl / P,
  };
}

function fmt(v: number, digits = 3): string {
  return (v >= 0 ? "+" : "") + v.toFixed(digits);
}

function main(): void {
  console.log("Task 4 — DPO from scratch\n");

  const rng = makeRng(SEED);
  const pairs = makePairs(rng);
  const refLogp = REF_LOGITS.map((row) => logSoftmax(row));
  const logits = REF_LOGITS.map((row) => [...row]); // start the policy at π_ref
  console.log(
    `  World: ${P} prompts x ${K} candidates, ${N_PAIRS} preference pairs each`,
  );
  console.log(`  β = ${BETA}, lr = ${LR}, epochs = ${EPOCHS}\n`);

  // ── Grad check ───────────────────────────────────────────────────────────
  console.log("[1/2] Finite-difference grad check on your dpoGrad...");
  const dev = gradCheck([0.5, -0.3, 0.1, 0.8, -0.6, 0.2], refLogp[0], 3, 1, BETA);
  console.log(`  max |analytic − numeric| = ${dev.toExponential(2)}`);

  // ── Training ─────────────────────────────────────────────────────────────
  console.log("\n[2/2] Training the policy with DPO (full-batch gradient descent)...");
  console.log("  epoch |   loss  P(chosen)  P(rejected)  margin     KL");
  const history: Metrics[] = [];
  const printAt = new Set([0, 5, 10, 25, 50, 100, 300, EPOCHS]);
  for (let epoch = 0; epoch <= EPOCHS; epoch++) {
    const metrics = batchMetrics(logits, refLogp, pairs);
    history.push(metrics);
    if (printAt.has(epoch)) {
      console.log(
        `  ${String(epoch).padStart(5)} | ${metrics.loss.toFixed(4)}    ${metrics.pChosen.toFixed(3)}` +
          `       ${metrics.pRejected.toFixed(3)}     ${fmt(metrics.margin)}  ${metrics.kl.toFixed(3)}`,
      );
    }
    if (epoch === EPOCHS) break;
    for (let p = 0; p < P; p++) {
      const grad = new Array(K).fill(0) as number[];
      for (const { yw, yl } of pairs[p]) {
        const g = dpoGrad(logits[p], refLogp[p], yw, yl, BETA);
        for (let j = 0; j < K; j++) grad[j] += g[j];
      }
      for (let j = 0; j < K; j++) logits[p][j] -= (LR * grad[j]) / pairs[p].length;
    }
  }

  const final = history[history.length - 1];
  const losses = history.map((h) => h.loss);
  const first20 = losses.slice(0, 20);
  let monotone = true;
  for (let i = 0; i < first20.length - 1; i++) {
    if (first20[i + 1] > first20[i] + 1e-9) monotone = false;
  }
  const gap = final.pChosen - final.pRejected;
  const marginGrew = final.margin > history[0].margin;

  console.log(
    `\n  final: P(chosen) = ${final.pChosen.toFixed(3)}, P(rejected) = ${final.pRejected.toFixed(3)}`,
  );
  console.log(
    `  implicit reward margin β·Δlog(π/π_ref): ${fmt(history[0].margin)} → ${fmt(final.margin)}`,
  );
  console.log(`  KL(π‖π_ref) = ${final.kl.toFixed(3)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okGrad = dev < 1e-5;
  const okGap = gap > 0.2;
  const okMonotone = monotone && marginGrew;
  const okKl = final.kl < 1.5;
  console.log(
    `  [${okGrad ? "x" : " "}] grad check passes  (max dev = ${dev.toExponential(2)} < 1e-5)`,
  );
  console.log(
    `  [${okGap ? "x" : " "}] mean P(chosen) beats P(rejected) by a clear margin ` +
      `(gap = ${gap.toFixed(3)} > 0.2)`,
  );
  console.log(
    `  [${okMonotone ? "x" : " "}] DPO loss monotone decreasing (first 20 epochs) ` +
      `and implicit margin grew`,
  );
  console.log(
    `  [${okKl ? "x" : " "}] KL(π‖π_ref) stays below 1.5  (KL = ${final.kl.toFixed(3)})`,
  );

  if (okGrad && okGap && okMonotone && okKl) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
