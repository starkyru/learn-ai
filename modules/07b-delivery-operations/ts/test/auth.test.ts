/** Identity, RBAC, tenant-safe retrieval, and audit (T2.3). */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { buildApp } from "../src/app.js";
import { openDb } from "../src/db.js";
import { retrieve } from "../src/retrieval.js";
import {
  bearer,
  CHUNK_A_MARKER,
  CHUNK_B_MARKER,
  discardSink,
  FakeProvider,
  makeConfig,
  OPERATOR_A,
  RETRIEVAL_QUERY,
  seedIdentity,
  TENANT_A,
  TENANT_B,
  VIEWER_A,
} from "./fakes.js";

let dir: string;
let seq = 0;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-auth-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

/** A fresh, migrated + seeded DB path for one test (isolated from the others). */
function seededDb(): string {
  const path = join(dir, `auth-${seq++}.sqlite`);
  seedIdentity(path);
  return path;
}

function auditRows(dbPath: string): Array<Record<string, unknown>> {
  const db = openDb(dbPath);
  try {
    return db
      .prepare(
        "SELECT actor, tenant_id, action, decision, request_id FROM audit_events " +
          "ORDER BY created_at, id",
      )
      .all() as Array<Record<string, unknown>>;
  } finally {
    db.close();
  }
}

function documentCount(dbPath: string, tenantId: string): number {
  const db = openDb(dbPath);
  try {
    const row = db
      .prepare("SELECT COUNT(*) AS n FROM documents WHERE tenant_id = ?")
      .get(tenantId) as { n: number };
    return Number(row.n);
  } finally {
    db.close();
  }
}

// ── Authentication (401) ────────────────────────────────────────────────────

test("an unauthenticated /ask returns 401 and never reaches the provider", async () => {
  const provider = new FakeProvider();
  const app = buildApp({
    config: makeConfig(seededDb()),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    payload: { question: "launch" },
  });
  await app.close();

  expect(res.statusCode).toBe(401);
  // Enforcement is BEFORE retrieval/generation: the provider was never called.
  expect(provider.calls).toHaveLength(0);
});

test("an invalid token returns 401", async () => {
  const app = buildApp({
    config: makeConfig(seededDb()),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer("ghost-user"),
    payload: { question: "launch" },
  });
  await app.close();
  expect(res.statusCode).toBe(401);
});

test("auth runs before body validation: an unauthenticated bad-body request is 401", async () => {
  // The body ({ question: "" }) would earn a 400 on its own; proving 401 here
  // shows auth gates BEFORE validation (parity with the Python 422-vs-401 order).
  const provider = new FakeProvider();
  const app = buildApp({
    config: makeConfig(seededDb()),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    payload: { question: "" }, // invalid body AND no token
  });
  await app.close();
  expect(res.statusCode).toBe(401); // auth first — NOT the 400 the body would earn
  expect(provider.calls).toHaveLength(0);
});

test("an authenticated /ask succeeds", async () => {
  const app = buildApp({
    config: makeConfig(seededDb()),
    provider: new FakeProvider("HELLO"),
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: "launch" },
  });
  await app.close();
  expect(res.statusCode).toBe(200);
  expect(res.json().answer).toBe("HELLO");
});

// ── 401 vs 403 are distinct ─────────────────────────────────────────────────

test("401 (unauthenticated) and 403 (wrong role) are distinct on /documents", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  const unauth = await app.inject({
    method: "POST",
    url: "/documents",
    payload: { title: "x" },
  });
  const forbidden = await app.inject({
    method: "POST",
    url: "/documents",
    headers: bearer(VIEWER_A), // a valid identity, but a viewer
    payload: { title: "x" },
  });
  await app.close();

  expect(unauth.statusCode).toBe(401);
  expect(forbidden.statusCode).toBe(403);
  expect(unauth.statusCode).not.toBe(forbidden.statusCode);
});

// ── RBAC (viewer denied, operator allowed) ──────────────────────────────────

test("a viewer cannot create a document and none is written", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  const before = documentCount(dbPath, TENANT_A);
  const res = await app.inject({
    method: "POST",
    url: "/documents",
    headers: bearer(VIEWER_A),
    payload: { title: "viewer-doc" },
  });
  await app.close();

  expect(res.statusCode).toBe(403);
  // The role check gates the WRITE, not just the response: no document created.
  expect(documentCount(dbPath, TENANT_A)).toBe(before);
});

