"""
Task 4 🔴 — The bundle is a graph: link extraction and 1-hop expansion.

What you'll learn:
  - OKF is "graph-shaped, not just tree-shaped". The directory hierarchy is one
    view; the markdown links between concepts are the real structure. A link
    from A to B asserts a RELATIONSHIP — the kind (joins-with, derived-from,
    supersedes) lives in the surrounding prose, not in the link.
  - Two link forms resolve to a concept id: bundle-relative `/orders.md` (start
    from the bundle root — recommended, and the only form that survives a file
    being moved into a subdirectory) and relative `./orders.md`.
  - Retrieval over a cheap index has a blind spot: a fact whose concept shares
    no words with the question is unreachable, however good your ranker is. One
    hop along the links reaches it — this is GraphRAG's core move (module 05b)
    with the graph already written down for you.
  - Links rot. A target that does not resolve is a finding to REPORT, not a
    crash and not a silent skip.

🔴 lane: build the adjacency yourself — no graph library. Treat a link as an
undirected relationship when expanding (neighbours = out-links ∪ in-links):
`orders` never links to `promo_codes`, but `promo_codes` links to `orders`, and
that is exactly as much of a relationship in the other direction.

Prerequisites: Task 1 (`load_bundle`) and Task 2 (`rank_by_index`).

How to run:
  uv run python modules/16b-knowledge-bundles/py/04_link_graph.py
"""

from __future__ import annotations

import importlib.util
import re  # noqa: F401 — the extract_links() TODO below needs a markdown-link pattern
import sys
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[1] / "bundle"

#: How many index-search hits seed the expansion.
SEED_K = 2
#: A fact that exists in exactly one concept body, and in no index line.
NEEDLE = "412,900"


# ---------------------------------------------------------------------------
# Tasks 1 + 2  (provided — do not edit)
# ---------------------------------------------------------------------------


