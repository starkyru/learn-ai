"""
Task 1 🔴 — Parse and validate an OKF bundle (no YAML library).

What you'll learn:
  - An OKF (Open Knowledge Format) bundle is just a directory of markdown
    files with YAML frontmatter. There is no SDK, no query language, no
    service: `cat` is a valid client, and so is an LLM.
  - A concept's IDENTITY is its path: the concept id is the file's path inside
    the bundle with the `.md` suffix removed (`metrics/daily_revenue.md` →
    `metrics/daily_revenue`). Rename the file and you have renamed the concept.
  - `index.md` and `log.md` are RESERVED filenames — a directory listing and a
    changelog. They are not concepts and must be skipped at EVERY level.
  - `type` is the only always-required frontmatter key. A concept carrying just
    `type` is fully conformant; everything else is recommended or optional.

🔴 lane: parse the frontmatter YOURSELF. No `yaml`/`pyyaml` import — the point
is that the format is simple enough that you can. Real bundles need a real
parser; this bundle deliberately sticks to the documented "OKF-lite" subset:

    key: scalar                # string
    key: [a, b, c]             # flow list of strings
    key:                       # nested map (2-space indent)
      sub: scalar
    key:                       # list of maps (2-space indent, `- ` on first key)
      - sub: scalar
        sub2: scalar

No comments, no block scalars, no quoting rules, no type coercion (every scalar
stays a string). Two indent levels, that's it.

How to run:
  uv run python modules/16b-knowledge-bundles/py/01_parse_bundle.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[1] / "bundle"

#: Filenames the spec reserves — never concepts.
RESERVED_NAMES = frozenset({"index.md", "log.md"})


@dataclass
class Concept:
    """One OKF concept: its id, its parsed frontmatter, and its markdown body."""

    id: str
    meta: dict
    body: str


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split an OKF document into (frontmatter dict, markdown body).

    The document starts with a `---` fence line, then the OKF-lite YAML shown in
    the module docstring, then a closing `---`, then the body. Scalars stay
    strings; a `[a, b]` value becomes a `list[str]`; an indented `sub: value`
    block becomes a nested `dict`; an indented `- sub: value` block becomes a
    `list[dict]` (further-indented keys belong to the item the last `- ` opened).

    Raise `ValueError` when the document has no opening fence or the fence is
    never closed — a caller needs to tell "not a concept" from "broken concept".

    TODO: implement.
      - Split into lines. The first line must be the opening fence; find the
        index of the next `---` line after it (that is the closing fence).
      - The body is everything after the closing fence (strip the leading
        blank line so bodies start at real content).
      - Walk the lines BETWEEN the fences, skipping blank ones, and branch on
        the indent width (0 vs deeper) and on whether the stripped line starts
        with `- `. `str.partition(":")` splits one `key: value` line.
      - Track the most recent top-level key so an indented line knows which
        container it belongs to.
    """
    # TODO: parse the OKF-lite frontmatter into (meta, body)
    raise NotImplementedError("TODO: implement parse_frontmatter()")


def concept_id(root: Path, path: Path) -> str:
    """The concept id for a file: its bundle-relative posix path, minus `.md`.

    TODO: implement.
      - `Path.relative_to` + `Path.as_posix()` gives the portable relative path
        (use posix so the id is the same on Windows).
      - Strip exactly the `.md` suffix — do NOT use `str.strip(".md")`, which
        strips characters, not a suffix.
    """
    # TODO: derive the concept id from the file path
    raise NotImplementedError("TODO: implement concept_id()")


def load_bundle(root: Path) -> list[Concept]:
    """Every concept in the bundle, sorted by id, reserved filenames skipped.

    TODO: implement.
      - Walk `*.md` recursively (`Path.rglob`) so nested directories are
        included; sort so the result is deterministic.
      - Skip files whose NAME is in RESERVED_NAMES (at any depth).
      - Parse each remaining file into a `Concept` via parse_frontmatter() and
        concept_id().
    """
    # TODO: walk the bundle and build the Concept list
    raise NotImplementedError("TODO: implement load_bundle()")


