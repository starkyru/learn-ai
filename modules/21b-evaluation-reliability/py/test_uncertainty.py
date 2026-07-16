"""test_uncertainty.py — seeded LCG, paired bootstrap CI, and release verdict.

Exact bounds are asserted where they are hand-derivable (constant input, and a
two-point input whose bootstrap means are 0 / 0.5 / 1 so the tails are 0 and 1).
The LCG is pinned to a value computed by hand from its formula. Determinism is
asserted (same seed -> identical interval).
"""

from __future__ import annotations

import pytest
from uncertainty import Lcg, compare_variants, paired_bootstrap_ci, win_tie_loss


def test_lcg_first_value_hand_computed() -> None:
    # state0 = 42 ; next = (1664525*42 + 1013904223) mod 2**32
    #        = 69910050 + 1013904223 = 1083814273  (< 2**32)
    assert Lcg(42).next_u32() == 1083814273


def test_lcg_randint_uses_high_bits() -> None:
    # (1083814273 * 10) >> 32 = 10838142730 >> 32 = 2
    assert Lcg(42).randint(10) == 2


def test_bootstrap_constant_input_is_exact() -> None:
    # Every resample of a constant vector has the same mean, so both interval
    # bounds equal that constant regardless of seed.
    assert paired_bootstrap_ci([0.5, 0.5, 0.5], 200, seed=1) == (0.5, 0.5)


def test_bootstrap_single_element_is_exact() -> None:
    assert paired_bootstrap_ci([0.7], 50, seed=9) == (0.7, 0.7)


def test_bootstrap_two_point_tails_are_extremes() -> None:
    # Input [0, 1]: sample means are 0.0, 0.5, or 1.0. With 2000 resamples
    # ~25% are 0.0 and ~25% are 1.0, so the 2.5th and 97.5th percentiles
    # (nearest sorted element) are exactly 0.0 and 1.0.
    assert paired_bootstrap_ci([0.0, 1.0], 2000, seed=7) == (0.0, 1.0)


def test_bootstrap_is_deterministic_for_a_seed() -> None:
    data = [0.2, 0.8, 0.5, 0.1, 0.9]
    first = paired_bootstrap_ci(data, 500, seed=123)
    second = paired_bootstrap_ci(data, 500, seed=123)
    assert first == second


def test_bootstrap_bounds_bracket_the_data() -> None:
    data = [0.1, 0.4, 0.9, 0.3]
    lower, upper = paired_bootstrap_ci(data, 500, seed=5)
    assert min(data) <= lower <= upper <= max(data)


def test_bootstrap_rejects_empty_or_zero_iterations() -> None:
    with pytest.raises(ValueError):
        paired_bootstrap_ci([], 10, seed=1)
    with pytest.raises(ValueError):
        paired_bootstrap_ci([0.1], 0, seed=1)


def test_win_tie_loss_hand_counts() -> None:
    # diffs (candidate - baseline): +1, 0, +0.5 -> 2 wins, 1 tie, 0 losses
    assert win_tie_loss([0.0, 0.0, 0.0], [1.0, 0.0, 0.5]) == {
        "wins": 2,
        "ties": 1,
        "losses": 0,
    }


def test_verdict_promote_when_ci_clears_threshold() -> None:
    result = compare_variants([0, 0, 0, 0, 0], [1, 1, 1, 1, 1], 0.1, 500, seed=1)
    assert result["verdict"] == "promote"
    assert result["mean_difference"] == 1.0


def test_verdict_reject_when_ci_at_or_below_zero() -> None:
    result = compare_variants([1, 1, 1, 1, 1], [0, 0, 0, 0, 0], 0.1, 500, seed=1)
    assert result["verdict"] == "reject"


def test_verdict_inconclusive_when_ci_crosses_threshold() -> None:
    # Symmetric wins/losses -> mean 0, CI spans negative to positive.
    result = compare_variants([0, 0, 1, 1], [1, 1, 0, 0], 0.1, 500, seed=1)
    assert result["verdict"] == "inconclusive"


def test_compare_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        compare_variants([0.0, 1.0], [1.0], 0.1, 100, seed=1)
