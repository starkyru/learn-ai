/**
 * answer-eval.ts — claim-level answer & citation evaluation (Task 2).
 * Port of answer_eval.py; produces byte-identical reports.
 *
 * Each atomic claim is checked deterministically for support by its cited
 * passage and for a valid (gold) citation. The residual task-success judgement
 * comes from a fake, deterministic LLM judge whose canned scores are keyed by
 * input — modeled with the shared `ChatMessage` prompt shape, no network.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { ChatMessage } from "@learn-ai/llm-core";
import { fnv1a32, tokenize } from "./retrieval.js";

export function loadJson<T>(fixturesDir: string, name: string): T {
  return JSON.parse(readFileSync(join(fixturesDir, name), "utf-8")) as T;
}

export interface Claim {
  id: string;
  text: string;
  citation: string;
}
export interface AnswersFixture {
  cases: string[];
  variants: Record<string, Record<string, { answer_text: string; claims: Claim[] }>>;
}
export interface AnswerRubric {
  id: string;
  support_threshold: number;
  stopwords: string[];
}
export interface JudgeFixture {
  judge_model: string;
  prompt_version: string;
  canned: Record<string, number>;
}

// --- Deterministic support / citation checks ---------------------------------

export function contentTokens(text: string, stopwords: Iterable<string>): Set<string> {
  const stop = new Set(stopwords);
  return new Set(tokenize(text).filter((t) => !stop.has(t)));
}

export function supports(
  claimText: string,
  passageText: string,
  stopwords: Iterable<string>,
  threshold: number,
): boolean {
  const claimWords = contentTokens(claimText, stopwords);
  if (claimWords.size === 0) return false;
  const passageWords = new Set(tokenize(passageText));
  let overlap = 0;
  for (const w of claimWords) if (passageWords.has(w)) overlap += 1;
  return overlap / claimWords.size >= threshold;
}

export interface ClaimVerdict {
  claim_id: string;
  citation: string;
  grounded: boolean;
  citation_valid: boolean;
  reason: string;
}

export function evaluateClaim(
  claim: Claim,
  corpusText: ReadonlyMap<string, string>,
  goldIds: ReadonlySet<string>,
  stopwords: Iterable<string>,
  threshold: number,
): ClaimVerdict {
  const citation = claim.citation;
  const citedExists = corpusText.has(citation);
  const citedSupports =
    citedExists &&
    supports(claim.text, corpusText.get(citation)!, stopwords, threshold);
  let supportedElsewhere = false;
  for (const [cid, text] of corpusText) {
    if (cid !== citation && supports(claim.text, text, stopwords, threshold)) {
      supportedElsewhere = true;
      break;
    }
  }
  const isGold = goldIds.has(citation);
  const grounded = citedSupports;
  const citationValid = citedExists && citedSupports && isGold;

  let reason: string;
  if (!citedExists) reason = "dangling_citation";
  else if (!citedSupports)
    reason = supportedElsewhere ? "wrong_passage" : "unsupported";
  else if (!isGold) reason = "non_gold_passage";
  else reason = "valid";

  return {
    claim_id: claim.id,
    citation,
    grounded,
    citation_valid: citationValid,
    reason,
  };
}

// --- Fake LLM judge (the single mocked boundary) -----------------------------

/** Content key for the judge: FNV-1a of the full user prompt (embeds variant,
 * case, query, and answer). A changed answer rekeys the lookup. */
export function promptHash(userContent: string): string {
  return String(fnv1a32(userContent));
}

export class FakeJudge {
  readonly modelId: string;
  private readonly canned: Map<string, number>;

  constructor(canned: Map<string, number>, modelId: string) {
    this.canned = canned;
    this.modelId = modelId;
  }

  /** Deterministic stand-in for provider.chat: returns a canned JSON verdict.
   * Keyed by the FNV hash of the user prompt content; an unseen/changed answer
   * defaults to 0 ("the judge has not approved it"). */
  complete(messages: readonly ChatMessage[]): string {
    const user = messages.find((m) => m.role === "user");
    if (user === undefined) throw new Error("judge prompt has no user message");
    const score = this.canned.get(promptHash(user.content)) ?? 0;
    return JSON.stringify({ task_success: score });
  }
}

