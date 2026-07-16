/**
 * metrics.ts — retrieval metrics implemented from scratch (Module 21b, Task 1).
 *
 * These measure the RETRIEVER, before any generator runs. They are pure
 * functions of a ranked list of chunk ids plus the gold labels, so they are
 * deterministic and trivially unit-testable against hand-computed values.
 *
 * Conventions (kept identical to the Python port):
 *
 * - Recall@k = (relevant chunks in the top k) / (all relevant chunks). The
 *   caller passes the relevant set (grade >= rubric threshold).
 * - Reciprocal Rank = 1 / (rank of the first relevant chunk), rank from 1; 0 if
 *   none appears within the optional cutoff k. MRR is the mean over queries.
 * - NDCG@k uses exponential gain (2**grade - 1) and log discount
 *   1 / log2(rank + 1) with rank from 1, normalised by the ideal DCG.
 */

/**
 * Fail fast on a malformed ranking with duplicate ids. A retriever must return
 * each chunk at most once; duplicates would inflate Recall
 * (recallAtK(["a","a"], ["a"], 2) -> 2) and let NDCG exceed 1.
 */
function requireUnique(rankedIds: readonly string[]): void {
  if (new Set(rankedIds).size !== rankedIds.length) {
    throw new Error("rankedIds must not contain duplicates");
  }
}

export function recallAtK(
  rankedIds: readonly string[],
  relevantIds: Iterable<string>,
  k: number,
): number {
  if (k <= 0) throw new Error("k must be a positive integer");
  requireUnique(rankedIds);
  const relevant = new Set(relevantIds);
  if (relevant.size === 0) return 0.0;
  let found = 0;
  for (const cid of rankedIds.slice(0, k)) {
    if (relevant.has(cid)) found += 1;
  }
  return found / relevant.size;
}

export function reciprocalRank(
  rankedIds: readonly string[],
  relevantIds: Iterable<string>,
  k?: number,
): number {
  if (k !== undefined && k <= 0) throw new Error("k must be a positive integer");
  requireUnique(rankedIds);
  const relevant = new Set(relevantIds);
  if (relevant.size === 0) return 0.0;
  const limit = k === undefined ? rankedIds.length : Math.min(k, rankedIds.length);
  for (let position = 0; position < limit; position += 1) {
    if (relevant.has(rankedIds[position])) return 1.0 / (position + 1);
  }
  return 0.0;
}

export function meanReciprocalRank(
  results: Iterable<readonly [readonly string[], Iterable<string>]>,
  k?: number,
): number {
  const ranks: number[] = [];
  for (const [ranked, relevant] of results) {
    ranks.push(reciprocalRank(ranked, relevant, k));
  }
  if (ranks.length === 0) return 0.0;
  return ranks.reduce((a, b) => a + b, 0) / ranks.length;
}

export function dcgAtK(
  rankedIds: readonly string[],
  grades: ReadonlyMap<string, number>,
  k: number,
): number {
  if (k <= 0) throw new Error("k must be a positive integer");
  requireUnique(rankedIds);
  let total = 0.0;
  const top = rankedIds.slice(0, k);
  for (let i = 0; i < top.length; i += 1) {
    const grade = grades.get(top[i]) ?? 0.0;
    const gain = 2.0 ** grade - 1.0;
    total += gain / Math.log2(i + 2); // position is i+1, discount log2(position+1)
  }
  return total;
}

export function ndcgAtK(
  rankedIds: readonly string[],
  grades: ReadonlyMap<string, number>,
  k: number,
): number {
  const actual = dcgAtK(rankedIds, grades, k);
  const idealOrder = [...grades.keys()].sort(
    (a, b) => (grades.get(b) ?? 0) - (grades.get(a) ?? 0),
  );
  const ideal = dcgAtK(idealOrder, grades, k);
  if (ideal === 0.0) return 0.0;
  return actual / ideal;
}
