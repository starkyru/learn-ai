"""
Task 1 🟢 — Episodic memory + the read/write lifecycle.

What you'll learn:
  - Episodic memory is the agent's conversation history: WHAT was said, in
    order, per thread. It is the one memory every chat app already has — the
    point here is to manage it deliberately instead of letting it happen.
  - The lifecycle: memory READS run BEFORE the model call (so the context the
    model sees is assembled from the store), memory WRITES run AFTER (so the
    turn that just happened is persisted for the next call).
  - Thread isolation: a store holds many conversations; a read must return
    only the requested thread's turns, never a neighbour's.

The turn shape (one JSON record per message in the store):

    {"thread_id": "A", "role": "user" | "assistant", "content": "..."}

The lifecycle you are wiring (run_turn below is provided — read it):

    load store  →  READ episodic  →  build context  →  model call
                →  WRITE user turn + assistant turn  →  save store

OFFLINE: takes `chat_fn: Callable[[list[dict]], str]`. With --stub the fake
model deterministically echoes what history it saw; without --stub it wraps
get_provider().chat (never a hardcoded vendor).

How to run:
  uv run python modules/06d-agent-memory/py/01_episodic.py --stub
  uv run python modules/06d-agent-memory/py/01_episodic.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

ChatFn = Callable[[list[dict[str, str]]], str]

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
STORE_PATH = STATE_DIR / "py-01-episodic.json"

SYSTEM = "You are a concise assistant. Use the conversation history when it helps."
LAST_N = 6  # how many past turns a read may inject


# ---------------------------------------------------------------------------
# JSON-file store  (provided — do not edit)
# ---------------------------------------------------------------------------


def new_store() -> dict:
    return {"episodic": []}


def load_store(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return new_store()


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def read_episodic(store: dict, thread_id: str, last_n: int) -> list[dict[str, str]]:
    """Return the last `last_n` turns of ONE thread as chat messages.

    The store keeps every thread's turns in one flat `store["episodic"]` list
    (each record has "thread_id", "role", "content"). A read must:
      - keep only the records whose thread_id matches (isolation),
      - preserve their original order (the list is already chronological),
      - keep only the LAST `last_n` of them (the injection bound),
      - return them as chat messages: dicts with just "role" and "content"
        (the model never sees thread_id).

    TODO: implement.
      - Filter store["episodic"] by thread_id.
      - Slice the last `last_n` records.
      - Map each record to a {"role": ..., "content": ...} dict and return the list.
    """
    # TODO: implement the episodic read (filter -> slice -> map)
    raise NotImplementedError("TODO: implement read_episodic()")


def write_episodic(store: dict, thread_id: str, role: str, content: str) -> None:
    """Append one turn record to the store (the WRITE half of the lifecycle).

    TODO: implement.
      - Append a dict with the three keys "thread_id", "role", "content" to
        store["episodic"] so the flat list stays chronological across threads.
    """
    # TODO: implement the episodic write (append one record)
    raise NotImplementedError("TODO: implement write_episodic()")


def build_context(
    system: str, episodic: list[dict[str, str]], user_msg: str
) -> list[dict[str, str]]:
    """Assemble the ordered message list the model will see.

    Order matters: system message first, then the episodic turns (already
    chronological), then the new user message last.

    TODO: implement.
      - Return a list[dict[str, str]] of chat messages: one system message
        built from `system`, followed by the episodic messages, ending with
        one user message built from `user_msg`.
    """
    # TODO: implement the ordered context assembly
    raise NotImplementedError("TODO: implement build_context()")


# ---------------------------------------------------------------------------
# One memory-aware turn  (provided — this IS the lifecycle; read it)
# ---------------------------------------------------------------------------


def run_turn(
    chat_fn: ChatFn, path: Path, thread_id: str, user_msg: str
) -> tuple[list[dict[str, str]], str]:
    store = load_store(path)  # reload from disk — proves persistence
    episodic = read_episodic(store, thread_id, LAST_N)  # READ before the call
    context = build_context(SYSTEM, episodic, user_msg)
    reply = chat_fn(context)  # the model call
    write_episodic(store, thread_id, "user", user_msg)  # WRITE after the call
    write_episodic(store, thread_id, "assistant", reply)
    save_store(path, store)
    return context, reply


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: echo how much (and which) history the model saw."""

    def chat_fn(messages: list[dict[str, str]]) -> str:
        hist = [m["content"] for m in messages[1:-1]]  # between system and new user msg
        user = messages[-1]["content"]
        digest = " | ".join(h[:40] for h in hist) if hist else "(none)"
        return f"[stub] reply to '{user}' after {len(hist)} history msgs: {digest}"

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