export class LlmJudge {
  readonly modelId: string;
  readonly promptVersion: string;
  private readonly provider: FakeJudge;

  constructor(provider: FakeJudge, promptVersion: string) {
    this.provider = provider;
    this.modelId = provider.modelId;
    this.promptVersion = promptVersion;
  }

  buildMessages(
    variant: string,
    caseId: string,
    query: string,
    answerText: string,
  ): ChatMessage[] {
    const system =
      "You are a strict answer evaluator. Decide whether the answer fully " +
      'satisfies the query. Reply only with JSON {"task_success": 0 or 1}.';
    const user = `KEY: ${variant}/${caseId}\nQUERY: ${query}\nANSWER: ${answerText}`;
    return [
      { role: "system", content: system },
      { role: "user", content: user },
    ];
  }

  taskSuccess(
    variant: string,
    caseId: string,
    query: string,
    answerText: string,
  ): number {
    const messages = this.buildMessages(variant, caseId, query, answerText);
    return Number(JSON.parse(this.provider.complete(messages)).task_success);
  }
}

export function makeFakeJudge(fixturesDir: string): LlmJudge {
  const fixture = loadJson<JudgeFixture>(fixturesDir, "judge.json");
  const canned = new Map<string, number>();
  for (const [h, v] of Object.entries(fixture.canned)) canned.set(String(h), Number(v));
  return new LlmJudge(
    new FakeJudge(canned, fixture.judge_model),
    fixture.prompt_version,
  );
}

// --- Answer-level evaluation -------------------------------------------------

interface CasesFile {
  cases: Array<{
    id: string;
    query: string;
    gold: Array<{ chunk_id: string; grade: number }>;
  }>;
}
interface CorpusFile {
  chunks: Array<{ id: string; text: string }>;
}

export interface VariantReport {
  rubric: string;
  judge: { model: string; prompt_version: string };
  variant: string;
  num_cases: number;
  num_claims: number;
  metrics: {
    groundedness: number;
    citation_validity: number;
    completeness: number;
    task_success_rate: number;
  };
  unsupported_claims: Array<{ case_id: string; claim_id: string; citation: string }>;
  invalid_citations: Array<{
    case_id: string;
    claim_id: string;
    citation: string;
    reason: string;
  }>;
  per_case: Record<
    string,
    {
      answer_sha: string;
      groundedness: number;
      citation_validity: number;
      completeness: number;
      task_success: number;
      score: number;
    }
  >;
}

/** Mean, or 0.0 for an empty array (matches answer_eval.py; avoids NaN). */
export function mean(values: readonly number[]): number {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0.0;
}

