"""
Task 4 — Output parsing & guardrails 🟢

What this teaches:
  - Forcing a constrained output format (e.g. "one word only") is harder
    than it sounds. Models add punctuation, explanations, or extra words.
  - Guardrails = validate the output, and if it fails, retry with feedback.
  - The repair loop: prompt → parse → fail → tell the model what went wrong
    → try again. This is more robust than hoping the first call is perfect.
  - After 2-3 failed retries you should give up and raise — infinite retry
    loops are a production anti-pattern.

How to run:
  uv run python modules/03-prompting/py/04_guardrails.py
"""

from __future__ import annotations

from typing import Literal

from llm_core import get_provider, ChatMessage

SentimentLabel = Literal["positive", "negative", "neutral"]
VALID_LABELS: tuple[str, ...] = ("positive", "negative", "neutral")

SYSTEM_PROMPT = """You are a sentiment classifier.
Respond with EXACTLY one word — no punctuation, no explanation, no extra text.
The word must be one of: positive, negative, neutral."""


# ---------------------------------------------------------------------------
# TODO 1: Implement parse_label.
#         Take the raw model output string, clean it, and return the matching
#         SentimentLabel. Raise a ValueError if the output doesn't match after
#         cleaning.
#         Cleaning steps (in order):
#           1. strip() whitespace
#           2. lower()
#           3. Remove non-alpha chars: re.sub(r"[^a-z]", "", text)
# ---------------------------------------------------------------------------
def parse_label(raw: str) -> SentimentLabel:
    import re
    # TODO: implement
    cleaned = re.sub(r"[^a-z]", "", raw.strip().lower())
    if cleaned in VALID_LABELS:
        return cleaned  # type: ignore[return-value]
    raise ValueError(
        f'Invalid label: "{raw}" → cleaned: "{cleaned}". '
        f'Expected one of: {", ".join(VALID_LABELS)}'
    )


# ---------------------------------------------------------------------------
# TODO 2: Implement classify_with_guardrails.
#         Try up to max_retries times to get a valid label.
#         On parse failure: add the bad assistant message to history, then add
#         a user correction message explaining what went wrong.
#         Return the valid label on success, raise after exhausting retries.
# ---------------------------------------------------------------------------
def classify_with_guardrails(text: str, max_retries: int = 3) -> SentimentLabel:
    llm = get_provider()
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=text),
    ]

    for attempt in range(max_retries):
        # TODO: implement one attempt of the repair loop.
        #   - Call llm.chat(messages) and try to parse_label(...) the reply text;
        #     return the label immediately if it parses.
        #   - If parse_label raises ValueError, the reply was malformed: grow the
        #     conversation so the next attempt can self-correct. Append the model's
        #     bad reply as a ChatMessage(role="assistant", ...), then append a
        #     ChatMessage(role="user", ...) that quotes the bad output and restates
        #     the one-word constraint. Then let the loop try again.
        #   - After the loop exhausts max_retries, the raise below fires.

        print(f"Attempt {attempt + 1}: TODO — implement the retry loop above.")
        break  # remove once implemented

    raise RuntimeError(f"Failed to get a valid label after {max_retries} attempts.")


# ---------------------------------------------------------------------------
# Demo inputs — some chosen to provoke edge-case outputs.
# ---------------------------------------------------------------------------
INPUTS = [
    "This is the best product I've ever used!",
    "Totally broken. Avoid at all costs.",
    "Meh. It's fine I guess.",
    "Not bad, not great — somewhere in the middle.",
    "I'm genuinely impressed. Five stars!",
]


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")
    print("Classifying with guardrails (retry on invalid output):\n")

    for text in INPUTS:
        try:
            label = classify_with_guardrails(text)
            print(f'"{text}"\n  → {label}\n')
        except RuntimeError as err:
            print(f'"{text}"\n  → FAILED: {err}\n')

    # -------------------------------------------------------------------------
    # TODO 3 (stretch): Add a second constraint — the model must also return a
    #         confidence score as a float between 0.0 and 1.0 in the format:
    #         "positive 0.92". Update parse_label to return a tuple
    #         (label, confidence) and validate the confidence range.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
