"""test_retrieval_benchmark.py — tests for the Module 21b retrieval benchmark.

Two kinds of test:

1. Metric correctness. The expected Recall@k / MRR / NDCG@k values are derived
   BY HAND on paper (see the comments) on tiny known inputs and asserted as
   exact numbers. They are never produced by calling the function under test,
   so a regression in the metric changes the number and fails the test.

2. Fixture integrity + determinism. Every gold id must exist in the corpus, the
   dev and held-out splits must be disjoint, and each retrieval method must
   return the identical ranking when run twice on the same query.

Run:
    uv run pytest modules/21b-evaluation-reliability/py -q
"""

from __future__ import annotations

import math
from typing import Any

import benchmark as bench
import pytest
from metrics import (
    dcg_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from retrieval import (
    METHODS,
    RetrievalConfig,
    RetrievalIndex,
    bigram_set,
    embed,
    fnv1a_32,
    tokenize,
)

# --- Recall@k (hand-computed) -------------------------------------------------


def test_recall_at_k_partial_hit() -> None:
    # ranked top-2 = {a, b}; relevant = {b, d}; overlap = {b}; 1 of 2 = 0.5
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, {"b", "d"}, 2) == 0.5


def test_recall_at_k_full_recall_at_larger_k() -> None:
    # top-4 = {a, b, c, d}; both relevant present; 2 of 2 = 1.0
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, {"b", "d"}, 4) == 1.0


def test_recall_at_k_zero_when_none_in_top_k() -> None:
    # top-1 = {a}; relevant = {b, d}; none present -> 0 of 2 = 0.0
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, {"b", "d"}, 1) == 0.0


def test_recall_at_k_gold_absent_from_ranking() -> None:
    # relevant id "x" is not in the ranking at all -> 0/1 = 0.0
    assert recall_at_k(["a", "b"], {"x"}, 2) == 0.0


# --- Reciprocal rank / MRR (hand-computed) -----------------------------------


def test_reciprocal_rank_first_relevant_at_two() -> None:
    # first relevant ("b") is at position 2 -> 1/2 = 0.5
    assert reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5


def test_reciprocal_rank_first_relevant_at_one() -> None:
    # "a" is relevant and at position 1 -> 1/1 = 1.0
    assert reciprocal_rank(["a", "b", "c"], {"a", "c"}) == 1.0


def test_reciprocal_rank_none_found() -> None:
    assert reciprocal_rank(["a", "b"], {"z"}) == 0.0


def test_reciprocal_rank_cutoff_excludes_late_hit() -> None:
    # first relevant ("c") is at position 3, but cutoff k=2 -> 0.0
    assert reciprocal_rank(["a", "b", "c"], {"c"}, k=2) == 0.0


def test_reciprocal_rank_rejects_nonpositive_k() -> None:
    # Validation policy matches recall_at_k / dcg_at_k.
    with pytest.raises(ValueError):
        reciprocal_rank(["a"], {"a"}, k=0)
    with pytest.raises(ValueError):
        reciprocal_rank(["a"], {"a"}, k=-1)


def test_mean_reciprocal_rank_average() -> None:
    # RRs are 1/2, 1/1, 0 -> mean = (0.5 + 1.0 + 0.0) / 3 = 0.5
    results = [
        (["a", "b", "c"], {"b"}),
        (["a", "b", "c"], {"a"}),
        (["a", "b", "c"], {"z"}),
    ]
    assert mean_reciprocal_rank(results) == 0.5


# --- DCG / NDCG (hand-computed) ----------------------------------------------


def test_dcg_at_k_hand_value() -> None:
    # grades a=3, c=1; ranked a,b,c; gains 2^g - 1 -> 7, 0, 1
    # DCG = 7/log2(2) + 0/log2(3) + 1/log2(4) = 7/1 + 0 + 1/2 = 7.5
    grades = {"a": 3.0, "c": 1.0}
    assert dcg_at_k(["a", "b", "c"], grades, 3) == 7.5


def test_ndcg_perfect_ranking_is_one() -> None:
    # ranking already equals the ideal (grades descending) -> NDCG = 1.0
    grades = {"a": 3.0, "b": 1.0}
    assert ndcg_at_k(["a", "b"], grades, 2) == 1.0


