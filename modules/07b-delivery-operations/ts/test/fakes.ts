/**
 * Test doubles: the ONLY thing mocked is the external LLM provider boundary.
 * Everything else (config, logging, readiness, routing) is the real code.
 */

import type {
  ChatMessage,
  ChatOptions,
  ChatResult,
  EmbeddingResult,
  LLMProvider,
} from "@learn-ai/llm-core";

import type { Config } from "../src/config.js";
import { openDb } from "../src/db.js";
import type { LogSink } from "../src/logging.js";
import { applyPending } from "../src/migrations.js";

/** A deterministic, offline stand-in for a real llm-core provider. */
export class FakeProvider implements LLMProvider {
  readonly name = "fake";
  readonly chatModel = "fake-chat";
  readonly embedModel = "fake-embed";
  readonly calls: ChatMessage[][] = [];

  constructor(private readonly answer: string = "CANNED-ANSWER") {}

  async chat(messages: ChatMessage[], _options?: ChatOptions): Promise<ChatResult> {
    this.calls.push(messages);
    return { text: this.answer, model: this.chatModel };
  }

  async *chatStream(
    _messages: ChatMessage[],
    _options?: ChatOptions,
  ): AsyncIterable<string> {
    yield this.answer;
  }

  async embed(_input: string[]): Promise<EmbeddingResult> {
    throw new Error("FakeProvider does not embed");
  }
}

/** An in-memory log sink so tests can assert on emitted JSON lines. */
export class BufferSink implements LogSink {
  private readonly chunks: string[] = [];

  write(chunk: string): void {
    this.chunks.push(chunk);
  }

  text(): string {
    return this.chunks.join("");
  }

  lines(): Array<Record<string, unknown>> {
    return this.text()
      .split("\n")
      .filter((line) => line.length > 0)
      .map((line) => JSON.parse(line) as Record<string, unknown>);
  }
}

/** A log sink that discards output — for tests that do not assert on logs. */
export const discardSink: LogSink = { write() {} };

/** Build a full Config with test defaults and a chosen db path. */
export function makeConfig(dbPath: string, overrides: Partial<Config> = {}): Config {
  return {
    serviceEnv: "development",
    provider: "ollama",
    port: 8001,
    dbPath,
    requestTimeoutMs: 30000,
    providerMaxConcurrency: 8,
    rateLimitPerMinute: 60,
    providerMaxRetries: 2,
    circuitFailureThreshold: 5,
    circuitCooldownMs: 30000,
    logLevel: "info",
    ...overrides,
  };
}

// ── Synthetic identities + tenant-scoped corpus (TOY: the bearer token is the
//    user id). Two tenants; each with a viewer, and tenant A also has an operator.
export const TENANT_A = "tenant-a";
export const TENANT_B = "tenant-b";
export const VIEWER_A = "alice-viewer";
export const OPERATOR_A = "art-operator";
export const VIEWER_B = "bob-viewer";

// Both chunks share the query term "launch" but carry distinct markers, so a
// cross-tenant leak is detectable in BOTH directions.
export const RETRIEVAL_QUERY = "launch";
export const CHUNK_A_MARKER = "swordfish";
export const CHUNK_B_MARKER = "starfish";
export const CHUNK_A = `Alpha team launch note: the code word is ${CHUNK_A_MARKER}.`;
export const CHUNK_B = `Bravo team launch note: the code word is ${CHUNK_B_MARKER}.`;

/** Migrate + seed tenants, users (2 tenants; viewer+operator), docs, chunks. */
export function seedIdentity(dbPath: string): void {
  applyPending(dbPath);
  const db = openDb(dbPath);
  try {
    const tenants = db.prepare("INSERT INTO tenants (id, name) VALUES (?, ?)");
    tenants.run(TENANT_A, "Tenant A");
    tenants.run(TENANT_B, "Tenant B");

    const users = db.prepare(
      "INSERT INTO users (id, tenant_id, email, role) VALUES (?, ?, ?, ?)",
    );
    users.run(VIEWER_A, TENANT_A, "alice@a.test", "viewer");
    users.run(OPERATOR_A, TENANT_A, "art@a.test", "operator");
    users.run(VIEWER_B, TENANT_B, "bob@b.test", "viewer");

    const docs = db.prepare(
      "INSERT INTO documents (id, tenant_id, title) VALUES (?, ?, ?)",
    );
    docs.run("doc-a1", TENANT_A, "A doc");
    docs.run("doc-b1", TENANT_B, "B doc");

    const chunks = db.prepare(
      "INSERT INTO chunks (id, tenant_id, document_id, ordinal, content) VALUES (?, ?, ?, ?, ?)",
    );
    chunks.run("chunk-a1", TENANT_A, "doc-a1", 0, CHUNK_A);
    chunks.run("chunk-b1", TENANT_B, "doc-b1", 0, CHUNK_B);
  } finally {
    db.close();
  }
}

/** An `Authorization: Bearer <token>` header (TOY: the token is the user id). */
export function bearer(token: string): Record<string, string> {
  return { authorization: `Bearer ${token}` };
}
