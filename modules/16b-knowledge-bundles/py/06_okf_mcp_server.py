"""
Task 6 🟢 — Serve the bundle over MCP (Model Context Protocol).

What you'll learn:
  - Because a bundle is just files, serving it is a 3-tool MCP server: list,
    read, search. That is the whole interface Google's own reference
    implementation exposes over a markdown knowledge base (`list_contents`,
    `read_file`, `search_content`) — the format does the heavy lifting.
  - Progressive disclosure becomes the CLIENT's job once it is served: the
    model calls `list_concepts` (cheap), decides, then calls `read_concept`
    (expensive) only for what it needs. Task 2 did this in one process; MCP
    turns it into a protocol any agent can drive.
  - `search_concepts` returns line-level hits so a model can locate a fact
    without reading whole documents — the same "reference, then retrieve on
    demand" pattern as module 16's tool-output offloading.

The three tools are ordinary functions with a `--selftest` path, so you can get
them right offline before any protocol is involved. Wiring them into an MCP
server is the last step.

Wire it into Claude Code (or any MCP client) once it runs — add to `.mcp.json`
in the repo root:

    {
      "mcpServers": {
        "okf-bundle": {
          "command": "uv",
          "args": ["run", "python", "modules/16b-knowledge-bundles/py/06_okf_mcp_server.py"]
        }
      }
    }

Prerequisite: Task 1 (`load_bundle`). Python deps: `uv sync --extra mcp`.

How to run:
  uv run python modules/16b-knowledge-bundles/py/06_okf_mcp_server.py --selftest
  uv run --extra mcp python modules/16b-knowledge-bundles/py/06_okf_mcp_server.py
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parents[1] / "bundle"


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


# ---------------------------------------------------------------------------
# The three tools — YOU implement these
# ---------------------------------------------------------------------------


def list_concepts(prefix: str = "") -> list[str]:
    """Concept ids in the bundle, sorted; optionally restricted to a prefix.

    `prefix=""` lists everything; `prefix="metrics/"` lists one subdirectory.
    This is the CHEAP call — ids only, no bodies.

    TODO: implement.
      - Load the bundle with `_t1.load_bundle(BUNDLE_DIR)` and return the ids
        that start with `prefix` (sorted; `load_bundle` already sorts).
    """
    # TODO: list the concept ids under a prefix
    raise NotImplementedError("TODO: implement list_concepts()")


def read_concept(concept_id: str) -> str:
    """The full document text for one concept id — frontmatter fences included.

    Return the file's text VERBATIM (not a re-render): a client that reads a
    concept must see exactly what is on disk, provenance and all.

    Raise `KeyError` naming the id when it does not exist — a served tool that
    returns "" for a typo is a debugging trap.

    TODO: implement.
      - Map the id back to a path: `BUNDLE_DIR / f"{concept_id}.md"`.
      - Guard against a missing file, and against an id that escapes the bundle
        (a client-supplied `../../etc/passwd` must not be readable — resolve the
        path and confirm it is still inside BUNDLE_DIR).
      - Return `Path.read_text`.
    """
    # TODO: read one concept document verbatim
    raise NotImplementedError("TODO: implement read_concept()")


def search_concepts(query: str, max_hits: int = 5) -> list[dict]:
    """Line-level, case-insensitive substring search across concept BODIES.

    Return up to `max_hits` dicts `{"id": str, "line": int, "text": str}` where
    `line` is the 1-based line number WITHIN THE BODY (frontmatter excluded, so
    the numbers line up with what a reader sees after the fences) and `text` is
    the matching line, stripped.

    Order: by concept id, then by line number — deterministic, so a model gets
    the same answer twice.

    TODO: implement.
      - Load the bundle; for each concept, enumerate `Concept.body.split("\\n")`
        starting at 1.
      - Compare lowercased line against lowercased query (substring).
      - Stop once you have `max_hits` results.
    """
    # TODO: search bodies and return line-level hits
    raise NotImplementedError("TODO: implement search_concepts()")


# ---------------------------------------------------------------------------
# MCP server — YOU implement this
# ---------------------------------------------------------------------------


def build_server():
    """Create the MCP server and register the three tools.

    TODO: implement (see module 17 Task 3 for the same shape).
      - Import `Server` from `mcp.server`, `InitializationOptions` from
        `mcp.server.models`, and `mcp.types as types` INSIDE this function, so
        `--selftest` still runs without the `mcp` extra installed.
      - Create a `Server(...)` named for this bundle.
      - Register a `@server.list_tools()` handler returning a `list[types.Tool]`
        that advertises the three tools with JSON-Schema `inputSchema`s:
          * list_concepts   — optional "prefix" (string)
          * read_concept    — required "concept_id" (string)
          * search_concepts — required "query" (string), optional "max_hits"
        The descriptions matter: they are the only documentation the model gets.
        Say that list is cheap and read is expensive.
      - Register a `@server.call_tool()` handler that dispatches on the tool
        name, calls the function above, and returns a single
        `types.TextContent`. Turn a `KeyError` into an error message rather
        than letting it escape as a protocol error.
      - Return the configured server.
    """
    # TODO: build and return the MCP server
    raise NotImplementedError("TODO: implement build_server()")


def serve() -> None:
    """Run the server over the stdio transport.

    TODO: implement.
      - `build_server()`, then open `mcp.server.stdio.stdio_server()` to get the
        (read_stream, write_stream) pair and `await server.run(...)` with an
        `InitializationOptions` carrying the server name, a version, and
        `server.get_capabilities(...)`.
      - Drive the coroutine with `asyncio.run`.
    """
    # TODO: start the stdio MCP server
    raise NotImplementedError("TODO: implement serve()")


# ---------------------------------------------------------------------------
# Offline self-test  (provided — do not edit)
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


def selftest() -> None:
    print("\n=== Task 6: OKF over MCP — offline self-test of the three tools ===\n")

    all_ids = list_concepts()
    nested = list_concepts("metrics/")
    document = read_concept("orders")
    needle_hits = search_concepts("412,900")
    settlement_hits = search_concepts("settlement", max_hits=10)
    capped = search_concepts("settlement", max_hits=1)
    empty = search_concepts("no-such-string-anywhere")

    try:
        read_concept("does_not_exist")
        missing_error = "RETURNED (bug)"
    except KeyError as exc:
        missing_error = f"KeyError: {exc}"
    try:
        read_concept("../../../etc/passwd")
        escape_error = "RETURNED (bug)"
    except (KeyError, ValueError) as exc:
        escape_error = f"{type(exc).__name__}: {exc}"

    print(f"list_concepts()          -> {all_ids}")
    print(f"list_concepts('metrics/')-> {nested}")
    print(
        f"read_concept('orders')   -> {len(document)} chars, first line {document.splitlines()[0]!r}"
    )
    print(f"search('412,900')        -> {needle_hits}")
    print(f"search('settlement')     -> {[(h['id'], h['line']) for h in settlement_hits]}")
    print(f"read_concept(missing)    -> {missing_error}")
    print(f"read_concept(escaping)   -> {escape_error}")

    ok_list = all_ids == EXPECTED_IDS
    ok_prefix = nested == ["metrics/daily_revenue"]
    ok_verbatim = (
        document.startswith("---") and "type: table" in document and "# Orders" in document
    )
    ok_missing = missing_error.startswith("KeyError") and "does_not_exist" in missing_error
    ok_escape = not escape_error.startswith("RETURNED")
    ok_needle = (
        needle_hits == [{"id": "metrics/daily_revenue", "line": 7, "text": needle_hits[0]["text"]}]
        and "412,900" in needle_hits[0]["text"]
    )
    ok_multi = len(settlement_hits) == 4 and {h["id"] for h in settlement_hits} == {
        "metrics/daily_revenue",
        "orders",
    }
    ok_cap = len(capped) == 1
    ok_empty = empty == []

    print("\nAcceptance:")
    all_ok = [
        check("list_concepts() returns all 6 ids, sorted", ok_list),
        check("a prefix narrows the listing to the metrics/ subdirectory", ok_prefix),
        check("read_concept returns the document verbatim, fences included", ok_verbatim),
        check("an unknown id raises KeyError naming the id", ok_missing),
        check("an id escaping the bundle root is refused", ok_escape),
        check("search finds the needle at body line 7 of metrics/daily_revenue", ok_needle),
        check("search spans concepts: 4 'settlement' hits across 2 concepts", ok_multi),
        check("max_hits caps the result set; a miss returns []", ok_cap and ok_empty),
    ]
    if all(all_ok):
        print("\n  All acceptance checks passed.")
        print("  Now wire build_server() / serve() up and point an MCP client at it.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Serve an OKF bundle over MCP (Task 6).")
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="exercise the three tools offline instead of starting the server",
    )
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        serve()


if __name__ == "__main__":
    main()
