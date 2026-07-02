/**
 * Task 3 🟡 — Entity memory + summary memory (with just-in-time expansion).
 *
 * What you'll learn:
 *   - Entity memory keys facts by WHO/WHAT (name + type), not by when they
 *     were said. Extraction is a model call that must return STRUCTURED output
 *     (a JSON array) — so you parse and validate, never trust.
 *   - Merging is update-on-write for entities: the same (name, type) updates
 *     the fact in place; a new name appends. Without it every mention of
 *     "Dana" piles up a duplicate, and the stale fact competes with the fresh.
 *   - Summary memory compresses old turns into one record — but it MARKS the
 *     originals (archivedBy = summaryId), it never deletes them. That is what
 *     makes just-in-time expansion possible: when the agent actually needs the
 *     detail, `expandSummary` recovers the originals verbatim.
 *
 * The records:
 *
 *     turn:    { seq: 3, role: "user", content: "...", archivedBy: null }
 *     entity:  { name: "Dana", type: "person", fact: "CEO of Acme Corp" }
 *     summary: { summaryId: "sum-1-4", text: "...", turnSeqs: [1, 2, 3, 4] }
 *
 * OFFLINE: takes `chatFn`. With --stub, extraction returns a fixed valid JSON
 * array and summarisation a fixed sentence, so assertions are exact; without
 * --stub the same prompts hit getProvider().chat (expect to harden the JSON
 * parsing for a real model!).
 *
 * How to run:
 *   pnpm tsx modules/06d-agent-memory/ts/03-entity-summary.ts --stub
 *   pnpm tsx modules/06d-agent-memory/ts/03-entity-summary.ts
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider } from "@learn-ai/llm-core";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

interface Turn {
  seq: number;
  role: string;
  content: string;
  archivedBy: string | null;
}
interface Entity {
  name: string;
  type: string;
  fact: string;
}
interface SummaryRecord {
  summaryId: string;
  text: string;
  turnSeqs: number[];
}
interface Store {
  turns: Turn[];
  entities: Entity[];
  summaries: SummaryRecord[];
}

const STATE_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "state",
);
const STORE_PATH = path.join(STATE_DIR, "ts-03-entity-summary.json");

const EXTRACT_PROMPT_PREFIX =
  "Extract entities from the text below. Return a JSON array of objects, " +
  'each with exactly the string keys "name", "type", "fact". ' +
  "Return the JSON array only, no prose.\n\nText: ";

const SUMMARY_PROMPT_PREFIX =
  "Summarise the following conversation turns in one short sentence:\n\n";

// ---------------------------------------------------------------------------
// JSON-file store  (provided — do not edit)
// ---------------------------------------------------------------------------

function newStore(): Store {
  return { turns: [], entities: [], summaries: [] };
}

function loadStore(storePath: string): Store {
  if (fs.existsSync(storePath))
    return JSON.parse(fs.readFileSync(storePath, "utf8")) as Store;
  return newStore();
}

function saveStore(storePath: string, store: Store): void {
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  fs.writeFileSync(storePath, JSON.stringify(store, null, 2));
}

/** Append a turn with the next seq number; not archived yet. */
function addTurn(store: Store, role: string, content: string): Turn {
  const turn: Turn = { seq: store.turns.length + 1, role, content, archivedBy: null };
  store.turns.push(turn);
  return turn;
}

