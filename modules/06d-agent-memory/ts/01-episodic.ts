/**
 * Task 1 🟢 — Episodic memory + the read/write lifecycle.
 *
 * What you'll learn:
 *   - Episodic memory is the agent's conversation history: WHAT was said, in
 *     order, per thread. It is the one memory every chat app already has — the
 *     point here is to manage it deliberately instead of letting it happen.
 *   - The lifecycle: memory READS run BEFORE the model call (so the context the
 *     model sees is assembled from the store), memory WRITES run AFTER (so the
 *     turn that just happened is persisted for the next call).
 *   - Thread isolation: a store holds many conversations; a read must return
 *     only the requested thread's turns, never a neighbour's.
 *
 * The turn shape (one JSON record per message in the store):
 *
 *     { threadId: "A", role: "user" | "assistant", content: "..." }
 *
 * The lifecycle you are wiring (runTurn below is provided — read it):
 *
 *     load store  →  READ episodic  →  build context  →  model call
 *                 →  WRITE user turn + assistant turn  →  save store
 *
 * OFFLINE: takes `chatFn: (msgs) => string`. With --stub the fake model
 * deterministically echoes what history it saw; without --stub it wraps
 * getProvider().chat (never a hardcoded vendor).
 *
 * How to run:
 *   pnpm tsx modules/06d-agent-memory/ts/01-episodic.ts --stub
 *   pnpm tsx modules/06d-agent-memory/ts/01-episodic.ts
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

interface EpisodicEntry {
  threadId: string;
  role: string;
  content: string;
}
interface Store {
  episodic: EpisodicEntry[];
}

const STATE_DIR = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
  "state",
);
const STORE_PATH = path.join(STATE_DIR, "ts-01-episodic.json");

const SYSTEM =
  "You are a concise assistant. Use the conversation history when it helps.";
const LAST_N = 6; // how many past turns a read may inject

// ---------------------------------------------------------------------------
// JSON-file store  (provided — do not edit)
// ---------------------------------------------------------------------------

function newStore(): Store {
  return { episodic: [] };
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
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * Return the last `lastN` turns of ONE thread as chat messages.
 *
 * The store keeps every thread's turns in one flat `store.episodic` array
 * (each record has threadId, role, content). A read must:
 *   - keep only the records whose threadId matches (isolation),
 *   - preserve their original order (the array is already chronological),
 *   - keep only the LAST `lastN` of them (the injection bound),
 *   - return them as chat messages: objects with just role and content
 *     (the model never sees threadId).
 *
 * TODO: implement.
 *   - Filter store.episodic by threadId.
 *   - Slice the last `lastN` records.
 *   - Map each record to a { role, content } object and return the array.
 */
function readEpisodic(_store: Store, _threadId: string, _lastN: number): Msg[] {
  // TODO: implement the episodic read (filter -> slice -> map)
  throw new Error("TODO: implement readEpisodic()");
}

/**
 * Append one turn record to the store (the WRITE half of the lifecycle).
 *
 * TODO: implement.
 *   - Push an object with the three keys threadId, role, content onto
 *     store.episodic so the flat array stays chronological across threads.
 */
function writeEpisodic(
  _store: Store,
  _threadId: string,
  _role: string,
  _content: string,
): void {
  // TODO: implement the episodic write (append one record)
  throw new Error("TODO: implement writeEpisodic()");
}

/**
 * Assemble the ordered message list the model will see.
 *
 * Order matters: system message first, then the episodic turns (already
 * chronological), then the new user message last.
 *
 * TODO: implement.
 *   - Return a Msg[]: one system message built from `system`, followed by the
 *     episodic messages, ending with one user message built from `userMsg`.
 */
function buildContext(_system: string, _episodic: Msg[], _userMsg: string): Msg[] {
  // TODO: implement the ordered context assembly
  throw new Error("TODO: implement buildContext()");
}

// ---------------------------------------------------------------------------
// One memory-aware turn  (provided — this IS the lifecycle; read it)
// ---------------------------------------------------------------------------

