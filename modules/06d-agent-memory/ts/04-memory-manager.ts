/**
 * Task 4 🔴 — The MemoryManager: composed lifecycle + TTL/staleness.
 *
 * This file is STANDALONE: the working pieces you built in Tasks 1–3 (store
 * helpers, bag-of-words cosine retrieval, entity extraction + merge,
 * summarisation) are copied in below as PROVIDED code. This task is about the
 * COMPOSITION — one manager that runs the whole read side before the model
 * call and the whole write side after it, under a hard token budget:
 *
 *     per turn:
 *         evictStale(...)                        // forget
 *         ctx = mm.assembleContext(thread, q)    // read:  episodic -> semantic
 *                                                //        -> entities -> summaries
 *         reply = model(ctx + q)                 // the one model call
 *         mm.finalizeTurn(thread, q, reply)      // write: episodic, entities,
 *                                                //        conditional summarisation
 *
 * You implement:
 *   - MemoryManager.assembleContext — the fixed read order + the token budget
 *     (oldest history falls back to its summary instead of verbatim turns).
 *   - MemoryManager.finalizeTurn — the write path: episodic write, entity
 *     extract+merge, summarise the oldest turns when history exceeds its budget.
 *   - evictStale — TTL eviction for semantic records (fake clock, no real time).
 *
 * Determinism: fake integer clock (one tick per turn), stub model, whitespace
 * token counter — no Date.now() anywhere.
 *
 * How to run:
 *   pnpm tsx modules/06d-agent-memory/ts/04-memory-manager.ts --stub
 *   pnpm tsx modules/06d-agent-memory/ts/04-memory-manager.ts
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
  threadId: string;
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
interface SemanticDoc {
  text: string;
  createdAt: number;
}
interface Store {
  episodic: Turn[];
  entities: Entity[];
  summaries: SummaryRecord[];
  semantic: Record<string, SemanticDoc>;
}
interface Hit {
  docId: string;
  text: string;
  score: number;
}

const STATE_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "state",
);
const STORE_PATH = path.join(STATE_DIR, "ts-04-memory-manager.json");

const BUDGET = 110; // hard token budget for the assembled context (incl. the query)
const HISTORY_BUDGET = 40; // when active-turn tokens exceed this, compact the oldest
const KEEP_RECENT = 2; // records kept verbatim when compacting (1 exchange)
const K = 2; // semantic top-k
const MIN_SCORE = 0.35; // semantic relevance threshold (Task 2)
const TTL = 3; // semantic records older than this many ticks are stale

const SYSTEM =
  "You are a concise assistant. Ground your answer in the provided context.";

const EXTRACT_PROMPT_PREFIX =
  "Extract entities from the text below. Return a JSON array of objects, " +
  'each with exactly the string keys "name", "type", "fact". ' +
  "Return the JSON array only, no prose.\n\nText: ";

const SUMMARY_PROMPT_PREFIX =
  "Summarise the following conversation turns in one short sentence:\n\n";

// ---------------------------------------------------------------------------
// PROVIDED — token counting + store (from Task 1)
// ---------------------------------------------------------------------------

/** Deterministic proxy tokenizer: whitespace-separated chunks. */
function countTokens(text: string): number {
  return text.match(/\S+/g)?.length ?? 0;
}

function newStore(): Store {
  return { episodic: [], entities: [], summaries: [], semantic: {} };
}

function saveStore(storePath: string, store: Store): void {
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
  fs.writeFileSync(storePath, JSON.stringify(store, null, 2));
}

function writeTurn(
  store: Store,
  threadId: string,
  role: string,
  content: string,
): void {
  store.episodic.push({
    seq: store.episodic.length + 1,
    threadId,
    role,
    content,
    archivedBy: null,
  });
}

/** Non-archived turns of one thread, chronological. */
function readActiveTurns(store: Store, threadId: string): Turn[] {
  return store.episodic.filter((t) => t.threadId === threadId && t.archivedBy === null);
}

function turnLine(turn: Turn): string {
  return `${turn.role}: ${turn.content}`;
}

// ---------------------------------------------------------------------------
// PROVIDED — semantic retrieval with threshold (from Task 2)
// ---------------------------------------------------------------------------

