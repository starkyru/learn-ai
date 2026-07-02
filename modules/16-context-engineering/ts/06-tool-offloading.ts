/**
 * Task 6 — Tool-output offloading 🟡
 *
 * What this teaches:
 *   - In a multi-iteration agent loop, every tool result you append to the message
 *     history is re-sent to the model on EVERY later iteration. One 3–4 K-token
 *     web-search result therefore doesn't cost 3–4 K tokens once — it costs that
 *     much per remaining iteration.
 *   - The offloading pattern: persist the full tool output to a tool-log store
 *     keyed by an id, put only a one-line reference into the history
 *     ("[Tool Log #2] stored; call read_tool_log to retrieve"), and expose a
 *     readToolLog(id) tool so the agent can pull the full text back on demand.
 *   - Correctness requirement: the store must round-trip the output exactly, and
 *     the loop must still reach answers whose supporting facts live only inside a
 *     stored payload.
 *
 * Fully offline and deterministic: the "agent" is a scripted 5-iteration loop and
 * web_search returns large canned payloads — no provider, no network.
 *
 * Dependencies (already in package.json):
 *   @dqbd/tiktoken — same tokenizer as Task 1.
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/06-tool-offloading.ts
 */

import { get_encoding } from "@dqbd/tiktoken";

type Role = "system" | "user" | "assistant" | "tool";
interface Message {
  role: Role;
  content: string;
}
interface ToolLogRecord {
  id: number;
  toolName: string;
  output: string;
}
type ToolLogStore = ToolLogRecord[];

type ScriptStep =
  | { action: "web_search"; query: string }
  | { action: "read_tool_log"; logId: number }
  | { action: "answer" };

// ---------------------------------------------------------------------------
// Provided: token counting (same tooling as Task 1 — do not edit)
// ---------------------------------------------------------------------------

// One shared encoder; freed at the end of main() to release the WASM memory.
const ENCODING = get_encoding("cl100k_base");

/** Exact token count with tiktoken (cl100k_base), as in Task 1. */
function countTokens(text: string): number {
  return ENCODING.encode(text).length;
}

/** Sum of token counts across every message currently in the context. */
function countContextTokens(messages: Message[]): number {
  return messages.reduce((sum, m) => sum + countTokens(m.content), 0);
}

// ---------------------------------------------------------------------------
// Provided: the fake web_search tool with large canned payloads (do not edit)
// ---------------------------------------------------------------------------

// The needle: this number exists ONLY inside the second search payload. The
// final answer must contain it — proving that on-demand retrieval worked.
const NEEDLE_FACT = "-183.4";
const FINDING_LINE =
  "FINDING: The Meridian-3 probe recorded a nightside surface temperature of " +
  `${NEEDLE_FACT} degrees Celsius at its polar landing site.`;

const FILLER_SENTENCES = [
  "Independent laboratories have replicated the measurement under a range of ambient conditions.",
  "The methodology section describes calibration runs, control groups, and error bars in detail.",
  "Commentators note that funding cycles and launch windows constrain how fast follow-ups appear.",
  "A meta-analysis is planned once at least five independent data sets become available.",
  "Reviewers flagged instrument drift as the dominant source of systematic uncertainty.",
];

/** Build a deterministic, large search-result payload (~3-4 K tokens). */
function makePayload(topic: string, nResults: number, finding?: string): string {
  const lines = [`web_search results for: ${topic}`, ""];
  for (let i = 0; i < nResults; i++) {
    const a = FILLER_SENTENCES[i % FILLER_SENTENCES.length];
    const b = FILLER_SENTENCES[(i + 2) % FILLER_SENTENCES.length];
    lines.push(`[Result ${i + 1}] ${topic} — source ${i + 1}: ${a} ${b}`);
    if (finding !== undefined && i === Math.floor(nResults / 2)) {
      lines.push(finding);
    }
  }
  return lines.join("\n");
}

const SEARCH_QUERIES = [
  "solar-sail propulsion field tests",
  "Meridian-3 probe landing telemetry",
  "cryogenic fuel storage benchmarks",
];

const CANNED_RESULTS = new Map<string, string>([
  [SEARCH_QUERIES[0], makePayload(SEARCH_QUERIES[0], 80)],
  [SEARCH_QUERIES[1], makePayload(SEARCH_QUERIES[1], 80, FINDING_LINE)],
  [SEARCH_QUERIES[2], makePayload(SEARCH_QUERIES[2], 80)],
]);

