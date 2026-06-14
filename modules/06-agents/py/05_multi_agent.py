"""
Task 5 — Multi-agent system  🟡

What this teaches:
  - A single agent has limited attention and context-window capacity. Breaking
    work into a planner + specialised workers is a practical architecture.
  - The planner decomposes the user's question into subtasks and delegates each
    to a focused worker that has its own system prompt and skills.
  - The planner collects results and calls a synthesiser to produce a coherent
    final answer.
  - This pattern scales horizontally: add workers (critic, coder, retriever, ...)
    without touching the planner.

Architecture:
  User question
    └─> Planner   (LLM: decompose -> JSON task list)
          ├─> Worker A  (LLM: solve subtask A)
          ├─> Worker B  (LLM: solve subtask B)
          └─> Synthesiser  (LLM: combine results -> final answer)

How to run:
  uv run python modules/06-agents/py/05_multi_agent.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from llm_core import get_provider, ChatMessage


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Subtask:
    id: str           # e.g. "task-1"
    worker: str       # "researcher" | "calculator" | "writer"
    instruction: str  # the specific question or job for that worker


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

# TODO 1: Write the planner system prompt.
#   It should instruct the LLM to:
#     - Break the user question into 2-4 independent subtasks.
#     - Output ONLY a JSON array — no prose, no markdown fence.
#     - Choose a worker type per subtask:
#         "researcher"  — fact retrieval or background info
#         "calculator"  — numerical computation or unit conversion
#         "writer"      — synthesis, summarisation, final prose
#   Example output:
#     [
#       {"id": "task-1", "worker": "researcher", "instruction": "Find the height of the Eiffel Tower."},
#       {"id": "task-2", "worker": "calculator",  "instruction": "Convert 330 metres to feet (1m=3.281ft)."}
#     ]

PLANNER_SYSTEM_PROMPT = "TODO: write the planner system prompt."


def run_planner(question: str) -> list[Subtask]:
    """Ask the planner LLM to decompose `question` into subtasks."""
    provider = get_provider()

    # TODO 2: Call provider.chat() with PLANNER_SYSTEM_PROMPT and `question`.
    #         Parse the JSON array from result.text.
    #         Validate each item has id, worker, instruction keys.
    #         Return a list of Subtask objects.

    print(f"\n[Planner] Decomposing: \"{question}\"")
    raise NotImplementedError("TODO: implement run_planner")


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

WORKER_PROMPTS: dict[str, str] = {
    "researcher": (
        # TODO 3a: Write a researcher prompt. The worker should answer factual
        #          questions concisely and say "I don't know" instead of guessing.
        "TODO: researcher prompt"
    ),
    "calculator": (
        # TODO 3b: Write a calculator prompt. The worker receives a plain-English
        #          computation task, works step-by-step, returns just the result
        #          and a brief explanation.
        "TODO: calculator prompt"
    ),
    "writer": (
        # TODO 3c: Write a synthesiser prompt. The worker receives a summary of
        #          other workers' findings and weaves them into a clear final answer.
        "TODO: writer/synthesiser prompt"
    ),
}


def run_worker(subtask: Subtask) -> str:
    """Run a single worker agent for the given subtask."""
    provider = get_provider()
    system_prompt = WORKER_PROMPTS.get(subtask.worker, WORKER_PROMPTS["researcher"])

    # TODO 4: Call provider.chat() with:
    #   - system_prompt as a system message
    #   - subtask.instruction as the user message
    #   Return result.text.
    #   Log: f"[Worker:{subtask.worker}] {subtask.instruction[:60]}..."

    print(f"\n[Worker:{subtask.worker}] {subtask.instruction[:60]}...")
    raise NotImplementedError("TODO: implement run_worker")


# ---------------------------------------------------------------------------
# Synthesiser
# ---------------------------------------------------------------------------

def run_synthesiser(
    original_question: str,
    results: list[tuple[Subtask, str]],
) -> str:
    """Combine all worker results into a final answer using the writer worker."""
    # TODO 5: Build a user message that contains:
    #           - The original question
    #           - Each subtask instruction + its result, labelled clearly
    #         Create a synthetic Subtask(id="synthesis", worker="writer", instruction=...)
    #         and pass it to run_worker().

    print("\n[Synthesiser] Combining results...")
    raise NotImplementedError("TODO: implement run_synthesiser")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_multi_agent(question: str) -> str:
    """Full pipeline: planner -> workers -> synthesiser."""
    print("=" * 60)
    print(f"Question: {question}")
    print("=" * 60)

    # TODO 6: Wire the pipeline:
    #   a) subtasks = run_planner(question)
    #   b) Print the plan.
    #   c) Run non-writer subtasks through run_worker(). Collect (subtask, result) pairs.
    #      For extra speed, use concurrent.futures.ThreadPoolExecutor to run workers in parallel.
    #   d) Call run_synthesiser(question, results) for the final answer.
    #   e) Return the final answer.

    raise NotImplementedError("TODO: implement run_multi_agent")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    question = (
        "Explain what the Eiffel Tower is, how tall it is, and what its height "
        "is in feet. Then write a one-sentence fun fact about it."
    )
    answer = run_multi_agent(question)
    print("\n" + "=" * 60)
    print("Final Answer:\n", answer)

    # TODO 7 (stretch): Add a "critic" worker.
    #   After the writer produces a draft, pass it to the critic for improvement
    #   suggestions, then back to the writer for a revision. This is the
    #   "reflection" or "critique-revise" pattern used in production agents.


if __name__ == "__main__":
    main()
