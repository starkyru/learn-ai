/**
 * Task 3 🔴 — RLHF with REINFORCE, and its failure mode: reward hacking.
 *
 * What you'll learn:
 *   - The RLHF objective:  maximize  E_π[r(x)] − β·KL(π ‖ π_ref)
 *   - The policy-gradient (REINFORCE) update for a tabular softmax policy,
 *     with a baseline to cut variance
 *   - Goodhart's law in action: optimizing an IMPERFECT reward model makes the
 *     true reward rise at first... then collapse (reward hacking /
 *     overoptimization)
 *   - Why the KL penalty is the leash that prevents the collapse
 *
 * The math (README derives each step):
 *
 *   Policy: per prompt, logits z ∈ ℝ^K over K candidate responses,
 *       π_θ(k) = softmax(z)_k = e^{z_k} / Σ_j e^{z_j}
 *   Expected reward:  J(θ) = Σ_k π(k)·R(k).  Its exact gradient w.r.t. z_j is
 *       ∂J/∂z_j = π(j)·(R(j) − b) ,   baseline b = Σ_k π(k)·R(k)
 *   (this is REINFORCE in expectation — we use the exact form over the small
 *   candidate set to stay deterministic). Gradient ASCENT: z ← z + lr·∂J/∂z.
 *
 *   KL divergence:  KL(π ‖ π_ref) = Σ_k π(k) · log(π(k) / π_ref(k))
 *
 *   The KL-regularized objective  J_KL = E_π[R] − β·KL(π‖π_ref)  has exactly
 *   the same gradient as plain REINFORCE with the SHAPED reward
 *       R'(k) = R(k) − β·log(π(k)/π_ref(k))
 *   (the harness applies this shaping and calls your reinforceStep).
 *
 *   The reward model here is IMPERFECT (pre-baked from few noisy pairs, the
 *   Task 2 recipe): θ_RM = w* + error·û, with û ⊥ w*. It scores ordinary
 *   responses correctly — but each prompt has one "exploit" response pointing
 *   along û that the RM overrates even though its TRUE reward is terrible.
 *   Optimize the proxy hard enough and the policy finds it.
 *
 * You implement the three core functions (softmax, reinforceStep,
 * klDivergence) using plain arrays only (no math libraries). The toy world,
 * the imperfect RM, both optimization runs, and the side-by-side report are
 * provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/13b-alignment/ts/03-rlhf-reward-hacking.ts
 */

const SEED = 33;
const D = 6; // response feature dimension
const P = 4; // prompts
const K = 6; // candidate responses per prompt (index K-1 is the exploit)
const STEPS = 600;
const LR = 0.5;
const BETA = 3.5; // KL coefficient for run (b)

// Hidden TRUE reward direction (what humans actually want).
const W_STAR = [1.0, -0.6, 0.8, 0.4, -0.5, 0.3];

// The reward model's spurious direction (raw, orthogonalised in buildWorld).
const U_RAW = [0.5, 1.0, -0.3, 0.8, 0.9, -0.2];
const RM_ERROR_SCALE = 1.0; // how much θ_RM leans on the spurious direction û
const EXPLOIT_TRUE_COST = 1.5; // exploit's true reward is −this·‖w*‖
const EXPLOIT_PROXY_MARGIN = 0.3; // proxy edge of the exploit over the best normal

// True reward of each prompt's K-1 NORMAL candidates (provided "dataset":
// every prompt has a couple of awful drafts, mediocre ones, and good ones).
const TRUE_NORMALS = [
  [-4.0, -2.5, 0.5, 1.8, 2.3],
  [-3.5, -2.8, 0.0, 1.5, 2.6],
  [-4.2, -1.5, 0.8, 2.0, 2.4],
  [-3.8, -2.2, 0.3, 1.7, 2.2],
];

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
// Toy world: candidates, true reward, imperfect reward model
// (provided — do not edit)
// ---------------------------------------------------------------------------

