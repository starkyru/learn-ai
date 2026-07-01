"""
Task 6 🟢 — Routing, fallbacks & load testing.

Running multiple LLM providers in production requires three pieces:

  1. ROUTING — send easy queries to a cheap/fast model and hard queries to a
     stronger one. Correctly routing a query saves cost and latency without
     sacrificing quality on queries that actually need the bigger model.

  2. FALLBACKS — when a provider fails (timeout, rate limit, server error),
     automatically retry with the next provider in the list. This turns
     a single provider's reliability into a multi-provider SLA.

  3. LOAD TESTING — measure what happens under concurrent load: how many
     requests per second can you sustain, what is the p50/p95 latency
     distribution, and what is the error rate?

What you'll learn:
  - Heuristic and embedding-based difficulty classification
  - Provider fallback chains with timeout handling
  - Concurrent request execution with asyncio
  - Latency percentile (p50, p95) calculation
  - Reading throughput and error-rate metrics from a load test

How to run:
  uv run python modules/14-local-inference-optimization/py/06_routing_fallbacks.py
"""

from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class RoutingDecision:
    query: str
    difficulty: str          # "easy" | "hard"
    chosen_model: str        # e.g. "llama3.2:1b" or "llama3.2"
    reason: str


@dataclass
class LoadTestResult:
    total_requests: int
    success_count: int
    error_count: int
    elapsed_s: float
    latencies_ms: list[float]   # one per successful request

    @property
    def throughput_rps(self) -> float:
        return self.total_requests / max(self.elapsed_s, 1e-9)

    @property
    def error_rate(self) -> float:
        return self.error_count / max(self.total_requests, 1)

    @property
    def p50_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.median(self.latencies_ms)

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]


# ---------------------------------------------------------------------------
# Step 1 — Difficulty classification
# ---------------------------------------------------------------------------

# Heuristic features that suggest a query is "hard":
# - Asks for code, math, or reasoning (keywords)
# - Long query (> 20 words) — tends to need more context
# - Multiple questions in one (contains "and", "?...?")
HARD_KEYWORDS = [
    "explain", "compare", "analyse", "analyze", "design", "implement",
    "proof", "derive", "calculate", "optimise", "optimize", "refactor",
    "debug", "architecture", "tradeoff", "trade-off", "algorithm",
    "why does", "how does", "what would happen",
]

EASY_KEYWORDS = [
    "what is", "define", "list", "name", "who is", "when was",
    "translate", "summarise", "summarize", "capital of",
]


def classify_difficulty(query: str) -> str:
    """
    Classify a query as "easy" or "hard" using heuristics.

    TODO: implement this function.

    Heuristic rules (apply in order; FIRST match wins, so order matters):
      1. Lowercase the query. If it contains any HARD_KEYWORDS entry → "hard".
      2. If the query is long (word count past a "this needs context" threshold,
         ~20) → "hard".
      3. If it packs more than one question mark (a compound question) → "hard".
      4. If it contains any EASY_KEYWORDS entry → "easy".
      5. Otherwise default to "easy".

    Returns "easy" or "hard".
    """
    # TODO: implement classify_difficulty
    raise NotImplementedError("TODO: implement classify_difficulty()")


# ---------------------------------------------------------------------------
# Step 2 — Router
# ---------------------------------------------------------------------------

# Model configuration: map difficulty → model name.
# By default we use Ollama. Adjust these to the models you have pulled.
EASY_MODEL = "llama3.2:1b"    # fast, cheap — good for simple lookups
HARD_MODEL = "llama3.2"       # slower, stronger — used for complex queries


def route(query: str) -> RoutingDecision:
    """
    Decide which model to use for `query`.

    TODO: implement this function.

    Steps:
      1. Classify the query with classify_difficulty().
      2. Map "hard" → HARD_MODEL and everything else → EASY_MODEL.
      3. Compose a short human-readable reason explaining the choice (mention the
         difficulty and why the bigger/faster model fits).
      4. Return a RoutingDecision(query, difficulty, chosen_model, reason).
    """
    # TODO: implement route
    raise NotImplementedError("TODO: implement route()")


# ---------------------------------------------------------------------------
# Step 3 — Provider fallback
# ---------------------------------------------------------------------------


async def with_fallback(
    providers: list[Any],
    call: Callable[[Any], Any],
    timeout_s: float = 10.0,
) -> tuple[Any, str]:
    """
    Try each provider in order. Return the first successful result.

    TODO: implement this function.

    Algorithm:
      Loop over providers in order. For each one:
        1. Run call(provider) off the event loop with asyncio.to_thread (the
           provider call is synchronous), and bound it with asyncio.wait_for
           using timeout_s so a slow provider can't hang the chain.
        2. On success, return (result, provider.name) immediately.
        3. On asyncio.TimeoutError OR any other exception: warn and fall through
           to the next provider.
      If every provider is exhausted, raise a RuntimeError.

    Tip: asyncio.to_thread wraps the synchronous provider.chat(); asyncio.wait_for
    enforces the per-provider timeout.
    """
    # TODO: implement with_fallback
    raise NotImplementedError("TODO: implement with_fallback()")


