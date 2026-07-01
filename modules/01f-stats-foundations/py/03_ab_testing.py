"""
Task 3 🟢 — Hypothesis testing and the A/B test.

What you'll learn:
  - The sampling distribution of a proportion and the two-proportion z-test —
    the statistical engine behind every A/B test
  - What a p-value actually is (and is not): P(data this extreme | H₀ true),
    NOT P(H₀ true | data)
  - Confidence intervals for the difference in conversion rates
  - Type I error (α), statistical power, and why running 20 metrics on an
    A/A test almost guarantees a spurious "win" (multiple testing)

The math (README derives each step):

  Pooled proportion:  p̂ = (conv_a + conv_b) / (n_a + n_b)
  Pooled SE (H₀):     SE = √( p̂(1−p̂)·(1/n_a + 1/n_b) )
  z statistic:        z  = (p̂_b − p̂_a) / SE
  Two-sided p-value:  p  = 2 · (1 − Φ(|z|))          Φ = standard normal CDF
  Φ via erf:          Φ(z) = ½·(1 + erf(z / √2))

  CI for the difference (unpooled SE):
    (p̂_b − p̂_a) ± z_crit · √( p̂_a(1−p̂_a)/n_a + p̂_b(1−p̂_b)/n_b )

You implement normal_cdf, two_proportion_ztest, confidence_interval_diff.
The worked example, the A/A / power simulations, and the multiple-testing
demo are provided and runnable.

How to run:
  uv run python modules/01f-stats-foundations/py/03_ab_testing.py
"""

from __future__ import annotations

import math  # noqa: F401  (your normal_cdf implementation uses math.erf / math.sqrt)

import numpy as np

SEED = 5
ALPHA = 0.05
Z_CRIT_95 = 1.96  # two-sided 95% critical value

N_SIMS = 2000  # experiments per simulation batch


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def normal_cdf(z: float) -> float:
    """
    Standard normal CDF Φ(z), via the error function:

      Φ(z) = ½ · (1 + erf(z / √2))

    TODO: implement — one line with math.erf and math.sqrt.
    """
    # TODO: implement the standard normal CDF via erf
    raise NotImplementedError("TODO: implement normal_cdf()")


def two_proportion_ztest(conv_a: int, n_a: int, conv_b: int, n_b: int) -> tuple[float, float]:
    """
    Two-proportion z-test (the A/B test). Under H₀ the two arms share one
    conversion rate, so the standard error uses the POOLED proportion.

    Returns (z, p_value) — z the test statistic, p_value two-sided.

    TODO: implement.
      1. Per-arm rates p̂_a = conv_a/n_a, p̂_b = conv_b/n_b, and the pooled
         rate p̂ over both arms combined.
      2. Pooled standard error: √( p̂(1−p̂)·(1/n_a + 1/n_b) ).
      3. z = (rate difference) / SE; two-sided p-value from normal_cdf of |z|
         per the formula in the header.
    """
    # TODO: pooled proportion → pooled SE → z → two-sided p-value
    raise NotImplementedError("TODO: implement two_proportion_ztest()")


def confidence_interval_diff(
    conv_a: int, n_a: int, conv_b: int, n_b: int, z_crit: float
) -> tuple[float, float]:
    """
    Confidence interval for the difference in conversion rates (p̂_b − p̂_a),
    using the UNPOOLED standard error (each arm keeps its own variance):

      SE = √( p̂_a(1−p̂_a)/n_a + p̂_b(1−p̂_b)/n_b )

    Returns (low, high) = diff ∓ z_crit·SE.

    TODO: implement.
      - Per-arm rates, their difference, the unpooled SE per the formula,
        then the (low, high) tuple around the difference.
    """
    # TODO: implement the CI for the difference in proportions
    raise NotImplementedError("TODO: implement confidence_interval_diff()")


# ---------------------------------------------------------------------------
# Simulation helpers  (provided — do not edit)
# ---------------------------------------------------------------------------


