/**
 * Task 5 🟢 — Produce a bundle: emit conformant OKF, then check your own output.
 *
 * What you'll learn:
 *   - Anyone can PRODUCE OKF: a human with an editor, an export pipeline, or an
 *     agent walking a database. The format is the contract, not the producer.
 *   - The division of labour that keeps generated knowledge trustworthy: the
 *     MODEL writes prose (title, description, tags), the CODE writes structure
 *     (`type`, `resource`, `generated.by`, `generated.at`). Never let the model
 *     invent the provenance of its own output.
 *   - Serialising frontmatter is the exact inverse of Task 1's parser, so the
 *     honest test is a ROUND TRIP: parse what you rendered and compare it to
 *     what you meant. A generator that cannot be re-read is not a generator.
 *   - `generated: { by, at }` is what makes a bundle auditable later: `by` uses
 *     the actor convention `<producer>/<version>` for agents, `human:<id>` for
 *     people, `process:<id>` for automation.
 *
 * Determinism: the timestamp is a fixed constant, not a clock read — a generator
 * whose output changes on every run cannot be diffed in git, which is half the
 * reason the format is files in the first place.
 *
 * Prerequisites: Task 1 (`parseFrontmatter`, `loadBundle`, `validate`) and
 * Task 2 (`buildIndex`).
 *
 * How to run:
 *   pnpm tsx modules/16b-knowledge-bundles/ts/05-produce-bundle.ts --stub
 *   pnpm tsx modules/16b-knowledge-bundles/ts/05-produce-bundle.ts
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { getProvider } from "@learn-ai/llm-core";
import {
  asMap,
  asString,
  check,
  loadBundle,
  parseFrontmatter,
  validate,
  type Meta,
} from "./01-parse-bundle";
import { buildIndex } from "./02-progressive-disclosure";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

const OUT_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "out-ts");

/** Stamped into every concept this generator writes (never read from a clock). */
const GENERATED_BY = "reference_agent/16b";
const GENERATED_AT = "2026-07-29T00:00:00Z";

// ---------------------------------------------------------------------------
// Raw input  (provided — do not edit)
// ---------------------------------------------------------------------------

// What a producer actually starts from: a name, a kind, a resource URI, and an
// unstructured dump. No titles, no descriptions, no tags — that is the gap the
// model fills.
interface RawTable {
  name: string;
  kind: string;
  resource: string;
  raw: string;
}

const RAW_TABLES: RawTable[] = [
  {
    name: "shipments",
    kind: "table",
    resource: "bigquery://acme-retail/warehouse/shipments",
    raw:
      "CREATE TABLE shipments (shipment_id STRING, order_id STRING, carrier STRING, " +
      "handed_over_at TIMESTAMP, delivered_at TIMESTAMP);\n" +
      "-- one row per parcel handed to a carrier; a cancelled order has no row",
  },
  {
    name: "returns",
    kind: "table",
    resource: "bigquery://acme-retail/warehouse/returns",
    raw:
      "CREATE TABLE returns (return_id STRING, order_id STRING, reason_code STRING, " +
      "refunded_cents INT64);\n" +
      "-- reason_code is a free-text-ish enum maintained by support, not analytics",
  },
  {
    name: "warehouse_zones",
    kind: "table",
    resource: "bigquery://acme-retail/ops/warehouse_zones",
    raw:
      "CREATE TABLE warehouse_zones (zone_id STRING, site STRING, temperature_c INT64);\n" +
      "-- chilled zones have temperature_c below 8; ambient zones are NULL",
  },
];

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

export interface Prose {
  title: string;
  description: string;
  tags: string[];
}

/**
 * Ask the model for the PROSE fields only, and validate what comes back.
 *
 * Return `{ title, description, tags }` and nothing else — the structural
 * fields are the caller's job, not the model's.
 *
 * Prompt the model to answer as a single JSON object with exactly those three
 * keys, and include the raw dump so it has something to describe (the offline
 * stub also looks for the table name in your prompt, so pass the raw text
 * through). Then parse the reply and reject anything malformed: a real model
 * will wrap JSON in prose sooner or later, and a silent `{}` here becomes a
 * conformance failure three steps downstream.
 *
 * TODO: implement.
 *   - Build the `Msg[]` asking for those three keys as JSON, with the raw dump
 *     included.
 *   - Call `chatFn`, then `JSON.parse` the reply — slice from the first `{` to
 *     the last `}` first if you want to tolerate a chatty model.
 *   - Validate: all three keys present, `title`/`description` non-empty
 *     strings, `tags` an array of strings. Throw otherwise.
 *   - Return only those three keys.
 */
