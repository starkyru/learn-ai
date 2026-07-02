"""
Task 3 🟡 — Entity memory + summary memory (with just-in-time expansion).

What you'll learn:
  - Entity memory keys facts by WHO/WHAT (name + type), not by when they were
    said. Extraction is a model call that must return STRUCTURED output (a
    JSON array) — so you parse and validate, never trust.
  - Merging is update-on-write for entities: the same (name, type) updates
    the fact in place; a new name appends. Without it every mention of "Dana"
    piles up a duplicate, and the stale fact competes with the fresh one.
  - Summary memory compresses old turns into one record — but it MARKS the
    originals (archived_by = summary_id), it never deletes them. That is what
    makes just-in-time expansion possible: when the agent actually needs the
    detail, `expand_summary` recovers the originals verbatim.

The records:

    turn:    {"seq": 3, "role": "user", "content": "...", "archived_by": None}
    entity:  {"name": "Dana", "type": "person", "fact": "CEO of Acme Corp"}
    summary: {"summary_id": "sum-1-4", "text": "...", "turn_seqs": [1, 2, 3, 4]}

OFFLINE: takes `chat_fn`. With --stub, extraction returns a fixed valid JSON
array and summarisation a fixed sentence, so assertions are exact; without
--stub the same prompts hit get_provider().chat (expect to harden the JSON
parsing for a real model!).

How to run:
  uv run python modules/06d-agent-memory/py/03_entity_summary.py --stub
  uv run python modules/06d-agent-memory/py/03_entity_summary.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

ChatFn = Callable[[list[dict[str, str]]], str]

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
STORE_PATH = STATE_DIR / "py-03-entity-summary.json"

EXTRACT_PROMPT = (
    "Extract entities from the text below. Return a JSON array of objects, "
    'each with exactly the string keys "name", "type", "fact". '
    "Return the JSON array only, no prose.\n\nText: {text}"
)

SUMMARY_PROMPT = "Summarise the following conversation turns in one short sentence:\n\n{turns}"


# ---------------------------------------------------------------------------
# JSON-file store  (provided — do not edit)
# ---------------------------------------------------------------------------


def new_store() -> dict:
    return {"turns": [], "entities": [], "summaries": []}


def load_store(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return new_store()


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def add_turn(store: dict, role: str, content: str) -> dict:
    """Append a turn with the next seq number; not archived yet."""
    turn = {"seq": len(store["turns"]) + 1, "role": role, "content": content, "archived_by": None}
    store["turns"].append(turn)
    return turn


def assemble_context(store: dict) -> str:
    """Render what the model would see: summaries stand in for archived turns."""
    lines = [f"[summary {s['summary_id']}] {s['text']}" for s in store["summaries"]]
    lines += [f"{t['role']}: {t['content']}" for t in store["turns"] if t["archived_by"] is None]
    lines += [f"{e['name']} ({e['type']}): {e['fact']}" for e in store["entities"]]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def extract_entities(chat_fn: ChatFn, text: str) -> list[dict[str, str]]:
    """Prompt the model for entities; parse + validate the JSON it returns.

    TODO: implement.
      - Fill EXTRACT_PROMPT with the text and send it as one user message via
        chat_fn.
      - Parse the reply with json.loads.
      - Validate the shape: the result must be a list; every item must be a
        dict whose "name", "type", "fact" values are all strings — raise
        ValueError (mention the offending item) otherwise.
      - Return the validated list of {"name", "type", "fact"} dicts.
    """
    # TODO: implement extract (prompt -> chat_fn -> json.loads -> validate)
    raise NotImplementedError("TODO: implement extract_entities()")


def merge_entities(store: dict, new: list[dict[str, str]]) -> None:
    """Update-on-write for entities: same (name, type) updates; new appends.

    TODO: implement.
      - For each new entity, scan store["entities"] for a record with the
        same name AND type; if found, overwrite its "fact" in place.
      - If none matches, append a copy of the new entity.
    """
    # TODO: implement update-on-write merging for entities
    raise NotImplementedError("TODO: implement merge_entities()")


def summarise_turns(chat_fn: ChatFn, turns: list[dict]) -> dict:
    """Compress turns into a summary record — mark the originals, don't delete.

    TODO: implement.
      - Render the turns as "role: content" lines and fill SUMMARY_PROMPT;
        send it as one user message via chat_fn to get the summary text.
      - Build a deterministic id from the covered range: "sum-<first>-<last>"
        using the first and last turn's seq.
      - Mark each turn: set its "archived_by" to the summary id (the turn
        objects live in the store, so this mutation is the archival).
      - Return {"summary_id", "text", "turn_seqs"} where turn_seqs lists the
        covered seq numbers.
    """
    # TODO: implement compaction (summarise via the model, mark originals, return the record)
    raise NotImplementedError("TODO: implement summarise_turns()")


def expand_summary(store: dict, summary_id: str) -> list[dict]:
    """Just-in-time expansion: recover the original turns behind a summary.

    TODO: implement.
      - Collect the turns in store["turns"] whose "archived_by" equals
        summary_id, sorted by seq, and return them (full records, verbatim).
    """
    # TODO: implement just-in-time expansion
    raise NotImplementedError("TODO: implement expand_summary()")


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: fixed valid JSON per known text; fixed summary."""

    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        if prompt.startswith("Extract entities"):
            if "promoted to CEO" in prompt:
                return json.dumps([{"name": "Dana", "type": "person", "fact": "CEO of Acme Corp"}])
            if "headquartered in Berlin" in prompt:
                return json.dumps(
                    [{"name": "Acme Corp", "type": "company", "fact": "headquartered in Berlin"}]
                )
            if "joined Acme Corp" in prompt:
                return json.dumps(
                    [
                        {"name": "Dana", "type": "person", "fact": "CTO of Acme Corp"},
                        {"name": "Acme Corp", "type": "company", "fact": "employs Dana as CTO"},
                    ]
                )
            return "[]"
        if prompt.startswith("Summarise"):
            return "Dana joined Acme Corp (Berlin) as CTO."
        return "[stub-reply] ok."

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

