"""benchmark.py — run the gold-evidence retrieval benchmark (Module 21b, Task 1).

Loads the versioned synthetic corpus and the case fixtures, ranks every case
with each retrieval method, computes Recall@k / MRR / NDCG@k FROM SCRATCH
(before any generator runs), prints a comparison table, and writes a
deterministic JSON report (metrics + per-query failure report) to an output dir.

Run it:

    uv run python modules/21b-evaluation-reliability/py/benchmark.py
    uv run python modules/21b-evaluation-reliability/py/benchmark.py --split heldout --k 5
    uv run python modules/21b-evaluation-reliability/py/benchmark.py --split both --out /tmp/21b

Everything is offline and deterministic: no provider, no network, no randomness.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from metrics import ndcg_at_k, recall_at_k, reciprocal_rank
from retrieval import METHODS, RetrievalConfig, RetrievalIndex

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_manifest() -> dict[str, Any]:
    return _load_json(FIXTURES_DIR / "manifest.json")


def load_corpus() -> dict[str, Any]:
    return _load_json(FIXTURES_DIR / "corpus.json")


def load_rubric() -> dict[str, Any]:
    return _load_json(FIXTURES_DIR / "rubrics.json")


def load_cases(split: str) -> dict[str, Any]:
    if split not in ("dev", "heldout"):
        raise ValueError(f"unknown split: {split}")
    return _load_json(FIXTURES_DIR / f"cases_{split}.json")


def build_index(
    corpus: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
) -> RetrievalIndex:
    corpus = corpus or load_corpus()
    manifest = manifest or load_manifest()
    config = RetrievalConfig.from_manifest(manifest)
    return RetrievalIndex(corpus["chunks"], config)


# --- Fixture validation (runs before any evaluation) -------------------------
#
# Every provenance/metadata field is bound before a single metric is computed:
# corpus version + unique non-empty chunks; rubric id + grade range + threshold;
# manifest cross-refs (versions, default_k, embedder/bm25/hybrid/reranker params);
# per-split label + corpus_version + rubric id; per-case id/query/rubric/gold and
# the primary-grade contract; and global uniqueness of case ids and queries so a
# swapped, mislabeled, or duplicated fixture cannot reach the release population.


def _require_positive_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    return float(value)


def _require_nonempty_str(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")


def rubric_grade_range(rubric: Mapping[str, Any]) -> tuple[int, int]:
    """Lowest/highest grade the rubric declares (e.g. (0, 3))."""
    grades = [int(g["grade"]) for g in rubric["grades"]]
    if not grades:
        raise ValueError("rubric declares no grades")
    return min(grades), max(grades)


def validate_rubric(rubric: Mapping[str, Any]) -> tuple[str, tuple[int, int]]:
    """Bind the rubric id, grade range, and relevant_threshold. Returns both."""
    rubric_id = rubric.get("id")
    _require_nonempty_str(rubric_id, "rubric.id")
    grade_range = rubric_grade_range(rubric)
    grade_min, grade_max = grade_range
    threshold = rubric.get("relevant_threshold")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, int)
        or not (grade_min <= threshold <= grade_max)
    ):
        raise ValueError(
            f"rubric.relevant_threshold {threshold!r} outside grade range "
            f"[{grade_min}, {grade_max}]"
        )
    return rubric_id, grade_range


def validate_corpus(corpus: Mapping[str, Any]) -> set[str]:
    ids: list[str] = []
    for chunk in corpus["chunks"]:
        cid = chunk.get("id")
        _require_nonempty_str(cid, "corpus chunk id")
        _require_nonempty_str(chunk.get("text"), f"corpus chunk {cid!r} text")
        ids.append(cid)
    if len(ids) != len(set(ids)):
        raise ValueError("corpus contains duplicate chunk ids")
    return set(ids)


def validate_manifest(manifest: Mapping[str, Any], corpus_version: str, rubric_id: str) -> None:
    """Bind the manifest cross-refs the report and retrieval config depend on."""
    _require_nonempty_str(manifest.get("benchmark"), "manifest.benchmark")
    _require_nonempty_str(manifest.get("manifest_version"), "manifest.manifest_version")
    if manifest.get("corpus_version") != corpus_version:
        raise ValueError(
            f"manifest corpus_version {manifest.get('corpus_version')!r} "
            f"!= corpus version {corpus_version!r}"
        )
    if manifest.get("rubric") != rubric_id:
        raise ValueError(f"manifest rubric {manifest.get('rubric')!r} != rubric id {rubric_id!r}")
    _require_positive_int(manifest.get("default_k"), "manifest.default_k")
    for block in ("chunker", "embedder", "index", "bm25", "hybrid", "reranker"):
        sub = manifest.get(block)
        if not isinstance(sub, Mapping):
            raise ValueError(f"manifest.{block} block is missing")
        _require_nonempty_str(sub.get("version"), f"manifest.{block}.version")
    _require_positive_int(manifest["embedder"].get("dim"), "manifest.embedder.dim")
    _require_positive_int(manifest["embedder"].get("ngram"), "manifest.embedder.ngram")
    _require_number(manifest["bm25"].get("k1"), "manifest.bm25.k1")
    b = _require_number(manifest["bm25"].get("b"), "manifest.bm25.b")
    if not (0.0 <= b <= 1.0):
        raise ValueError(f"manifest.bm25.b must be in [0, 1], got {b}")
    _require_positive_int(manifest["hybrid"].get("rrf_k"), "manifest.hybrid.rrf_k")
    _require_positive_int(manifest["reranker"].get("candidates"), "manifest.reranker.candidates")
    _require_number(manifest["reranker"].get("phrase_weight"), "manifest.reranker.phrase_weight")


def validate_case(
    case: Mapping[str, Any],
    corpus_ids: set[str],
    grade_min: int,
    grade_max: int,
    rubric_id: str,
) -> None:
    # The primary grade is the rubric's highest declared grade (read from the
    # rubric, not hardcoded): every case must carry at least one such chunk.
    primary_grade = grade_max
    _require_nonempty_str(case.get("id"), "case id")
    cid = case["id"]
    _require_nonempty_str(case.get("query"), f"{cid}: query")
    if case.get("rubric") != rubric_id:
        raise ValueError(f"{cid}: rubric {case.get('rubric')!r} != declared {rubric_id!r}")
    gold = case["gold"]
    if not gold:
        raise ValueError(f"{cid}: no gold evidence")
    gold_ids = [g["chunk_id"] for g in gold]
    if len(gold_ids) != len(set(gold_ids)):
        raise ValueError(f"{cid}: duplicate gold chunk id")
    for g in gold:
        grade = g["grade"]
        if isinstance(grade, bool) or not isinstance(grade, int):
            raise ValueError(f"{cid}: grade {grade!r} is not an integer")
        if not (grade_min <= grade <= grade_max):
            raise ValueError(
                f"{cid}: grade {grade} outside rubric range [{grade_min}, {grade_max}]"
            )
        if g["chunk_id"] not in corpus_ids:
            raise ValueError(f"{cid}: unknown gold chunk {g['chunk_id']!r}")
    if not any(g["grade"] == primary_grade for g in gold):
        raise ValueError(f"{cid}: no primary evidence (needs a grade-{primary_grade} chunk)")


def validate_split(
    cases_obj: Mapping[str, Any],
    corpus_ids: set[str],
    corpus_version: str,
    grade_range: tuple[int, int],
    rubric_id: str,
    expected_split: str,
) -> None:
    if cases_obj.get("split") != expected_split:
        raise ValueError(f"split label {cases_obj.get('split')!r} != expected {expected_split!r}")
    if cases_obj.get("corpus_version") != corpus_version:
        raise ValueError(
            f"split {expected_split!r}: corpus_version "
            f"{cases_obj.get('corpus_version')!r} != corpus {corpus_version!r}"
        )
    if cases_obj.get("rubric") != rubric_id:
        raise ValueError(
            f"split {expected_split!r}: rubric "
            f"{cases_obj.get('rubric')!r} != declared {rubric_id!r}"
        )
    grade_min, grade_max = grade_range
    cases = cases_obj["cases"]
    for case in cases:
        validate_case(case, corpus_ids, grade_min, grade_max, rubric_id)
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"split {expected_split!r}: duplicate case id")
    queries = [c["query"] for c in cases]
    if len(queries) != len(set(queries)):
        raise ValueError(f"split {expected_split!r}: duplicate query")


def validate_fixtures(
    corpus: Mapping[str, Any],
    manifest: Mapping[str, Any],
    rubric: Mapping[str, Any],
    cases_by_split: Mapping[str, Mapping[str, Any]],
) -> None:
    """Raise if any fixture is malformed. Called before evaluation as a gate.

    ``cases_by_split`` maps the EXPECTED split name (from the CLI/filename) to the
    loaded cases object, so a mislabeled file is caught.
    """
    corpus_ids = validate_corpus(corpus)
    rubric_id, grade_range = validate_rubric(rubric)
    validate_manifest(manifest, corpus["version"], rubric_id)

    all_ids: list[str] = []
    all_queries: list[str] = []
    for expected_split, cases_obj in cases_by_split.items():
        validate_split(
            cases_obj, corpus_ids, corpus["version"], grade_range, rubric_id, expected_split
        )
        all_ids.extend(c["id"] for c in cases_obj["cases"])
        all_queries.extend(c["query"] for c in cases_obj["cases"])
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("duplicate case id across splits")
    if len(all_queries) != len(set(all_queries)):
        raise ValueError("duplicate query across splits")


def _relevant_ids(case: Mapping[str, Any], threshold: int) -> set[str]:
    return {g["chunk_id"] for g in case["gold"] if g["grade"] >= threshold}


def _grades(case: Mapping[str, Any]) -> dict[str, float]:
    return {g["chunk_id"]: float(g["grade"]) for g in case["gold"]}


def evaluate_case(
    index: RetrievalIndex,
    method: str,
    case: Mapping[str, Any],
    k: int,
    threshold: int,
) -> dict[str, Any]:
    """Evaluate one case with one method. Metrics only — no generation."""
    ranked = index.rank(method, case["query"])
    relevant = _relevant_ids(case, threshold)
    grades = _grades(case)

    recall = recall_at_k(ranked, relevant, k)
    rr = reciprocal_rank(ranked, relevant)
    ndcg = ndcg_at_k(ranked, grades, k)

    top_k = [
        {
            "chunk_id": cid,
            "grade": grades.get(cid, 0.0),
            "is_gold": cid in relevant,
        }
        for cid in ranked[:k]
    ]
    missing_gold = sorted(cid for cid in relevant if cid not in ranked[:k])

    return {
        "case_id": case["id"],
        "query": case["query"],
        "method": method,
        "recall_at_k": recall,
        "reciprocal_rank": rr,
        "ndcg_at_k": ndcg,
        "top_k": top_k,
        "missing_gold": missing_gold,
    }


def _has_inversion(top_k: Sequence[Mapping[str, Any]]) -> bool:
    """True if a non-gold chunk is ranked above a gold chunk within the top-k."""
    seen_non_gold = False
    for entry in top_k:
        if entry["is_gold"] and seen_non_gold:
            return True
        if not entry["is_gold"]:
            seen_non_gold = True
    return False


def _classify_failure(case_eval: Mapping[str, Any]) -> str | None:
    """A case fails a method if gold is missing from top-k or is mis-ranked.

    "Mis-ranked" means an irrelevant chunk outranks a relevant one inside the
    top-k (a real inversion of gold evidence), not merely a suboptimal order
    among gold chunks of different grades.
    """
    if case_eval["missing_gold"]:
        return "missing_gold"
    if _has_inversion(case_eval["top_k"]):
        return "misranked_gold"
    return None


def all_rankings(
    index: RetrievalIndex,
    cases: Sequence[Mapping[str, Any]],
    methods: Sequence[str] = METHODS,
) -> dict[str, dict[str, list[str]]]:
    """Full ranked chunk-id list per method per case (for the golden lock)."""
    return {
        method: {case["id"]: index.rank(method, case["query"]) for case in cases}
        for method in methods
    }


def evaluate_split(
    index: RetrievalIndex,
    cases: Sequence[Mapping[str, Any]],
    k: int,
    threshold: int,
    methods: Sequence[str] = METHODS,
) -> dict[str, Any]:
    """Compute per-method aggregate metrics and a failure report over a split."""
    per_method_metrics: dict[str, dict[str, float]] = {}
    failures: dict[str, list[dict[str, Any]]] = {}

    for method in methods:
        evals = [evaluate_case(index, method, c, k, threshold) for c in cases]
        n = len(evals) or 1
        per_method_metrics[method] = {
            "recall_at_k": sum(e["recall_at_k"] for e in evals) / n,
            "mrr": sum(e["reciprocal_rank"] for e in evals) / n,
            "ndcg_at_k": sum(e["ndcg_at_k"] for e in evals) / n,
            "num_cases": len(evals),
        }
        method_failures = []
        for e in evals:
            reason = _classify_failure(e)
            if reason is not None:
                method_failures.append({**e, "failure": reason})
        per_method_metrics[method]["num_failures"] = len(method_failures)
        failures[method] = method_failures

    return {"metrics": per_method_metrics, "failures": failures}


def build_report(
    split: str,
    k: int,
    manifest: Mapping[str, Any],
    result: Mapping[str, Any],
    num_cases: int,
    threshold: int,
) -> dict[str, Any]:
    """A fully deterministic report (no wall-clock timestamp) for CI diffing."""
    return {
        "benchmark": manifest["benchmark"],
        "split": split,
        "k": k,
        "relevant_threshold": threshold,
        "num_cases": num_cases,
        "versions": {
            "manifest_version": manifest["manifest_version"],
            "corpus_version": manifest["corpus_version"],
            "chunker_version": manifest["chunker"]["version"],
            "embedder_version": manifest["embedder"]["version"],
            "index_version": manifest["index"]["version"],
            "bm25_version": manifest["bm25"]["version"],
            "hybrid_version": manifest["hybrid"]["version"],
            "reranker_version": manifest["reranker"]["version"],
            "rubric": manifest["rubric"],
        },
        "metrics": result["metrics"],
        "failures": result["failures"],
    }


def format_table(k: int, metrics: Mapping[str, Mapping[str, float]]) -> str:
    header = (
        f"{'method':<10} {'Recall@' + str(k):>10} {'MRR':>8} {'NDCG@' + str(k):>10} {'fails':>6}"
    )
    lines = [header, "-" * len(header)]
    for method in METHODS:
        m = metrics[method]
        lines.append(
            f"{method:<10} {m['recall_at_k']:>10.3f} {m['mrr']:>8.3f} "
            f"{m['ndcg_at_k']:>10.3f} {int(m['num_failures']):>6}"
        )
    return "\n".join(lines)


def format_failures(failures: Mapping[str, Sequence[Mapping[str, Any]]]) -> str:
    lines: list[str] = []
    for method in METHODS:
        method_failures = failures[method]
        if not method_failures:
            lines.append(f"[{method}] no failures")
            continue
        lines.append(f"[{method}] {len(method_failures)} failing case(s):")
        for f in method_failures:
            top = ", ".join(f"{t['chunk_id']}{'*' if t['is_gold'] else ''}" for t in f["top_k"])
            detail = f"missing={f['missing_gold']}" if f["missing_gold"] else "mis-ranked"
            lines.append(
                f'  - {f["case_id"]} ({f["failure"]}): "{f["query"]}" '
                f"[ndcg={f['ndcg_at_k']:.3f}] {detail}; top-k: {top}"
            )
    return "\n".join(lines)


def _canonicalize(obj: Any) -> Any:
    """Render whole-number floats as ints so the JSON report matches the JS one.

    Python's ``json`` writes ``1.0`` / ``3.0`` where JavaScript's
    ``JSON.stringify`` writes ``1`` / ``3`` for the identical IEEE-754 value.
    Coercing integral floats to ints (JS does this implicitly) lets the two
    reports be compared byte-for-byte.
    """
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float) and obj.is_integer():
        return int(obj)
    if isinstance(obj, dict):
        return {key: _canonicalize(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_canonicalize(value) for value in obj]
    return obj


def serialize_canonical(obj: Any) -> str:
    """Canonical JSON for any structure: sorted keys, integral floats as ints,
    trailing newline. Byte-identical to the TypeScript ``serializeCanonical``."""
    body = json.dumps(_canonicalize(obj), indent=2, sort_keys=True, ensure_ascii=False)
    return f"{body}\n"


def serialize_report(report: Mapping[str, Any]) -> str:
    """Canonical JSON for a report (see ``serialize_canonical``)."""
    return serialize_canonical(report)


def write_report(report: Mapping[str, Any], path: Path) -> None:
    """Write a canonical, deterministic JSON report (sorted keys, no timestamp)."""
    path.write_text(serialize_report(report), encoding="utf-8")


def run(split: str, k: int, out_dir: Path) -> dict[str, Any]:
    manifest = load_manifest()
    rubric = load_rubric()
    corpus = load_corpus()
    threshold = int(rubric.get("relevant_threshold", 1))

    # Gate: reject malformed fixtures before any evaluation runs. The dict keys
    # are the EXPECTED split names, so a mislabeled cases file is caught.
    splits = ["dev", "heldout"] if split == "both" else [split]
    cases_by_split = {s: load_cases(s) for s in splits}
    validate_fixtures(corpus, manifest, rubric, cases_by_split)

    index = build_index(corpus=corpus, manifest=manifest)
    reports: dict[str, Any] = {}
    out_dir.mkdir(parents=True, exist_ok=True)

    for s in splits:
        cases = cases_by_split[s]["cases"]
        result = evaluate_split(index, cases, k, threshold)
        report = build_report(s, k, manifest, result, len(cases), threshold)
        report_path = out_dir / f"report_{s}_k{k}.json"
        write_report(report, report_path)
        reports[s] = {"report": report, "path": report_path}

        print(f"\n=== split: {s}  (k={k}, cases={len(cases)}) ===")
        print(format_table(k, report["metrics"]))
        print()
        print(format_failures(report["failures"]))
        print(f"\nreport written to: {report_path}")

    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        choices=["dev", "heldout", "both"],
        default="dev",
        help="which case split to evaluate (default: dev)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=int(load_manifest()["default_k"]),
        help="cutoff k for Recall@k and NDCG@k (default: manifest default_k)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output directory for JSON reports (default: a fresh temp dir)",
    )
    args = parser.parse_args()
    out_dir = args.out or Path(tempfile.mkdtemp(prefix="m21b-retrieval-"))
    run(args.split, args.k, out_dir)


if __name__ == "__main__":
    main()
