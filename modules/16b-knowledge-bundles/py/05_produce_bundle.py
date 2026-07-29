"""
Task 5 🟢 — Produce a bundle: emit conformant OKF, then check your own output.

What you'll learn:
  - Anyone can PRODUCE OKF: a human with an editor, an export pipeline, or an
    agent walking a database. The format is the contract, not the producer.
  - The division of labour that keeps generated knowledge trustworthy: the MODEL
    writes prose (title, description, tags), the CODE writes structure (`type`,
    `resource`, `generated.by`, `generated.at`). Never let the model invent the
    provenance of its own output.
  - Serialising frontmatter is the exact inverse of Task 1's parser, so the
    honest test is a ROUND TRIP: parse what you rendered and compare it to what
    you meant. A generator that cannot be re-read is not a generator.
  - `generated: { by, at }` is what makes a bundle auditable later: `by` uses
    the actor convention `<producer>/<version>` for agents, `human:<id>` for
    people, `process:<id>` for automation.

Determinism: the timestamp is a fixed constant, not a clock read — a generator
whose output changes on every run cannot be diffed in git, which is half the
reason the format is files in the first place.

Prerequisites: Task 1 (`parse_frontmatter`, `load_bundle`, `validate`) and
Task 2 (`build_index`).

How to run:
  uv run python modules/16b-knowledge-bundles/py/05_produce_bundle.py --stub
  uv run python modules/16b-knowledge-bundles/py/05_produce_bundle.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path

ChatFn = Callable[[list[dict[str, str]]], str]

OUT_DIR = Path(__file__).resolve().parents[1] / "out"

#: Stamped into every concept this generator writes (never read from a clock).
GENERATED_BY = "reference_agent/16b"
GENERATED_AT = "2026-07-29T00:00:00Z"


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


# ---------------------------------------------------------------------------
# Raw input  (provided — do not edit)
# ---------------------------------------------------------------------------

# What a producer actually starts from: a name, a kind, a resource URI, and an
# unstructured dump. No titles, no descriptions, no tags — that is the gap the
# model fills.
RAW_TABLES: list[dict[str, str]] = [
    {
        "name": "shipments",
        "kind": "table",
        "resource": "bigquery://acme-retail/warehouse/shipments",
        "raw": (
            "CREATE TABLE shipments (shipment_id STRING, order_id STRING, "
            "carrier STRING, handed_over_at TIMESTAMP, delivered_at TIMESTAMP);\n"
            "-- one row per parcel handed to a carrier; a cancelled order has no row"
        ),
    },
    {
        "name": "returns",
        "kind": "table",
        "resource": "bigquery://acme-retail/warehouse/returns",
        "raw": (
            "CREATE TABLE returns (return_id STRING, order_id STRING, "
            "reason_code STRING, refunded_cents INT64);\n"
            "-- reason_code is a free-text-ish enum maintained by support, not analytics"
        ),
    },
    {
        "name": "warehouse_zones",
        "kind": "table",
        "resource": "bigquery://acme-retail/ops/warehouse_zones",
        "raw": (
            "CREATE TABLE warehouse_zones (zone_id STRING, site STRING, "
            "temperature_c INT64);\n"
            "-- chilled zones have temperature_c below 8; ambient zones are NULL"
        ),
    },
]


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def describe_concept(chat_fn: ChatFn, raw: dict[str, str]) -> dict:
    """Ask the model for the PROSE fields only, and validate what comes back.

    Return `{"title": str, "description": str, "tags": list[str]}` and nothing
    else — the structural fields are the caller's job, not the model's.

    Prompt the model to answer as a single JSON object with exactly those three
    keys, and include the raw dump so it has something to describe (the offline
    stub also looks for the table name in your prompt, so pass the raw text
    through). Then parse the reply and reject anything malformed: a real model
    will wrap JSON in prose sooner or later, and a silent `{}` here becomes a
    conformance failure three steps downstream.

    TODO: implement.
      - Build a `list[dict]` of chat messages asking for those three keys as
        JSON, with the raw dump included.
      - Call `chat_fn`, then `json.loads` the reply — slice from the first `{`
        to the last `}` first if you want to tolerate a chatty model.
      - Validate: all three keys present, `title`/`description` non-empty
        strings, `tags` a list of strings. Raise `ValueError` otherwise.
      - Return only those three keys.
    """
    # TODO: get + validate the model-written prose fields
    raise NotImplementedError("TODO: implement describe_concept()")


def render_frontmatter(meta: dict) -> str:
    """Serialise a metadata dict back into the OKF-lite YAML of Task 1.

    The inverse of `parse_frontmatter`, and it must round-trip: parsing your
    output has to return the dict you started from. Handle the three shapes the
    subset allows — a string scalar, a `list[str]` (flow style `[a, b]`), and a
    `dict[str, str]` (a nested block, two-space indent). Preserve key order.

    Do not emit the `---` fences here; that is `render_concept`'s job.

    TODO: implement.
      - Walk `meta.items()` and branch on the value's type.
      - Lists render on one line; dicts render as `key:` then one indented
        `sub: value` line per entry.
      - End with a newline so the closing fence lands on its own line.
    """
    # TODO: render the frontmatter block
    raise NotImplementedError("TODO: implement render_frontmatter()")


def conformance_check(text: str) -> list[str]:
    """Errors in one rendered document — empty list means conformant.

    This is the gate a generator runs on its OWN output before writing it:
      - it must parse (Task 1's `parse_frontmatter` raises if it does not);
      - `type` must be present (Task 1's `validate` rule);
      - `generated.by` and `generated.at` must both be stamped, or the concept
        is unauditable;
      - the body must be non-empty.

    Return human-readable messages; never raise.

    TODO: implement.
      - Call `_t1.parse_frontmatter(text)` inside a try/except ValueError and
        return the parse failure as a single message.
      - Reuse `_t1.validate` for the `type` and id rules by wrapping the parsed
        result in a `_t1.Concept`.
      - Add your own checks for the `generated` sub-keys and the empty body.
    """
    # TODO: return the list of conformance errors for this rendered document
    raise NotImplementedError("TODO: implement conformance_check()")


# ---------------------------------------------------------------------------
# Rendering + the stub/real model  (provided — do not edit)
# ---------------------------------------------------------------------------


def render_concept(meta: dict, body: str) -> str:
    """A full OKF document: fenced frontmatter, then the markdown body."""
    return f"---\n{render_frontmatter(meta)}---\n\n{body}"


def build_meta(raw: dict[str, str], prose: dict) -> dict:
    """Structure from the producer, prose from the model, provenance from us."""
    return {
        "type": raw["kind"],
        "title": prose["title"],
        "description": prose["description"],
        "resource": raw["resource"],
        "tags": prose["tags"],
        "status": "draft",
        "generated": {"by": GENERATED_BY, "at": GENERATED_AT},
    }


# The deterministic offline model: it finds the table name in the prompt and
# returns fixed JSON for it, so the acceptance checks are exact.
STUB_PROSE: dict[str, dict] = {
    "shipments": {
        "title": "Shipments",
        "description": "One row per parcel handed to a carrier.",
        "tags": ["logistics", "core"],
    },
    "returns": {
        "title": "Returns",
        "description": "One row per returned order line, with refund amount.",
        "tags": ["support", "core"],
    },
    "warehouse_zones": {
        "title": "Warehouse zones",
        "description": "Storage zones per site, with chilled-zone temperatures.",
        "tags": ["ops"],
    },
}


def make_stub_chat_fn() -> ChatFn:
    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        for name, prose in STUB_PROSE.items():
            if name in prompt:
                return json.dumps(prose)
        return "{}"  # nothing recognisable in the prompt — let validation fail

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def check(label: str, ok: bool) -> bool:
    print(f"  [{'x' if ok else ' '}] {label}")
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Produce an OKF bundle (Task 5).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 5: produce an OKF bundle — {mode} ===\n")

    if OUT_DIR.exists():
        for stale in OUT_DIR.glob("*.md"):
            stale.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rendered: dict[str, str] = {}
    round_trips: dict[str, bool] = {}
    errors: dict[str, list[str]] = {}
    for raw in RAW_TABLES:
        prose = describe_concept(chat_fn, raw)
        meta = build_meta(raw, prose)
        body = f"# {meta['title']}\n\n{meta['description']}\n\n```sql\n{raw['raw']}\n```\n"
        document = render_concept(meta, body)

        rendered[raw["name"]] = document
        errors[raw["name"]] = conformance_check(document)
        parsed_meta, _ = _t1.parse_frontmatter(document)
        round_trips[raw["name"]] = parsed_meta == meta

        (OUT_DIR / f"{raw['name']}.md").write_text(document, encoding="utf-8")
        print(f"wrote out/{raw['name']}.md  ({len(document)} chars)")
        print(
            f"  round-trips: {round_trips[raw['name']]}   conformance: {errors[raw['name']] or 'ok'}"
        )

    # Produce the index too — the consumer side (Task 2) reads this first.
    written = _t1.load_bundle(OUT_DIR)
    (OUT_DIR / "index.md").write_text(_t2.build_index(written) + "\n", encoding="utf-8")
    print(f"\nwrote out/index.md ({len(written)} concepts)")
    print("\n--- out/shipments.md ---")
    print(rendered["shipments"])

    # A deliberately broken document: the generator must catch its own mistake.
    broken = render_concept({"title": "No type here"}, "# Body\n")
    broken_errors = conformance_check(broken)
    unauditable = render_concept({"type": "table", "title": "No provenance"}, "# Body\n")
    unauditable_errors = conformance_check(unauditable)
    print(f"\nbroken document errors:      {broken_errors}")
    print(f"unauditable document errors: {unauditable_errors}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    if not args.stub:
        print("\nRun with --stub for the exact acceptance checks.")
        return

    ok_written = sorted(p.name for p in OUT_DIR.glob("*.md")) == [
        "index.md",
        "returns.md",
        "shipments.md",
        "warehouse_zones.md",
    ]
    ok_round_trip = all(round_trips.values())
    ok_conformant = all(errs == [] for errs in errors.values())
    ok_loadable = [c.id for c in written] == ["returns", "shipments", "warehouse_zones"]
    ok_valid = _t1.validate(written) == []
    ok_provenance = all(
        c.meta.get("generated", {}).get("by") == GENERATED_BY
        and c.meta.get("generated", {}).get("at") == GENERATED_AT
        for c in written
    )
    ok_prose = any(
        c.meta.get("description") == STUB_PROSE["returns"]["description"] for c in written
    )
    ok_catches_type = any("type" in e for e in broken_errors)
    ok_catches_provenance = any("generated" in e for e in unauditable_errors)

    print("\nAcceptance:")
    all_ok = [
        check("three concepts plus an index written to out/", ok_written),
        check("every rendered document round-trips through Task 1's parser", ok_round_trip),
        check("every rendered document passes its own conformance check", ok_conformant),
        check("the written bundle re-loads as 3 concepts and validates", ok_loadable and ok_valid),
        check("generated.by / generated.at are stamped by the code, not the model", ok_provenance),
        check("the model's prose (title/description/tags) made it into the frontmatter", ok_prose),
        check("a document missing `type` is caught by conformance_check", ok_catches_type),
        check("a document missing `generated` provenance is caught too", ok_catches_provenance),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
