"""agent_gate.py — deterministic agent-safety release gate (Module 21b, Task 4).

Exits NONZERO when any candidate trajectory violates policy (unauthorised tool,
side effect without approval, exceeded steps, non-idempotent duplicate) or the
task-success rate is below the floor, AND when the committed agent report drifts;
exits 0 on a clean candidate. This is the CI agent-safety gate. Offline,
deterministic. The load-bearing rule: an unsafe trajectory fails EVEN IF its
final answer is correct.

Run it:
    uv run python modules/21b-evaluation-reliability/py/agent_gate.py
    uv run python modules/21b-evaluation-reliability/py/agent_gate.py --policy <path> --out <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import agent_eval
from benchmark import FIXTURES_DIR, serialize_canonical

GOLDEN_DIR = FIXTURES_DIR / "golden"


def load_policy() -> dict[str, Any]:
    with (FIXTURES_DIR / "agent_gate_policy.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_gate_policy(policy: Mapping[str, Any]) -> None:
    """Reject a malformed gate policy before any evaluation."""
    known = set(agent_eval.scenario_ids())
    candidates = policy.get("candidate_scenarios")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidate_scenarios must be a non-empty list")
    if len(candidates) != len(set(candidates)):
        raise ValueError("candidate_scenarios has duplicates")
    unknown = [c for c in candidates if c not in known]
    if unknown:
        raise ValueError(f"candidate_scenarios references unknown scenarios: {unknown}")
    floor = policy.get("task_success_floor")
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("task_success_floor must be a number")
    if not math.isfinite(floor) or not (0.0 <= floor <= 1.0):
        raise ValueError("task_success_floor must be in [0, 1]")


@dataclass
class GateOutcome:
    ok: bool
    violations: list[str]
    report: dict[str, Any]


def gate_evidence(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Per-candidate safety metrics (reported separately) + aggregates."""
    scenarios = agent_eval.load_scenarios()["scenarios"]
    candidates = sorted(policy["candidate_scenarios"])
    per_scenario: dict[str, Any] = {}
    for sid in candidates:
        result = agent_eval.evaluate_trajectory(sid, scenarios[sid])
        per_scenario[sid] = {
            "task_success": result["task_success"],
            "policy_compliant": result["policy_compliant"],
            "tool_argument_accuracy": result["tool_argument_accuracy"],
            "step_count": result["step_count"],
            "latency": result["latency"],
            "cost": result["cost"],
            "violation_types": sorted({v["type"] for v in result["violations"]}),
        }
    n = len(candidates) or 1
    metrics = {
        "task_success_rate": sum(per_scenario[s]["task_success"] for s in candidates) / n,
        "policy_compliance_rate": sum(per_scenario[s]["policy_compliant"] for s in candidates) / n,
        "total_cost": sum(per_scenario[s]["cost"] for s in candidates),
        "total_latency": sum(per_scenario[s]["latency"] for s in candidates),
        "total_steps": sum(per_scenario[s]["step_count"] for s in candidates),
    }
    return {"candidates": per_scenario, "metrics": metrics}


def evaluate_gate(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> list[str]:
    """Gate violations from the evidence (no drift). Pure — the unit for tests.

    The policy-compliance check is UNCONDITIONAL: a policy-violating candidate
    ALWAYS fails the gate (it cannot be disabled by policy)."""
    violations: list[str] = []
    candidates = sorted(policy["candidate_scenarios"])
    for sid in candidates:
        entry = evidence["candidates"][sid]
        if not entry["policy_compliant"]:
            violations.append(f"{sid}: policy violation {entry['violation_types']}")
    if evidence["metrics"]["task_success_rate"] < policy["task_success_floor"]:
        violations.append(
            f"task_success_rate {evidence['metrics']['task_success_rate']:.4f} "
            f"< floor {policy['task_success_floor']}"
        )
    return violations


def _check_drift() -> tuple[dict[str, bool], list[str]]:
    """Mandatory golden-drift: the committed agent report must be reproducible."""
    golden = GOLDEN_DIR / "agent_report.golden"
    drifted = serialize_canonical(agent_eval.build_agent_report()) != golden.read_text(
        encoding="utf-8"
    )
    violations = ["agent report drifted from agent_report.golden"] if drifted else []
    return {"checked": True, "drifted": drifted}, violations


def build_gate_report(policy: Mapping[str, Any]) -> GateOutcome:
    validate_gate_policy(policy)
    evidence = gate_evidence(policy)
    violations = evaluate_gate(policy, evidence)
    golden_drift, drift_violations = _check_drift()
    violations += drift_violations
    report = {
        **evidence,
        "golden_drift": golden_drift,
        "gate": {"ok": not violations, "violations": violations},
    }
    return GateOutcome(ok=not violations, violations=violations, report=report)


def run_gate(policy: Mapping[str, Any], out_dir: Path | None = None) -> GateOutcome:
    outcome = build_gate_report(policy)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "agent_gate_report.json").write_text(
            serialize_canonical(outcome.report), encoding="utf-8"
        )
    return outcome


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=None, help="agent gate policy JSON")
    parser.add_argument("--out", type=Path, default=None, help="output dir for the gate report")
    args = parser.parse_args()

    if args.policy is not None:
        with args.policy.open(encoding="utf-8") as handle:
            policy = json.load(handle)
    else:
        policy = load_policy()

    out_dir = args.out or Path(tempfile.mkdtemp(prefix="m21b-agent-gate-"))
    try:
        outcome = run_gate(policy, out_dir)
    except ValueError as error:
        print(f"agent gate: FAIL  (rejected: {error})")
        sys.exit(1)

    print(f"agent gate: {'PASS' if outcome.ok else 'FAIL'}")
    for violation in outcome.violations:
        print(f"  - violation: {violation}")
    print(f"agent_gate_report written to: {out_dir / 'agent_gate_report.json'}")
    sys.exit(0 if outcome.ok else 1)


if __name__ == "__main__":
    main()
