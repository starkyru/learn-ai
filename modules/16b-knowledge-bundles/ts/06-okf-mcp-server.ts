/**
 * Task 6 🟢 — Serve the bundle over MCP (Model Context Protocol).
 *
 * What you'll learn:
 *   - Because a bundle is just files, serving it is a 3-tool MCP server: list,
 *     read, search. That is the whole interface Google's own reference
 *     implementation exposes over a markdown knowledge base (`list_contents`,
 *     `read_file`, `search_content`) — the format does the heavy lifting.
 *   - Progressive disclosure becomes the CLIENT's job once it is served: the
 *     model calls `list_concepts` (cheap), decides, then calls `read_concept`
 *     (expensive) only for what it needs. Task 2 did this in one process; MCP
 *     turns it into a protocol any agent can drive.
 *   - `search_concepts` returns line-level hits so a model can locate a fact
 *     without reading whole documents — the same "reference, then retrieve on
 *     demand" pattern as module 16's tool-output offloading.
 *
 * The three tools are ordinary functions with a `--selftest` path, so you can
 * get them right offline before any protocol is involved. Wiring them into an
 * MCP server is the last step.
 *
 * Wire it into Claude Code (or any MCP client) once it runs — add to `.mcp.json`
 * in the repo root:
 *
 *     {
 *       "mcpServers": {
 *         "okf-bundle": {
 *           "command": "pnpm",
 *           "args": ["tsx", "modules/16b-knowledge-bundles/ts/06-okf-mcp-server.ts"]
 *         }
 *       }
 *     }
 *
 * Prerequisite: Task 1 (`loadBundle`). TS deps: `@modelcontextprotocol/sdk`
 * (already in this module's package.json).
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/06-okf-mcp-server.ts --selftest
 *   pnpm tsx modules/16b-knowledge-bundles/ts/06-okf-mcp-server.ts
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { pathToFileURL } from "node:url";
import { BUNDLE_DIR, check, loadBundle } from "./01-parse-bundle";

export interface Hit {
  id: string;
  line: number;
  text: string;
}

// ---------------------------------------------------------------------------
// The three tools — YOU implement these
// ---------------------------------------------------------------------------

/**
 * Concept ids in the bundle, sorted; optionally restricted to a prefix.
 *
 * `prefix=""` lists everything; `prefix="metrics/"` lists one subdirectory.
 * This is the CHEAP call — ids only, no bodies.
 *
 * TODO: implement.
 *   - Load the bundle with `loadBundle(BUNDLE_DIR)` and return the ids that
 *     start with `prefix` (sorted; `loadBundle` already sorts).
 */
export function listConcepts(_prefix = ""): string[] {
  // TODO: list the concept ids under a prefix
  throw new Error("TODO: implement listConcepts()");
}

/**
 * The full document text for one concept id — frontmatter fences included.
 *
 * Return the file's text VERBATIM (not a re-render): a client that reads a
 * concept must see exactly what is on disk, provenance and all.
 *
 * Throw an `Error` naming the id when it does not exist — a served tool that
 * returns "" for a typo is a debugging trap.
 *
 * TODO: implement.
 *   - Map the id back to a path: `path.join(BUNDLE_DIR, `${conceptId}.md`)`.
 *   - Guard against a missing file, and against an id that escapes the bundle
 *     (a client-supplied `../../etc/passwd` must not be readable — resolve the
 *     path and confirm it still starts with the resolved BUNDLE_DIR).
 *   - Return `fs.readFileSync(file, "utf8")`.
 */
export function readConcept(_conceptId: string): string {
  // TODO: read one concept document verbatim
  throw new Error("TODO: implement readConcept()");
}

/**
 * Line-level, case-insensitive substring search across concept BODIES.
 *
 * Return up to `maxHits` hits `{ id, line, text }` where `line` is the 1-based
 * line number WITHIN THE BODY (frontmatter excluded, so the numbers line up
 * with what a reader sees after the fences) and `text` is the matching line,
 * trimmed.
 *
 * Order: by concept id, then by line number — deterministic, so a model gets
 * the same answer twice.
 *
 * TODO: implement.
 *   - Load the bundle; for each concept, split `Concept.body` on newlines and
 *     track a 1-based line number.
 *   - Compare lowercased line against lowercased query (`String.includes`).
 *   - Stop once you have `maxHits` results.
 */
export function searchConcepts(_query: string, _maxHits = 5): Hit[] {
  // TODO: search bodies and return line-level hits
  throw new Error("TODO: implement searchConcepts()");
}

// ---------------------------------------------------------------------------
// MCP server — YOU implement this
// ---------------------------------------------------------------------------

