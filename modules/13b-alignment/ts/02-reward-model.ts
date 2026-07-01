/**
 * Task 2 🟡 — Reward model from preferences (Bradley–Terry).
 *
 * What you'll learn:
 *   - The Bradley–Terry model: turning "chosen ≻ rejected" pairs into a
 *     probabilistic training signal
 *   - The reward-modeling loss used by InstructGPT: −log σ(r_chosen − r_rejected)
 *   - Why maximum likelihood on noisy preferences recovers the hidden reward
 *     (direction) — the exact recipe behind every RLHF reward model
 *
 * The math (README derives each step):
 *
 *   Responses are feature vectors x ∈ ℝ^D. A hidden true reward scores them:
 *       r*(x) = w* · x
 *   Preference data: for a pair (x_a, x_b), the label "a chosen" is sampled with
 *       P(a ≻ b) = σ(r*(x_a) − r*(x_b))          (Bradley–Terry)
 *   We fit a linear reward model  r_θ(x) = θ · x  by minimising, over pairs,
 *       L(θ) = −mean log σ(Δ) ,   Δ = r_θ(x_chosen) − r_θ(x_rejected)
 *   Gradient (derive it: d/dΔ [−log σ(Δ)] = −(1 − σ(Δ)), then chain to θ):
 *       ∂L/∂θ = −mean (1 − σ(Δ)) · (x_chosen − x_rejected)
 *
 * You implement the three core functions (btProb, btLoss, btGradStep) using
 * plain arrays only (no math libraries). Data generation, the train/held-out
 * split, the training loop, and the evaluation report are provided and
 * runnable.
 *
 * How to run:
 *   pnpm tsx modules/13b-alignment/ts/02-reward-model.ts
 */

const SEED = 21;
const D = 6; // response feature dimension
const N_TRAIN = 400; // preference pairs for training
const N_TEST = 200; // held-out preference pairs
const LR = 0.2;
const EPOCHS = 200;

// The hidden "true" reward direction the annotators (noisily) follow.
const W_TRUE = [3.0, -4.0, 2.0, 1.2, -2.4, 1.6];

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