def test_ndcg_single_relevant_pushed_to_rank_two() -> None:
    # ranked b,a; grades a=3, b=0.
    # DCG  = 0/log2(2) + 7/log2(3) = 7/log2(3)
    # IDCG = 7/log2(2) + 0         = 7
    # NDCG = (7/log2(3)) / 7 = 1/log2(3) = 0.6309297535714575
    grades = {"a": 3.0, "b": 0.0}
    expected = 1.0 / math.log2(3.0)
    assert math.isclose(ndcg_at_k(["b", "a"], grades, 2), expected, rel_tol=0.0, abs_tol=1e-12)


def test_ndcg_mixed_grades_hand_value() -> None:
    # ranked a,b,c; grades a=1, b=0, c=3.
    # DCG  = 1/log2(2) + 0 + 7/log2(4) = 1 + 3.5 = 4.5
    # IDCG = 7/log2(2) + 1/log2(3) + 0 = 7 + 1/log2(3) = 7.6309297535714575
    # NDCG = 4.5 / 7.6309297535714575 = 0.5897068...
    grades = {"a": 1.0, "b": 0.0, "c": 3.0}
    expected = 4.5 / (7.0 + 1.0 / math.log2(3.0))
    assert math.isclose(ndcg_at_k(["a", "b", "c"], grades, 3), expected, rel_tol=0.0, abs_tol=1e-12)


def test_ndcg_all_zero_grades_is_zero() -> None:
    # IDCG is 0 when there is no positive grade -> NDCG defined as 0.0
    assert ndcg_at_k(["a", "b"], {"a": 0.0, "b": 0.0}, 2) == 0.0


# --- FNV-1a hash pins (stable, cross-language) --------------------------------


def test_fnv1a_known_vectors() -> None:
    # FNV-1a/32 reference values (canonical test vectors for this algorithm).
    assert fnv1a_32("") == 2166136261
    assert fnv1a_32("a") == 0xE40C292C
    assert fnv1a_32("foobar") == 0xBF9CF968


# --- Reranker bigram encoding (collision-free) --------------------------------


def test_bigram_set_has_no_false_collision() -> None:
    # ("do","g") and ("d","og") are DIFFERENT bigrams: phrase_hits must be 0.
    # A separator-less concat encoding would map both to "dog" and yield 1.
    colliding = bigram_set(["do", "g"]) & bigram_set(["d", "og"])
    assert colliding == set()  # phrase_hits = 0


def test_bigram_set_matches_a_genuine_adjacent_pair() -> None:
    # A real adjacent bigram still matches: phrase_hits = 1.
    real = bigram_set(["do", "g"]) & bigram_set(["do", "g", "x"])
    assert real == {("do", "g")}


# --- Fixture integrity --------------------------------------------------------


def _corpus_ids() -> set[str]:
    return {c["id"] for c in bench.load_corpus()["chunks"]}


def test_all_gold_ids_exist_in_corpus() -> None:
    corpus_ids = _corpus_ids()
    for split in ("dev", "heldout"):
        for case in bench.load_cases(split)["cases"]:
            for gold in case["gold"]:
                assert gold["chunk_id"] in corpus_ids, (
                    f"{case['id']} references unknown chunk {gold['chunk_id']}"
                )


def test_every_case_has_a_primary_grade_three() -> None:
    for split in ("dev", "heldout"):
        for case in bench.load_cases(split)["cases"]:
            grades = [g["grade"] for g in case["gold"]]
            assert max(grades) == 3, f"{case['id']} has no grade-3 primary evidence"


def test_dev_and_heldout_queries_are_disjoint() -> None:
    dev_q = {c["query"] for c in bench.load_cases("dev")["cases"]}
    hold_q = {c["query"] for c in bench.load_cases("heldout")["cases"]}
    assert dev_q.isdisjoint(hold_q)


def test_split_case_counts_meet_minimum() -> None:
    assert len(bench.load_cases("dev")["cases"]) >= 30
    assert len(bench.load_cases("heldout")["cases"]) >= 20


