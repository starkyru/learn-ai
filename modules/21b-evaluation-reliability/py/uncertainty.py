"""uncertainty.py — paired comparison, bootstrap CI, release verdict (Task 3).

Compare two answer variants over the SAME held-out cases. Report the mean paired
difference, a paired bootstrap confidence interval (from scratch, with a SEEDED
deterministic resampler so it is reproducible and identical across languages),
win/tie/loss counts, and a verdict that can be ``inconclusive`` when the interval
crosses the practical-improvement threshold — so a model is not promoted on a
handful of noisy cases.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

_TIE_EPS = 1e-9

# Numerical Recipes linear congruential generator (mod 2**32). A tiny, fully
# specified PRNG so the resample sequence is reproducible and byte-identical in
# the TypeScript port.
_LCG_A = 1664525
_LCG_C = 1013904223
_LCG_M = 0x100000000


class Lcg:
    """Seeded LCG. State is advanced explicitly; no global RNG is touched."""

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    def next_u32(self) -> int:
        self.state = (_LCG_A * self.state + _LCG_C) % _LCG_M
        return self.state

    def randint(self, n: int) -> int:
        # Use the HIGH bits (multiply-shift), not `% n`: an LCG's low bits are
        # highly periodic, so `next_u32() % n` degenerates for small n. The
        # product stays below 2**53, so it is exact in both Python and JS.
        return (self.next_u32() * n) >> 32


def _sorted_index(sorted_values: Sequence[float], fractional_rank: float) -> float:
    idx = int(fractional_rank)
    if idx < 0:
        idx = 0
    if idx > len(sorted_values) - 1:
        idx = len(sorted_values) - 1
    return sorted_values[idx]


def paired_bootstrap_ci(
    diffs: Sequence[float],
    iterations: int,
    seed: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """95% (by default) paired bootstrap CI of the mean difference.

    Resamples ``diffs`` with replacement ``iterations`` times using a seeded LCG,
    then takes the lower/upper interval bounds from the sorted bootstrap means.
    """
    n = len(diffs)
    if n == 0:
        raise ValueError("diffs must be non-empty")
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    rng = Lcg(seed)
    means: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randint(n)]
        means.append(total / n)
    means.sort()
    lower = _sorted_index(means, math.floor(alpha / 2.0 * iterations))
    upper = _sorted_index(means, math.ceil((1.0 - alpha / 2.0) * iterations) - 1)
    return lower, upper


def win_tie_loss(baseline: Sequence[float], candidate: Sequence[float]) -> dict[str, int]:
    """Per-case win/tie/loss counts for the candidate vs the baseline."""
    if len(baseline) != len(candidate):
        raise ValueError("score sequences must be the same length")
    wins = ties = losses = 0
    for b, c in zip(baseline, candidate, strict=True):
        diff = c - b
        if diff > _TIE_EPS:
            wins += 1
        elif diff < -_TIE_EPS:
            losses += 1
        else:
            ties += 1
    return {"wins": wins, "ties": ties, "losses": losses}


def compare_variants(
    baseline: Sequence[float],
    candidate: Sequence[float],
    practical_threshold: float,
    iterations: int,
    seed: int,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Full paired comparison + release verdict.

    Verdict:
      - ``promote``      when the CI lower bound clears the practical threshold,
      - ``reject``       when the CI upper bound is at or below 0,
      - ``inconclusive`` otherwise (the interval crosses the threshold).
    """
    if len(baseline) != len(candidate):
        raise ValueError("score sequences must be the same length")
    diffs = [c - b for b, c in zip(baseline, candidate, strict=True)]
    mean_diff = sum(diffs) / len(diffs)
    lower, upper = paired_bootstrap_ci(diffs, iterations, seed, alpha)
    if lower >= practical_threshold:
        verdict = "promote"
    elif upper <= 0.0:
        verdict = "reject"
    else:
        verdict = "inconclusive"
    return {
        "num_cases": len(diffs),
        "mean_difference": mean_diff,
        "ci_lower": lower,
        "ci_upper": upper,
        "alpha": alpha,
        "practical_threshold": practical_threshold,
        "bootstrap_iterations": iterations,
        "bootstrap_seed": seed,
        "win_tie_loss": win_tie_loss(baseline, candidate),
        "verdict": verdict,
    }
