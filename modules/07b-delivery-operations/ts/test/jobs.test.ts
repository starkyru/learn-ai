/**
 * Unit tests for the durable ingestion job queue (Task 3), deterministic + offline.
 *
 * Mirrors test_07b_jobs.py. These exercise the REAL queue code (`../src/jobs`)
 * against a real migrated SQLite database — the only injected thing is the job
 * HANDLER (the side-effect boundary), so idempotency, atomic claim, bounded
 * retry, and the dead-letter path are all driven deterministically.
 */

import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { openDb } from "../src/db.js";
import {
  DEAD,
  deadLetters,
  drain,
  enqueue,
  getJob,
  type IngestJob,
  indexDocument,
  JobWorker,
  listJobs,
  PENDING,
  processNext,
  requeue,
  SUCCEEDED,
} from "../src/jobs.js";
import { applyPending } from "../src/migrations.js";
import { createDocument, retrieve } from "../src/retrieval.js";

const TENANT_A = "tenant-a";
const TENANT_B = "tenant-b";

let dir: string;

beforeAll(() => {
  dir = mkdtempSync(join(tmpdir(), "m07b-ts-jobs-"));
});

afterAll(() => {
  rmSync(dir, { recursive: true, force: true });
});

/** A migrated db with two tenants (no jobs yet) — real schema. */
function makeDb(name: string): string {
  const path = join(dir, name);
  applyPending(path);
  const db = openDb(path);
  try {
    const insert = db.prepare("INSERT INTO tenants (id, name) VALUES (?, ?)");
    insert.run(TENANT_A, "Tenant A");
    insert.run(TENANT_B, "Tenant B");
  } finally {
    db.close();
  }
  return path;
}

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

/** Records the jobs it ran; fails the first `failTimes` attempts. */
class Recorder {
  readonly seen: string[] = [];
  constructor(private readonly failTimes = 0) {}
  handle = (job: IngestJob): void => {
    this.seen.push(job.id);
    if (this.seen.length <= this.failTimes) throw new Error("transient failure");
  };
}

const alwaysFail = (): void => {
  throw new Error("permanent failure");
};

// ── enqueue + idempotency ───────────────────────────────────────────────────

test("enqueue creates a pending job", () => {
  const path = makeDb("enqueue.sqlite");
  const result = enqueue(path, { tenantId: TENANT_A });
  expect(result.created).toBe(true);
  const job = getJob(path, TENANT_A, result.jobId);
  expect(job?.status).toBe(PENDING);
  expect(job?.retries).toBe(0);
});

test("enqueue is idempotent per key", () => {
  const path = makeDb("idem.sqlite");
  const first = enqueue(path, { tenantId: TENANT_A, idempotencyKey: "k1" });
  const second = enqueue(path, { tenantId: TENANT_A, idempotencyKey: "k1" });
  expect(first.created).toBe(true);
  expect(second.created).toBe(false);
  expect(second.jobId).toBe(first.jobId); // same job, not a duplicate
  expect(listJobs(path, TENANT_A)).toHaveLength(1);
});

test("the same key in a different tenant is a distinct job", () => {
  const path = makeDb("idem-tenant.sqlite");
  const a = enqueue(path, { tenantId: TENANT_A, idempotencyKey: "shared" });
  const b = enqueue(path, { tenantId: TENANT_B, idempotencyKey: "shared" });
  expect(b.created).toBe(true);
  expect(b.jobId).not.toBe(a.jobId);
});

test("enqueue without a key creates distinct jobs", () => {
  const path = makeDb("nokey.sqlite");
  const a = enqueue(path, { tenantId: TENANT_A });
  const b = enqueue(path, { tenantId: TENANT_A });
  expect(a.jobId).not.toBe(b.jobId);
  expect(listJobs(path, TENANT_A)).toHaveLength(2);
});

