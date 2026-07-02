/**
 * Task 6 — Harden the loop: stop conditions, failure detection, idempotency 🟡
 *
 * What this teaches:
 *   - A naive agent loop exits only when the model stops emitting tool calls.
 *     A production harness needs *engineered* exits: an iteration cap, a
 *     wall-clock timeout, and a goal-completion predicate that is DISTINCT
 *     from "the model produced a terminal message" (a terminal message may be
 *     a clarifying question, not success).
 *   - Failure detection: an agent that calls the SAME tool with IDENTICAL
 *     arguments over and over (or oscillates A/B/A/B between two calls) is
 *     stuck. Detect it and exit early with a diagnostic instead of burning
 *     the remaining budget.
 *   - Idempotency for side-effecting tools: a retried `send_email` must not
 *     send twice. Assign a stable idempotency key per logical call and dedupe
 *     at execution time. This is HARNESS-level engineering — the model never
 *     sees the key.
 *   - Determinism: the timeout branch is tested with an injected FAKE clock
 *     (a counter the harness advances), not real sleeps.
 *
 * How to run:
 *   pnpm tsx modules/06-agents/ts/06-harden-loop.ts --stub   # offline, deterministic
 *   pnpm tsx modules/06-agents/ts/06-harden-loop.ts          # real model via getProvider()
 *
 * The `--stub` path replays scripted tool-call decisions through YOUR guarded
 * loop — no network, no key, exact assertions. The real path drives the same
 * loop with a live model through llm-core (never a hardcoded vendor).
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Core types  (provided — do not edit)
// ---------------------------------------------------------------------------

type ToolArgs = Record<string, unknown>;

/** One model turn: EITHER a tool call (tool + args) OR a terminal message. */
interface Decision {
  tool?: string;
  args?: ToolArgs;
  message?: string;
}

interface HardenedTool {
  name: string;
  execute(args: ToolArgs): string;
}

/** A tool failure that is safe to retry (network blip, 429, timeout). */
class TransientToolError extends Error {}

/**
 * What the guarded loop reports back to the caller.
 *
 * status is one of:
 *   "success"        — terminal message AND goalCheck(message) is true
 *   "incomplete"     — terminal message but goalCheck is false
 *                      (e.g. the model asked a clarifying question)
 *   "stuck"          — detectStuck fired; diagnostic explains why
 *   "timeout"        — wall-clock budget exceeded (per the injected clock)
 *   "maxIterations"  — iteration cap reached without a terminal message
 */
interface LoopResult {
  status: "success" | "incomplete" | "stuck" | "timeout" | "maxIterations";
  finalMessage: string | null;
  iterations: number;
  diagnostic?: string;
}

interface Model {
  decide(history: string[]): Promise<Decision>;
}

// ---------------------------------------------------------------------------
// Clocks  (provided — do not edit)
// ---------------------------------------------------------------------------

interface Clock {
  now(): number;
}

/**
 * Deterministic clock: every now() call returns the current time, then
 * advances it by `step` seconds. No real time passes — the timeout branch
 * becomes exactly testable. The loop contract: call now() ONCE to record the
 * start time, then ONCE at the top of each iteration.
 */
class FakeClock implements Clock {
  private t = 0;
  constructor(private step = 0) {}
  now(): number {
    const current = this.t;
    this.t += this.step;
    return current;
  }
}

/** Real wall-clock time (seconds), for the live (non---stub) path. */
class SystemClock implements Clock {
  now(): number {
    return Date.now() / 1000;
  }
}

// ---------------------------------------------------------------------------
// Tools  (provided — do not edit)
// ---------------------------------------------------------------------------

interface ToolWorld {
  tools: Record<string, HardenedTool>;
  outbox: Array<{ to: string; subject: string }>;
  stats: { sendAttempts: number; sendFailures: number };
}

/**
 * Build a fresh tool set per scenario.
 *   - `search` returns canned text (read-only, safe to repeat).
 *   - `send_email` appends to `outbox` — a SIDE EFFECT. With
 *     failFirstSend=true the FIRST attempt throws TransientToolError before
 *     anything is sent (the flaky wrapper).
 *   - `stats` counts send_email attempts/failures so the harness can prove
 *     how many times the side effect was really tried.
 */
