/** Logs are structured JSON, carry the correlation id, and never leak secrets. */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { buildApp } from "../src/app.js";
import { createLogger } from "../src/logging.js";
import {
  bearer,
  BufferSink,
  FakeProvider,
  makeConfig,
  seedIdentity,
  VIEWER_A,
} from "./fakes.js";

const SECRET = "SENTINEL-SECRET-do-not-log-9f3a";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-log-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

test("a configured secret never appears in the emitted logs", async () => {
  const sink = new BufferSink();
  const dbPath = join(dir, "log.sqlite");
  seedIdentity(dbPath); // /ask is protected: authenticate as a viewer
  const app = buildApp({
    config: makeConfig(dbPath, { providerApiKey: SECRET }),
    provider: new FakeProvider(),
    logSink: sink,
  });
  await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "hi" },
  });
  await app.close();

  const output = sink.text();
  expect(output).not.toContain(SECRET);
  expect(output).toContain("[REDACTED]");
});

test("the startup config event is emitted as JSON with the provider name", async () => {
  const sink = new BufferSink();
  const app = buildApp({
    config: makeConfig(join(dir, "log2.sqlite")),
    provider: new FakeProvider(),
    logSink: sink,
  });
  await app.close();

  const configured = sink.lines().filter((l) => l.msg === "service_configured");
  expect(configured).toHaveLength(1);
  expect(configured[0].provider).toBe("ollama");
  expect(configured[0].level).toBe("info");
});

test("the request_completed log carries the correlation id and status", async () => {
  const sink = new BufferSink();
  const app = buildApp({
    config: makeConfig(join(dir, "log3.sqlite")),
    provider: new FakeProvider(),
    logSink: sink,
  });
  await app.inject({
    method: "GET",
    url: "/healthz",
    headers: { "x-request-id": "trace-777" },
  });
  await app.close();

  const completed = sink.lines().filter((l) => l.msg === "request_completed");
  expect(completed).toHaveLength(1);
  expect(completed[0].request_id).toBe("trace-777");
  expect(completed[0].path).toBe("/healthz");
  expect(completed[0].status).toBe(200);
});

test("createLogger scrubs a registered secret from a free-text message", () => {
  // Direct unit test of the secret scrub — the net that catches a secret leaked
  // into `msg`, which the key-based `redact` cannot reach.
  const sink = new BufferSink();
  const logger = createLogger({ sink });
  logger.registerSecret("hunter2-secret");
  logger.info("leaked hunter2-secret in the message", { safe: 1 });

  const output = sink.text();
  expect(output).not.toContain("hunter2-secret");
  expect(output).toContain("[REDACTED]");
  // A non-registered value is untouched.
  expect(output).toContain("leaked");
});

test("redact masks a credential nested inside an array", () => {
  const sink = new BufferSink();
  const logger = createLogger({ sink });
  logger.info("evt", { payload: [{ api_key: "should-be-masked", keep: 1 }] });

  const line = sink.lines()[0];
  expect(line.payload).toEqual([{ api_key: "[REDACTED]", keep: 1 }]);
  expect(sink.text()).not.toContain("should-be-masked");
});