/**
 * Run the server over the stdio transport, exposing the three tools.
 *
 * TODO: implement (see module 17 Task 3 for the same shape).
 *   - Import the SDK DYNAMICALLY inside this function so `--selftest` still
 *     runs when the dependency is not installed:
 *       const { Server } = await import("@modelcontextprotocol/sdk/server/index.js");
 *       const { StdioServerTransport } = await import(".../server/stdio.js");
 *       const { CallToolRequestSchema, ListToolsRequestSchema } = await import(".../types.js");
 *   - Create the `Server` with a name/version and `{ capabilities: { tools: {} } }`.
 *   - `server.setRequestHandler(ListToolsRequestSchema, ...)` returning the three
 *     tools with JSON-Schema `inputSchema`s:
 *       * list_concepts   — optional "prefix" (string)
 *       * read_concept    — required "concept_id" (string)
 *       * search_concepts — required "query" (string), optional "max_hits"
 *     The descriptions matter: they are the only documentation the model gets.
 *     Say that list is cheap and read is expensive.
 *   - `server.setRequestHandler(CallToolRequestSchema, ...)` dispatching on
 *     `request.params.name`, calling the function above, and returning
 *     `{ content: [{ type: "text", text }] }`. Turn a thrown unknown-id error
 *     into an error message rather than letting it escape as a protocol error.
 *   - `await server.connect(new StdioServerTransport())`.
 */
export async function serve(): Promise<void> {
  // TODO: build and start the stdio MCP server
  throw new Error("TODO: implement serve()");
}

// ---------------------------------------------------------------------------
// Offline self-test  (provided — do not edit)
// ---------------------------------------------------------------------------

const EXPECTED_IDS = [
  "customers",
  "legacy_orders_v1",
  "metrics/daily_revenue",
  "orders",
  "promo_codes",
  "revenue_dashboard",
];

function selftest(): void {
  console.log(
    "\n=== Task 6: OKF over MCP — offline self-test of the three tools ===\n",
  );

  const allIds = listConcepts();
  const nested = listConcepts("metrics/");
  const document = readConcept("orders");
  const needleHits = searchConcepts("412,900");
  const settlementHits = searchConcepts("settlement", 10);
  const capped = searchConcepts("settlement", 1);
  const empty = searchConcepts("no-such-string-anywhere");

  let missingError = "RETURNED (bug)";
  try {
    readConcept("does_not_exist");
  } catch (err) {
    missingError = `Error: ${(err as Error).message}`;
  }
  let escapeError = "RETURNED (bug)";
  try {
    readConcept("../../../etc/passwd");
  } catch (err) {
    escapeError = `Error: ${(err as Error).message}`;
  }

  console.log(`listConcepts()           -> ${JSON.stringify(allIds)}`);
  console.log(`listConcepts('metrics/') -> ${JSON.stringify(nested)}`);
  console.log(
    `readConcept('orders')    -> ${document.length} chars, first line ${JSON.stringify(document.split("\n")[0])}`,
  );
  console.log(`search('412,900')        -> ${JSON.stringify(needleHits)}`);
  console.log(
    `search('settlement')     -> ${JSON.stringify(settlementHits.map((h) => [h.id, h.line]))}`,
  );
  console.log(`readConcept(missing)     -> ${missingError}`);
  console.log(`readConcept(escaping)    -> ${escapeError}`);

  const okList = JSON.stringify(allIds) === JSON.stringify(EXPECTED_IDS);
  const okPrefix = JSON.stringify(nested) === JSON.stringify(["metrics/daily_revenue"]);
  const okVerbatim =
    document.startsWith("---") &&
    document.includes("type: table") &&
    document.includes("# Orders");
  const okMissing =
    missingError.startsWith("Error:") && missingError.includes("does_not_exist");
  const okEscape = !escapeError.startsWith("RETURNED");
  const okNeedle =
    needleHits.length === 1 &&
    needleHits[0].id === "metrics/daily_revenue" &&
    needleHits[0].line === 7 &&
    needleHits[0].text.includes("412,900");
  const okMulti =
    settlementHits.length === 4 &&
    JSON.stringify([...new Set(settlementHits.map((h) => h.id))].sort()) ===
      JSON.stringify(["metrics/daily_revenue", "orders"]);
  const okCap = capped.length === 1;
  const okEmpty = empty.length === 0;

  console.log("\nAcceptance:");
  const all = [
    check("listConcepts() returns all 6 ids, sorted", okList),
    check("a prefix narrows the listing to the metrics/ subdirectory", okPrefix),
    check("readConcept returns the document verbatim, fences included", okVerbatim),
    check("an unknown id throws an error naming the id", okMissing),
    check("an id escaping the bundle root is refused", okEscape),
    check("search finds the needle at body line 7 of metrics/daily_revenue", okNeedle),
    check("search spans concepts: 4 'settlement' hits across 2 concepts", okMulti),
    check("maxHits caps the result set; a miss returns []", okCap && okEmpty),
  ];
  if (all.every(Boolean)) {
    console.log("\n  All acceptance checks passed.");
    console.log("  Now wire serve() up and point an MCP client at it.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

async function main(): Promise<void> {
  if (process.argv.includes("--selftest")) selftest();
  else await serve();
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)
  void main();
