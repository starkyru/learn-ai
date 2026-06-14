"""
Task 3 — Chain-of-thought & self-consistency 🟡

What this teaches:
  - Chain-of-thought (CoT): ask the model to "think step by step" before
    giving the final answer. For reasoning tasks this dramatically improves
    accuracy because the model can't skip steps it would otherwise hide.
  - Self-consistency: sample the same CoT prompt N times (temperature > 0)
    and majority-vote the final answer. Individual samples may reach the
    wrong answer via different reasoning paths; voting averages out noise.
  - The trade-off: CoT uses more output tokens (= higher cost) and
    self-consistency multiplies that by N. Use sparingly on hard tasks.

How to run:
  uv run python modules/03-prompting/py/03_cot.py
"""

from __future__ import annotations

import re
from collections import Counter

from llm_core import get_provider, ChatOptions

# ---------------------------------------------------------------------------
# Sample problems — grade-school math and logical reasoning.
# ---------------------------------------------------------------------------
PROBLEMS = [
    {
        "question": (
            "A shop sells apples for $0.50 each and bananas for $0.30 each. "
            "Alice buys 4 apples and 6 bananas. How much does she pay in total?"
        ),
        "answer": "3.80",
    },
    {
        "question": (
            "If all Bloops are Razzies and all Razzies are Lazzies, "
            "are all Bloops definitely Lazzies?"
        ),
        "answer": "yes",
    },
    {
        "question": "A train travels 60 km in 45 minutes. What is its speed in km/h?",
        "answer": "80",
    },
]


# ---------------------------------------------------------------------------
# TODO 1: Write a zero-shot prompt (no CoT) that asks for only the final answer.
#         The model should respond with JUST the answer, no explanation.
# ---------------------------------------------------------------------------
def build_direct_prompt(question: str) -> str:
    # TODO: return a prompt that instructs the model to answer directly.
    # Example: "Answer with only the final answer, no explanation.\n\nQuestion: ..."
    return f"TODO: build direct (non-CoT) prompt for: {question}"


# ---------------------------------------------------------------------------
# TODO 2: Write a chain-of-thought prompt.
#         Include "Let's think step by step" or a natural variant.
#         The response should contain reasoning AND a clearly marked final answer.
#         Suggested format: "Final answer: <answer>"
# ---------------------------------------------------------------------------
def build_cot_prompt(question: str) -> str:
    # TODO: return a CoT prompt.
    return f"TODO: build CoT prompt for: {question}"


# ---------------------------------------------------------------------------
# TODO 3: Implement extract_final_answer.
#         Parse the CoT response to extract just the final answer.
#         Your logic should match the format you used in TODO 2.
#         For "Final answer: X" format: re.search(r"[Ff]inal answer:\s*(.+)", text)
# ---------------------------------------------------------------------------
def extract_final_answer(cot_response: str) -> str:
    # TODO: implement extraction matching your CoT format
    return cot_response.strip().split("\n")[-1]


# ---------------------------------------------------------------------------
# TODO 4: Implement majority_vote.
#         Given a list of answer strings, return the most common one.
#         Normalise before comparing: lowercase + strip.
# ---------------------------------------------------------------------------
def majority_vote(answers: list[str]) -> str:
    # TODO: implement
    normalised = [a.lower().strip() for a in answers]
    if not normalised:
        return ""
    return Counter(normalised).most_common(1)[0][0]


N_SAMPLES = 3  # number of self-consistency samples


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} / {llm.chat_model}\n")

    for problem in PROBLEMS:
        question = problem["question"]
        expected = problem["answer"]
        print(f"\nQ: {question}")
        print(f"Expected: {expected}\n")

        # -------------------------------------------------------------------------
        # TODO 5: Zero-shot direct answer.
        # -------------------------------------------------------------------------
        # direct_result = llm.chat([{"role": "user", "content": build_direct_prompt(question)}])
        # print(f"Direct (0-shot): {direct_result.text.strip()}")
        print("Direct (0-shot): TODO")

        # -------------------------------------------------------------------------
        # TODO 6: Single CoT sample (temperature=0 for determinism).
        # -------------------------------------------------------------------------
        # cot_result = llm.chat(
        #     [{"role": "user", "content": build_cot_prompt(question)}],
        #     ChatOptions(temperature=0),
        # )
        # cot_answer = extract_final_answer(cot_result.text)
        # print(f"CoT (single):   {cot_answer}")
        # print("Reasoning snippet:", cot_result.text[:200] + "...")
        print("CoT (single):   TODO")

        # -------------------------------------------------------------------------
        # TODO 7: Self-consistency — sample N_SAMPLES times at temperature=0.7,
        #         extract each answer, majority vote.
        # -------------------------------------------------------------------------
        # samples = []
        # for _ in range(N_SAMPLES):
        #     r = llm.chat(
        #         [{"role": "user", "content": build_cot_prompt(question)}],
        #         ChatOptions(temperature=0.7),
        #     )
        #     samples.append(extract_final_answer(r.text))
        # winner = majority_vote(samples)
        # print(f"Self-consistency: samples={samples}, vote={winner}")
        print(f"Self-consistency (N={N_SAMPLES}): TODO")

    # -------------------------------------------------------------------------
    # TODO 8 (stretch): Count total output tokens for direct vs CoT vs
    #         self-consistency. CoT costs more — is the accuracy gain worth it
    #         for your use case? Print a cost comparison.
    # -------------------------------------------------------------------------


if __name__ == "__main__":
    main()
