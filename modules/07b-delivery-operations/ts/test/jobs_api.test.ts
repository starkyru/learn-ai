/**
 * Tests for the durable-job HTTP surface: POST /jobs and GET /jobs/:jobId (Task 3).
 *
 * Enqueue is operator-only and tenant-scoped; status inspection is open to any
 * authenticated caller but only within their tenant. Processing is driven here by
 * calling the real queue's `drain` directly (buildApp does NOT run the background
 * worker — that is production-only in server.ts — so the request path stays
 * deterministic). The only faked boundary is the LLM provider.
 */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { buildApp } from "../src/app.js";
import { openDb } from "../src/db.js";
import { drain, indexDocument } from "../src/jobs.js";
import {
  bearer,
  discardSink,
  FakeProvider,
  makeConfig,
  OPERATOR_A,
  seedIdentity,
  VIEWER_A,
  VIEWER_B,
} from "./fakes.js";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-jobs-api-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

function seededDb(name: string): string {
  const path = join(dir, name);
  seedIdentity(path);
  return path;
}

function appFor(dbPath: string) {
  return buildApp({
    config: makeConfig(dbPath),
    provider: new FakeProvider(),
    logSink: discardSink,
  });
}

/** Create a document as operator A via the real endpoint; return its id. */
async function freshDocument(
  app: ReturnType<typeof buildApp>,
  title: string,
): Promise<string> {
  const res = await app.inject({
    method: "POST",
    url: "/documents",
    headers: bearer(OPERATOR_A),
    payload: { title },
  });
  expect(res.statusCode).toBe(201);
  return res.json().id as string;
}

test("enqueue requires an operator", async () => {
  const app = appFor(seededDb("jobs-auth.sqlite"));
  const unauth = await app.inject({
    method: "POST",
    url: "/jobs",
    payload: { document_id: "doc-a1" },
  });
  const viewer = await app.inject({
    method: "POST",
    url: "/jobs",
    headers: bearer(VIEWER_A),
    payload: { document_id: "doc-a1" },
  });
  await app.close();
  expect(unauth.statusCode).toBe(401); // no token
  expect(viewer.statusCode).toBe(403); // authenticated but not an operator
});

test("enqueue of an unknown or cross-tenant document is 404", async () => {
  const app = appFor(seededDb("jobs-404.sqlite"));
  const missing = await app.inject({
    method: "POST",
    url: "/jobs",
    headers: bearer(OPERATOR_A),
    payload: { document_id: "no-such-doc" },
  });
  // doc-b1 belongs to tenant B; operator A must not enqueue against it.
  const cross = await app.inject({
    method: "POST",
    url: "/jobs",
    headers: bearer(OPERATOR_A),
    payload: { document_id: "doc-b1" },
  });
  await app.close();
  expect(missing.statusCode).toBe(404);
  expect(cross.statusCode).toBe(404);
});

test("enqueue is accepted and the job is inspectable (and not yet processed)", async () => {
  const app = appFor(seededDb("jobs-accept.sqlite"));
  const docId = await freshDocument(app, "launch notes");
  const enq = await app.inject({
    method: "POST",
    url: "/jobs",
    headers: bearer(OPERATOR_A),
    payload: { document_id: docId },
  });
  expect(enq.statusCode).toBe(202); // accepted for background processing
  const jobId = enq.json().job_id as string;
  expect(enq.json().status).toBe("pending");
  // Any authenticated caller in the tenant can inspect it; with no worker running
  // in tests, it is still pending — proving buildApp does not process in the app.
  const status = await app.inject({
    method: "GET",
    url: `/jobs/${jobId}`,
    headers: bearer(VIEWER_A),
  });
  await app.close();
  expect(status.statusCode).toBe(200);
  expect(status.json()).toMatchObject({
    id: jobId,
    document_id: docId,
    status: "pending",
  });
});

test("enqueue is idempotent with a key and yields one effect", async () => {
  const dbPath = seededDb("jobs-idem.sqlite");
  const app = appFor(dbPath);
  const docId = await freshDocument(app, "idem doc");
  const headers = { ...bearer(OPERATOR_A), "idempotency-key": "req-77" };
  const first = await app.inject({
    method: "POST",
    url: "/jobs",
    headers,
    payload: { document_id: docId },
  });
  const second = await app.inject({
    method: "POST",
    url: "/jobs",
    headers,
    payload: { document_id: docId },
  });
  expect(first.statusCode).toBe(202); // first creates the job
  expect(second.statusCode).toBe(200); // replay: no new job
  expect(second.json().job_id).toBe(first.json().job_id);

  // Process the queue, then confirm exactly one effect despite the repeat.
  drain(dbPath, indexDocument(dbPath));
  const done = await app.inject({
    method: "GET",
    url: `/jobs/${first.json().job_id}`,
    headers: bearer(OPERATOR_A),
  });
  await app.close();
  expect(done.json().status).toBe("succeeded");

  const db = openDb(dbPath);
  try {
    const row = db
      .prepare("SELECT COUNT(*) AS n FROM chunks WHERE document_id = ?")
      .get(docId) as { n: number };
    expect(Number(row.n)).toBe(1);
  } finally {
    db.close();
  }
});

test("job status is tenant-scoped", async () => {
  const app = appFor(seededDb("jobs-scope.sqlite"));
  const docId = await freshDocument(app, "tenant A only");
  const enq = await app.inject({
    method: "POST",
    url: "/jobs",
    headers: bearer(OPERATOR_A),
    payload: { document_id: docId },
  });
  const jobId = enq.json().job_id as string;
  // Tenant B viewer must not see tenant A's job — a 404, not a status leak.
  const cross = await app.inject({
    method: "GET",
    url: `/jobs/${jobId}`,
    headers: bearer(VIEWER_B),
  });
  await app.close();
  expect(cross.statusCode).toBe(404);
});
