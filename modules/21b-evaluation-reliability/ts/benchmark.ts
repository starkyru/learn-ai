/**
 * benchmark.ts — pure evaluation + reporting logic for Module 21b, Task 1.
 *
 * No filesystem access and no `import.meta` here, so this module loads cleanly
 * under both jest (CommonJS) and tsx (ESM). The CLI wrapper `run.ts` handles
 * reading the fixtures and writing the report.
 */

import { ndcgAtK, recallAtK, reciprocalRank } from "./metrics.js";
import { METHODS, type Method, RetrievalIndex } from "./retrieval.js";

export interface Gold {
  chunk_id: string;
  grade: number;
}

export interface BenchCase {
  id: string;
  query: string;
  gold: Gold[];
  why_sufficient: string;
  rubric: string;
}

export interface TopEntry {
  chunk_id: string;
  grade: number;
  is_gold: boolean;
}

export interface CaseEval {
  case_id: string;
  query: string;
  method: Method;
  recall_at_k: number;
  reciprocal_rank: number;
  ndcg_at_k: number;
  top_k: TopEntry[];
  missing_gold: string[];
  failure?: "missing_gold" | "misranked_gold";
}

export interface MethodMetrics {
  recall_at_k: number;
  mrr: number;
  ndcg_at_k: number;
  num_cases: number;
  num_failures: number;
}

export interface SplitResult {
  metrics: Record<Method, MethodMetrics>;
  failures: Record<Method, CaseEval[]>;
}

// --- Fixture validation (runs before any evaluation) -------------------------
//
// Every provenance/metadata field is bound before a single metric is computed:
// corpus version + unique non-empty chunks; rubric id + grade range + threshold;
// manifest cross-refs (versions, default_k, embedder/bm25/hybrid/reranker params);
// per-split label + corpus_version + rubric id; per-case id/query/rubric/gold and
// the primary-grade contract; and global uniqueness of case ids and queries so a
// swapped, mislabeled, or duplicated fixture cannot reach the release population.

export interface CorpusFixture {
  version: string;
  chunks: Array<{ id: string; text: string }>;
}

export interface RubricFixture {
  id: string;
  grades: Array<{ grade: number }>;
  relevant_threshold?: number;
}

export interface CasesFixture {
  split?: string;
  corpus_version?: string;
  rubric?: string;
  cases: BenchCase[];
}

export interface ManifestFixture {
  benchmark?: unknown;
  manifest_version?: unknown;
  corpus_version?: unknown;
  rubric?: unknown;
  default_k?: unknown;
  embedder?: { dim?: unknown; ngram?: unknown; version?: unknown };
  bm25?: { k1?: unknown; b?: unknown; version?: unknown };
  hybrid?: { rrf_k?: unknown; version?: unknown };
  reranker?: { candidates?: unknown; phrase_weight?: unknown; version?: unknown };
  [key: string]: unknown;
}

