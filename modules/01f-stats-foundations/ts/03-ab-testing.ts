/**
 * Task 3 🟢 — Hypothesis testing and the A/B test.
 *
 * What you'll learn:
 *   - The sampling distribution of a proportion and the two-proportion z-test —
 *     the statistical engine behind every A/B test
 *   - What a p-value actually is (and is not): P(data this extreme | H₀ true),
 *     NOT P(H₀ true | data)
 *   - Confidence intervals for the difference in conversion rates
 *   - Type I error (α), statistical power, and why running 20 metrics on an
 *     A/A test almost guarantees a spurious "win" (multiple testing)
 *
 * The math (README derives each step):
 *
 *   Pooled proportion:  p̂ = (conv_a + conv_b) / (n_a + n_b)
 *   Pooled SE (H₀):     SE = √( p̂(1−p̂)·(1/n_a + 1/n_b) )
 *   z statistic:        z  = (p̂_b − p̂_a) / SE
 *   Two-sided p-value:  p  = 2 · (1 − Φ(|z|))          Φ = standard normal CDF
 *   Φ via erf:          Φ(z) = ½·(1 + erf(z / √2))
 *
 *   CI for the difference (unpooled SE):
 *     (p̂_b − p̂_a) ± z_crit · √( p̂_a(1−p̂_a)/n_a + p̂_b(1−p̂_b)/n_b )
 *
 * An `erf(x)` helper is PROVIDED (JS has no Math.erf). You implement
 * normalCdf, twoProportionZtest, confidenceIntervalDiff. The worked example,
 * the A/A / power simulations, and the multiple-testing demo are provided.
 *
 * How to run:
 *   pnpm tsx modules/01f-stats-foundations/ts/03-ab-testing.ts
 */

const SEED = 5;
const ALPHA = 0.05;
const Z_CRIT_95 = 1.96; // two-sided 95% critical value

const N_SIMS = 2000; // experiments per simulation batch

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
// erf helper (provided — do not edit): Abramowitz & Stegun 7.1.26,
// max absolute error 1.5e-7 — plenty for p-values.
// ---------------------------------------------------------------------------

function erf(x: number): number {
  const sign = x < 0 ? -1 : 1;
  const ax = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * ax);
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp(-ax * ax);
  return sign * y;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * Standard normal CDF Φ(z), via the provided error function:
 *
 *   Φ(z) = ½ · (1 + erf(z / √2))
 *
 * TODO: implement — one line with erf() and Math.sqrt.
 */
function normalCdf(z: number): number {
  // TODO: implement the standard normal CDF via erf
  throw new Error("TODO: implement normalCdf()");
}

/**
 * Two-proportion z-test (the A/B test). Under H₀ the two arms share one
 * conversion rate, so the standard error uses the POOLED proportion.
 *
 * Returns { z, pValue } — z the test statistic, pValue two-sided.
 *
 * TODO: implement.
 *   1. Per-arm rates p̂_a = convA/nA, p̂_b = convB/nB, and the pooled rate p̂
 *      over both arms combined.
 *   2. Pooled standard error: √( p̂(1−p̂)·(1/nA + 1/nB) ).
 *   3. z = (rate difference) / SE; two-sided p-value from normalCdf of |z|
 *      per the formula in the header.
 */
function twoProportionZtest(
  convA: number,
  nA: number,
  convB: number,
  nB: number,
): { z: number; pValue: number } {
  // TODO: pooled proportion → pooled SE → z → two-sided p-value
  throw new Error("TODO: implement twoProportionZtest()");
}

/**
 * Confidence interval for the difference in conversion rates (p̂_b − p̂_a),
 * using the UNPOOLED standard error (each arm keeps its own variance):
 *
 *   SE = √( p̂_a(1−p̂_a)/nA + p̂_b(1−p̂_b)/nB )
 *
 * Returns [low, high] = diff ∓ zCrit·SE.
 *
 * TODO: implement.
 *   - Per-arm rates, their difference, the unpooled SE per the formula,
 *     then the [low, high] pair around the difference.
 */
function confidenceIntervalDiff(
  convA: number,
  nA: number,
  convB: number,
  nB: number,
  zCrit: number,
): [number, number] {
  // TODO: implement the CI for the difference in proportions
  throw new Error("TODO: implement confidenceIntervalDiff()");
}

// ---------------------------------------------------------------------------
// Simulation helpers (provided — do not edit)
// ---------------------------------------------------------------------------

/** One binomial draw: the number of successes in n Bernoulli(p) trials. */
function binomial(u: () => number, n: number, p: number): number {
  let successes = 0;
  for (let i = 0; i < n; i++) if (u() < p) successes++;
  return successes;
}

