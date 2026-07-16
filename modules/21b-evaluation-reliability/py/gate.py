"""gate.py — enforceable offline release gate (Module 21b).

Exits NONZERO when the release policy is violated:
  - a held-out metric floor is breached (retrieval OR any of the FOUR answer
    metrics: groundedness, citation_validity, completeness, task_success),
  - the candidate variant is misconfigured (answer floors not bound to the
    variant actually being compared/promoted),
  - an improvement was required but the paired comparison is inconclusive,
  - any committed report drifts at runtime (retrieval report, answer reports, or
    the release evidence);
and exits 0 when the policy passes. This is what makes the module usable as a CI
release gate. Everything is offline and deterministic.

Run it:
    uv run python modules/21b-evaluation-reliability/py/gate.py
    uv run python modules/21b-evaluation-reliability/py/gate.py --policy <path> --out <dir>
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

import agreement
import answer_eval
import uncertainty
from benchmark import (
    FIXTURES_DIR,
    RetrievalConfig,
    RetrievalIndex,
    build_report,
    evaluate_split,
    load_cases,
    load_corpus,
    load_manifest,
    load_rubric,
    serialize_canonical,
    serialize_report,
)
from retrieval import METHODS as RETRIEVAL_METHODS

GOLDEN_DIR = FIXTURES_DIR / "golden"

# Policy floor key -> answer-report metric key.
_FLOOR_METRICS = {
    "groundedness": "groundedness",
    "citation_validity": "citation_validity",
    "completeness": "completeness",
    "task_success": "task_success_rate",
}

# Retrieval quality metrics a floor may gate on (NOT report metadata like
# num_cases / num_failures, which would pass a [0,1] floor without measuring
# retrieval quality).
_QUALITY_METRICS = frozenset({"recall_at_k", "mrr", "ndcg_at_k"})


def load_policy() -> dict[str, Any]:
    with (FIXTURES_DIR / "release_policy.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def validate_policy(policy: Mapping[str, Any]) -> None:
    """Reject a malformed/no-op policy BEFORE evaluation. A no-op policy
    (baseline == candidate, threshold 0) would make every diff 0 and yield a
    spurious 'promote', so it must be rejected."""
    cp = policy["comparison"]
    if cp["baseline"] == cp["candidate"]:
        raise ValueError("comparison.baseline and candidate must be distinct")
    threshold = cp["practical_threshold"]
    if not _finite_number(threshold) or threshold <= 0:
        raise ValueError("comparison.practical_threshold must be a finite number > 0")

    # Retrieval selectors: gate on HELD-OUT data with a supported method and a
    # QUALITY metric (never the tuning split or report metadata).
    rf = policy["retrieval_floor"]
    if rf["split"] != "heldout":
        raise ValueError("retrieval_floor.split must be 'heldout' (not a tuning split)")
    if isinstance(rf["k"], bool) or not isinstance(rf["k"], int) or rf["k"] <= 0:
        raise ValueError("retrieval_floor.k must be a positive integer")
    if rf["method"] not in RETRIEVAL_METHODS:
        raise ValueError(f"retrieval_floor.method must be one of {sorted(RETRIEVAL_METHODS)}")
    if rf["metric"] not in _QUALITY_METRICS:
        raise ValueError(f"retrieval_floor.metric must be one of {sorted(_QUALITY_METRICS)}")

    floors = [("retrieval_floor.floor", policy["retrieval_floor"]["floor"])]
    floors += [(f"answer_floors.{k}", policy["answer_floors"][k]) for k in _FLOOR_METRICS]
    for name, floor in floors:
        if not _finite_number(floor) or not (0.0 <= floor <= 1.0):
            raise ValueError(f"{name} must be a finite number in [0, 1]")

    bp = policy["bootstrap"]
    iterations = bp["iterations"]
    if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations <= 0:
        raise ValueError("bootstrap.iterations must be a positive integer")
    alpha = bp["alpha"]
    if not _finite_number(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("bootstrap.alpha must be a number in (0, 1)")
    seed = bp["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or not (0 <= seed <= 0xFFFFFFFF):
        raise ValueError("bootstrap.seed must be an integer in [0, 2**32 - 1]")


_CONTRACT_KEYS = ("retrieval_floor", "answer_floors", "comparison", "bootstrap")


def policy_digest(policy: Mapping[str, Any]) -> str:
    """Canonical digest of the release-contract fields of a policy."""
    return serialize_canonical({k: policy[k] for k in _CONTRACT_KEYS})


def require_committed_policy(policy: Mapping[str, Any]) -> None:
    """Bind the runtime policy to the committed release_policy.json. A runtime
    policy that differs (e.g. an unpinned candidate variant) is rejected — you
    must commit a new policy AND regenerate its goldens to change the contract."""
    if policy_digest(policy) != policy_digest(load_policy()):
        raise ValueError(
            "runtime policy does not match the committed release_policy.json "
            "(commit a new policy + goldens to change the release contract)"
        )


def _retrieval_report(split: str, k: int) -> dict[str, Any]:
    manifest = load_manifest()
    threshold = int(load_rubric()["relevant_threshold"])
    corpus = load_corpus()
    index = RetrievalIndex(corpus["chunks"], RetrievalConfig.from_manifest(manifest))
    cases = load_cases(split)["cases"]
    result = evaluate_split(index, cases, k, threshold)
    return build_report(split, k, manifest, result, len(cases), threshold)


@dataclass
class GateOutcome:
    ok: bool
    violations: list[str]
    report: dict[str, Any]


def _agreement_report(variant_reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Judge <-> human agreement. Judge labels are the fake judge's ACTUAL
    per-case task_success on the committed answers (content-keyed), not a static
    table, so a changed answer changes the judge label too."""
    judge_fixture = answer_eval.load_judge_fixture()
    human = answer_eval.load_human_labels()["labels"]
    variant = next(iter(human))
    report = variant_reports.get(variant) or answer_eval.evaluate_variant(variant)
    judge_labels = {c: int(report["per_case"][c]["task_success"]) for c in human[variant]}
    return agreement.build_agreement_report(
        variant,
        judge_labels,
        {c: int(v) for c, v in human[variant].items()},
        judge_fixture["judge_model"],
        judge_fixture["prompt_version"],
    )


