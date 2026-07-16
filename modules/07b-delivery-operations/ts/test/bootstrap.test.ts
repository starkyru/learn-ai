/** bootstrap() fails fast on a bad provider credential, before the port binds. */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { LLMProvider } from "@learn-ai/llm-core";

import { bootstrap } from "../src/app.js";
import { discardSink, FakeProvider, makeConfig } from "./fakes.js";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-bootstrap-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

test("bootstrap rejects when the provider build fails", async () => {
  // Simulate a missing credential: the real buildDefaultProvider throws for a
  // provider whose key is absent. bootstrap must surface that at startup.
  const failing = async (): Promise<LLMProvider> => {
    throw new Error("missing OPENAI_API_KEY");
  };
  await expect(
    bootstrap({
      config: makeConfig(join(dir, "boot.sqlite")),
      providerFactory: failing,
    }),
  ).rejects.toThrow("missing OPENAI_API_KEY");
});

test("bootstrap skips the factory when a provider is injected", async () => {
  const boom = async (): Promise<LLMProvider> => {
    throw new Error("providerFactory must not be called when a provider is injected");
  };
  const app = await bootstrap({
    config: makeConfig(join(dir, "boot2.sqlite")),
    provider: new FakeProvider(),
    providerFactory: boom,
    logSink: discardSink,
  });
  const res = await app.inject({ method: "GET", url: "/healthz" });
  await app.close();

  expect(res.statusCode).toBe(200);
});
