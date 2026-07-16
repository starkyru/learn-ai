/**
 * agent-tools.test.ts — deterministic fake tools + clock (exact assertions).
 * Mirrors test_agent_tools.py.
 */

import {
  Clock,
  isSideEffecting,
  makeEnv,
  runTool,
  ToolError,
  ToolTimeout,
} from "./agent-tools.js";

test("clock advances deterministically", () => {
  const clock = new Clock();
  expect(clock.now()).toBe(0);
  clock.advance(3);
  clock.advance(2);
  expect(clock.now()).toBe(5);
});

test("lookup is read-only and idempotent", () => {
  const env = makeEnv();
  const r1 = runTool("lookup_account", env, { account_id: "acc-1" });
  const r2 = runTool("lookup_account", env, { account_id: "acc-1" });
  expect(r1).toEqual({ account_id: "acc-1", balance: 100, owner: "owner@example.com" });
  expect(r2).toEqual(r1);
  expect(env.effects).toEqual([]);
  expect(env.clock.now()).toBe(2);
});

test("lookup unknown account throws", () => {
  expect(() => runTool("lookup_account", makeEnv(), { account_id: "acc-999" })).toThrow(
    ToolError,
  );
});

test("flaky_fetch fails then succeeds", () => {
  const env = makeEnv(1);
  expect(() => runTool("flaky_fetch", env, { report: "daily" })).toThrow(ToolError);
  expect(runTool("flaky_fetch", env, { report: "daily" })).toEqual({
    report: "daily",
    status: "ok",
  });
});

test("slow_query times out", () => {
  expect(() => runTool("slow_query", makeEnv(), { query: "big" })).toThrow(ToolTimeout);
});

test("send_email records one effect", () => {
  const env = makeEnv();
  const result = runTool("send_email", env, {
    to: "a@b",
    subject: "hi",
    idempotency_key: "k1",
  });
  expect(result.replayed).toBe(false);
  expect(env.effects).toEqual([
    { type: "email", to: "a@b", subject: "hi", idempotency_key: "k1" },
  ]);
});

test("send_email is idempotent per key (duplicate -> ONE effect)", () => {
  const env = makeEnv();
  const args = { to: "a@b", subject: "hi", idempotency_key: "k1" };
  runTool("send_email", env, args);
  const replay = runTool("send_email", env, args);
  expect(replay.replayed).toBe(true);
  expect(env.effects.length).toBe(1);
});

test("send_email different keys produce two effects", () => {
  const env = makeEnv();
  runTool("send_email", env, { to: "a@b", subject: "hi", idempotency_key: "k1" });
  runTool("send_email", env, { to: "a@b", subject: "hi", idempotency_key: "k2" });
  expect(env.effects.length).toBe(2);
});

test("send_email without a key never dedups (falsy key is not a replay)", () => {
  // Regression guard: a missing/falsy idempotency key must NOT dedup — two
  // keyless requests are distinct effects, never collapsed into one "replay".
  const env = makeEnv();
  const first = runTool("send_email", env, { to: "a@b", subject: "one" });
  const second = runTool("send_email", env, { to: "a@b", subject: "two" });
  expect(first.replayed).toBe(false);
  expect(second.replayed).toBe(false);
  expect(env.effects.length).toBe(2);
});

test("tool metadata marks side effects", () => {
  expect(isSideEffecting("send_email")).toBe(true);
  expect(isSideEffecting("lookup_account")).toBe(false);
});
