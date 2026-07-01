"""
Task 5 — Batch API 🟢

What this teaches:
  - The Batch API lets you submit many requests in one API call and receive results
    asynchronously (typically within 24 hours). In return, providers discount the
    price — often 50 % of the live rate.
  - Batching is ideal for: eval pipelines, bulk summarisation, data extraction from
    large corpora — any workload where latency doesn't matter.
  - This task goes BEYOND llm_core — you must use the provider SDKs directly.

Environment variables:
  ANTHROPIC_API_KEY — required for the Anthropic Batch API path
  OPENAI_API_KEY    — required for the OpenAI Batch API path

How to run:
  uv run python modules/16-context-engineering/py/05_batch_api.py

Note: batch jobs take minutes to hours to process. The script polls and waits.
      Add a --dry-run flag (stretch goal) to print the payload without submitting.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Sample requests to batch — sentiment classification.
# ---------------------------------------------------------------------------
BATCH_INPUTS = [
    {"id": "req-1", "text": "The product exceeded all my expectations. Absolutely love it!"},
    {"id": "req-2", "text": "Terrible experience. The item arrived broken and support was unhelpful."},
    {"id": "req-3", "text": "It is what it is. Does the job but nothing special."},
    {"id": "req-4", "text": "Genuinely impressed by the build quality and fast delivery."},
    {"id": "req-5", "text": "Would not recommend. The instructions were incomprehensible."},
]

CLASSIFY_SYSTEM = (
    "Classify the sentiment of the following text as exactly one of: "
    "positive, negative, or neutral. Reply with only the single word."
)

POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 60  # 10 minutes max wait


# ---------------------------------------------------------------------------
# TODO 1: Implement run_anthropic_batch using the Anthropic Message Batches API.
#         Create an `anthropic.Anthropic` client; read the model from ANTHROPIC_MODEL
#         (a cheap Haiku model is a good default for a classification batch).
#         Conceptual steps:
#         1. Turn BATCH_INPUTS into one batch-request object per item. Each carries a
#            unique `custom_id` (reuse item["id"]) and a `params` dict holding model,
#            a small max_tokens, `system=CLASSIFY_SYSTEM`, and a one-user-message list
#            with the item's text.
#         2. Submit them with `client.beta.messages.batches.create(requests=...)`.
#         3. Poll `client.beta.messages.batches.retrieve(batch_id)` on an interval
#            (use POLL_INTERVAL_SECONDS / MAX_POLL_ATTEMPTS) until its
#            `processing_status` reaches "ended".
#         4. Stream the outputs via `client.beta.messages.batches.results(batch_id)`.
#         5. For each result, print its custom_id and the text of the first content block.
# ---------------------------------------------------------------------------
def run_anthropic_batch() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set — skipping Anthropic batch demo.")
        return

    raise NotImplementedError("TODO: implement run_anthropic_batch")


# ---------------------------------------------------------------------------
# TODO 2: Implement run_openai_batch using the OpenAI Batch API.
#         Create an `openai.OpenAI` client; read the model from OPENAI_CHAT_MODEL.
#         Unlike Anthropic, OpenAI batches are driven through an uploaded JSONL file.
#         Conceptual steps:
#         1. Build a JSONL payload — one line per BATCH_INPUTS item. Each line is a
#            request object with `custom_id`, `method` "POST", `url`
#            "/v1/chat/completions", and a `body` holding model, the messages list
#            (system = CLASSIFY_SYSTEM, user = the item text), and a small max_tokens.
#            Write those lines to a temp .jsonl file.
#         2. Upload it with `client.files.create(file=..., purpose="batch")`.
#         3. Submit with `client.batches.create(input_file_id=..., endpoint=...,
#            completion_window="24h")`.
#         4. Poll `client.batches.retrieve(batch_id)` (POLL_INTERVAL_SECONDS /
#            MAX_POLL_ATTEMPTS) until `status == "completed"`.
#         5. Fetch the results file via `client.files.content(output_file_id)`.
#         6. Parse each returned JSON line and print its custom_id + response content.
# ---------------------------------------------------------------------------
def run_openai_batch() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  OPENAI_API_KEY not set — skipping OpenAI batch demo.")
        return

    raise NotImplementedError("TODO: implement run_openai_batch")


def estimate_savings(
    n_requests: int,
    avg_input_tokens: int = 100,
    avg_output_tokens: int = 10,
    input_price_per_1m: float = 0.15,
    output_price_per_1m: float = 0.60,
    batch_discount: float = 0.50,
) -> None:
    """Print a cost comparison: live vs batch for the given workload."""
    live_cost = (
        (n_requests * avg_input_tokens / 1_000_000) * input_price_per_1m
        + (n_requests * avg_output_tokens / 1_000_000) * output_price_per_1m
    )
    batch_cost = live_cost * (1 - batch_discount)
    print(f"  Workload: {n_requests} requests × ~{avg_input_tokens} in + {avg_output_tokens} out tokens")
    print(f"  Live cost   : ${live_cost:.6f}")
    print(f"  Batch cost  : ${batch_cost:.6f}  ({batch_discount:.0%} discount)")
    print(f"  Saving      : ${live_cost - batch_cost:.6f}")


def main() -> None:
    print("=== Task 5: Batch API ===\n")
    print(f"Requests to batch: {len(BATCH_INPUTS)}")
    for item in BATCH_INPUTS:
        print(f"  [{item['id']}] {item['text'][:60]}...")

    print()
    print("--- Cost comparison (before running) ---")
    estimate_savings(
        n_requests=len(BATCH_INPUTS),
        avg_input_tokens=80,
        avg_output_tokens=5,
        input_price_per_1m=0.15,  # gpt-4o-mini
        output_price_per_1m=0.60,
        batch_discount=0.50,
    )

    print()
    print("--- Anthropic Batch API ---")
    try:
        run_anthropic_batch()
    except NotImplementedError as e:
        print(f"  {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("--- OpenAI Batch API ---")
    try:
        run_openai_batch()
    except NotImplementedError as e:
        print(f"  {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("Observation:")
    print("  Batch API is best when you have hundreds+ of requests and no latency SLA.")
    print("  For < 10 requests, the overhead of polling outweighs the savings.")
    print("  Use live calls when a user is waiting; use batches for offline pipelines.")


if __name__ == "__main__":
    main()
