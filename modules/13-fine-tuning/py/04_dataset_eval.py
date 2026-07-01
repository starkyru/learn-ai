"""
Task 4 🟡 — Dataset prep and overfitting evaluation.

What you'll learn:
  - What "clean" training data actually means and how to enforce it
  - How to create proper train / val / test splits
  - How to use an LLM-as-judge to score model outputs on held-out data
  - How to detect overfitting: training score rises while val score stalls

Key insight: the most common fine-tuning failure mode is bad data quality.
Inconsistent formatting, duplicate examples, or near-duplicate train/val
examples all make your eval metrics unreliable. This task builds the
data hygiene habits that make fine-tuning actually work.

How to run:
  uv run python modules/13-fine-tuning/py/04_dataset_eval.py
"""

from __future__ import annotations

import html
import random
import re
import textwrap
from typing import TypedDict

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class Example(TypedDict):
    informal: str
    formal: str


class EvalResult(TypedDict):
    train_score: float
    val_score: float


# ---------------------------------------------------------------------------
# Raw dataset (we'll clean and split this)
# ---------------------------------------------------------------------------

RAW_EXAMPLES: list[Example] = [
    {"informal": "hey can u send me the report asap thx", "formal": "Dear colleague, could you please send me the report at your earliest convenience? Thank you."},
    {"informal": "gonna be late to the meeting srry", "formal": "I apologise for the inconvenience, but I will be arriving to the meeting slightly late."},
    {"informal": "wtf is going on with the server its been down for hours", "formal": "I am writing to flag a critical issue: the server has been unavailable for several hours."},
    {"informal": "can we reschedule tmrw? something came up", "formal": "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen."},
    {"informal": "the numbers look good lmk if u need anything else", "formal": "The figures appear satisfactory. Please do not hesitate to reach out should you require further information."},
    {"informal": "yo the budget is way over can we fix this", "formal": "I wish to draw your attention to a budget overrun that requires prompt resolution."},
    {"informal": "just fyi we missed the deadline again", "formal": "I am writing to inform you that we have again not met the agreed deadline."},
    {"informal": "could u review my slides b4 the presentation", "formal": "I would appreciate it if you could review my presentation slides before the scheduled meeting."},
    {"informal": "hi got ur email ill get back to u soon", "formal": "Thank you for your message. I will respond to you in due course."},
    {"informal": "the client wants changes asap its urgent!!", "formal": "The client has requested revisions urgently; I would appreciate your immediate attention to this matter."},
    {"informal": "can u cover for me tmrw i have a family thing", "formal": "I am writing to request coverage for tomorrow, as I have a prior family commitment."},
    {"informal": "pls approve the purchase order before friday", "formal": "I kindly request your approval of the purchase order prior to Friday."},
    {"informal": "the meeting got cancelled btw", "formal": "Please note that the meeting has been cancelled."},
    {"informal": "good job on the launch everyone!!", "formal": "I would like to extend my congratulations to the entire team for the successful launch."},
    {"informal": "hey we need more headcount this quarter", "formal": "I wish to raise the need for additional headcount in the current quarter."},
    {"informal": "can u ping me when the data is ready", "formal": "Please notify me when the data becomes available."},
    {"informal": "fyi the demo is pushed to next week", "formal": "For your information, the demonstration has been rescheduled to next week."},
    {"informal": "thx for the help earlier means a lot", "formal": "Thank you for your assistance earlier; it was greatly appreciated."},
    {"informal": "can we hop on a quick call tmrw morning", "formal": "I would like to propose a brief call tomorrow morning at your convenience."},
    {"informal": "the report has typos pls fix before sending", "formal": "I have noticed typographical errors in the report; please correct them before distribution."},
    {"informal": "heads up: new policy kicks in monday", "formal": "Please be advised that the new policy will take effect on Monday."},
    {"informal": "r u free this afternoon to review the contract", "formal": "I would like to enquire whether you are available this afternoon to review the contract."},
    {"informal": "we r behind schedule need to talk", "formal": "I would like to arrange a discussion, as we are currently behind schedule."},
    {"informal": "awesome work on the deck!!", "formal": "Excellent work on the presentation — it was very well received."},
    {"informal": "pls dont forget the meeting @ 3pm", "formal": "A reminder that the meeting is scheduled for 3:00 PM today."},
    {"informal": "can someone help me with the excel file", "formal": "I would appreciate assistance with the Excel file at someone's earliest convenience."},
    {"informal": "just checking if everyone got the invite", "formal": "I am writing to confirm that all relevant parties have received the calendar invitation."},
    {"informal": "the vendor hasnt responded in 2 weeks smh", "formal": "I wish to note that the vendor has not responded in two weeks; further follow-up may be required."},
    {"informal": "great chatting c u at the conf next month!", "formal": "It was a pleasure speaking with you. I look forward to seeing you at the conference next month."},
    {"informal": "yo where is my invoice?? i need it now", "formal": "I am writing to enquire about the outstanding invoice, which I require promptly."},
]


# ---------------------------------------------------------------------------
# Data cleaning
# ---------------------------------------------------------------------------


