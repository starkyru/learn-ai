/**
 * Task 3 🟡 — Trust: provenance, lifecycle status, and staleness.
 *
 * What you'll learn:
 *   - Retrieval that only asks "is this relevant?" will happily cite a
 *     deprecated table, a snapshot that expired last quarter, or a paragraph no
 *     human has ever read. OKF puts those signals in QUERYABLE frontmatter so
 *     the filter is a few lines of code instead of a research project:
 *       * `status`      draft | stable | deprecated  (lifecycle)
 *       * `stale_after` a date after which the content is not trustworthy
 *       * `generated`   { by, at }        — who wrote it (agent or human)
 *       * `verified`    [{ by, at }, ...] — who signed it off
 *       * `sources`     what it was derived from
 *   - Freshness is a property of the KNOWLEDGE, not of the file. `promo_codes`
 *     has not changed in months and its file mtime is recent — it is still
 *     stale, because `stale_after` says the snapshot only described one quarter.
 *   - `draft` is not the same as untrusted, and `verified` is not the same as
 *     correct. Decide which signal your answer actually needs, then say why in
 *     the citation.
 *   - Every drop needs a REASON naming the field that caused it. A filter that
 *     silently returns fewer results is indistinguishable from a broken one.
 *
 * Determinism: `now` is passed in as an ISO date string. Never call `Date.now()`
 * here — the acceptance checks pin two different "nows".
 *
 * Prerequisite: Task 1 (this file imports your `loadBundle`).
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/03-trust-gating.ts
 */

import { pathToFileURL } from "node:url";
import {
  asMap,
  asMaps,
  asString,
  BUNDLE_DIR,
  check,
  loadBundle,
  type Concept,
  type Meta,
} from "./01-parse-bundle";

/** The two "todays" the harness evaluates the same bundle against. */
const NOW = "2026-07-01";
const EARLIER = "2026-05-01";

export type Drop = [id: string, reason: string];

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * True when this concept's `stale_after` date has passed.
 *
 * A concept with no `stale_after` never goes stale on its own — absence of the
 * key means "no expiry declared", not "expired".
 *
 * TODO: implement.
 *   - Read `stale_after` from `meta` (`asString`); return false when empty.
 *   - Compare it against `now` as DATES, not strings — `Date.parse` on a
 *     `YYYY-MM-DD` string gives you a comparable number. Stale means the expiry
 *     is strictly before `now`, so a concept is still fresh on its
 *     `stale_after` day.
 */
export function isStale(_meta: Meta, _now: string): boolean {
  // TODO: decide whether this concept has expired
  throw new Error("TODO: implement isStale()");
}

/**
 * Split concepts into trusted and dropped, where dropped carries a reason.
 *
 * Return `{ kept, dropped }`, both in the input order. Each reason must NAME the
 * frontmatter key that caused the drop — `status`, `stale_after`, or `verified`
 * — so the report says which rule fired.
 *
 * Apply the rules in this order (strongest, most permanent first), so a concept
 * that trips several is reported under the most fundamental one:
 *   1. `status: deprecated`  → dropped, always. It may be fresh and verified and
 *      is still the wrong answer to every question.
 *   2. stale (`isStale`)     → dropped.
 *   3. `requireVerified` and no `verified` entry → dropped.
 * Everything else is kept — including `status: draft`, which is a lifecycle
 * stage, not a trust verdict.
 *
 * TODO: implement.
 *   - Walk the concepts once, test the three rules in the documented order, and
 *     push to `kept` or to `dropped` with a reason string that includes the
 *     deciding key (and the useful value, e.g. the expiry date). `asMaps` turns
 *     `verified` into an array you can test for emptiness.
 */
export function trustFilter(
  _concepts: Concept[],
  _now: string,
  _requireVerified: boolean,
): { kept: Concept[]; dropped: Drop[] } {
  // TODO: gate the concepts on lifecycle, freshness, and verification
  throw new Error("TODO: implement trustFilter()");
}

