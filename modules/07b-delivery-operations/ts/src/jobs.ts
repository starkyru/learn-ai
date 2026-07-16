/**
 * Durable background ingestion jobs (Task 3, the queue half).
 *
 * An LLM service does its slow, fallible work — chunking + embedding a document —
 * OUT of the request path, in a durable queue, so a request returns immediately
 * and the work survives a process restart. This module is that queue, backed by
 * the `ingest_jobs` and `idempotency_keys` tables the initial migration already
 * defines. It composes four production concerns:
 *
 *   - IDEMPOTENCY  — enqueuing the same logical work twice (same key) creates ONE
 *     job, so a retried client request produces one effect.
 *   - ATOMIC CLAIM — a worker transitions exactly one `pending` job to `running`
 *     under `BEGIN IMMEDIATE`, so two workers never run the same job.
 *   - BOUNDED RETRY — a failed attempt is re-queued until `maxRetries` is spent.
 *   - DEAD-LETTER  — an exhausted job lands in `dead` for inspection and manual
 *     requeue, instead of retrying forever or vanishing.
 *
 * The Python port (`jobs.py`) is the structural twin. Delivery is AT-LEAST-ONCE,
 * so the reference handler (`indexDocument`) is IDEMPOTENT — its write is an
 * `INSERT OR IGNORE` on the `UNIQUE(document_id, ordinal)` key — making the
 * observable effect effectively-once. The handler is the injected side-effect
 * boundary: tests pass a recording/failing handler to drive every path
 * deterministically; production passes `indexDocument`.
 */

import { randomUUID } from "node:crypto";
import type { DatabaseSync } from "node:sqlite";

import { openDb } from "./db.js";

/** Scope namespacing the idempotency keys this module owns in the shared table. */
export const IDEMPOTENCY_SCOPE = "ingest_job";

/** Total attempts = 1 initial + `maxRetries`; matches the `max_retries` column default. */
export const DEFAULT_MAX_RETRIES = 5;

// Bound the stored failure detail so a pathological error message cannot bloat
// the row. It is operational text; the handler must never surface a credential.
const MAX_ERROR_CHARS = 500;

// Hard backstop on drain() so a mis-implemented handler cannot spin forever.
const DRAIN_ITERATION_CAP = 10_000;

export const PENDING = "pending";
export const RUNNING = "running";
export const SUCCEEDED = "succeeded";
export const DEAD = "dead";