function requirePositiveInt(value: unknown, name: string): void {
  if (typeof value !== "number" || !Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer, got ${String(value)}`);
  }
}

function requireNumber(value: unknown, name: string): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    throw new Error(`${name} must be a number, got ${String(value)}`);
  }
  return value;
}

function requireNonEmptyString(value: unknown, name: string): void {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`${name} must be a non-empty string, got ${String(value)}`);
  }
}

/** Lowest/highest grade the rubric declares (e.g. [0, 3]). */
export function rubricGradeRange(rubric: RubricFixture): [number, number] {
  const grades = rubric.grades.map((g) => g.grade);
  if (grades.length === 0) throw new Error("rubric declares no grades");
  return [Math.min(...grades), Math.max(...grades)];
}

/** Bind the rubric id, grade range, and relevant_threshold. */
export function validateRubric(rubric: RubricFixture): {
  rubricId: string;
  range: [number, number];
} {
  requireNonEmptyString(rubric.id, "rubric.id");
  const range = rubricGradeRange(rubric);
  const [gradeMin, gradeMax] = range;
  const threshold = rubric.relevant_threshold;
  if (
    typeof threshold !== "number" ||
    !Number.isInteger(threshold) ||
    threshold < gradeMin ||
    threshold > gradeMax
  ) {
    throw new Error(
      `rubric.relevant_threshold ${String(threshold)} outside grade range [${gradeMin}, ${gradeMax}]`,
    );
  }
  return { rubricId: rubric.id, range };
}

export function validateCorpus(corpus: CorpusFixture): Set<string> {
  const ids: string[] = [];
  for (const chunk of corpus.chunks) {
    requireNonEmptyString(chunk.id, "corpus chunk id");
    requireNonEmptyString(chunk.text, `corpus chunk ${chunk.id} text`);
    ids.push(chunk.id);
  }
  if (new Set(ids).size !== ids.length) {
    throw new Error("corpus contains duplicate chunk ids");
  }
  return new Set(ids);
}

/** Bind the manifest cross-refs the report and retrieval config depend on. */
export function validateManifest(
  manifest: ManifestFixture,
  corpusVersion: string,
  rubricId: string,
): void {
  requireNonEmptyString(manifest.benchmark, "manifest.benchmark");
  requireNonEmptyString(manifest.manifest_version, "manifest.manifest_version");
  if (manifest.corpus_version !== corpusVersion) {
    throw new Error(
      `manifest corpus_version ${String(manifest.corpus_version)} != corpus version ${corpusVersion}`,
    );
  }
  if (manifest.rubric !== rubricId) {
    throw new Error(
      `manifest rubric ${String(manifest.rubric)} != rubric id ${rubricId}`,
    );
  }
  requirePositiveInt(manifest.default_k, "manifest.default_k");
  for (const block of [
    "chunker",
    "embedder",
    "index",
    "bm25",
    "hybrid",
    "reranker",
  ] as const) {
    const sub = manifest[block];
    if (sub === null || typeof sub !== "object") {
      throw new Error(`manifest.${block} block is missing`);
    }
    requireNonEmptyString(
      (sub as { version?: unknown }).version,
      `manifest.${block}.version`,
    );
  }
  requirePositiveInt(manifest.embedder?.dim, "manifest.embedder.dim");
  requirePositiveInt(manifest.embedder?.ngram, "manifest.embedder.ngram");
  requireNumber(manifest.bm25?.k1, "manifest.bm25.k1");
  const b = requireNumber(manifest.bm25?.b, "manifest.bm25.b");
  if (b < 0 || b > 1) throw new Error(`manifest.bm25.b must be in [0, 1], got ${b}`);
  requirePositiveInt(manifest.hybrid?.rrf_k, "manifest.hybrid.rrf_k");
  requirePositiveInt(manifest.reranker?.candidates, "manifest.reranker.candidates");
  requireNumber(manifest.reranker?.phrase_weight, "manifest.reranker.phrase_weight");
}

export function validateCase(
  c: BenchCase,
  corpusIds: ReadonlySet<string>,
  gradeMin: number,
  gradeMax: number,
  rubricId: string,
): void {
  // The primary grade is the rubric's highest declared grade (read from the
  // rubric, not hardcoded): every case must carry at least one such chunk.
  const primaryGrade = gradeMax;
  requireNonEmptyString(c.id, "case id");
  requireNonEmptyString(c.query, `${c.id}: query`);
  if (c.rubric !== rubricId) {
    throw new Error(`${c.id}: rubric ${c.rubric} != declared ${rubricId}`);
  }
  if (c.gold.length === 0) throw new Error(`${c.id}: no gold evidence`);
  const goldIds = c.gold.map((g) => g.chunk_id);
  if (new Set(goldIds).size !== goldIds.length) {
    throw new Error(`${c.id}: duplicate gold chunk id`);
  }
  for (const g of c.gold) {
    if (!Number.isInteger(g.grade)) {
      throw new Error(`${c.id}: grade ${g.grade} is not an integer`);
    }
    if (g.grade < gradeMin || g.grade > gradeMax) {
      throw new Error(
        `${c.id}: grade ${g.grade} outside rubric range [${gradeMin}, ${gradeMax}]`,
      );
    }
    if (!corpusIds.has(g.chunk_id)) {
      throw new Error(`${c.id}: unknown gold chunk ${g.chunk_id}`);
    }
  }
  if (!c.gold.some((g) => g.grade === primaryGrade)) {
    throw new Error(
      `${c.id}: no primary evidence (needs a grade-${primaryGrade} chunk)`,
    );
  }
}

export function validateSplit(
  casesObj: CasesFixture,
  corpusIds: ReadonlySet<string>,
  corpusVersion: string,
  range: [number, number],
  rubricId: string,
  expectedSplit: string,
): void {
  if (casesObj.split !== expectedSplit) {
    throw new Error(
      `split label ${String(casesObj.split)} != expected ${expectedSplit}`,
    );
  }
  if (casesObj.corpus_version !== corpusVersion) {
    throw new Error(
      `split ${expectedSplit}: corpus_version ${casesObj.corpus_version} != corpus ${corpusVersion}`,
    );
  }
  if (casesObj.rubric !== rubricId) {
    throw new Error(
      `split ${expectedSplit}: rubric ${casesObj.rubric} != declared ${rubricId}`,
    );
  }
  const [gradeMin, gradeMax] = range;
  for (const c of casesObj.cases)
    validateCase(c, corpusIds, gradeMin, gradeMax, rubricId);
  const ids = casesObj.cases.map((c) => c.id);
  if (new Set(ids).size !== ids.length) {
    throw new Error(`split ${expectedSplit}: duplicate case id`);
  }
  const queries = casesObj.cases.map((c) => c.query);
  if (new Set(queries).size !== queries.length) {
    throw new Error(`split ${expectedSplit}: duplicate query`);
  }
}

export function validateFixtures(
  corpus: CorpusFixture,
  manifest: ManifestFixture,
  rubric: RubricFixture,
  casesBySplit: ReadonlyMap<string, CasesFixture>,
): void {
  const corpusIds = validateCorpus(corpus);
  const { rubricId, range } = validateRubric(rubric);
  validateManifest(manifest, corpus.version, rubricId);

  const allIds: string[] = [];
  const allQueries: string[] = [];
  for (const [expectedSplit, casesObj] of casesBySplit) {
    validateSplit(casesObj, corpusIds, corpus.version, range, rubricId, expectedSplit);
    for (const c of casesObj.cases) {
      allIds.push(c.id);
      allQueries.push(c.query);
    }
  }
  if (new Set(allIds).size !== allIds.length) {
    throw new Error("duplicate case id across splits");
  }
  if (new Set(allQueries).size !== allQueries.length) {
    throw new Error("duplicate query across splits");
  }
}

function relevantIds(c: BenchCase, threshold: number): Set<string> {
  return new Set(c.gold.filter((g) => g.grade >= threshold).map((g) => g.chunk_id));
}

function gradeMap(c: BenchCase): Map<string, number> {
  return new Map(c.gold.map((g) => [g.chunk_id, g.grade]));
}

export function evaluateCase(
  index: RetrievalIndex,
  method: Method,
  c: BenchCase,
  k: number,
  threshold: number,
): CaseEval {
  const ranked = index.rank(method, c.query);
  const relevant = relevantIds(c, threshold);
  const grades = gradeMap(c);

  const topIds = ranked.slice(0, k);
  const top_k: TopEntry[] = topIds.map((cid) => ({
    chunk_id: cid,
    grade: grades.get(cid) ?? 0.0,
    is_gold: relevant.has(cid),
  }));
  const topSet = new Set(topIds);
  const missing_gold = [...relevant].filter((cid) => !topSet.has(cid)).sort();

  return {
    case_id: c.id,
    query: c.query,
    method,
    recall_at_k: recallAtK(ranked, relevant, k),
    reciprocal_rank: reciprocalRank(ranked, relevant),
    ndcg_at_k: ndcgAtK(ranked, grades, k),
    top_k,
    missing_gold,
  };
}

/** A non-gold chunk ranked above a gold chunk within the top-k. */
function hasInversion(topK: readonly TopEntry[]): boolean {
  let seenNonGold = false;
  for (const entry of topK) {
    if (entry.is_gold && seenNonGold) return true;
    if (!entry.is_gold) seenNonGold = true;
  }
  return false;
}

export function classifyFailure(
  e: CaseEval,
): "missing_gold" | "misranked_gold" | undefined {
  if (e.missing_gold.length > 0) return "missing_gold";
  if (hasInversion(e.top_k)) return "misranked_gold";
  return undefined;
}

/** Full ranked chunk-id list per method per case (for the golden lock). */
export function allRankings(
  index: RetrievalIndex,
  cases: readonly BenchCase[],
): Record<Method, Record<string, string[]>> {
  const out = {} as Record<Method, Record<string, string[]>>;
  for (const method of METHODS) {
    const perCase: Record<string, string[]> = {};
    for (const c of cases) perCase[c.id] = index.rank(method, c.query);
    out[method] = perCase;
  }
  return out;
}

export function evaluateSplit(
  index: RetrievalIndex,
  cases: readonly BenchCase[],
  k: number,
  threshold: number,
): SplitResult {
  const metrics = {} as Record<Method, MethodMetrics>;
  const failures = {} as Record<Method, CaseEval[]>;

  for (const method of METHODS) {
    const evals = cases.map((c) => evaluateCase(index, method, c, k, threshold));
    const n = evals.length || 1;
    const sum = (pick: (e: CaseEval) => number) =>
      evals.reduce((a, e) => a + pick(e), 0);
    const methodFailures: CaseEval[] = [];
    for (const e of evals) {
      const reason = classifyFailure(e);
      if (reason !== undefined) methodFailures.push({ ...e, failure: reason });
    }
    metrics[method] = {
      recall_at_k: sum((e) => e.recall_at_k) / n,
      mrr: sum((e) => e.reciprocal_rank) / n,
      ndcg_at_k: sum((e) => e.ndcg_at_k) / n,
      num_cases: evals.length,
      num_failures: methodFailures.length,
    };
    failures[method] = methodFailures;
  }

  return { metrics, failures };
}

export interface Report {
  benchmark: string;
  split: string;
  k: number;
  relevant_threshold: number;
  num_cases: number;
  versions: Record<string, string>;
  metrics: Record<Method, MethodMetrics>;
  failures: Record<Method, CaseEval[]>;
}

export interface ReportManifest {
  benchmark: string;
  manifest_version: string;
  corpus_version: string;
  chunker: { version: string };
  embedder: { version: string };
  index: { version: string };
  bm25: { version: string };
  hybrid: { version: string };
  reranker: { version: string };
  rubric: string;
  [key: string]: unknown;
}

/** A fully deterministic report (no wall-clock timestamp) for CI diffing. */
export function buildReport(
  split: string,
  k: number,
  manifest: ReportManifest,
  result: SplitResult,
  numCases: number,
  threshold: number,
): Report {
  return {
    benchmark: manifest.benchmark,
    split,
    k,
    relevant_threshold: threshold,
    num_cases: numCases,
    versions: {
      manifest_version: manifest.manifest_version,
      corpus_version: manifest.corpus_version,
      chunker_version: manifest.chunker.version,
      embedder_version: manifest.embedder.version,
      index_version: manifest.index.version,
      bm25_version: manifest.bm25.version,
      hybrid_version: manifest.hybrid.version,
      reranker_version: manifest.reranker.version,
      rubric: manifest.rubric,
    },
    metrics: result.metrics,
    failures: result.failures,
  };
}

/** Recursively sort object keys (arrays keep their order) to match Python's
 * `sort_keys=True`, so the two reports serialise byte-for-byte identically. */
function sortKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeysDeep);
  if (value !== null && typeof value === "object") {
    const source = value as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(source).sort()) out[key] = sortKeysDeep(source[key]);
    return out;
  }
  return value;
}

/**
 * Canonical JSON for any structure: sorted keys and a trailing newline.
 * JavaScript already renders whole-number floats as ints (`1`, `3`), which the
 * Python writer mirrors, so the output is byte-for-byte identical across ports.
 */
export function serializeCanonical(value: unknown): string {
  return `${JSON.stringify(sortKeysDeep(value), null, 2)}\n`;
}

/** Canonical JSON for a report (see {@link serializeCanonical}). */
export function serializeReport(report: Report): string {
  return serializeCanonical(report);
}

function pad(value: string, width: number): string {
  return value.length >= width ? value : " ".repeat(width - value.length) + value;
}

export function formatTable(k: number, metrics: Record<Method, MethodMetrics>): string {
  const header = `${"method".padEnd(10)} ${pad(`Recall@${k}`, 10)} ${pad("MRR", 8)} ${pad(
    `NDCG@${k}`,
    10,
  )} ${pad("fails", 6)}`;
  const lines = [header, "-".repeat(header.length)];
  for (const method of METHODS) {
    const m = metrics[method];
    lines.push(
      `${method.padEnd(10)} ${pad(m.recall_at_k.toFixed(3), 10)} ${pad(
        m.mrr.toFixed(3),
        8,
      )} ${pad(m.ndcg_at_k.toFixed(3), 10)} ${pad(String(m.num_failures), 6)}`,
    );
  }
  return lines.join("\n");
}

export function formatFailures(failures: Record<Method, CaseEval[]>): string {
  const lines: string[] = [];
  for (const method of METHODS) {
    const methodFailures = failures[method];
    if (methodFailures.length === 0) {
      lines.push(`[${method}] no failures`);
      continue;
    }
    lines.push(`[${method}] ${methodFailures.length} failing case(s):`);
    for (const f of methodFailures) {
      const top = f.top_k.map((t) => `${t.chunk_id}${t.is_gold ? "*" : ""}`).join(", ");
      const detail =
        f.missing_gold.length > 0
          ? `missing=[${f.missing_gold.join(", ")}]`
          : "mis-ranked";
      lines.push(
        `  - ${f.case_id} (${f.failure}): "${f.query}" ` +
          `[ndcg=${f.ndcg_at_k.toFixed(3)}] ${detail}; top-k: ${top}`,
      );
    }
  }
  return lines.join("\n");
}