export function evaluateVariant(fixturesDir: string, variant: string): VariantReport {
  const answers = loadJson<AnswersFixture>(fixturesDir, "answers.json");
  const rubric = loadJson<AnswerRubric>(fixturesDir, "answer_rubric.json");
  const corpus = loadJson<CorpusFile>(fixturesDir, "corpus.json");
  const cases = loadJson<CasesFile>(fixturesDir, "cases_heldout.json");
  // "Gold" here is the SAME relevance threshold Task 1 uses, sourced from
  // rubrics.json so the two cannot desync.
  const relThreshold = loadJson<{ relevant_threshold: number }>(
    fixturesDir,
    "rubrics.json",
  ).relevant_threshold;

  const corpusText = new Map(corpus.chunks.map((c) => [c.id, c.text]));
  const goldByCase = new Map<string, Set<string>>();
  const queryByCase = new Map<string, string>();
  for (const c of cases.cases) {
    goldByCase.set(
      c.id,
      new Set(c.gold.filter((g) => g.grade >= relThreshold).map((g) => g.chunk_id)),
    );
    queryByCase.set(c.id, c.query);
  }
  const stopwords = rubric.stopwords;
  const threshold = rubric.support_threshold;
  const judge = makeFakeJudge(fixturesDir);

  const caseIds = answers.cases;
  const variantAnswers = answers.variants[variant];
  const unsupported: VariantReport["unsupported_claims"] = [];
  const invalid: VariantReport["invalid_citations"] = [];
  const perCase: VariantReport["per_case"] = {};
  let totalClaims = 0;
  let groundedClaims = 0;
  let validClaims = 0;

  for (const caseId of caseIds) {
    const answer = variantAnswers[caseId];
    const goldIds = goldByCase.get(caseId) ?? new Set<string>();
    const claims = answer.claims;
    let caseGrounded = 0;
    let caseValid = 0;
    const coveredGold = new Set<string>();
    for (const claim of claims) {
      const v = evaluateClaim(claim, corpusText, goldIds, stopwords, threshold);
      totalClaims += 1;
      if (v.grounded) {
        caseGrounded += 1;
        groundedClaims += 1;
        if (goldIds.has(claim.citation)) coveredGold.add(claim.citation);
      } else {
        unsupported.push({
          case_id: caseId,
          claim_id: claim.id,
          citation: claim.citation,
        });
      }
      if (v.citation_valid) {
        caseValid += 1;
        validClaims += 1;
      } else {
        invalid.push({
          case_id: caseId,
          claim_id: claim.id,
          citation: claim.citation,
          reason: v.reason,
        });
      }
    }
    const nClaims = claims.length;
    const nGold = goldIds.size;
    const groundedness = nClaims ? caseGrounded / nClaims : 0.0;
    const citationValidity = nClaims ? caseValid / nClaims : 0.0;
    const completeness = nGold ? coveredGold.size / nGold : 0.0;
    const taskSuccess = judge.taskSuccess(
      variant,
      caseId,
      queryByCase.get(caseId) ?? "",
      answer.answer_text,
    );
    perCase[caseId] = {
      // A hash of the answer text so a changed answer causes golden drift the
      // gate detects at runtime, even if the numeric metrics are equal.
      answer_sha: String(fnv1a32(answer.answer_text)),
      groundedness,
      citation_validity: citationValidity,
      completeness,
      task_success: taskSuccess,
      // Comparison score includes task_success so an answer that fails the task
      // lowers it (and cannot leave the release green).
      score: (groundedness + citationValidity + completeness + taskSuccess) / 4.0,
    };
  }

  const nCases = caseIds.length;
  return {
    rubric: rubric.id,
    judge: { model: judge.modelId, prompt_version: judge.promptVersion },
    variant,
    num_cases: nCases,
    num_claims: totalClaims,
    metrics: {
      groundedness: totalClaims ? groundedClaims / totalClaims : 0.0,
      citation_validity: totalClaims ? validClaims / totalClaims : 0.0,
      completeness: mean(caseIds.map((c) => perCase[c].completeness)),
      task_success_rate: mean(caseIds.map((c) => perCase[c].task_success)),
    },
    unsupported_claims: unsupported,
    invalid_citations: invalid,
    per_case: perCase,
  };
}

export function variantCaseScores(
  report: VariantReport,
  caseIds: readonly string[],
): number[] {
  return caseIds.map((cid) => report.per_case[cid].score);
}