export function describeConcept(_chatFn: ChatFn, _raw: RawTable): Prose {
  // TODO: get + validate the model-written prose fields
  throw new Error("TODO: implement describeConcept()");
}

/**
 * Serialise a metadata object back into the OKF-lite YAML of Task 1.
 *
 * The inverse of `parseFrontmatter`, and it must round-trip: parsing your output
 * has to return the object you started from. Handle the three shapes the subset
 * allows — a string scalar, a `string[]` (flow style `[a, b]`), and a nested
 * object (a block, two-space indent). Preserve key order.
 *
 * Do not emit the `---` fences here; that is `renderConcept`'s job.
 *
 * TODO: implement.
 *   - Walk `Object.entries(meta)` and branch on the value's shape
 *     (`Array.isArray`, then `typeof === "object"`).
 *   - Arrays render on one line; objects render as `key:` then one indented
 *     `sub: value` line per entry.
 *   - End with a newline so the closing fence lands on its own line.
 */
export function renderFrontmatter(_meta: Meta): string {
  // TODO: render the frontmatter block
  throw new Error("TODO: implement renderFrontmatter()");
}

/**
 * Errors in one rendered document — an empty array means conformant.
 *
 * This is the gate a generator runs on its OWN output before writing it:
 *   - it must parse (Task 1's `parseFrontmatter` throws if it does not);
 *   - `type` must be present (Task 1's `validate` rule);
 *   - `generated.by` and `generated.at` must both be stamped, or the concept is
 *     unauditable;
 *   - the body must be non-empty.
 *
 * Return human-readable messages; never throw.
 *
 * TODO: implement.
 *   - Call `parseFrontmatter(text)` in a try/catch and return the parse failure
 *     as a single message.
 *   - Reuse `validate` for the `type` and id rules by wrapping the parsed result
 *     in a `Concept`.
 *   - Add your own checks for the `generated` sub-keys (`asMap`) and the empty
 *     body.
 */
export function conformanceCheck(_text: string): string[] {
  // TODO: return the list of conformance errors for this rendered document
  throw new Error("TODO: implement conformanceCheck()");
}

// ---------------------------------------------------------------------------
// Rendering + the stub/real model  (provided — do not edit)
// ---------------------------------------------------------------------------

/** A full OKF document: fenced frontmatter, then the markdown body. */
export function renderConcept(meta: Meta, body: string): string {
  return `---\n${renderFrontmatter(meta)}---\n\n${body}`;
}

/** Structure from the producer, prose from the model, provenance from us. */
function buildMeta(raw: RawTable, prose: Prose): Meta {
  return {
    type: raw.kind,
    title: prose.title,
    description: prose.description,
    resource: raw.resource,
    tags: prose.tags,
    status: "draft",
    generated: { by: GENERATED_BY, at: GENERATED_AT },
  };
}

// The deterministic offline model: it finds the table name in the prompt and
// returns fixed JSON for it, so the acceptance checks are exact.
const STUB_PROSE: Record<string, Prose> = {
  shipments: {
    title: "Shipments",
    description: "One row per parcel handed to a carrier.",
    tags: ["logistics", "core"],
  },
  returns: {
    title: "Returns",
    description: "One row per returned order line, with refund amount.",
    tags: ["support", "core"],
  },
  warehouse_zones: {
    title: "Warehouse zones",
    description: "Storage zones per site, with chilled-zone temperatures.",
    tags: ["ops"],
  },
};