def test_corpus_size_in_expected_range() -> None:
    assert 15 <= len(_corpus_ids()) <= 40


def test_case_ids_are_unique() -> None:
    ids = [c["id"] for split in ("dev", "heldout") for c in bench.load_cases(split)["cases"]]
    assert len(ids) == len(set(ids))


# --- Determinism --------------------------------------------------------------


def _index() -> RetrievalIndex:
    manifest = bench.load_manifest()
    config = RetrievalConfig.from_manifest(manifest)
    return RetrievalIndex(bench.load_corpus()["chunks"], config)


def test_each_method_is_deterministic() -> None:
    index = _index()
    query = "How long does an access token last before it expires?"
    for method in METHODS:
        first = index.rank(method, query)
        second = index.rank(method, query)
        assert first == second
        # A full permutation of the corpus is returned every time.
        assert set(first) == set(index.ids)
        assert len(first) == len(index.ids)


def test_embed_is_deterministic_and_normalised() -> None:
    v1 = embed("token bucket rate limit", 256, 3)
    v2 = embed("token bucket rate limit", 256, 3)
    assert list(v1) == list(v2)
    assert math.isclose(float((v1 * v1).sum()), 1.0, abs_tol=1e-12)


def test_methods_are_not_all_identical() -> None:
    # Dense (fuzzy) and BM25 (exact-term) must disagree on at least one case,
    # otherwise "comparing methods" would be vacuous.
    index = _index()
    disagreements = 0
    for case in bench.load_cases("dev")["cases"]:
        if index.dense(case["query"])[:5] != index.bm25(case["query"])[:5]:
            disagreements += 1
    assert disagreements > 0


def test_tokenize_splits_on_non_alphanumeric() -> None:
    assert tokenize("X-RateLimit-Remaining: 42!") == ["x", "ratelimit", "remaining", "42"]


# --- End-to-end evaluation shape ---------------------------------------------


def test_evaluate_split_reports_all_methods_and_versions() -> None:
    manifest = bench.load_manifest()
    index = bench.build_index(manifest=manifest)
    cases = bench.load_cases("dev")["cases"]
    result = bench.evaluate_split(index, cases, k=5, threshold=1)
    report = bench.build_report("dev", 5, manifest, result, len(cases), 1)

    for method in METHODS:
        m = report["metrics"][method]
        assert 0.0 <= m["recall_at_k"] <= 1.0
        assert 0.0 <= m["mrr"] <= 1.0
        assert 0.0 <= m["ndcg_at_k"] <= 1.0

    versions = report["versions"]
    assert versions["corpus_version"] == "aurora-docs-v1"
    for key in (
        "chunker_version",
        "embedder_version",
        "index_version",
        "bm25_version",
        "hybrid_version",
        "reranker_version",
    ):
        assert versions[key], f"missing version: {key}"
    assert report["k"] == 5


def test_failure_report_flags_missing_gold_for_a_hard_case() -> None:
    # hold-05 ("why am I getting a 403 ...") — the dense stand-in misses the
    # gold auth-scopes / api-errors chunks, so it must appear in dense failures.
    index = _index()
    cases = bench.load_cases("heldout")["cases"]
    result = bench.evaluate_split(index, cases, k=5, threshold=1)
    dense_failures = {f["case_id"] for f in result["failures"]["dense"]}
    assert "hold-05" in dense_failures


# --- Golden byte-parity regression lock --------------------------------------
#
# These committed goldens (fixtures/golden/*.golden) are byte-identical across
# the Python and TypeScript ports. The tests regenerate the report and the
# per-case rankings and assert they byte-equal the committed goldens, so ANY
# ranking or serialization drift in either implementation fails deterministically.


def _golden(name: str) -> str:
    return (bench.FIXTURES_DIR / "golden" / name).read_text(encoding="utf-8")


def test_report_serialization_byte_matches_golden() -> None:
    manifest = bench.load_manifest()
    rubric = bench.load_rubric()
    threshold = int(rubric["relevant_threshold"])
    k = int(manifest["default_k"])
    index = bench.build_index(manifest=manifest)
    for split in ("dev", "heldout"):
        cases = bench.load_cases(split)["cases"]
        result = bench.evaluate_split(index, cases, k, threshold)
        report = bench.build_report(split, k, manifest, result, len(cases), threshold)
        assert bench.serialize_report(report) == _golden(f"report_{split}_k{k}.golden")