function bagOfWords(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const tok of text.toLowerCase().match(/[a-z0-9]+/g) ?? [])
    counts.set(tok, (counts.get(tok) ?? 0) + 1);
  return counts;
}

function cosine(a: Map<string, number>, b: Map<string, number>): number {
  let dot = 0;
  for (const [word, count] of a) dot += count * (b.get(word) ?? 0);
  let sqA = 0;
  for (const v of a.values()) sqA += v * v;
  let sqB = 0;
  for (const v of b.values()) sqB += v * v;
  const normA = Math.sqrt(sqA);
  const normB = Math.sqrt(sqB);
  if (normA === 0 || normB === 0) return 0;
  return dot / (normA * normB);
}

function retrieveSemantic(
  store: Store,
  query: string,
  k: number,
  minScore: number,
): Hit[] {
  const qv = bagOfWords(query);
  const scored: Hit[] = Object.entries(store.semantic).map(([docId, rec]) => ({
    docId,
    text: rec.text,
    score: cosine(qv, bagOfWords(rec.text)),
  }));
  scored.sort((x, y) => y.score - x.score);
  return scored.slice(0, k).filter((h) => h.score >= minScore);
}

// ---------------------------------------------------------------------------
// PROVIDED — entity extraction + merge, summarisation (from Task 3)
// ---------------------------------------------------------------------------

function extractEntities(chatFn: ChatFn, text: string): Entity[] {
  const raw = chatFn([{ role: "user", content: EXTRACT_PROMPT_PREFIX + text }]);
  const data: unknown = JSON.parse(raw);
  if (!Array.isArray(data))
    throw new Error(`expected a JSON array of entities, got: ${raw}`);
  const out: Entity[] = [];
  for (const item of data) {
    const rec = item as Record<string, unknown>;
    if (
      typeof rec !== "object" ||
      rec === null ||
      typeof rec.name !== "string" ||
      typeof rec.type !== "string" ||
      typeof rec.fact !== "string"
    ) {
      throw new Error(`bad entity record: ${JSON.stringify(item)}`);
    }
    out.push({ name: rec.name, type: rec.type, fact: rec.fact });
  }
  return out;
}

function mergeEntities(store: Store, newEntities: Entity[]): void {
  for (const entity of newEntities) {
    const existing = store.entities.find(
      (e) => e.name === entity.name && e.type === entity.type,
    );
    if (existing) existing.fact = entity.fact;
    else store.entities.push({ ...entity });
  }
}

function summariseTurns(chatFn: ChatFn, turns: Turn[]): SummaryRecord {
  const rendered = turns.map(turnLine).join("\n");
  const text = chatFn([{ role: "user", content: SUMMARY_PROMPT_PREFIX + rendered }]);
  const summaryId = `sum-${turns[0].seq}-${turns[turns.length - 1].seq}`;
  for (const turn of turns) turn.archivedBy = summaryId;
  return { summaryId, text, turnSeqs: turns.map((t) => t.seq) };
}

// ---------------------------------------------------------------------------
// Core — YOU implement assembleContext, finalizeTurn, evictStale
// ---------------------------------------------------------------------------

/** Owns the full lifecycle: read order, budget, writes, compaction. */
class MemoryManager {
  constructor(
    private chatFn: ChatFn,
    private store: Store,
  ) {}

  /**
   * Build the context block for one model call, under the token budget.
   *
   * Fixed read order of the sections in the returned text:
   *   1. "## Recent turns"       — active (non-archived) episodic turns
   *   2. "## Relevant knowledge" — semantic hits (top-K, thresholded)
   *   3. "## Known entities"     — every entity as "- name (type): fact"
   *   4. "## Summaries"          — summary texts standing in for archived turns
   *
   * The budget: sections 2–4 plus the query are the FIXED cost. Whatever
   * token budget remains goes to episodic turns, filled NEWEST-first (so
   * the oldest history is the first to fall back to its summary), then
   * re-ordered chronologically for the final text.
   *
   * Return { context, tokens } where tokens counts the context text plus the
   * query — the number the harness holds under BUDGET.
   *
   * TODO: implement.
   *   - Get semantic hits via retrieveSemantic (K, MIN_SCORE); render
   *     sections 2-4 as header + "- ..." lines (skip a section's lines, keep
   *     its header, when it is empty).
   *   - Compute the fixed token cost: countTokens of all headers + the
   *     section 2-4 lines + the query (header for section 1 included).
   *   - Walk readActiveTurns(...) in REVERSE, adding turnLine(t) while its
   *     countTokens still fits in BUDGET - fixed cost; then restore
   *     chronological order.
   *   - Join sections 1-4 (headers + lines) with newlines; return the text
   *     and countTokens(text) + countTokens(query).
   */
  assembleContext(
    _threadId: string,
    _query: string,
  ): { context: string; tokens: number } {
    // TODO: implement the fixed read order + the token budget
    throw new Error("TODO: implement MemoryManager.assembleContext()");
  }