function makeStubChatFn(): ChatFn {
  return (messages) => {
    const prompt = messages[messages.length - 1].content;
    for (const [name, prose] of Object.entries(STUB_PROSE)) {
      if (prompt.includes(name)) return JSON.stringify(prose);
    }
    return "{}"; // nothing recognisable in the prompt — let validation fail
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or make describeConcept async and `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 5: produce an OKF bundle — ${mode} ===\n`);

  fs.rmSync(OUT_DIR, { recursive: true, force: true });
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const rendered: Record<string, string> = {};
  const roundTrips: Record<string, boolean> = {};
  const errors: Record<string, string[]> = {};
  for (const raw of RAW_TABLES) {
    const prose = describeConcept(chatFn, raw);
    const meta = buildMeta(raw, prose);
    const body = `# ${prose.title}\n\n${prose.description}\n\n\`\`\`sql\n${raw.raw}\n\`\`\`\n`;
    const document = renderConcept(meta, body);

    rendered[raw.name] = document;
    errors[raw.name] = conformanceCheck(document);
    roundTrips[raw.name] =
      JSON.stringify(parseFrontmatter(document).meta) === JSON.stringify(meta);

    fs.writeFileSync(path.join(OUT_DIR, `${raw.name}.md`), document);
    console.log(`wrote out-ts/${raw.name}.md  (${document.length} chars)`);
    console.log(
      `  round-trips: ${roundTrips[raw.name]}   conformance: ${
        errors[raw.name].length ? JSON.stringify(errors[raw.name]) : "ok"
      }`,
    );
  }

  // Produce the index too — the consumer side (Task 2) reads this first.
  const written = loadBundle(OUT_DIR);
  fs.writeFileSync(path.join(OUT_DIR, "index.md"), buildIndex(written) + "\n");
  console.log(`\nwrote out-ts/index.md (${written.length} concepts)`);
  console.log("\n--- out-ts/shipments.md ---");
  console.log(rendered.shipments);

  // A deliberately broken document: the generator must catch its own mistake.
  const brokenErrors = conformanceCheck(
    renderConcept({ title: "No type here" }, "# Body\n"),
  );
  const unauditableErrors = conformanceCheck(
    renderConcept({ type: "table", title: "No provenance" }, "# Body\n"),
  );
  console.log(`\nbroken document errors:      ${JSON.stringify(brokenErrors)}`);
  console.log(`unauditable document errors: ${JSON.stringify(unauditableErrors)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  if (!useStub) {
    console.log("\nRun with --stub for the exact acceptance checks.");
    return;
  }

  const okWritten =
    JSON.stringify(fs.readdirSync(OUT_DIR).sort()) ===
    JSON.stringify(["index.md", "returns.md", "shipments.md", "warehouse_zones.md"]);
  const okRoundTrip = Object.values(roundTrips).every(Boolean);
  const okConformant = Object.values(errors).every((e) => e.length === 0);
  const okLoadable =
    JSON.stringify(written.map((c) => c.id)) ===
    JSON.stringify(["returns", "shipments", "warehouse_zones"]);
  const okValid = validate(written).length === 0;
  const okProvenance = written.every(
    (c) =>
      asMap(c.meta.generated).by === GENERATED_BY &&
      asMap(c.meta.generated).at === GENERATED_AT,
  );
  const okProse = written.some(
    (c) => asString(c.meta.description) === STUB_PROSE.returns.description,
  );
  const okCatchesType = brokenErrors.some((e) => e.includes("type"));
  const okCatchesProvenance = unauditableErrors.some((e) => e.includes("generated"));

  console.log("\nAcceptance:");
  const all = [
    check("three concepts plus an index written to out-ts/", okWritten),
    check("every rendered document round-trips through Task 1's parser", okRoundTrip),
    check("every rendered document passes its own conformance check", okConformant),
    check(
      "the written bundle re-loads as 3 concepts and validates",
      okLoadable && okValid,
    ),
    check(
      "generated.by / generated.at are stamped by the code, not the model",
      okProvenance,
    ),
    check(
      "the model's prose (title/description/tags) made it into the frontmatter",
      okProse,
    ),
    check("a document missing `type` is caught by conformanceCheck", okCatchesType),
    check(
      "a document missing `generated` provenance is caught too",
      okCatchesProvenance,
    ),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