/** Deterministic stand-in for a web-search tool. Same query → same payload. */
function fakeWebSearch(query: string): string {
  const result = CANNED_RESULTS.get(query);
  if (result === undefined) throw new Error(`no canned result for query: "${query}"`);
  return result;
}

/** Return the first line starting with 'FINDING:' — the fact the task needs. */
function extractFinding(text: string): string {
  for (const line of text.split("\n")) {
    if (line.startsWith("FINDING:")) return line;
  }
  return "FINDING: (not located in the current context)";
}

// ---------------------------------------------------------------------------
// Provided: the scripted agent loop (do not edit)
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT =
  "You are a research agent. Use web_search to gather sources, then answer " +
  "the user's question with the specific figure you found.";
const USER_TASK =
  "What nightside surface temperature did the Meridian-3 probe record? " +
  "Search the three assigned topics, then answer.";

// A fixed 5-iteration script — the same sequence drives BOTH loops.
const SCRIPT: ScriptStep[] = [
  { action: "web_search", query: SEARCH_QUERIES[0] },
  { action: "web_search", query: SEARCH_QUERIES[1] },
  { action: "web_search", query: SEARCH_QUERIES[2] },
  { action: "read_tool_log", logId: 2 },
  { action: "answer" },
];

interface LoopResult {
  messages: Message[];
  perIteration: number[];
  finalAnswer: string;
}

/**
 * Baseline: every full tool output is appended to the message history, so
 * every later iteration re-carries it.
 */
function runLoopNaive(script: ScriptStep[]): LoopResult {
  const messages: Message[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: USER_TASK },
  ];
  const perIteration: number[] = [];
  let finalAnswer = "";

  for (const step of script) {
    if (step.action === "web_search") {
      const output = fakeWebSearch(step.query);
      messages.push({
        role: "assistant",
        content: `Calling web_search("${step.query}")`,
      });
      messages.push({ role: "tool", content: output });
    } else if (step.action === "read_tool_log") {
      // Naive loop keeps everything inline — nothing to fetch.
      messages.push({
        role: "assistant",
        content: "(full outputs already inline — no lookup needed)",
      });
    } else {
      const finding = extractFinding(messages.map((m) => m.content).join("\n"));
      finalAnswer = `Answer: ${finding}`;
      messages.push({ role: "assistant", content: finalAnswer });
    }
    perIteration.push(countContextTokens(messages));
  }

  return { messages, perIteration, finalAnswer };
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * Persist one full tool output into the store; return its new id.
 *
 * TODO: implement.
 *   - Compute the new id: ids are 1-based and sequential (the store's current
 *     length tells you the next one).
 *   - Push a record with fields id, toolName, output.
 *   - Return the new id.
 */
function writeToolLog(store: ToolLogStore, toolName: string, output: string): number {
  // TODO: push the record and return its id
  throw new Error("TODO: implement writeToolLog()");
}

/**
 * Build the compact one-liner that goes into the message history INSTEAD of
 * the full output. A later iteration must be able to act on it, so it should:
 *   - name the tool and the log id (e.g. a "[Tool Log #<id>]" tag),
 *   - state the stored size in tokens (use countTokens on the output),
 *   - include a short preview — the first ~80 characters of the output,
 *   - say that read_tool_log(<id>) retrieves the full text.
 *
 * Return a SINGLE line (no newlines), well under 100 tokens.
 *
 * TODO: implement — assemble and return that reference string.
 */
function makeReference(logId: number, toolName: string, output: string): string {
  // TODO: build the one-line reference (id + tool name + token count + preview + how to retrieve)
  throw new Error("TODO: implement makeReference()");
}

/**
 * Return the EXACT stored output for logId (character-for-character round-trip).
 *
 * TODO: implement.
 *   - Find the record whose id equals logId.
 *   - Return its output unmodified.
 *   - Throw an Error if no record has that id.
 */
function readToolLog(store: ToolLogStore, logId: number): string {
  // TODO: look the record up by id and return its stored output
  throw new Error("TODO: implement readToolLog()");
}

/**
 * The same scripted loop as runLoopNaive, but full tool outputs never enter
 * the message history — only references do.
 *
 * TODO: implement. Mirror runLoopNaive step by step:
 *   - Start from the same two seed messages (system + user), an empty
 *     per-iteration array, and an empty final answer.
 *   - "web_search": call fakeWebSearch, persist the full output with
 *     writeToolLog, push the same assistant "Calling web_search(...)" line,
 *     then push a tool message whose content is ONLY makeReference(...) —
 *     never the payload itself.
 *   - "read_tool_log": call readToolLog with the step's logId, run
 *     extractFinding on the retrieved text, and push an assistant line
 *     (e.g. noting the lookup) plus a tool message containing just that
 *     finding line — the agent keeps the one sentence it needs, not the
 *     whole payload.
 *   - "answer": exactly as in the naive loop — extract the finding from the
 *     joined message contents and record "Answer: <finding>" as both the
 *     final answer and a new assistant message.
 *   - After EVERY iteration, push countContextTokens(messages) onto the
 *     per-iteration array.
 * Return { messages, perIteration, finalAnswer }.
 */