function makeTools(failFirstSend = false): ToolWorld {
  const outbox: Array<{ to: string; subject: string }> = [];
  const stats = { sendAttempts: 0, sendFailures: 0 };
  let failuresLeft = failFirstSend ? 1 : 0;

  const search: HardenedTool = {
    name: "search",
    execute(args: ToolArgs): string {
      const query = String(args.query ?? "")
        .toLowerCase()
        .trim();
      if (query.includes("eiffel")) return "The Eiffel Tower is 330 metres tall.";
      if (query.includes("population of france"))
        return "France has a population of ~68 million (2024).";
      if (query.includes("capital of france")) return "The capital of France is Paris.";
      return `No result found for: ${query}`;
    },
  };

  const sendEmail: HardenedTool = {
    name: "send_email",
    execute(args: ToolArgs): string {
      stats.sendAttempts += 1;
      if (failuresLeft > 0) {
        failuresLeft -= 1;
        stats.sendFailures += 1;
        throw new TransientToolError(
          "SMTP connection dropped before send (safe to retry)",
        );
      }
      const to = String(args.to ?? "");
      outbox.push({ to, subject: String(args.subject ?? "") });
      return `email sent to ${to}`;
    },
  };

  return { tools: { search: search, send_email: sendEmail }, outbox, stats };
}

// ---------------------------------------------------------------------------
// Models  (provided — do not edit)
// ---------------------------------------------------------------------------

/**
 * Replays a fixed script of Decisions, ignoring the history. This is the
 * deterministic fake model: each scenario scripts exactly what a (mis)behaving
 * model would do, so YOUR guards are the only thing under test.
 */
class StubModel implements Model {
  private script: Decision[];
  constructor(script: Decision[]) {
    this.script = [...script];
  }
  async decide(_history: string[]): Promise<Decision> {
    return this.script.shift() ?? { message: "(stub script exhausted)" };
  }
}

/**
 * The real path: asks the provider (via llm-core) to emit ONE JSON object per
 * turn — {"tool": ..., "args": {...}} or {"message": ...} — and parses it into
 * a Decision. Never a hardcoded vendor.
 */
class LiveModel implements Model {
  readonly provider = getProvider();
  constructor(private goal: string) {}

  async decide(history: string[]): Promise<Decision> {
    const system = [
      "You control tools by replying with EXACTLY ONE JSON object and nothing else.",
      'To call a tool: {"tool": "<name>", "args": {...}}',
      "Tools:",
      '  search — looks up a fact. args: {"query": "<text>"}',
      '  send_email — sends an email. args: {"to": "<addr>", "subject": "<text>"}',
      'Only when the goal is fully accomplished, reply: {"message": "<short summary>"}',
    ].join("\n");
    const transcript = history.length > 0 ? history.join("\n") : "(nothing yet)";
    const user = `Goal: ${this.goal}\n\nWhat happened so far:\n${transcript}\n\nNext JSON:`;
    const messages: ChatMessage[] = [
      { role: "system", content: system },
      { role: "user", content: user },
    ];
    const result = await this.provider.chat(messages, {
      temperature: 0,
      maxTokens: 300,
    });
    const text = result.text;
    let payload: unknown;
    try {
      payload = JSON.parse(text.slice(text.indexOf("{"), text.lastIndexOf("}") + 1));
    } catch {
      return { message: text.trim() };
    }
    if (payload !== null && typeof payload === "object") {
      const obj = payload as Record<string, unknown>;
      if (typeof obj.tool === "string" && obj.tool) {
        return { tool: obj.tool, args: (obj.args as ToolArgs) ?? {} };
      }
      if ("message" in obj) return { message: String(obj.message) };
    }
    return { message: text.trim() };
  }
}

// ---------------------------------------------------------------------------
// Canonical JSON helper  (provided — do not edit)
// ---------------------------------------------------------------------------

