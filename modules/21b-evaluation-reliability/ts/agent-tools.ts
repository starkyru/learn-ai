/**
 * agent-tools.ts — deterministic fake tools + clock (Module 21b, Task 4).
 * Port of agent_tools.py; behaviour and recorded effects are byte-identical.
 */

export class ToolError extends Error {}
export class ToolTimeout extends Error {}

/** Injectable deterministic clock (integer ticks); no wall-clock time. */
export class Clock {
  private t: number;
  constructor(start = 0) {
    this.t = Math.trunc(start);
  }
  now(): number {
    return this.t;
  }
  advance(dt: number): void {
    this.t += Math.trunc(dt);
  }
}

export interface Effect {
  type: string;
  to: unknown;
  subject: unknown;
  idempotency_key: unknown;
}

export interface AgentEnv {
  clock: Clock;
  flakyFailures: number;
  effects: Effect[];
  idempotency: Map<string, { type: string; effect_id: number }>;
  callCounts: Map<string, number>;
}

export function makeEnv(flakyFailures = 0): AgentEnv {
  return {
    clock: new Clock(),
    flakyFailures,
    effects: [],
    idempotency: new Map(),
    callCounts: new Map(),
  };
}

export interface ToolMeta {
  side_effecting: boolean;
  cost: number;
  latency: number;
}

export const TOOLS: Record<string, ToolMeta> = {
  lookup_account: { side_effecting: false, cost: 1, latency: 1 },
  flaky_fetch: { side_effecting: false, cost: 1, latency: 2 },
  slow_query: { side_effecting: false, cost: 1, latency: 5 },
  send_email: { side_effecting: true, cost: 2, latency: 3 },
};

const ACCOUNTS: Record<string, { balance: number; owner: string }> = {
  "acc-1": { balance: 100, owner: "owner@example.com" },
};

export function isKnownTool(name: string): boolean {
  return name in TOOLS;
}

export function isSideEffecting(name: string): boolean {
  return TOOLS[name]?.side_effecting ?? false;
}

export function runTool(
  name: string,
  env: AgentEnv,
  args: Record<string, unknown>,
): Record<string, unknown> {
  const meta = TOOLS[name];
  env.clock.advance(meta.latency);
  env.callCounts.set(name, (env.callCounts.get(name) ?? 0) + 1);

  if (name === "lookup_account") {
    const account = ACCOUNTS[args.account_id as string];
    if (account === undefined)
      throw new ToolError(`unknown account ${String(args.account_id)}`);
    return { account_id: args.account_id, ...account };
  }
  if (name === "flaky_fetch") {
    if (env.flakyFailures > 0) {
      env.flakyFailures -= 1;
      throw new ToolError("transient failure");
    }
    return { report: args.report, status: "ok" };
  }
  if (name === "slow_query") {
    throw new ToolTimeout("tool exceeded its deadline");
  }
  if (name === "send_email") {
    const key = args.idempotency_key as string | undefined;
    // Only a TRUTHY key dedups. A missing/falsy key means NO dedup, so two
    // distinct keyless requests each produce their own effect (a falsy sentinel
    // must never collapse unrelated requests into one "replay").
    if (key && env.idempotency.has(key)) {
      return { ...env.idempotency.get(key), replayed: true };
    }
    env.effects.push({
      type: "email",
      to: args.to,
      subject: args.subject,
      idempotency_key: key ?? null,
    });
    const stored = { type: "email", effect_id: env.effects.length };
    if (key) env.idempotency.set(key, stored);
    return { ...stored, replayed: false };
  }
  throw new ToolError(`unknown tool ${name}`);
}
