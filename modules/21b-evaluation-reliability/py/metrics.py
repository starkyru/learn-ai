"""metrics.py — retrieval metrics implemented from scratch (Module 21b, Task 1).

These are the measurements you take of the RETRIEVER, before any generator
runs. They are pure functions of a ranked list of chunk ids plus the gold
labels, so they are deterministic and trivially unit-testable against
hand-computed values.

Conventions (documented so tests and the report agree):

- ``Recall@k``  = (relevant chunks found in the top k) / (all relevant chunks).
  "Relevant" is any chunk whose graded relevance is at or above the rubric
  threshold; the caller passes that set in as ``relevant_ids``.

- ``Reciprocal Rank`` = 1 / (rank of the first relevant chunk), rank counted
  from 1. 0.0 if no relevant chunk appears (within the optional cutoff ``k``).
  ``MRR`` is the mean of the reciprocal ranks over a set of queries.

- ``NDCG@k`` uses the exponential gain ``2**grade - 1`` and the log discount
  ``1 / log2(rank + 1)`` with rank counted from 1 (so position 1 has discount
  ``1 / log2(2) = 1``). It is normalised by the ideal DCG (the DCG of the same
  grades sorted in descending order). 0.0 when the ideal DCG is 0.

No provider, no network, no randomness.
"""

from __future__ import annotations

import math
from collections.abc import Collection, Iterable, Mapping, Sequence


def _require_unique(ranked_ids: Sequence[str]) -> None:
    """Fail fast on a malformed ranking with duplicate ids.

    A retriever must return each chunk at most once. Duplicates would inflate
    Recall (``recall_at_k(["a", "a"], {"a"}, 2)`` -> 2) and let NDCG exceed 1,
    so a duplicate is a bug worth surfacing rather than silently scoring.
    """
    if len(set(ranked_ids)) != len(ranked_ids):
        raise ValueError("ranked_ids must not contain duplicates")


def recall_at_k(
    ranked_ids: Sequence[str],
    relevant_ids: Collection[str],
    k: int,
) -> float:
    """Fraction of the relevant chunks that appear in the top ``k`` results."""
    if k <= 0:
        raise ValueError("k must be a positive integer")
    _require_unique(ranked_ids)
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    top_k = ranked_ids[:k]
    found = sum(1 for cid in top_k if cid in relevant)
    return found / len(relevant)


def reciprocal_rank(
    ranked_ids: Sequence[str],
    relevant_ids: Collection[str],
    k: int | None = None,
) -> float:
    """Reciprocal of the rank (1-based) of the first relevant chunk.

    Returns 0.0 if no relevant chunk is found (within the cutoff ``k`` when
    given).
    """
    if k is not None and k <= 0:
        raise ValueError("k must be a positive integer")
    _require_unique(ranked_ids)
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    limit = len(ranked_ids) if k is None else min(k, len(ranked_ids))
    for position in range(limit):
        if ranked_ids[position] in relevant:
            return 1.0 / (position + 1)
    return 0.0


def mean_reciprocal_rank(
    results: Iterable[tuple[Sequence[str], Collection[str]]],
    k: int | None = None,
) -> float:
    """Mean of the reciprocal ranks over ``(ranked_ids, relevant_ids)`` pairs."""
    ranks = [reciprocal_rank(ranked, relevant, k) for ranked, relevant in results]
    if not ranks:
        return 0.0
    return sum(ranks) / len(ranks)


def dcg_at_k(
    ranked_ids: Sequence[str],
    grades: Mapping[str, float],
    k: int,
) -> float:
    """Discounted cumulative gain over the top ``k`` results.

    Gain is ``2**grade - 1``; a chunk absent from ``grades`` contributes 0.
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    _require_unique(ranked_ids)
    total = 0.0
    for position, cid in enumerate(ranked_ids[:k], start=1):
        grade = grades.get(cid, 0.0)
        gain = (2.0**grade) - 1.0
        total += gain / math.log2(position + 1)
    return total


def ndcg_at_k(
    ranked_ids: Sequence[str],
    grades: Mapping[str, float],
    k: int,
) -> float:
    """Normalised DCG at ``k``: actual DCG divided by the ideal DCG."""
    actual = dcg_at_k(ranked_ids, grades, k)
    ideal_order = sorted(grades.keys(), key=lambda cid: grades[cid], reverse=True)
    ideal = dcg_at_k(ideal_order, grades, k)
    if ideal == 0.0:
        return 0.0
    return actual / ideal