test("an operator can create a document in its own tenant", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  const before = documentCount(dbPath, TENANT_A);
  const res = await app.inject({
    method: "POST",
    url: "/documents",
    headers: bearer(OPERATOR_A),
    payload: { title: "operator-doc" },
  });
  await app.close();

  expect(res.statusCode).toBe(201);
  const id = res.json().id as string;
  expect(id.length).toBeGreaterThan(0);
  expect(documentCount(dbPath, TENANT_A)).toBe(before + 1);
  // The new document belongs to the OPERATOR's tenant.
  const db = openDb(dbPath);
  const row = db.prepare("SELECT tenant_id FROM documents WHERE id = ?").get(id) as {
    tenant_id: string;
  };
  db.close();
  expect(row.tenant_id).toBe(TENANT_A);
});

// ── Tenant-safe retrieval (load-bearing) ────────────────────────────────────

test("retrieve() is tenant-scoped in both directions", () => {
  const dbPath = seededDb();
  // Both chunks match "launch". Each tenant sees only its own marker.
  const tenantA = retrieve(dbPath, TENANT_A, RETRIEVAL_QUERY)
    .map((c) => c.content)
    .join(" ");
  const tenantB = retrieve(dbPath, TENANT_B, RETRIEVAL_QUERY)
    .map((c) => c.content)
    .join(" ");

  expect(tenantA).toContain(CHUNK_A_MARKER);
  expect(tenantA).not.toContain(CHUNK_B_MARKER);
  expect(tenantB).toContain(CHUNK_B_MARKER);
  expect(tenantB).not.toContain(CHUNK_A_MARKER);
});

test("/ask only uses the caller's tenant context", async () => {
  const provider = new FakeProvider();
  const app = buildApp({
    config: makeConfig(seededDb()),
    provider,
    logSink: discardSink,
  });
  const res = await app.inject({
    method: "POST",
    url: "/ask",
    headers: bearer(VIEWER_A),
    payload: { question: RETRIEVAL_QUERY },
  });
  await app.close();

  expect(res.statusCode).toBe(200);
  expect(provider.calls).toHaveLength(1);
  const system = provider.calls[0].find((m) => m.role === "system")!.content;
  expect(system).toContain(CHUNK_A_MARKER); // tenant A's chunk was retrieved
  expect(system).not.toContain(CHUNK_B_MARKER); // tenant B's matching chunk was NOT
});

// ── Audit ───────────────────────────────────────────────────────────────────

test("audit records an allow for /ask without sensitive content", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  await app.inject({
    method: "POST",
    url: "/ask",
    headers: { ...bearer(VIEWER_A), "x-request-id": "rid-ask" },
    payload: { question: `tell me about ${RETRIEVAL_QUERY} SENSITIVE-QUESTION` },
  });
  await app.close();

  const allow = auditRows(dbPath).filter(
    (r) => r.decision === "allow" && r.action === "POST /ask",
  );
  expect(allow).toHaveLength(1);
  expect(allow[0].actor).toBe(VIEWER_A);
  expect(allow[0].tenant_id).toBe(TENANT_A);
  expect(allow[0].request_id).toBe("rid-ask");
  // The audit records who/what/decision — never the question content.
  for (const value of Object.values(allow[0])) {
    expect(String(value)).not.toContain("SENSITIVE-QUESTION");
  }
});

test("audit records a deny for a forbidden write", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  await app.inject({
    method: "POST",
    url: "/documents",
    headers: { ...bearer(VIEWER_A), "x-request-id": "rid-deny" },
    payload: { title: "nope" },
  });
  await app.close();

  const deny = auditRows(dbPath).filter(
    (r) => r.decision === "deny" && r.action === "POST /documents",
  );
  expect(deny).toHaveLength(1);
  expect(deny[0].actor).toBe(VIEWER_A);
  expect(deny[0].tenant_id).toBe(TENANT_A);
  expect(deny[0].request_id).toBe("rid-deny");
});

test("audit records a deny for an unauthenticated request", async () => {
  const dbPath = seededDb();
  const app = buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
  await app.inject({
    method: "POST",
    url: "/ask",
    headers: { "x-request-id": "rid-401" },
    payload: { question: "hi" },
  });
  await app.close();

  const deny = auditRows(dbPath).filter(
    (r) => r.decision === "deny" && r.request_id === "rid-401",
  );
  expect(deny).toHaveLength(1);
  expect(deny[0].actor).toBeNull(); // unknown caller
  expect(deny[0].tenant_id).toBeNull();
  expect(deny[0].action).toBe("POST /ask");
});