def _load_sibling(filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"okf_{filename[:2]}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # so Task 1's @dataclass can resolve its module
    spec.loader.exec_module(module)
    return module


_t1 = _load_sibling("01_parse_bundle.py")
_t2 = _load_sibling("02_progressive_disclosure.py")
Concept = _t1.Concept


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def extract_links(concept_id: str, body: str) -> list[str]:
    """Every concept id this body links to, in document order.

    `concept_id` is the linking concept's own id — you need it to resolve a
    relative link from a nested concept (a `./x.md` inside
    `metrics/daily_revenue` means `metrics/x`).

    Keep only links to concepts: skip external URLs (anything with `://`),
    in-page anchors, `mailto:`, and any target that is not a `.md` file. Strip
    a trailing `#anchor`. Turn the surviving target into an id by dropping the
    leading `/` (bundle-relative) or the `./` plus prefixing the linking
    concept's directory (relative), then dropping `.md`.

    TODO: implement.
      - Find markdown link targets with a regex over `[text](target)` — capture
        only the target.
      - Filter out the non-concept targets listed above.
      - Resolve the two accepted forms to ids; `str.rsplit("/", 1)` gives you
        the linking concept's directory (empty string at the bundle root).
    """
    # TODO: extract and resolve the outgoing concept links
    raise NotImplementedError("TODO: implement extract_links()")


def build_graph(concepts: list[Concept]) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """The out-edge adjacency plus every dangling link.

    Return `(edges, dangling)` where `edges` maps every concept id to its
    sorted, de-duplicated list of resolvable targets (an isolated concept maps
    to an empty list — the key must still be present), and `dangling` is a
    sorted list of `(source_id, unresolved_target)` pairs.

    TODO: implement.
      - Build the set of real concept ids first; that set is what makes a link
        resolvable.
      - For each concept, split `extract_links(...)` into resolvable targets
        and dangling pairs.
      - Sort + de-duplicate both so the graph is deterministic.
    """
    # TODO: build the adjacency and collect dangling links
    raise NotImplementedError("TODO: implement build_graph()")


def neighbours(edges: dict[str, list[str]], concept_id: str) -> set[str]:
    """Every concept one link away, in EITHER direction.

    TODO: implement.
      - Start from this concept's own out-edges.
      - Add every concept whose out-edges contain `concept_id` (the in-edges).
        You are scanning the adjacency for that; a reverse index would be the
        optimisation, and is not needed at this size.
    """
    # TODO: union of out-links and in-links
    raise NotImplementedError("TODO: implement neighbours()")


def expand(edges: dict[str, list[str]], seeds: list[str], hops: int = 1) -> list[str]:
    """The seed set plus everything within `hops` links of it, sorted.

    Breadth-first: hop 1 adds the seeds' neighbours, hop 2 adds THOSE
    neighbours, and so on. A concept already reached is never re-expanded, so
    the walk terminates even though the graph has cycles.

    TODO: implement.
      - Keep a `seen` set (starts as the seeds) and a `frontier` set.
      - Per hop: union the frontier's `neighbours`, subtract `seen`, add the
        remainder to `seen`, and make it the next frontier.
      - Return the sorted ids.
    """
    # TODO: breadth-first expansion over the link graph
    raise NotImplementedError("TODO: implement expand()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------

# A question whose answer lives in a concept that the index search CANNOT find:
# nothing in that concept's title, description, or tags mentions the date, the
# order volume, or the jump.
QUESTION = "Why did order volume jump on 2026-05-17?"

EXPECTED_EDGES = {
    "customers": ["orders"],
    "legacy_orders_v1": ["orders"],
    "metrics/daily_revenue": ["orders", "promo_codes"],
    "orders": ["customers", "metrics/daily_revenue"],
    "promo_codes": ["orders"],
    "revenue_dashboard": ["metrics/daily_revenue", "promo_codes"],
}
EXPECTED_DANGLING = [("revenue_dashboard", "warehouse/missing")]
EXPECTED_SEEDS = ["orders", "legacy_orders_v1"]
EXPECTED_EXPANDED = [
    "customers",
    "legacy_orders_v1",
    "metrics/daily_revenue",
    "orders",
    "promo_codes",
]


def context_for(concepts: list[Concept], ids: list[str]) -> str:
    by_id = {c.id: c for c in concepts}
    return "\n\n".join(_t2.concept_block(by_id[i]) for i in ids if i in by_id)


def check(label: str, ok: bool) -> bool:
    print(f"  [{'x' if ok else ' '}] {label}")
    return ok


def main() -> None:
    print("\n=== Task 4: the link graph and 1-hop expansion ===\n")

    concepts = _t1.load_bundle(BUNDLE_DIR)
    edges, dangling = build_graph(concepts)

    print("link graph (out-edges):")
    for cid in sorted(edges):
        print(f"  {cid:24} -> {edges[cid]}")
    print(f"\ndangling links: {dangling}")

    ranked = _t2.rank_by_index(concepts, QUESTION)
    seeds = [cid for cid, score in ranked if score > 0][:SEED_K]
    expanded = expand(edges, seeds, hops=1)

    seed_ctx = context_for(concepts, seeds)
    expanded_ctx = context_for(concepts, expanded)

    print(f"\nquestion: {QUESTION}")
    print(f"  index ranking:  {[(i, round(s, 3)) for i, s in ranked[:4]]}")
    print(f"  seeds:          {seeds}  ({_t2.count_tokens(seed_ctx)} tokens)")
    print(f"  after 1 hop:    {expanded}  ({_t2.count_tokens(expanded_ctx)} tokens)")
    print(f"  needle {NEEDLE!r} in the seed context:     {NEEDLE in seed_ctx}")
    print(f"  needle {NEEDLE!r} in the expanded context: {NEEDLE in expanded_ctx}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    ok_edges = {cid: edges.get(cid) for cid in EXPECTED_EDGES} == EXPECTED_EDGES
    ok_keys = sorted(edges) == sorted(EXPECTED_EDGES)
    ok_dangling = dangling == EXPECTED_DANGLING
    ok_seeds = seeds == EXPECTED_SEEDS
    ok_needle_missing = NEEDLE not in seed_ctx
    ok_needle_found = NEEDLE in expanded_ctx
    ok_expanded = expanded == EXPECTED_EXPANDED
    ok_selective = "revenue_dashboard" not in expanded
    # promo_codes links TO orders; orders never links to it — reaching it proves
    # in-links count as relationships.
    ok_inlinks = "promo_codes" in expanded and "promo_codes" not in edges.get("orders", [])
    one_hop = expand(edges, ["revenue_dashboard"], hops=1)
    two_hop = expand(edges, ["revenue_dashboard"], hops=2)
    ok_hops = one_hop == ["metrics/daily_revenue", "promo_codes", "revenue_dashboard"] and set(
        two_hop
    ) - set(one_hop) == {"orders"}

    print("\nAcceptance:")
    all_ok = [
        check(
            "both link forms resolve — bundle-relative /x.md and relative ./x.md",
            ok_edges and ok_keys,
        ),
        check("the one dangling link is reported, not crashed on", ok_dangling),
        check(
            f"index search seeds {EXPECTED_SEEDS} and misses the answer concept",
            ok_seeds and ok_needle_missing,
        ),
        check("1-hop expansion reaches the concept holding the needle fact", ok_needle_found),
        check("the expanded set is exactly the seeds' neighbourhood", ok_expanded),
        check("expansion is selective — revenue_dashboard is NOT pulled in", ok_selective),
        check("expansion follows in-links as well as out-links", ok_inlinks),
        check("hops is respected: a 2-hop walk reaches exactly one more concept", ok_hops),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
