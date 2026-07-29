/**
 * Task 2 🟡 — Progressive disclosure: pay for the index, not the bundle.
 *
 * What you'll learn:
 *   - OKF's `index.md` is not decoration, it is a CHEAP TABLE OF CONTENTS. One
 *     line per concept (title + description + tags + link) is a few tokens;
 *     the concept body is a few hundred. Load the index first, decide from it,
 *     then spend the remaining budget on the bodies you actually need.
 *   - That is the whole "progressive disclosure" idea module 16 spends its token
 *     budget on, except here the structure that makes it possible is already in
 *     the knowledge format: the queryable fields live in frontmatter, the
 *     expensive prose lives in the body, and the two are separable.
 *   - The failure mode of the naive alternative is not subtle: dumping the whole
 *     bundle costs ~10x the index and buries the answer in irrelevant prose
 *     ("lost in the middle", module 16).
 *
 * Token counting here is a WHITESPACE APPROXIMATION so the numbers are
 * deterministic and offline. Module 16 Task 1 counts precisely with tiktoken;
 * the budgeting discipline is identical either way.
 *
 * Prerequisite: Task 1 (this file imports your `loadBundle`).
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/02-progressive-disclosure.ts
 */

import { pathToFileURL } from "node:url";
import {
  asString,
  asStrings,
  BUNDLE_DIR,
  check,
  loadBundle,
  type Concept,
} from "./01-parse-bundle";

/** Hard context budget, in (approximate) tokens, for the assembled prompt. */
export const BUDGET = 250;

// ---------------------------------------------------------------------------
// Token counting + bag-of-words scoring  (provided — do not edit)
// ---------------------------------------------------------------------------

