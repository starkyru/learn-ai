"""
Task 2 🟡 — Progressive disclosure: pay for the index, not the bundle.

What you'll learn:
  - OKF's `index.md` is not decoration, it is a CHEAP TABLE OF CONTENTS. One
    line per concept (title + description + tags + link) is a few tokens;
    the concept body is a few hundred. Load the index first, decide from it,
    then spend the remaining budget on the bodies you actually need.
  - That is the whole "progressive disclosure" idea module 16 spends its token
    budget on, except here the structure that makes it possible is already in
    the knowledge format: the queryable fields live in frontmatter, the
    expensive prose lives in the body, and the two are separable.
  - The failure mode of the naive alternative is not subtle: dumping the whole
    bundle costs ~10x the index and buries the answer in irrelevant prose
    ("lost in the middle", module 16).

Token counting here is a WHITESPACE APPROXIMATION (`len(text.split())`) so the
numbers are deterministic and offline. Module 16 Task 1 counts precisely with
tiktoken; the budgeting discipline is identical either way.

Prerequisite: Task 1 (this file imports your `load_bundle`).

How to run:
  uv run python modules/16b-knowledge-bundles/py/02_progressive_disclosure.py
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
from collections import Counter
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[1] / "bundle"

#: Hard context budget, in (approximate) tokens, for the assembled prompt.
BUDGET = 250


# ---------------------------------------------------------------------------
# Task 1's loader  (provided — do not edit)
# ---------------------------------------------------------------------------
# Exercise filenames start with a digit, so a plain `import` is impossible —
# load Task 1's module by path instead. Implement Task 1 first: this file uses
# your `Concept` and `load_bundle`.


def _load_task1():
    path = Path(__file__).with_name("01_parse_bundle.py")
    spec = importlib.util.spec_from_file_location("okf_task1", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # so Task 1's @dataclass can resolve its module
    spec.loader.exec_module(module)
    return module


_t1 = _load_task1()
Concept = _t1.Concept


# ---------------------------------------------------------------------------
# Token counting + bag-of-words scoring  (provided — do not edit)
# ---------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """Approximate token count: whitespace-separated words."""
    return len(text.split())


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters/digits)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bag_of_words(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Cosine similarity over sparse count vectors (0 if either norm is 0)."""
    dot = sum(a[w] * b[w] for w in a if w in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return 0.0 if norm_a == 0 or norm_b == 0 else dot / (norm_a * norm_b)


def concept_block(concept: Concept) -> str:
    """The expensive form of a concept: a heading plus its full body."""
    return f"## /{concept.id}.md\n{concept.body}"


def whole_bundle_context(concepts: list[Concept]) -> str:
    """The naive baseline: the index AND every body, in id order."""
    ordered = sorted(concepts, key=lambda c: c.id)
    return build_index(concepts) + "\n\n" + "\n\n".join(concept_block(c) for c in ordered)


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def index_line(concept: Concept) -> str:
    """One index entry for a concept: the cheap, queryable summary of it.

    It must carry enough for a reader (human or model) to decide whether the
    body is worth loading, and enough for a lexical search to match on:
    the `title`, a bundle-relative markdown link to `/<id>.md`, the
    `description`, and the `tags`. Fall back to the concept id when `title` is
    missing (remember: `type` is the only required key).

    Keep the format stable — `build_index`, the ranker, and Task 4's seed
    search all read these lines.

    TODO: implement.
      - Pull `title`, `description`, and `tags` out of `concept.meta` with
        `dict.get` defaults; `tags` is a `list[str]` (join it).
      - Return a single markdown list item — no trailing newline.
    """
    # TODO: build one index line for this concept
    raise NotImplementedError("TODO: implement index_line()")


def build_index(concepts: list[Concept]) -> str:
    """The generated `index.md` body: one `index_line` per concept, id-sorted.

    TODO: implement.
      - Sort by `Concept.id` so the index is deterministic, then join the
        lines with newlines.
    """
    # TODO: assemble the index from the concept lines
    raise NotImplementedError("TODO: implement build_index()")


def rank_by_index(concepts: list[Concept], question: str) -> list[tuple[str, float]]:
    """Score every concept against the question USING ONLY ITS INDEX LINE.

    This is the point of the exercise: the ranker is not allowed to look at
    bodies, because in a real bundle the bodies are the thing you have not paid
    for yet. Return `(concept_id, score)` pairs, best first.

    TODO: implement.
      - Vectorise the question once with `bag_of_words`.
      - Score each concept with `cosine` against `bag_of_words(index_line(c))`.
      - Sort by score descending; break ties by concept id so the order is
        stable (sort on a `(-score, id)` key).
    """
    # TODO: rank concepts by index-line similarity
    raise NotImplementedError("TODO: implement rank_by_index()")


def disclose(concepts: list[Concept], question: str, budget: int) -> tuple[str, list[str]]:
    """Assemble a context under `budget` tokens: index first, then bodies.

    Return `(context, chosen_ids)` where `chosen_ids` are the concepts whose
    FULL BODY made it in, in the order you added them.

    The rules:
      - The index is always included, and it is charged against the budget.
      - Only concepts with a score above zero are candidates (an empty result
        beats a plausible-looking irrelevant one — module 06d's lesson).
      - Walk candidates best-first; add a body when it still fits; skip it when
        it does not and carry on down the list.
      - Never exceed `budget`.

    TODO: implement.
      - Start the parts list with `build_index(concepts)` and set `used` to its
        `count_tokens`.
      - Build an id -> Concept lookup so you can fetch bodies by id.
      - Loop over `rank_by_index(...)`, skip non-positive scores, cost each
        candidate with `count_tokens(concept_block(c))`, and only accept it
        while `used + cost` stays within `budget`.
      - Join the parts with a blank line between them.
    """
    # TODO: assemble the budgeted, index-first context
    raise NotImplementedError("TODO: implement disclose()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------

# Each question is answered by exactly one concept in this bundle.
QUESTIONS: list[tuple[str, str]] = [
    ("Which table holds one row per customer order?", "orders"),
    ("Which promo codes are active and what are their redemption limits?", "promo_codes"),
    ("Where are takings aggregated per calendar day?", "metrics/daily_revenue"),
]


def check(label: str, ok: bool) -> bool:
    print(f"  [{'x' if ok else ' '}] {label}")
    return ok


def main() -> None:
    print("\n=== Task 2: progressive disclosure under a token budget ===\n")

    concepts = _t1.load_bundle(BUNDLE_DIR)
    index = build_index(concepts)
    index_tokens = count_tokens(index)
    whole_tokens = count_tokens(whole_bundle_context(concepts))

    print(f"budget:            {BUDGET} tokens")
    print(f"index only:        {index_tokens} tokens ({len(concepts)} concepts)")
    print(f"whole bundle:      {whole_tokens} tokens")
    print(f"index is {index_tokens / whole_tokens:.0%} of the bundle\n")

    results: list[tuple[str, str, int, list[str]]] = []
    for question, expected in QUESTIONS:
        context, chosen = disclose(concepts, question, BUDGET)
        results.append((question, expected, count_tokens(context), chosen))
        print(f"q: {question}")
        print(f"   ranking: {[(i, round(s, 3)) for i, s in rank_by_index(concepts, question)[:3]]}")
        print(f"   disclosed: {count_tokens(context)} tokens, bodies={chosen}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    ok_index_cheap = index_tokens * 5 < whole_tokens
    ok_baseline_blows = whole_tokens > 2 * BUDGET
    ok_under_budget = all(tokens <= BUDGET for _, _, tokens, _ in results)
    ok_right_concept = all(expected in chosen for _, expected, _, chosen in results)
    ok_index_present = all(
        disclose(concepts, q, BUDGET)[0].startswith(index) for q, _, _, _ in results
    )
    ok_selective = all(len(chosen) < len(concepts) for _, _, _, chosen in results)

    print("\nAcceptance:")
    all_ok = [
        check(
            f"the index ({index_tokens}) is under a fifth of the bundle ({whole_tokens})",
            ok_index_cheap,
        ),
        check(
            f"the whole-bundle baseline ({whole_tokens}) blows the {BUDGET}-token budget",
            ok_baseline_blows,
        ),
        check(f"every disclosed context fits in {BUDGET} tokens", ok_under_budget),
        check("each question disclosed the one concept that answers it", ok_right_concept),
        check("the index is always present, and comes first", ok_index_present),
        check("disclosure is selective — never all bodies", ok_selective),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