/** JSON.stringify with object keys recursively sorted, so the same logical
 *  value always renders to the same string (unlike plain JSON.stringify,
 *  which preserves insertion order). Use it inside idempotencyKey(). */
function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const entries = Object.keys(obj)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${stableJson(obj[k])}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value);
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these four
// ---------------------------------------------------------------------------

/**
 * A STABLE key identifying one logical tool call.
 *
 * Two calls with the same tool and the same arguments must produce the same
 * key even if the args object was built in a different insertion order — and
 * different arguments must produce different keys. This key is used both as
 * the "signature" for stuck detection and as the dedupe key for
 * side-effecting tools.
 *
 * TODO: implement.
 *   - Combine the tool name and a canonical rendering of `args` into one
 *     string. Use the provided stableJson() helper — plain JSON.stringify
 *     preserves insertion order, which would break key stability.
 */
function idempotencyKey(toolName: string, args: ToolArgs): string {
  // TODO: implement the stable key
  throw new Error("TODO: implement idempotencyKey()");
}

/**
 * Detect a stuck agent from its recent call signatures.
 *
 * Two classic signals:
 *   1. Repetition — the last `window` signatures are all IDENTICAL.
 *   2. Oscillation — the last 4 signatures alternate A, B, A, B between two
 *      DISTINCT calls.
 *
 * Return a human-readable diagnostic string when stuck, else null.
 *
 * TODO: implement.
 *   - Repetition: with at least `window` calls, look at the last `window`
 *     signatures (Array.slice); if they are all the same value, return a
 *     diagnostic that names the repeated signature.
 *   - Oscillation: with at least 4 calls, take the last 4; if positions
 *     1 & 3 match, positions 2 & 4 match, and the two values differ,
 *     return a diagnostic naming both signatures.
 *   - Otherwise (including too few calls) return null.
 */
function detectStuck(recentCalls: string[], window = 3): string | null {
  // TODO: implement repetition + oscillation detection
  throw new Error("TODO: implement detectStuck()");
}

/**
 * Execute a tool with (a) at-most-once side effects and (b) one retry.
 *
 * - If this call's idempotency key is already in `executed`, do NOT run the
 *   tool again — return the recorded result.
 * - Otherwise run it; on TransientToolError retry ONCE (a second failure
 *   propagates to the caller).
 * - Record the successful result under the key before returning it.
 *
 * TODO: implement.
 *   - Compute this call's key with idempotencyKey().
 *   - Dedupe: if the key is already in `executed` (Map.get), return the
 *     recorded result WITHOUT running the tool again.
 *   - Run tool.execute(args) in a try/catch; if the caught error is a
 *     TransientToolError (instanceof), call it once more — any other error
 *     (and a second transient failure) must propagate to the caller.
 *   - Store the successful result in `executed` under the key, return it.
 */
function executeWithRetry(
  tool: HardenedTool,
  args: ToolArgs,
  executed: Map<string, string>,
): string {
  // TODO: implement dedupe + single retry
  throw new Error("TODO: implement executeWithRetry()");
}

/**
 * The guarded agent loop.
 *
 * Contract per iteration i = 1..maxIterations:
 *   1. Timeout guard: if clock.now() - start > maxSeconds, return a
 *      "timeout" LoopResult. Record `start` with ONE clock.now() call before
 *      the loop; call now() exactly ONCE per iteration.
 *   2. decision = await model.decide(history).
 *   3. Terminal message? Then goalCheck(message) decides between "success"
 *      and "incomplete" (terminal message != goal complete).
 *   4. Tool call: append its idempotencyKey signature to recentCalls, run
 *      detectStuck — if it fires, return "stuck" with the diagnostic BEFORE
 *      executing (don't waste the call).
 *   5. Otherwise execute via executeWithRetry and append the action +
 *      observation to `history`.
 * Falls out of the loop -> "maxIterations".
 *
 * Tips:
 *   - State to initialise before the loop: a `history: string[]` transcript,
 *     a `recentCalls: string[]` of signatures, an
 *     `executed: Map<string, string>` dedupe map, and the recorded start time.
 *   - An unknown tool name should push an error observation to `history`
 *     and continue — not crash.
 *   - The "stuck" LoopResult carries detectStuck's diagnostic; every
 *     LoopResult carries the iteration number it exited on.
 */