function runLoopWithOffloading(script: ScriptStep[], store: ToolLogStore): LoopResult {
  // TODO: implement the offloaded loop (use runLoopNaive above as your template)
  throw new Error("TODO: implement runLoopWithOffloading()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

const NAIVE_FLOOR = 9_000; // naive context must END above this many tokens
const OFFLOADED_CEILING = 1_200; // offloaded context must STAY below this at every iteration

function main() {
  console.log("=== Task 6: Tool-output offloading ===\n");

  const naive = runLoopNaive(SCRIPT);
  const store: ToolLogStore = [];
  const off = runLoopWithOffloading(SCRIPT, store);

  console.log(
    "Iter".padEnd(5) +
      " " +
      "Action".padEnd(28) +
      "Naive ctx tokens".padStart(18) +
      "Offloaded ctx tokens".padStart(22),
  );
  console.log("-".repeat(75));
  SCRIPT.forEach((step, i) => {
    let action: string = step.action;
    if (step.action === "web_search")
      action = `web_search("${step.query.slice(0, 14)}…")`;
    else if (step.action === "read_tool_log") action = `read_tool_log(${step.logId})`;
    console.log(
      String(i + 1).padEnd(5) +
        " " +
        action.padEnd(28) +
        String(naive.perIteration[i]).padStart(18) +
        String(off.perIteration[i]).padStart(22),
    );
  });

  const naiveTotal = naive.perIteration.reduce((a, b) => a + b, 0);
  const offTotal = off.perIteration.reduce((a, b) => a + b, 0);
  console.log("-".repeat(75));
  console.log(
    "Tokens the model reads across all 5 iterations".padEnd(52) +
      String(naiveTotal).padStart(7) +
      String(offTotal).padStart(15),
  );
  console.log(`\nNaive final answer     : ${naive.finalAnswer}`);
  console.log(`Offloaded final answer : ${off.finalAnswer}`);
  console.log(
    `Tool-log store         : ${store.length} record(s), ids [${store.map((r) => r.id).join(", ")}]`,
  );

  // ── Acceptance checks ──────────────────────────────────────────────────────
  const okMonotone = naive.perIteration.every(
    (n, i) => i === 0 || n > naive.perIteration[i - 1],
  );
  const okNaiveBig = naive.perIteration[naive.perIteration.length - 1] > NAIVE_FLOOR;
  const offMax = Math.max(...off.perIteration);
  const okOffSmall = offMax < OFFLOADED_CEILING;
  const original = fakeWebSearch(SEARCH_QUERIES[1]);
  const okRoundtrip = readToolLog(store, 2) === original;
  const okStore = store.map((r) => r.id).join(",") === "1,2,3";
  const okAnswer = off.finalAnswer.includes(NEEDLE_FACT);

  const check = (ok: boolean) => (ok ? "x" : " ");
  console.log("\nAcceptance:");
  console.log(
    `  [${check(okMonotone)}] naive context grows monotonically every iteration`,
  );
  console.log(
    `  [${check(okNaiveBig)}] naive context ends above ${NAIVE_FLOOR} tokens ` +
      `(got ${naive.perIteration[naive.perIteration.length - 1]})`,
  );
  console.log(
    `  [${check(okOffSmall)}] offloaded context stays below ${OFFLOADED_CEILING} ` +
      `tokens at every iteration (max ${offMax})`,
  );
  console.log(`  [${check(okStore)}] writeToolLog assigned sequential ids 1, 2, 3`);
  console.log(
    `  [${check(okRoundtrip)}] readToolLog(2) round-trips the exact original payload`,
  );
  console.log(
    `  [${check(okAnswer)}] offloaded final answer contains the needle fact ` +
      `(${NEEDLE_FACT}) that lives only inside stored payload #2`,
  );

  if (okMonotone && okNaiveBig && okOffSmall && okStore && okRoundtrip && okAnswer) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

try {
  main();
} finally {
  ENCODING.free(); // release the WASM encoder memory
}
