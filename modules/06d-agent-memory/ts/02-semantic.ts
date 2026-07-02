/**
 * Task 2 🟡 — Semantic memory with a relevance threshold (noisy retrieval).
 *
 * What you'll learn:
 *   - Semantic memory is the agent's knowledge base: facts looked up by
 *     MEANING (similarity search), not by recency. We rank with bag-of-words
 *     cosine (module 06c's trick) so it's offline and deterministic.
 *   - Noisy retrieval: top-k ALWAYS returns k results, even when the k-th one
 *     is a semantically-adjacent-but-wrong-topic distractor. The mitigation is
 *     a relevance threshold: drop results scoring below `minScore`.
 *   - Update-on-write: `upsert` keyed by docId REPLACES a changed fact instead
 *     of appending a duplicate — otherwise retrieval can surface the stale
 *     version of the truth next to the fresh one.
 *
 * The math (same as 06c Task 2):
 *
 *     cosine(a, b) = (a · b) / (||a|| * ||b||)
 *
 *     a · b = Σ_w a[w]·b[w]  over shared words;  ||a|| = sqrt(Σ_w a[w]²)
 *     Zero norm on either side → similarity 0.
 *
 * OFFLINE: retrieval never needs a model. The final "inject" step (answer the
 * question grounded in retrieved memory) takes `chatFn`; with --stub the fake
 * model echoes the memory it was given, without --stub it wraps
 * getProvider().chat.
 *
 * How to run:
 *   pnpm tsx modules/06d-agent-memory/ts/02-semantic.ts --stub
 *   pnpm tsx modules/06d-agent-memory/ts/02-semantic.ts
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

interface Store {
  docs: Record<string, { text: string }>;
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
const STORE_PATH = path.join(STATE_DIR, "ts-02-semantic.json");

const K = 2; // top-k
const THRESHOLD = 0.4; // tuned relevance threshold: true hit ≈ 0.63, distractor ≈ 0.31

// ---------------------------------------------------------------------------
// JSON-file store  (provided — do not edit)
// ---------------------------------------------------------------------------

function newStore(): Store {
  return { docs: {} };
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

// ---------------------------------------------------------------------------
// Bag-of-words vectors  (provided — do not edit)
// ---------------------------------------------------------------------------

/** Lowercase word tokens (letters/digits). */
function tokenize(text: string): string[] {
  return text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
}

/** Word -> count. */
function bagOfWords(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const tok of tokenize(text)) counts.set(tok, (counts.get(tok) ?? 0) + 1);
  return counts;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * Cosine similarity between two sparse count vectors.
 *
 *     cosine(a, b) = dot(a, b) / (||a|| * ||b||)
 *
 * TODO: implement.
 *   - Dot product: for each word/count in `a`, if `b` also has that word, add
 *     the product of the two counts.
 *   - Each norm: Math.sqrt of the sum of that vector's squared counts.
 *   - If either norm is 0, return 0; otherwise dot / (normA * normB).
 */
function cosine(_a: Map<string, number>, _b: Map<string, number>): number {
  // TODO: implement cosine similarity over sparse count vectors
  throw new Error("TODO: implement cosine()");
}

/**
 * Top-k retrieval, then drop anything below the relevance threshold.
 *
 * Return an array of { docId, text, score } hits, best first. The threshold
 * runs AFTER the top-k cut: first rank and slice the k best, then keep only
 * those with score >= minScore (that's why minScore=0 lets a distractor leak
 * through — top-k alone has no notion of "good enough").
 *
 * TODO: implement.
 *   - Vectorize the query with bagOfWords.
 *   - Score every doc in store.docs (a record docId -> { text }) with cosine,
 *     building { docId, text, score } hits.
 *   - Sort by score descending (Array.prototype.sort is stable — ties keep
 *     insertion order), slice the first k.
 *   - Filter the slice: keep hits with score >= minScore, and return it.
 */
function retrieve(_store: Store, _query: string, _k: number, _minScore: number): Hit[] {
  // TODO: implement thresholded top-k retrieval (score -> sort -> cut -> filter)
  throw new Error("TODO: implement retrieve()");
}

/**
 * Update-on-write: same docId replaces the record, never duplicates.
 *
 * TODO: implement.
 *   - Write { text } into store.docs under docId — a keyed assignment is
 *     already an upsert (insert new key or overwrite old).
 */
function upsert(_store: Store, _docId: string, _text: string): void {
  // TODO: implement update-on-write
  throw new Error("TODO: implement upsert()");
}

// ---------------------------------------------------------------------------
// The inject step  (provided — do not edit)
// ---------------------------------------------------------------------------

