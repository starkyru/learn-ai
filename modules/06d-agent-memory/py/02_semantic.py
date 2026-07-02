"""
Task 2 🟡 — Semantic memory with a relevance threshold (noisy retrieval).

What you'll learn:
  - Semantic memory is the agent's knowledge base: facts looked up by
    MEANING (similarity search), not by recency. We rank with bag-of-words
    cosine (module 06c's trick) so it's offline and deterministic.
  - Noisy retrieval: top-k ALWAYS returns k results, even when the k-th one
    is a semantically-adjacent-but-wrong-topic distractor. The mitigation is
    a relevance threshold: drop results scoring below `min_score`.
  - Update-on-write: `upsert` keyed by doc_id REPLACES a changed fact instead
    of appending a duplicate — otherwise retrieval can surface the stale
    version of the truth next to the fresh one.

The math (same as 06c Task 2):

    cosine(a, b) = (a · b) / (||a|| * ||b||)

    a · b = Σ_w a[w]·b[w]  over shared words;  ||a|| = sqrt(Σ_w a[w]²)
    Zero norm on either side → similarity 0.

OFFLINE: retrieval never needs a model. The final "inject" step (answer the
question grounded in retrieved memory) takes `chat_fn`; with --stub the fake
model echoes the memory it was given, without --stub it wraps
get_provider().chat.

How to run:
  uv run python modules/06d-agent-memory/py/02_semantic.py --stub
  uv run python modules/06d-agent-memory/py/02_semantic.py
"""

from __future__ import annotations

import argparse
import json
import math  # noqa: F401 — the cosine() TODO below uses math.sqrt
import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ChatFn = Callable[[list[dict[str, str]]], str]

STATE_DIR = Path(__file__).resolve().parents[1] / "state"
STORE_PATH = STATE_DIR / "py-02-semantic.json"

K = 2  # top-k
THRESHOLD = 0.4  # tuned relevance threshold: true hit ≈ 0.63, distractor ≈ 0.31


# ---------------------------------------------------------------------------
# JSON-file store  (provided — do not edit)
# ---------------------------------------------------------------------------


def new_store() -> dict:
    return {"docs": {}}


def load_store(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return new_store()


def save_store(path: Path, store: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=2))


# ---------------------------------------------------------------------------
# Bag-of-words vectors  (provided — do not edit)
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters/digits)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bag_of_words(text: str) -> Counter[str]:
    """Word -> count."""
    return Counter(tokenize(text))


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Cosine similarity between two sparse count vectors.

        cosine(a, b) = dot(a, b) / (||a|| * ||b||)

    TODO: implement.
      - Dot product: sum a[w]*b[w] over the words the two vectors share
        (a Counter returns 0 for missing keys, so only shared words add).
      - Each norm: math.sqrt of the sum of that vector's squared counts.
      - If either norm is 0, return 0.0; otherwise dot / (norm_a * norm_b).
    """
    # TODO: implement cosine similarity over sparse count vectors
    raise NotImplementedError("TODO: implement cosine()")


def retrieve(store: dict, query: str, k: int, min_score: float) -> list[dict]:
    """Top-k retrieval, then drop anything below the relevance threshold.

    Return a list of {"doc_id", "text", "score"} dicts, best first. The
    threshold runs AFTER the top-k cut: first rank and slice the k best, then
    keep only those with score >= min_score (that's why min_score=0 lets a
    distractor leak through — top-k alone has no notion of "good enough").

    TODO: implement.
      - Vectorize the query with bag_of_words.
      - Score every doc in store["docs"] (a dict doc_id -> {"text": ...})
        with cosine, building {"doc_id", "text", "score"} dicts.
      - Sort by score descending (Python's sort is stable — ties keep
        insertion order), slice the first k.
      - Filter the slice: keep entries with score >= min_score, and return it.
    """
    # TODO: implement thresholded top-k retrieval (score -> sort -> cut -> filter)
    raise NotImplementedError("TODO: implement retrieve()")


def upsert(store: dict, doc_id: str, text: str) -> None:
    """Update-on-write: same doc_id replaces the record, never duplicates.

    TODO: implement.
      - Write {"text": text} into store["docs"] under doc_id — a dict
        assignment is already an upsert (insert new key or overwrite old).
    """
    # TODO: implement update-on-write
    raise NotImplementedError("TODO: implement upsert()")


# ---------------------------------------------------------------------------
# The inject step  (provided — do not edit)
# ---------------------------------------------------------------------------

ANSWER_TEMPLATE = (
    "Answer the question using ONLY the memory below.\n\n"
    "Memory:\n{memory}\n\n"
    "Question: {question}\n"
    "Answer:"
)


def answer_from_memory(chat_fn: ChatFn, question: str, hits: list[dict]) -> str:
    memory = "\n".join(f"- {h['text']}" for h in hits) if hits else "(no relevant memory)"
    prompt = ANSWER_TEMPLATE.format(memory=memory, question=question)
    return chat_fn([{"role": "user", "content": prompt}])


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: echo the memory block it was grounded in."""

    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        memory = prompt.split("Memory:\n", 1)[1].split("\n\nQuestion:", 1)[0]
        return f"[stub] grounded in: {memory}"

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

