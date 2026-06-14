"""
Task 2 — Observability  🟢

What this teaches:
  - Every LLM call in production should emit a structured log entry so you can
    answer later: what was sent, what came back, how long it took, what it cost.
  - JSONL (newline-delimited JSON) is a simple, queryable format: easy to stream
    into Langfuse, Datadog, or a data warehouse.
  - A thin wrapper around your provider keeps logging logic out of application code.
  - In production, use Langfuse (https://langfuse.com) or OpenTelemetry for
    distributed tracing, session grouping, and dashboards.

How to run:
  uv run python modules/07-advanced-production/py/02_observability.py
  # Then inspect the log:
  cat modules/07-advanced-production/llm-calls.jsonl
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_core import get_provider, ChatMessage, ChatOptions, ChatResult


# ---------------------------------------------------------------------------
# Cost table  (approx USD per 1M tokens — update as models change)
# ---------------------------------------------------------------------------

COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini":        {"input": 0.15,  "output": 0.60},
    "gpt-4o":             {"input": 2.50,  "output": 10.00},
    "claude-haiku-4-5":   {"input": 0.25,  "output": 1.25},
    "claude-opus-4-8":    {"input": 15.00, "output": 75.00},
    # Ollama / local: 0 cost (omit from table)
}


# ---------------------------------------------------------------------------
# Log entry
# ---------------------------------------------------------------------------

@dataclass
class LLMCallLog:
    id: str
    timestamp: str
    provider: str
    model: str
    messages: list[dict[str, str]]
    options: dict[str, Any] | None
    response_text: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    estimated_cost_usd: float | None
    error: str | None = None


LOG_PATH = Path("modules/07-advanced-production/llm-calls.jsonl")


def append_log(entry: LLMCallLog) -> None:
    """Append a log entry as a JSON line to LOG_PATH.

    TODO 1: Serialise entry to JSON using asdict() or dataclasses.asdict(),
    then write it + "\\n" to LOG_PATH (append mode).
    Create the parent directory if it doesn't exist.
    """
    raise NotImplementedError("TODO: implement append_log")


# ---------------------------------------------------------------------------
# Cost estimator
# ---------------------------------------------------------------------------

def estimate_cost(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Return estimated USD cost for this call, or None if unknown.

    TODO 2: Look up `model` in COST_PER_1M.
    If found and both token counts are not None:
        cost = (input_tokens / 1_000_000) * costs["input"]
             + (output_tokens / 1_000_000) * costs["output"]
    Return None if model is not in the table or tokens are missing.
    """
    raise NotImplementedError("TODO: implement estimate_cost")


# ---------------------------------------------------------------------------
# Observing wrapper
# ---------------------------------------------------------------------------

def observed_chat(
    messages: list[ChatMessage],
    options: ChatOptions | None = None,
) -> ChatResult:
    """Call provider.chat() and log the call to JSONL.

    TODO 3: Wrap provider.chat() in a try/except/finally:
      - Record t0 = time.perf_counter() before the call.
      - On success: populate all LLMCallLog fields from the result.
      - On error: set error=str(e), response_text="", tokens=None.
      - In finally: always call append_log().
      - Re-raise any exception after logging.
    """
    raise NotImplementedError("TODO: implement observed_chat")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    provider = get_provider()
    print(f"Logging calls to: {LOG_PATH.resolve()}\n")

    questions = [
        "What is 12 * 34?",
        "Name the three laws of thermodynamics in one sentence each.",
        "What is the capital of Japan?",
    ]

    for q in questions:
        print(f"Q: {q}")
        try:
            result = observed_chat([ChatMessage("user", q)])
            print(f"A: {result.text[:80]}...\n")
        except Exception as e:
            print(f"Error: {e}\n")

    # TODO 4: Read LOG_PATH line-by-line. For each entry print:
    #   id, model, latency_ms (rounded), input_tokens, output_tokens, estimated_cost_usd
    # Then print total estimated cost for this session.
    print("\n--- Log summary ---")
    print("TODO: parse and summarise the JSONL log.")

    # TODO 5 (stretch): Add a session-level cost accumulator.
    # Note: in production, use Langfuse (langfuse.com) or OpenTelemetry for
    # richer dashboards, alerting, and multi-user session isolation.


if __name__ == "__main__":
    main()