async function runAgentLoop(
  model: Model,
  tools: Record<string, HardenedTool>,
  goalCheck: (message: string) => boolean,
  opts: { maxIterations: number; maxSeconds: number; clock: Clock },
): Promise<LoopResult> {
  // TODO: implement the guarded loop per the contract in the doc comment
  throw new Error("TODO: implement runAgentLoop()");
}

// ---------------------------------------------------------------------------
// Scenario harness  (provided — do not edit)
// ---------------------------------------------------------------------------

const SEND_ARGS = { to: "learner@example.com", subject: "Eiffel Tower height" };

async function runScenario(
  name: string,
  script: Decision[],
  tools: Record<string, HardenedTool>,
  goalCheck: (message: string) => boolean,
  opts?: { maxIterations?: number; maxSeconds?: number; clock?: Clock },
): Promise<LoopResult> {
  const result = await runAgentLoop(new StubModel(script), tools, goalCheck, {
    maxIterations: opts?.maxIterations ?? 10,
    maxSeconds: opts?.maxSeconds ?? 1000,
    clock: opts?.clock ?? new FakeClock(1),
  });
  console.log(`  [${name}]`);
  console.log(
    `    status='${result.status}' iterations=${result.iterations}` +
      (result.diagnostic ? ` diagnostic='${result.diagnostic}'` : ""),
  );
  return result;
}