function runTurn(
  chatFn: ChatFn,
  storePath: string,
  threadId: string,
  userMsg: string,
): { context: Msg[]; reply: string } {
  const store = loadStore(storePath); // reload from disk — proves persistence
  const episodic = readEpisodic(store, threadId, LAST_N); // READ before the call
  const context = buildContext(SYSTEM, episodic, userMsg);
  const reply = chatFn(context); // the model call
  writeEpisodic(store, threadId, "user", userMsg); // WRITE after the call
  writeEpisodic(store, threadId, "assistant", reply);
  saveStore(storePath, store);
  return { context, reply };
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/** Deterministic fake: echo how much (and which) history the model saw. */
function makeStubChatFn(): ChatFn {
  return (messages) => {
    const hist = messages.slice(1, -1).map((m) => m.content); // between system and new user msg
    const user = messages[messages.length - 1].content;
    const digest =
      hist.length > 0 ? hist.map((h) => h.slice(0, 40)).join(" | ") : "(none)";
    return `[stub] reply to '${user}' after ${hist.length} history msgs: ${digest}`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt runTurn to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

function check(label: string, ok: boolean): boolean {
  console.log(`  [${ok ? "x" : " "}] ${label}`);
  return ok;
}

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 1: episodic memory — ${mode} ===\n`);

  fs.rmSync(STORE_PATH, { force: true }); // clean state on start

  // Two threads, interleaved — the store must keep them apart.
  const a1 = "alpha thread: my favourite colour is teal";
  const b1 = "bravo thread: my favourite colour is orange";
  const a2 = "alpha thread: what colour do I like?";
  const b2 = "bravo thread: what colour do I like?";

  const contexts: Record<string, Msg[][]> = { A: [], B: [] };
  const replies: Record<string, string[]> = { A: [], B: [] };
  const turns: [string, string][] = [
    ["A", a1],
    ["B", b1],
    ["A", a2],
    ["B", b2],
  ];
  for (const [threadId, msg] of turns) {
    const { context, reply } = runTurn(chatFn, STORE_PATH, threadId, msg);
    contexts[threadId].push(context);
    replies[threadId].push(reply);
    console.log(`[${threadId}] user: ${msg}`);
    console.log(`[${threadId}] assistant: ${reply}\n`);
  }

  const store = loadStore(STORE_PATH);
  const aEntries = store.episodic.filter((e) => e.threadId === "A");
  const bEntries = store.episodic.filter((e) => e.threadId === "B");
  console.log(
    `Store after the run: ${aEntries.length} A-entries, ${bEntries.length} B-entries`,
  );

  // ── Acceptance checks ────────────────────────────────────────────────────
  if (!useStub) {
    console.log("\nRun with --stub for the exact acceptance checks.");
    return;
  }

  // 1) Isolation: thread A's contexts never contain thread B's turns (and v.v.).
  const okIsolation =
    contexts.A.every((ctx) => ctx.every((m) => !m.content.includes("bravo"))) &&
    contexts.B.every((ctx) => ctx.every((m) => !m.content.includes("alpha")));

  // 2) Order preserved: A's episodic reads back user/assistant alternating,
  //    chronologically.
  const expectedA: Msg[] = [
    { role: "user", content: a1 },
    { role: "assistant", content: replies.A[0] },
    { role: "user", content: a2 },
    { role: "assistant", content: replies.A[1] },
  ];
  const okOrder =
    JSON.stringify(readEpisodic(store, "A", 10)) === JSON.stringify(expectedA);

  // 3) Counts: 2 turns per thread → 4 records each (user + assistant per turn).
  const okCounts =
    aEntries.length === 4 && bEntries.length === 4 && store.episodic.length === 8;

  // 4) The lastN bound is respected.
  const okLastN =
    JSON.stringify(readEpisodic(store, "A", 2)) === JSON.stringify(expectedA.slice(-2));

  // 5) Context shape: system first, new user message last, episodic between.
  const lastCtx = contexts.A[contexts.A.length - 1];
  const okShape =
    lastCtx[0].role === "system" &&
    lastCtx[0].content === SYSTEM &&
    lastCtx[lastCtx.length - 1].role === "user" &&
    lastCtx[lastCtx.length - 1].content === a2 &&
    lastCtx.length === 2 + 2; // system + 2 episodic (turn 1) + user

  console.log("\nAcceptance:");
  const all = [
    check("thread A's context never contains thread B's turns", okIsolation),
    check("turn order preserved on read-back", okOrder),
    check("store holds 4 A-entries + 4 B-entries after 2 turns each", okCounts),
    check("last_n bound respected (read of 2 returns the last 2)", okLastN),
    check("context ordered: system → episodic → new user msg", okShape),
  ];
  if (all.every(Boolean)) console.log("\n  All acceptance checks passed.");
  else console.log("\n  Some checks failed — revisit your implementation.");
}

main();