function answerFromMemory(chatFn: ChatFn, question: string, hits: Hit[]): string {
  const memory =
    hits.length > 0
      ? hits.map((h) => `- ${h.text}`).join("\n")
      : "(no relevant memory)";
  const prompt =
    "Answer the question using ONLY the memory below.\n\n" +
    `Memory:\n${memory}\n\n` +
    `Question: ${question}\n` +
    "Answer:";
  return chatFn([{ role: "user", content: prompt }]);
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/** Deterministic fake: echo the memory block it was grounded in. */
function makeStubChatFn(): ChatFn {
  return (messages) => {
    const prompt = messages[messages.length - 1].content;
    const memory = prompt.split("Memory:\n")[1].split("\n\nQuestion:")[0];
    return `[stub] grounded in: ${memory}`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt answerFromMemory to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

// A knowledge base with a deliberate near-miss distractor: "kb-search" shares
// infrastructure words with the query (service, uses, the) but answers a
// different question. Pure top-k will happily hand it to the model.
const SEED_DOCS: Record<string, string> = {
  "kb-checkout": "The checkout service uses the Postgres database.",
  "kb-search":
    "The search service uses Elasticsearch to index products for the storefront.",
  "kb-standup": "The team standup meeting moved to 9am on Mondays.",
  "kb-pasta": "Basil and oregano make a simple pasta sauce.",
};

const QUERY = "Which database does the checkout service use?";
const UPDATED_FACT =
  "The checkout service now uses the MySQL database, replacing Postgres.";

function check(label: string, ok: boolean): boolean {
  console.log(`  [${ok ? "x" : " "}] ${label}`);
  return ok;
}

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 2: semantic memory + threshold — ${mode} ===\n`);

  fs.rmSync(STORE_PATH, { force: true }); // clean state on start
  let store = newStore();
  for (const [docId, text] of Object.entries(SEED_DOCS)) upsert(store, docId, text);
  saveStore(STORE_PATH, store);
  store = loadStore(STORE_PATH); // retrieval works off the persisted KB

  // ── Noisy retrieval: threshold 0 lets the distractor into top-k ─────────
  console.log(`Query: ${JSON.stringify(QUERY)}\n`);
  const noisy = retrieve(store, QUERY, K, 0.0);
  console.log(`top-${K} with minScore=0.0 (noisy):`);
  for (const r of noisy) console.log(`  ${r.score.toFixed(3)}  ${r.docId}: ${r.text}`);

  // ── The mitigation: a tuned relevance threshold ──────────────────────────
  const filtered = retrieve(store, QUERY, K, THRESHOLD);
  console.log(`\ntop-${K} with minScore=${THRESHOLD} (filtered):`);
  for (const r of filtered)
    console.log(`  ${r.score.toFixed(3)}  ${r.docId}: ${r.text}`);

  // ── Update-on-write: the fact changes; same docId must replace it ───────
  upsert(store, "kb-checkout", UPDATED_FACT);
  saveStore(STORE_PATH, store);
  store = loadStore(STORE_PATH);
  const fresh = retrieve(store, QUERY, K, THRESHOLD);
  console.log(
    `\nafter upsert of kb-checkout (${Object.keys(store.docs).length} docs in store):`,
  );
  for (const r of fresh) console.log(`  ${r.score.toFixed(3)}  ${r.docId}: ${r.text}`);

  // ── Inject: ground the model in what survived the threshold ─────────────
  const answer = answerFromMemory(chatFn, QUERY, fresh);
  console.log(`\nmodel answer: ${answer}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  if (!useStub) {
    console.log("\nRun with --stub for the exact acceptance checks.");
    return;
  }

  // 1) With threshold 0 the distractor leaks into top-k.
  const okLeak =
    JSON.stringify(noisy.map((r) => r.docId)) === '["kb-checkout","kb-search"]';
  // 2) The tuned threshold filters the distractor; the true hit survives.
  const okFilter = JSON.stringify(filtered.map((r) => r.docId)) === '["kb-checkout"]';
  // 3) Upsert leaves store size unchanged (no duplicate record)...
  const okSize = Object.keys(store.docs).length === Object.keys(SEED_DOCS).length;
  // 4) ...and retrieval returns the NEW text, not the stale one.
  const okFresh =
    fresh.length === 1 &&
    fresh[0].text === UPDATED_FACT &&
    Object.values(store.docs).every((rec) => rec.text !== SEED_DOCS["kb-checkout"]);
  // 5) The inject step grounded the model in the fresh memory.
  const okInject = answer.includes(UPDATED_FACT);

  console.log("\nAcceptance:");
  const all = [
    check(`minScore=0: distractor kb-search leaks into top-${K}`, okLeak),
    check(`minScore=${THRESHOLD}: distractor filtered, true hit survives`, okFilter),
    check(
      `upsert keeps store size at ${Object.keys(SEED_DOCS).length} (no duplicate)`,
      okSize,
    ),
    check("retrieval returns the NEW text after upsert", okFresh),
    check("the model was grounded in the fresh memory", okInject),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

main();