test("getJob is tenant-scoped", () => {
  const path = makeDb("scoped.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A });
  expect(getJob(path, TENANT_B, jobId)).toBeNull(); // another tenant cannot read it
});

// ── claim + process ─────────────────────────────────────────────────────────

test("processNext on an empty queue returns null", () => {
  const path = makeDb("empty.sqlite");
  expect(processNext(path, new Recorder().handle)).toBeNull();
});

test("processNext success marks the job succeeded", () => {
  const path = makeDb("success.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A });
  const recorder = new Recorder();
  const settled = processNext(path, recorder.handle);
  expect(settled?.status).toBe(SUCCEEDED);
  expect(recorder.seen).toEqual([jobId]); // ran exactly once, on this job
});

test("drain runs each job exactly once", () => {
  const path = makeDb("drain.sqlite");
  const a = enqueue(path, { tenantId: TENANT_A });
  const b = enqueue(path, { tenantId: TENANT_A });
  const recorder = new Recorder();
  const attempts = drain(path, recorder.handle);
  expect(attempts).toBe(2);
  expect(recorder.seen.sort()).toEqual([a.jobId, b.jobId].sort());
  expect(getJob(path, TENANT_A, a.jobId)?.status).toBe(SUCCEEDED);
  expect(getJob(path, TENANT_A, b.jobId)?.status).toBe(SUCCEEDED);
});

// ── retry + dead-letter ─────────────────────────────────────────────────────

test("a transient failure is retried then succeeds", () => {
  const path = makeDb("retry.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A, maxRetries: 3 });
  const recorder = new Recorder(2); // fail twice, then succeed
  const attempts = drain(path, recorder.handle);
  expect(attempts).toBe(3); // 2 failed + 1 successful
  const job = getJob(path, TENANT_A, jobId);
  expect(job?.status).toBe(SUCCEEDED);
  expect(job?.retries).toBe(2);
});

test("exhausted retries land in the dead-letter state", () => {
  const path = makeDb("dead.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A, maxRetries: 2 });
  const attempts = drain(path, alwaysFail);
  expect(attempts).toBe(3); // 1 initial + 2 retries, then dead
  const job = getJob(path, TENANT_A, jobId);
  expect(job?.status).toBe(DEAD);
  expect(job?.retries).toBe(3);
  expect(job?.lastError).toContain("permanent failure");
  expect(deadLetters(path, TENANT_A).map((d) => d.id)).toEqual([jobId]);
});

test("zero retries dies on the first failure", () => {
  const path = makeDb("zero.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A, maxRetries: 0 });
  const attempts = drain(path, alwaysFail);
  expect(attempts).toBe(1);
  const job = getJob(path, TENANT_A, jobId);
  expect(job?.status).toBe(DEAD);
  expect(job?.retries).toBe(1);
});

test("requeue revives a dead job and it can then succeed", () => {
  const path = makeDb("requeue.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A, maxRetries: 0 });
  drain(path, alwaysFail); // -> dead
  expect(requeue(path, TENANT_A, jobId)).toBe(true);
  const revived = getJob(path, TENANT_A, jobId);
  expect(revived?.status).toBe(PENDING);
  expect(revived?.retries).toBe(0);
  expect(revived?.lastError).toBeNull();
  // A second requeue is a no-op (it is pending now, not dead).
  expect(requeue(path, TENANT_A, jobId)).toBe(false);
  drain(path, new Recorder().handle);
  expect(getJob(path, TENANT_A, jobId)?.status).toBe(SUCCEEDED);
});

test("requeue of a non-dead job returns false", () => {
  const path = makeDb("requeue-noop.sqlite");
  const { jobId } = enqueue(path, { tenantId: TENANT_A }); // pending
  expect(requeue(path, TENANT_A, jobId)).toBe(false);
});

// ── the reference indexing handler ──────────────────────────────────────────

test("indexDocument creates a retrievable, tenant-scoped chunk", () => {
  const path = makeDb("index.sqlite");
  const docId = createDocument(path, { tenantId: TENANT_A, title: "Launch plan" });
  const { jobId } = enqueue(path, { tenantId: TENANT_A, documentId: docId });
  drain(path, indexDocument(path));
  expect(getJob(path, TENANT_A, jobId)?.status).toBe(SUCCEEDED);
  expect(retrieve(path, TENANT_A, "Launch").map((h) => h.content)).toEqual([
    "Launch plan",
  ]);
  expect(retrieve(path, TENANT_B, "Launch")).toEqual([]); // never leaks cross-tenant
});

test("indexDocument is idempotent — no double write", () => {
  const path = makeDb("index-idem.sqlite");
  const docId = createDocument(path, { tenantId: TENANT_A, title: "once" });
  // Two jobs for the SAME document both run the handler, but INSERT OR IGNORE on
  // UNIQUE(document_id, ordinal) yields one chunk, not two.
  enqueue(path, { tenantId: TENANT_A, documentId: docId });
  enqueue(path, { tenantId: TENANT_A, documentId: docId });
  drain(path, indexDocument(path));
  const db = openDb(path);
  try {
    const row = db
      .prepare("SELECT COUNT(*) AS n FROM chunks WHERE document_id = ?")
      .get(docId) as { n: number };
    expect(Number(row.n)).toBe(1);
  } finally {
    db.close();
  }
});

// ── the background worker ────────────────────────────────────────────────────

test("JobWorker processes in the background then stops cleanly", async () => {
  const path = makeDb("worker.sqlite");
  const docId = createDocument(path, { tenantId: TENANT_A, title: "bg work" });
  const real = indexDocument(path);
  let resolveRan!: () => void;
  const ran = new Promise<void>((r) => {
    resolveRan = r;
  });
  const handler = (job: IngestJob): void => {
    real(job);
    resolveRan();
  };
  const worker = new JobWorker(path, handler, 5);
  const { jobId } = enqueue(path, { tenantId: TENANT_A, documentId: docId });
  worker.start();
  try {
    await ran; // the worker ran the handler
    for (
      let i = 0;
      i < 200 && getJob(path, TENANT_A, jobId)?.status !== SUCCEEDED;
      i++
    ) {
      await sleep(5);
    }
  } finally {
    worker.stop();
  }
  expect(worker.isRunning).toBe(false);
  expect(getJob(path, TENANT_A, jobId)?.status).toBe(SUCCEEDED);
});
