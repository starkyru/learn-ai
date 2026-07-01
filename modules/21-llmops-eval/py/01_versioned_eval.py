"""
Task 1 — Versioned eval set + graders  🟢

What this teaches:
  - Eval datasets should be versioned (like code) so you can detect regressions
    across prompt or model changes. Storing them as JSON/YAML files makes them
    diffable in git.
  - Graders form a spectrum: cheap/fast (exact match, contains) → expensive/smart
    (LLM-as-judge). Combine them: exact checks where possible, LLM for nuance.
  - A runner writes results to a timestamped file so every run is reproducible.

How to run:
  uv run python modules/21-llmops-eval/py/01_versioned_eval.py
  # Results land in: modules/21-llmops-eval/results/
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "data"
RESULTS_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "results"

EVAL_SET_PATH = DATA_DIR / "eval_set_v1.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class EvalCase:
    id: str
    question: str
    context: str
    reference_answer: str
    graders: list[str]
    rubric: str


@dataclass
class GraderResult:
    grader: str
    score: float          # 0.0–1.0
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    case_id: str
    question: str
    system_output: str
    latency_ms: float
    grader_results: list[GraderResult] = field(default_factory=list)
    overall_score: float = 0.0


# ---------------------------------------------------------------------------
# Step 1 — Load the versioned eval set
# ---------------------------------------------------------------------------

def load_eval_set(path: Path) -> tuple[str, list[EvalCase]]:
    """Read eval_set_v1.json and return (version, cases).

    TODO 1a: Open `path`, parse JSON.
    TODO 1b: Extract `version` (str) and `cases` (list of dicts).
    TODO 1c: Convert each dict to an EvalCase dataclass.
    Return (version, list[EvalCase]).
    """
    raise NotImplementedError("TODO: implement load_eval_set")


# ---------------------------------------------------------------------------
# Step 2 — System under test
# ---------------------------------------------------------------------------

def run_system(case: EvalCase, provider: Any) -> tuple[str, float]:
    """Call the LLM with a RAG-style prompt and return (answer, latency_ms).

    The 'system under test' is simple: stuff the context into the system
    prompt and answer the question.

    TODO 2a: Build a system prompt that instructs the model to answer ONLY
             from the provided context.
    TODO 2b: Call provider.chat() with [system_msg, user_question].
    TODO 2c: Time the call; compute latency_ms.
    Return (result.text, latency_ms).
    """
    raise NotImplementedError("TODO: implement run_system")


# ---------------------------------------------------------------------------
# Step 3 — Graders
# ---------------------------------------------------------------------------

def grade_exact(output: str, case: EvalCase) -> GraderResult:
    """Exact-match grader: passes if reference_answer appears verbatim in output.

    TODO 3a: Decide whether case.reference_answer appears inside output, ignoring
             letter case (normalise both sides before comparing).
    Return a GraderResult whose score is 1.0 when it matches and 0.0 otherwise,
    with passed set to match.
    """
    raise NotImplementedError("TODO: implement grade_exact")


def grade_contains(output: str, case: EvalCase) -> GraderResult:
    """Contains grader: passes if any key term from reference_answer appears.

    TODO 3b: Split case.reference_answer on whitespace.
             Pass if at least one token (len > 3) appears in output (case-insensitive).
    Return a GraderResult.
    """
    raise NotImplementedError("TODO: implement grade_contains")


def grade_llm_judge(output: str, case: EvalCase, provider: Any) -> GraderResult:
    """LLM-as-judge grader: ask a second LLM to score 0–10.

    TODO 3c: Build a `list[ChatMessage]` for a judge that sees the original
             question, the rubric (case.rubric), and the system output to
             evaluate, and is told to reply with ONLY a JSON object carrying an
             integer score field (0–10) and a short reason field.
    TODO 3d: Call provider.chat() with temperature=0 (deterministic grading).
    TODO 3e: Parse the JSON, normalise the score into 0–1 (divide by the 0–10
             range), and treat a score of 7+ as a pass.
    Handle JSON parse errors gracefully (fall back to score=0, passed=False).
    Return a GraderResult.
    """
    raise NotImplementedError("TODO: implement grade_llm_judge")


def run_graders(
    output: str,
    case: EvalCase,
    provider: Any,
) -> list[GraderResult]:
    """Run each grader listed in case.graders and return results."""
    results: list[GraderResult] = []
    for grader in case.graders:
        if grader == "exact":
            results.append(grade_exact(output, case))
        elif grader == "contains":
            results.append(grade_contains(output, case))
        elif grader == "llm_judge":
            results.append(grade_llm_judge(output, case, provider))
    return results


# ---------------------------------------------------------------------------
# Step 4 — Runner
# ---------------------------------------------------------------------------

def run_eval(eval_set_path: Path, provider: Any) -> list[CaseResult]:
    """Load the eval set, run every case, collect results.

    TODO 4a: Call load_eval_set().
    TODO 4b: For each EvalCase, call run_system() then run_graders().
    TODO 4c: Compute overall_score as average of grader scores.
    TODO 4d: Print progress: case id, latency, grader scores.
    Return list[CaseResult].
    """
    raise NotImplementedError("TODO: implement run_eval")


# ---------------------------------------------------------------------------
# Step 5 — Results writer
# ---------------------------------------------------------------------------

def write_results(case_results: list[CaseResult], eval_version: str) -> Path:
    """Write results to a timestamped JSON file in RESULTS_DIR.

    TODO 5a: Create RESULTS_DIR if it doesn't exist.
    TODO 5b: Build a results dict with keys:
             eval_version, run_at (ISO timestamp), provider, model,
             summary (pass_rate, avg_score, avg_latency_ms),
             cases (list of CaseResult as dicts).
    TODO 5c: Write to RESULTS_DIR / f"run_{timestamp}.json".
    Return the output path.
    """
    raise NotImplementedError("TODO: implement write_results")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    provider = get_provider()
    print(f"Provider: {provider.name}  model: {provider.chat_model}\n")

    case_results = run_eval(EVAL_SET_PATH, provider)

    # Summary
    scores = [r.overall_score for r in case_results]
    avg = sum(scores) / len(scores) if scores else 0.0
    pass_rate = sum(1 for s in scores if s >= 0.7) / len(scores) if scores else 0.0
    print(f"\n=== Summary ===")
    print(f"Cases:      {len(case_results)}")
    print(f"Pass rate:  {pass_rate:.1%}")
    print(f"Avg score:  {avg:.2f}")

    out_path = write_results(case_results, "1.0.0")
    print(f"\nResults written to: {out_path}")


if __name__ == "__main__":
    main()
