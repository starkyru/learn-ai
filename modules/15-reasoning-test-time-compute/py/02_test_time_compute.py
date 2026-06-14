"""
Task 2 — Test-time compute without a reasoning model 🟡

What this teaches:
  - You don't need a special reasoning model to get better answers — you can
    spend more compute at inference time using a standard model and these techniques:
      * Self-consistency: sample the same CoT prompt N times, majority-vote the final answer.
      * Best-of-N + verifier: sample N answers, score each with a cheap verifier, pick best.
  - Accuracy rises with N — but so does cost. The verifier is the key to efficiency.
  - Implementing these by hand (rather than using a framework) teaches you exactly
    what "test-time compute" means in practice.

How to run:
  uv run python modules/15-reasoning-test-time-compute/py/02_test_time_compute.py
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Test problems with verifiable answers.
# ---------------------------------------------------------------------------
PROBLEMS = [
    {
        "question": "What is 17 × 24? Show your working.",
        "answer": "408",
    },
    {
        "question": (
            "A bat and a ball cost $1.10 in total. "
            "The bat costs $1.00 more than the ball. "
            "How much does the ball cost? Give the answer in cents."
        ),
        "answer": "5",
    },
    {
        "question": (
            "If you have a 3-litre jug and a 5-litre jug, how do you measure "
            "exactly 4 litres of water? List the steps."
        ),
        "answer": "4",  # look for "4" appearing in the answer
    },
]

N_SAMPLES = 3  # default number of samples for self-consistency / best-of-N

COT_SYSTEM = (
    "You are a careful problem solver. "
    "Think step by step, then end your response with: "
    "'Final answer: <your answer>'"
)


@dataclass
class RunStats:
    strategy: str
    correct: int = 0
    total: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# TODO 1: Implement extract_final_answer.
#         Parse "Final answer: X" from the CoT response.
#         Strip punctuation and whitespace from the extracted value.
#         Fall back to the last non-empty line if the pattern isn't found.
# ---------------------------------------------------------------------------
def extract_final_answer(text: str) -> str:
    # Hint: re.search(r"[Ff]inal answer[:\s]+(.+)", text)
    # TODO: implement
    return text.strip().split("\n")[-1].strip()


# ---------------------------------------------------------------------------
# TODO 2: Implement majority_vote.
#         Given a list of answer strings, return the most common one.
#         Normalise: lowercase, strip, remove trailing punctuation.
# ---------------------------------------------------------------------------
def majority_vote(answers: list[str]) -> str:
    # TODO: implement
    normalised = [a.lower().strip().rstrip(".,!?") for a in answers]
    return Counter(normalised).most_common(1)[0][0] if normalised else ""


# ---------------------------------------------------------------------------
# TODO 3: Implement single_shot.
#         One CoT call at temperature=0. Return (answer, input_tokens, output_tokens).
# ---------------------------------------------------------------------------
def single_shot(question: str) -> tuple[str, int, int]:
    # llm = get_provider()
    # result = llm.chat(
    #     [ChatMessage("system", COT_SYSTEM), ChatMessage("user", question)],
    #     ChatOptions(temperature=0),
    # )
    # answer = extract_final_answer(result.text)
    # return answer, result.usage.input_tokens or 0, result.usage.output_tokens or 0
    raise NotImplementedError("TODO: implement single_shot")


# ---------------------------------------------------------------------------
# TODO 4: Implement self_consistency.
#         Sample `n` CoT completions at temperature=0.8.
#         Extract the final answer from each.
#         Return (majority_vote(answers), total_input_tokens, total_output_tokens).
# ---------------------------------------------------------------------------
def self_consistency(question: str, n: int = N_SAMPLES) -> tuple[str, int, int]:
    # llm = get_provider()
    # answers, in_tok, out_tok = [], 0, 0
    # for _ in range(n):
    #     result = llm.chat(
    #         [ChatMessage("system", COT_SYSTEM), ChatMessage("user", question)],
    #         ChatOptions(temperature=0.8),
    #     )
    #     answers.append(extract_final_answer(result.text))
    #     in_tok += result.usage.input_tokens or 0
    #     out_tok += result.usage.output_tokens or 0
    # return majority_vote(answers), in_tok, out_tok
    raise NotImplementedError("TODO: implement self_consistency")


# ---------------------------------------------------------------------------
# TODO 5: Implement verify.
#         Ask the model: "Is '<answer>' the correct answer to '<question>'?
#         Reply with only YES or NO."
#         Return True if the model says YES (case-insensitive).
# ---------------------------------------------------------------------------
def verify(question: str, answer: str) -> bool:
    # llm = get_provider()
    # prompt = (
    #     f"Question: {question}\n"
    #     f"Proposed answer: {answer}\n"
    #     "Is this answer correct? Reply with only YES or NO."
    # )
    # result = llm.chat(
    #     [ChatMessage("user", prompt)],
    #     ChatOptions(temperature=0),
    # )
    # return result.text.strip().upper().startswith("YES")
    raise NotImplementedError("TODO: implement verify")


# ---------------------------------------------------------------------------
# TODO 6: Implement best_of_n.
#         Sample `n` CoT answers at temperature=0.8.
#         Run verify() on each in order; return the first approved answer.
#         If none are approved, fall back to majority_vote of all candidates.
#         Return (answer, total_input_tokens, total_output_tokens).
# ---------------------------------------------------------------------------
def best_of_n(question: str, n: int = N_SAMPLES) -> tuple[str, int, int]:
    raise NotImplementedError("TODO: implement best_of_n")


# ---------------------------------------------------------------------------
# Helper: check if an answer is correct (simple substring match on expected).
# ---------------------------------------------------------------------------
def is_correct(answer: str, expected: str) -> bool:
    return expected.lower() in answer.lower()


def main() -> None:
    print("=== Task 2: Test-Time Compute (no reasoning model) ===\n")

    strategies: list[RunStats] = [
        RunStats("single-shot CoT"),
        RunStats(f"self-consistency (N={N_SAMPLES})"),
        RunStats(f"best-of-N (N={N_SAMPLES})"),
    ]

    for problem in PROBLEMS:
        q, expected = problem["question"], problem["answer"]
        print(f"Q: {q[:70]}... (expected: {expected})")

        # -------------------------------------------------------------------------
        # TODO 7: For each problem, call single_shot, self_consistency, and best_of_n.
        #         Update the corresponding RunStats (correct/total/tokens).
        #         Wrap each in try/except so a missing implementation prints a placeholder.
        # -------------------------------------------------------------------------

        for i, (strategy_fn, stats) in enumerate(
            [
                (lambda q=q: single_shot(q), strategies[0]),
                (lambda q=q: self_consistency(q, N_SAMPLES), strategies[1]),
                (lambda q=q: best_of_n(q, N_SAMPLES), strategies[2]),
            ]
        ):
            try:
                answer, in_tok, out_tok = strategy_fn()
                correct = is_correct(answer, expected)
                stats.correct += int(correct)
                stats.total += 1
                stats.input_tokens += in_tok
                stats.output_tokens += out_tok
                mark = "✓" if correct else "✗"
                print(f"  [{stats.strategy:<28}] {mark}  answer={answer!r:30}  tokens={in_tok+out_tok}")
            except NotImplementedError:
                print(f"  [{stats.strategy:<28}] TODO: not yet implemented")
        print()

    # -------------------------------------------------------------------------
    # TODO 8: Print a summary table: strategy | correct/total | accuracy | total tokens.
    # -------------------------------------------------------------------------
    print("\n--- Summary ---")
    print(f"{'Strategy':<32} {'Correct':>8} {'Accuracy':>10} {'Total tokens':>14}")
    print("-" * 70)
    for s in strategies:
        total_tok = s.input_tokens + s.output_tokens
        acc_str = f"{s.accuracy:.0%}" if s.total > 0 else "n/a"
        correct_str = f"{s.correct}/{s.total}" if s.total > 0 else "n/a"
        print(f"{s.strategy:<32} {correct_str:>8} {acc_str:>10} {total_tok:>14}")

    print()
    print(
        "Observation: accuracy should rise with N, but so does token cost. "
        "The verifier in best-of-N is the key to spending wisely."
    )


if __name__ == "__main__":
    main()