/** Approximate token count: whitespace-separated words. */
export function countTokens(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

/** Lowercase word tokens (letters/digits). */
function tokenize(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

function bagOfWords(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const tok of tokenize(text)) counts.set(tok, (counts.get(tok) ?? 0) + 1);
  return counts;
}

/** Cosine similarity over sparse count vectors (0 if either norm is 0). */
function cosine(a: Map<string, number>, b: Map<string, number>): number {
  let dot = 0;
  for (const [word, count] of a) dot += count * (b.get(word) ?? 0);
  const norm = (v: Map<string, number>) =>
    Math.sqrt([...v.values()].reduce((s, c) => s + c * c, 0));
  const na = norm(a);
  const nb = norm(b);
  return na === 0 || nb === 0 ? 0 : dot / (na * nb);
}

/** The expensive form of a concept: a heading plus its full body. */
export function conceptBlock(concept: Concept): string {
  return `## /${concept.id}.md\n${concept.body}`;
}

/** The naive baseline: the index AND every body, in id order. */
export function wholeBundleContext(concepts: Concept[]): string {
  const ordered = [...concepts].sort((a, b) => a.id.localeCompare(b.id));
  return buildIndex(concepts) + "\n\n" + ordered.map(conceptBlock).join("\n\n");
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * One index entry for a concept: the cheap, queryable summary of it.
 *
 * It must carry enough for a reader (human or model) to decide whether the body
 * is worth loading, and enough for a lexical search to match on: the `title`, a
 * bundle-relative markdown link to `/<id>.md`, the `description`, and the
 * `tags`. Fall back to the concept id when `title` is missing (remember: `type`
 * is the only required key).
 *
 * Keep the format stable — `buildIndex`, the ranker, and Task 4's seed search
 * all read these lines.
 *
 * TODO: implement.
 *   - Pull `title`, `description`, and `tags` out of `concept.meta` with the
 *     provided `asString` / `asStrings` helpers (they handle the fallbacks).
 *   - Return a single markdown list item — no trailing newline.
 */
export function indexLine(_concept: Concept): string {
  // TODO: build one index line for this concept
  throw new Error("TODO: implement indexLine()");
}

/**
 * The generated `index.md` body: one `indexLine` per concept, id-sorted.
 *
 * TODO: implement.
 *   - Sort by `Concept.id` (`localeCompare`) so the index is deterministic,
 *     then join the lines with newlines.
 */
export function buildIndex(_concepts: Concept[]): string {
  // TODO: assemble the index from the concept lines
  throw new Error("TODO: implement buildIndex()");
}

/**
 * Score every concept against the question USING ONLY ITS INDEX LINE.
 *
 * This is the point of the exercise: the ranker is not allowed to look at
 * bodies, because in a real bundle the bodies are the thing you have not paid
 * for yet. Return `[id, score]` pairs, best first.
 *
 * TODO: implement.
 *   - Vectorise the question once with `bagOfWords`.
 *   - Score each concept with `cosine` against `bagOfWords(indexLine(c))`.
 *   - Sort by score descending; break ties by concept id so the order is stable.
 */
export function rankByIndex(
  _concepts: Concept[],
  _question: string,
): [string, number][] {
  // TODO: rank concepts by index-line similarity
  throw new Error("TODO: implement rankByIndex()");
}

/**
 * Assemble a context under `budget` tokens: index first, then bodies.
 *
 * Return `{ context, chosen }` where `chosen` are the ids of the concepts whose
 * FULL BODY made it in, in the order you added them.
 *
 * The rules:
 *   - The index is always included, and it is charged against the budget.
 *   - Only concepts with a score above zero are candidates (an empty result
 *     beats a plausible-looking irrelevant one — module 06d's lesson).
 *   - Walk candidates best-first; add a body when it still fits; skip it when it
 *     does not and carry on down the list.
 *   - Never exceed `budget`.
 *
 * TODO: implement.
 *   - Start the parts array with `buildIndex(concepts)` and set `used` to its
 *     `countTokens`.
 *   - Build an id → Concept lookup (a `Map`) so you can fetch bodies by id.
 *   - Loop over `rankByIndex(...)`, skip non-positive scores, cost each
 *     candidate with `countTokens(conceptBlock(c))`, and only accept it while
 *     `used + cost` stays within `budget`.
 *   - Join the parts with a blank line between them.
 */
export function disclose(
  _concepts: Concept[],
  _question: string,
  _budget: number,
): { context: string; chosen: string[] } {
  // TODO: assemble the budgeted, index-first context
  throw new Error("TODO: implement disclose()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

// Each question is answered by exactly one concept in this bundle.
const QUESTIONS: [string, string][] = [
  ["Which table holds one row per customer order?", "orders"],
  ["Which promo codes are active and what are their redemption limits?", "promo_codes"],
  ["Where are takings aggregated per calendar day?", "metrics/daily_revenue"],
];

function main(): void {
  console.log("\n=== Task 2: progressive disclosure under a token budget ===\n");

  const concepts = loadBundle(BUNDLE_DIR);
  const index = buildIndex(concepts);
  const indexTokens = countTokens(index);
  const wholeTokens = countTokens(wholeBundleContext(concepts));

  console.log(`budget:            ${BUDGET} tokens`);
  console.log(`index only:        ${indexTokens} tokens (${concepts.length} concepts)`);
  console.log(`whole bundle:      ${wholeTokens} tokens`);
  console.log(
    `index is ${Math.round((indexTokens / wholeTokens) * 100)}% of the bundle\n`,
  );

  const results: { expected: string; tokens: number; chosen: string[] }[] = [];
  for (const [question, expected] of QUESTIONS) {
    const { context, chosen } = disclose(concepts, question, BUDGET);
    results.push({ expected, tokens: countTokens(context), chosen });
    const top = rankByIndex(concepts, question)
      .slice(0, 3)
      .map(([id, s]) => `${id}:${s.toFixed(3)}`);
    console.log(`q: ${question}`);
    console.log(`   ranking: ${top.join("  ")}`);
    console.log(
      `   disclosed: ${countTokens(context)} tokens, bodies=${JSON.stringify(chosen)}`,
    );
  }

  // ── Acceptance checks ────────────────────────────────────────────────────
  const okIndexCheap = indexTokens * 5 < wholeTokens;
  const okBaselineBlows = wholeTokens > 2 * BUDGET;
  const okUnderBudget = results.every((r) => r.tokens <= BUDGET);
  const okRightConcept = results.every((r) => r.chosen.includes(r.expected));
  const okIndexPresent = QUESTIONS.every(([q]) =>
    disclose(concepts, q, BUDGET).context.startsWith(index),
  );
  const okSelective = results.every((r) => r.chosen.length < concepts.length);
  // The ranker must not peek at bodies: the needle fact lives in a body only.
  const okIndexOnly = !indexLine(
    concepts.find((c) => c.id === "metrics/daily_revenue")!,
  ).includes("412,900");
  console.log("\nAcceptance:");
  const all = [
    check(
      `the index (${indexTokens}) is under a fifth of the bundle (${wholeTokens})`,
      okIndexCheap,
    ),
    check(
      `the whole-bundle baseline (${wholeTokens}) blows the ${BUDGET}-token budget`,
      okBaselineBlows,
    ),
    check(`every disclosed context fits in ${BUDGET} tokens`, okUnderBudget),
    check("each question disclosed the one concept that answers it", okRightConcept),
    check("the index is always present, and comes first", okIndexPresent),
    check("disclosure is selective — never all bodies", okSelective),
    check("index lines summarise frontmatter only — no body content", okIndexOnly),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