# ---------------------------------------------------------------------------
# Step 4 — Load test
# ---------------------------------------------------------------------------


async def load_test(
    fn: Callable[[], Any],
    concurrency: int,
    n: int,
) -> LoadTestResult:
    """
    Fire `n` total requests with `concurrency` concurrent workers.

    TODO: implement this function.

    Algorithm:
      1. Use a semaphore to cap concurrency: sem = asyncio.Semaphore(concurrency).
      2. For each of `n` calls, define an async task that:
           a. Acquires the semaphore.
           b. Records start_time.
           c. Calls: result = await asyncio.to_thread(fn)
           d. Records latency in ms.
           e. Releases the semaphore.
           f. Returns (True, latency_ms) on success, (False, 0) on exception.
      3. Use asyncio.gather(*tasks) to run all tasks concurrently.
      4. Collect successes, errors, and latencies.
      5. Return LoadTestResult.

    Note: fn is a zero-argument callable that makes one request (synchronous).
    wrap it with asyncio.to_thread inside the task.
    """
    # TODO: implement load_test
    raise NotImplementedError("TODO: implement load_test()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

SAMPLE_QUERIES = [
    "What is the capital of France?",
    "Define machine learning in one sentence.",
    "Who invented the telephone?",
    "Explain the tradeoffs between RAG and fine-tuning for a production chatbot.",
    "Design an architecture for a high-throughput LLM serving system that handles 10,000 RPS.",
    "Why does the KV cache reduce memory bandwidth in transformer inference?",
    "List three programming languages.",
    "Summarise what a neural network does.",
    "Compare and analyse the differences between quantization and distillation as model compression techniques.",
    "What year was Python first released?",
]


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Chat model: {provider.chat_model}\n")

    # -------------------------------------------------------------------------
    # Part A: Routing demo
    # -------------------------------------------------------------------------
    print("=" * 60)
    print("PART A — ROUTING")
    print("=" * 60)
    print(f"\n{'Query':<55} {'Difficulty':<8} {'Model'}")
    print("-" * 80)
    for q in SAMPLE_QUERIES:
        decision = route(q)
        print(f"  {q[:53]:<53}  {decision.difficulty:<8}  {decision.chosen_model}")

    easy_count = sum(1 for q in SAMPLE_QUERIES if route(q).difficulty == "easy")
    hard_count = len(SAMPLE_QUERIES) - easy_count
    print(f"\n  Easy: {easy_count} → {EASY_MODEL}  |  Hard: {hard_count} → {HARD_MODEL}")

    # -------------------------------------------------------------------------
    # Part B: Fallback demo
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PART B — FALLBACK")
    print("=" * 60)

    # Build a fallback chain: primary provider first, then the same provider
    # with a very short timeout (simulating a failing endpoint) to demonstrate
    # fallback logic. In production you'd use two different providers.
    primary = get_provider()
    # Simulate a second provider (same endpoint — timeout triggers fallback demo)
    fallback_provider = get_provider()

    prompt = "Say 'fallback works' and nothing else."

    def make_call(p: Any) -> str:
        result = p.chat([ChatMessage("user", prompt)], options=ChatOptions(max_tokens=10))
        return result.text

    print("\nAttempting request with fallback chain [primary → fallback]...")
    try:
        result, used_provider = asyncio.run(
            with_fallback([primary, fallback_provider], make_call, timeout_s=30.0)
        )
        print(f"  Success via '{used_provider}': {result.strip()!r}")
    except RuntimeError as e:
        print(f"  All providers failed: {e}")

    # -------------------------------------------------------------------------
    # Part C: Load test
    # -------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("PART C — LOAD TEST")
    print("=" * 60)

    test_prompt = "Reply with exactly one word: OK."

    def single_request() -> str:
        return provider.chat(
            [ChatMessage("user", test_prompt)],
            options=ChatOptions(max_tokens=5),
        ).text

    for concurrency, n in [(1, 5), (3, 9)]:
        print(f"\n  concurrency={concurrency}, n={n} requests...")
        result_lt = asyncio.run(load_test(single_request, concurrency=concurrency, n=n))
        print(f"  Throughput  : {result_lt.throughput_rps:.2f} req/s")
        print(f"  p50 latency : {result_lt.p50_ms:.0f} ms")
        print(f"  p95 latency : {result_lt.p95_ms:.0f} ms")
        print(f"  Error rate  : {result_lt.error_rate:.1%}  "
              f"({result_lt.error_count}/{result_lt.total_requests} failed)")

    print(
        "\nKey insights:"
        "\n  1. Routing lets you serve cheap queries cheaply without sacrificing quality."
        "\n  2. Fallbacks turn single-provider reliability into multi-provider SLAs."
        "\n  3. Load tests reveal p95 latency spikes that p50 hides."
        "\n  4. Concurrency > 1 improves throughput but may increase p95 latency."
        "\n  5. Error rate under load tells you where your provider's limits are."
    )


if __name__ == "__main__":
    main()
