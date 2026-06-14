"""
Task 6 — Retries & errors 🟡

What this teaches:
  - LLM APIs are remote HTTP calls; they fail with rate limits (429),
    server errors (500), and timeouts. Resilient code handles these.
  - Exponential backoff with jitter is the standard retry pattern:
    wait 2^attempt * base_ms + random jitter, doubling each retry.
  - The openai and anthropic Python SDKs already retry automatically
    (by default 2 retries). This exercise teaches you the pattern
    explicitly so you can tune it, wrap non-SDK calls, or build
    higher-level retry policies.
  - Typed error handling: distinguish retriable errors (429, 503) from
    permanent ones (401 invalid key, 400 bad request) — don't retry those.

How to run:
  uv run python modules/02-llm-integration/py/06_retries.py
"""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from llm_core import get_provider, ChatMessage, ChatResult

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Custom error type for wrapping provider errors with extra context.
# ---------------------------------------------------------------------------


class LLMError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retriable: bool = True) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retriable = retriable


# ---------------------------------------------------------------------------
# TODO 1: Implement is_retriable(error: Exception) -> bool
#         Return True for:
#           - HTTP 429 (rate limit) — always retry
#           - HTTP 500, 502, 503, 504 (server errors) — usually transient
#         Return False for:
#           - HTTP 401 (bad API key) — retrying won't help
#           - HTTP 400 (bad request) — your bug, not theirs
#         Hint: openai raises openai.RateLimitError, openai.APIStatusError etc.
#               anthropic raises anthropic.RateLimitError, anthropic.APIStatusError etc.
#               Both attach .status_code to their errors.
#               Check hasattr(error, "status_code") first.
# ---------------------------------------------------------------------------
def is_retriable(error: Exception) -> bool:
    if isinstance(error, LLMError):
        return error.retriable
    # TODO: implement for real SDK errors
    status = getattr(error, "status_code", None)
    if status is None:
        return True  # network error — probably retriable
    return status in (429, 500, 502, 503, 504)


# ---------------------------------------------------------------------------
# TODO 2: Implement with_retry.
#         Parameters:
#           fn         — callable returning T, may raise
#           max_retries — max attempts after the first (default 3)
#           base_ms    — base delay in ms (default 500)
#         Algorithm:
#           1. Try fn().
#           2. On exception: if not is_retriable(err) or attempt >= max_retries → raise.
#           3. Else: compute delay = base_ms * 2**attempt + random(0, base_ms)  (ms).
#           4. Log attempt, delay, and error.
#           5. Sleep and retry.
# ---------------------------------------------------------------------------
def with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    base_ms: float = 500.0,
) -> T:
    # TODO: implement
    # for attempt in range(max_retries + 1):
    #     try:
    #         return fn()
    #     except Exception as err:
    #         if attempt == max_retries or not is_retriable(err):
    #             raise
    #         delay_ms = base_ms * (2 ** attempt) + random.random() * base_ms
    #         print(f"Attempt {attempt + 1} failed ({err}). Retrying in {delay_ms:.0f}ms...")
    #         time.sleep(delay_ms / 1000)
    # raise RuntimeError("unreachable")
    raise NotImplementedError("with_retry not implemented yet — uncomment the block above")


# ---------------------------------------------------------------------------
# TODO 3: Implement chat_with_retry — thin wrapper around with_retry + llm.chat().
# ---------------------------------------------------------------------------
def chat_with_retry(
    messages: list[ChatMessage],
    max_retries: int = 3,
) -> ChatResult:
    llm = get_provider()
    # TODO: return with_retry(lambda: llm.chat(messages), max_retries)
    return llm.chat(messages)  # placeholder — replace with line above


# ---------------------------------------------------------------------------
# Simulation helpers — let you test the retry logic without a real API error.
# ---------------------------------------------------------------------------

_call_count = 0


def make_flaky(fail_times: int, status_code: int) -> Callable[[], str]:
    """Return a function that fails the first `fail_times` calls with
    the given status_code, then returns "success". Test your retry logic here."""
    def inner() -> str:
        global _call_count
        _call_count += 1
        if _call_count <= fail_times:
            err = LLMError(f"Simulated {status_code}", status_code=status_code)
            raise err
        return "success after retries"
    return inner


def main() -> None:
    print("=== Retry & error handling demo ===\n")

    global _call_count

    # -------------------------------------------------------------------------
    # Test 1: flaky function that fails twice then succeeds (429 → retriable)
    # -------------------------------------------------------------------------
    print("Test 1: 2 rate-limit errors then success")
    _call_count = 0
    try:
        result = with_retry(make_flaky(2, 429))
        print(f"Result: {result}\n")
    except Exception as err:
        print(f"Failed: {err}\n")

    # -------------------------------------------------------------------------
    # Test 2: permanent error (401) — should NOT retry
    # -------------------------------------------------------------------------
    print("Test 2: permanent auth error (401) — should fail immediately")
    _call_count = 0
    try:
        with_retry(make_flaky(5, 401))
    except LLMError as err:
        print(f"Correctly failed without retrying: {err}\n")
    except NotImplementedError as err:
        print(f"(not implemented yet: {err})\n")

    # -------------------------------------------------------------------------
    # Test 3: real API call with retry wrapper
    # -------------------------------------------------------------------------
    print("Test 3: real API call (should succeed on first attempt)")
    try:
        result = chat_with_retry([
            ChatMessage(role="user", content="Say 'retry test passed' and nothing else."),
        ])
        print(f"Response: {result.text}")
        print(f"Model: {result.model}\n")
    except Exception as err:
        print(f"Real call failed: {err}")

    # -------------------------------------------------------------------------
    # TODO 4 (stretch): Implement a circuit breaker that opens after N
    #         consecutive failures and refuses calls for a cooldown period.
    #         This prevents hammering an API that's completely down.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