def simulate_experiments(
    rng: np.random.Generator, n_exp: int, p_a: float, p_b: float, n_per_arm: int
) -> np.ndarray:
    """Run n_exp simulated experiments; return each one's two-sided p-value."""
    conv_a = rng.binomial(n_per_arm, p_a, size=n_exp)
    conv_b = rng.binomial(n_per_arm, p_b, size=n_exp)
    return np.array(
        [
            two_proportion_ztest(int(ca), n_per_arm, int(cb), n_per_arm)[1]
            for ca, cb in zip(conv_a, conv_b, strict=True)
        ]
    )


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 3 — Hypothesis testing and the A/B test\n")
    rng = np.random.default_rng(SEED)

    # ── 1. One worked A/B experiment ─────────────────────────────────────────
    print("[1/4] Worked example — a real lift...")
    conv_a, n_a = 500, 5000  # control:   10.0% conversion
    conv_b, n_b = 600, 5000  # treatment: 12.0% conversion
    z, p_value = two_proportion_ztest(conv_a, n_a, conv_b, n_b)
    ci_low, ci_high = confidence_interval_diff(conv_a, n_a, conv_b, n_b, Z_CRIT_95)
    print(f"  A: {conv_a}/{n_a} = {conv_a / n_a:.3f}    B: {conv_b}/{n_b} = {conv_b / n_b:.3f}")
    print(f"  z = {z:.4f}   two-sided p = {p_value:.6f}")
    print(f"  95% CI for (p_b − p_a): [{ci_low:.4f}, {ci_high:.4f}]")
    print(f"  → p < {ALPHA} and the CI excludes 0: reject H₀, the lift is real.\n")

    # ── 2. A/A simulation: the false-positive rate should be ≈ α ────────────
    print(f"[2/4] A/A simulation — {N_SIMS} experiments with NO true difference...")
    p_aa = simulate_experiments(rng, N_SIMS, p_a=0.05, p_b=0.05, n_per_arm=2000)
    fpr = float(np.mean(p_aa < ALPHA))
    print(f"  Fraction 'significant' at α={ALPHA}: {fpr:.4f}   (expected ≈ {ALPHA})")
    print("  → With no real effect, the test still fires α of the time — by design.\n")

    # ── 3. A/B simulation: empirical power ───────────────────────────────────
    print(f"[3/4] A/B simulation — {N_SIMS} experiments with a TRUE lift (5% → 6%)...")
    p_ab = simulate_experiments(rng, N_SIMS, p_a=0.05, p_b=0.06, n_per_arm=5000)
    power = float(np.mean(p_ab < ALPHA))
    print(f"  Empirical power at n=5000/arm: {power:.4f}")
    print("  → Power = P(detect the lift when it exists). Bigger n or bigger lift → more power.\n")

    # ── 4. Multiple testing: 20 metrics on an A/A test ───────────────────────
    print("[4/4] Multiple-testing demo — 20 metrics, NO true difference anywhere...")
    p_metrics = simulate_experiments(rng, 20, p_a=0.05, p_b=0.05, n_per_arm=2000)
    n_hits = int(np.sum(p_metrics < ALPHA))
    for i, p in enumerate(p_metrics):
        if p < ALPHA:
            print(f"  metric {i + 1:>2}: p = {p:.4f}  ← 'significant' (spurious!)")
    print(f"  {n_hits} of 20 null metrics came up 'significant' at α={ALPHA}.")
    print("  ⚠ WARNING: check 20 metrics and P(≥1 false win) = 1 − 0.95²⁰ ≈ 64%.")
    print("    Pick your primary metric BEFORE the test (or correct, e.g. Bonferroni).")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_worked = p_value < ALPHA and ci_low > 0.0
    ok_fpr = abs(fpr - ALPHA) <= 0.02
    ok_power = power > fpr
    ok_multi = n_hits >= 1
    print(f"  [{'x' if ok_worked else ' '}] worked example: p < 0.05 and 95% CI excludes 0")
    print(
        f"  [{'x' if ok_fpr else ' '}] A/A false-positive rate ≈ α  ({fpr:.4f} within 0.05 ± 0.02)"
    )
    print(
        f"  [{'x' if ok_power else ' '}] empirical power reported and exceeds the A/A rate  ({power:.4f} > {fpr:.4f})"
    )
    print(
        f"  [{'x' if ok_multi else ' '}] 20-metric A/A run finds ≥ 1 spurious 'significant' result  (found {n_hits})"
    )

    if ok_worked and ok_fpr and ok_power and ok_multi:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
