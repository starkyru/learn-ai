"""
Task 4 — Cost / latency of reasoning strategies 🟢

What this teaches:
  - Making the test-time compute trade-off concrete: plot tokens used, wall time,
    and accuracy for each strategy on a fixed benchmark.
  - Estimated cost lets you compare "accuracy per dollar" and find the sweet spot.
  - This is the culminating exercise for the module — pull everything together.

How to run:
  uv run python modules/15-reasoning-test-time-compute/py/04_cost_latency.py

Note: this file runs a fixed benchmark. If you haven't implemented Tasks 1–3, the
      strategies that call them will raise NotImplementedError and be skipped.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Price table — $ per 1,000,000 tokens (update as prices change).
# ---------------------------------------------------------------------------
PRICE_TABLE: dict[str, dict[str, float]] = {
    "gpt-4o-mini":  {"input_per_1m": 0.15,   "output_per_1m": 0.60},
    "gpt-4o":       {"input_per_1m": 5.00,   "output_per_1m": 15.00},
    "o4-mini":      {"input_per_1m": 1.10,   "output_per_1m": 4.40},  # pricing varies
    "claude-opus-4-8":  {"input_per_1m": 15.00, "output_per_1m": 75.00},
    "claude-haiku-4-5": {"input_per_1m": 0.80,  "output_per_1m": 4.00},
    "default":      {"input_per_1m": 0.50,   "output_per_1m": 1.50},
}

# ---------------------------------------------------------------------------
# Benchmark problems (same set across all strategies for fair comparison).
# ---------------------------------------------------------------------------
BENCHMARK = [
    {
        "question": "What is 23 × 47? Show your working.",
        "answer": "1081",
    },
    {
        "question": (
            "A snail climbs 3 metres up a wall each day and slips back 2 metres "
            "each night. The wall is 10 metres tall. How many days to reach the top?"
        ),
        "answer": "8",
    },
    {
        "question": (
            "Alice is taller than Bob. Bob is taller than Carol. "
            "Is Alice taller than Carol? Give only YES or NO and one sentence of reasoning."
        ),
        "answer": "yes",
    },
]


@dataclass
class BenchmarkResult:
    strategy: str
    model: str
    correct: int = 0
    total: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def estimated_cost(self) -> float:
        prices = PRICE_TABLE.get(self.model, PRICE_TABLE["default"])
        return (
            (self.total_input_tokens / 1_000_000) * prices["input_per_1m"]
            + (self.total_output_tokens / 1_000_000) * prices["output_per_1m"]
        )

    def accuracy_per_dollar(self) -> float:
        cost = self.estimated_cost()
        return self.accuracy / cost if cost > 0 else float("inf")


# ---------------------------------------------------------------------------
# Strategy implementations — using only llm_core for portability.
# Adapt or replace these with the implementations from tasks 1–3 if you want
# provider-specific reasoning models.
# ---------------------------------------------------------------------------

def _cot_messages(question: str) -> list[ChatMessage]:
    return [
        ChatMessage(
            "system",
            "Think step by step. End with 'Final answer: <answer>'",
        ),
        ChatMessage("user", question),
    ]


def _extract(text: str) -> str:
    import re
    m = re.search(r"[Ff]inal answer[:\s]+(.+)", text)
    return m.group(1).strip() if m else text.strip().split("\n")[-1].strip()


def _is_correct(answer: str, expected: str) -> bool:
    return expected.lower().strip() in answer.lower()


# ---------------------------------------------------------------------------
# TODO 1: Implement run_zero_shot(problem) -> BenchmarkResult.
#         One call with no CoT, temperature=0.
#         Record tokens and latency.
# ---------------------------------------------------------------------------
def run_zero_shot(problems: list[dict]) -> BenchmarkResult:
    llm = get_provider()
    result = BenchmarkResult(strategy="zero-shot", model=llm.chat_model)
    for p in problems:
        # TODO: call llm.chat, record usage and latency, check correctness
        result.total += 1
        result.errors.append("not implemented")
    return result


# ---------------------------------------------------------------------------
# TODO 2: Implement run_cot(problems) -> BenchmarkResult.
#         One CoT call at temperature=0. Extract final answer.
# ---------------------------------------------------------------------------
def run_cot(problems: list[dict]) -> BenchmarkResult:
    llm = get_provider()
    result = BenchmarkResult(strategy="CoT (single)", model=llm.chat_model)
    for p in problems:
        # TODO: call llm.chat with CoT system prompt, record usage and latency
        result.total += 1
        result.errors.append("not implemented")
    return result


# ---------------------------------------------------------------------------
# TODO 3: Implement run_self_consistency(problems, n=3) -> BenchmarkResult.
#         N samples at temperature=0.8, majority vote.
# ---------------------------------------------------------------------------
def run_self_consistency(problems: list[dict], n: int = 3) -> BenchmarkResult:
    llm = get_provider()
    result = BenchmarkResult(strategy=f"self-consistency (N={n})", model=llm.chat_model)
    for p in problems:
        # TODO: sample N times, majority vote, record aggregate tokens and latency
        result.total += 1
        result.errors.append("not implemented")
    return result


# ---------------------------------------------------------------------------
# TODO 4: Implement run_self_refine(problems, iterations=2) -> BenchmarkResult.
#         Draft → critique → revise loop. Score the final revision.
# ---------------------------------------------------------------------------
def run_self_refine(problems: list[dict], iterations: int = 2) -> BenchmarkResult:
    llm = get_provider()
    result = BenchmarkResult(strategy=f"self-refine ({iterations} iter)", model=llm.chat_model)
    for p in problems:
        # TODO: implement the refine loop, score final answer
        result.total += 1
        result.errors.append("not implemented")
    return result


# ---------------------------------------------------------------------------
# TODO 5 (stretch): Implement run_reasoning_model(problems) -> BenchmarkResult.
#         Call OpenAI o4-mini or Anthropic extended thinking directly via SDK.
#         Use a different model name so the price lookup is correct.
# ---------------------------------------------------------------------------
def run_reasoning_model(problems: list[dict]) -> BenchmarkResult:
    result = BenchmarkResult(strategy="reasoning model", model="o4-mini")
    for p in problems:
        result.total += 1
        result.errors.append("not implemented (stretch)")
    return result


def print_table(results: list[BenchmarkResult]) -> None:
    print(
        f"\n{'Strategy':<30} {'Model':<20} {'Acc':>6} {'In tok':>8} "
        f"{'Out tok':>8} {'Latency ms':>11} {'Est. cost $':>12} {'Acc/$ ':>10}"
    )
    print("-" * 110)
    for r in sorted(results, key=lambda x: x.estimated_cost()):
        if r.total == 0:
            continue
        acc_str = f"{r.accuracy:.0%}"
        cost_str = f"{r.estimated_cost():.6f}"
        apd_str = f"{r.accuracy_per_dollar():.1f}" if r.estimated_cost() > 0 else "inf"
        print(
            f"{r.strategy:<30} {r.model:<20} {acc_str:>6} "
            f"{r.total_input_tokens:>8} {r.total_output_tokens:>8} "
            f"{r.total_latency_ms:>11.0f} {cost_str:>12} {apd_str:>10}"
        )

    # Find sweet spot
    valid = [r for r in results if r.total > 0 and r.estimated_cost() > 0]
    if valid:
        best = max(valid, key=lambda r: r.accuracy_per_dollar())
        print(f"\nSweet spot (best accuracy per $): {best.strategy!r}")


def main() -> None:
    print("=== Task 4: Cost / Latency of Reasoning Strategies ===")
    print(f"Benchmark: {len(BENCHMARK)} problems\n")

    # -------------------------------------------------------------------------
    # TODO 6: Call each run_* function and collect results.
    #         Wrap each in try/except — a NotImplementedError should just skip
    #         the strategy gracefully.
    # -------------------------------------------------------------------------

    strategies = [
        run_zero_shot,
        run_cot,
        lambda p: run_self_consistency(p, n=3),
        lambda p: run_self_refine(p, iterations=2),
        run_reasoning_model,
    ]

    results: list[BenchmarkResult] = []
    for fn in strategies:
        try:
            r = fn(BENCHMARK)
            results.append(r)
            status = f"{r.correct}/{r.total}" if r.total > 0 else "skipped"
            print(f"  {r.strategy:<30} done ({status})")
        except Exception as e:
            print(f"  ERROR running strategy: {e}")

    print_table(results)

    print(
        "\nObservation: the 'sweet spot' balances accuracy and cost. "
        "For cheap/simple tasks zero-shot wins. For high-stakes tasks "
        "the reasoning model (or self-consistency-5) is worth the premium."
    )


if __name__ == "__main__":
    main()
