/**
 * Task 1 🔴 — Parse and validate an OKF bundle (no YAML library).
 *
 * What you'll learn:
 *   - An OKF (Open Knowledge Format) bundle is just a directory of markdown
 *     files with YAML frontmatter. There is no SDK, no query language, no
 *     service: `cat` is a valid client, and so is an LLM.
 *   - A concept's IDENTITY is its path: the concept id is the file's path inside
 *     the bundle with the `.md` suffix removed (`metrics/daily_revenue.md` →
 *     `metrics/daily_revenue`). Rename the file and you have renamed the concept.
 *   - `index.md` and `log.md` are RESERVED filenames — a directory listing and a
 *     changelog. They are not concepts and must be skipped at EVERY level.
 *   - `type` is the only always-required frontmatter key. A concept carrying just
 *     `type` is fully conformant; everything else is recommended or optional.
 *
 * 🔴 lane: parse the frontmatter YOURSELF. No `js-yaml` — the point is that the
 * format is simple enough that you can. Real bundles need a real parser; this
 * bundle deliberately sticks to the documented "OKF-lite" subset:
 *
 *     key: scalar                # string
 *     key: [a, b, c]             # flow list of strings
 *     key:                       # nested map (2-space indent)
 *       sub: scalar
 *     key:                       # list of maps (2-space indent, `- ` on first key)
 *       - sub: scalar
 *         sub2: scalar
 *
 * No comments, no block scalars, no quoting rules, no type coercion (every
 * scalar stays a string). Two indent levels, that's it.
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/01-parse-bundle.ts
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const BUNDLE_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "bundle",
);

/** Filenames the spec reserves — never concepts. */
export const RESERVED_NAMES = new Set(["index.md", "log.md"]);

/** The three value shapes OKF-lite frontmatter can hold. */
export type MetaValue =
  | string
  | string[]
  | Record<string, string>
  | Record<string, string>[]
  | null;
export type Meta = Record<string, MetaValue>;

/** One OKF concept: its id, its parsed frontmatter, and its markdown body. */
export interface Concept {
  id: string;
  meta: Meta;
  body: string;
}

// ---------------------------------------------------------------------------
// Narrowing helpers  (provided — do not edit)
// ---------------------------------------------------------------------------

/** A frontmatter scalar, or `fallback` when absent / not a scalar. */
export function asString(value: MetaValue | undefined, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

/** A flow list (`tags: [a, b]`), or `[]`. */
export function asStrings(value: MetaValue | undefined): string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string")
    ? (value as string[])
    : [];
}

/** A nested map (`generated:` → `{ by, at }`), or `{}`. */
export function asMap(value: MetaValue | undefined): Record<string, string> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, string>)
    : {};
}

/** A list of maps (`sources:` → `[{ resource, title }]`), or `[]`. */
export function asMaps(value: MetaValue | undefined): Record<string, string>[] {
  return Array.isArray(value) && value.every((v) => typeof v === "object")
    ? (value as Record<string, string>[])
    : [];
}

/** Every `*.md` path under `root`, recursively, sorted. (provided) */
export function walkMarkdown(root: string): string[] {
  const found: string[] = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) found.push(...walkMarkdown(full));
    else if (entry.name.endsWith(".md")) found.push(full);
  }
  return found.sort();
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Split an OKF document into its frontmatter and its markdown body.
 *
 * The document starts with a `---` fence line, then the OKF-lite YAML shown in
 * the header, then a closing `---`, then the body. Scalars stay strings; a
 * `[a, b]` value becomes a `string[]`; an indented `sub: value` block becomes a
 * nested object; an indented `- sub: value` block becomes an array of objects
 * (further-indented keys belong to the item the last `- ` opened).
 *
 * Throw an `Error` when the document has no opening fence or the fence is never
 * closed — a caller needs to tell "not a concept" from "broken concept".
 *
 * TODO: implement.
 *   - Split on newlines. The first line must be the opening fence; find the
 *     index of the next `---` line after it (that is the closing fence).
 *   - The body is everything after the closing fence (trim the leading blank
 *     line so bodies start at real content).
 *   - Walk the lines BETWEEN the fences, skipping blank ones, and branch on the
 *     indent width (0 vs deeper) and on whether the trimmed line starts with
 *     `- `. Splitting one `key: value` line: find the first `:` with
 *     `indexOf(":")` and slice around it (NOT `split(":")` — values contain
 *     colons, e.g. `bigquery://…` and ISO timestamps).
 *   - Track the most recent top-level key so an indented line knows which
 *     container it belongs to.
 */
export function parseFrontmatter(_text: string): { meta: Meta; body: string } {
  // TODO: parse the OKF-lite frontmatter into { meta, body }
  throw new Error("TODO: implement parseFrontmatter()");
}

/**
 * The concept id for a file: its bundle-relative posix path, minus `.md`.
 *
 * TODO: implement.
 *   - `path.relative(root, file)` gives the relative path; normalise the
 *     separators to `/` so the id is the same on Windows.
 *   - Strip exactly the trailing `.md`.
 */
export function conceptId(_root: string, _file: string): string {
  // TODO: derive the concept id from the file path
  throw new Error("TODO: implement conceptId()");
}

/**
 * Every concept in the bundle, sorted by id, reserved filenames skipped.
 *
 * TODO: implement.
 *   - Use the provided `walkMarkdown(root)` so nested directories are included.
 *   - Skip files whose BASENAME is in RESERVED_NAMES (at any depth).
 *   - Parse each remaining file (`fs.readFileSync(file, "utf8")`) into a
 *     `Concept` via parseFrontmatter() and conceptId().
 */