/** Run nExp simulated experiments; return each one's two-sided p-value. */
function simulateExperiments(
  u: () => number,
  nExp: number,
  pA: number,
  pB: number,
  nPerArm: number,
): number[] {
  const pValues: number[] = [];
  for (let e = 0; e < nExp; e++) {
    const convA = binomial(u, nPerArm, pA);
    const convB = binomial(u, nPerArm, pB);
    pValues.push(twoProportionZtest(convA, nPerArm, convB, nPerArm).pValue);
  }
  return pValues;
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 3 — Hypothesis testing and the A/B test\n");
  const u = makeRng(SEED);

  // ── 1. One worked A/B experiment ───────────────────────────────────────────
  console.log("[1/4] Worked example — a real lift...");
  const [convA, nA] = [500, 5000]; // control:   10.0% conversion
  const [convB, nB] = [600, 5000]; // treatment: 12.0% conversion
  const { z, pValue } = twoProportionZtest(convA, nA, convB, nB);
  const [ciLow, ciHigh] = confidenceIntervalDiff(convA, nA, convB, nB, Z_CRIT_95);
  console.log(
    `  A: ${convA}/${nA} = ${(convA / nA).toFixed(3)}    B: ${convB}/${nB} = ${(convB / nB).toFixed(3)}`,
  );
  console.log(`  z = ${z.toFixed(4)}   two-sided p = ${pValue.toFixed(6)}`);
  console.log(`  95% CI for (p_b − p_a): [${ciLow.toFixed(4)}, ${ciHigh.toFixed(4)}]`);
  console.log(`  → p < ${ALPHA} and the CI excludes 0: reject H₀, the lift is real.\n`);

  // ── 2. A/A simulation: the false-positive rate should be ≈ α ──────────────
  console.log(
    `[2/4] A/A simulation — ${N_SIMS} experiments with NO true difference...`,
  );
  const pAa = simulateExperiments(u, N_SIMS, 0.05, 0.05, 2000);
  const fpr = pAa.filter((p) => p < ALPHA).length / pAa.length;
  console.log(
    `  Fraction 'significant' at α=${ALPHA}: ${fpr.toFixed(4)}   (expected ≈ ${ALPHA})`,
  );
  console.log(
    "  → With no real effect, the test still fires α of the time — by design.\n",
  );

  // ── 3. A/B simulation: empirical power ─────────────────────────────────────
  console.log(
    `[3/4] A/B simulation — ${N_SIMS} experiments with a TRUE lift (5% → 6%)...`,
  );
  const pAb = simulateExperiments(u, N_SIMS, 0.05, 0.06, 5000);
  const power = pAb.filter((p) => p < ALPHA).length / pAb.length;
  console.log(`  Empirical power at n=5000/arm: ${power.toFixed(4)}`);
  console.log(
    "  → Power = P(detect the lift when it exists). Bigger n or bigger lift → more power.\n",
  );

  // ── 4. Multiple testing: 20 metrics on an A/A test ─────────────────────────
  console.log(
    "[4/4] Multiple-testing demo — 20 metrics, NO true difference anywhere...",
  );
  const pMetrics = simulateExperiments(u, 20, 0.05, 0.05, 2000);
  let nHits = 0;
  pMetrics.forEach((p, i) => {
    if (p < ALPHA) {
      nHits++;
      console.log(
        `  metric ${String(i + 1).padStart(2)}: p = ${p.toFixed(4)}  ← 'significant' (spurious!)`,
      );
    }
  });
  console.log(`  ${nHits} of 20 null metrics came up 'significant' at α=${ALPHA}.`);
  console.log("  ⚠ WARNING: check 20 metrics and P(≥1 false win) = 1 − 0.95²⁰ ≈ 64%.");
  console.log(
    "    Pick your primary metric BEFORE the test (or correct, e.g. Bonferroni).",
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okWorked = pValue < ALPHA && ciLow > 0;
  const okFpr = Math.abs(fpr - ALPHA) <= 0.02;
  const okPower = power > fpr;
  const okMulti = nHits >= 1;
  console.log(
    `  [${okWorked ? "x" : " "}] worked example: p < 0.05 and 95% CI excludes 0`,
  );
  console.log(
    `  [${okFpr ? "x" : " "}] A/A false-positive rate ≈ α  (${fpr.toFixed(4)} within 0.05 ± 0.02)`,
  );
  console.log(
    `  [${okPower ? "x" : " "}] empirical power reported and exceeds the A/A rate  (${power.toFixed(4)} > ${fpr.toFixed(4)})`,
  );
  console.log(
    `  [${okMulti ? "x" : " "}] 20-metric A/A run finds ≥ 1 spurious 'significant' result  (found ${nHits})`,
  );

  if (okWorked && okFpr && okPower && okMulti) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
