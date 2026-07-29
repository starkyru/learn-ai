/**
 * Task 4 🔴 — The bundle is a graph: link extraction and 1-hop expansion.
 *
 * What you'll learn:
 *   - OKF is "graph-shaped, not just tree-shaped". The directory hierarchy is
 *     one view; the markdown links between concepts are the real structure. A
 *     link from A to B asserts a RELATIONSHIP — the kind (joins-with,
 *     derived-from, supersedes) lives in the surrounding prose, not in the link.
 *   - Two link forms resolve to a concept id: bundle-relative `/orders.md`
 *     (start from the bundle root — recommended, and the only form that survives
 *     a file being moved into a subdirectory) and relative `./orders.md`.
 *   - Retrieval over a cheap index has a blind spot: a fact whose concept shares
 *     no words with the question is unreachable, however good your ranker is.
 *     One hop along the links reaches it — this is GraphRAG's core move
 *     (module 05b) with the graph already written down for you.
 *   - Links rot. A target that does not resolve is a finding to REPORT, not a
 *     crash and not a silent skip.
 *
 * 🔴 lane: build the adjacency yourself — no graph library. Treat a link as an
 * undirected relationship when expanding (neighbours = out-links ∪ in-links):
 * `orders` never links to `promo_codes`, but `promo_codes` links to `orders`,
 * and that is exactly as much of a relationship in the other direction.
 *
 * Prerequisites: Task 1 (`loadBundle`) and Task 2 (`rankByIndex`).
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/04-link-graph.ts
 */

import { pathToFileURL } from "node:url";
import { BUNDLE_DIR, check, loadBundle, type Concept } from "./01-parse-bundle";
import { conceptBlock, countTokens, rankByIndex } from "./02-progressive-disclosure";

/** How many index-search hits seed the expansion. */
const SEED_K = 2;
/** A fact that exists in exactly one concept body, and in no index line. */
const NEEDLE = "412,900";

export type Graph = Record<string, string[]>;
export type Dangling = [source: string, target: string];

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Every concept id this body links to, in document order.
 *
 * `conceptId` is the linking concept's own id — you need it to resolve a
 * relative link from a nested concept (a `./x.md` inside
 * `metrics/daily_revenue` means `metrics/x`).
 *
 * Keep only links to concepts: skip external URLs (anything with `://`),
 * in-page anchors, `mailto:`, and any target that is not a `.md` file. Strip a
 * trailing `#anchor`. Turn the surviving target into an id by dropping the
 * leading `/` (bundle-relative) or the `./` plus prefixing the linking
 * concept's directory (relative), then dropping `.md`.
 *
 * TODO: implement.
 *   - Find markdown link targets with a global regex over `[text](target)` and
 *     capture only the target (`String.prototype.matchAll`).
 *   - Filter out the non-concept targets listed above.
 *   - Resolve the two accepted forms to ids; the linking concept's directory is
 *     everything before its last `/` (empty at the bundle root).
 */
export function extractLinks(_conceptId: string, _body: string): string[] {
  // TODO: extract and resolve the outgoing concept links
  throw new Error("TODO: implement extractLinks()");
}

/**
 * The out-edge adjacency plus every dangling link.
 *
 * Return `{ edges, dangling }` where `edges` maps every concept id to its
 * sorted, de-duplicated array of resolvable targets (an isolated concept maps to
 * an empty array — the key must still be present), and `dangling` is a sorted
 * array of `[sourceId, unresolvedTarget]` pairs.
 *
 * TODO: implement.
 *   - Build the set of real concept ids first; that set is what makes a link
 *     resolvable.
 *   - For each concept, split `extractLinks(...)` into resolvable targets and
 *     dangling pairs.
 *   - Sort + de-duplicate both so the graph is deterministic.
 */
export function buildGraph(_concepts: Concept[]): {
  edges: Graph;
  dangling: Dangling[];
} {
  // TODO: build the adjacency and collect dangling links
  throw new Error("TODO: implement buildGraph()");
}

/**
 * Every concept one link away, in EITHER direction.
 *
 * TODO: implement.
 *   - Start from this concept's own out-edges.
 *   - Add every concept whose out-edges contain `conceptId` (the in-edges). You
 *     are scanning the adjacency for that; a reverse index would be the
 *     optimisation, and is not needed at this size.
 */
export function neighbours(_edges: Graph, _conceptId: string): Set<string> {
  // TODO: union of out-links and in-links
  throw new Error("TODO: implement neighbours()");
}

/**
 * The seed set plus everything within `hops` links of it, sorted.
 *
 * Breadth-first: hop 1 adds the seeds' neighbours, hop 2 adds THOSE neighbours,
 * and so on. A concept already reached is never re-expanded, so the walk
 * terminates even though the graph has cycles.
 *
 * TODO: implement.
 *   - Keep a `seen` Set (starts as the seeds) and a `frontier` Set.
 *   - Per hop: union the frontier's `neighbours`, remove anything already in
 *     `seen`, add the remainder to `seen`, and make it the next frontier.
 *   - Return the sorted ids.
 */
