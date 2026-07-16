"""answer_eval.py — claim-level answer & citation evaluation (Module 21b, Task 2).

An answer is decomposed into atomic claims (pre-segmented in the fixture). For
each claim we check DETERMINISTICALLY whether (a) the CITED passage supports it
and (b) the citation points to the RIGHT passage (a gold-evidence chunk for the
query). We report answer-level metrics separately — groundedness, claim-level
citation validity, completeness, task success — and list unsupported claims and
invalid citations separately.

The residual holistic judgement (task success) comes from an LLM rubric via the
shared ``llm_core`` client, faked with a deterministic ``FakeJudgeProvider``
whose scores are canned and keyed by input (variant + case) — no network.

Everything else is deterministic and offline.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any

from benchmark import FIXTURES_DIR, load_cases, load_corpus, load_rubric
from llm_core import ChatMessage, ChatOptions, ChatResult, EmbeddingResult, TokenUsage
from retrieval import fnv1a_32, tokenize


def _load_json(name: str) -> Any:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_answers() -> dict[str, Any]:
    return _load_json("answers.json")


def load_answer_rubric() -> dict[str, Any]:
    return _load_json("answer_rubric.json")


def load_judge_fixture() -> dict[str, Any]:
    return _load_json("judge.json")


def load_human_labels() -> dict[str, Any]:
    return _load_json("human_labels.json")


# --- Deterministic support / citation checks ---------------------------------


def content_tokens(text: str, stopwords: Iterable[str]) -> set[str]:
    stop = set(stopwords)
    return {t for t in tokenize(text) if t not in stop}


def supports(
    claim_text: str, passage_text: str, stopwords: Iterable[str], threshold: float
) -> bool:
    """A claim is supported by a passage when >= ``threshold`` of its content
    words appear in the passage (a deterministic lexical grounding check)."""
    claim_words = content_tokens(claim_text, stopwords)
    if not claim_words:
        return False
    passage_words = set(tokenize(passage_text))
    coverage = len(claim_words & passage_words) / len(claim_words)
    return coverage >= threshold


def evaluate_claim(
    claim: Mapping[str, Any],
    corpus_text: Mapping[str, str],
    gold_ids: set[str],
    stopwords: Iterable[str],
    threshold: float,
) -> dict[str, Any]:
    """Deterministic per-claim verdict: grounded? citation valid? why not?"""
    citation = claim["citation"]
    cited_exists = citation in corpus_text
    cited_supports = cited_exists and supports(
        claim["text"], corpus_text[citation], stopwords, threshold
    )
    supported_elsewhere = any(
        supports(claim["text"], corpus_text[cid], stopwords, threshold)
        for cid in corpus_text
        if cid != citation
    )
    is_gold = citation in gold_ids
    grounded = cited_supports
    citation_valid = cited_exists and cited_supports and is_gold

    if not cited_exists:
        reason = "dangling_citation"
    elif not cited_supports:
        reason = "wrong_passage" if supported_elsewhere else "unsupported"
    elif not is_gold:
        reason = "non_gold_passage"
    else:
        reason = "valid"

    return {
        "claim_id": claim["id"],
        "citation": citation,
        "grounded": grounded,
        "citation_valid": citation_valid,
        "reason": reason,
    }


# --- Fake LLM judge (the single mocked boundary) -----------------------------


def prompt_hash(user_content: str) -> str:
    """Content key for the judge: FNV-1a of the full user prompt (which embeds
    variant, case, query, and answer). A changed answer rekeys the lookup."""
    return str(fnv1a_32(user_content))


class FakeJudgeProvider:
    """Deterministic, offline stand-in for an LLM judge, conforming to the
    ``llm_core.LLMProvider`` protocol. The canned scores are keyed by the FNV
    hash of the full user prompt CONTENT (variant + case + query + answer), so a
    changed answer rekeys and defaults to 0 (unseen/unapproved) — the judge does
    not ignore the answer. No network, no randomness."""

    name = "fake-judge"
    embed_model = "none"

    def __init__(self, canned: Mapping[str, int], model_id: str) -> None:
        self._canned = dict(canned)
        self.chat_model = model_id

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        msgs = [m if isinstance(m, ChatMessage) else ChatMessage(**m) for m in messages]
        user = next(m.content for m in msgs if m.role == "user")
        # Unseen/changed answers default to 0 ("the judge has not approved it").
        score = self._canned.get(prompt_hash(user), 0)
        return ChatResult(
            text=json.dumps({"task_success": score}),
            model=self.chat_model,
            usage=TokenUsage(),
        )

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]:
        yield self.chat(messages, options).text

    def embed(self, input: list[str]) -> EmbeddingResult:
        raise NotImplementedError("the judge does not embed")


class LlmJudge:
    """Builds an anchored rubric prompt (shared ``ChatMessage`` shape) and asks
    the provider for a task-success verdict."""

    def __init__(self, provider: FakeJudgeProvider, prompt_version: str) -> None:
        self.provider = provider
        self.model_id = provider.chat_model
        self.prompt_version = prompt_version

    def build_messages(
        self, variant: str, case_id: str, query: str, answer_text: str
    ) -> list[ChatMessage]:
        system = (
            "You are a strict answer evaluator. Decide whether the answer fully "
            'satisfies the query. Reply only with JSON {"task_success": 0 or 1}.'
        )
        user = f"KEY: {variant}/{case_id}\nQUERY: {query}\nANSWER: {answer_text}"
        return [ChatMessage("system", system), ChatMessage("user", user)]

    def task_success(self, variant: str, case_id: str, query: str, answer_text: str) -> int:
        messages = self.build_messages(variant, case_id, query, answer_text)
        result = self.provider.chat(messages, ChatOptions(temperature=0))
        return int(json.loads(result.text)["task_success"])


def make_fake_judge(variant: str | None = None) -> LlmJudge:
    fixture = load_judge_fixture()
    canned = {str(h): int(v) for h, v in fixture["canned"].items()}
    provider = FakeJudgeProvider(canned, fixture["judge_model"])
    return LlmJudge(provider, fixture["prompt_version"])


# --- Answer-level evaluation -------------------------------------------------


def mean(values: Sequence[float]) -> float:
    """Mean, or 0.0 for an empty sequence (matches the TS port; avoids a divide
    by zero for an empty case set)."""
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _gold_ids_by_case(threshold: int | None = None) -> dict[str, set[str]]:
    # "Gold" here is the SAME relevance threshold Task 1 uses, sourced from
    # rubrics.json so the two cannot desync.
    if threshold is None:
        threshold = int(load_rubric()["relevant_threshold"])
    out: dict[str, set[str]] = {}
    for case in load_cases("heldout")["cases"]:
        out[case["id"]] = {g["chunk_id"] for g in case["gold"] if g["grade"] >= threshold}
    return out


def _query_by_case() -> dict[str, str]:
    return {case["id"]: case["query"] for case in load_cases("heldout")["cases"]}


def evaluate_variant(variant: str) -> dict[str, Any]:
    """Evaluate one answer variant across the answered held-out cases."""
    answers = load_answers()
    rubric = load_answer_rubric()
    corpus_text = {c["id"]: c["text"] for c in load_corpus()["chunks"]}
    gold_by_case = _gold_ids_by_case()
    query_by_case = _query_by_case()
    stopwords = rubric["stopwords"]
    threshold = float(rubric["support_threshold"])
    judge = make_fake_judge(variant)

    case_ids: list[str] = answers["cases"]
    variant_answers = answers["variants"][variant]

    unsupported_claims: list[dict[str, Any]] = []
    invalid_citations: list[dict[str, Any]] = []
    per_case: dict[str, Any] = {}
    total_claims = 0
    grounded_claims = 0
    valid_claims = 0

    for case_id in case_ids:
        answer = variant_answers[case_id]
        gold_ids = gold_by_case[case_id]
        claims = answer["claims"]
        case_grounded = 0
        case_valid = 0
        covered_gold: set[str] = set()
        for claim in claims:
            verdict = evaluate_claim(claim, corpus_text, gold_ids, stopwords, threshold)
            total_claims += 1
            if verdict["grounded"]:
                case_grounded += 1
                grounded_claims += 1
                if claim["citation"] in gold_ids:
                    covered_gold.add(claim["citation"])
            else:
                unsupported_claims.append(
                    {"case_id": case_id, "claim_id": claim["id"], "citation": claim["citation"]}
                )
            if verdict["citation_valid"]:
                case_valid += 1
                valid_claims += 1
            else:
                invalid_citations.append(
                    {
                        "case_id": case_id,
                        "claim_id": claim["id"],
                        "citation": claim["citation"],
                        "reason": verdict["reason"],
                    }
                )
        n_claims = len(claims)
        n_gold = len(gold_ids)
        groundedness = case_grounded / n_claims if n_claims else 0.0
        citation_validity = case_valid / n_claims if n_claims else 0.0
        completeness = len(covered_gold) / n_gold if n_gold else 0.0
        task_success = judge.task_success(
            variant, case_id, query_by_case[case_id], answer["answer_text"]
        )
        per_case[case_id] = {
            # A hash of the answer text so a changed answer causes golden drift
            # the gate detects at runtime, even if the numeric metrics are equal.
            "answer_sha": str(fnv1a_32(answer["answer_text"])),
            "groundedness": groundedness,
            "citation_validity": citation_validity,
            "completeness": completeness,
            "task_success": task_success,
            # Comparison score includes task_success so an answer that fails the
            # task lowers it (and cannot leave the release green).
            "score": (groundedness + citation_validity + completeness + task_success) / 4.0,
        }

    n_cases = len(case_ids)
    metrics = {
        "groundedness": grounded_claims / total_claims if total_claims else 0.0,
        "citation_validity": valid_claims / total_claims if total_claims else 0.0,
        "completeness": mean([per_case[c]["completeness"] for c in case_ids]),
        "task_success_rate": mean([per_case[c]["task_success"] for c in case_ids]),
    }
    return {
        "rubric": rubric["id"],
        "judge": {"model": judge.model_id, "prompt_version": judge.prompt_version},
        "variant": variant,
        "num_cases": n_cases,
        "num_claims": total_claims,
        "metrics": metrics,
        "unsupported_claims": unsupported_claims,
        "invalid_citations": invalid_citations,
        "per_case": per_case,
    }


def variant_case_scores(variant_report: Mapping[str, Any], case_ids: Sequence[str]) -> list[float]:
    """Per-case deterministic answer-quality score, in ``case_ids`` order."""
    return [float(variant_report["per_case"][cid]["score"]) for cid in case_ids]


def validate_answer_fixtures() -> None:
    """Validate the answer fixture BEFORE evaluation, so a dropped, duplicated,
    or mislabeled case cannot silently change the denominators/population."""
    answers = load_answers()
    rubric = load_answer_rubric()
    judge_fixture = load_judge_fixture()
    human = load_human_labels()
    corpus = load_corpus()
    corpus_ids = {c["id"] for c in corpus["chunks"]}
    heldout = load_cases("heldout")["cases"]
    heldout_ids = {c["id"] for c in heldout}
    queries = {c["id"]: c["query"] for c in heldout}

    # Provenance bindings.
    if answers.get("corpus_version") != corpus["version"]:
        raise ValueError("answers.corpus_version != corpus version")
    if answers.get("rubric") != rubric["id"]:
        raise ValueError("answers.rubric != answer_rubric id")
    if judge_fixture.get("rubric") != rubric["id"]:
        raise ValueError("judge.rubric != answer_rubric id")
    if human.get("rubric") != rubric["id"]:
        raise ValueError("human_labels.rubric != answer_rubric id")

    # Population: unique, non-empty, and EXACTLY the held-out id set.
    case_ids = answers["cases"]
    if not case_ids:
        raise ValueError("answers.cases is empty")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("answers.cases has duplicate ids")
    if set(case_ids) != heldout_ids:
        raise ValueError("answers.cases must equal the exact held-out id set")

    # Per-variant coverage identical + well-formed claims.
    variants = answers["variants"]
    if not variants:
        raise ValueError("answers has no variants")
    for variant, cases in variants.items():
        if set(cases.keys()) != set(case_ids):
            raise ValueError(f"variant {variant!r} coverage != declared cases")
        for cid in case_ids:
            answer_text = cases[cid].get("answer_text")
            if not isinstance(answer_text, str) or not answer_text.strip():
                raise ValueError(f"{variant}/{cid}: empty or non-string answer_text")
            claims = cases[cid].get("claims")
            if not claims:
                raise ValueError(f"{variant}/{cid}: no claims")
            claim_ids = [c["id"] for c in claims]
            if len(claim_ids) != len(set(claim_ids)):
                raise ValueError(f"{variant}/{cid}: duplicate claim id")
            for c in claims:
                if not str(c.get("text", "")).strip():
                    raise ValueError(f"{variant}/{cid}/{c.get('id')}: empty claim text")
                if c["citation"] not in corpus_ids:
                    raise ValueError(f"{variant}/{cid}/{c['id']}: citation not in corpus")

    # Judge provenance: the canned keys must EXACTLY cover the full-prompt hashes
    # of the current answers (no missing, no extra) with binary scores, so a
    # changed answer + a smuggled-in canned entry cannot leave the judgement
    # bound to stale content.
    judge = make_fake_judge()
    expected_hashes = {
        prompt_hash(
            judge.build_messages(variant, cid, queries[cid], cases[cid]["answer_text"])[1].content
        )
        for variant, cases in variants.items()
        for cid in case_ids
    }
    canned = judge_fixture["canned"]
    if {str(h) for h in canned} != expected_hashes:
        raise ValueError("judge.canned keys must exactly cover the answer prompts")
    if any(int(v) not in (0, 1) for v in canned.values()):
        raise ValueError("judge.canned scores must be binary (0 or 1)")

    # Human-label coverage: known variant, cases subset, and >= 10% of cases.
    for variant, lab in human["labels"].items():
        if variant not in variants:
            raise ValueError(f"human labels reference unknown variant {variant!r}")
        if not set(lab) <= set(case_ids):
            raise ValueError(f"human labels for {variant!r} reference unknown cases")
        if len(lab) < math.ceil(0.1 * len(case_ids)):
            raise ValueError(f"human labels for {variant!r} cover < 10% of cases")
