"""
Task 3 🟡 — Trust: provenance, lifecycle status, and staleness.

What you'll learn:
  - Retrieval that only asks "is this relevant?" will happily cite a
    deprecated table, a snapshot that expired last quarter, or a paragraph no
    human has ever read. OKF puts those signals in QUERYABLE frontmatter so the
    filter is a few lines of code instead of a research project:
      * `status`      draft | stable | deprecated  (lifecycle)
      * `stale_after` a date after which the content is not trustworthy
      * `generated`   { by, at }        — who wrote it (agent or human)
      * `verified`    [{ by, at }, ...] — who signed it off
      * `sources`     what it was derived from
  - Freshness is a property of the KNOWLEDGE, not of the file. `promo_codes`
    has not changed in months and its file mtime is recent — it is still stale,
    because `stale_after` says the snapshot only described one quarter.
  - `draft` is not the same as untrusted, and `verified` is not the same as
    correct. Decide which signal your answer actually needs, then say why in
    the citation.
  - Every drop needs a REASON naming the field that caused it. A filter that
    silently returns fewer results is indistinguishable from a broken one.

Determinism: `now` is passed in as an ISO date string. Never call
`date.today()` here — the acceptance checks pin two different "nows".

Prerequisite: Task 1 (this file imports your `load_bundle`).

How to run:
  uv run python modules/16b-knowledge-bundles/py/03_trust_gating.py
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date  # noqa: F401 — the is_stale() TODO below uses date.fromisoformat
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[1] / "bundle"

#: The two "todays" the harness evaluates the same bundle against.
NOW = "2026-07-01"
EARLIER = "2026-05-01"


# ---------------------------------------------------------------------------
# Task 1's loader  (provided — do not edit)
# ---------------------------------------------------------------------------


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
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def is_stale(meta: dict, now: str) -> bool:
    """True when this concept's `stale_after` date has passed.

    A concept with no `stale_after` never goes stale on its own — absence of the
    key means "no expiry declared", not "expired".

    TODO: implement.
      - Read `stale_after` from `meta`; return False when it is missing/empty.
      - Compare it against `now` as DATES, not strings — `date.fromisoformat`
        parses both (`YYYY-MM-DD`). Stale means the expiry is strictly before
        `now`, so a concept is still fresh on its `stale_after` day.
    """
    # TODO: decide whether this concept has expired
    raise NotImplementedError("TODO: implement is_stale()")


def trust_filter(
    concepts: list[Concept], now: str, require_verified: bool
) -> tuple[list[Concept], list[tuple[str, str]]]:
    """Split concepts into (trusted, dropped) where dropped carries a reason.

    Return `(kept, [(concept_id, reason), ...])`, both in the input order.
    Each reason must NAME the frontmatter key that caused the drop — `status`,
    `stale_after`, or `verified` — so the report says which rule fired.

    Apply the rules in this order (strongest, most permanent first), so a
    concept that trips several is reported under the most fundamental one:
      1. `status: deprecated`  → dropped, always. It may be fresh and verified
         and is still the wrong answer to every question.
      2. stale (`is_stale`)    → dropped.
      3. `require_verified` and no `verified` entry → dropped.
    Everything else is kept — including `status: draft`, which is a lifecycle
    stage, not a trust verdict.

    TODO: implement.
      - Walk the concepts once, test the three rules in the documented order,
        and append to `kept` or to `dropped` with a reason string that includes
        the deciding key (and the useful value, e.g. the expiry date).
    """
    # TODO: gate the concepts on lifecycle, freshness, and verification
    raise NotImplementedError("TODO: implement trust_filter()")


def provenance(concept: Concept) -> str:
    """A one-line citation: what this claim is, and who stands behind it.

    This is the string you would append to a generated answer, so it has to
    survive being read on its own. Include the concept id, its `type`, its
    `status`, who `generated` it, and who `verified` it (or say plainly that
    nobody did).

    TODO: implement.
      - Read `type`, `status`, `generated.by`, and the first `verified` entry's
        `by` out of `concept.meta` (all optional — use defaults).
      - Return one line, no newline; make the unverified case explicit rather
        than blank.
    """
    # TODO: render the provenance citation line
    raise NotImplementedError("TODO: implement provenance()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------

# Which frontmatter key must appear in each drop's reason, at NOW with
# require_verified=True. Note WHY each one is dropped: legacy_orders_v1 is
# verified and fresh (status decides), promo_codes is verified (the expiry
# decides), revenue_dashboard is fresh and not deprecated (verification decides).
EXPECTED_DROPS = {
    "legacy_orders_v1": "status",
    "promo_codes": "stale_after",
    "revenue_dashboard": "verified",
}
EXPECTED_KEPT = ["customers", "metrics/daily_revenue", "orders"]


def check(label: str, ok: bool) -> bool:
    print(f"  [{'x' if ok else ' '}] {label}")
    return ok


def main() -> None:
    print("\n=== Task 3: trust gating on provenance, status, and staleness ===\n")

    concepts = _t1.load_bundle(BUNDLE_DIR)

    strict_kept, strict_dropped = trust_filter(concepts, NOW, require_verified=True)
    loose_kept, loose_dropped = trust_filter(concepts, NOW, require_verified=False)
    earlier_kept, earlier_dropped = trust_filter(concepts, EARLIER, require_verified=False)

    def show(title: str, kept: list[Concept], dropped: list[tuple[str, str]]) -> None:
        print(title)
        print(f"  kept:    {[c.id for c in kept]}")
        for cid, reason in dropped:
            print(f"  dropped: {cid:22} {reason}")
        print()

    show(f"now={NOW}, require_verified=True", strict_kept, strict_dropped)
    show(f"now={NOW}, require_verified=False", loose_kept, loose_dropped)
    show(f"now={EARLIER}, require_verified=False", earlier_kept, earlier_dropped)

    print("citations for the trusted set:")
    for c in strict_kept:
        print(f"  {provenance(c)}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    strict_drop_ids = [cid for cid, _ in strict_dropped]
    ok_kept = [c.id for c in strict_kept] == EXPECTED_KEPT
    ok_dropped = strict_drop_ids == list(EXPECTED_DROPS)
    ok_reasons = all(EXPECTED_DROPS[cid] in reason for cid, reason in strict_dropped)
    # The draft, unverified dashboard is the ONLY difference the flag makes.
    ok_flag = [c.id for c in loose_kept] == sorted([*EXPECTED_KEPT, "revenue_dashboard"])
    # Same bundle, earlier date: the promo snapshot had not expired yet.
    ok_time = [c.id for c in earlier_kept] == sorted(
        [*EXPECTED_KEPT, "promo_codes", "revenue_dashboard"]
    ) and [cid for cid, _ in earlier_dropped] == ["legacy_orders_v1"]
    orders_citation = provenance(next(c for c in concepts if c.id == "orders"))
    ok_citation = (
        "orders" in orders_citation
        and "reference_agent/llama3.2" in orders_citation
        and "human:learner" in orders_citation
    )

    print("\nAcceptance:")
    all_ok = [
        check(f"trusted set at {NOW} is exactly {EXPECTED_KEPT}", ok_kept),
        check("the other three are dropped, in rule order", ok_dropped),
        check(
            "each drop reason names the deciding key (status / stale_after / verified)", ok_reasons
        ),
        check("require_verified=False re-admits the unverified draft, and only that", ok_flag),
        check(
            f"at {EARLIER} the promo snapshot is fresh again (same files, different now)", ok_time
        ),
        check("the citation names the generating agent AND the human verifier", ok_citation),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
