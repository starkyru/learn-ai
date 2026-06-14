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
# TODO 1: Implement run_anthropic_batch.
#         Use the Anthropic Message Batches API.
#
#         Steps:
#         1. Build a list of `MessageBatchRequest` objects, one per BATCH_INPUTS item.
#            Each request needs a unique `custom_id` and a `params` dict with
#            model, max_tokens, system, and messages.
#         2. Submit with `client.beta.messages.batches.create(requests=[...])`.
#         3. Poll `client.beta.messages.batches.retrieve(batch_id)` until
#            `processing_status == "ended"`.
#         4. Iterate results with `client.beta.messages.batches.results(batch_id)`.
#         5. Print each result's custom_id and the first text block content.
#
#         Example skeleton:
#           import anthropic
#           client = anthropic.Anthropic(api_key=...)
#           requests = [
#               anthropic.types.beta.messages.MessageBatchRequestParam(
#                   custom_id=item["id"],
#                   params={
#                       "model": model,
#                       "max_tokens": 10,
#                       "system": CLASSIFY_SYSTEM,
#                       "messages": [{"role": "user", "content": item["text"]}],
#                   }
#               )
#               for item in BATCH_INPUTS
#           ]
#           batch = client.beta.messages.batches.create(requests=requests)
# ---------------------------------------------------------------------------
def run_anthropic_batch() -> None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set — skipping Anthropic batch demo.")
        return

    # TODO: implement
    # import anthropic
    # client = anthropic.Anthropic(api_key=api_key)
    # model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")  # use haiku for low cost
    # ...
    raise NotImplementedError("TODO: implement run_anthropic_batch")


# ---------------------------------------------------------------------------
# TODO 2: Implement run_openai_batch.
#         Use the OpenAI Batch API.
#
#         Steps:
#         1. Write a JSONL file where each line is a request dict:
#            {"custom_id": id, "method": "POST", "url": "/v1/chat/completions",
#             "body": {"model": ..., "messages": [...], "max_tokens": 10}}
#         2. Upload the file with `client.files.create(file=..., purpose="batch")`.
#         3. Submit with `client.batches.create(input_file_id=..., endpoint=..., completion_window="24h")`.
#         4. Poll `client.batches.retrieve(batch_id)` until `status == "completed"`.
#         5. Download the output file with `client.files.content(output_file_id)`.
#         6. Parse each JSON line and print custom_id + response content.
#
#         Example skeleton:
#           import openai, tempfile
#           client = openai.OpenAI(api_key=...)
#           lines = [json.dumps({...}) for item in BATCH_INPUTS]
#           with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
#               f.write("\n".join(lines))
#               tmp_path = f.name
#           file_obj = client.files.create(file=open(tmp_path, "rb"), purpose="batch")
#           batch = client.batches.create(input_file_id=file_obj.id, endpoint="/v1/chat/completions", completion_window="24h")
# ---------------------------------------------------------------------------
def run_openai_batch() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("  OPENAI_API_KEY not set — skipping OpenAI batch demo.")
        return

    # TODO: implement
    # import openai, tempfile
    # client = openai.OpenAI(api_key=api_key)
    # model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    # ...
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