# A knowledge base with a deliberate near-miss distractor: "kb-search" shares
# infrastructure words with the query (service, uses, the) but answers a
# different question. Pure top-k will happily hand it to the model.
SEED_DOCS = {
    "kb-checkout": "The checkout service uses the Postgres database.",
    "kb-search": "The search service uses Elasticsearch to index products for the storefront.",
    "kb-standup": "The team standup meeting moved to 9am on Mondays.",
    "kb-pasta": "Basil and oregano make a simple pasta sauce.",
}

QUERY = "Which database does the checkout service use?"
UPDATED_FACT = "The checkout service now uses the MySQL database, replacing Postgres."


def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic memory + relevance threshold (Task 2).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 2: semantic memory + threshold — {mode} ===\n")

    STORE_PATH.unlink(missing_ok=True)  # clean state on start
    store = new_store()
    for doc_id, text in SEED_DOCS.items():
        upsert(store, doc_id, text)
    save_store(STORE_PATH, store)
    store = load_store(STORE_PATH)  # retrieval works off the persisted KB

    # ── Noisy retrieval: threshold 0 lets the distractor into top-k ─────────
    print(f"Query: {QUERY!r}\n")
    noisy = retrieve(store, QUERY, k=K, min_score=0.0)
    print(f"top-{K} with min_score=0.0 (noisy):")
    for r in noisy:
        print(f"  {r['score']:.3f}  {r['doc_id']}: {r['text']}")

    # ── The mitigation: a tuned relevance threshold ──────────────────────────
    filtered = retrieve(store, QUERY, k=K, min_score=THRESHOLD)
    print(f"\ntop-{K} with min_score={THRESHOLD} (filtered):")
    for r in filtered:
        print(f"  {r['score']:.3f}  {r['doc_id']}: {r['text']}")

    # ── Update-on-write: the fact changes; same doc_id must replace it ──────
    upsert(store, "kb-checkout", UPDATED_FACT)
    save_store(STORE_PATH, store)
    store = load_store(STORE_PATH)
    fresh = retrieve(store, QUERY, k=K, min_score=THRESHOLD)
    print(f"\nafter upsert of kb-checkout ({len(store['docs'])} docs in store):")
    for r in fresh:
        print(f"  {r['score']:.3f}  {r['doc_id']}: {r['text']}")

    # ── Inject: ground the model in what survived the threshold ─────────────
    answer = answer_from_memory(chat_fn, QUERY, fresh)
    print(f"\nmodel answer: {answer}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    if not args.stub:
        print("\nRun with --stub for the exact acceptance checks.")
        return

    # 1) With threshold 0 the distractor leaks into top-k.
    ok_leak = [r["doc_id"] for r in noisy] == ["kb-checkout", "kb-search"]
    # 2) The tuned threshold filters the distractor; the true hit survives.
    ok_filter = [r["doc_id"] for r in filtered] == ["kb-checkout"]
    # 3) Upsert leaves store size unchanged (no duplicate record)...
    ok_size = len(store["docs"]) == len(SEED_DOCS)
    # 4) ...and retrieval returns the NEW text, not the stale one.
    ok_fresh = (
        len(fresh) == 1
        and fresh[0]["text"] == UPDATED_FACT
        and all(rec["text"] != SEED_DOCS["kb-checkout"] for rec in store["docs"].values())
    )
    # 5) The inject step grounded the model in the fresh memory.
    ok_inject = UPDATED_FACT in answer

    print("\nAcceptance:")
    print(f"  [{'x' if ok_leak else ' '}] min_score=0: distractor kb-search leaks into top-{K}")
    print(
        f"  [{'x' if ok_filter else ' '}] min_score={THRESHOLD}: distractor filtered, true hit survives"
    )
    print(
        f"  [{'x' if ok_size else ' '}] upsert keeps store size at {len(SEED_DOCS)} (no duplicate)"
    )
    print(f"  [{'x' if ok_fresh else ' '}] retrieval returns the NEW text after upsert")
    print(f"  [{'x' if ok_inject else ' '}] the model was grounded in the fresh memory")

    if all([ok_leak, ok_filter, ok_size, ok_fresh, ok_inject]):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
