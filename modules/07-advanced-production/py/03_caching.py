"""
Task 3 — Caching & cost control  🟡

What this teaches:
  - Identical or near-identical prompts are common. A cache returns the stored
    answer instantly at zero model cost and near-zero latency.
  - Cache keys are deterministic hashes of (model + messages + options). Any
    field change means a cache miss, so prompts must be stable across sessions.
  - A running cost tracker quantifies exactly how much the cache saved.
  - In production: semantic caching (embed the prompt, find the nearest cached
    response above a similarity threshold) handles paraphrased repeats too.

How to run:
  uv run python modules/07-advanced-production/py/03_caching.py
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from llm_core import get_provider, ChatMessage, ChatOptions, ChatResult


# ---------------------------------------------------------------------------
# Cache storage  (JSONL keyed by request hash)
# ---------------------------------------------------------------------------

CACHE_PATH = Path("modules/07-advanced-production/prompt-cache.jsonl")


@dataclass
class CacheEntry:
    key: str
    model: str
    messages: list[dict]
    result_text: str
    input_tokens: int | None
    output_tokens: int | None
    cached_at: str


def load_cache() -> dict[str, CacheEntry]:
    """Load the JSONL cache file and return a dict keyed by entry.key.

    TODO 1: If CACHE_PATH doesn't exist, return {}.
    Otherwise read it line-by-line, parse each JSON entry, reconstruct a
    CacheEntry, and store it in a dict[str, CacheEntry].
    """
    raise NotImplementedError("TODO: implement load_cache")


def save_to_cache(entry: CacheEntry) -> None:
    """Append a cache entry as a JSON line.

    TODO 2: Serialise entry using asdict() and append to CACHE_PATH.
    Create the parent directory if needed.
    """
    raise NotImplementedError("TODO: implement save_to_cache")


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------

def cache_key(
    model: str,
    messages: list[ChatMessage],
    options: ChatOptions | None,
) -> str:
    """Return a deterministic SHA-256 hex hash of the request parameters.

    TODO 3: Serialise (model, messages as list-of-dicts, options as dict or None)
    to a canonical JSON string, then return hashlib.sha256(s.encode()).hexdigest().
    Use sort_keys=True so key order doesn't affect the hash.
    """
    raise NotImplementedError("TODO: implement cache_key")


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------

COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini":      {"input": 0.15,  "output": 0.60},
    "claude-haiku-4-5": {"input": 0.25,  "output": 1.25},
}


@dataclass
class CostTracker:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    saved_cost_usd: float = 0.0


def add_cost(
    tracker: CostTracker,
    model: str,
    result: ChatResult,
    was_cache_hit: bool,
) -> None:
    """Update the cost tracker after a call.

    TODO 4: Increment tracker.calls.
    If was_cache_hit: increment tracker.cache_hits and compute what the call
    would have cost (add to tracker.saved_cost_usd).
    If not was_cache_hit: add input/output tokens to totals, compute actual
    cost and add to tracker.estimated_cost_usd.
    Use COST_PER_1M for price lookups; skip if model not in table.
    """
    raise NotImplementedError("TODO: implement add_cost")


# ---------------------------------------------------------------------------
# Cached chat
# ---------------------------------------------------------------------------

def cached_chat(
    messages: list[ChatMessage],
    options: ChatOptions | None = None,
    tracker: CostTracker | None = None,
) -> tuple[ChatResult, bool]:
    """Return (result, cache_hit).

    TODO 5: Build the cache key. Load the cache.
    If the key exists: reconstruct a ChatResult from the cached entry,
    update tracker (cache hit), return (result, True).
    If not: call provider.chat(), save to cache, update tracker (miss),
    return (result, False).
    """
    raise NotImplementedError("TODO: implement cached_chat")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    provider = get_provider()
    print(f"Provider: {provider.name} / {provider.chat_model}")
    print(f"Cache: {CACHE_PATH.resolve()}\n")

    tracker = CostTracker()

    questions = [
        "What is the capital of France?",
        "What is 12 * 34?",
        "What is the capital of France?",    # should hit cache
        "What is 12 * 34?",                  # should hit cache
        "What year was the Eiffel Tower built?",
    ]

    for q in questions:
        t0 = time.perf_counter()
        result, hit = cached_chat([ChatMessage("user", q)], tracker=tracker)
        ms = (time.perf_counter() - t0) * 1000
        tag = "[HIT] " if hit else "[MISS]"
        print(f"{tag} {ms:6.0f} ms | {q}")
        print(f"        {result.text[:80]}\n")

    # TODO 6: Print tracker summary:
    #   calls, cache_hits, hit_rate %, input_tokens, output_tokens,
    #   estimated_cost_usd, saved_cost_usd
    print("--- Cost summary ---")
    print("TODO: print tracker stats.")


if __name__ == "__main__":
    main()