function makeGaussianFrom(u: () => number): () => number {
  return () => {
    // Box-Muller: two uniforms → one standard normal
    const u1 = u() + 1e-12;
    const u2 = u();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Small vector helpers (provided)
// ---------------------------------------------------------------------------

/** Dot product a·b. */
function dot(a: number[], b: number[]): number {
  return a.reduce((acc, v, i) => acc + v * b[i], 0);
}

/** Euclidean norm ‖a‖. */
function norm(a: number[]): number {
  return Math.sqrt(dot(a, a));
}

// ---------------------------------------------------------------------------
// Preference-pair generation  (provided — do not edit)
// ---------------------------------------------------------------------------

/**
 * Generate n preference pairs. Each pair draws two random "responses"
 * xA, xB ~ N(0, I_D); the winner is sampled from the Bradley–Terry
 * probability under the TRUE reward — so labels contain realistic noise
 * (the better response usually wins, not always).
 *
 * Returns { Xc, Xr } (chosen / rejected), each n×D.
 */
function makePairs(
  n: number,
  uniform: () => number,
  gauss: () => number,
): { Xc: number[][]; Xr: number[][] } {
  const Xc: number[][] = [];
  const Xr: number[][] = [];
  for (let i = 0; i < n; i++) {
    const xA = Array.from({ length: D }, () => gauss());
    const xB = Array.from({ length: D }, () => gauss());
    const pA = 1 / (1 + Math.exp(-(dot(xA, W_TRUE) - dot(xB, W_TRUE))));
    if (uniform() < pA) {
      Xc.push(xA);
      Xr.push(xB);
    } else {
      Xc.push(xB);
      Xr.push(xA);
    }
  }
  return { Xc, Xr };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Bradley–Terry probability that "chosen" beats "rejected", element-wise:
 *
 *     P(chosen ≻ rejected) = σ(r_chosen − r_rejected)
 *
 * Both inputs are length-n arrays of scalar rewards; return a length-n array.
 * Clamp the exponent argument to [-500, 500] to avoid overflow.
 *
 * TODO: implement.
 *   - Form each reward gap, clamp it, and push it through the sigmoid
 *     σ(z) = 1 / (1 + e^{-z}).
 */
function btProb(rChosen: number[], rRejected: number[]): number[] {
  // TODO: sigmoid of each clamped reward gap
  throw new Error("TODO: implement btProb()");
}

/**
 * The reward-modeling loss (negative log-likelihood of the preferences):
 *
 *     L = −mean log σ(r_chosen − r_rejected)
 *
 * Clip each probability to [1e-12, 1 − 1e-12] before the log.
 *
 * TODO: implement.
 *   - Get the pairwise probabilities from btProb, clip each, and return the
 *     mean of the negative logs.
 */
function btLoss(rChosen: number[], rRejected: number[]): number {
  // TODO: mean negative log of the clipped btProb values
  throw new Error("TODO: implement btLoss()");
}

/**
 * One full-batch gradient-descent step on the Bradley–Terry loss for the
 * linear reward model r_θ(x) = θ·x.
 *
 *   Δ_i    = θ·xChosen_i − θ·xRejected_i               (length n)
 *   ∂L/∂θ  = −(1/n) Σ_i (1 − σ(Δ_i)) · (xChosen_i − xRejected_i)
 *   update:  θ_new = θ − lr · ∂L/∂θ
 *
 * Return the UPDATED θ as a NEW length-D array (do not mutate the input —
 * the training loop reassigns theta = btGradStep(...)).
 *
 * TODO: implement.
 *   - Compute both reward arrays with dot products, then σ(Δ) via btProb.
 *   - Accumulate the gradient: for each pair, add its feature difference
 *     (xChosen − xRejected) scaled by its (1 − σ(Δ_i)) factor; divide by n
 *     and apply the leading minus sign.
 *   - Return the stepped weights.
 */
function btGradStep(
  theta: number[],
  Xc: number[][],
  Xr: number[][],
  lr: number,
): number[] {
  // TODO: build the Bradley–Terry gradient and take one descent step
  throw new Error("TODO: implement btGradStep()");
}

// ---------------------------------------------------------------------------
// Evaluation helpers  (provided — use your bt* functions)
// ---------------------------------------------------------------------------

/** Fraction of held-out pairs where the model ranks chosen above rejected. */
function rankingAccuracy(theta: number[], Xc: number[][], Xr: number[][]): number {
  let correct = 0;
  for (let i = 0; i < Xc.length; i++) {
    if (dot(Xc[i], theta) > dot(Xr[i], theta)) correct++;
  }
  return correct / Xc.length;
}

/** Cosine similarity between two vectors. */
function cosine(a: number[], b: number[]): number {
  return dot(a, b) / (norm(a) * norm(b) + 1e-12);
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 2 — Reward model from preferences (Bradley–Terry)\n");

  const uniform = makeRng(SEED);
  const gauss = makeGaussianFrom(makeRng(SEED + 99));
  const { Xc: XcTrain, Xr: XrTrain } = makePairs(N_TRAIN, uniform, gauss);
  const { Xc: XcTest, Xr: XrTest } = makePairs(N_TEST, uniform, gauss);
  console.log(`  Pairs: ${N_TRAIN} train / ${N_TEST} held-out, D=${D}`);
  console.log(`  Hidden true reward w* = [${W_TRUE}]\n`);

  console.log("[1/2] Training the linear reward model on preference pairs...");
  let theta = new Array(D).fill(0) as number[];
  const lossHistory: number[] = [];
  for (let epoch = 0; epoch < EPOCHS; epoch++) {
    lossHistory.push(
      btLoss(
        XcTrain.map((x) => dot(x, theta)),
        XrTrain.map((x) => dot(x, theta)),
      ),
    );
    theta = btGradStep(theta, XcTrain, XrTrain, LR);
  }

  for (const e of [1, 5, 20, 60, EPOCHS]) {
    console.log(
      `  epoch ${String(e).padStart(4)}: BT loss = ${lossHistory[e - 1].toFixed(4)}`,
    );
  }

  const first30 = lossHistory.slice(0, 30);
  let monotonic = true;
  for (let i = 0; i < first30.length - 1; i++) {
    if (first30[i + 1] > first30[i] + 1e-9) monotonic = false;
  }

  console.log("\n[2/2] Evaluating the learned reward model...");
  const acc = rankingAccuracy(theta, XcTest, XrTest);
  const cos = cosine(theta, W_TRUE);
  console.log(`  learned θ = [${theta.map((t) => t.toFixed(3)).join(", ")}]`);
  console.log(`  held-out ranking accuracy = ${acc.toFixed(3)}`);
  console.log(`  cosine(θ, w*)             = ${cos.toFixed(4)}`);
  console.log(`  loss monotone (first 30)  = ${monotonic}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okAcc = acc >= 0.9;
  const okCos = cos >= 0.9;
  const okMonotone = monotonic;
  console.log(
    `  [${okAcc ? "x" : " "}] held-out ranking accuracy >= 0.9  (acc = ${acc.toFixed(3)})`,
  );
  console.log(
    `  [${okCos ? "x" : " "}] cosine(θ, w*) >= 0.9  (cos = ${cos.toFixed(4)})`,
  );
  console.log(
    `  [${okMonotone ? "x" : " "}] BT loss decreases monotonically over first 30 epochs`,
  );

  if (okAcc && okCos && okMonotone) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