def _release_evidence(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic release evidence (no gate/drift meta). Evaluates the ACTUAL
    comparison candidate/baseline and enforces the four answer floors against the
    candidate."""
    rf = policy["retrieval_floor"]
    report = _retrieval_report(rf["split"], rf["k"])
    observed_retrieval = float(report["metrics"][rf["method"]][rf["metric"]])

    cp = policy["comparison"]
    bp = policy["bootstrap"]
    af = policy["answer_floors"]
    case_ids = answer_eval.load_answers()["cases"]
    baseline_report = answer_eval.evaluate_variant(cp["baseline"])
    candidate_report = answer_eval.evaluate_variant(cp["candidate"])

    answer_floor_results = {}
    for floor_key, metric_key in _FLOOR_METRICS.items():
        floor = af[floor_key]
        observed = float(candidate_report["metrics"][metric_key])
        answer_floor_results[floor_key] = {
            "floor": floor,
            "observed": observed,
            "passed": observed >= floor,
        }

    comparison = uncertainty.compare_variants(
        answer_eval.variant_case_scores(baseline_report, case_ids),
        answer_eval.variant_case_scores(candidate_report, case_ids),
        cp["practical_threshold"],
        bp["iterations"],
        bp["seed"],
        bp["alpha"],
    )
    agreement_report = _agreement_report(
        {cp["baseline"]: baseline_report, cp["candidate"]: candidate_report}
    )

    return {
        "retrieval_floor": {
            "split": rf["split"],
            "method": rf["method"],
            "metric": rf["metric"],
            "k": rf["k"],
            "floor": rf["floor"],
            "observed": observed_retrieval,
            "passed": observed_retrieval >= rf["floor"],
        },
        "answer_floors": {
            "variant": af["variant"],
            "candidate": cp["candidate"],
            **answer_floor_results,
        },
        "comparison": {
            "baseline": cp["baseline"],
            "candidate": cp["candidate"],
            "require_improvement": bool(cp.get("require_improvement")),
            **comparison,
        },
        "agreement": agreement_report,
    }


def _check_drift() -> tuple[dict[str, bool], list[str]]:
    """Runtime golden-drift over ALL committed artifacts: the retrieval report,
    both answer reports, and the release evidence (which pins the bootstrap CI
    and kappa). Uses the COMMITTED policy so it is independent of the runtime
    policy."""
    committed = load_policy()
    violations: list[str] = []

    rf = committed["retrieval_floor"]
    golden = GOLDEN_DIR / f"report_{rf['split']}_k{rf['k']}.golden"
    if serialize_report(_retrieval_report(rf["split"], rf["k"])) != golden.read_text(
        encoding="utf-8"
    ):
        violations.append(f"retrieval report drifted from {golden.name}")

    cp = committed["comparison"]
    for variant in sorted({cp["baseline"], cp["candidate"]}):
        golden_path = GOLDEN_DIR / f"answer_report_{variant}.golden"
        if serialize_canonical(answer_eval.evaluate_variant(variant)) != golden_path.read_text(
            encoding="utf-8"
        ):
            violations.append(f"answer report drifted from {golden_path.name}")

    evidence_golden = GOLDEN_DIR / "release_report.golden"
    if serialize_canonical(_release_evidence(committed)) != evidence_golden.read_text(
        encoding="utf-8"
    ):
        violations.append(f"release evidence drifted from {evidence_golden.name}")

    return {"checked": True, "drifted": bool(violations)}, violations


def evaluate_policy(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> list[str]:
    """Floor / config / verdict violations for a policy + its evidence (no drift,
    no policy binding). Pure logic — the discriminating unit for floor tests."""
    violations: list[str] = []
    cp = policy["comparison"]
    af = policy["answer_floors"]

    if af["variant"] != cp["candidate"]:
        violations.append(
            f"answer_floors.variant {af['variant']!r} != comparison.candidate {cp['candidate']!r}"
        )
    rfe = evidence["retrieval_floor"]
    if not rfe["passed"]:
        violations.append(
            f"retrieval floor breached: {rfe['method']}.{rfe['metric']} "
            f"{rfe['observed']:.4f} < {rfe['floor']}"
        )
    for floor_key in _FLOOR_METRICS:
        fr = evidence["answer_floors"][floor_key]
        if not fr["passed"]:
            violations.append(
                f"answer floor breached: {cp['candidate']}.{floor_key} "
                f"{fr['observed']:.4f} < {fr['floor']}"
            )
    if cp.get("require_improvement") and evidence["comparison"]["verdict"] != "promote":
        violations.append(
            f"improvement required but comparison verdict is {evidence['comparison']['verdict']!r}"
        )
    return violations


def build_release_report(policy: Mapping[str, Any]) -> GateOutcome:
    # Gate 0: reject a malformed/no-op policy, an unpinned runtime policy, or a
    # malformed answer fixture BEFORE any evaluation.
    validate_policy(policy)
    require_committed_policy(policy)
    answer_eval.validate_answer_fixtures()

    evidence = _release_evidence(policy)
    violations = evaluate_policy(policy, evidence)

    # Golden-drift enforcement is MANDATORY for a release-gate run: it cannot be
    # disabled by policy (that would let a consistently-doctored answer pass).
    golden_drift, drift_violations = _check_drift()
    violations += drift_violations

    report = {
        **evidence,
        "golden_drift": golden_drift,
        "gate": {"ok": not violations, "violations": violations},
    }
    return GateOutcome(ok=not violations, violations=violations, report=report)


def run_gate(policy: Mapping[str, Any], out_dir: Path | None = None) -> GateOutcome:
    outcome = build_release_report(policy)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "release_report.json").write_text(
            serialize_canonical(outcome.report), encoding="utf-8"
        )
    return outcome


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=None, help="release policy JSON")
    parser.add_argument("--out", type=Path, default=None, help="output dir for release_report.json")
    args = parser.parse_args()

    if args.policy is not None:
        with args.policy.open(encoding="utf-8") as handle:
            policy = json.load(handle)
    else:
        policy = load_policy()

    out_dir = args.out or Path(tempfile.mkdtemp(prefix="m21b-gate-"))
    try:
        outcome = run_gate(policy, out_dir)
    except ValueError as error:
        # Malformed policy or fixture -> the gate rejects the release.
        print(f"release gate: FAIL  (rejected: {error})")
        sys.exit(1)

    verdict = outcome.report["comparison"]["verdict"]
    print(f"release gate: {'PASS' if outcome.ok else 'FAIL'}  (comparison verdict: {verdict})")
    for violation in outcome.violations:
        print(f"  - violation: {violation}")
    print(f"release_report written to: {out_dir / 'release_report.json'}")
    sys.exit(0 if outcome.ok else 1)


if __name__ == "__main__":
    main()