/** Render what the model would see: summaries stand in for archived turns. */
function assembleContext(store: Store): string {
  const lines = store.summaries.map((s) => `[summary ${s.summaryId}] ${s.text}`);
  for (const t of store.turns)
    if (t.archivedBy === null) lines.push(`${t.role}: ${t.content}`);
  for (const e of store.entities) lines.push(`${e.name} (${e.type}): ${e.fact}`);
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Prompt the model for entities; parse + validate the JSON it returns.
 *
 * TODO: implement.
 *   - Build the prompt as EXTRACT_PROMPT_PREFIX + text and send it as one
 *     user message via chatFn.
 *   - Parse the reply with JSON.parse.
 *   - Validate the shape: the result must be an array; every item must be an
 *     object whose name, type, fact values are all strings — throw an Error
 *     (mention the offending item) otherwise.
 *   - Return the validated array of { name, type, fact } objects.
 */
function extractEntities(_chatFn: ChatFn, _text: string): Entity[] {
  // TODO: implement extract (prompt -> chatFn -> JSON.parse -> validate)
  throw new Error("TODO: implement extractEntities()");
}

/**
 * Update-on-write for entities: same (name, type) updates; new appends.
 *
 * TODO: implement.
 *   - For each new entity, scan store.entities for a record with the same
 *     name AND type; if found, overwrite its fact in place.
 *   - If none matches, push a copy of the new entity.
 */
function mergeEntities(_store: Store, _newEntities: Entity[]): void {
  // TODO: implement update-on-write merging for entities
  throw new Error("TODO: implement mergeEntities()");
}

/**
 * Compress turns into a summary record — mark the originals, don't delete.
 *
 * TODO: implement.
 *   - Render the turns as "role: content" lines and build the prompt as
 *     SUMMARY_PROMPT_PREFIX + rendered; send it as one user message via
 *     chatFn to get the summary text.
 *   - Build a deterministic id from the covered range: "sum-<first>-<last>"
 *     using the first and last turn's seq.
 *   - Mark each turn: set its archivedBy to the summary id (the turn objects
 *     live in the store, so this mutation is the archival).
 *   - Return { summaryId, text, turnSeqs } where turnSeqs lists the covered
 *     seq numbers.
 */
function summariseTurns(_chatFn: ChatFn, _turns: Turn[]): SummaryRecord {
  // TODO: implement compaction (summarise via the model, mark originals, return the record)
  throw new Error("TODO: implement summariseTurns()");
}

/**
 * Just-in-time expansion: recover the original turns behind a summary.
 *
 * TODO: implement.
 *   - Collect the turns in store.turns whose archivedBy equals summaryId,
 *     sorted by seq, and return them (full records, verbatim).
 */
function expandSummary(_store: Store, _summaryId: string): Turn[] {
  // TODO: implement just-in-time expansion
  throw new Error("TODO: implement expandSummary()");
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/** Deterministic fake: fixed valid JSON per known text; fixed summary. */
function makeStubChatFn(): ChatFn {
  return (messages) => {
    const prompt = messages[messages.length - 1].content;
    if (prompt.startsWith("Extract entities")) {
      if (prompt.includes("promoted to CEO")) {
        return JSON.stringify([
          { name: "Dana", type: "person", fact: "CEO of Acme Corp" },
        ]);
      }
      if (prompt.includes("headquartered in Berlin")) {
        return JSON.stringify([
          { name: "Acme Corp", type: "company", fact: "headquartered in Berlin" },
        ]);
      }
      if (prompt.includes("joined Acme Corp")) {
        return JSON.stringify([
          { name: "Dana", type: "person", fact: "CTO of Acme Corp" },
          { name: "Acme Corp", type: "company", fact: "employs Dana as CTO" },
        ]);
      }
      return "[]";
    }
    if (prompt.startsWith("Summarise")) return "Dana joined Acme Corp (Berlin) as CTO.";
    return "[stub-reply] ok.";
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt extractEntities/summariseTurns to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

const SCRIPT: [string, string][] = [
  ["user", "Dana just joined Acme Corp as the new CTO."],
  ["assistant", "Noted - Dana is Acme Corp's CTO."],
  ["user", "Acme Corp is headquartered in Berlin."],
  ["assistant", "Got it: Acme Corp is based in Berlin."],
  ["user", "Update: Dana has been promoted to CEO of Acme Corp."],
  ["assistant", "Understood - Dana is now the CEO."],
];

function check(label: string, ok: boolean): boolean {
  console.log(`  [${ok ? "x" : " "}] ${label}`);
  return ok;
}

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 3: entity + summary memory — ${mode} ===\n`);

  fs.rmSync(STORE_PATH, { force: true }); // clean state on start
  const store = newStore();

  // ── Ingest the conversation: turns + entity extraction on user turns ────
  for (const [role, content] of SCRIPT) {
    addTurn(store, role, content);
    if (role === "user") mergeEntities(store, extractEntities(chatFn, content));
  }

  console.log("Entities after ingestion:");
  for (const e of store.entities) console.log(`  ${e.name} (${e.type}): ${e.fact}`);

  // ── Compaction: summarise the first 4 turns (mark, don't delete) ────────
  const ctxBefore = assembleContext(store);
  const oldTurns = store.turns.filter((t) => t.seq <= 4);
  const record = summariseTurns(chatFn, oldTurns);
  store.summaries.push(record);
  const ctxAfter = assembleContext(store);
  console.log(
    `\nSummary record: '${record.summaryId}' covering seqs [${record.turnSeqs}]`,
  );
  console.log(`Context size before compaction: ${ctxBefore.length} chars`);
  console.log(`Context size after  compaction: ${ctxAfter.length} chars`);

  // ── "Restart": persist, then reload the store fresh from disk ───────────
  saveStore(STORE_PATH, store);
  const store2 = loadStore(STORE_PATH);

  const dana = store2.entities.filter((e) => e.name === "Dana");
  const expanded = expandSummary(store2, record.summaryId);
  console.log("\nAfter restart (fresh load from disk):");
  console.log(`  Dana entries: ${JSON.stringify(dana)}`);
  console.log(
    `  expandSummary('${record.summaryId}') -> ${expanded.length} original turns`,
  );

  // ── Acceptance checks ────────────────────────────────────────────────────
  if (!useStub) {
    console.log("\nRun with --stub for the exact acceptance checks.");
    return;
  }

  // 1) Known entities recalled across a restart, with the LATEST fact.
  const okRecall = dana.length === 1 && dana[0].fact === "CEO of Acme Corp";
  // 2) Merging updates instead of duplicating: 2 entities total, both fresh.
  const acme = store2.entities.filter((e) => e.name === "Acme Corp");
  const okMerge =
    store2.entities.length === 2 &&
    acme.length === 1 &&
    acme[0].fact === "headquartered in Berlin";
  // 3) Compaction shrinks the assembled context.
  const okShorter = ctxAfter.length < ctxBefore.length;
  // 4) Just-in-time expansion recovers the originals verbatim (post-restart).
  const okExpand =
    JSON.stringify(expanded.map((t) => [t.role, t.content])) ===
    JSON.stringify(SCRIPT.slice(0, 4));
  // 5) Mark, don't delete: the store still holds all 6 turns.
  const okMarked =
    store2.turns.length === 6 &&
    store2.turns.filter((t) => t.archivedBy === record.summaryId).length === 4;

  console.log("\nAcceptance:");
  const all = [
    check("Dana recalled across restart with the merged fact (CEO)", okRecall),
    check("merging updates in place — 2 entities, no duplicates", okMerge),
    check(
      `context shorter after compaction (${ctxBefore.length} -> ${ctxAfter.length} chars)`,
      okShorter,
    ),
    check("expandSummary recovers the 4 original turns verbatim", okExpand),
    check("originals marked archived, never deleted", okMarked),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

main();
