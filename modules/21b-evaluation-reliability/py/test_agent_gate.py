"""test_agent_gate.py — the agent-safety release gate (exit code is the crux)."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import agent_gate as ag
import pytest
from benchmark import FIXTURES_DIR, serialize_canonical

GATE_SCRIPT = Path(__file__).resolve().parent / "agent_gate.py"


def _policy() -> dict:
    return copy.deepcopy(ag.load_policy())


@pytest.fixture
def track_restore() -> Iterator[Callable[[Path], None]]:
    saved: dict[Path, str] = {}

    def track(path: Path) -> None:
        saved[path] = path.read_text(encoding="utf-8")

    try:
        yield track
    finally:
        for path, text in saved.items():
            path.write_text(text, encoding="utf-8")


def test_gate_passes_on_clean_candidates() -> None:
    outcome = ag.run_gate(ag.load_policy())
    assert outcome.ok is True
    assert outcome.violations == []


def test_gate_evidence_byte_matches_golden() -> None:
    evidence = ag.gate_evidence(ag.load_policy())
    golden = (FIXTURES_DIR / "golden" / "agent_gate_report.golden").read_text(encoding="utf-8")
    assert serialize_canonical(evidence) == golden


def test_gate_fails_on_unauthorised_side_effect_despite_correct_answer() -> None:
    # CRUX: the candidate's answer is correct (task_success_rate 1.0) but it sent
    # an unauthorised email -> the gate FAILS.
    p = _policy()
    p["candidate_scenarios"] = ["unauthorised_side_effect"]
    evidence = ag.gate_evidence(p)
    violations = ag.evaluate_gate(p, evidence)
    assert evidence["metrics"]["task_success_rate"] == 1.0  # answer is correct
    assert violations  # ...but the gate still fails
    assert any("unauthorised_tool" in v for v in violations)


def test_gate_fails_on_missing_approval() -> None:
    p = _policy()
    p["candidate_scenarios"] = ["missing_approval"]
    assert ag.evaluate_gate(p, ag.gate_evidence(p))


def test_gate_fails_on_exceeded_steps() -> None:
    p = _policy()
    p["candidate_scenarios"] = ["exceeds_max_steps"]
    assert ag.evaluate_gate(p, ag.gate_evidence(p))


def test_gate_fails_on_non_idempotent_duplicate() -> None:
    p = _policy()
    p["candidate_scenarios"] = ["non_idempotent_duplicate"]
    assert ag.evaluate_gate(p, ag.gate_evidence(p))


def test_gate_rejects_unknown_scenario() -> None:
    p = _policy()
    p["candidate_scenarios"] = ["does_not_exist"]
    with pytest.raises(ValueError):
        ag.run_gate(p)


def test_gate_rejects_out_of_range_floor() -> None:
    p = _policy()
    p["task_success_floor"] = 1.5
    with pytest.raises(ValueError):
        ag.run_gate(p)


def test_gate_fails_on_agent_report_drift(track_restore: Callable[[Path], None]) -> None:
    golden = FIXTURES_DIR / "golden" / "agent_report.golden"
    track_restore(golden)
    golden.write_text(golden.read_text(encoding="utf-8") + "  \n", encoding="utf-8")
    outcome = ag.run_gate(ag.load_policy())
    assert outcome.ok is False
    assert any("drifted" in v for v in outcome.violations)


def test_gate_cli_exit_zero_on_pass(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "agent_gate_report.json").exists()


def test_gate_cli_exit_nonzero_on_unsafe_candidate(tmp_path: Path) -> None:
    p = _policy()
    p["candidate_scenarios"] = ["unauthorised_side_effect"]
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(p), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--policy", str(policy_path), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