SCRIPT = [
    ("user", "Dana just joined Acme Corp as the new CTO."),
    ("assistant", "Noted - Dana is Acme Corp's CTO."),
    ("user", "Acme Corp is headquartered in Berlin."),
    ("assistant", "Got it: Acme Corp is based in Berlin."),
    ("user", "Update: Dana has been promoted to CEO of Acme Corp."),
    ("assistant", "Understood - Dana is now the CEO."),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Entity + summary memory (Task 3).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 3: entity + summary memory — {mode} ===\n")

    STORE_PATH.unlink(missing_ok=True)  # clean state on start
    store = new_store()

    # ── Ingest the conversation: turns + entity extraction on user turns ────
    for role, content in SCRIPT:
        add_turn(store, role, content)
        if role == "user":
            merge_entities(store, extract_entities(chat_fn, content))

    print("Entities after ingestion:")
    for e in store["entities"]:
        print(f"  {e['name']} ({e['type']}): {e['fact']}")

    # ── Compaction: summarise the first 4 turns (mark, don't delete) ────────
    ctx_before = assemble_context(store)
    old_turns = [t for t in store["turns"] if t["seq"] <= 4]
    record = summarise_turns(chat_fn, old_turns)
    store["summaries"].append(record)
    ctx_after = assemble_context(store)
    print(f"\nSummary record: {record['summary_id']!r} covering seqs {record['turn_seqs']}")
    print(f"Context size before compaction: {len(ctx_before)} chars")
    print(f"Context size after  compaction: {len(ctx_after)} chars")

    # ── "Restart": persist, then reload the store fresh from disk ───────────
    save_store(STORE_PATH, store)
    store2 = load_store(STORE_PATH)

    dana = [e for e in store2["entities"] if e["name"] == "Dana"]
    expanded = expand_summary(store2, record["summary_id"])
    print("\nAfter restart (fresh load from disk):")
    print(f"  Dana entries: {dana}")
    print(f"  expand_summary({record['summary_id']!r}) -> {len(expanded)} original turns")

    # ── Acceptance checks ────────────────────────────────────────────────────
    if not args.stub:
        print("\nRun with --stub for the exact acceptance checks.")
        return

    # 1) Known entities recalled across a restart, with the LATEST fact.
    ok_recall = len(dana) == 1 and dana[0]["fact"] == "CEO of Acme Corp"
    # 2) Merging updates instead of duplicating: 2 entities total, both fresh.
    acme = [e for e in store2["entities"] if e["name"] == "Acme Corp"]
    ok_merge = (
        len(store2["entities"]) == 2
        and len(acme) == 1
        and acme[0]["fact"] == "headquartered in Berlin"
    )
    # 3) Compaction shrinks the assembled context.
    ok_shorter = len(ctx_after) < len(ctx_before)
    # 4) Just-in-time expansion recovers the originals verbatim (post-restart).
    ok_expand = [(t["role"], t["content"]) for t in expanded] == SCRIPT[:4]
    # 5) Mark, don't delete: the store still holds all 6 turns.
    ok_marked = (
        len(store2["turns"]) == 6
        and sum(1 for t in store2["turns"] if t["archived_by"] == record["summary_id"]) == 4
    )

    print("\nAcceptance:")
    print(
        f"  [{'x' if ok_recall else ' '}] Dana recalled across restart with the merged fact (CEO)"
    )
    print(f"  [{'x' if ok_merge else ' '}] merging updates in place — 2 entities, no duplicates")
    print(
        f"  [{'x' if ok_shorter else ' '}] context shorter after compaction "
        f"({len(ctx_before)} -> {len(ctx_after)} chars)"
    )
    print(f"  [{'x' if ok_expand else ' '}] expand_summary recovers the 4 original turns verbatim")
    print(f"  [{'x' if ok_marked else ' '}] originals marked archived, never deleted")

    if all([ok_recall, ok_merge, ok_shorter, ok_expand, ok_marked]):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