  /**
   * The write path, AFTER the model call.
   *
   * In order:
   *   1. Episodic write: the user turn, then the assistant turn.
   *   2. Entity extract + merge on the user message.
   *   3. Conditional summarisation: if the active turns' total tokens exceed
   *      HISTORY_BUDGET (and there are more than KEEP_RECENT records),
   *      summarise all but the newest KEEP_RECENT records and push the
   *      summary record onto store.summaries.
   *
   * TODO: implement.
   *   - writeTurn twice (user then assistant).
   *   - extractEntities on userMsg, mergeEntities the result.
   *   - Sum countTokens(turnLine(t)) over readActiveTurns(...); when over
   *     HISTORY_BUDGET, call summariseTurns on the active turns minus the
   *     last KEEP_RECENT (it marks them archived) and push the returned
   *     record onto store.summaries.
   */
  finalizeTurn(_threadId: string, _userMsg: string, _reply: string): void {
    // TODO: implement the write path (episodic, entities, conditional compaction)
    throw new Error("TODO: implement MemoryManager.finalizeTurn()");
  }
}

/**
 * Forget: drop semantic records whose age exceeds the TTL.
 *
 * A record is stale when  now - createdAt > ttl  (fake integer clock).
 * Return the sorted array of evicted docIds (empty array when nothing is
 * stale) and remove them from store.semantic.
 *
 * TODO: implement.
 *   - Collect the docIds whose record is stale by the rule above (sorted).
 *   - Delete each from store.semantic, then return the array.
 */
function evictStale(_store: Store, _now: number, _ttl: number): string[] {
  // TODO: implement TTL eviction
  throw new Error("TODO: implement evictStale()");
}

// ---------------------------------------------------------------------------
// PROVIDED — the no-management baseline
// ---------------------------------------------------------------------------

/**
 * What a memory-augmented (unmanaged) agent would send: EVERY turn verbatim +
 * EVERY semantic doc (no threshold, no TTL) + the query.
 */