def clean_example(example: Example | None, max_chars: int = 512) -> Example | None:
    """
    Normalise and validate a single training example.

    Rules:
      - Return None if the example is None or either field is empty after cleaning.
      - Strip HTML tags (e.g. "<b>hello</b>" → "hello").
      - Unescape HTML entities ("&amp;" → "&").
      - Collapse multiple whitespace characters into single spaces.
      - Strip leading/trailing whitespace.
      - Truncate both fields to max_chars characters.
      - Ensure the formal rewrite ends with a period, question mark, or
        exclamation mark (if not, append ".").

    Returns the cleaned Example or None if invalid.

    TODO: implement the rules above.
    """
    # TODO: implement clean_example
    raise NotImplementedError("TODO: implement clean_example()")


# ---------------------------------------------------------------------------
# Train / val / test split
# ---------------------------------------------------------------------------


def split_dataset(
    examples: list[Example],
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    seed: int = 42,
) -> tuple[list[Example], list[Example], list[Example]]:
    """
    Shuffle and split examples into train / val / test.

    test_frac = 1 - train_frac - val_frac (the remainder).
    The splits must be non-overlapping and their sizes must sum to len(examples).

    TODO:
      1. Shuffle a COPY of examples deterministically — seed with `seed` first,
         then random.shuffle() the copy (don't mutate the caller's list).
      2. Compute the split sizes from the fractions: round(n * train_frac) for
         train and round(n * val_frac) for val; everything left over is test.
      3. Slice the shuffled list into the three non-overlapping parts and return
         (train, val, test).
    """
    # TODO: implement split_dataset
    raise NotImplementedError("TODO: implement split_dataset()")


# ---------------------------------------------------------------------------
# LLM-based evaluation on a split
# ---------------------------------------------------------------------------


def eval_on_split(
    examples: list[Example],
    provider,
    n_samples: int = 5,
) -> float:
    """
    Evaluate a simple few-shot rewriting prompt on a sample from `examples`.

    For each sampled example:
      1. Call the LLM with a zero-shot rewriting prompt (no examples in context).
      2. Ask a judge LLM to score the output vs the reference on a 1–5 scale.
    Return the mean score across sampled examples.

    TODO:
      1. Sample min(n_samples, len(examples)) examples (random, seed=0 for
         reproducibility).
      2. For each sampled example:
         a. Rewrite step — call provider.chat() with a system message telling the
            model to rewrite text as formal business English and a user message
            holding example["informal"].
         b. Judge step — a SECOND provider.chat() call that asks the model to
            rate 1–5 how well the candidate rewrite matches the reference formal
            version (pass both example["formal"] and the step-a output), replying
            with a single digit only.
         c. Parse the first digit out of the judge's reply; fall back to 3.
      3. Return the mean score over the sampled examples.

    Note: this is slow (2 LLM calls per sample). Keep n_samples small.
    """
    # TODO: implement eval_on_split
    raise NotImplementedError("TODO: implement eval_on_split()")


# ---------------------------------------------------------------------------
# Overfitting check
# ---------------------------------------------------------------------------


def overfitting_check(measurements: list[EvalResult]) -> None:
    """
    Print a table of train vs val scores over epochs and flag overfitting.

    Overfitting signal: val score stops improving (or drops) while train score
    continues to rise over 2+ consecutive measurements.

    TODO:
      1. Print a table:
           Epoch | Train | Val  | Status
           1     | 3.2   | 3.1  | ok
           2     | 3.8   | 3.4  | ok
           3     | 4.2   | 3.3  | OVERFIT?
      2. Flag "OVERFIT?" if val_score[i] <= val_score[i-1] and
         train_score[i] > train_score[i-1].
    """
    # TODO: implement overfitting_check
    raise NotImplementedError("TODO: implement overfitting_check()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (model: {provider.chat_model})")

    # Step 1: clean the dataset
    print("\nStep 1: Cleaning dataset...")
    cleaned: list[Example] = []
    for ex in RAW_EXAMPLES:
        result = clean_example(ex)
        if result is not None:
            cleaned.append(result)
    print(f"  {len(RAW_EXAMPLES)} raw → {len(cleaned)} clean examples")

    # Step 2: split
    print("\nStep 2: Splitting dataset (70/15/15)...")
    train, val, test = split_dataset(cleaned)
    print(f"  Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")

    # Step 3: evaluate on train and val (mock a few "epochs")
    print("\nStep 3: Evaluating on train and val splits...")
    print("  (Using 3 samples per split to keep latency low)")
    train_score = eval_on_split(train, provider, n_samples=3)
    val_score = eval_on_split(val, provider, n_samples=3)
    print(f"  Train score: {train_score:.2f} | Val score: {val_score:.2f}")

    # Step 4: simulate overfitting pattern (mocked measurements)
    print("\nStep 4: Overfitting check (mocked multi-epoch measurements):")
    mocked = [
        {"train_score": 3.1, "val_score": 3.0},
        {"train_score": 3.6, "val_score": 3.4},
        {"train_score": 4.1, "val_score": 3.5},
        {"train_score": 4.5, "val_score": 3.4},  # val stops improving
        {"train_score": 4.8, "val_score": 3.3},  # overfitting
    ]
    overfitting_check(mocked)

    print("\nDone. In a real fine-tune, you'd plot these curves and stop early.")


if __name__ == "__main__":
    main()
