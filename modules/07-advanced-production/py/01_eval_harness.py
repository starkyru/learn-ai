"""
Task 1 — Eval harness + LLM-as-judge  🟡

What this teaches:
  - You can't improve what you can't measure. An eval harness runs your system
    over a fixed test set and grades each output automatically.
  - LLM-as-judge: ask a second LLM call to score an output against a rubric.
    This handles open-ended generation quality without hand-crafted assertions.
  - Aggregating scores and pass rates lets you catch regressions when you
    change the model, prompt, or retrieval pipeline.

How to run:
  uv run python modules/07-advanced-production/py/01_eval_harness.py
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from llm_core import get_provider, ChatMessage, ChatOptions


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    id: str
    input: str    # the user question to send to the system under test
    rubric: str   # what a good answer must do / contain


# TODO 1: Add at least 5 test cases across different quality dimensions:
#   - factual accuracy
#   - instruction following
#   - conciseness / length constraints
#   - safety / refusal behaviour
TEST_CASES: list[TestCase] = [
    TestCase(
        id="tc-01",
        input="What is the capital of France?",
        rubric="The answer must name Paris as the capital of France.",
    ),
    TestCase(
        id="tc-02",
        input="Explain recursion in one sentence.",
        rubric=(
            "The answer must be exactly one sentence and correctly describe "
            "recursion as a function calling itself."
        ),
    ),
    # TODO: add 3+ more test cases
]


# ---------------------------------------------------------------------------
# System under test
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = "You are a concise, accurate assistant. Answer in as few words as possible."


def run_system(user_input: str) -> str:
    """Run the system under test and return its response text.

    TODO 2: Call provider.chat() with SYSTEM_PROMPT (as system role) and
    user_input (as user role). Return result.text.
    """
    raise NotImplementedError("TODO: implement run_system")


# ---------------------------------------------------------------------------
# LLM-as-judge
# ---------------------------------------------------------------------------

PASS_THRESHOLD = 7

JUDGE_SYSTEM_PROMPT = f"""You are an impartial evaluator. You receive:
  - A user question
  - A rubric describing what a good answer must do
  - The system's actual answer

Score the answer from 0 to 10 based on how well it satisfies the rubric.
Respond ONLY with valid JSON (no prose, no markdown fences):
{{"score": <0-10>, "pass": <true|false>, "reasoning": "<one sentence>"}}

pass is true if score >= {PASS_THRESHOLD}."""


@dataclass
class JudgeScore:
    score: int
    pass_: bool
    reasoning: str


def judge_output(question: str, rubric: str, answer: str) -> JudgeScore:
    """Ask an LLM judge to score the answer against the rubric.

    TODO 3: Build a user message containing the question, rubric, and answer
    (clearly labelled). Call provider.chat() with JUDGE_SYSTEM_PROMPT.
    Parse the JSON response into a JudgeScore. Handle parse errors by
    returning JudgeScore(score=0, pass_=False, reasoning="parse error").
    """
    raise NotImplementedError("TODO: implement judge_output")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    test_case: TestCase
    answer: str
    score: JudgeScore
    latency_ms: float


def run_eval() -> None:
    provider = get_provider()
    print(f"\nEval harness | provider: {provider.name} / {provider.chat_model}")
    print(f"Test cases: {len(TEST_CASES)}\n")
    print("=" * 70)

    results: list[EvalResult] = []

    for tc in TEST_CASES:
        t0 = time.perf_counter()

        # TODO 4: Call run_system(tc.input) to get the answer.
        #         Call judge_output(tc.input, tc.rubric, answer) to score it.
        #         Compute latency = (time.perf_counter() - t0) * 1000 ms.
        #         Append an EvalResult and print a one-line summary:
        #           [tc-01] PASS 8/10  "What is the capital..."  (142 ms)

        print(f"TODO: run test case {tc.id}")

    # TODO 5: Print an aggregate summary:
    #   - Pass rate: X/Y (Z%)
    #   - Average score: N.N / 10
    #   - Average latency: N ms
    #   - List any FAIL cases with their reasoning
    print("\n--- Summary ---")
    print("TODO: print aggregate stats.")


if __name__ == "__main__":
    run_eval()
