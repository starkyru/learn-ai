"""
Task 3 🟡 — Throughput vs latency: batching and concurrency.

What you'll learn:
  - The difference between latency (single request) and throughput (many requests)
  - Time-to-first-token (TTFT): the most user-perceived metric in chat apps
  - How concurrent requests improve aggregate throughput
  - Why batching is the fundamental mechanism for high-throughput serving

Key insight: a single request gets the lowest latency by monopolising the GPU/CPU.
But throughput (total tokens/sec across all users) is maximised by batching multiple
requests together — the weight-loading overhead is amortised.

How to run:
  uv run python modules/14-local-inference-optimization/py/03_throughput_latency.py
"""

from __future__ import annotations

import asyncio
import time

from llm_core import ChatMessage, ChatOptions, get_provider

PROMPT = (
    "List 5 practical tips for writing clean, maintainable Python code. "
    "Be concise — one sentence per tip."
)

SHORT_PROMPT = "What is 2 + 2? Answer with just the number."


# ---------------------------------------------------------------------------
# Time-to-first-token (TTFT)
# ---------------------------------------------------------------------------


def measure_ttft(prompt: str, provider) -> float:
    """
    Measure the time from sending a request to receiving the FIRST token.

    This uses streaming (chat_stream) to capture the exact moment the first
    chunk arrives. TTFT is the dominant latency for interactive chat UIs.

    Returns elapsed seconds until the first token.

    TODO:
      1. Snapshot start = time.perf_counter().
      2. Iterate provider.chat_stream() over a single "user" message.
      3. The moment you see the FIRST non-empty chunk, snapshot the clock and
         break — don't drain the rest of the stream.
      4. Return the elapsed seconds from start to that first chunk.

    Note: we break immediately after the first chunk to avoid waiting for
    the full response — that's the whole point of TTFT.
    """
    # TODO: implement measure_ttft
    raise NotImplementedError("TODO: implement measure_ttft()")


# ---------------------------------------------------------------------------
# Single-request latency
# ---------------------------------------------------------------------------


def measure_single_request(prompt: str, provider) -> dict:
    """
    Measure total latency, TTFT, and tokens/sec for one request.

    Returns:
      "ttft_s"      : time to first token in seconds
      "total_s"     : total response time in seconds
      "tokens_out"  : number of output tokens
      "tokens_per_s": tokens_out / total_s

    TODO:
      1. Measure TTFT with measure_ttft().
      2. Measure full request with time.perf_counter() + provider.chat().
      3. Return the dict.
    """
    # TODO: implement measure_single_request
    raise NotImplementedError("TODO: implement measure_single_request()")


# ---------------------------------------------------------------------------
# Concurrent requests
# ---------------------------------------------------------------------------


async def _send_request_async(prompt: str, provider) -> dict:
    """Run one chat request in a thread and return timing info."""
    loop = asyncio.get_running_loop()
    start = time.perf_counter()
    result = await loop.run_in_executor(
        None,
        lambda: provider.chat([ChatMessage("user", prompt)], ChatOptions(max_tokens=100)),
    )
    elapsed = time.perf_counter() - start
    tokens_out = result.usage.output_tokens or 0
    return {
        "tokens_out": tokens_out,
        "elapsed_s": elapsed,
        "tokens_per_s": tokens_out / elapsed if elapsed > 0 else 0,
    }


async def measure_concurrent_async(prompt: str, provider, n: int) -> dict:
    """
    Fire `n` requests concurrently and measure aggregate throughput.

    Returns:
      "n"                  : number of concurrent requests
      "wall_clock_s"       : total wall-clock time (from first send to last receive)
      "total_tokens"       : sum of all output tokens
      "aggregate_tokens_per_s": total_tokens / wall_clock_s

    TODO:
      1. Record start = time.perf_counter().
      2. Use asyncio.gather(*[_send_request_async(prompt, provider) for _ in range(n)]).
      3. Record end time.
      4. Compute wall_clock_s = end - start.
      5. Sum tokens from all results.
      6. Return the dict.
    """
    # TODO: implement measure_concurrent_async
    raise NotImplementedError("TODO: implement measure_concurrent_async()")


def measure_concurrent(prompt: str, provider, n: int) -> dict:
    """Sync wrapper for measure_concurrent_async."""
    return asyncio.run(measure_concurrent_async(prompt, provider, n))


# ---------------------------------------------------------------------------
# Latency table
# ---------------------------------------------------------------------------


def print_latency_table(results: list[dict]) -> None:
    """
    Print a table comparing single-request latency vs concurrent throughput.

    Expected columns: Concurrency | Wall-clock(s) | Tokens | Agg. Tokens/sec

    TODO:
      1. Print a header row.
      2. For each result in results, print a formatted row.
         result keys: "n", "wall_clock_s", "total_tokens", "aggregate_tokens_per_s"
         (results from measure_single_request have different keys — adapt accordingly)
    """
    # TODO: implement print_latency_table
    raise NotImplementedError("TODO: implement print_latency_table()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"Provider: {provider.name} | Model: {provider.chat_model}")

    # Single-request baseline
    print("\n" + "=" * 60)
    print("SINGLE REQUEST BASELINE")
    print("=" * 60)
    try:
        single = measure_single_request(PROMPT, provider)
        print(f"  TTFT           : {single['ttft_s']:.3f}s")
        print(f"  Total latency  : {single['total_s']:.3f}s")
        print(f"  Output tokens  : {single['tokens_out']}")
        print(f"  Tokens/sec     : {single['tokens_per_s']:.1f}")
    except Exception as e:
        print(f"  Skipped: {e}")
        return

    # Concurrent benchmark
    print("\n" + "=" * 60)
    print("CONCURRENT THROUGHPUT (N parallel requests)")
    print("=" * 60)

    table_results = []
    for n in [1, 2, 4, 8]:
        try:
            print(f"  n={n}...", end=" ", flush=True)
            res = measure_concurrent(SHORT_PROMPT, provider, n)
            print(f"wall={res['wall_clock_s']:.2f}s  agg={res['aggregate_tokens_per_s']:.1f} tok/s")
            table_results.append(res)
        except Exception as e:
            print(f"skipped ({e})")

    print()
    print_latency_table(table_results)

    print(
        "\nKey takeaway: concurrent requests increase aggregate throughput because"
        "\nthe model (or Ollama server) can batch work. Wall-clock time grows sub-"
        "\nlinearly with N — especially visible at higher concurrency."
    )


if __name__ == "__main__":
    main()
