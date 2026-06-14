"""
Task 1 🟢 — LLM zero-shot and few-shot classification.

What you'll learn:
  - How to turn an LLM into a classifier with a single prompt
  - How zero-shot (no examples) differs from few-shot (a handful of examples)
  - Robust label parsing: what to do when the model says "Technology" vs "technology"
  - The cost/latency trade-off vs. a trained classifier

Key insight: LLMs are already trained on human text, so they "understand" labels
like "technology" or "sports" without any task-specific training data. Few-shot
examples narrow their interpretation and reduce format errors.

How to run:
  uv run python modules/08-classification/py/01_llm_classifier.py

Dataset:
  modules/08-classification/data/texts.json
  50 news snippets across 6 categories: technology, science, business, sports, health, politics
"""

from __future__ import annotations

import json
import pathlib

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Labels and dataset
# ---------------------------------------------------------------------------

LABELS = ["technology", "science", "business", "sports", "health", "politics"]

DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "texts.json"


def load_dataset() -> list[dict]:
    with open(DATA_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Label parsing — robust against model formatting variations
# ---------------------------------------------------------------------------


def parse_label(raw: str, valid_labels: list[str]) -> str | None:
    """
    Extract a clean label from the model's raw response.

    The model might return:
      - "technology"           → exact match
      - "Technology"           → case difference
      - "Label: technology"    → wrapped in a key
      - "The answer is sports" → embedded in prose
      - "tech"                 → partial match (handle carefully)

    TODO: implement this function.

    Steps:
      1. Lowercase and strip the raw string.
      2. Check if any valid label appears as a substring.
         Return the FIRST match found.
      3. If nothing matches, return None.

    Hint: a single loop over valid_labels with `label in text` is enough.
    """
    # TODO: implement robust label extraction
    raise NotImplementedError("TODO: implement parse_label()")


# ---------------------------------------------------------------------------
# Zero-shot classifier
# ---------------------------------------------------------------------------


def zero_shot_prompt(text: str, labels: list[str]) -> str:
    """
    Build a zero-shot classification prompt.

    Zero-shot means: no examples — just a task description and the label set.

    TODO: craft a prompt that:
      1. Tells the model it is a text classifier.
      2. Lists the valid labels exactly.
      3. Instructs it to reply with ONLY the label (no explanation).
      4. Presents the text to classify.

    Tip: use a system message for the task description and a user message
    for the text, OR put everything in a single user message — either works,
    but a system message leads to more consistent output.
    """
    # TODO: return the formatted prompt string
    raise NotImplementedError("TODO: implement zero_shot_prompt()")


def classify_zero_shot(text: str, provider, labels: list[str] = LABELS) -> str | None:
    """
    Classify `text` using zero-shot prompting.

    TODO:
      1. Build the prompt with zero_shot_prompt().
      2. Call provider.chat() with a low temperature (0 or 0.1 is good for classification).
      3. Parse the result with parse_label().
      4. Return the label (or None if parsing fails).
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement classify_zero_shot()")


# ---------------------------------------------------------------------------
# Few-shot classifier
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = [
    ("NASA launched a new space telescope to study distant galaxies.", "science"),
    ("The central bank cut interest rates amid recession fears.", "business"),
    ("The striker scored a hat-trick in the cup final.", "sports"),
    ("Eating more fibre reduces cholesterol and improves gut health.", "health"),
    ("The new legislation restricts campaign finance donations.", "politics"),
    ("Engineers demonstrated a chip that runs on ambient light alone.", "technology"),
]


def few_shot_prompt(text: str, examples: list[tuple[str, str]], labels: list[str]) -> str:
    """
    Build a few-shot classification prompt.

    Few-shot means: prepend labelled examples before the query.
    This anchors the model's interpretation of each label.

    TODO: craft a prompt that:
      1. Describes the task and valid labels (same as zero-shot).
      2. Shows each (example_text, label) pair in a clear, consistent format.
         A common pattern:
           Text: <example_text>
           Label: <label>
      3. Ends with the query text in the same format but without the label
         (so the model fills it in).

    Tip: keep the format consistent — if you use "Text:" in examples, use it
    for the query too.
    """
    # TODO: return the formatted prompt string
    raise NotImplementedError("TODO: implement few_shot_prompt()")


def classify_few_shot(
    text: str,
    provider,
    examples: list[tuple[str, str]] = FEW_SHOT_EXAMPLES,
    labels: list[str] = LABELS,
) -> str | None:
    """
    Classify `text` using few-shot prompting.

    TODO: same structure as classify_zero_shot() but use few_shot_prompt().
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement classify_few_shot()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (chat model: {provider.chat_model})")

    dataset = load_dataset()

    # Run on the first 10 examples only (LLM calls are slow/costly for the full set)
    sample = dataset[:10]

    print("\n" + "=" * 70)
    print("ZERO-SHOT CLASSIFICATION")
    print("=" * 70)
    zero_correct = 0
    for item in sample:
        pred = classify_zero_shot(item["text"], provider)
        correct = pred == item["label"]
        if correct:
            zero_correct += 1
        mark = "✓" if correct else "✗"
        print(f"  [{mark}] true={item['label']:<12} pred={str(pred):<12} | {item['text'][:60]}...")

    print(f"\n  Zero-shot accuracy: {zero_correct}/{len(sample)}")

    print("\n" + "=" * 70)
    print("FEW-SHOT CLASSIFICATION")
    print("=" * 70)
    few_correct = 0
    for item in sample:
        pred = classify_few_shot(item["text"], provider)
        correct = pred == item["label"]
        if correct:
            few_correct += 1
        mark = "✓" if correct else "✗"
        print(f"  [{mark}] true={item['label']:<12} pred={str(pred):<12} | {item['text'][:60]}...")

    print(f"\n  Few-shot accuracy: {few_correct}/{len(sample)}")

    print("\n" + "=" * 70)
    print("REFLECTION")
    print("=" * 70)
    print("  Did few-shot improve accuracy? Which categories are hardest?")
    print("  Notice the latency — each call goes to the network.")
    print("  In Task 3 we'll compare this to a trained classifier on the full set.")


if __name__ == "__main__":
    main()