def main() -> None:
    ap = argparse.ArgumentParser(description="Episodic memory lifecycle (Task 1).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 1: episodic memory — {mode} ===\n")

    STORE_PATH.unlink(missing_ok=True)  # clean state on start

    # Two threads, interleaved — the store must keep them apart.
    a1 = "alpha thread: my favourite colour is teal"
    b1 = "bravo thread: my favourite colour is orange"
    a2 = "alpha thread: what colour do I like?"
    b2 = "bravo thread: what colour do I like?"

    contexts: dict[str, list[list[dict[str, str]]]] = {"A": [], "B": []}
    replies: dict[str, list[str]] = {"A": [], "B": []}
    for thread_id, msg in [("A", a1), ("B", b1), ("A", a2), ("B", b2)]:
        ctx, reply = run_turn(chat_fn, STORE_PATH, thread_id, msg)
        contexts[thread_id].append(ctx)
        replies[thread_id].append(reply)
        print(f"[{thread_id}] user: {msg}")
        print(f"[{thread_id}] assistant: {reply}\n")

    store = load_store(STORE_PATH)
    a_entries = [e for e in store["episodic"] if e["thread_id"] == "A"]
    b_entries = [e for e in store["episodic"] if e["thread_id"] == "B"]
    print(f"Store after the run: {len(a_entries)} A-entries, {len(b_entries)} B-entries")

    # ── Acceptance checks ────────────────────────────────────────────────────
    if not args.stub:
        print("\nRun with --stub for the exact acceptance checks.")
        return

    # 1) Isolation: thread A's contexts never contain thread B's turns (and v.v.).
    ok_isolation = all("bravo" not in m["content"] for ctx in contexts["A"] for m in ctx) and all(
        "alpha" not in m["content"] for ctx in contexts["B"] for m in ctx
    )

    # 2) Order preserved: A's episodic reads back user/assistant alternating,
    #    chronologically.
    expected_a = [
        {"role": "user", "content": a1},
        {"role": "assistant", "content": replies["A"][0]},
        {"role": "user", "content": a2},
        {"role": "assistant", "content": replies["A"][1]},
    ]
    ok_order = read_episodic(store, "A", 10) == expected_a

    # 3) Counts: 2 turns per thread → 4 records each (user + assistant per turn).
    ok_counts = len(a_entries) == 4 and len(b_entries) == 4 and len(store["episodic"]) == 8

    # 4) The last_n bound is respected.
    ok_lastn = read_episodic(store, "A", 2) == expected_a[-2:]

    # 5) Context shape: system first, new user message last, episodic between.
    last_ctx = contexts["A"][-1]
    ok_shape = (
        last_ctx[0] == {"role": "system", "content": SYSTEM}
        and last_ctx[-1] == {"role": "user", "content": a2}
        and len(last_ctx) == 2 + 2  # system + 2 episodic (turn 1) + user
    )

    print("\nAcceptance:")
    print(f"  [{'x' if ok_isolation else ' '}] thread A's context never contains thread B's turns")
    print(f"  [{'x' if ok_order else ' '}] turn order preserved on read-back")
    print(
        f"  [{'x' if ok_counts else ' '}] store holds 4 A-entries + 4 B-entries after 2 turns each"
    )
    print(f"  [{'x' if ok_lastn else ' '}] last_n bound respected (read of 2 returns the last 2)")
    print(f"  [{'x' if ok_shape else ' '}] context ordered: system → episodic → new user msg")

    if all([ok_isolation, ok_order, ok_counts, ok_lastn, ok_shape]):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
