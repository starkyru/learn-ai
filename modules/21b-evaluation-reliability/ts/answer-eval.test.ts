/**
 * answer-eval.test.ts — claim-level answer & citation evaluation (Task 2).
 * Mirrors test_answer_eval.py; classifications and metrics asserted exactly.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { serializeCanonical } from "./benchmark.js";
import {
  type AnswersFixture,
  type Claim,
  evaluateClaim,
  evaluateVariant,
  loadJson,
  makeFakeJudge,
  mean,
  supports,
  validateAnswerFixtures,
} from "./answer-eval.js";

const FX = join(__dirname, "..", "fixtures");
const corpus = loadJson<{ chunks: Array<{ id: string; text: string }> }>(
  FX,
  "corpus.json",
);
const rubric = loadJson<{ stopwords: string[]; support_threshold: number }>(
  FX,
  "answer_rubric.json",
);
const STOP = rubric.stopwords;
const THR = rubric.support_threshold;
const corpusText = new Map(corpus.chunks.map((c) => [c.id, c.text]));

function claim(text: string, citation: string): Claim {
  return { id: "c1", text, citation };
}

describe("deterministic support / citation checks", () => {
  test("supports true when content words present", () => {
    expect(
      supports(
        "Create an API key from the dashboard",
        corpusText.get("auth-api-keys")!,
        STOP,
        THR,
      ),
    ).toBe(true);
  });
  test("supports false for an off-topic claim", () => {
    expect(
      supports(
        "Tokens are stored in a browser cookie",
        corpusText.get("auth-api-keys")!,
        STOP,
        THR,
      ),
    ).toBe(false);
  });
  test("valid when cited gold supports", () => {
    const v = evaluateClaim(
      claim(
        "Create an API key from the Aurora dashboard under Settings Keys",
        "auth-api-keys",
      ),
      corpusText,
      new Set(["auth-api-keys"]),
      STOP,
      THR,
    );
    expect(v.grounded).toBe(true);
    expect(v.citation_valid).toBe(true);
    expect(v.reason).toBe("valid");
  });
  test("fabricated claim is unsupported", () => {
    const v = evaluateClaim(
      claim(
        "Aurora stores your login token inside a browser cookie for single sign on",
        "auth-token-expiry",
      ),
      corpusText,
      new Set(["auth-token-expiry"]),
      STOP,
      THR,
    );
    expect(v.grounded).toBe(false);
    expect(v.citation_valid).toBe(false);
    expect(v.reason).toBe("unsupported");
  });
  test("wrong-passage citation", () => {
    const v = evaluateClaim(
      claim(
        "The response includes a Retry-After header telling you how many seconds to wait before retrying",
        "ratelimit-headers",
      ),
      corpusText,
      new Set(["ratelimit-429"]),
      STOP,
      THR,
    );
    expect(v.grounded).toBe(false);
    expect(v.citation_valid).toBe(false);
    expect(v.reason).toBe("wrong_passage");
  });
  test("non-gold passage", () => {
    const v = evaluateClaim(
      claim("Enterprise is custom priced", "billing-plans"),
      corpusText,
      new Set(["billing-usage-metering"]),
      STOP,
      THR,
    );
    expect(v.grounded).toBe(true);
    expect(v.citation_valid).toBe(false);
    expect(v.reason).toBe("non_gold_passage");
  });
});

test("mean of empty is 0 (zero-cases guard, parity with Python)", () => {
  expect(mean([])).toBe(0.0);
  expect(mean([1, 2, 3])).toBe(2.0);
});

describe("variant-level evaluation", () => {
  test("variant_b is fully clean", () => {
    const r = evaluateVariant(FX, "variant_b");
    expect(r.metrics.groundedness).toBe(1.0);
    expect(r.metrics.citation_validity).toBe(1.0);
    expect(r.metrics.completeness).toBe(1.0);
    expect(r.unsupported_claims).toEqual([]);
    expect(r.invalid_citations).toEqual([]);
  });

  test("variant_a reports expected defects", () => {
    const r = evaluateVariant(FX, "variant_a");
    expect(r.num_claims).toBe(24);
    expect(r.metrics.groundedness).toBe(22 / 24);
    expect(r.metrics.citation_validity).toBe(21 / 24);
    expect(r.metrics.completeness).toBe(19 / 22);
    expect(r.metrics.task_success_rate).toBe(19 / 22);
    const unsupported = new Set(
      r.unsupported_claims.map((c) => `${c.case_id}/${c.claim_id}`),
    );
    expect(unsupported).toEqual(new Set(["hold-04/c1", "hold-07/c1"]));
    const invalid = new Set(r.invalid_citations.map((c) => `${c.case_id}/${c.reason}`));
    expect(invalid).toEqual(
      new Set([
        "hold-04/unsupported",
        "hold-07/wrong_passage",
        "hold-10/non_gold_passage",
      ]),
    );
  });

  test("fake judge is content-sensitive (finding-3 proof)", () => {
    const answers = loadJson<AnswersFixture>(FX, "answers.json");
    const cases = loadJson<{ cases: Array<{ id: string; query: string }> }>(
      FX,
      "cases_heldout.json",
    );
    const queries = new Map(cases.cases.map((c) => [c.id, c.query]));
    const judge = makeFakeJudge(FX);
    const a4 = answers.variants.variant_a["hold-04"].answer_text;
    expect(judge.taskSuccess("variant_a", "hold-04", queries.get("hold-04")!, a4)).toBe(
      0,
    );
    const a1 = answers.variants.variant_a["hold-01"].answer_text;
    expect(judge.taskSuccess("variant_a", "hold-01", queries.get("hold-01")!, a1)).toBe(
      1,
    );
    // Changed answer -> different prompt hash -> not approved.
    expect(
      judge.taskSuccess("variant_a", "hold-01", queries.get("hold-01")!, "unseen"),
    ).toBe(0);
    expect(judge.modelId).toBe("fake-judge-v1");
  });

  test("validateAnswerFixtures accepts the real fixtures", () => {
    expect(() => validateAnswerFixtures(FX)).not.toThrow();
  });

  test("answer reports byte-match the committed golden", () => {
    for (const variant of ["variant_a", "variant_b"]) {
      const report = evaluateVariant(FX, variant);
      const golden = readFileSync(
        join(FX, "golden", `answer_report_${variant}.golden`),
        "utf-8",
      );
      expect(serializeCanonical(report)).toBe(golden);
    }
  });
});
