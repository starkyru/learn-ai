"""
Task 1 🟢 — Decide: prompt vs fine-tune.

What you'll learn:
  - A structured decision framework for when fine-tuning actually pays off
  - How to approximate fine-tuning via few-shot prompting
  - How to use an LLM as a judge to score output quality automatically
  - Why fine-tuning beats few-shot when you have many examples and consistent format

Key insight: few-shot prompting is the cheapest approximation of fine-tuning. If
few-shot already solves your problem, fine-tuning probably is NOT worth the cost
and complexity. Fine-tuning shines when: (a) you have 100s of consistent examples,
(b) you need the behaviour in every call without paying the few-shot token overhead,
(c) you want output format locked in tightly.

How to run:
  uv run python modules/13-fine-tuning/py/01_decide.py
"""

from __future__ import annotations

import textwrap

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Sample task: rewrite casual emails as formal business emails
# ---------------------------------------------------------------------------

# Informal → formal training pairs (used by mock_finetuned as few-shot examples)
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    (
        "hey can u send me the report asap thx",
        "Dear colleague, could you please send me the report at your earliest convenience? Thank you.",
    ),
    (
        "gonna be late to the meeting srry",
        "I apologise for the inconvenience, but I will be arriving to the meeting slightly late.",
    ),
    (
        "wtf is going on with the server its been down for hours",
        "I am writing to flag a critical issue: the server has been unavailable for several hours and requires immediate attention.",
    ),
    (
        "can we reschedule tmrw? something came up",
        "I would like to request rescheduling tomorrow's appointment, as an unforeseen commitment has arisen.",
    ),
    (
        "the numbers look good lmk if u need anything else",
        "The figures appear satisfactory. Please do not hesitate to reach out should you require any further information.",
    ),
]

# Test inputs — these are NOT in the few-shot examples
TEST_INPUTS = [
    "yo where is my invoice?? i need it now",
    "fyi the client is kinda unhappy with our progress",
    "can u double check the contract before we sign",
    "just wanted to say great work on the presentation!!",
    "heads up the deadline got moved to friday",
]


# ---------------------------------------------------------------------------
# Approach 1: system-prompt baseline
# ---------------------------------------------------------------------------


def prompt_baseline(text: str, provider) -> str:
    """
    Rewrite `text` as a formal business email using a system prompt.

    The system prompt describes the task; no examples are shown.
    This is the simplest approach — pure prompting, no data needed.

    TODO:
      1. Build a ChatMessage("system", ...) that tells the model to rewrite
         casual text as formal business English, preserving the meaning.
      2. Build a ChatMessage("user", text) with the input.
      3. Call provider.chat() with temperature=0.2 (a little creativity is fine).
      4. Return result.text.strip().
    """
    # TODO: implement prompt_baseline
    raise NotImplementedError("TODO: implement prompt_baseline()")


# ---------------------------------------------------------------------------
# Approach 2: mock fine-tuned (few-shot approximation)
# ---------------------------------------------------------------------------


def mock_finetuned(text: str, provider) -> str:
    """
    Rewrite `text` as a formal email using 5 (input, output) few-shot examples.

    This simulates what a fine-tuned model has learned: by embedding the training
    distribution in the prompt itself, we anchor the output format and style.

    TODO:
      1. Build a system message explaining the task.
      2. For each (informal, formal) pair in FEW_SHOT_EXAMPLES, add two messages:
           ChatMessage("user", informal)
           ChatMessage("assistant", formal)
         This creates a multi-turn example conversation.
      3. Add a final ChatMessage("user", text) — the query.
      4. Call provider.chat() with temperature=0.
      5. Return result.text.strip().

    Key difference from prompt_baseline: the model sees CONCRETE EXAMPLES of
    the exact transformation you want, not just an instruction.
    """
    # TODO: implement mock_finetuned
    raise NotImplementedError("TODO: implement mock_finetuned()")


# ---------------------------------------------------------------------------
# Evaluation: LLM-as-judge formality scorer
# ---------------------------------------------------------------------------


def score_formality(text: str, provider) -> int:
    """
    Ask the LLM to rate the formality of `text` on a 1–5 scale.

    1 = very informal / casual
    5 = highly formal business English

    TODO:
      1. Build a prompt asking the model to rate the formality of the text.
         Tell it to respond with ONLY a single digit (1–5), nothing else.
      2. Call provider.chat() with temperature=0.
      3. Parse the result: find the first digit character in the response.
         Return it as int. If parsing fails, return 3 (neutral fallback).

    Note: this is "LLM-as-judge" — using one LLM call to evaluate another.
    It's imperfect but surprisingly useful for rough quality comparisons.
    """
    # TODO: implement score_formality
    raise NotImplementedError("TODO: implement score_formality()")


# ---------------------------------------------------------------------------
# Decision guide (reference, not TODO)
# ---------------------------------------------------------------------------


DECISION_GUIDE = """
WHEN TO FINE-TUNE (vs just prompting / adding examples)
=========================================================

Fine-tune when ALL of the following are true:
  1. You have 100+ high-quality, consistent (prompt, completion) pairs.
  2. The task definition is stable — it won't change monthly.
  3. You need the behaviour in EVERY call without the few-shot token overhead
     (large few-shot blocks cost tokens at inference time).
  4. Output format must be extremely consistent (JSON schema, specific lengths).

Stick with prompting / few-shot when:
  - You have < 50 examples (fine-tune will overfit).
  - The task / labels change often.
  - You're still exploring — fine-tuning locks you in.
  - Few-shot already meets your quality bar (it often does!).

Use RAG instead when:
  - The model needs external or up-to-date facts, not a new SKILL.
  - Your "training data" is actually a document corpus.
"""


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (model: {provider.chat_model})")

    print(DECISION_GUIDE)

    header = f"{'INPUT':<40} {'BASELINE':>9} {'FEW-SHOT':>9}"
    print("=" * 70)
    print("COMPARISON TABLE — formality scores (1=casual, 5=formal)")
    print("=" * 70)
    print(header)
    print("-" * 70)

    for raw in TEST_INPUTS:
        baseline_out = prompt_baseline(raw, provider)
        fewshot_out = mock_finetuned(raw, provider)
        baseline_score = score_formality(baseline_out, provider)
        fewshot_score = score_formality(fewshot_out, provider)
        short = textwrap.shorten(raw, 38)
        print(f"{short:<40} {baseline_score:>9} {fewshot_score:>9}")

    print("-" * 70)
    print(
        "\nReflection: did few-shot beat the plain system prompt? If scores are similar,"
        "\nfew-shot is probably not worth adding (save the tokens). If few-shot wins"
        "\nclearly, that suggests a real fine-tune on 200+ examples would lock it in."
    )


if __name__ == "__main__":
    main()
