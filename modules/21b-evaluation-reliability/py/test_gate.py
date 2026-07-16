"""test_gate.py — the enforceable release gate (exit-code behavior is the crux).

Includes an ADVERSARIAL false-green test per hardening finding: each proves the
gate now EXITS NONZERO where a weaker gate would have passed.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import answer_eval as ae
import gate
import pytest
from benchmark import FIXTURES_DIR, serialize_canonical

GATE_SCRIPT = Path(__file__).resolve().parent / "gate.py"


def _policy() -> dict:
    return copy.deepcopy(gate.load_policy())


def _prompt_hash(variant: str, case_id: str, answer_text: str) -> str:
    query = {c["id"]: c["query"] for c in ae.load_cases("heldout")["cases"]}[case_id]
    user = ae.make_fake_judge().build_messages(variant, case_id, query, answer_text)[1].content
    return ae.prompt_hash(user)


def _violations(policy: dict) -> list[str]:
    """Floor/config/verdict violations for a crafted policy (bypasses the policy
    binding, which is tested separately)."""
    return gate.evaluate_policy(policy, gate._release_evidence(policy))


@pytest.fixture
def track_restore() -> Iterator[Callable[[Path], None]]:
    """Return a `track(path)` that snapshots a file; all are restored on teardown."""
    saved: dict[Path, str] = {}

    def track(path: Path) -> None:
        saved[path] = path.read_text(encoding="utf-8")

    try:
        yield track
    finally:
        for path, text in saved.items():
            path.write_text(text, encoding="utf-8")


# --- Baseline ----------------------------------------------------------------


def test_gate_passes_on_the_real_policy() -> None:
    outcome = gate.run_gate(gate.load_policy())
    assert outcome.ok is True
    assert outcome.violations == []
    assert outcome.report["comparison"]["verdict"] == "inconclusive"


def test_release_evidence_byte_matches_golden() -> None:
    evidence = gate._release_evidence(gate.load_policy())
    golden = (FIXTURES_DIR / "golden" / "release_report.golden").read_text(encoding="utf-8")
    assert serialize_canonical(evidence) == golden


# --- [high] no-op / malformed policy rejected before evaluation ---------------


def test_gate_rejects_noop_policy() -> None:
    p = _policy()
    p["comparison"]["baseline"] = "variant_b"
    p["comparison"]["candidate"] = "variant_b"  # baseline == candidate
    p["comparison"]["practical_threshold"] = 0.0
    with pytest.raises(ValueError):
        gate.run_gate(p)


def test_gate_rejects_out_of_range_floor() -> None:
    p = _policy()
    p["answer_floors"]["groundedness"] = 1.5
    with pytest.raises(ValueError):
        gate.run_gate(p)


def test_gate_rejects_bad_bootstrap_config() -> None:
    p = _policy()
    p["bootstrap"]["alpha"] = 1.0
    with pytest.raises(ValueError):
        gate.run_gate(p)


# --- [high] retrieval selectors pinned (held-out + quality metric) -----------


def test_gate_rejects_dev_split() -> None:
    # Evaluating the tuning split instead of held-out is a false-green.
    p = _policy()
    p["retrieval_floor"]["split"] = "dev"
    with pytest.raises(ValueError):
        gate.run_gate(p)


def test_gate_rejects_report_metadata_metric() -> None:
    # num_cases passes a [0,1] floor without measuring retrieval quality.
    p = _policy()
    p["retrieval_floor"]["metric"] = "num_cases"
    with pytest.raises(ValueError):
        gate.run_gate(p)


def test_gate_rejects_unknown_retrieval_method() -> None:
    p = _policy()
    p["retrieval_floor"]["method"] = "bogus"
    with pytest.raises(ValueError):
        gate.run_gate(p)


# --- [high] golden-drift enforcement cannot be disabled by policy ------------


def test_gate_enforces_drift_even_when_opt_out_requested(
    track_restore: Callable[[Path], None],
) -> None:
    golden = FIXTURES_DIR / "golden" / "report_heldout_k5.golden"
    track_restore(golden)
    golden.write_text(golden.read_text(encoding="utf-8") + "  \n", encoding="utf-8")
    p = _policy()
    p["check_golden_drift"] = False  # ignored: drift is mandatory
    outcome = gate.run_gate(p)
    assert outcome.ok is False
    assert any("drifted" in v for v in outcome.violations)


# --- [high] candidate variant / config mismatch ------------------------------


def test_gate_fails_on_candidate_floor_variant_mismatch() -> None:
    p = _policy()
    p["comparison"]["baseline"] = "variant_b"
    p["comparison"]["candidate"] = "variant_a"
    p["answer_floors"] = {
        "variant": "variant_b",  # floors NOT bound to the candidate
        "groundedness": 0.0,
        "citation_validity": 0.0,
        "completeness": 0.0,
        "task_success": 0.0,
    }
    assert any("!= comparison.candidate" in v for v in _violations(p))


# --- [high] independent floors ----------------------------------------------


def test_gate_fails_when_citation_validity_below_floor_though_grounded_passes() -> None:
    p = _policy()
    p["comparison"]["baseline"] = "variant_b"
    p["comparison"]["candidate"] = "variant_a"
    p["answer_floors"] = {
        "variant": "variant_a",
        "groundedness": 0.5,  # variant_a 0.917 -> passes
        "citation_validity": 0.9,  # variant_a 0.875 -> FAILS
        "completeness": 0.5,
        "task_success": 0.5,
    }
    violations = _violations(p)
    assert any("citation_validity" in v for v in violations)
    assert not any("groundedness" in v for v in violations)


def test_gate_fails_when_task_success_below_floor() -> None:
    p = _policy()
    p["comparison"]["baseline"] = "variant_b"
    p["comparison"]["candidate"] = "variant_a"
    p["answer_floors"] = {
        "variant": "variant_a",
        "groundedness": 0.5,
        "citation_validity": 0.5,
        "completeness": 0.5,
        "task_success": 0.9,  # variant_a 0.864 -> FAILS
    }
    assert any("task_success" in v for v in _violations(p))


# --- [high] judge verdict bound to the evaluated answer content --------------


def test_gate_rejects_tampered_answer_with_smuggled_canned(
    track_restore: Callable[[Path], None],
) -> None:
    answers_path = FIXTURES_DIR / "answers.json"
    judge_path = FIXTURES_DIR / "judge.json"
    track_restore(answers_path)
    track_restore(judge_path)
    data = json.loads(answers_path.read_text(encoding="utf-8"))
    new_text = "smuggled tampered candidate answer"
    data["variants"]["variant_b"]["hold-13"]["answer_text"] = new_text
    answers_path.write_text(json.dumps(data), encoding="utf-8")
    jd = json.loads(judge_path.read_text(encoding="utf-8"))
    jd["canned"][_prompt_hash("variant_b", "hold-13", new_text)] = 1  # add, keep old
    judge_path.write_text(json.dumps(jd), encoding="utf-8")
    # Exact-coverage validation: the old hold-13 hash is now an EXTRA canned key.
    with pytest.raises(ValueError):
        gate.run_gate(gate.load_policy())


def test_gate_fails_on_tampered_answer_via_golden_drift(
    track_restore: Callable[[Path], None],
) -> None:
    answers_path = FIXTURES_DIR / "answers.json"
    judge_path = FIXTURES_DIR / "judge.json"
    track_restore(answers_path)
    track_restore(judge_path)
    data = json.loads(answers_path.read_text(encoding="utf-8"))
    old_text = data["variants"]["variant_b"]["hold-13"]["answer_text"]
    new_text = "consistently tampered candidate answer"
    data["variants"]["variant_b"]["hold-13"]["answer_text"] = new_text
    answers_path.write_text(json.dumps(data), encoding="utf-8")
    jd = json.loads(judge_path.read_text(encoding="utf-8"))
    old_hash = _prompt_hash("variant_b", "hold-13", old_text)
    jd["canned"] = {k: v for k, v in jd["canned"].items() if k != old_hash}
    jd["canned"][_prompt_hash("variant_b", "hold-13", new_text)] = 1  # consistent replace
    judge_path.write_text(json.dumps(jd), encoding="utf-8")
    # Exact coverage now passes, but the answer_sha in the answer report drifts.
    outcome = gate.run_gate(gate.load_policy())
    assert outcome.ok is False
    assert any("answer report drifted" in v for v in outcome.violations)


# --- [high] runtime golden drift over ALL committed artifacts ----------------


def test_gate_fails_on_release_golden_corruption(track_restore: Callable[[Path], None]) -> None:
    golden = FIXTURES_DIR / "golden" / "release_report.golden"
    track_restore(golden)
    golden.write_text(golden.read_text(encoding="utf-8") + "  \n", encoding="utf-8")
    outcome = gate.run_gate(gate.load_policy())
    assert outcome.ok is False
    assert any("release evidence drifted" in v for v in outcome.violations)


def test_gate_fails_on_answer_golden_corruption(track_restore: Callable[[Path], None]) -> None:
    golden = FIXTURES_DIR / "golden" / "answer_report_variant_b.golden"
    track_restore(golden)
    golden.write_text(golden.read_text(encoding="utf-8") + "  \n", encoding="utf-8")
    outcome = gate.run_gate(gate.load_policy())
    assert outcome.ok is False
    assert any("answer report drifted" in v for v in outcome.violations)


def test_gate_fails_on_retrieval_golden_corruption(track_restore: Callable[[Path], None]) -> None:
    golden = FIXTURES_DIR / "golden" / "report_heldout_k5.golden"
    track_restore(golden)
    golden.write_text(golden.read_text(encoding="utf-8") + "  \n", encoding="utf-8")
    outcome = gate.run_gate(gate.load_policy())
    assert outcome.ok is False
    assert any("retrieval report drifted" in v for v in outcome.violations)


# --- [high] answer-fixture provenance validated before evaluation ------------


def test_gate_fails_on_dropped_answer_case(track_restore: Callable[[Path], None]) -> None:
    answers_path = FIXTURES_DIR / "answers.json"
    track_restore(answers_path)
    data = json.loads(answers_path.read_text(encoding="utf-8"))
    del data["variants"]["variant_b"]["hold-22"]  # coverage mismatch
    answers_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        gate.run_gate(gate.load_policy())


def test_gate_fails_on_duplicated_answer_case(track_restore: Callable[[Path], None]) -> None:
    answers_path = FIXTURES_DIR / "answers.json"
    track_restore(answers_path)
    data = json.loads(answers_path.read_text(encoding="utf-8"))
    data["cases"].append("hold-01")  # duplicate id
    answers_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        gate.run_gate(gate.load_policy())


# --- other floor / improvement / CLI paths -----------------------------------


def test_gate_fails_when_retrieval_floor_breached() -> None:
    p = _policy()
    p["retrieval_floor"]["floor"] = 0.99
    assert any("retrieval floor breached" in v for v in _violations(p))


def test_gate_fails_when_improvement_required_but_inconclusive() -> None:
    p = _policy()
    p["comparison"]["require_improvement"] = True
    assert any("improvement required" in v for v in _violations(p))


# --- [high] runtime policy bound to the committed contract -------------------


def test_gate_rejects_unpinned_candidate() -> None:
    # A runtime policy that selects a different candidate has no committed golden.
    p = _policy()
    p["comparison"]["candidate"] = "variant_c"
    with pytest.raises(ValueError):
        gate.run_gate(p)


def test_gate_rejects_runtime_floor_change() -> None:
    p = _policy()
    p["retrieval_floor"]["floor"] = 0.5  # weaker floor, not the committed contract
    with pytest.raises(ValueError):
        gate.run_gate(p)


# --- [high] bootstrap seed validated -----------------------------------------


@pytest.mark.parametrize("bad_seed", ["not-a-seed", 3.5, -1, 2**32])
def test_gate_rejects_bad_seed(bad_seed: object) -> None:
    p = _policy()
    p["bootstrap"]["seed"] = bad_seed
    with pytest.raises(ValueError):
        gate.validate_policy(p)


def test_gate_cli_exit_zero_on_pass(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "release_report.json").exists()


def test_gate_cli_exit_nonzero_on_fail(tmp_path: Path) -> None:
    p = _policy()
    p["retrieval_floor"]["floor"] = 0.99
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(p), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--policy", str(policy_path), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


def test_gate_cli_exit_nonzero_on_noop_policy(tmp_path: Path) -> None:
    p = _policy()
    p["comparison"]["baseline"] = "variant_b"
    p["comparison"]["candidate"] = "variant_b"
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(p), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--policy", str(policy_path), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "rejected" in proc.stdout


@pytest.mark.parametrize("bad_seed", ["not-a-seed", 3.5, 4294967296])
def test_gate_cli_exit_nonzero_on_bad_seed(bad_seed: object, tmp_path: Path) -> None:
    p = _policy()
    p["bootstrap"]["seed"] = bad_seed
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(p), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT), "--policy", str(policy_path), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
