"""
Task 4 🔴 — The MemoryManager: composed lifecycle + TTL/staleness.

This file is STANDALONE: the working pieces you built in Tasks 1–3 (store
helpers, bag-of-words cosine retrieval, entity extraction + merge,
summarisation) are copied in below as PROVIDED code. This task is about the
COMPOSITION — one manager that runs the whole read side before the model call
and the whole write side after it, under a hard token budget:

    per turn:
        evict_stale(...)                        # forget
        ctx = mm.assemble_context(thread, q)    # read:  episodic -> semantic
                                                #        -> entities -> summaries
        reply = model(ctx + q)                  # the one model call
        mm.finalize_turn(thread, q, reply)      # write: episodic, entities,
                                                #        conditional summarisation

You implement:
  - MemoryManager.assemble_context — the fixed read order + the token budget
    (oldest history falls back to its summary instead of verbatim turns).
  - MemoryManager.finalize_turn — the write path: episodic write, entity
    extract+merge, summarise the oldest turns when history exceeds its budget.
  - evict_stale — TTL eviction for semantic records (fake clock, no real time).

Determinism: fake integer clock (one tick per turn), stub model, whitespace
token counter — no Date/time calls anywhere.

How to run:
  uv run python modules/06d-agent-memory/py/04_memory_manager.py --stub
  uv run python modules/06d-agent-memory/py/04_memory_manager.py
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ChatFn = Callable[[list[dict[str, str]]], str]

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
STORE_PATH = STATE_DIR / "py-04-memory-manager.json"

BUDGET = 110  # hard token budget for the assembled context (incl. the query)
HISTORY_BUDGET = 40  # when active-turn tokens exceed this, compact the oldest
KEEP_RECENT = 2  # records kept verbatim when compacting (1 exchange)
K = 2  # semantic top-k
MIN_SCORE = 0.35  # semantic relevance threshold (Task 2)
TTL = 3  # semantic records older than this many ticks are stale

SYSTEM = "You are a concise assistant. Ground your answer in the provided context."

EXTRACT_PROMPT = (
    "Extract entities from the text below. Return a JSON array of objects, "
    'each with exactly the string keys "name", "type", "fact". '
    "Return the JSON array only, no prose.\n\nText: {text}"
)

SUMMARY_PROMPT = "Summarise the following conversation turns in one short sentence:\n\n{turns}"


# ---------------------------------------------------------------------------
# PROVIDED — token counting + store (from Task 1)
# ---------------------------------------------------------------------------


def count_tokens(text: str) -> int:
    """Deterministic proxy tokenizer: whitespace-separated chunks."""
    return len(re.findall(r"\S+", text))


def new_store() -> dict:
    return {"episodic": [], "entities": [], "summaries": [], "semantic": {}}


def load_store(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return new_store()


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


def write_turn(store: dict, thread_id: str, role: str, content: str) -> None:
    store["episodic"].append(
        {
            "seq": len(store["episodic"]) + 1,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "archived_by": None,
        }
    )


def read_active_turns(store: dict, thread_id: str) -> list[dict]:
    """Non-archived turns of one thread, chronological."""
    return [
        t for t in store["episodic"] if t["thread_id"] == thread_id and t["archived_by"] is None
    ]


def turn_line(turn: dict) -> str:
    return f"{turn['role']}: {turn['content']}"


# ---------------------------------------------------------------------------
# PROVIDED — semantic retrieval with threshold (from Task 2)
# ---------------------------------------------------------------------------


def bag_of_words(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", text.lower()))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    dot = sum(a[w] * b[w] for w in a if w in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_semantic(store: dict, query: str, k: int, min_score: float) -> list[dict]:
    qv = bag_of_words(query)
    scored = [
        {"doc_id": doc_id, "text": rec["text"], "score": cosine(qv, bag_of_words(rec["text"]))}
        for doc_id, rec in store["semantic"].items()
    ]
    scored.sort(key=lambda r: -r["score"])
    return [r for r in scored[:k] if r["score"] >= min_score]


# ---------------------------------------------------------------------------
# PROVIDED — entity extraction + merge, summarisation (from Task 3)
# ---------------------------------------------------------------------------


def extract_entities(chat_fn: ChatFn, text: str) -> list[dict[str, str]]:
    raw = chat_fn([{"role": "user", "content": EXTRACT_PROMPT.format(text=text)}])
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"expected a JSON array of entities, got: {data!r}")
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) for key in ("name", "type", "fact")
        ):
            raise ValueError(f"bad entity record: {item!r}")
        out.append({"name": item["name"], "type": item["type"], "fact": item["fact"]})
    return out


def merge_entities(store: dict, new: list[dict[str, str]]) -> None:
    for entity in new:
        for existing in store["entities"]:
            if existing["name"] == entity["name"] and existing["type"] == entity["type"]:
                existing["fact"] = entity["fact"]
                break
        else:
            store["entities"].append(dict(entity))


def summarise_turns(chat_fn: ChatFn, turns: list[dict]) -> dict:
    rendered = "\n".join(turn_line(t) for t in turns)
    text = chat_fn([{"role": "user", "content": SUMMARY_PROMPT.format(turns=rendered)}])
    summary_id = f"sum-{turns[0]['seq']}-{turns[-1]['seq']}"
    for turn in turns:
        turn["archived_by"] = summary_id
    return {"summary_id": summary_id, "text": text, "turn_seqs": [t["seq"] for t in turns]}


# ---------------------------------------------------------------------------
# Core — YOU implement assemble_context, finalize_turn, evict_stale
# ---------------------------------------------------------------------------


class MemoryManager:
    """Owns the full lifecycle: read order, budget, writes, compaction."""

    def __init__(self, chat_fn: ChatFn, store: dict) -> None:
        self.chat_fn = chat_fn
        self.store = store

    def assemble_context(self, thread_id: str, query: str) -> tuple[str, int]:
        """Build the context block for one model call, under the token budget.

        Fixed read order of the sections in the returned text:
          1. "## Recent turns"       — active (non-archived) episodic turns
          2. "## Relevant knowledge" — semantic hits (top-K, thresholded)
          3. "## Known entities"     — every entity as "- name (type): fact"
          4. "## Summaries"          — summary texts standing in for archived turns

        The budget: sections 2–4 plus the query are the FIXED cost. Whatever
        token budget remains goes to episodic turns, filled NEWEST-first (so
        the oldest history is the first to fall back to its summary), then
        re-ordered chronologically for the final text.

        Return (context_text, total_tokens) where total_tokens counts the
        context text plus the query — the number the harness holds under BUDGET.

        TODO: implement.
          - Get semantic hits via retrieve_semantic (K, MIN_SCORE); render
            sections 2-4 as header + "- ..." lines (skip a section's lines,
            keep its header, when it is empty).
          - Compute the fixed token cost: count_tokens of all headers + the
            section 2-4 lines + the query (headers for section 1 included).
          - Walk read_active_turns(...) in REVERSE, adding turn_line(t) while
            its count_tokens still fits in BUDGET - fixed cost; then restore
            chronological order.
          - Join sections 1-4 (headers + lines) with newlines; return the text
            and count_tokens(text) + count_tokens(query).
        """
        # TODO: implement the fixed read order + the token budget
        raise NotImplementedError("TODO: implement MemoryManager.assemble_context()")

    def finalize_turn(self, thread_id: str, user_msg: str, reply: str) -> None:
        """The write path, AFTER the model call.

        In order:
          1. Episodic write: the user turn, then the assistant turn.
          2. Entity extract + merge on the user message.
          3. Conditional summarisation: if the active turns' total tokens
             exceed HISTORY_BUDGET (and there are more than KEEP_RECENT
             records), summarise all but the newest KEEP_RECENT records and
             append the summary record to store["summaries"].

        TODO: implement.
          - write_turn twice (user then assistant).
          - extract_entities on user_msg, merge_entities the result.
          - Sum count_tokens(turn_line(t)) over read_active_turns(...); when
            over HISTORY_BUDGET, call summarise_turns on the active turns
            minus the last KEEP_RECENT (it marks them archived) and append
            the returned record to store["summaries"].
        """
        # TODO: implement the write path (episodic, entities, conditional compaction)
        raise NotImplementedError("TODO: implement MemoryManager.finalize_turn()")


def evict_stale(store: dict, now: int, ttl: int) -> list[str]:
    """Forget: drop semantic records whose age exceeds the TTL.

    A record is stale when  now - created_at > ttl  (fake integer clock).
    Return the sorted list of evicted doc_ids (empty list when nothing is
    stale) and remove them from store["semantic"].

    TODO: implement.
      - Collect the doc_ids whose record is stale by the rule above (sorted).
      - Delete each from store["semantic"], then return the list.
    """
    # TODO: implement TTL eviction
    raise NotImplementedError("TODO: implement evict_stale()")


# ---------------------------------------------------------------------------
# PROVIDED — the no-management baseline
# ---------------------------------------------------------------------------


def baseline_tokens(store: dict, semantic_seed: dict, query: str) -> int:
    """What a memory-augmented (unmanaged) agent would send: EVERY turn
    verbatim + EVERY semantic doc (no threshold, no TTL) + the query."""
    parts = [turn_line(t) for t in store["episodic"]]
    parts += [rec["text"] for rec in semantic_seed.values()]
    parts.append(query)
    return count_tokens("\n".join(parts))


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: canned entity JSON, fixed summary, short replies."""

    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        if prompt.startswith("Extract entities"):
            if "leading the Atlas project" in prompt:
                return json.dumps(
                    [{"name": "Dana", "type": "person", "fact": "leads the Atlas project"}]
                )
            if "deadline moved" in prompt:
                return json.dumps(
                    [{"name": "Atlas", "type": "project", "fact": "deadline moved to Friday"}]
                )
            return "[]"
        if prompt.startswith("Summarise"):
            return "[compressed older turns]"
        return "[stub-reply] noted."

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