export function expand(_edges: Graph, _seeds: string[], _hops = 1): string[] {
  // TODO: breadth-first expansion over the link graph
  throw new Error("TODO: implement expand()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

// A question whose answer lives in a concept that the index search CANNOT find:
// nothing in that concept's title, description, or tags mentions the date, the
// order volume, or the jump.
const QUESTION = "Why did order volume jump on 2026-05-17?";

const EXPECTED_EDGES: Graph = {
  customers: ["orders"],
  legacy_orders_v1: ["orders"],
  "metrics/daily_revenue": ["orders", "promo_codes"],
  orders: ["customers", "metrics/daily_revenue"],
  promo_codes: ["orders"],
  revenue_dashboard: ["metrics/daily_revenue", "promo_codes"],
};
const EXPECTED_DANGLING: Dangling[] = [["revenue_dashboard", "warehouse/missing"]];
const EXPECTED_SEEDS = ["orders", "legacy_orders_v1"];
const EXPECTED_EXPANDED = [
  "customers",
  "legacy_orders_v1",
  "metrics/daily_revenue",
  "orders",
  "promo_codes",
];

function contextFor(concepts: Concept[], ids: string[]): string {
  const byId = new Map(concepts.map((c) => [c.id, c]));
  return ids
    .map((id) => byId.get(id))
    .filter((c): c is Concept => !!c)
    .map(conceptBlock)
    .join("\n\n");
}

function main(): void {
  console.log("\n=== Task 4: the link graph and 1-hop expansion ===\n");

  const concepts = loadBundle(BUNDLE_DIR);
  const { edges, dangling } = buildGraph(concepts);

  console.log("link graph (out-edges):");
  for (const id of Object.keys(edges).sort()) {
    console.log(`  ${id.padEnd(24)} -> ${JSON.stringify(edges[id])}`);
  }
  console.log(`\ndangling links: ${JSON.stringify(dangling)}`);

  const ranked = rankByIndex(concepts, QUESTION);
  const seeds = ranked
    .filter(([, score]) => score > 0)
    .slice(0, SEED_K)
    .map(([id]) => id);
  const expanded = expand(edges, seeds, 1);

  const seedCtx = contextFor(concepts, seeds);
  const expandedCtx = contextFor(concepts, expanded);

  console.log(`\nquestion: ${QUESTION}`);
  console.log(
    `  index ranking:  ${ranked
      .slice(0, 4)
      .map(([id, s]) => `${id}:${s.toFixed(3)}`)
      .join("  ")}`,
  );
  console.log(
    `  seeds:          ${JSON.stringify(seeds)}  (${countTokens(seedCtx)} tokens)`,
  );
  console.log(
    `  after 1 hop:    ${JSON.stringify(expanded)}  (${countTokens(expandedCtx)} tokens)`,
  );
  console.log(`  needle in the seed context:     ${seedCtx.includes(NEEDLE)}`);
  console.log(`  needle in the expanded context: ${expandedCtx.includes(NEEDLE)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  const okEdges =
    JSON.stringify(Object.keys(edges).sort()) ===
      JSON.stringify(Object.keys(EXPECTED_EDGES).sort()) &&
    Object.keys(EXPECTED_EDGES).every(
      (id) => JSON.stringify(edges[id]) === JSON.stringify(EXPECTED_EDGES[id]),
    );
  const okDangling = JSON.stringify(dangling) === JSON.stringify(EXPECTED_DANGLING);
  const okSeeds = JSON.stringify(seeds) === JSON.stringify(EXPECTED_SEEDS);
  const okNeedleMissing = !seedCtx.includes(NEEDLE);
  const okNeedleFound = expandedCtx.includes(NEEDLE);
  const okExpanded = JSON.stringify(expanded) === JSON.stringify(EXPECTED_EXPANDED);
  const okSelective = !expanded.includes("revenue_dashboard");
  // promo_codes links TO orders; orders never links to it — reaching it proves
  // in-links count as relationships.
  const okInlinks =
    expanded.includes("promo_codes") && !edges.orders.includes("promo_codes");
  const oneHop = expand(edges, ["revenue_dashboard"], 1);
  const twoHop = expand(edges, ["revenue_dashboard"], 2);
  const okHops =
    JSON.stringify(oneHop) ===
      JSON.stringify(["metrics/daily_revenue", "promo_codes", "revenue_dashboard"]) &&
    JSON.stringify(twoHop.filter((id) => !oneHop.includes(id))) ===
      JSON.stringify(["orders"]);

  console.log("\nAcceptance:");
  const all = [
    check(
      "both link forms resolve — bundle-relative /x.md and relative ./x.md",
      okEdges,
    ),
    check("the one dangling link is reported, not crashed on", okDangling),
    check(
      `index search seeds ${JSON.stringify(EXPECTED_SEEDS)} and misses the answer concept`,
      okSeeds && okNeedleMissing,
    ),
    check("1-hop expansion reaches the concept holding the needle fact", okNeedleFound),
    check("the expanded set is exactly the seeds' neighbourhood", okExpanded),
    check("expansion is selective — revenue_dashboard is NOT pulled in", okSelective),
    check("expansion follows in-links as well as out-links", okInlinks),
    check("hops is respected: a 2-hop walk reaches exactly one more concept", okHops),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