def test_per_case_rankings_byte_match_golden() -> None:
    manifest = bench.load_manifest()
    index = bench.build_index(manifest=manifest)
    for split in ("dev", "heldout"):
        cases = bench.load_cases(split)["cases"]
        ranks = bench.all_rankings(index, cases)
        assert bench.serialize_canonical(ranks) == _golden(f"rankings_{split}.golden")


# --- Metric fail-fast on malformed (duplicate) rankings ----------------------


def test_recall_rejects_duplicate_ranked_ids() -> None:
    # Without the guard this would return 2 (an impossible recall > 1).
    with pytest.raises(ValueError):
        recall_at_k(["a", "a"], {"a"}, 2)


def test_dcg_rejects_duplicate_ranked_ids() -> None:
    with pytest.raises(ValueError):
        dcg_at_k(["a", "a"], {"a": 3.0}, 2)


def test_ndcg_rejects_duplicate_ranked_ids() -> None:
    # A repeated gold id would push NDCG above 1; fail fast instead.
    with pytest.raises(ValueError):
        ndcg_at_k(["a", "a"], {"a": 3.0}, 2)


# --- Fixture validation: comprehensive provenance binding --------------------

RUBRIC_ID = "graded-relevance-v1"
CORPUS_VERSION = "aurora-docs-v1"
_REAL_CHUNK = "auth-api-keys"


def _mk_case(gold: list[dict[str, Any]], rubric: str = RUBRIC_ID) -> dict[str, Any]:
    return {"id": "x", "query": "q", "gold": gold, "rubric": rubric}


def _valid_case(cid: str, query: str, chunk: str = _REAL_CHUNK) -> dict[str, Any]:
    return {
        "id": cid,
        "query": query,
        "gold": [{"chunk_id": chunk, "grade": 3}],
        "rubric": RUBRIC_ID,
    }


def _split_obj(split: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {"split": split, "corpus_version": CORPUS_VERSION, "rubric": RUBRIC_ID, "cases": cases}


def test_validate_fixtures_accepts_the_real_fixtures() -> None:
    bench.validate_fixtures(
        bench.load_corpus(),
        bench.load_manifest(),
        bench.load_rubric(),
        {"dev": bench.load_cases("dev"), "heldout": bench.load_cases("heldout")},
    )


# -- per-case ----------------------------------------------------------------


def test_validate_case_rejects_out_of_range_grade() -> None:
    # Otherwise valid (grade-3 primary, right rubric); only the 4 is wrong.
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "b", "grade": 4}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a", "b"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_negative_grade() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "b", "grade": -1}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a", "b"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_non_integer_grade() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "b", "grade": 2.5}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a", "b"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_duplicate_gold_id() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "a", "grade": 1}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_unknown_chunk() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "zzz", "grade": 1}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_mismatched_rubric_id() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}], rubric="other-rubric-v9")
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_missing_primary_grade() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 1}])
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a"}, 0, 3, RUBRIC_ID)


def test_validate_case_rejects_empty_query() -> None:
    case = {"id": "x", "query": "   ", "gold": [{"chunk_id": "a", "grade": 3}], "rubric": RUBRIC_ID}
    with pytest.raises(ValueError):
        bench.validate_case(case, {"a"}, 0, 3, RUBRIC_ID)


def test_validate_case_accepts_a_valid_case() -> None:
    case = _mk_case([{"chunk_id": "a", "grade": 3}, {"chunk_id": "b", "grade": 1}])
    bench.validate_case(case, {"a", "b"}, 0, 3, RUBRIC_ID)  # must not raise


# -- per-split provenance ----------------------------------------------------


def test_validate_split_rejects_swapped_split_label() -> None:
    # A cases file labeled "heldout" but loaded as the expected "dev" split.
    cases_obj = _split_obj("heldout", [_valid_case("d1", "q1")])
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


