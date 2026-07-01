"""
Task 5 — Prompt eval harness 🟡

What this teaches:
  - Prompt engineering without measurement is guessing. A tiny eval harness
    turns "I think prompt A is better" into "prompt A scores 80%, prompt B
    scores 60% on this dataset."
  - The dataset is eval_dataset.json (10 labelled sentiment examples) located
    one directory up from this file.
  - You define two or more prompt variants, run each on the full dataset,
    and print a comparison table. Pick the winner with numbers.
  - This is the same principle behind large-scale LLM evals — just smaller.

Dataset: modules/03-prompting/eval_dataset.json

How to run:
  uv run python modules/03-prompting/py/05_eval_harness.py
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Callable

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# Load dataset
# ---------------------------------------------------------------------------
DATASET_PATH = pathlib.Path(__file__).parent.parent / "eval_dataset.json"

with open(DATASET_PATH) as f:
    DATASET: list[dict] = json.load(f)


# ---------------------------------------------------------------------------
# TODO 1: Define at least TWO prompt variants for sentiment classification.
#         Vary the instruction style, persona, output format instruction,
#         or example count. Form a hypothesis about which will score higher
#         BEFORE running.
#         Examples of things to vary:
#           - "Respond with one word" vs "Answer: <label>" format
#           - No examples vs 1 example
#           - Terse system prompt vs detailed system prompt
# ---------------------------------------------------------------------------
@dataclass
class PromptVariant:
    name: str
    build_messages: Callable[[str], list[ChatMessage]]


def variant_a_messages(text: str) -> list[ChatMessage]:
    """Minimal zero-shot."""
    return [
        ChatMessage(role="system", content="Classify sentiment as positive, negative, or neutral. One word only."),
        ChatMessage(role="user", content=text),
    ]


def variant_b_messages(text: str) -> list[ChatMessage]:
    """TODO: define your second variant here.
    Try a different instruction style. Ideas:
      - Add a persona: "You are a customer review analyst..."
      - Change the output format instruction
      - Add a one-shot example
    """
    return [
        # TODO: implement
        ChatMessage(role="user", content=f"TODO — implement variant B. Input: {text}"),
    ]


VARIANTS: list[PromptVariant] = [
    PromptVariant(name="variant-A: minimal", build_messages=variant_a_messages),
    PromptVariant(name="variant-B: TODO — define your second variant", build_messages=variant_b_messages),
    # TODO (stretch): add variant_c with a few-shot example
]


# ---------------------------------------------------------------------------
# TODO 2: Implement parse_output.
#         Same as task 4: normalise the model output to a label string.
#         Normalise: strip, lowercase, remove non-alpha chars.
#         Return the cleaned string (don't raise — just return whatever comes
#         back so you can see where the model deviates in the eval table).
# ---------------------------------------------------------------------------
def parse_output(raw: str) -> str:
    import re
    # TODO: implement
    return re.sub(r"[^a-z]", "", raw.strip().lower())


# ---------------------------------------------------------------------------
# TODO 3: Implement eval_variant.
#         Run the given variant on every DataPoint in DATASET.
#         For each point: call the LLM, parse output, compare to expected label.
#         Return a list of per-sample results plus overall accuracy.
# ---------------------------------------------------------------------------
@dataclass
class SampleResult:
    id: str
    input: str
    expected: str
    predicted: str
    correct: bool


@dataclass
class EvalResult:
    variant_name: str
    samples: list[SampleResult] = field(default_factory=list)
    accuracy: float = 0.0


def eval_variant(variant: PromptVariant) -> EvalResult:
    llm = get_provider()
    result = EvalResult(variant_name=variant.name)

    for point in DATASET:
        # TODO: run this variant on `point` and record a real SampleResult.
        #   - Build the messages with variant.build_messages(point["input"]) and
        #     send them through llm.chat(...).
        #   - Run the reply text through parse_output(...) to get the predicted
        #     label, and mark it correct when it matches point["label"]
        #     case-insensitively.
        #   - Append a SampleResult with those id/input/expected/predicted/correct
        #     fields (replace the placeholder below).

        # Placeholder until implemented:
        result.samples.append(SampleResult(
            id=point["id"], input=point["input"],
            expected=point["label"], predicted="TODO", correct=False,
        ))

    result.accuracy = sum(1 for s in result.samples if s.correct) / len(result.samples)
    return result


# ---------------------------------------------------------------------------
# TODO 4: Print results in a readable table.
# ---------------------------------------------------------------------------
def print_results(results: list[EvalResult]) -> None:
    for r in results:
        correct_count = sum(1 for s in r.samples if s.correct)
        print(f"\n=== {r.variant_name} ===")
        print(f"Accuracy: {r.accuracy:.0%} ({correct_count}/{len(r.samples)})\n")
        print(f"{'ID':<12} {'Expected':<12} {'Predicted':<12} {'OK?':<5} Input")
        print("-" * 80)
        for s in r.samples:
            ok = "✓" if s.correct else "✗"
            truncated = s.input[:35] + "..." if len(s.input) > 35 else s.input
            print(f"{s.id:<12} {s.expected:<12} {s.predicted:<12} {ok:<5} {truncated}")

    # Summary
    print("\n=== Summary ===")
    print(f"{'Variant':<35} {'Accuracy'}")
    print("-" * 45)
    for r in sorted(results, key=lambda x: x.accuracy, reverse=True):
        print(f"{r.variant_name:<35} {r.accuracy:.0%}")


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}")
    print(f"Dataset: {len(DATASET)} examples")
    print(f"Variants: {len(VARIANTS)}\n")

    # -------------------------------------------------------------------------
    # TODO 5: Run eval_variant for each entry in VARIANTS, collect the
    #         EvalResult list, and hand it to print_results(...).
    # -------------------------------------------------------------------------

    # Placeholder until implemented:
    results = [eval_variant(v) for v in VARIANTS]
    print_results(results)
    print("\n(TODO: implement the LLM calls inside eval_variant to get real results)")


if __name__ == "__main__":
    main()
