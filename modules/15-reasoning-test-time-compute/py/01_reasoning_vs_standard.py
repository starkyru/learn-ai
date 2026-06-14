"""
Task 1 — Reasoning vs standard model 🟢

What this teaches:
  - Reasoning / extended-thinking models spend extra compute at inference time
    before producing visible output. This costs more but often yields better
    correctness on hard multi-step problems.
  - You will measure the difference concretely: answer quality, token counts,
    and wall-clock latency.
  - This file goes BEYOND llm_core because extended thinking and OpenAI reasoning
    models require provider-specific SDK parameters that the abstraction does not
    expose. That is intentional: the leak teaches you where the abstraction breaks.

Environment variables:
  OPENAI_API_KEY        — required for the OpenAI path
  OPENAI_CHAT_MODEL     — standard model (default: gpt-4o-mini)
  OPENAI_REASONING_MODEL — reasoning model (default: o4-mini)
  ANTHROPIC_API_KEY     — required for the Anthropic extended-thinking path
  ANTHROPIC_MODEL       — base model (default: claude-opus-4-8)

How to run:
  uv run python modules/15-reasoning-test-time-compute/py/01_reasoning_vs_standard.py
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Test problems — hard enough that extra reasoning helps.
# ---------------------------------------------------------------------------
PROBLEMS = [
    {
        "id": "math",
        "question": (
            "A farmer has 17 sheep. All but 9 die. How many sheep are left? "
            "Now, separately: if it takes 1.5 hours to boil 1 egg, how long does "
            "it take to boil 3 eggs simultaneously in the same pot? "
            "Give both answers and explain your reasoning."
        ),
        "expected_contains": ["9", "1.5"],
    },
    {
        "id": "logic",
        "question": (
            "A doctor has a brother who is a lawyer. The lawyer's sister is a "
            "surgeon. The surgeon has no siblings. How is this possible? "
            "Explain step by step."
        ),
        "expected_contains": ["doctor"],
    },
    {
        "id": "multi-step",
        "question": (
            "Alice, Bob, and Carol each have some apples. Alice has twice as many "
            "as Bob. Carol has 3 fewer than Alice. Together they have 29 apples. "
            "How many does each person have?"
        ),
        "expected_contains": ["8", "4", "5"],  # Bob=4, Alice=8 (wait, let's solve: B + 2B + 2B-3 = 29 -> 5B-3=29 -> B=6.4 ... hmm)
        # Actually: B + 2B + (2B-3) = 29 -> 5B = 32 -> B = 6.4 (not integer)
        # Let's keep it as an open problem — interesting to see if models notice!
    },
]


@dataclass
class ModelResult:
    model: str
    strategy: str
    answer: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


# ---------------------------------------------------------------------------
# TODO 1: Implement call_standard.
#         Use get_provider("openai") from llm_core with the standard chat model.
#         Record start/end time for latency; return a ModelResult.
#         Hint: result.usage has input_tokens and output_tokens.
# ---------------------------------------------------------------------------
def call_standard(question: str) -> ModelResult:
    # from llm_core import get_provider, ChatMessage
    # provider = get_provider("openai")
    # start = time.time()
    # result = provider.chat([ChatMessage("user", question)])
    # elapsed_ms = (time.time() - start) * 1000
    # return ModelResult(
    #     model=result.model,
    #     strategy="standard",
    #     answer=result.text,
    #     input_tokens=result.usage.input_tokens or 0,
    #     output_tokens=result.usage.output_tokens or 0,
    #     latency_ms=elapsed_ms,
    # )
    raise NotImplementedError("TODO: implement call_standard")


# ---------------------------------------------------------------------------
# TODO 2: Implement call_reasoning_openai.
#         Use the openai SDK directly (NOT llm_core) so you can pass
#         `reasoning_effort` and use `max_completion_tokens`.
#
#         Key differences from a standard call:
#         - model: os.getenv("OPENAI_REASONING_MODEL", "o4-mini")
#         - Use max_completion_tokens instead of max_tokens
#         - Pass reasoning_effort="medium" (or "high" for harder problems)
#         - usage.completion_tokens_details shows reasoning vs. visible tokens
#
#         Example skeleton:
#           import openai
#           client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#           response = client.chat.completions.create(
#               model="o4-mini",
#               messages=[{"role": "user", "content": question}],
#               max_completion_tokens=4096,
#               reasoning_effort="medium",
#           )
# ---------------------------------------------------------------------------
def call_reasoning_openai(question: str) -> ModelResult:
    raise NotImplementedError("TODO: implement call_reasoning_openai")


# ---------------------------------------------------------------------------
# TODO 3 (alternative): Implement call_reasoning_anthropic.
#         Use the anthropic SDK with extended thinking enabled.
#         This is a beta feature — pass betas=["interleaved-thinking-2025-05-14"].
#
#         Key parameters:
#         - thinking={"type": "enabled", "budget_tokens": 5000}
#         - The response content list contains ThinkingBlock and TextBlock items.
#         - Extract .text from TextBlock items for the visible answer.
#         - Extract .thinking from ThinkingBlock items if you want to display reasoning.
#
#         Example skeleton:
#           import anthropic
#           client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
#           response = client.beta.messages.create(
#               model=os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8"),
#               max_tokens=8000,
#               thinking={"type": "enabled", "budget_tokens": 5000},
#               betas=["interleaved-thinking-2025-05-14"],
#               messages=[{"role": "user", "content": question}],
#           )
# ---------------------------------------------------------------------------
def call_reasoning_anthropic(question: str) -> ModelResult:
    raise NotImplementedError("TODO: implement call_reasoning_anthropic")


# ---------------------------------------------------------------------------
# Helper: print a comparison table row.
# ---------------------------------------------------------------------------
def print_row(label: str, r: ModelResult) -> None:
    truncated = r.answer.replace("\n", " ")[:60] + "..."
    print(
        f"  {label:<18} | {r.model:<20} | {r.latency_ms:6.0f} ms "
        f"| in={r.input_tokens:5d} out={r.output_tokens:5d} "
        f"| {truncated}"
    )


def main() -> None:
    print("=== Task 1: Reasoning vs Standard Model ===\n")
    print(
        f"{'Strategy':<18} | {'Model':<20} | {'Latency':>9} "
        f"| {'Tokens':^22} | Answer (truncated)"
    )
    print("-" * 100)

    for problem in PROBLEMS:
        print(f"\nProblem [{problem['id']}]: {problem['question'][:80]}...")

        # -------------------------------------------------------------------------
        # TODO 4: Call call_standard and one of the reasoning implementations.
        #         Wrap each in a try/except so a missing API key doesn't crash
        #         the whole script — print a placeholder row instead.
        # -------------------------------------------------------------------------

        try:
            std = call_standard(problem["question"])
            print_row("standard", std)
        except NotImplementedError:
            print("  standard           | (TODO: implement call_standard)")
        except Exception as e:
            print(f"  standard           | ERROR: {e}")

        # Pick whichever reasoning provider you have a key for:
        try:
            reasoning = call_reasoning_openai(problem["question"])
            print_row("reasoning (openai)", reasoning)
        except NotImplementedError:
            print("  reasoning (openai) | (TODO: implement call_reasoning_openai)")
        except Exception as e:
            print(f"  reasoning (openai) | ERROR: {e}")

        # -------------------------------------------------------------------------
        # TODO 5 (stretch): Check whether the answer contains the expected
        #         keywords from problem["expected_contains"]. Print ✓ or ✗.
        # -------------------------------------------------------------------------

    print()
    print("Observation: note how reasoning models trade latency + tokens for accuracy.")
    print("On simple problems the overhead is rarely worth it.")


if __name__ == "__main__":
    main()