function baselineTokens(
  store: Store,
  semanticSeed: Record<string, SemanticDoc>,
  query: string,
): number {
  const parts = store.episodic.map(turnLine);
  for (const rec of Object.values(semanticSeed)) parts.push(rec.text);
  parts.push(query);
  return countTokens(parts.join("\n"));
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/** Deterministic fake: canned entity JSON, fixed summary, short replies. */
function makeStubChatFn(): ChatFn {
  return (messages) => {
    const prompt = messages[messages.length - 1].content;
    if (prompt.startsWith("Extract entities")) {
      if (prompt.includes("leading the Atlas project")) {
        return JSON.stringify([
          { name: "Dana", type: "person", fact: "leads the Atlas project" },
        ]);
      }
      if (prompt.includes("deadline moved")) {
        return JSON.stringify([
          { name: "Atlas", type: "project", fact: "deadline moved to Friday" },
        ]);
      }
      return "[]";
    }
    if (prompt.startsWith("Summarise")) return "[compressed older turns]";
    return "[stub-reply] noted.";
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt the manager's calls to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

const SEED_SEMANTIC: Record<string, SemanticDoc> = {
  "kb-promo": {
    text: "The spring promo discount code SAVE10 expires soon.",
    createdAt: 0,
  },
  "kb-pricing": {
    text: "The pricing page lists the Pro plan at 20 dollars per month.",
    createdAt: 3,
  },
  "kb-deploy": {
    text: "Deploys to production happen from the main branch via CI.",
    createdAt: 3,
  },
};

const SCRIPT = [
  "Dana is leading the Atlas project for our team this quarter.",
  "What is the promo discount code for the Pro plan this spring?",
  "The Atlas project deadline moved to Friday because the billing migration is taking longer.",
  "Please draft a short status update covering the deadline change and the migration work.",
  "Is the promo discount code still valid for new signups today?",
  "Remind me, who leads the Atlas project?",
];

const DANA_ENTITY_LINE = "- Dana (person): leads the Atlas project";

function check(label: string, ok: boolean): boolean {
  console.log(`  [${ok ? "x" : " "}] ${label}`);
  return ok;
}

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 4: MemoryManager — ${mode} ===\n`);

  fs.rmSync(STORE_PATH, { force: true }); // clean state on start
  const store = newStore();
  for (const [docId, rec] of Object.entries(SEED_SEMANTIC))
    store.semantic[docId] = { ...rec };
  const mm = new MemoryManager(chatFn, store);

  const evictions: Record<number, string[]> = {};
  const managed: number[] = [];
  const baselines: number[] = [];
  const contexts: string[] = [];

  console.log(`token budget = ${BUDGET}\n`);
  SCRIPT.forEach((userMsg, i) => {
    const now = i + 1; // fake clock: 1 tick per turn
    const evicted = evictStale(store, now, TTL);
    if (evicted.length > 0) evictions[now] = evicted;
    const { context, tokens } = mm.assembleContext("main", userMsg);
    const reply = chatFn([
      { role: "system", content: SYSTEM },
      { role: "user", content: `${context}\n\n${userMsg}` },
    ]);
    mm.finalizeTurn("main", userMsg, reply);
    const base = baselineTokens(store, SEED_SEMANTIC, userMsg);
    managed.push(tokens);
    baselines.push(base);
    contexts.push(context);
    saveStore(STORE_PATH, store);
    const evic = evicted.length > 0 ? `  evicted=${JSON.stringify(evicted)}` : "";
    console.log(
      `turn ${now}: managed=${String(tokens).padStart(3)} tokens   ` +
        `baseline=${String(base).padStart(3)} tokens${evic}`,
    );
  });

  console.log(
    `\nsummaries made: ${JSON.stringify(store.summaries.map((s) => s.summaryId))}`,
  );
  console.log(
    `entities: ${JSON.stringify(store.entities.map((e) => `${e.name}: ${e.fact}`))}`,
  );

  // ── Acceptance checks ────────────────────────────────────────────────────
  if (!useStub) {
    console.log("\nRun with --stub for the exact acceptance checks.");
    return;
  }

  // 1) Managed context stays under the budget on every turn...
  const okBudget = managed.every((n) => n <= BUDGET);
  // 2) ...while the no-management baseline grows monotonically past it.
  const okBaseline =
    baselines.every((b, i) => i === 0 || baselines[i - 1] < b) &&
    baselines[baselines.length - 1] > BUDGET;
  // 3) The stale semantic record is evicted at the right fake-clock tick...
  const okEvict = JSON.stringify(evictions) === '{"4":["kb-promo"]}';
  // 4) ...and is no longer retrieved: turn 2 saw it, turn 5 must not.
  const okGone = contexts[1].includes("SAVE10") && !contexts[4].includes("SAVE10");
  // 5) The entity from turn 1 is still cited in turn 6's context, even though
  //    turn 1's verbatim text has been compacted away.
  const okEntity =
    contexts[5].includes(DANA_ENTITY_LINE) && !contexts[5].includes(SCRIPT[0]);

  console.log("\nAcceptance:");
  const all = [
    check(
      `managed context ≤ ${BUDGET} tokens on all ${SCRIPT.length} turns (max = ${Math.max(...managed)})`,
      okBudget,
    ),
    check(
      `baseline grows monotonically past the budget (ends at ${baselines[baselines.length - 1]})`,
      okBaseline,
    ),
    check(`kb-promo evicted exactly at tick 4 (TTL=${TTL})`, okEvict),
    check("SAVE10 retrieved at turn 2, gone by turn 5", okGone),
    check("turn-1 entity cited in turn 6 (verbatim turn 1 is not)", okEntity),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

main();
