/**
 * metrics.test.ts — tests for the Module 21b retrieval benchmark (jest).
 *
 * Same two-part contract as the Python suite:
 *   1. Metric correctness — expected Recall@k / MRR / NDCG@k are hand-derived on
 *      tiny inputs (see comments) and asserted as exact numbers; they are never
 *      produced by calling the function under test.
 *   2. Fixture integrity + determinism — gold ids exist in the corpus, dev and
 *      held-out splits are disjoint, and each method ranks identically twice.
 *
 * Run: pnpm test  (or: pnpm jest modules/21b-evaluation-reliability)
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  allRankings,
  type BenchCase,
  buildReport,
  type CasesFixture,
  type CorpusFixture,
  evaluateSplit,
  type RubricFixture,
  serializeCanonical,
  serializeReport,
  validateCase,
  validateCorpus,
  validateFixtures,
  validateManifest,
  validateRubric,
  validateSplit,
} from "./benchmark.js";
import {
  dcgAtK,
  meanReciprocalRank,
  ndcgAtK,
  recallAtK,
  reciprocalRank,
} from "./metrics.js";
import {
  bigramSet,
  type Chunk,
  configFromManifest,
  embed,
  fnv1a32,
  type Manifest,
  METHODS,
  RetrievalIndex,
  tokenize,
} from "./retrieval.js";

function loadFixture<T>(name: string): T {
  return JSON.parse(
    readFileSync(join(__dirname, "..", "fixtures", name), "utf-8"),
  ) as T;
}

function loadGolden(name: string): string {
  return readFileSync(join(__dirname, "..", "fixtures", "golden", name), "utf-8");
}

const corpus = loadFixture<CorpusFixture & { chunks: Chunk[] }>("corpus.json");
const manifest = loadFixture<
  Manifest & { rubric: string; default_k: number; corpus_version: string }
>("manifest.json");
const rubric = loadFixture<RubricFixture>("rubrics.json");
const devCases = loadFixture<{ cases: BenchCase[] }>("cases_dev.json").cases;
const heldoutCases = loadFixture<{ cases: BenchCase[] }>("cases_heldout.json").cases;

function buildIndex(): RetrievalIndex {
  return new RetrievalIndex(corpus.chunks, configFromManifest(manifest));
}

// --- Recall@k (hand-computed) ------------------------------------------------

describe("Recall@k", () => {
  const ranked = ["a", "b", "c", "d"];
  test("partial hit: top-2 {a,b} vs relevant {b,d} = 1/2", () => {
    expect(recallAtK(ranked, ["b", "d"], 2)).toBe(0.5);
  });
  test("full recall at k=4 = 2/2", () => {
    expect(recallAtK(ranked, ["b", "d"], 4)).toBe(1.0);
  });
  test("zero when none in top-1", () => {
    expect(recallAtK(ranked, ["b", "d"], 1)).toBe(0.0);
  });
  test("gold absent from ranking = 0/1", () => {
    expect(recallAtK(["a", "b"], ["x"], 2)).toBe(0.0);
  });
});

// --- Reciprocal rank / MRR (hand-computed) -----------------------------------

describe("Reciprocal rank / MRR", () => {
  test("first relevant at position 2 = 1/2", () => {
    expect(reciprocalRank(["a", "b", "c"], ["b"])).toBe(0.5);
  });
  test("first relevant at position 1 = 1", () => {
    expect(reciprocalRank(["a", "b", "c"], ["a", "c"])).toBe(1.0);
  });
  test("none found = 0", () => {
    expect(reciprocalRank(["a", "b"], ["z"])).toBe(0.0);
  });
  test("cutoff k=2 excludes a hit at position 3", () => {
    expect(reciprocalRank(["a", "b", "c"], ["c"], 2)).toBe(0.0);
  });
  test("MRR of [1/2, 1, 0] = 0.5", () => {
    const results: Array<[string[], string[]]> = [
      [["a", "b", "c"], ["b"]],
      [["a", "b", "c"], ["a"]],
      [["a", "b", "c"], ["z"]],
    ];
    expect(meanReciprocalRank(results)).toBe(0.5);
  });
  test("rejects non-positive k (validation parity with recallAtK)", () => {
    expect(() => reciprocalRank(["a"], ["a"], 0)).toThrow();
    expect(() => reciprocalRank(["a"], ["a"], -1)).toThrow();
  });
});

// --- DCG / NDCG (hand-computed) ----------------------------------------------

describe("DCG / NDCG", () => {
  test("DCG: 7/log2(2) + 0 + 1/log2(4) = 7 + 0.5 = 7.5", () => {
    const grades = new Map([
      ["a", 3],
      ["c", 1],
    ]);
    expect(dcgAtK(["a", "b", "c"], grades, 3)).toBe(7.5);
  });

  test("perfect ranking (grades descending) = 1.0", () => {
    const grades = new Map([
      ["a", 3],
      ["b", 1],
    ]);
    expect(ndcgAtK(["a", "b"], grades, 2)).toBe(1.0);
  });

  test("single relevant pushed to rank 2 => 1/log2(3)", () => {
    // ranked b,a; grades a=3,b=0. DCG = 7/log2(3); IDCG = 7. NDCG = 1/log2(3).
    const grades = new Map([
      ["a", 3],
      ["b", 0],
    ]);
    const expected = 1.0 / Math.log2(3);
    expect(ndcgAtK(["b", "a"], grades, 2)).toBeCloseTo(expected, 12);
  });

  test("mixed grades a=1,b=0,c=3 => 4.5 / (7 + 1/log2(3))", () => {
    // DCG = 1/log2(2) + 0 + 7/log2(4) = 1 + 3.5 = 4.5.
    // IDCG = 7/log2(2) + 1/log2(3) = 7 + 1/log2(3).
    const grades = new Map([
      ["a", 1],
      ["b", 0],
      ["c", 3],
    ]);
    const expected = 4.5 / (7 + 1 / Math.log2(3));
    expect(ndcgAtK(["a", "b", "c"], grades, 3)).toBeCloseTo(expected, 12);
  });

  test("all-zero grades => 0.0 (IDCG is 0)", () => {
    const grades = new Map([
      ["a", 0],
      ["b", 0],
    ]);
    expect(ndcgAtK(["a", "b"], grades, 2)).toBe(0.0);
  });
});

// --- FNV-1a hash pins (stable, cross-language) -------------------------------

describe("FNV-1a/32", () => {
  test("canonical test vectors", () => {
    expect(fnv1a32("")).toBe(2166136261);
    expect(fnv1a32("a")).toBe(0xe40c292c);
    expect(fnv1a32("foobar")).toBe(0xbf9cf968);
  });
});

// --- Reranker bigram encoding (collision-free) -------------------------------

describe("reranker bigram encoding", () => {
  // phrase_hits, exactly as the reranker computes it: how many query bigrams
  // are present as adjacent doc bigrams (the intersection size of the two sets).
  const phraseHits = (q: string[], doc: string[]): number => {
    const qb = bigramSet(q);
    const db = bigramSet(doc);
    let hits = 0;
    for (const bg of qb) if (db.has(bg)) hits += 1;
    return hits;
  };

  test("colliding token splits do NOT produce a false phrase hit", () => {
    // ("do","g") vs ("d","og"): distinct bigrams. Python reference phrase_hits
    // = |{("do","g")} ∩ {("d","og")}| = 0. A separator-less `${a}${b}` encoding
    // maps both to "dog" and wrongly returns 1 — this assertion locks that out.
    expect(phraseHits(["do", "g"], ["d", "og"])).toBe(0);
  });

  test("a genuine adjacent bigram still matches (phrase_hits = 1)", () => {
    // Python reference: |{("do","g")} ∩ {("do","g"),("g","x")}| = 1.
    expect(phraseHits(["do", "g"], ["do", "g", "x"])).toBe(1);
  });
});

// --- Fixture integrity -------------------------------------------------------

describe("fixture integrity", () => {
  const corpusIds = new Set(corpus.chunks.map((c) => c.id));

  test("all gold ids exist in the corpus", () => {
    for (const c of [...devCases, ...heldoutCases]) {
      for (const g of c.gold) {
        expect(corpusIds.has(g.chunk_id)).toBe(true);
      }
    }
  });

  test("every case has a grade-3 primary", () => {
    for (const c of [...devCases, ...heldoutCases]) {
      expect(Math.max(...c.gold.map((g) => g.grade))).toBe(3);
    }
  });

  test("dev and held-out queries are disjoint", () => {
    const devQ = new Set(devCases.map((c) => c.query));
    const holdQ = new Set(heldoutCases.map((c) => c.query));
    for (const q of holdQ) expect(devQ.has(q)).toBe(false);
  });

  test("split case counts meet the minimum", () => {
    expect(devCases.length).toBeGreaterThanOrEqual(30);
    expect(heldoutCases.length).toBeGreaterThanOrEqual(20);
  });

  test("corpus size is in the expected range", () => {
    expect(corpusIds.size).toBeGreaterThanOrEqual(15);
    expect(corpusIds.size).toBeLessThanOrEqual(40);
  });

  test("case ids are unique", () => {
    const ids = [...devCases, ...heldoutCases].map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

// --- Determinism -------------------------------------------------------------

describe("determinism", () => {
  test("each method ranks identically twice and returns a full permutation", () => {
    const index = buildIndex();
    const query = "How long does an access token last before it expires?";
    for (const method of METHODS) {
      const first = index.rank(method, query);
      const second = index.rank(method, query);
      expect(first).toEqual(second);
      expect(new Set(first)).toEqual(new Set(index.ids));
      expect(first.length).toBe(index.ids.length);
    }
  });

  test("embedding is deterministic and L2-normalised", () => {
    const v1 = embed("token bucket rate limit", 256, 3);
    const v2 = embed("token bucket rate limit", 256, 3);
    expect(v1).toEqual(v2);
    const normSq = v1.reduce((a, x) => a + x * x, 0);
    expect(normSq).toBeCloseTo(1.0, 12);
  });

  test("dense and bm25 disagree on at least one case", () => {
    const index = buildIndex();
    let disagreements = 0;
    for (const c of devCases) {
      const d = index.dense(c.query).slice(0, 5);
      const b = index.bm25(c.query).slice(0, 5);
      if (JSON.stringify(d) !== JSON.stringify(b)) disagreements += 1;
    }
    expect(disagreements).toBeGreaterThan(0);
  });

  test("tokenize splits on non-alphanumeric runs", () => {
    expect(tokenize("X-RateLimit-Remaining: 42!")).toEqual([
      "x",
      "ratelimit",
      "remaining",
      "42",
    ]);
  });
});

// --- End-to-end evaluation shape ---------------------------------------------

describe("evaluateSplit + buildReport", () => {
  test("reports every method with in-range metrics and version provenance", () => {
    const index = buildIndex();
    const result = evaluateSplit(index, devCases, 5, 1);
    const report = buildReport("dev", 5, manifest as never, result, devCases.length, 1);

    for (const method of METHODS) {
      const m = report.metrics[method];
      expect(m.recall_at_k).toBeGreaterThanOrEqual(0);
      expect(m.recall_at_k).toBeLessThanOrEqual(1);
      expect(m.mrr).toBeGreaterThanOrEqual(0);
      expect(m.mrr).toBeLessThanOrEqual(1);
      expect(m.ndcg_at_k).toBeGreaterThanOrEqual(0);
      expect(m.ndcg_at_k).toBeLessThanOrEqual(1);
    }
    expect(report.versions.corpus_version).toBe("aurora-docs-v1");
    for (const key of [
      "chunker_version",
      "embedder_version",
      "index_version",
      "bm25_version",
      "hybrid_version",
      "reranker_version",
    ]) {
      expect(report.versions[key]).toBeTruthy();
    }
    expect(report.k).toBe(5);
  });

  test("failure report flags the hard dense case hold-05", () => {
    const index = buildIndex();
    const result = evaluateSplit(index, heldoutCases, 5, 1);
    const denseFailures = new Set(result.failures.dense.map((f) => f.case_id));
    expect(denseFailures.has("hold-05")).toBe(true);
  });
});

// --- Golden byte-parity regression lock --------------------------------------
//
// The committed goldens (fixtures/golden/*.golden) are byte-identical across the
// Python and TypeScript ports. These tests regenerate the report and the
// per-case rankings and assert byte-equality, so any ranking or serialization
// drift in either implementation fails deterministically.

describe("golden byte-parity", () => {
  const k = manifest.default_k;
  const threshold = rubric.relevant_threshold ?? 1;
  const splits = [
    ["dev", devCases],
    ["heldout", heldoutCases],
  ] as const;

  test("report serialisation byte-matches the committed golden", () => {
    const index = buildIndex();
    for (const [split, cases] of splits) {
      const result = evaluateSplit(index, cases, k, threshold);
      const report = buildReport(
        split,
        k,
        manifest as never,
        result,
        cases.length,
        threshold,
      );
      expect(serializeReport(report)).toBe(loadGolden(`report_${split}_k${k}.golden`));
    }
  });

  test("per-case rankings byte-match the committed golden", () => {
    const index = buildIndex();
    for (const [split, cases] of splits) {
      expect(serializeCanonical(allRankings(index, cases))).toBe(
        loadGolden(`rankings_${split}.golden`),
      );
    }
  });
});

// --- Metric fail-fast on malformed (duplicate) rankings ----------------------

describe("metrics reject duplicate ranked ids", () => {
  test("recallAtK(['a','a'],['a'],2) throws instead of returning 2", () => {
    expect(() => recallAtK(["a", "a"], ["a"], 2)).toThrow();
  });
  test("dcgAtK rejects duplicate ranked ids", () => {
    const grades = new Map([["a", 3]]);
    expect(() => dcgAtK(["a", "a"], grades, 2)).toThrow();
  });
  test("ndcgAtK rejects duplicate ranked ids (would otherwise exceed 1)", () => {
    const grades = new Map([["a", 3]]);
    expect(() => ndcgAtK(["a", "a"], grades, 2)).toThrow();
  });
});

// --- Fixture validation: comprehensive provenance binding --------------------

describe("fixture validation", () => {
  const corpusIds = new Set(corpus.chunks.map((c) => c.id));
  const RUBRIC_ID = "graded-relevance-v1";
  const CORPUS_VERSION = "aurora-docs-v1";
  const CHUNK = "auth-api-keys";

  const mkCase = (
    gold: Array<{ chunk_id: string; grade: number }>,
    rubricId = RUBRIC_ID,
  ): BenchCase => ({ id: "x", query: "q", gold, why_sufficient: "", rubric: rubricId });

  const validCase = (id: string, query: string): BenchCase => ({
    id,
    query,
    gold: [{ chunk_id: CHUNK, grade: 3 }],
    why_sufficient: "",
    rubric: RUBRIC_ID,
  });

  const splitObj = (split: string, cases: BenchCase[]): CasesFixture => ({
    split,
    corpus_version: CORPUS_VERSION,
    rubric: RUBRIC_ID,
    cases,
  });

  test("accepts the real fixtures", () => {
    expect(() =>
      validateFixtures(
        corpus,
        manifest,
        rubric,
        new Map([
          ["dev", loadFixture<CasesFixture>("cases_dev.json")],
          ["heldout", loadFixture<CasesFixture>("cases_heldout.json")],
        ]),
      ),
    ).not.toThrow();
  });

  // -- per-case --------------------------------------------------------------

  test("rejects an out-of-range grade (4)", () => {
    expect(() =>
      validateCase(
        mkCase([
          { chunk_id: CHUNK, grade: 3 },
          { chunk_id: "auth-oauth", grade: 4 },
        ]),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects a negative grade", () => {
    expect(() =>
      validateCase(
        mkCase([
          { chunk_id: CHUNK, grade: 3 },
          { chunk_id: "auth-oauth", grade: -1 },
        ]),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects a non-integer grade", () => {
    expect(() =>
      validateCase(
        mkCase([
          { chunk_id: CHUNK, grade: 3 },
          { chunk_id: "auth-oauth", grade: 2.5 },
        ]),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects duplicate gold ids within a case", () => {
    expect(() =>
      validateCase(
        mkCase([
          { chunk_id: CHUNK, grade: 3 },
          { chunk_id: CHUNK, grade: 1 },
        ]),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects an unknown gold chunk id", () => {
    expect(() =>
      validateCase(
        mkCase([
          { chunk_id: CHUNK, grade: 3 },
          { chunk_id: "zzz", grade: 1 },
        ]),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects a mismatched rubric id", () => {
    expect(() =>
      validateCase(
        mkCase([{ chunk_id: CHUNK, grade: 3 }], "other-rubric-v9"),
        corpusIds,
        0,
        3,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("rejects a case with no primary (grade-3) evidence", () => {
    expect(() =>
      validateCase(mkCase([{ chunk_id: CHUNK, grade: 1 }]), corpusIds, 0, 3, RUBRIC_ID),
    ).toThrow();
  });

  test("rejects an empty query", () => {
    const c: BenchCase = {
      id: "x",
      query: "   ",
      gold: [{ chunk_id: CHUNK, grade: 3 }],
      why_sufficient: "",
      rubric: RUBRIC_ID,
    };
    expect(() => validateCase(c, corpusIds, 0, 3, RUBRIC_ID)).toThrow();
  });

  test("accepts a valid case", () => {
    expect(() =>
      validateCase(mkCase([{ chunk_id: CHUNK, grade: 3 }]), corpusIds, 0, 3, RUBRIC_ID),
    ).not.toThrow();
  });

  // -- per-split provenance --------------------------------------------------

  test("rejects a swapped split label (heldout loaded as dev)", () => {
    expect(() =>
      validateSplit(
        splitObj("heldout", [validCase("d1", "q1")]),
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  test("rejects a missing split field", () => {
    expect(() =>
      validateSplit(
        { corpus_version: CORPUS_VERSION, rubric: RUBRIC_ID, cases: [] },
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  test("rejects a corpus_version mismatch on a split", () => {
    expect(() =>
      validateSplit(
        { split: "dev", corpus_version: "WRONG", rubric: RUBRIC_ID, cases: [] },
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  test("rejects a mismatched rubric id on a split", () => {
    expect(() =>
      validateSplit(
        { split: "dev", corpus_version: CORPUS_VERSION, rubric: "other-v9", cases: [] },
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  test("rejects a duplicate case id within a split", () => {
    expect(() =>
      validateSplit(
        splitObj("dev", [validCase("d1", "q1"), validCase("d1", "q2")]),
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  test("rejects a duplicate query within a split", () => {
    expect(() =>
      validateSplit(
        splitObj("dev", [validCase("d1", "same"), validCase("d2", "same")]),
        corpusIds,
        CORPUS_VERSION,
        [0, 3],
        RUBRIC_ID,
        "dev",
      ),
    ).toThrow();
  });

  // -- cross-split + top-level provenance ------------------------------------

  test("rejects a cross-split duplicate query", () => {
    const m = new Map<string, CasesFixture>([
      ["dev", splitObj("dev", [validCase("d1", "shared query")])],
      ["heldout", splitObj("heldout", [validCase("h1", "shared query")])],
    ]);
    expect(() => validateFixtures(corpus, manifest, rubric, m)).toThrow();
  });

  test("rejects a cross-split duplicate case id", () => {
    const m = new Map<string, CasesFixture>([
      ["dev", splitObj("dev", [validCase("dup", "q-dev")])],
      ["heldout", splitObj("heldout", [validCase("dup", "q-held")])],
    ]);
    expect(() => validateFixtures(corpus, manifest, rubric, m)).toThrow();
  });

  test("rejects a swapped split file at the fixtures level", () => {
    const m = new Map<string, CasesFixture>([
      ["dev", loadFixture<CasesFixture>("cases_heldout.json")],
      ["heldout", loadFixture<CasesFixture>("cases_dev.json")],
    ]);
    expect(() => validateFixtures(corpus, manifest, rubric, m)).toThrow();
  });

  // -- corpus / rubric / manifest metadata -----------------------------------

  test("validateCorpus rejects a duplicate chunk id", () => {
    expect(() =>
      validateCorpus({
        version: "v",
        chunks: [
          { id: "a", text: "t" },
          { id: "a", text: "u" },
        ],
      }),
    ).toThrow();
  });

  test("validateCorpus rejects empty chunk text", () => {
    expect(() =>
      validateCorpus({ version: "v", chunks: [{ id: "a", text: "   " }] }),
    ).toThrow();
  });

  test("validateRubric rejects an out-of-range threshold", () => {
    expect(() => validateRubric({ ...rubric, relevant_threshold: 9 })).toThrow();
  });

  test("validateManifest rejects a bad default_k", () => {
    expect(() =>
      validateManifest({ ...manifest, default_k: 0 }, CORPUS_VERSION, RUBRIC_ID),
    ).toThrow();
  });

  test("validateManifest rejects an out-of-range bm25.b", () => {
    expect(() =>
      validateManifest(
        { ...manifest, bm25: { ...manifest.bm25, b: 1.5 } },
        CORPUS_VERSION,
        RUBRIC_ID,
      ),
    ).toThrow();
  });

  test("validateManifest rejects a corpus_version mismatch", () => {
    expect(() => validateManifest(manifest, "WRONG-VERSION", RUBRIC_ID)).toThrow();
  });
});
