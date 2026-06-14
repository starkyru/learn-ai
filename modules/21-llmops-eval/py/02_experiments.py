"""
Task 2 — Experiments  🟡

What this teaches:
  - Systematic prompt/model experimentation is the core LLMOps workflow.
    You shouldn't tweak prompts and *hope* things improve — you measure.
  - Every run is stored with metadata (model, prompt version, timestamp)
    so you can replay, diff, and compare across time.
  - A simple winner-selection function turns numeric scores into decisions.

How to run:
  # Default experiment (uses LLM_PROVIDER env var):
  uv run python modules/21-llmops-eval/py/02_experiments.py

  # Override model and prompt version via args:
  uv run python modules/21-llmops-eval/py/02_experiments.py \\
      --model gpt-4o-mini --prompt-version v2

  # Compare two existing run files:
  uv run python modules/21-llmops-eval/py/02_experiments.py \\
      --compare results/run_A.json results/run_B.json
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "data"
RESULTS_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "results"
EVAL_SET_PATH = DATA_DIR / "eval_set_v1.json"

# ---------------------------------------------------------------------------
# Prompt variants (the experiment independent variable)
# ---------------------------------------------------------------------------

PROMPT_VARIANTS: dict[str, str] = {
    "v1": (
        "You are a helpful assistant. Answer the user's question using ONLY "
        "the provided context. If the context does not contain the answer, "
        "say 'I don't know'.\n\nContext:\n{context}"
    ),
    "v2": (
        "You are a precise technical assistant. Answer in one or two sentences. "
        "Use ONLY the following context — do not add outside knowledge.\n\n"
        "Context:\n{context}\n\n"
        "If the answer is not in the context, reply exactly: 'Not found in context.'"
    ),
    "v3": (
        "Answer the question based solely on the context below. "
        "Be concise. Quote the relevant part of the context in your answer.\n\n"
        "Context:\n{context}"
    ),
}


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class RunMetadata:
    run_id: str
    provider: str
    model: str
    prompt_version: str
    timestamp: str
    eval_version: str = "1.0.0"


@dataclass
class ExperimentRun:
    metadata: RunMetadata
    scores: list[float] = field(default_factory=list)
    avg_score: float = 0.0
    pass_rate: float = 0.0
    avg_latency_ms: float = 0.0
    raw_cases: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1 — Load eval set (reuse from task 1)
# ---------------------------------------------------------------------------

def load_eval_set(path: Path) -> list[dict[str, Any]]:
    """Load cases from the versioned eval JSON.

    TODO 1: Open and parse the JSON; return the 'cases' list.
    """
    raise NotImplementedError("TODO: implement load_eval_set")


# ---------------------------------------------------------------------------
# Step 2 — Single-case runner
# ---------------------------------------------------------------------------

def run_one(
    case: dict[str, Any],
    system_prompt: str,
    provider: Any,
) -> tuple[str, float]:
    """Run a single eval case and return (answer, latency_ms).

    TODO 2a: Format system_prompt by substituting {context} with case['context'].
    TODO 2b: Call provider.chat([system_msg, user_msg], options=ChatOptions(temperature=0)).
    TODO 2c: Time the call.
    Return (answer_text, latency_ms).
    """
    raise NotImplementedError("TODO: implement run_one")


# ---------------------------------------------------------------------------
# Step 3 — Quick scorer (contains-based, no LLM judge to keep it fast)
# ---------------------------------------------------------------------------

def quick_score(output: str, case: dict[str, Any]) -> float:
    """Return 1.0 if the reference answer's key tokens appear in output, else 0.0.

    TODO 3: Split case['reference_answer'] on whitespace.
    Pass if any token (len > 3) appears in output.lower().
    This is the fast grader; task 1 adds the LLM-judge layer.
    """
    raise NotImplementedError("TODO: implement quick_score")


# ---------------------------------------------------------------------------
# Step 4 — Run an experiment (one prompt x model combination)
# ---------------------------------------------------------------------------

def run_experiment(
    prompt_version: str,
    model_override: str | None,
    provider: Any,
    cases: list[dict[str, Any]],
) -> ExperimentRun:
    """Run the full eval set for one prompt+model variant.

    TODO 4a: Build RunMetadata (generate a short run_id, e.g. first 8 chars of timestamp).
    TODO 4b: Retrieve the system prompt from PROMPT_VARIANTS[prompt_version].
    TODO 4c: For each case, call run_one() and quick_score().
    TODO 4d: Compute avg_score, pass_rate (score >= 0.5), avg_latency_ms.
    TODO 4e: Append each case's output + score to raw_cases.
    Return ExperimentRun.
    """
    raise NotImplementedError("TODO: implement run_experiment")


# ---------------------------------------------------------------------------
# Step 5 — Persist run
# ---------------------------------------------------------------------------

def save_run(run: ExperimentRun) -> Path:
    """Save an ExperimentRun to RESULTS_DIR as JSON.

    TODO 5a: Create RESULTS_DIR.
    TODO 5b: Filename: run_{timestamp}_{prompt_version}_{model}.json
             (sanitise special chars with str.replace).
    TODO 5c: Serialise via asdict() and json.dump.
    Return the path.
    """
    raise NotImplementedError("TODO: implement save_run")


# ---------------------------------------------------------------------------
# Step 6 — Compare runs and pick a winner
# ---------------------------------------------------------------------------

def compare_runs(run_a: ExperimentRun, run_b: ExperimentRun) -> None:
    """Print a side-by-side comparison and declare a winner.

    TODO 6a: Print a table: run_id, model, prompt_version, avg_score, pass_rate, avg_latency_ms.
    TODO 6b: Winner = higher avg_score (ties: lower latency).
    TODO 6c: Print: "Winner: <run_id> (avg_score=<n>, pass_rate=<n>)".
    """
    raise NotImplementedError("TODO: implement compare_runs")


def load_run_from_file(path: Path) -> ExperimentRun:
    """Load a previously saved ExperimentRun from JSON.

    TODO: Parse the JSON and reconstruct the ExperimentRun + RunMetadata.
    """
    raise NotImplementedError("TODO: implement load_run_from_file")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLMOps experiment runner")
    parser.add_argument("--model", default=None, help="Override chat model id")
    parser.add_argument("--prompt-version", default="v1", choices=list(PROMPT_VARIANTS),
                        help="Which prompt variant to run")
    parser.add_argument("--compare", nargs=2, metavar="RUN_FILE",
                        help="Compare two saved run JSON files instead of running")
    args = parser.parse_args()

    if args.compare:
        # Compare two existing runs
        run_a = load_run_from_file(Path(args.compare[0]))
        run_b = load_run_from_file(Path(args.compare[1]))
        compare_runs(run_a, run_b)
        return

    provider = get_provider()
    print(f"Provider: {provider.name}  model: {provider.chat_model}")
    print(f"Prompt version: {args.prompt_version}\n")

    cases = load_eval_set(EVAL_SET_PATH)
    run = run_experiment(args.prompt_version, args.model, provider, cases)
    path = save_run(run)

    print(f"\nRun: {run.metadata.run_id}")
    print(f"Avg score:  {run.avg_score:.2f}")
    print(f"Pass rate:  {run.pass_rate:.1%}")
    print(f"Avg latency: {run.avg_latency_ms:.0f} ms")
    print(f"\nSaved to: {path}")
    print("\nTip: run with different --prompt-version or --model, then compare:")
    print(f"  python 02_experiments.py --compare {path} <other_run>.json")


if __name__ == "__main__":
    main()
