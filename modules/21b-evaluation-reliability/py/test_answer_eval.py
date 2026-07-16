"""test_answer_eval.py — claim-level answer & citation evaluation (Task 2).

Deterministic per-claim classification is asserted exactly on crafted claims
(fabricated, wrong-passage, non-gold, valid), and the variant-level metrics +
unsupported/invalid lists are asserted exactly against the hand-traced fixture.
The fake judge is the only mocked boundary.
"""

from __future__ import annotations

import answer_eval as ae
from benchmark import FIXTURES_DIR, load_corpus, serialize_canonical


def _corpus_text() -> dict[str, str]:
    return {c["id"]: c["text"] for c in load_corpus()["chunks"]}


def _rubric_params() -> tuple[list[str], float]:
    rubric = ae.load_answer_rubric()
    return rubric["stopwords"], float(rubric["support_threshold"])


def test_supports_true_when_content_words_present() -> None:
    stop, thr = _rubric_params()
    text = load_corpus()["chunks"][0]["text"]  # auth-api-keys
    assert ae.supports("Create an API key from the dashboard", text, stop, thr) is True


def test_supports_false_for_off_topic_claim() -> None:
    stop, thr = _rubric_params()
    text = _corpus_text()["auth-api-keys"]
    assert ae.supports("Tokens are stored in a browser cookie", text, stop, thr) is False


def test_claim_valid_when_cited_gold_supports() -> None:
    stop, thr = _rubric_params()
    claim = {
        "id": "c1",
        "text": "Create an API key from the Aurora dashboard under Settings Keys",
        "citation": "auth-api-keys",
    }
    v = ae.evaluate_claim(claim, _corpus_text(), {"auth-api-keys"}, stop, thr)
    assert v["grounded"] is True
    assert v["citation_valid"] is True
    assert v["reason"] == "valid"


def test_claim_fabricated_is_unsupported() -> None:
    stop, thr = _rubric_params()
    claim = {
        "id": "c1",
        "text": "Aurora stores your login token inside a browser cookie for single sign on",
        "citation": "auth-token-expiry",
    }
    v = ae.evaluate_claim(claim, _corpus_text(), {"auth-token-expiry"}, stop, thr)
    assert v["grounded"] is False
    assert v["citation_valid"] is False
    assert v["reason"] == "unsupported"


def test_claim_wrong_passage_citation() -> None:
    stop, thr = _rubric_params()
    claim = {
        "id": "c1",
        "text": "The response includes a Retry-After header telling you how many seconds to wait before retrying",
        "citation": "ratelimit-headers",
    }
    v = ae.evaluate_claim(claim, _corpus_text(), {"ratelimit-429"}, stop, thr)
    assert v["grounded"] is False  # not supported by the CITED passage
    assert v["citation_valid"] is False
    assert v["reason"] == "wrong_passage"  # but supported by another passage


def test_claim_non_gold_passage() -> None:
    stop, thr = _rubric_params()
    claim = {"id": "c1", "text": "Enterprise is custom priced", "citation": "billing-plans"}
    v = ae.evaluate_claim(claim, _corpus_text(), {"billing-usage-metering"}, stop, thr)
    assert v["grounded"] is True  # billing-plans does support the claim
    assert v["citation_valid"] is False  # but it is not gold for this query
    assert v["reason"] == "non_gold_passage"


def test_mean_zero_cases_guard_matches_ts() -> None:
    # Empty case set -> 0.0 (not a ZeroDivisionError), matching the TS port.
    assert ae.mean([]) == 0.0
    assert ae.mean([1.0, 2.0, 3.0]) == 2.0


def test_variant_b_is_fully_clean() -> None:
    report = ae.evaluate_variant("variant_b")
    assert report["metrics"]["groundedness"] == 1.0
    assert report["metrics"]["citation_validity"] == 1.0
    assert report["metrics"]["completeness"] == 1.0
    assert report["unsupported_claims"] == []
    assert report["invalid_citations"] == []


def test_variant_a_reports_expected_defects() -> None:
    report = ae.evaluate_variant("variant_a")
    # 24 claims (22 cases; hold-03 & hold-05 have 2), 2 ungrounded -> 22/24;
    # 3 invalid citations -> 21/24; completeness 19/22; task_success 19/22.
    assert report["num_claims"] == 24
    assert report["metrics"]["groundedness"] == 22 / 24
    assert report["metrics"]["citation_validity"] == 21 / 24
    assert report["metrics"]["completeness"] == 19 / 22
    assert report["metrics"]["task_success_rate"] == 19 / 22
    unsupported = {(c["case_id"], c["claim_id"]) for c in report["unsupported_claims"]}
    assert unsupported == {("hold-04", "c1"), ("hold-07", "c1")}
    invalid = {(c["case_id"], c["reason"]) for c in report["invalid_citations"]}
    assert invalid == {
        ("hold-04", "unsupported"),
        ("hold-07", "wrong_passage"),
        ("hold-10", "non_gold_passage"),
    }


def test_fake_judge_is_content_sensitive() -> None:
    # The judge keys on the FULL prompt content, so the COMMITTED answer gets its
    # canned score, but a CHANGED/unseen answer defaults to 0 (finding-3 proof:
    # the judge cannot ignore the answer).
    answers = ae.load_answers()
    queries = {c["id"]: c["query"] for c in ae.load_cases("heldout")["cases"]}
    judge = ae.make_fake_judge()
    a4 = answers["variants"]["variant_a"]["hold-04"]["answer_text"]
    assert judge.task_success("variant_a", "hold-04", queries["hold-04"], a4) == 0
    a1 = answers["variants"]["variant_a"]["hold-01"]["answer_text"]
    assert judge.task_success("variant_a", "hold-01", queries["hold-01"], a1) == 1
    # Change the answer -> different prompt hash -> not approved.
    assert judge.task_success("variant_a", "hold-01", queries["hold-01"], "unseen answer") == 0
    assert judge.model_id == "fake-judge-v1"


def test_validate_answer_fixtures_accepts_real_fixtures() -> None:
    ae.validate_answer_fixtures()  # must not raise


def test_answer_reports_byte_match_golden() -> None:
    for variant in ("variant_a", "variant_b"):
        report = ae.evaluate_variant(variant)
        golden = (FIXTURES_DIR / "golden" / f"answer_report_{variant}.golden").read_text(
            encoding="utf-8"
        )
        assert serialize_canonical(report) == golden
