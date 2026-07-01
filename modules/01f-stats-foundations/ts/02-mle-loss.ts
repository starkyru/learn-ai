/**
 * Task 2 🟡 — Maximum likelihood, and why your loss functions ARE likelihoods.
 *
 * What you'll learn:
 *   - Maximum likelihood estimation (MLE): pick the parameters that make the
 *     observed data most probable
 *   - The closed-form MLEs for a Gaussian (μ̂ = sample mean, σ̂² = biased
 *     sample variance) and a Bernoulli (p̂ = sample mean)
 *   - The punchline every interviewer loves: minimising MSE ≡ maximising a
 *     Gaussian likelihood in μ, and minimising binary cross-entropy ≡
 *     maximising a Bernoulli likelihood. Your loss functions were MLE all along.
 *
 * The math (README derives each step):
 *
 *   Likelihood:      L(θ) = Π_i p(x_i | θ)          (i.i.d. data)
 *   Log-likelihood:  ℓ(θ) = Σ_i log p(x_i | θ)      (same argmax, no underflow)
 *   NLL:             minimise −ℓ(θ)  ⇔  maximise ℓ(θ)
 *
 *   Gaussian per-point NLL:   ½·log(2πσ²) + (x − μ)² / (2σ²)
 *     ∂/∂μ = 0  →  μ̂ = (1/N) Σ x_i          (the mean!)
 *     ∂/∂σ² = 0 →  σ̂² = (1/N) Σ (x_i − μ̂)²  (biased MLE variance: divide by N)
 *
 *   Bernoulli per-point NLL:  −[ x·log p + (1 − x)·log(1 − p) ]   ← literally BCE
 *     ∂/∂p = 0  →  p̂ = (1/N) Σ x_i           (the fraction of 1s)
 *
 * You implement gaussianMle, bernoulliMle, nllGaussian, nllBernoulli.
 * The data, the grid searches, the MSE/BCE curves, and the report are provided.
 *
 * How to run:
 *   pnpm tsx modules/01f-stats-foundations/ts/02-mle-loss.ts
 */

const SEED = 11;
const N = 400;
const MU_TRUE = 2.5;
const SIGMA_TRUE = 1.2;
const P_TRUE = 0.3;

const MU_GRID_STEP = 0.01;
const P_GRID_STEP = 0.005;

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
// Synthetic data (provided — do not edit)
// ---------------------------------------------------------------------------

