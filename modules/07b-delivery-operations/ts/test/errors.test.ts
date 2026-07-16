/** Error responses never leak provider details, raw input, or secrets. */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type {
  ChatMessage,
  ChatResult,
  EmbeddingResult,
  LLMProvider,
} from "@learn-ai/llm-core";

import { buildApp } from "../src/app.js";
import {
  bearer,
  BufferSink,
  FakeProvider,
  makeConfig,
  seedIdentity,
  VIEWER_A,
} from "./fakes.js";

/** A fake provider whose chat() rejects — models a provider SDK failure.
 * An optional statusCode models a thrown http-error (e.g. a 502 upstream). */
class RaisingProvider implements LLMProvider {
  readonly name = "fake";
  readonly chatModel = "fake-chat";
  readonly embedModel = "fake-embed";

  constructor(
    private readonly message: string,
    private readonly statusCode?: number,
  ) {}

  async chat(): Promise<ChatResult> {
    const err = new Error(this.message);
    if (this.statusCode !== undefined) {
      (err as Error & { statusCode: number }).statusCode = this.statusCode;
    }
    throw err;
  }

  async *chatStream(_messages: ChatMessage[]): AsyncIterable<string> {
    yield "";
  }

  async embed(_input: string[]): Promise<EmbeddingResult> {
    throw new Error("no embed");
  }
}

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-errors-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

test("a provider exception returns a bounded 502 without leaking", async () => {
  const original = process.env.OPENAI_API_KEY;
  process.env.OPENAI_API_KEY = "FAKE-OPENAI-KEY-ts";
  const sink = new BufferSink();
  try {
    const dbPath = join(dir, "err.sqlite");
    seedIdentity(dbPath); // /ask is protected: authenticate to reach the handler
    const app = buildApp({
      // No retries so the raising provider is called once (keeps the test fast);
      // the reliability envelope maps a provider failure to an UPSTREAM error (502).
      config: makeConfig(dbPath, { providerMaxRetries: 0 }),
      provider: new RaisingProvider("upstream 401 using FAKE-OPENAI-KEY-ts"),
      logSink: sink,
    });
    const res = await app.inject({
      method: "POST",
      url: "/ask",
      headers: { ...bearer(VIEWER_A), "x-request-id": "rid-e" },
      payload: { question: "hi" },
    });
    await app.close();

    expect(res.statusCode).toBe(502);
    expect(res.json()).toEqual({ error: "internal server error", request_id: "rid-e" });
    expect(res.headers["x-request-id"]).toBe("rid-e");
    // Neither the provider message nor the credential reaches the response OR logs.
    const logs = sink.text();
    for (const sinkText of [res.payload, logs]) {
      expect(sinkText).not.toContain("upstream 401");
      expect(sinkText).not.toContain("FAKE-OPENAI-KEY-ts");
    }
    // A bounded observability event names the failure MODE, not the raw cause.
    expect(logs).toContain("provider_call_failed");
    expect(logs).toContain("ProviderUnavailable");
  } finally {
    if (original === undefined) delete process.env.OPENAI_API_KEY;
    else process.env.OPENAI_API_KEY = original;
  }
});

test("a rejected body does not echo the input in the response", async () => {
  const provider = new FakeProvider();
  const dbPath = join(dir, "err2.sqlite");
  seedIdentity(dbPath); // auth (preValidation) runs before the 400 body check
  const app = buildApp({
    config: makeConfig(dbPath),
    provider,
    logSink: new BufferSink(),
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi", leaked: "SENTINEL-TS-INPUT" }, // unknown field
  });
  await app.close();

  expect(res.statusCode).toBe(400);
  expect(res.json()).toEqual({
    error: "bad request",
    request_id: res.headers["x-request-id"],
  });
  expect(res.payload).not.toContain("SENTINEL-TS-INPUT");
  // The rejected request never reached the provider.
  expect(provider.calls).toHaveLength(0);
});

test("a provider error carrying a status is still a bounded 502 with no detail leak", async () => {
  const sink = new BufferSink();
  const dbPath = join(dir, "err3.sqlite");
  seedIdentity(dbPath);
  const app = buildApp({
    config: makeConfig(dbPath, { providerMaxRetries: 0 }),
    // A provider throwing an http-error whose message carries a secret detail. The
    // reliability envelope treats ANY provider failure as an upstream error (502)
    // and drops the raw detail — it does not pass the provider's status through.
    provider: new RaisingProvider("SENTINEL-HTTP-DETAIL", 502),
    logSink: sink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi" },
  });
  await app.close();

  expect(res.statusCode).toBe(502);
  expect(res.json()).toEqual({
    error: "internal server error",
    request_id: res.headers["x-request-id"],
  });
  // The raw error message reaches neither the client nor the logs.
  expect(res.payload).not.toContain("SENTINEL-HTTP-DETAIL");
  expect(sink.text()).not.toContain("SENTINEL-HTTP-DETAIL");
  expect(sink.text()).toContain("provider_call_failed");
});
