"""
Task 3 — Regression gate in CI  🟡

What this teaches:
  - A CI gate fails the build (non-zero exit) when a key metric drops below a
    threshold, preventing regressions from reaching production.
  - The same script works both as a standalone CLI check AND as a pre-push hook
    (see .github/workflows/eval-gate.yml and the husky note in the README).
  - Thresholds belong in config, not hard-coded — so different teams/models
    can set different bars.

How to run:
  # Run against a pre-built results file:
  uv run python modules/21-llmops-eval/py/03_regression_gate.py \\
      --results modules/21-llmops-eval/results/<run>.json \\
      --metric avg_score --threshold 0.6

  # Run a fresh eval then gate:
  uv run python modules/21-llmops-eval/py/03_regression_gate.py \\
      --run-fresh --metric faithfulness --threshold 0.7

  # Non-zero exit if threshold is not met (for CI):
  # The script exits with code 1 on failure, 0 on pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "data"
RESULTS_DIR = REPO_ROOT / "modules" / "21-llmops-eval" / "results"
EVAL_SET_PATH = DATA_DIR / "eval_set_v1.json"

# Default thresholds — override per metric via --threshold
DEFAULT_THRESHOLDS: dict[str, float] = {
    "avg_score": 0.60,
    "pass_rate": 0.60,
    "faithfulness": 0.70,   # from LLM-judge; requires --run-fresh
}


# ---------------------------------------------------------------------------
# Step 1 — Load a results file (from task 1 or 2)
# ---------------------------------------------------------------------------

def load_results(path: Path) -> dict[str, Any]:
    """Parse a JSON results file produced by task 1 or 2.

    TODO 1: Open path, parse JSON, return the dict.
    Raise FileNotFoundError with a helpful message if the path doesn't exist.
    """
    raise NotImplementedError("TODO: implement load_results")


# ---------------------------------------------------------------------------
# Step 2 — Extract the metric value
# ---------------------------------------------------------------------------

def extract_metric(results: dict[str, Any], metric: str) -> float:
    """Pull the numeric value of `metric` from the results dict.

    The results structure has a 'summary' key with: avg_score, pass_rate,
    avg_latency_ms. It may also have per-case grader scores.

    TODO 2a: Try results['summary'][metric].
    TODO 2b: If not there, check for a per-case 'faithfulness' average:
             iterate results['cases'], find grader_results with grader=='llm_judge',
             average their scores, and use that.
    TODO 2c: Raise ValueError if the metric cannot be found.
    Return the float value.
    """
    raise NotImplementedError("TODO: implement extract_metric")


# ---------------------------------------------------------------------------
# Step 3 — Run a fresh eval (optional, reuses task 1 logic)
# ---------------------------------------------------------------------------

def run_fresh_eval(provider: Any) -> dict[str, Any]:
    """Run a quick eval and return a results-dict compatible with extract_metric.

    This is a stripped version of task 1's runner (no file write needed —
    the gate only cares about the numbers).

    TODO 3a: Load eval set from EVAL_SET_PATH.
    TODO 3b: For each case, call provider.chat() with a system prompt that
             includes the context.
    TODO 3c: Score faithfulness with an LLM-judge call (score 0–10, /10).
    TODO 3d: Return {'summary': {'avg_score': ..., 'pass_rate': ...,
                                  'faithfulness': ...},
                      'cases': [...]}.
    Tip: faithfulness = avg of LLM-judge scores across all cases.
    """
    raise NotImplementedError("TODO: implement run_fresh_eval")


# ---------------------------------------------------------------------------
# Step 4 — Gate check
# ---------------------------------------------------------------------------

def check_gate(metric_value: float, threshold: float, metric: str) -> bool:
    """Return True if metric_value >= threshold, else print failure and return False.

    TODO 4: Print one clear line tagged PASS or FAIL that names the metric, its
            value, the comparison, and the threshold, so CI logs are scannable.
    Return True on pass, False on fail.
    """
    raise NotImplementedError("TODO: implement check_gate")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regression gate — exits non-zero if a metric drops below threshold."
    )
    parser.add_argument(
        "--results", type=Path, default=None,
        help="Path to a results JSON from task 1/2. Mutually exclusive with --run-fresh.",
    )
    parser.add_argument(
        "--run-fresh", action="store_true",
        help="Run a fresh eval before checking the gate.",
    )
    parser.add_argument(
        "--metric", default="avg_score",
        choices=list(DEFAULT_THRESHOLDS) + ["faithfulness"],
        help="Which metric to gate on.",
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help="Override the default threshold for this metric.",
    )
    args = parser.parse_args()

    threshold = args.threshold if args.threshold is not None else DEFAULT_THRESHOLDS.get(args.metric, 0.6)

    if args.run_fresh:
        provider = get_provider()
        print(f"Running fresh eval with {provider.name}/{provider.chat_model}...")
        results = run_fresh_eval(provider)
    elif args.results:
        results = load_results(args.results)
    else:
        parser.error("Provide --results <path> or --run-fresh.")

    value = extract_metric(results, args.metric)
    passed = check_gate(value, threshold, args.metric)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