/** Validate the answer fixture BEFORE evaluation (port of validate_answer_fixtures). */
export function validateAnswerFixtures(fixturesDir: string): void {
  const answers = loadJson<
    AnswersFixture & { corpus_version?: string; rubric?: string }
  >(fixturesDir, "answers.json");
  const rubric = loadJson<AnswerRubric>(fixturesDir, "answer_rubric.json");
  const judge = loadJson<JudgeFixture & { rubric?: string }>(fixturesDir, "judge.json");
  const human = loadJson<{
    rubric?: string;
    labels: Record<string, Record<string, number>>;
  }>(fixturesDir, "human_labels.json");
  const corpus = loadJson<CorpusFile & { version?: string }>(
    fixturesDir,
    "corpus.json",
  );
  const cases = loadJson<CasesFile>(fixturesDir, "cases_heldout.json");
  const corpusIds = new Set(corpus.chunks.map((c) => c.id));
  const heldoutIds = new Set(cases.cases.map((c) => c.id));
  const queries = new Map(cases.cases.map((c) => [c.id, c.query]));

  if (answers.corpus_version !== corpus.version)
    throw new Error("answers.corpus_version mismatch");
  if (answers.rubric !== rubric.id)
    throw new Error("answers.rubric != answer_rubric id");
  if (judge.rubric !== rubric.id) throw new Error("judge.rubric != answer_rubric id");
  if (human.rubric !== rubric.id)
    throw new Error("human_labels.rubric != answer_rubric id");

  const caseIds = answers.cases;
  if (caseIds.length === 0) throw new Error("answers.cases is empty");
  if (new Set(caseIds).size !== caseIds.length)
    throw new Error("answers.cases has duplicate ids");
  if (caseIds.length !== heldoutIds.size || caseIds.some((c) => !heldoutIds.has(c))) {
    throw new Error("answers.cases must equal the exact held-out id set");
  }

  const variants = answers.variants;
  if (Object.keys(variants).length === 0) throw new Error("answers has no variants");
  const idSet = new Set(caseIds);
  for (const [variant, cases2] of Object.entries(variants)) {
    const keys = new Set(Object.keys(cases2));
    if (keys.size !== idSet.size || [...idSet].some((c) => !keys.has(c))) {
      throw new Error(`variant ${variant} coverage != declared cases`);
    }
    for (const cid of caseIds) {
      const answerText = cases2[cid].answer_text;
      if (typeof answerText !== "string" || answerText.trim() === "") {
        throw new Error(`${variant}/${cid}: empty or non-string answer_text`);
      }
      const claims = cases2[cid].claims;
      if (!claims || claims.length === 0)
        throw new Error(`${variant}/${cid}: no claims`);
      const claimIds = claims.map((c) => c.id);
      if (new Set(claimIds).size !== claimIds.length) {
        throw new Error(`${variant}/${cid}: duplicate claim id`);
      }
      for (const c of claims) {
        if (!c.text || c.text.trim() === "")
          throw new Error(`${variant}/${cid}/${c.id}: empty text`);
        if (!corpusIds.has(c.citation)) {
          throw new Error(`${variant}/${cid}/${c.id}: citation not in corpus`);
        }
      }
    }
  }

  // Judge provenance: the canned keys must EXACTLY cover the full-prompt hashes
  // of the current answers (no missing, no extra) with binary scores, so a
  // changed answer + a smuggled-in canned entry cannot leave the judgement bound
  // to stale content.
  const jdg = makeFakeJudge(fixturesDir);
  const expected = new Set<string>();
  for (const [variant, cases2] of Object.entries(variants)) {
    for (const cid of caseIds) {
      const user = jdg.buildMessages(
        variant,
        cid,
        queries.get(cid) ?? "",
        cases2[cid].answer_text,
      )[1].content;
      expected.add(promptHash(user));
    }
  }
  const cannedKeys = new Set(Object.keys(judge.canned).map(String));
  if (
    cannedKeys.size !== expected.size ||
    [...expected].some((h) => !cannedKeys.has(h))
  ) {
    throw new Error("judge.canned keys must exactly cover the answer prompts");
  }
  if (Object.values(judge.canned).some((v) => Number(v) !== 0 && Number(v) !== 1)) {
    throw new Error("judge.canned scores must be binary (0 or 1)");
  }

  for (const [variant, lab] of Object.entries(human.labels)) {
    if (!(variant in variants))
      throw new Error(`human labels reference unknown variant ${variant}`);
    if (Object.keys(lab).some((c) => !idSet.has(c))) {
      throw new Error(`human labels for ${variant} reference unknown cases`);
    }
    if (Object.keys(lab).length < Math.ceil(0.1 * caseIds.length)) {
      throw new Error(`human labels for ${variant} cover < 10% of cases`);
    }
  }
}
