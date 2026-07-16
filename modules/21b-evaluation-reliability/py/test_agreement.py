"""test_agreement.py — Cohen's kappa + agreement (hand-derived expected values).

The expected kappa values are derived on paper from the confusion matrix
(kappa = (p_o - p_e) / (1 - p_e)); they are NOT produced by the function under
test. See each test's comment for the derivation.
"""

from __future__ import annotations

import math

import pytest
from agreement import build_agreement_report, cohens_kappa, percent_agreement


def test_kappa_moderate_hand_value() -> None:
    # pairs: (1,1)x4, (1,0)x2, (0,1)x1, (0,0)x3  ->  p_o = 7/10 = 0.7
    # marginals A: 1->6, 0->4 ; B: 1->5, 0->5
    # p_e = (6/10)(5/10) + (4/10)(5/10) = 0.3 + 0.2 = 0.5
    # kappa = (0.7 - 0.5) / (1 - 0.5) = 0.2 / 0.5 = 0.4
    a = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
    b = [1, 1, 1, 1, 0, 0, 1, 0, 0, 0]
    assert math.isclose(cohens_kappa(a, b), 0.4, abs_tol=1e-9)


def test_kappa_three_category_hand_value_and_parity() -> None:
    # 3 categories {0, 1, 2}; a = [0,0,0,1,1,2], b = [0,1,2,1,1,2].
    # p_o = 4/6 (agree at positions 0, 3, 4, 5).
    # marginals A {0:3, 1:2, 2:1}, B {0:1, 1:3, 2:2}
    # p_e = (3/6)(1/6) + (2/6)(3/6) + (1/6)(2/6) = 11/36
    # kappa = (4/6 - 11/36) / (1 - 11/36) = (13/36) / (25/36) = 13/25 = 0.52
    # The exact IEEE-754 result is pinned so Python and TypeScript agree
    # byte-for-byte (this is the >2-category parity proof).
    a = [0, 0, 0, 1, 1, 2]
    b = [0, 1, 2, 1, 1, 2]
    assert cohens_kappa(a, b) == 0.5199999999999999


def test_kappa_chance_is_zero() -> None:
    # p_o = 2/4 = 0.5 ; marginals A and B both {1:2, 0:2} -> p_e = 0.5
    # kappa = (0.5 - 0.5) / (1 - 0.5) = 0.0
    assert cohens_kappa([1, 1, 0, 0], [1, 0, 1, 0]) == 0.0


def test_kappa_perfect_nondegenerate_is_one() -> None:
    # p_o = 1 ; marginals {1:2, 0:2} both -> p_e = 0.5 ; kappa = 0.5/0.5 = 1.0
    assert cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0


def test_kappa_systematic_disagreement_is_minus_one() -> None:
    # p_o = 0 ; marginals both {1:2, 0:2} -> p_e = 0.5
    # kappa = (0 - 0.5) / (1 - 0.5) = -1.0
    assert cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]) == -1.0


def test_kappa_degenerate_single_category_is_one() -> None:
    # All labels identical -> p_e = 1 (undefined); our convention returns 1.0
    # for perfect agreement.
    assert cohens_kappa([1, 1, 1], [1, 1, 1]) == 1.0


def test_percent_agreement_hand_value() -> None:
    # matches at positions 0 and 2 -> 2/4 = 0.5
    assert percent_agreement([1, 0, 1, 1], [1, 1, 1, 0]) == 0.5


def test_kappa_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        cohens_kappa([1, 0], [1])


def test_kappa_rejects_empty() -> None:
    with pytest.raises(ValueError):
        cohens_kappa([], [])


def test_agreement_report_queues_disagreements() -> None:
    judge = {"c1": 1, "c2": 0, "c3": 1, "c4": 0}
    human = {"c1": 1, "c2": 0, "c3": 0, "c4": 1}  # disagree on c3, c4
    report = build_agreement_report("variant_a", judge, human, "fake-judge-v1", "p-v1")
    assert report["num_labeled"] == 4
    assert report["percent_agreement"] == 0.5
    assert [d["case_id"] for d in report["disagreement_queue"]] == ["c3", "c4"]
    assert report["judge"] == {"model": "fake-judge-v1", "prompt_version": "p-v1"}