function makeData(): { xGauss: number[]; xBern: number[] } {
  const g = makeGaussian(SEED);
  const xGauss = Array.from({ length: N }, () => MU_TRUE + SIGMA_TRUE * g());
  const u = makeRng(SEED + 99);
  const xBern = Array.from({ length: N }, () => (u() < P_TRUE ? 1 : 0));
  return { xGauss, xBern };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Closed-form Gaussian MLE.
 *
 * Returns { mu, sigma2 }:
 *   mu     = sample mean
 *   sigma2 = BIASED MLE variance — mean of squared deviations from mu,
 *            dividing by N (not N−1).
 *
 * TODO: implement — two simple statistics of x (a mean, then a mean of
 * squared deviations).
 */
function gaussianMle(x: number[]): { mu: number; sigma2: number } {
  // TODO: return { mu, sigma2 } — biased variance, divide by N
  throw new Error("TODO: implement gaussianMle()");
}

/**
 * Closed-form Bernoulli MLE: p̂ = the fraction of 1s in x.
 *
 * TODO: implement — one statistic of x.
 */
function bernoulliMle(x: number[]): number {
  // TODO: return the Bernoulli MLE
  throw new Error("TODO: implement bernoulliMle()");
}

/**
 * Average Gaussian negative log-likelihood of x under N(mu, sigma²):
 *
 *   NLL(μ, σ) = (1/N) Σ_i [ ½·log(2πσ²) + (x_i − μ)² / (2σ²) ]
 *
 * TODO: implement.
 *   - Sum the per-point NLL per the formula (Math.log, Math.PI) and divide
 *     by the number of points.
 */
function nllGaussian(x: number[], mu: number, sigma: number): number {
  // TODO: implement the average Gaussian NLL
  throw new Error("TODO: implement nllGaussian()");
}

/**
 * Average Bernoulli negative log-likelihood of the 0/1 array x under
 * Bernoulli(p):
 *
 *   NLL(p) = −(1/N) Σ_i [ x_i·log(p) + (1 − x_i)·log(1 − p) ]
 *
 * (Look closely: this is binary cross-entropy with x as the targets.)
 *
 * TODO: implement.
 *   - Sum the per-point term per the formula, negate, divide by the number
 *     of points. Assume 0 < p < 1 (the grid never touches 0 or 1).
 */
function nllBernoulli(x: number[], p: number): number {
  // TODO: implement the average Bernoulli NLL (a.k.a. BCE)
  throw new Error("TODO: implement nllBernoulli()");
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function argmin(values: number[]): number {
  let best = 0;
  for (let i = 1; i < values.length; i++) if (values[i] < values[best]) best = i;
  return best;
}

function makeGrid(start: number, stop: number, step: number): number[] {
  const grid: number[] = [];
  for (let v = start; v <= stop + 1e-9; v += step) grid.push(v);
  return grid;
}

function main(): void {
  console.log("Task 2 — Maximum likelihood and the loss-function connection\n");

  const { xGauss, xBern } = makeData();
  console.log(`  Data: ${N} Gaussian draws (true μ=${MU_TRUE}, σ=${SIGMA_TRUE}),`);
  console.log(`        ${N} Bernoulli draws (true p=${P_TRUE})\n`);

  // ── Closed-form MLEs ───────────────────────────────────────────────────────
  console.log("[1/3] Closed-form MLEs...");
  const { mu: muHat, sigma2: sigma2Hat } = gaussianMle(xGauss);
  const sigmaHat = Math.sqrt(sigma2Hat);
  const pHat = bernoulliMle(xBern);
  console.log(
    `  Gaussian : μ̂ = ${muHat.toFixed(4)}   σ̂² = ${sigma2Hat.toFixed(4)}  (σ̂ = ${sigmaHat.toFixed(4)})`,
  );
  console.log(`  Bernoulli: p̂ = ${pHat.toFixed(4)}\n`);

  // ── Grid search: does the NLL argmin land on the closed form? ──────────────
  console.log("[2/3] Grid-searching each NLL...");
  const muGrid = makeGrid(1.5, 3.5, MU_GRID_STEP);
  const nllMu = muGrid.map((m) => nllGaussian(xGauss, m, sigmaHat));
  const iNllMu = argmin(nllMu);
  console.log(`  Gaussian NLL over μ-grid [1.5, 3.5] (step ${MU_GRID_STEP}):`);
  console.log(
    `    argmin μ = ${muGrid[iNllMu].toFixed(4)}   (closed-form μ̂ = ${muHat.toFixed(4)})`,
  );

  const pGrid = makeGrid(0.01, 0.99, P_GRID_STEP);
  const nllP = pGrid.map((p) => nllBernoulli(xBern, p));
  const iNllP = argmin(nllP);
  console.log(`  Bernoulli NLL over p-grid [0.01, 0.99] (step ${P_GRID_STEP}):`);
  console.log(
    `    argmin p = ${pGrid[iNllP].toFixed(4)}   (closed-form p̂ = ${pHat.toFixed(4)})\n`,
  );

  // ── The punchline: MSE and BCE are the same curves ─────────────────────────
  console.log("[3/3] The loss-function connection...");
  // MSE as a function of μ, on the SAME data:
  const mseMu = muGrid.map(
    (m) => xGauss.reduce((acc, xi) => acc + (xi - m) ** 2, 0) / xGauss.length,
  );
  const iMse = argmin(mseMu);
  // BCE as a function of p (targets = the Bernoulli data), on the SAME data:
  const bceP = pGrid.map(
    (p) =>
      -xBern.reduce(
        (acc, xi) => acc + xi * Math.log(p) + (1 - xi) * Math.log(1 - p),
        0,
      ) / xBern.length,
  );
  const iBce = argmin(bceP);

  console.log(
    `  MSE(μ) argmin      = ${muGrid[iMse].toFixed(4)}   vs Gaussian-NLL argmin  = ${muGrid[iNllMu].toFixed(4)}`,
  );
  console.log(
    `  BCE(p) argmin      = ${pGrid[iBce].toFixed(4)}   vs Bernoulli-NLL argmin = ${pGrid[iNllP].toFixed(4)}`,
  );
  console.log("  → Minimising MSE in μ IS maximising a Gaussian likelihood;");
  console.log(
    "    minimising binary cross-entropy IS maximising a Bernoulli likelihood.",
  );
  console.log(
    "    (Gaussian NLL = MSE/(2σ²) + const; Bernoulli NLL = BCE, identically.)",
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okGridMu = Math.abs(muGrid[iNllMu] - muHat) <= MU_GRID_STEP + 1e-9;
  const okGridP = Math.abs(pGrid[iNllP] - pHat) <= P_GRID_STEP + 1e-9;
  const okMse = iMse === iNllMu;
  const okBce = iBce === iNllP;
  console.log(
    `  [${okGridMu ? "x" : " "}] Gaussian NLL grid-argmin within one grid step of closed-form μ̂`,
  );
  console.log(
    `  [${okGridP ? "x" : " "}] Bernoulli NLL grid-argmin within one grid step of closed-form p̂`,
  );
  console.log(
    `  [${okMse ? "x" : " "}] MSE argmin == Gaussian-NLL argmin (same grid index)`,
  );
  console.log(
    `  [${okBce ? "x" : " "}] BCE argmin == Bernoulli-NLL argmin (same grid index)`,
  );

  if (okGridMu && okGridP && okMse && okBce) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