export interface IngestJob {
  id: string;
  tenantId: string;
  documentId: string | null;
  status: string;
  retries: number;
  maxRetries: number;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Runs the work for one job; returns on success and THROWS on failure. Must be idempotent. */
export type JobHandler = (job: IngestJob) => void;

export interface EnqueueResult {
  jobId: string;
  /** False on an idempotent replay (the key was already present). */
  created: boolean;
}

const COLUMNS =
  "id, tenant_id, document_id, status, retries, max_retries, " +
  "last_error, created_at, updated_at";

function rowToJob(row: Record<string, unknown>): IngestJob {
  return {
    id: String(row.id),
    tenantId: String(row.tenant_id),
    documentId: row.document_id === null ? null : String(row.document_id),
    status: String(row.status),
    retries: Number(row.retries),
    maxRetries: Number(row.max_retries),
    lastError: row.last_error === null ? null : String(row.last_error),
    createdAt: String(row.created_at),
    updatedAt: String(row.updated_at),
  };
}

/**
 * Enqueue an ingestion job; idempotent per `(tenantId, idempotencyKey)`.
 *
 * With an `idempotencyKey`, a second enqueue for the same tenant+key returns the
 * FIRST job's id and `created: false` — no duplicate job. The check-then-insert
 * runs under `BEGIN IMMEDIATE`, so two concurrent same-key enqueues serialise
 * (the second sees the first's key row); the `idempotency_keys` primary key is
 * the backstop. A given `documentId` must belong to `tenantId` — the composite
 * foreign key enforces it.
 */
export function enqueue(
  dbPath: string,
  args: {
    tenantId: string;
    documentId?: string | null;
    idempotencyKey?: string | null;
    maxRetries?: number;
  },
): EnqueueResult {
  const jobId = randomUUID();
  const documentId = args.documentId ?? null;
  const idempotencyKey = args.idempotencyKey ?? null;
  const maxRetries = args.maxRetries ?? DEFAULT_MAX_RETRIES;
  const db = openDb(dbPath);
  try {
    db.exec("BEGIN IMMEDIATE");
    if (idempotencyKey !== null) {
      const existing = db
        .prepare(
          "SELECT result_ref FROM idempotency_keys " +
            "WHERE tenant_id = ? AND scope = ? AND key = ?",
        )
        .get(args.tenantId, IDEMPOTENCY_SCOPE, idempotencyKey) as
        | { result_ref: string }
        | undefined;
      if (existing !== undefined) {
        db.exec("ROLLBACK");
        return { jobId: existing.result_ref, created: false };
      }
      db.prepare(
        "INSERT INTO idempotency_keys (key, scope, tenant_id, result_ref) " +
          "VALUES (?, ?, ?, ?)",
      ).run(idempotencyKey, IDEMPOTENCY_SCOPE, args.tenantId, jobId);
    }
    db.prepare(
      "INSERT INTO ingest_jobs (id, tenant_id, document_id, status, max_retries) " +
        "VALUES (?, ?, ?, 'pending', ?)",
    ).run(jobId, args.tenantId, documentId, maxRetries);
    db.exec("COMMIT");
  } catch (err) {
    db.exec("ROLLBACK");
    throw err;
  } finally {
    db.close();
  }
  return { jobId, created: true };
}

/** Return the job if it exists IN `tenantId` — else null (tenant-scoped). */
export function getJob(
  dbPath: string,
  tenantId: string,
  jobId: string,
): IngestJob | null {
  const db = openDb(dbPath);
  try {
    const row = db
      .prepare(`SELECT ${COLUMNS} FROM ingest_jobs WHERE tenant_id = ? AND id = ?`)
      .get(tenantId, jobId) as Record<string, unknown> | undefined;
    return row === undefined ? null : rowToJob(row);
  } finally {
    db.close();
  }
}

/** List jobs in `tenantId` (optionally filtered by status), newest first. */
export function listJobs(
  dbPath: string,
  tenantId: string,
  opts: { status?: string; limit?: number } = {},
): IngestJob[] {
  const limit = opts.limit ?? 100;
  const db = openDb(dbPath);
  try {
    const rows =
      opts.status === undefined
        ? db
            .prepare(
              `SELECT ${COLUMNS} FROM ingest_jobs WHERE tenant_id = ? ` +
                "ORDER BY created_at DESC, id DESC LIMIT ?",
            )
            .all(tenantId, limit)
        : db
            .prepare(
              `SELECT ${COLUMNS} FROM ingest_jobs WHERE tenant_id = ? AND status = ? ` +
                "ORDER BY created_at DESC, id DESC LIMIT ?",
            )
            .all(tenantId, opts.status, limit);
    return (rows as Record<string, unknown>[]).map(rowToJob);
  } finally {
    db.close();
  }
}

/** The dead-letter view: jobs in `tenantId` that exhausted their retries. */
export function deadLetters(
  dbPath: string,
  tenantId: string,
  limit = 100,
): IngestJob[] {
  return listJobs(dbPath, tenantId, { status: DEAD, limit });
}

/**
 * Move a DEAD job back to `pending` (retries reset). Returns true if it moved.
 *
 * The `status = 'dead'` predicate makes this a no-op (false) for a
 * pending/running/succeeded job, so requeue cannot resurrect an in-flight or
 * already-done job.
 */
export function requeue(dbPath: string, tenantId: string, jobId: string): boolean {
  const db = openDb(dbPath);
  try {
    const result = db
      .prepare(
        "UPDATE ingest_jobs SET status = 'pending', retries = 0, last_error = NULL, " +
          "updated_at = datetime('now') " +
          "WHERE tenant_id = ? AND id = ? AND status = 'dead'",
      )
      .run(tenantId, jobId);
    return Number(result.changes) > 0;
  } finally {
    db.close();
  }
}

/**
 * Atomically transition the oldest `pending` job to `running` and return it.
 *
 * `BEGIN IMMEDIATE` takes the write lock up front so two workers cannot select
 * the same row; the `AND status = 'pending'` guard on the UPDATE is a second line
 * of defence. Returns null when nothing is claimable.
 */
function claimNext(db: DatabaseSync): IngestJob | null {
  db.exec("BEGIN IMMEDIATE");
  try {
    const row = db
      .prepare(
        `SELECT ${COLUMNS} FROM ingest_jobs WHERE status = 'pending' ` +
          "ORDER BY created_at, id LIMIT 1",
      )
      .get() as Record<string, unknown> | undefined;
    if (row === undefined) {
      db.exec("ROLLBACK");
      return null;
    }
    db.prepare(
      "UPDATE ingest_jobs SET status = 'running', updated_at = datetime('now') " +
        "WHERE id = ? AND status = 'pending'",
    ).run(String(row.id));
    db.exec("COMMIT");
    return rowToJob(row);
  } catch (err) {
    db.exec("ROLLBACK");
    throw err;
  }
}

function settleSuccess(db: DatabaseSync, jobId: string): void {
  db.prepare(
    "UPDATE ingest_jobs SET status = 'succeeded', last_error = NULL, " +
      "updated_at = datetime('now') WHERE id = ?",
  ).run(jobId);
}

/** Record a failed attempt: re-queue if retries remain, else dead-letter. */
function settleFailure(db: DatabaseSync, job: IngestJob, error: string): void {
  const retries = job.retries + 1;
  const status = retries <= job.maxRetries ? PENDING : DEAD;
  db.prepare(
    "UPDATE ingest_jobs SET status = ?, retries = ?, last_error = ?, " +
      "updated_at = datetime('now') WHERE id = ?",
  ).run(status, retries, error.slice(0, MAX_ERROR_CHARS), job.id);
}

/**
 * Claim and run ONE job. Returns the job's post-run snapshot, or null if idle.
 *
 * A handler throw is counted and the job re-queued (`pending`) or dead-lettered
 * (`dead`); a handler failure never propagates out, so a worker loop keeps
 * draining. The returned snapshot reflects the settled state.
 */
export function processNext(dbPath: string, handler: JobHandler): IngestJob | null {
  const db = openDb(dbPath);
  let job: IngestJob | null;
  try {
    job = claimNext(db);
    if (job === null) return null;
    try {
      handler(job);
      settleSuccess(db, job.id);
    } catch (err) {
      settleFailure(db, job, err instanceof Error ? err.message : String(err));
    }
  } finally {
    db.close();
  }
  // Re-read so the caller observes the settled row, not the claim.
  return getJob(dbPath, job.tenantId, job.id);
}

/**
 * Run attempts until the queue has no claimable job. Returns attempts run.
 *
 * A re-queued job is retried on a later iteration of the SAME drain, so a
 * transiently-failing job settles here. Bounded by `DRAIN_ITERATION_CAP`.
 */
export function drain(dbPath: string, handler: JobHandler): number {
  let attempts = 0;
  while (attempts < DRAIN_ITERATION_CAP) {
    if (processNext(dbPath, handler) === null) break;
    attempts += 1;
  }
  return attempts;
}

/**
 * The reference indexing handler: chunk a document's title into `chunks`.
 *
 * A deliberately naive stand-in for real chunk+embed (see Module 05): it writes
 * ONE chunk whose content is the document title. The deterministic chunk id and
 * `INSERT OR IGNORE` on the `UNIQUE(document_id, ordinal)` key make it
 * idempotent, so replaying the job after a crash never double-writes. Throws when
 * the document is missing so the job retries / dead-letters rather than no-op'ing.
 */
export function indexDocument(dbPath: string): JobHandler {
  return (job: IngestJob): void => {
    if (job.documentId === null) return;
    const db = openDb(dbPath);
    try {
      const row = db
        .prepare("SELECT title FROM documents WHERE tenant_id = ? AND id = ?")
        .get(job.tenantId, job.documentId) as { title: string } | undefined;
      if (row === undefined) {
        throw new Error(`document ${job.documentId} not found for tenant`);
      }
      db.prepare(
        "INSERT OR IGNORE INTO chunks " +
          "(id, tenant_id, document_id, ordinal, content) VALUES (?, ?, ?, ?, ?)",
      ).run(`${job.documentId}:0`, job.tenantId, job.documentId, 0, row.title);
    } finally {
      db.close();
    }
  };
}

/**
 * A background poller that drains the queue, for the running service.
 *
 * Not started by `buildApp` (so request tests stay deterministic and timer-free);
 * the production launcher starts it and stops it on shutdown. Tests drive `drain`
 * directly. The poll timer is `unref`'d so a leaked worker cannot keep the process
 * alive, and `stop()` clears it for a prompt, clean shutdown.
 */
export class JobWorker {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private stopped = true;

  constructor(
    private readonly dbPath: string,
    private readonly handler: JobHandler,
    private readonly pollIntervalMs = 1000,
  ) {}

  start(): void {
    if (!this.stopped) return;
    this.stopped = false;
    this.tick();
  }

  private tick = (): void => {
    if (this.stopped) return;
    drain(this.dbPath, this.handler);
    if (this.stopped) return;
    this.timer = setTimeout(this.tick, this.pollIntervalMs);
    // Do not let the poll timer keep the event loop (and tests) alive.
    this.timer.unref?.();
  };

  stop(): void {
    this.stopped = true;
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  get isRunning(): boolean {
    return !this.stopped;
  }
}
