"""
Task 3 — Self-refine / reflection 🟡

What this teaches:
  - Draft → critique → revise is a three-turn loop that mimics how a human
    reviews their own work. Each iteration uses the model to judge AND improve
    its own previous output.
  - Even a single round of self-refinement frequently improves factual accuracy,
    completeness, and clarity on open-ended tasks.
  - Multiple iterations converge quickly: the marginal gain from iteration 3 is
    usually not worth iteration 2's cost. Measure, don't assume.

How to run:
  uv run python modules/15-reasoning-test-time-compute/py/03_self_refine.py
"""

from __future__ import annotations

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Tasks to refine — open-ended so there is real room for improvement.
# ---------------------------------------------------------------------------
TASKS = [
    {
        "id": "explain",
        "prompt": (
            "Explain how a transformer attention mechanism works to a software "
            "engineer who has not studied machine learning. Use an analogy."
        ),
    },
    {
        "id": "plan",
        "prompt": (
            "Write a brief 5-step plan for launching a personal blog in 2025, "
            "including tools, audience strategy, and monetisation."
        ),
    },
]

MAX_ITERATIONS = 2  # number of critique-revise cycles

CRITIQUE_PROMPT = (
    "You are a critical reviewer. Read the task and the draft answer below.\n"
    "List 3–5 specific issues, gaps, or inaccuracies in the draft. "
    "Be concrete — do not say 'it could be clearer'; say exactly what is unclear and why.\n"
    "Format your response as a numbered list."
)

REVISE_PROMPT = (
    "You are a skilled writer. You will receive a task, a draft answer, and a critique.\n"
    "Produce a revised answer that directly addresses every point in the critique. "
    "Your revision should be complete and self-contained — do not reference the critique in your output."
)


# ---------------------------------------------------------------------------
# TODO 1: Implement draft(task_prompt).
#         Generate an initial answer to the task. Use temperature=0.7 so the
#         output is natural but not overly conservative.
#         Return the text of the draft.
# ---------------------------------------------------------------------------
def draft(task_prompt: str) -> str:
    # Get the default provider, make one chat call with a list[ChatMessage]
    # holding just the task_prompt as a "user" message, using
    # ChatOptions(temperature=0.7), and return the reply text.
    raise NotImplementedError("TODO: implement draft()")


# ---------------------------------------------------------------------------
# TODO 2: Implement critique(task_prompt, draft_text).
#         Send a message with the critique system prompt + the task + the draft.
#         Return the critique text.
#         Temperature=0 keeps the critique factual and repeatable.
# ---------------------------------------------------------------------------
def critique(task_prompt: str, draft_text: str) -> str:
    # Build a list[ChatMessage]: the CRITIQUE_PROMPT constant as the "system"
    # message, and a "user" message that presents both the task and the draft
    # answer (label each so the model can tell them apart). Call llm.chat with
    # ChatOptions(temperature=0) and return the reply text.
    raise NotImplementedError("TODO: implement critique()")


# ---------------------------------------------------------------------------
# TODO 3: Implement revise(task_prompt, draft_text, critique_text).
#         Send a message with the revise system prompt + task + draft + critique.
#         Return the revised text.
# ---------------------------------------------------------------------------
def revise(task_prompt: str, draft_text: str, critique_text: str) -> str:
    # Build a list[ChatMessage]: the REVISE_PROMPT constant as the "system"
    # message, and a "user" message that supplies all three pieces the reviser
    # needs — the task, the draft answer, and the critique (label each). Call
    # llm.chat with a low-but-nonzero temperature (e.g. ChatOptions(
    # temperature=0.3)) and return the reply text.
    raise NotImplementedError("TODO: implement revise()")


# ---------------------------------------------------------------------------
# TODO 4: Implement compare(original, final).
#         A simple heuristic comparison: length change, unique words added,
#         etc. Return a dict with at least {"length_delta": int, "changed": bool}.
#         This is a stub — replace with an LLM-as-judge call if you like.
# ---------------------------------------------------------------------------
def compare(original: str, final: str) -> dict:
    # TODO: implement
    length_delta = len(final) - len(original)
    original_words = set(original.lower().split())
    final_words = set(final.lower().split())
    new_words = final_words - original_words
    return {
        "length_delta": length_delta,
        "new_unique_words": len(new_words),
        "changed": original.strip() != final.strip(),
    }


def divider(label: str) -> None:
    print(f"\n{'='*10} {label} {'='*10}")


def main() -> None:
    print("=== Task 3: Self-Refine / Reflection ===\n")

    for task in TASKS:
        print(f"\nTask [{task['id']}]: {task['prompt']}\n")

        # -------------------------------------------------------------------------
        # TODO 5: Run the draft → critique → revise loop.
        #         1. Generate initial draft.
        #         2. For each iteration: critique the current draft, revise it.
        #         3. Print each step so the reader can see the improvement.
        # -------------------------------------------------------------------------

        try:
            # Step 1: initial draft
            divider("DRAFT")
            current = draft(task["prompt"])
            original = current
            print(current)

            # Iteration loop
            for iteration in range(1, MAX_ITERATIONS + 1):
                divider(f"CRITIQUE (iteration {iteration})")
                crit = critique(task["prompt"], current)
                print(crit)

                divider(f"REVISION (iteration {iteration})")
                current = revise(task["prompt"], current, crit)
                print(current)

            # -------------------------------------------------------------------------
            # TODO 6: Print a comparison between the original draft and final revision.
            # -------------------------------------------------------------------------
            divider("COMPARISON")
            stats = compare(original, current)
            print(f"  Length change     : {stats['length_delta']:+d} chars")
            print(f"  New unique words  : {stats['new_unique_words']}")
            print(f"  Changed at all?   : {stats['changed']}")

        except NotImplementedError as e:
            print(f"  {e}")

        print()

    print(
        "Observation: self-refinement tends to add specificity and fix factual gaps.\n"
        "Two iterations usually capture most of the gain."
    )


if __name__ == "__main__":
    main()