def test_validate_split_rejects_missing_split_field() -> None:
    cases_obj = {"corpus_version": CORPUS_VERSION, "rubric": RUBRIC_ID, "cases": []}
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


def test_validate_split_rejects_corpus_version_mismatch() -> None:
    cases_obj = {"split": "dev", "corpus_version": "WRONG", "rubric": RUBRIC_ID, "cases": []}
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


def test_validate_split_rejects_mismatched_rubric_id() -> None:
    cases_obj = {
        "split": "dev",
        "corpus_version": CORPUS_VERSION,
        "rubric": "other-v9",
        "cases": [],
    }
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


def test_validate_split_rejects_duplicate_case_id_within_split() -> None:
    cases_obj = _split_obj("dev", [_valid_case("d1", "q1"), _valid_case("d1", "q2")])
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


def test_validate_split_rejects_duplicate_query_within_split() -> None:
    cases_obj = _split_obj("dev", [_valid_case("d1", "same"), _valid_case("d2", "same")])
    with pytest.raises(ValueError):
        bench.validate_split(cases_obj, {_REAL_CHUNK}, CORPUS_VERSION, (0, 3), RUBRIC_ID, "dev")


# -- cross-split + top-level provenance --------------------------------------


def test_validate_fixtures_rejects_cross_split_duplicate_query() -> None:
    dev = _split_obj("dev", [_valid_case("d1", "shared query")])
    held = _split_obj("heldout", [_valid_case("h1", "shared query")])
    with pytest.raises(ValueError):
        bench.validate_fixtures(
            bench.load_corpus(),
            bench.load_manifest(),
            bench.load_rubric(),
            {"dev": dev, "heldout": held},
        )


def test_validate_fixtures_rejects_cross_split_duplicate_case_id() -> None:
    dev = _split_obj("dev", [_valid_case("dup", "q-dev")])
    held = _split_obj("heldout", [_valid_case("dup", "q-held")])
    with pytest.raises(ValueError):
        bench.validate_fixtures(
            bench.load_corpus(),
            bench.load_manifest(),
            bench.load_rubric(),
            {"dev": dev, "heldout": held},
        )


def test_validate_fixtures_rejects_swapped_split_file() -> None:
    # The "dev" key holds the heldout cases object (split label "heldout").
    with pytest.raises(ValueError):
        bench.validate_fixtures(
            bench.load_corpus(),
            bench.load_manifest(),
            bench.load_rubric(),
            {"dev": bench.load_cases("heldout"), "heldout": bench.load_cases("dev")},
        )


# -- corpus / rubric / manifest metadata -------------------------------------


def test_validate_corpus_rejects_duplicate_chunk_id() -> None:
    corpus = {"version": "v", "chunks": [{"id": "a", "text": "t"}, {"id": "a", "text": "u"}]}
    with pytest.raises(ValueError):
        bench.validate_corpus(corpus)


def test_validate_corpus_rejects_empty_text() -> None:
    corpus = {"version": "v", "chunks": [{"id": "a", "text": "   "}]}
    with pytest.raises(ValueError):
        bench.validate_corpus(corpus)


def test_validate_rubric_rejects_out_of_range_threshold() -> None:
    rubric = {**bench.load_rubric(), "relevant_threshold": 9}
    with pytest.raises(ValueError):
        bench.validate_rubric(rubric)


def test_validate_manifest_rejects_bad_default_k() -> None:
    manifest = {**bench.load_manifest(), "default_k": 0}
    with pytest.raises(ValueError):
        bench.validate_manifest(manifest, CORPUS_VERSION, RUBRIC_ID)


def test_validate_manifest_rejects_out_of_range_bm25_b() -> None:
    base = bench.load_manifest()
    manifest = {**base, "bm25": {**base["bm25"], "b": 1.5}}
    with pytest.raises(ValueError):
        bench.validate_manifest(manifest, CORPUS_VERSION, RUBRIC_ID)


def test_validate_manifest_rejects_corpus_version_mismatch() -> None:
    with pytest.raises(ValueError):
        bench.validate_manifest(bench.load_manifest(), "WRONG-VERSION", RUBRIC_ID)