/**
 * Build P prompts × K candidate "responses" (feature vectors) plus the
 * imperfect reward model θ_RM, and score everything.
 *
 * Geometry (ŵ = w* / ‖w*‖, û ⊥ ŵ unit):
 *   - θ_RM = w* + RM_ERROR_SCALE·û — right about the ŵ direction, but also
 *     rewards the spurious direction û that the true reward ignores.
 *   - Normal candidate with target true reward t:  x = (t/‖w*‖)·ŵ + noise,
 *     where the noise is orthogonal to BOTH ŵ and û — so true and proxy
 *     rewards agree exactly on normal responses (a *plausible-looking* RM).
 *   - Exploit candidate:  x = b·û − c·ŵ  with c = EXPLOIT_TRUE_COST and b
 *     solved so its proxy beats the prompt's best normal by
 *     EXPLOIT_PROXY_MARGIN, while its true reward is −c·‖w*‖ (the worst).
 *
 * Returns { trueR, proxyR }: (P×K) true rewards w*·x and RM rewards θ_RM·x.
 */
function buildWorld(): { trueR: number[][]; proxyR: number[][] } {
  const gauss = makeGaussian(SEED);
  const wNorm = norm(W_STAR);
  const wHat = W_STAR.map((v) => v / wNorm);
  const uProj = dot(U_RAW, wHat);
  const u = U_RAW.map((v, i) => v - uProj * wHat[i]); // orthogonalise against w*
  const uNorm = norm(u);
  const uHat = u.map((v) => v / uNorm);
  const thetaRm = W_STAR.map((v, i) => v + RM_ERROR_SCALE * uHat[i]);

  const X: number[][][] = [];
  for (let p = 0; p < P; p++) {
    const candidates: number[][] = [];
    for (let k = 0; k < K - 1; k++) {
      let noise = Array.from({ length: D }, () => 0.5 * gauss());
      const nw = dot(noise, wHat);
      noise = noise.map((v, i) => v - nw * wHat[i]); // keep true reward exact
      const nu = dot(noise, uHat);
      noise = noise.map((v, i) => v - nu * uHat[i]); // keep proxy reward exact
      const t = TRUE_NORMALS[p][k];
      candidates.push(noise.map((v, i) => (t / wNorm) * wHat[i] + v));
    }
    const maxNormalProxy = Math.max(...candidates.map((x) => dot(x, thetaRm)));
    // Solve θ_RM·(b·û − c·ŵ) = maxNormalProxy + margin for b, using
    // θ_RM·û = RM_ERROR_SCALE and θ_RM·ŵ = ‖w*‖ (since û ⊥ ŵ).
    const c = EXPLOIT_TRUE_COST;
    const b = (maxNormalProxy + EXPLOIT_PROXY_MARGIN + c * wNorm) / RM_ERROR_SCALE;
    candidates.push(uHat.map((v, i) => b * v - c * wHat[i]));
    X.push(candidates);
  }

  const trueR = X.map((prompt) => prompt.map((x) => dot(x, W_STAR)));
  const proxyR = X.map((prompt) => prompt.map((x) => dot(x, thetaRm)));
  return { trueR, proxyR };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Row-wise stable softmax. `logits` is P×K; return P×K with each row
 * summing to 1.
 *
 * Numerical stability: subtract each row's max before exponentiating
 * (softmax is shift-invariant, so the result is unchanged).
 *
 * TODO: implement.
 *   - For each row: shift by its max, exponentiate, divide by the row sum.
 */
function softmax(logits: number[][]): number[][] {
  // TODO: per row — shift by max, exponentiate, normalise
  throw new Error("TODO: implement softmax()");
}

/**
 * One exact policy-gradient ASCENT step on E_π[R], per prompt.
 *
 *   π = softmax(logits)                        row-wise, shape P×K
 *   baseline b_p = Σ_k π_p(k)·R_p(k)           expected reward per prompt
 *   gradient ∂J/∂z_{p,j} = π_p(j)·(R_p(j) − b_p)
 *   update:  zNew = z + lr·∂J/∂z               (ascent — we maximize J)
 *
 * The baseline is what makes this "REINFORCE with a baseline": it doesn't
 * change the expected gradient but centres the reward signal.
 *
 * Return the UPDATED logits as a NEW P×K array (do not mutate the input —
 * the loop reassigns logits = reinforceStep(...)).
 *
 * TODO: implement.
 *   - Get π via your softmax.
 *   - Compute each prompt's baseline as the π-weighted mean of its rewards.
 *   - Assemble the gradient per the formula and return the stepped logits
 *     (note the PLUS sign — gradient ascent).
 */
function reinforceStep(
  logits: number[][],
  rewards: number[][],
  lr: number,
): number[][] {
  // TODO: policy gradient with a baseline, then one ASCENT step
  throw new Error("TODO: implement reinforceStep()");
}

/**
 * Mean KL divergence over prompts:
 *
 *     KL(π ‖ π_ref) = Σ_k π(k) · log(π(k) / π_ref(k))
 *
 * `pi` and `piRef` are P×K; compute the KL of each row, then return the
 * mean over the P prompts. Clamp both distributions to at least 1e-12
 * before the log so 0·log(0) doesn't produce NaN.
 *
 * TODO: implement.
 *   - Per row: clamp, take the log-ratio, weight by π, sum over k.
 *   - Average the P row KLs.
 */
function klDivergence(pi: number[][], piRef: number[][]): number {
  // TODO: Σ π·log(π/π_ref) per row, then mean over prompts
  throw new Error("TODO: implement klDivergence()");
}

// ---------------------------------------------------------------------------
// Optimization runs  (provided — do not edit; uses your three functions)
// ---------------------------------------------------------------------------

type Trajectory = { true: number[]; proxy: number[]; kl: number[]; pExploit: number[] };

/**
 * Run `steps` of policy-gradient ascent on the proxy reward, optionally
 * KL-regularized (beta > 0), starting from the reference policy (logits 0).
 *
 * The KL penalty enters through reward shaping:
 *     R'(k) = proxy(k) − β·log(π(k)/π_ref(k))
 * which gives exactly the gradient of  E_π[proxy] − β·KL(π‖π_ref).
 *
 * Tracks expected true reward, expected proxy reward, KL, and the mean
 * probability of the exploit response over time (steps+1 entries each).
 */
function optimize(
  proxyR: number[][],
  trueR: number[][],
  piRef: number[][],
  beta: number,
  steps: number,
  lr: number,
): Trajectory {
  let logits: number[][] = Array.from(
    { length: P },
    () => new Array(K).fill(0) as number[],
  );
  const traj: Trajectory = { true: [], proxy: [], kl: [], pExploit: [] };

  const record = (): number[][] => {
    const pi = softmax(logits);
    const expOver = (R: number[][]) =>
      pi.reduce((acc, row, p) => acc + row.reduce((a, v, k) => a + v * R[p][k], 0), 0) /
      P;
    traj.true.push(expOver(trueR));
    traj.proxy.push(expOver(proxyR));
    traj.kl.push(klDivergence(pi, piRef));
    traj.pExploit.push(pi.reduce((acc, row) => acc + row[K - 1], 0) / P);
    return pi;
  };

  for (let t = 0; t < steps; t++) {
    const pi = record();
    const shaped = proxyR.map((row, p) =>
      row.map((r, k) => r - beta * Math.log(Math.max(pi[p][k], 1e-12) / piRef[p][k])),
    );
    logits = reinforceStep(logits, shaped, lr);
  }
  record();
  return traj;
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

function fmt(v: number, digits = 2): string {
  return (v >= 0 ? "+" : "") + v.toFixed(digits);
}

function main(): void {
  console.log("Task 3 — RLHF (REINFORCE) and reward hacking\n");

  const { trueR, proxyR } = buildWorld();
  const piRef: number[][] = Array.from(
    { length: P },
    () => new Array(K).fill(1 / K) as number[],
  );
  console.log(`  World: ${P} prompts x ${K} candidates (feature dim ${D})`);
  console.log(`  Exploit candidate (index ${K - 1}) per prompt:`);
  for (let p = 0; p < P; p++) {
    const bestNormalProxy = Math.max(...proxyR[p].slice(0, K - 1));
    const bestNormalTrue = Math.max(...trueR[p].slice(0, K - 1));
    console.log(
      `    prompt ${p}: proxy ${fmt(proxyR[p][K - 1])} (best normal ${fmt(bestNormalProxy)})` +
        `   true ${fmt(trueR[p][K - 1])} (best normal ${fmt(bestNormalTrue)})`,
    );
  }

  console.log("\n[1/2] Run (a): maximize proxy reward, NO KL penalty...");
  const a = optimize(proxyR, trueR, piRef, 0.0, STEPS, LR);
  console.log(`[2/2] Run (b): maximize proxy − β·KL(π‖π_ref),  β = ${BETA} ...`);
  const b = optimize(proxyR, trueR, piRef, BETA, STEPS, LR);

  console.log(
    "\n  step | (a) proxy   true  P(exploit) | (b) proxy   true  P(exploit)   KL",
  );
  for (const t of [0, 5, 10, 25, 50, 100, 300, STEPS]) {
    console.log(
      `  ${String(t).padStart(4)} |   ${fmt(a.proxy[t])}  ${fmt(a.true[t])}     ${a.pExploit[t].toFixed(3)}` +
        `   |   ${fmt(b.proxy[t])}  ${fmt(b.true[t])}     ${b.pExploit[t].toFixed(3)}    ${b.kl[t].toFixed(3)}`,
    );
  }

  const aPeakTrue = Math.max(...a.true);
  const aPeakStep = a.true.indexOf(aPeakTrue);
  const bPeakTrue = Math.max(...b.true);
  const aFinalTrue = a.true[a.true.length - 1];
  const bFinalTrue = b.true[b.true.length - 1];
  const aFinalProxy = a.proxy[a.proxy.length - 1];
  const aFinalExploit = a.pExploit[a.pExploit.length - 1];
  const bFinalExploit = b.pExploit[b.pExploit.length - 1];
  const bFinalKl = b.kl[b.kl.length - 1];
  console.log(
    `\n  (a) true reward: start ${fmt(a.true[0], 3)} → peak ${fmt(aPeakTrue, 3)} ` +
      `(step ${aPeakStep}) → final ${fmt(aFinalTrue, 3)}   ← Goodhart collapse`,
  );
  console.log(`  (a) final P(exploit) = ${aFinalExploit.toFixed(3)}`);
  console.log(
    `  (b) true reward: peak ${fmt(bPeakTrue, 3)} → final ${fmt(bFinalTrue, 3)}   ` +
      `(KL = ${bFinalKl.toFixed(3)}, P(exploit) = ${bFinalExploit.toFixed(3)})`,
  );

  // ── Acceptance checks ────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okAHack =
    aFinalTrue < aPeakTrue - 0.5 && aFinalProxy >= Math.max(...a.proxy) - 1e-6;
  const okAExploit = aFinalExploit > 0.9;
  const okBTrue = bFinalTrue >= 0.9 * bPeakTrue;
  const okBKl = bFinalKl < 1.0;
  const okBExploit = bFinalExploit < 0.3;
  console.log(
    `  [${okAHack ? "x" : " "}] (a) proxy at max but true reward collapsed below its peak ` +
      `(${fmt(aFinalTrue)} < ${fmt(aPeakTrue)} − 0.5)`,
  );
  console.log(
    `  [${okAExploit ? "x" : " "}] (a) policy concentrated on the exploit: ` +
      `P(exploit) = ${aFinalExploit.toFixed(3)} > 0.9`,
  );
  console.log(
    `  [${okBTrue ? "x" : " "}] (b) KL leash keeps true reward ≥ 0.9× its peak ` +
      `(${fmt(bFinalTrue)} vs peak ${fmt(bPeakTrue)})`,
  );
  console.log(
    `  [${okBKl ? "x" : " "}] (b) KL(π‖π_ref) stays below 1.0  (KL = ${bFinalKl.toFixed(3)})`,
  );
  console.log(
    `  [${okBExploit ? "x" : " "}] (b) exploit stays rare: P(exploit) = ${bFinalExploit.toFixed(3)} < 0.3`,
  );

  if (okAHack && okAExploit && okBTrue && okBKl && okBExploit) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