async function runStubScenarios(): Promise<void> {
  console.log("=== Task 6: harden the loop — STUB (offline) ===\n");
  console.log("Scenarios:");

  // ── A. Clean success: search -> send_email -> terminal, goal met ────────
  const worldA = makeTools();
  const rSuccess = await runScenario(
    "success",
    [
      { tool: "search", args: { query: "eiffel tower height" } },
      { tool: "send_email", args: { ...SEND_ARGS } },
      { message: "Done — I looked up the height and emailed it." },
    ],
    worldA.tools,
    () => worldA.outbox.length === 1, // goal = the email really went out
  );

  // ── B. Terminal message that is NOT success (clarifying question) ───────
  const worldB = makeTools();
  const rClarify = await runScenario(
    "clarifying question",
    [
      { tool: "search", args: { query: "eiffel tower height" } },
      { message: "Which email address should I send the answer to?" },
    ],
    worldB.tools,
    () => worldB.outbox.length === 1,
  );

  // ── C. Stuck: the identical search repeated 3x (cap is 10) ──────────────
  const worldC = makeTools();
  const rStuck = await runScenario(
    "stuck (repetition)",
    [
      { tool: "search", args: { query: "eiffel tower height" } },
      { tool: "search", args: { query: "how tall is the eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      // padding — never reached if detectStuck fires at iteration 5:
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
      { tool: "search", args: { query: "eiffel tower" } },
    ],
    worldC.tools,
    () => false,
  );

  // ── D. Stuck: A/B/A/B oscillation between two distinct calls ────────────
  const worldD = makeTools();
  const oscA: Decision = { tool: "search", args: { query: "capital of france" } };
  const oscB: Decision = { tool: "search", args: { query: "population of france" } };
  const rOsc = await runScenario(
    "stuck (oscillation)",
    [oscA, oscB, oscA, oscB, oscA, oscB, oscA, oscB],
    worldD.tools,
    () => false,
  );

  // ── E. Timeout via the fake clock (10s per tick, 35s budget) ────────────
  const worldE = makeTools();
  const rTimeout = await runScenario(
    "timeout (fake clock)",
    Array.from({ length: 12 }, (_, i) => ({
      tool: "search",
      args: { query: `fact ${i}` },
    })),
    worldE.tools,
    () => false,
    { maxIterations: 50, maxSeconds: 35, clock: new FakeClock(10) },
  );

  // ── F. Idempotency: transient failure + retry + duplicate call ──────────
  // First send_email attempt throws TransientToolError (nothing sent), the
  // retry succeeds. The model then re-issues the SAME logical call with the
  // args in a different key order — the harness must dedupe it.
  const worldF = makeTools(true);
  const rIdem = await runScenario(
    "idempotency (flaky send_email)",
    [
      { tool: "search", args: { query: "eiffel tower height" } },
      { tool: "send_email", args: { ...SEND_ARGS } },
      { tool: "send_email", args: { subject: SEND_ARGS.subject, to: SEND_ARGS.to } },
      { message: "The report email has been sent." },
    ],
    worldF.tools,
    () => worldF.outbox.length === 1,
  );
  console.log(
    `    outbox=${JSON.stringify(worldF.outbox)} sendAttempts=${worldF.stats.sendAttempts}`,
  );

  // ── Key stability (unit check) ───────────────────────────────────────────
  const k1 = idempotencyKey("send_email", { a: 1, b: [2, 3] });
  const k2 = idempotencyKey("send_email", { b: [2, 3], a: 1 });
  const k3 = idempotencyKey("send_email", { a: 1, b: [2, 4] });

  // ── Acceptance ───────────────────────────────────────────────────────────
  const checks: Array<[boolean, string]> = [
    [
      rSuccess.status === "success" &&
        rSuccess.iterations === 3 &&
        worldA.outbox.length === 1,
      "success run: goalCheck saw the sent email -> status 'success' in 3 iterations",
    ],
    [
      rClarify.status === "incomplete" && worldB.outbox.length === 0,
      "clarifying terminal message -> status 'incomplete' (terminal message != success)",
    ],
    [
      rStuck.status === "stuck" &&
        rStuck.iterations === 5 &&
        Boolean(rStuck.diagnostic),
      `stuck (repetition) exits at iteration ${rStuck.iterations} of cap 10 with a diagnostic`,
    ],
    [
      rOsc.status === "stuck" && rOsc.iterations === 4,
      "stuck (A/B/A/B oscillation) exits at iteration 4 with a diagnostic",
    ],
    [
      rTimeout.status === "timeout" && rTimeout.iterations < 50,
      "timeout run exits via the fake clock, well before the iteration cap",
    ],
    [
      rIdem.status === "success" &&
        worldF.outbox.length === 1 &&
        worldF.stats.sendAttempts === 2,
      "idempotency: EXACTLY 1 email in the outbox (1 transient failure + 1 retry; " +
        "duplicate call deduped)",
    ],
    [
      k1 === k2 && k1 !== k3,
      "idempotencyKey is arg-order-stable and argument-sensitive",
    ],
  ];

  console.log("\nAcceptance:");
  for (const [ok, label] of checks) {
    console.log(`  [${ok ? "x" : " "}] ${label}`);
  }
  if (checks.every(([ok]) => ok)) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

async function runLive(): Promise<void> {
  console.log("=== Task 6: harden the loop — REAL (getProvider) ===\n");
  const world = makeTools(true);
  const goal =
    "Find the height of the Eiffel Tower with the search tool, email it to " +
    "learner@example.com with the send_email tool, then reply with a short summary.";
  const model = new LiveModel(goal);
  console.log(`Provider: ${model.provider.name} / ${model.provider.chatModel}`);
  const result = await runAgentLoop(
    model,
    world.tools,
    () => world.outbox.length >= 1,
    {
      maxIterations: 10,
      maxSeconds: 120,
      clock: new SystemClock(),
    },
  );
  console.log(`\nstatus='${result.status}' iterations=${result.iterations}`);
  if (result.finalMessage) console.log(`final message: ${result.finalMessage}`);
  if (result.diagnostic) console.log(`diagnostic: ${result.diagnostic}`);
  console.log(
    `outbox: ${JSON.stringify(world.outbox)} (send attempts: ${world.stats.sendAttempts})`,
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  if (process.argv.includes("--stub")) {
    await runStubScenarios();
  } else {
    await runLive();
  }
}

main().catch(console.error);
