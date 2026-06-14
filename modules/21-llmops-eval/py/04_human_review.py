"""
Task 4 — Human review + feedback loop  🟡

What this teaches:
  - Not every output can be auto-graded reliably. Low-confidence outputs
    (LLM-judge score below a threshold) go into a review queue for humans
    to label.
  - Human labels close the loop: once labelled, cases are promoted back into
    the versioned eval set so future automated runs benefit from them.
  - The queue is a JSONL file — easy to open in a spreadsheet or a web UI.

How to run:
  # Step A — write low-confidence outputs to the queue:
  uv run python modules/21-llmops-eval/py/04_human_review.py --write-queue

  # Step B — simulate a human labelling (interactive CLI):
  uv run python modules/21-llmops-eval/py/04_human_review.py --label

  # Step C — merge approved labels back into the eval set:
  uv run python modules/21-llmops-eval/py/04_human_review.py --merge

  # Run A+B+C in sequence (demo mode):
  uv run python modules/21-llmops-eval/py/04_human_review.py --demo
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "data"
REVIEW_QUEUE_PATH = DATA_DIR / "review_queue.jsonl"
EVAL_SET_PATH = DATA_DIR / "eval_set_v1.json"

# How confident must the LLM judge be before we skip human review?
CONFIDENCE_THRESHOLD = 0.75   # score (0–1); below this → queue for human


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class QueueItem:
    item_id: str           # unique id for this queue entry
    case_id: str           # the original eval case id
    question: str
    context: str
    system_output: str
    judge_score: float     # 0–1 from LLM-as-judge
    judge_reason: str
    queued_at: str         # ISO timestamp
    human_label: str | None = None     # "correct" | "incorrect" | "partial"
    human_note: str | None = None
    labelled_at: str | None = None
    promoted: bool = False             # True once merged back into eval set


# ---------------------------------------------------------------------------
# Step 1 — LLM runner + judge (thin version)
# ---------------------------------------------------------------------------

def judge_output(question: str, output: str, rubric: str, provider: Any) -> tuple[float, str]:
    """Score `output` with an LLM-as-judge. Return (score_0_1, reason).

    TODO 1a: Build a prompt asking the judge to reply with JSON:
             {"score": <0-10>, "reason": "<string>"}
    TODO 1b: Call provider.chat() with temperature=0.
    TODO 1c: Parse JSON; normalise score to 0–1. Default to 0.0 on parse error.
    Return (normalised_score, reason_string).
    """
    raise NotImplementedError("TODO: implement judge_output")


def run_and_queue(cases: list[dict[str, Any]], provider: Any) -> list[QueueItem]:
    """Run a mini eval and collect low-confidence outputs into the queue.

    TODO 2a: For each case, call provider.chat() with the context-stuffed prompt.
    TODO 2b: Call judge_output().
    TODO 2c: If judge_score < CONFIDENCE_THRESHOLD, create a QueueItem and
             append it.
    TODO 2d: Print progress: case_id, judge_score, queued or skipped.
    Return the list of new QueueItem objects.
    """
    raise NotImplementedError("TODO: implement run_and_queue")


# ---------------------------------------------------------------------------
# Step 2 — Write to the review queue (JSONL)
# ---------------------------------------------------------------------------

def write_queue(items: list[QueueItem]) -> None:
    """Append QueueItems to REVIEW_QUEUE_PATH as JSONL.

    TODO 3a: Create DATA_DIR if needed.
    TODO 3b: Open REVIEW_QUEUE_PATH in append mode.
    TODO 3c: For each item, write json.dumps(asdict(item)) + '\\n'.
    Print how many items were queued.
    """
    raise NotImplementedError("TODO: implement write_queue")


# ---------------------------------------------------------------------------
# Step 3 — Human labelling (interactive CLI)
# ---------------------------------------------------------------------------

def label_queue_interactive() -> None:
    """Present each unlabelled item in the queue and collect a human label.

    TODO 4a: Read REVIEW_QUEUE_PATH line-by-line; parse each JSON line.
    TODO 4b: Skip items where human_label is already set.
    TODO 4c: Display: question, context (truncated), system_output, judge_score, judge_reason.
    TODO 4d: Prompt: "Label [correct/incorrect/partial/skip]: "
    TODO 4e: If not skip, set human_label, human_note, labelled_at; write back.
    TODO 4f: Rewrite the entire JSONL file with updated items.
    Print a summary of how many items were labelled.
    """
    raise NotImplementedError("TODO: implement label_queue_interactive")


# ---------------------------------------------------------------------------
# Step 4 — Merge labelled items back into the eval set
# ---------------------------------------------------------------------------

def merge_labels_into_eval_set() -> None:
    """Promote 'correct' labels from the queue into the versioned eval set.

    This closes the human-in-the-loop feedback cycle: human-validated
    correct outputs become new golden examples in the eval set.

    TODO 5a: Read REVIEW_QUEUE_PATH; collect items with human_label == 'correct'
             and promoted == False.
    TODO 5b: Load EVAL_SET_PATH.
    TODO 5c: For each approved item, add a new case to eval_set['cases'] with:
             id = "hq_<item_id>", question, context,
             reference_answer = system_output (human approved it),
             graders = ["contains", "llm_judge"],
             rubric = "Human-approved output".
    TODO 5d: Bump the patch version (e.g. "1.0.0" → "1.0.1").
    TODO 5e: Write the updated eval set back to EVAL_SET_PATH.
    TODO 5f: Mark promoted=True in the queue; rewrite REVIEW_QUEUE_PATH.
    Print how many new cases were added.
    """
    raise NotImplementedError("TODO: implement merge_labels_into_eval_set")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_eval_cases() -> list[dict[str, Any]]:
    with open(EVAL_SET_PATH) as f:
        return json.load(f)["cases"]


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Human review queue manager")
    parser.add_argument("--write-queue", action="store_true", help="Run eval + write low-confidence items to queue")
    parser.add_argument("--label", action="store_true", help="Interactive labelling session")
    parser.add_argument("--merge", action="store_true", help="Merge approved labels into eval set")
    parser.add_argument("--demo", action="store_true", help="Run all three steps sequentially")
    args = parser.parse_args()

    if args.write_queue or args.demo:
        provider = get_provider()
        cases = load_eval_cases()
        items = run_and_queue(cases, provider)
        write_queue(items)

    if args.label or args.demo:
        label_queue_interactive()

    if args.merge or args.demo:
        merge_labels_into_eval_set()

    if not any([args.write_queue, args.label, args.merge, args.demo]):
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
