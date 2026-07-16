"""agreement.py — judge <-> human reliability (Module 21b, Task 3).

Cohen's kappa (implemented from scratch, deterministic) and raw percent
agreement between the LLM judge's task-success labels and a blind human sample.
Disagreements are routed to an annotation queue (a listed output).

    kappa = (p_o - p_e) / (1 - p_e)

where p_o is the observed agreement and p_e is the agreement expected by chance,
p_e = sum over categories k of P(rater A = k) * P(rater B = k).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def percent_agreement(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must be the same length")
    if not labels_a:
        raise ValueError("no labels to compare")
    matches = sum(1 for x, y in zip(labels_a, labels_b, strict=True) if x == y)
    return matches / len(labels_a)


def cohens_kappa(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    """Cohen's kappa for two raters over paired categorical labels."""
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must be the same length")
    n = len(labels_a)
    if n == 0:
        raise ValueError("no labels to compare")
    p_o = sum(1 for x, y in zip(labels_a, labels_b, strict=True) if x == y) / n
    count_a = Counter(labels_a)
    count_b = Counter(labels_b)
    # Iterate categories in a CANONICAL SORTED order: float addition is not
    # associative, so an unordered (hash-slot) traversal could make p_e differ in
    # the last ULP from the TypeScript port for 3+ categories.
    categories = sorted(set(count_a) | set(count_b))
    p_e = sum((count_a[k] / n) * (count_b[k] / n) for k in categories)
    if p_e == 1.0:
        # No variance in the labels; kappa is undefined — report perfect
        # agreement as 1.0, otherwise 0.0.
        return 1.0 if p_o == 1.0 else 0.0
    return (p_o - p_e) / (1.0 - p_e)


def build_agreement_report(
    variant: str,
    judge_labels: Mapping[str, int],
    human_labels: Mapping[str, int],
    judge_model: str,
    prompt_version: str,
) -> dict[str, Any]:
    """Compare the judge and human on their common cases; queue disagreements."""
    common = sorted(set(judge_labels) & set(human_labels))
    if not common:
        raise ValueError("judge and human share no labeled cases")
    judge_seq = [judge_labels[c] for c in common]
    human_seq = [human_labels[c] for c in common]
    queue = [
        {"case_id": c, "judge": judge_labels[c], "human": human_labels[c]}
        for c in common
        if judge_labels[c] != human_labels[c]
    ]
    return {
        "variant": variant,
        "judge": {"model": judge_model, "prompt_version": prompt_version},
        "num_labeled": len(common),
        "percent_agreement": percent_agreement(judge_seq, human_seq),
        "cohens_kappa": cohens_kappa(judge_seq, human_seq),
        "disagreement_queue": queue,
    }
