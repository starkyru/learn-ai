/** POST /ask with an injected fake provider.
 *
 * `/ask` is protected (T2.3): a request needs a valid bearer token, and the
 * body validation (400) / size cap (413) are only reached once authenticated
 * OR reject before auth runs. Fastify validates the body BEFORE the auth
 * preHandler, so the 400/413 tests need neither a token nor a seeded DB; the
 * success tests authenticate as a seeded viewer. */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { ChatResult, LLMProvider } from "@learn-ai/llm-core";

import { buildApp } from "../src/app.js";
import {
  bearer,
  discardSink,
  FakeProvider,
  makeConfig,
  seedIdentity,
  VIEWER_A,
} from "./fakes.js";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-ask-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

/** A migrated + seeded DB path for a test that authenticates. */
function seededDb(name: string): string {
  const path = join(dir, name);
  seedIdentity(path);
  return path;
}

test("returns the provider answer and echoes the inbound request id", async () => {
  const provider = new FakeProvider("HELLO-FROM-FAKE");
  const app = buildApp({
    config: makeConfig(seededDb("ask.sqlite")),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: { ...bearer(VIEWER_A), "x-request-id": "req-abc-123" },
    payload: { question: "what is 07b about?" },
  });
  await app.close();

  expect(res.statusCode).toBe(200);
  expect(res.json()).toEqual({ answer: "HELLO-FROM-FAKE", request_id: "req-abc-123" });
  expect(res.headers["x-request-id"]).toBe("req-abc-123");
});

test("generates a request id when none is supplied", async () => {
  const app = buildApp({
    config: makeConfig(seededDb("ask2.sqlite")),
    provider: new FakeProvider("X"),
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi" },
  });
  await app.close();

  expect(res.statusCode).toBe(200);
  const generated = res.json().request_id as string;
  expect(generated.length).toBeGreaterThan(0);
  expect(res.headers["x-request-id"]).toBe(generated);
});

test("actually calls the provider with the user's question", async () => {
  const provider = new FakeProvider("Y");
  const app = buildApp({
    config: makeConfig(seededDb("ask3.sqlite")),
    provider,
    logSink: discardSink,
  });
  await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "unique-question-marker" },
  });
  await app.close();

  expect(provider.calls).toHaveLength(1);
  const userMessages = provider.calls[0]
    .filter((m) => m.role === "user")
    .map((m) => m.content);
  expect(userMessages).toEqual(["unique-question-marker"]);
});

test("rejects an empty question with 400 and does not call the provider", async () => {
  // Authenticated (auth's preValidation runs before schema validation), so the
  // 400 is reached — mirrors the Python 422 test that also carries a token.
  const provider = new FakeProvider("Z");
  const app = buildApp({
    config: makeConfig(seededDb("ask4.sqlite")),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "" },
  });
  await app.close();

  expect(res.statusCode).toBe(400);
  expect(provider.calls).toHaveLength(0);
});

test("rejects an over-length question with 400 and does not call the provider", async () => {
  const provider = new FakeProvider("Z");
  const app = buildApp({
    config: makeConfig(seededDb("ask5.sqlite")),
    provider,
    logSink: discardSink,
  });
  // 4001 chars > maxLength (4000); body is small enough to pass the size cap.
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "a".repeat(4001) },
  });
  await app.close();

  expect(res.statusCode).toBe(400);
  expect(provider.calls).toHaveLength(0);
});

// ── Reliability envelope at the HTTP boundary (Task 3) ──────────────────────

/** A provider whose chat blocks past the request deadline. */
class SlowProvider implements Pick<LLMProvider, "chat"> {
  constructor(private readonly delayMs: number) {}
  async chat(): Promise<ChatResult> {
    await new Promise((r) => setTimeout(r, this.delayMs));
    return { text: "late", model: "slow-chat" };
  }
}

/** A provider that always rejects, to drive the retry + circuit-breaker paths. */
class FailingProvider implements Pick<LLMProvider, "chat"> {
  calls = 0;
  async chat(): Promise<ChatResult> {
    this.calls += 1;
    throw new Error("provider down");
  }
}

test("a slow provider yields a bounded 504", async () => {
  const app = buildApp({
    config: makeConfig(seededDb("ask-slow.sqlite"), {
      requestTimeoutMs: 100,
      providerMaxRetries: 0,
    }),
    provider: new SlowProvider(1000) as unknown as LLMProvider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi" },
  });
  await app.close();
  expect(res.statusCode).toBe(504);
});

test("a rate-limited identity gets 429", async () => {
  const app = buildApp({
    config: makeConfig(seededDb("ask-rate.sqlite"), { rateLimitPerMinute: 1 }),
    provider: new FakeProvider("ok"),
    logSink: discardSink,
  });
  const first = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "one" },
  });
  const second = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "two" },
  });
  await app.close();
  expect(first.statusCode).toBe(200);
  expect(second.statusCode).toBe(429); // per-identity budget exhausted in the window
});

test("a provider outage opens the circuit (502 then 503, no second provider call)", async () => {
  const provider = new FailingProvider();
  const app = buildApp({
    config: makeConfig(seededDb("ask-circuit.sqlite"), {
      circuitFailureThreshold: 1,
      providerMaxRetries: 0,
    }),
    provider: provider as unknown as LLMProvider,
    logSink: discardSink,
  });
  const first = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "one" },
  });
  const second = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "two" },
  });
  await app.close();
  expect(first.statusCode).toBe(502); // provider failed -> upstream error
  expect(second.statusCode).toBe(503); // circuit now open -> fast fail
  expect(provider.calls).toBe(1); // the open circuit did not call the provider again
});

test("rejects an oversized body with 413 and does not call the provider", async () => {
  const provider = new FakeProvider("Z");
  const app = buildApp({
    config: makeConfig(join(dir, "ask6.sqlite")),
    provider,
    logSink: discardSink,
  });
  // ~70 KB body exceeds the 64 KB bodyLimit; Fastify rejects before parsing.
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    payload: { question: "a".repeat(70_000) },
  });
  await app.close();

  expect(res.statusCode).toBe(413);
  expect(provider.calls).toHaveLength(0);
});

test("rejects an unknown body field with 400 and does not call the provider", async () => {
  const provider = new FakeProvider("Z");
  const app = buildApp({
    config: makeConfig(seededDb("ask7.sqlite")),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi", role: "admin" }, // additionalProperties: false
  });
  await app.close();

  expect(res.statusCode).toBe(400);
  expect(provider.calls).toHaveLength(0);
});
