"""Tests for the enforced, downgrade-proof eval-gate activation marker.

Imports the real ``eval_gate_status`` functions and drives ``evaluate_gate`` with
synthetic current/base gate records + a ``tmp_path`` root. The regressions that
matter: a gate marked ACTIVE whose entrypoint is missing must FAIL, and a PR that
downgrades a base-active gate (turns it off OR deletes it) must FAIL — not skip
green.
"""

from __future__ import annotations

import json
from pathlib import Path

import eval_gate_status as egs

_REL = "modules/21b-evaluation-reliability/py/gate.py"


def _gate(active: bool, rel: str = _REL) -> dict:
    return {"id": "21b-release-gate", "active": active, "path": rel}


def _make_gate_file(root: Path, rel: str = _REL) -> None:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('gate')\n", encoding="utf-8")


def _write_marker(root: Path, gates: list[dict]) -> Path:
    marker = root / "ci_gates.json"
    marker.write_text(json.dumps({"gates": gates}), encoding="utf-8")
    return marker


# --- forward enforcement (no base) -----------------------------------------


def test_inactive_and_absent_skips(tmp_path: Path) -> None:
    should_run, error = egs.evaluate_gate(_gate(active=False), {}, tmp_path)
    assert should_run is False
    assert error is None


def test_active_but_missing_fails(tmp_path: Path) -> None:
    should_run, error = egs.evaluate_gate(_gate(active=True), {}, tmp_path)
    assert should_run is False
    assert error is not None
    assert "active but missing" in error


def test_present_runs_regardless_of_flag(tmp_path: Path) -> None:
    _make_gate_file(tmp_path)
    for active in (True, False):
        should_run, error = egs.evaluate_gate(_gate(active=active), {}, tmp_path)
        assert should_run is True
        assert error is None


# --- downgrade guard (vs protected base) -----------------------------------


def test_downgrade_active_to_inactive_fails(tmp_path: Path) -> None:
    # base marked the gate active; the PR turns it off → must FAIL.
    should_run, error = egs.evaluate_gate(_gate(active=False), _gate(active=True), tmp_path)
    assert should_run is False
    assert error is not None
    assert "downgrade" in error


def test_removing_a_base_active_gate_fails(tmp_path: Path) -> None:
    # base active + present, PR keeps active:true but deletes the entrypoint.
    should_run, error = egs.evaluate_gate(_gate(active=True), _gate(active=True), tmp_path)
    assert should_run is False
    assert "removal" in error


def test_base_active_still_present_runs(tmp_path: Path) -> None:
    _make_gate_file(tmp_path)
    should_run, error = egs.evaluate_gate(_gate(active=True), _gate(active=True), tmp_path)
    assert should_run is True
    assert error is None


def test_inactive_base_allows_absence(tmp_path: Path) -> None:
    # base did not have the gate active → the current tree may legitimately skip.
    should_run, error = egs.evaluate_gate(_gate(active=False), {}, tmp_path)
    assert should_run is False
    assert error is None


# --- loaders ----------------------------------------------------------------


def test_load_gate_reads_marker(tmp_path: Path) -> None:
    marker = _write_marker(tmp_path, [_gate(active=False)])
    gate = egs.load_gate("21b-release-gate", marker)
    assert gate["path"] == _REL
    assert gate["active"] is False


def test_load_gate_from_missing_ref_is_empty_without_require() -> None:
    # Local/dev (no --require-base): an unresolvable ref → {} (inactive base).
    assert egs.load_gate_from_ref("21b-release-gate", "does-not-exist-ref-xyz") == {}


def test_load_gate_from_missing_ref_fails_closed_with_require() -> None:
    # PR path (--require-base): an unresolvable base ref (fetch failure) must FAIL,
    # never be treated as an inactive base.
    try:
        egs.load_gate_from_ref("21b-release-gate", "no-such-ref-xyz", require=True)
    except egs.BaseRefError as exc:
        assert "not available" in str(exc)
    else:
        raise AssertionError("expected BaseRefError for an unreadable base ref")


def test_main_require_base_with_bad_ref_exits_nonzero() -> None:
    # End-to-end: detect with --require-base and an unfetchable base → exit 1.
    rc = egs.main(["21b-release-gate", "--base-ref", "no-such-ref-xyz", "--require-base"])
    assert rc == 1


def test_unlisted_gate_is_empty() -> None:
    assert egs._gate_from_data({"gates": []}, "nope") == {}


def test_real_marker_lists_the_21b_gate() -> None:
    gate = egs.load_gate("21b-release-gate")
    assert gate.get("path") == _REL


def test_main_on_real_repo_is_green_while_inactive() -> None:
    # 21b gate is inactive + absent on this branch → skip, exit 0 (never red).
    assert egs.main(["21b-release-gate"]) == 0