export function loadBundle(_root: string): Concept[] {
  // TODO: walk the bundle and build the Concept list
  throw new Error("TODO: implement loadBundle()");
}

/**
 * Conformance errors, one human-readable string each (empty array = valid).
 *
 * Two rules, both from the spec:
 *   - `type` is required and must be non-empty.
 *   - concept ids are unique within a bundle.
 *
 * Each message must name the offending concept id so the report is actionable.
 *
 * TODO: implement.
 *   - Collect a message for any concept whose `meta` has no usable `type`.
 *   - Track the ids you have seen and report a duplicate the second time it
 *     appears.
 */
export function validate(_concepts: Concept[]): string[] {
  // TODO: return the list of conformance errors
  throw new Error("TODO: implement validate()");
}

// ---------------------------------------------------------------------------
// Broken documents  (provided — do not edit)
// ---------------------------------------------------------------------------

// Inline fixtures: your parser and validator must reject each of these, and the
// rejection must be a clean error — never a crash and never a silent pass.
const BAD_NO_FENCE = "# Just a markdown file\n\nNo frontmatter here.\n";
const BAD_UNTERMINATED = "---\ntype: table\ntitle: Never closed\n\n# Body\n";
const BAD_NO_TYPE =
  "---\ntitle: Typeless\ndescription: Missing the one required key.\n---\n\n# Body\n";

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

const EXPECTED_IDS = [
  "customers",
  "legacy_orders_v1",
  "metrics/daily_revenue",
  "orders",
  "promo_codes",
  "revenue_dashboard",
];

export function check(label: string, ok: boolean): boolean {
  console.log(`  [${ok ? "x" : " "}] ${label}`);
  return ok;
}

function main(): void {
  console.log("\n=== Task 1: parse + validate an OKF bundle ===\n");

  const concepts = loadBundle(BUNDLE_DIR);
  console.log(`loaded ${concepts.length} concepts from bundle/:`);
  for (const c of concepts) {
    console.log(
      `  ${c.id.padEnd(24)} type=${asString(c.meta.type, "?").padEnd(10)} tags=${JSON.stringify(asStrings(c.meta.tags))}`,
    );
  }

  const errors = validate(concepts);
  console.log(
    `\nconformance errors: ${errors.length ? JSON.stringify(errors) : "none"}`,
  );

  const orders = concepts.find((c) => c.id === "orders");
  console.log("\norders frontmatter:");
  if (orders) {
    for (const [key, value] of Object.entries(orders.meta)) {
      console.log(`  ${key.padEnd(12)} ${JSON.stringify(value)}`);
    }
  }

  const rejections: Record<string, string> = {};
  for (const [name, doc] of [
    ["no-fence", BAD_NO_FENCE],
    ["unterminated", BAD_UNTERMINATED],
  ] as const) {
    try {
      parseFrontmatter(doc);
      rejections[name] = "ACCEPTED (bug)";
    } catch (err) {
      rejections[name] = `Error: ${(err as Error).message}`;
    }
  }
  const typeless = parseFrontmatter(BAD_NO_TYPE);
  const typelessErrors = validate([{ id: "typeless", meta: typeless.meta, body: "" }]);
  console.log("\nbroken documents:");
  for (const [name, outcome] of Object.entries(rejections)) {
    console.log(`  ${name.padEnd(14)} ${outcome}`);
  }
  console.log(`  no-type        ${JSON.stringify(typelessErrors)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  const okIds =
    JSON.stringify(concepts.map((c) => c.id)) === JSON.stringify(EXPECTED_IDS);
  const okReserved = concepts.every((c) => !/(^|\/)(index|log)$/.test(c.id));
  const okValid = errors.length === 0;
  const sources = orders ? asMaps(orders.meta.sources) : [];
  const okMeta =
    !!orders &&
    asString(orders.meta.type) === "table" &&
    JSON.stringify(asStrings(orders.meta.tags)) === JSON.stringify(["sales", "core"]) &&
    asMap(orders.meta.generated).by === "reference_agent/llama3.2" &&
    sources.length === 2 &&
    sources[0].resource === "warehouse/ddl/orders.sql" &&
    sources[0].title === "Orders DDL" &&
    asMaps(orders.meta.verified)[0]?.by === "human:learner";
  const okBody =
    !!orders &&
    orders.body.startsWith("# Orders") &&
    !orders.body.includes("type: table");
  const okRejects = Object.values(rejections).every((o) => o.startsWith("Error:"));
  const okTypeless = typelessErrors.length === 1 && typelessErrors[0].includes("type");

  console.log("\nAcceptance:");
  const all = [
    check(
      `loads exactly ${EXPECTED_IDS.length} concepts, ids sorted as expected`,
      okIds,
    ),
    check("reserved index.md / log.md files are skipped at every level", okReserved),
    check("the shipped bundle is conformant (no errors)", okValid),
    check("nested map, list-of-maps, and flow list all parsed (orders)", okMeta),
    check("the body excludes the frontmatter and starts at '# Orders'", okBody),
    check("no-fence and unterminated documents throw", okRejects),
    check("a document without `type` is reported by validate()", okTypeless),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

// Only run the harness when this file IS the entrypoint — later tasks import it.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