SEED_SEMANTIC = {
    "kb-promo": {"text": "The spring promo discount code SAVE10 expires soon.", "created_at": 0},
    "kb-pricing": {
        "text": "The pricing page lists the Pro plan at 20 dollars per month.",
        "created_at": 3,
    },
    "kb-deploy": {
        "text": "Deploys to production happen from the main branch via CI.",
        "created_at": 3,
    },
}

SCRIPT = [
    "Dana is leading the Atlas project for our team this quarter.",
    "What is the promo discount code for the Pro plan this spring?",
    "The Atlas project deadline moved to Friday because the billing migration is taking longer.",
    "Please draft a short status update covering the deadline change and the migration work.",
    "Is the promo discount code still valid for new signups today?",
    "Remind me, who leads the Atlas project?",
]

DANA_ENTITY_LINE = "- Dana (person): leads the Atlas project"


def main() -> None:
    ap = argparse.ArgumentParser(description="MemoryManager: composed lifecycle (Task 4).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 4: MemoryManager — {mode} ===\n")

    STORE_PATH.unlink(missing_ok=True)  # clean state on start
    store = new_store()
    store["semantic"] = {k: dict(v) for k, v in SEED_SEMANTIC.items()}
    mm = MemoryManager(chat_fn, store)

    evictions: dict[int, list[str]] = {}
    managed: list[int] = []
    baselines: list[int] = []
    contexts: list[str] = []

    print(f"token budget = {BUDGET}\n")
    for now, user_msg in enumerate(SCRIPT, start=1):  # fake clock: 1 tick per turn
        evicted = evict_stale(store, now, TTL)
        if evicted:
            evictions[now] = evicted
        ctx, n_tokens = mm.assemble_context("main", user_msg)
        reply = chat_fn(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"{ctx}\n\n{user_msg}"},
            ]
        )
        mm.finalize_turn("main", user_msg, reply)
        base = baseline_tokens(store, SEED_SEMANTIC, user_msg)
        managed.append(n_tokens)
        baselines.append(base)
        contexts.append(ctx)
        save_store(STORE_PATH, store)
        evic = f"  evicted={evicted}" if evicted else ""
        print(f"turn {now}: managed={n_tokens:>3} tokens   baseline={base:>3} tokens{evic}")

    print(f"\nsummaries made: {[s['summary_id'] for s in store['summaries']]}")
    entity_view = [f"{e['name']}: {e['fact']}" for e in store["entities"]]
    print(f"entities: {entity_view}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    if not args.stub:
        print("\nRun with --stub for the exact acceptance checks.")
        return

    # 1) Managed context stays under the budget on every turn...
    ok_budget = all(n <= BUDGET for n in managed)
    # 2) ...while the no-management baseline grows monotonically past it.
    ok_baseline = (
        all(b1 < b2 for b1, b2 in zip(baselines, baselines[1:], strict=False))
        and baselines[-1] > BUDGET
    )
    # 3) The stale semantic record is evicted at the right fake-clock tick...
    ok_evict = evictions == {4: ["kb-promo"]}
    # 4) ...and is no longer retrieved: turn 2 saw it, turn 5 must not.
    ok_gone = "SAVE10" in contexts[1] and "SAVE10" not in contexts[4]
    # 5) The entity from turn 1 is still cited in turn 6's context, even though
    #    turn 1's verbatim text has been compacted away.
    ok_entity = DANA_ENTITY_LINE in contexts[5] and SCRIPT[0] not in contexts[5]

    print("\nAcceptance:")
    print(
        f"  [{'x' if ok_budget else ' '}] managed context ≤ {BUDGET} tokens on all "
        f"{len(SCRIPT)} turns (max = {max(managed)})"
    )
    print(
        f"  [{'x' if ok_baseline else ' '}] baseline grows monotonically past the budget "
        f"(ends at {baselines[-1]})"
    )
    print(f"  [{'x' if ok_evict else ' '}] kb-promo evicted exactly at tick 4 (TTL={TTL})")
    print(f"  [{'x' if ok_gone else ' '}] SAVE10 retrieved at turn 2, gone by turn 5")
    print(f"  [{'x' if ok_entity else ' '}] turn-1 entity cited in turn 6 (verbatim turn 1 is not)")

    if all([ok_budget, ok_baseline, ok_evict, ok_gone, ok_entity]):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
