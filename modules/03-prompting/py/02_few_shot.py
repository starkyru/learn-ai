"""
Task 2 — Few-shot vs zero-shot 🟡

What this teaches:
  - Zero-shot: just the task description — the model must generalise from
    its training alone.
  - Few-shot: task description + k labelled examples before the actual
    input — the model "reads the pattern" from them.
  - In general, more examples → better accuracy BUT: more tokens, more
    cost, and diminishing returns beyond ~5-10 examples.
  - The quality of examples matters more than quantity. One well-chosen
    example can outperform three mediocre ones.

How to run:
  uv run python modules/03-prompting/py/02_few_shot.py
"""

from __future__ import annotations

from llm_core import get_provider, ChatMessage

# ---------------------------------------------------------------------------
# Task: sentiment classification (positive / negative / neutral).
# ---------------------------------------------------------------------------

TEST_INPUTS = [
    "I love this product! Works exactly as described.",
    "Absolute garbage. Broke after one day.",
    "It's fine. Does what it says.",
    "Incredible quality. Will buy again.",
    "Disappointed. Not worth the price.",
]

# ---------------------------------------------------------------------------
# TODO 1: Define the few-shot examples.
#         Each example is a dict with "input" and "label". These will be
#         injected as user/assistant pairs in the messages array.
#         Start with ONE and then try THREE — do you see a difference?
# ---------------------------------------------------------------------------
FEW_SHOT_EXAMPLES: list[dict[str, str]] = [
    # {"input": "...", "label": "positive"},
    # {"input": "...", "label": "negative"},
    # {"input": "...", "label": "neutral"},
]


# ---------------------------------------------------------------------------
# TODO 2: Implement build_zero_shot_messages.
#         Return a list of ChatMessage with:
#           - system: "You are a sentiment classifier. Respond with exactly one
#             word: positive, negative, or neutral."
#           - user: the input text
# ---------------------------------------------------------------------------
def build_zero_shot_messages(input_text: str) -> list[ChatMessage]:
    # TODO: return the messages list
    return []


# ---------------------------------------------------------------------------
# TODO 3: Implement build_few_shot_messages.
#         Build messages with the same system prompt, then insert examples as
#         alternating user/assistant pairs before the final user message.
#         Structure:
#           system
#           user: example1.input
#           assistant: example1.label
#           user: example2.input  (if k >= 2)
#           assistant: example2.label
#           ...
#           user: input_text  ← actual query
# ---------------------------------------------------------------------------
def build_few_shot_messages(
    input_text: str, examples: list[dict[str, str]]
) -> list[ChatMessage]:
    # TODO: implement
    return []


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")
    print("Comparing zero-shot vs few-shot sentiment classification\n")
    header = f"{'Input':<55} {'0-shot':<12} {'1-shot':<12} {'3-shot'}"
    print(header)
    print("-" * 90)

    for text in TEST_INPUTS:
        # ---------------------------------------------------------------------
        # TODO 4: For each input, make three calls:
        #   - Zero-shot (no examples)
        #   - One-shot (first example from FEW_SHOT_EXAMPLES)
        #   - Three-shot (first three examples)
        #   Trim and lowercase the results.
        # ---------------------------------------------------------------------

        # zero_shot = llm.chat(build_zero_shot_messages(text)).text.strip().lower()
        # one_shot = llm.chat(build_few_shot_messages(text, FEW_SHOT_EXAMPLES[:1])).text.strip().lower()
        # three_shot = llm.chat(build_few_shot_messages(text, FEW_SHOT_EXAMPLES[:3])).text.strip().lower()
        # truncated = text[:50] + "..." if len(text) > 50 else text
        # print(f"{truncated:<55} {zero_shot:<12} {one_shot:<12} {three_shot}")

        truncated = text[:50] + "..." if len(text) > 50 else text
        print(f"{truncated:<55} {'TODO':<12} {'TODO':<12} TODO")

    print("""
Observations:
- Do the results differ between 0-shot and 3-shot?
- Does the model follow the "one word only" instruction in all cases?
- Which examples were most effective?
(Fill in your observations here after running)
""")

    # -------------------------------------------------------------------------
    # TODO 5 (stretch): Count tokens for each variant and compute the cost
    #         increase of adding examples. At what point does few-shot become
    #         too expensive for your use case?
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