def validate(concepts: list[Concept]) -> list[str]:
    """Conformance errors, one human-readable string each (empty list = valid).

    Two rules, both from the spec:
      - `type` is required and must be non-empty.
      - concept ids are unique within a bundle.

    Each message must name the offending concept id so the report is actionable.

    TODO: implement.
      - Collect a message for any concept whose `meta` has no usable `type`.
      - Track the ids you have seen and report a duplicate the second time it
        appears.
    """
    # TODO: return the list of conformance errors
    raise NotImplementedError("TODO: implement validate()")


# ---------------------------------------------------------------------------
# Broken documents  (provided — do not edit)
# ---------------------------------------------------------------------------

# Inline fixtures: your parser and validator must reject each of these, and the
# rejection must be a clean error — never a crash and never a silent pass.
BAD_NO_FENCE = "# Just a markdown file\n\nNo frontmatter here.\n"
BAD_UNTERMINATED = "---\ntype: table\ntitle: Never closed\n\n# Body\n"
BAD_NO_TYPE = "---\ntitle: Typeless\ndescription: Missing the one required key.\n---\n\n# Body\n"


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------

EXPECTED_IDS = [
    "customers",
    "legacy_orders_v1",
    "metrics/daily_revenue",
    "orders",
    "promo_codes",
    "revenue_dashboard",
]


def check(label: str, ok: bool) -> bool:
    print(f"  [{'x' if ok else ' '}] {label}")
    return ok


def main() -> None:
    print("\n=== Task 1: parse + validate an OKF bundle ===\n")

    concepts = load_bundle(BUNDLE_DIR)
    print(f"loaded {len(concepts)} concepts from {BUNDLE_DIR.name}/:")
    for c in concepts:
        print(f"  {c.id:24} type={c.meta.get('type', '?'):10} tags={c.meta.get('tags')}")

    errors = validate(concepts)
    print(f"\nconformance errors: {errors if errors else 'none'}")

    orders = next((c for c in concepts if c.id == "orders"), None)
    print("\norders frontmatter:")
    if orders is not None:
        for key, value in orders.meta.items():
            print(f"  {key:12} {value!r}")

    # Broken documents: each must raise ValueError (parse) or report an error.
    rejections: dict[str, str] = {}
    for name, doc in (
        ("no-fence", BAD_NO_FENCE),
        ("unterminated", BAD_UNTERMINATED),
    ):
        try:
            parse_frontmatter(doc)
            rejections[name] = "ACCEPTED (bug)"
        except ValueError as exc:
            rejections[name] = f"ValueError: {exc}"
    typeless_meta, _ = parse_frontmatter(BAD_NO_TYPE)
    typeless_errors = validate([Concept(id="typeless", meta=typeless_meta, body="")])
    print("\nbroken documents:")
    for name, outcome in rejections.items():
        print(f"  {name:14} {outcome}")
    print(f"  no-type        {typeless_errors}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    ok_ids = [c.id for c in concepts] == EXPECTED_IDS
    ok_reserved = all(not c.id.endswith("index") and not c.id.endswith("log") for c in concepts)
    ok_valid = errors == []
    ok_meta = orders is not None and (
        orders.meta.get("type") == "table"
        and orders.meta.get("tags") == ["sales", "core"]
        and orders.meta.get("generated", {}).get("by") == "reference_agent/llama3.2"
        and orders.meta.get("sources", [{}])[0].get("resource") == "warehouse/ddl/orders.sql"
        and orders.meta.get("sources", [{}])[0].get("title") == "Orders DDL"
        and len(orders.meta.get("sources", [])) == 2
        and orders.meta.get("verified", [{}])[0].get("by") == "human:learner"
    )
    ok_body = orders is not None and (
        orders.body.startswith("# Orders") and "type: table" not in orders.body
    )
    ok_rejects = all(outcome.startswith("ValueError") for outcome in rejections.values())
    ok_typeless = len(typeless_errors) == 1 and "type" in typeless_errors[0]

    print("\nAcceptance:")
    all_ok = [
        check(f"loads exactly {len(EXPECTED_IDS)} concepts, ids sorted as expected", ok_ids),
        check("reserved index.md / log.md files are skipped at every level", ok_reserved),
        check("the shipped bundle is conformant (no errors)", ok_valid),
        check("nested map, list-of-maps, and flow list all parsed (orders)", ok_meta),
        check("the body excludes the frontmatter and starts at '# Orders'", ok_body),
        check("no-fence and unterminated documents raise ValueError", ok_rejects),
        check("a document without `type` is reported by validate()", ok_typeless),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