/**
 * A one-line citation: what this claim is, and who stands behind it.
 *
 * This is the string you would append to a generated answer, so it has to
 * survive being read on its own. Include the concept id, its `type`, its
 * `status`, who `generated` it, and who `verified` it (or say plainly that
 * nobody did).
 *
 * TODO: implement.
 *   - Read `type`, `status`, `asMap(meta.generated).by`, and the first
 *     `asMaps(meta.verified)` entry's `by` (all optional — use defaults).
 *   - Return one line; make the unverified case explicit rather than blank.
 */
export function provenance(_concept: Concept): string {
  // TODO: render the provenance citation line
  throw new Error("TODO: implement provenance()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

// Which frontmatter key must appear in each drop's reason, at NOW with
// requireVerified=true. Note WHY each one is dropped: legacy_orders_v1 is
// verified and fresh (status decides), promo_codes is verified (the expiry
// decides), revenue_dashboard is fresh and not deprecated (verification decides).
const EXPECTED_DROPS: Record<string, string> = {
  legacy_orders_v1: "status",
  promo_codes: "stale_after",
  revenue_dashboard: "verified",
};
const EXPECTED_KEPT = ["customers", "metrics/daily_revenue", "orders"];

function main(): void {
  console.log("\n=== Task 3: trust gating on provenance, status, and staleness ===\n");

  const concepts = loadBundle(BUNDLE_DIR);
  const strict = trustFilter(concepts, NOW, true);
  const loose = trustFilter(concepts, NOW, false);
  const earlier = trustFilter(concepts, EARLIER, false);

  const show = (title: string, r: { kept: Concept[]; dropped: Drop[] }) => {
    console.log(title);
    console.log(`  kept:    ${JSON.stringify(r.kept.map((c) => c.id))}`);
    for (const [id, reason] of r.dropped)
      console.log(`  dropped: ${id.padEnd(22)} ${reason}`);
    console.log();
  };

  show(`now=${NOW}, requireVerified=true`, strict);
  show(`now=${NOW}, requireVerified=false`, loose);
  show(`now=${EARLIER}, requireVerified=false`, earlier);

  console.log("citations for the trusted set:");
  for (const c of strict.kept) console.log(`  ${provenance(c)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  const okKept =
    JSON.stringify(strict.kept.map((c) => c.id)) === JSON.stringify(EXPECTED_KEPT);
  const okDropped =
    JSON.stringify(strict.dropped.map(([id]) => id)) ===
    JSON.stringify(Object.keys(EXPECTED_DROPS));
  const okReasons = strict.dropped.every(([id, reason]) =>
    reason.includes(EXPECTED_DROPS[id]),
  );
  const okFlag =
    JSON.stringify(loose.kept.map((c) => c.id)) ===
    JSON.stringify([...EXPECTED_KEPT, "revenue_dashboard"].sort());
  const okTime =
    JSON.stringify(earlier.kept.map((c) => c.id)) ===
      JSON.stringify([...EXPECTED_KEPT, "promo_codes", "revenue_dashboard"].sort()) &&
    JSON.stringify(earlier.dropped.map(([id]) => id)) ===
      JSON.stringify(["legacy_orders_v1"]);
  const ordersCitation = provenance(concepts.find((c) => c.id === "orders")!);
  const okCitation =
    ordersCitation.includes("orders") &&
    ordersCitation.includes("reference_agent/llama3.2") &&
    ordersCitation.includes("human:learner");
  // Freshness comes from the frontmatter, never the filesystem.
  const okNotMtime = isStale({ stale_after: "2026-06-30" }, NOW) && !isStale({}, NOW);
  console.log("\nAcceptance:");
  const all = [
    check(`trusted set at ${NOW} is exactly ${JSON.stringify(EXPECTED_KEPT)}`, okKept),
    check("the other three are dropped, in rule order", okDropped),
    check(
      "each drop reason names the deciding key (status / stale_after / verified)",
      okReasons,
    ),
    check(
      "requireVerified=false re-admits the unverified draft, and only that",
      okFlag,
    ),
    check(
      `at ${EARLIER} the promo snapshot is fresh again (same files, different now)`,
      okTime,
    ),
    check("the citation names the generating agent AND the human verifier", okCitation),
    check(
      "staleness comes from `stale_after`, and no expiry means never stale",
      okNotMtime,
    ),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
