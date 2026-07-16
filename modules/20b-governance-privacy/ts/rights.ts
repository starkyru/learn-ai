/**
 * Data-subject rights engine (Module 20b, Task 2).
 *
 * Synthetic data only — nothing here is real, and none of it is legal advice.
 *
 * The teaching point: a subject's data lives in MANY stores (primary record, the
 * embedding index, caches, feedback, human-review queues, background jobs), so
 * export and erasure must reach ALL of them, not just the source record. Erasure
 * is not uniform either: some stores hard-delete, while a store under a
 * documented retention EXCEPTION (e.g. a legal-hold review record) keeps a
 * TOMBSTONE — the id and a reason code, never the raw content — and separately,
 * records past their retention period are PURGED.
 *
 * Design discipline (reused from Task 1/2 and hardened here):
 * - **Metadata-only handles.** `addRecord`/`recordsFor` return metadata (id,
 *   store, class, timestamps, retention) — NEVER raw content. Only `export`
 *   returns content, as a deliberate point-in-time snapshot the requester owns.
 * - **Erase is a transaction with a WRITE BARRIER.** While a subject is being
 *   erased (and while its audit is flushed) any `addRecord` for it is REJECTED.
 * - **Reason CODES, not free text.** Audit reasons are an allowlisted set.
 * - **Engine-owned, validated policy.** Registration copies the policy fields
 *   into a fresh engine-owned object (never retains the caller's).
 */

// --- validation (mirrors consent.ts — safe labels, never raw PII) ----------

// A subject is a STRICT opaque token: `subj_` + hex only. A prefix-only rule
// like `subj_[A-Za-z0-9_]+` would admit `subj_Alice_Smith` — an identifier that
// is itself PII — and persist it in the audit. `recordId` (a caller string that
// survives into a tombstone and audit) is likewise an opaque `word_hex` token.
const SUBJECT_PATTERN = /^subj_[0-9a-f]+$/;
const RECORD_PATTERN = /^[a-z][a-z0-9]*_[0-9a-f]+$/; // opaque token, e.g. rec_1a2b
const ACTOR_PATTERN = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/; // service/role id, incl. reviewer
const STORE_PATTERN = /^[a-z][a-z0-9_]*$/; // snake_case store id

function assertSubject(subject: string): void {
  if (typeof subject !== "string" || !SUBJECT_PATTERN.test(subject)) {
    throw new Error(
      `subject must be an opaque pseudonymous token like 'subj_0042' (subj_ + ` +
        `hex only; a name/email/SSN suffix like 'subj_Alice_Smith' is rejected); ` +
        `got ${JSON.stringify(subject)}`,
    );
  }
}

function assertRecordId(recordId: string): void {
  if (typeof recordId !== "string" || !RECORD_PATTERN.test(recordId)) {
    throw new Error(
      `recordId must be an opaque token like 'rec_1a2b' (lowercase prefix + '_' ` +
        `+ hex; no free text / PII such as a name or SSN); got ` +
        `${JSON.stringify(recordId)}`,
    );
  }
}

function assertActor(actor: string): void {
  if (typeof actor !== "string" || !ACTOR_PATTERN.test(actor)) {
    throw new Error(
      `actor must be a service id like 'privacy-service' (starts with a letter; ` +
        `not a digit-dash run), not free PII; got ${JSON.stringify(actor)}`,
    );
  }
}

function assertReviewer(reviewer: string): void {
  if (typeof reviewer !== "string" || !ACTOR_PATTERN.test(reviewer)) {
    throw new Error(
      `reviewer must be a role/service id like 'legal-team' (not a raw person ` +
        `name); got ${JSON.stringify(reviewer)}`,
    );
  }
}

function assertStoreName(name: string): void {
  if (typeof name !== "string" || !STORE_PATTERN.test(name)) {
    throw new Error(
      `store name must be a snake_case label like 'human_review' (no raw PII ` +
        `such as an email); got ${JSON.stringify(name)}`,
    );
  }
}

/** Allowlisted lawful bases for RE-COLLECTING data after an erasure (mirrors the
 * Task-2 consent bases). Reactivating an erased subject must name one. */
export type LawfulBasis =
  | "consent"
  | "contract"
  | "legal_obligation"
  | "legitimate_interest"
  | "vital_interest"
  | "public_task";

const LAWFUL_BASES: ReadonlySet<string> = new Set<LawfulBasis>([
  "consent",
  "contract",
  "legal_obligation",
  "legitimate_interest",
  "vital_interest",
  "public_task",
]);

function assertLawfulBasis(basis: unknown): void {
  if (typeof basis !== "string" || !LAWFUL_BASES.has(basis)) {
    throw new Error(
      `lawful_basis must be an allowlisted lawful basis (e.g. 'consent', ` +
        `'contract', 'legal_obligation'); got ${JSON.stringify(basis)}`,
    );
  }
}

/** Recursively freeze objects/arrays so a returned snapshot can't be mutated. */
function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
    for (const nested of Object.values(value)) deepFreeze(nested);
    Object.freeze(value);
  }
  return value;
}

// --- retention policy + records --------------------------------------------

export type RetentionMode = "hard_delete" | "tombstone";

/** Allowlisted, non-PII reason codes — the ONLY reasons audit records carry.
 * Human-readable rationale lives in `StorePolicy.description` (not audited). */
export type ReasonCode =
  | "legal_hold"
  | "regulatory_retention"
  | "subject_request"
  | "retention_expiry";

const REASON_CODES: ReadonlySet<string> = new Set<ReasonCode>([
  "legal_hold",
  "regulatory_retention",
  "subject_request",
  "retention_expiry",
]);

function assertReasonCode(reason: unknown): void {
  if (typeof reason !== "string" || !REASON_CODES.has(reason)) {
    throw new Error(
      `reason must be an allowlisted ReasonCode (not free text that could carry ` +
        `PII); got ${JSON.stringify(reason)}`,
    );
  }
}

export interface StorePolicy {
  name: string;
  location: string; // storage location label, from the data map
  mode: RetentionMode;
  retentionTicks: number; // a record older than this (by the clock) is purged
  reason?: ReasonCode; // retention-exception CODE (tombstone stores)
  requiresReviewer?: boolean; // erasure needs a named reviewer sign-off
  description?: string; // human text — NOT written to the audit trail
}

/** LIVE internal record (mutable content). Never handed out directly. */
interface Record_ {
  store: string;
  subject: string;
  recordId: string;
  createdAt: number;
  content: Record<string, unknown>; // synthetic; emptied once tombstoned/erased
  tombstoned: boolean;
  tombstoneReason: string | null;
}

/** A metadata-only view of a record — NO raw content. Safe to hand out. */
export interface RecordMetadata {
  store: string;
  subject: string;
  recordId: string;
  createdAt: number;
  tombstoned: boolean;
  tombstoneReason: string | null;
  mode: RetentionMode;
  retentionTicks: number;
  location: string;
}

function scrub(record: Record_): void {
  for (const key of Object.keys(record.content)) {
    delete (record.content as Record<string, unknown>)[key];
  }
}

// --- export / erasure result types -----------------------------------------

export interface ExportCopy {
  store: string;
  location: string;
  recordId: string;
  tombstoned: boolean;
  content: Record<string, unknown>; // point-in-time copy the requester owns
}

export class ExportManifest {
  constructor(
    readonly subject: string,
    readonly copies: readonly ExportCopy[],
  ) {}

  stores(): Set<string> {
    return new Set(this.copies.map((c) => c.store));
  }

  locations(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const copy of this.copies) out[copy.store] = copy.location;
    return out;
  }
}

export interface ErasureOutcome {
  store: string;
  result: string; // "hard_deleted" | "tombstoned"
  count: number;
  reviewer: string | null;
  reason: string; // a ReasonCode
}

export class ErasureReport {
  constructor(
    readonly subject: string,
    readonly outcomes: readonly ErasureOutcome[],
  ) {}

  byStore(): Record<string, ErasureOutcome> {
    const out: Record<string, ErasureOutcome> = {};
    for (const outcome of this.outcomes) out[outcome.store] = outcome;
    return out;
  }
}

/** One row of the append-only decision log — exactly these fields. */
export interface RightsAuditEntry {
  actor: string;
  time: number;
  action: string; // "export" | "delete" | "tombstone" | "expire"
  subject: string; // pseudonymous id, or "*" for a store-wide sweep
  store: string; // store name, or "*" for all stores
  scope: string;
  result: string;
  reviewer: string | null;
  reason: string; // a ReasonCode — never free text
}

export type Clock = () => number;
export type AuditSink = (entry: RightsAuditEntry) => void;

function tickClock(): Clock {
  let n = 0;
  return () => n++;
}

function recordKey(subject: string, recordId: string): string {
  return JSON.stringify([subject, recordId]);
}

interface StoreState {
  policy: StorePolicy;
  // Keyed by a composite (subject, recordId) — keying by recordId alone would
  // let two subjects that reuse an id silently overwrite each other. Records
  // here are LIVE internal objects (mutable content); never handed out directly.
  records: Map<string, Record_>;
}

// --- engine -----------------------------------------------------------------

export class RightsEngine {
  private readonly clock: Clock;
  private readonly sink?: AuditSink;
  private readonly stores = new Map<string, StoreState>();
  private readonly audit: RightsAuditEntry[] = [];
  // Subjects whose erasure (incl. audit flush) is in progress — the barrier.
  private readonly erasing = new Set<string>();
  // DURABLE erased-subject marker that OUTLIVES the erase transaction. A
  // transient flag would let a DEFERRED add (e.g. a `queueMicrotask`ed
  // addRecord) run after the synchronous flush clears the flag; this marker
  // persists, so any add for an erased subject is rejected until reactivation.
  private readonly erased = new Set<string>();
  // Outbox: audit entries whose external sink delivery failed. Already durably
  // recorded in `this.audit`; a retry queue so a sink outage never fails an erase.
  private readonly pendingDelivery: RightsAuditEntry[] = [];

  constructor(opts: { clock?: Clock; sink?: AuditSink } = {}) {
    this.clock = opts.clock ?? tickClock();
    this.sink = opts.sink;
  }

  // --- setup -------------------------------------------------------------

  registerStore(policy: StorePolicy): void {
    assertStoreName(policy.name);
    if (policy.reason !== undefined) assertReasonCode(policy.reason);
    if (this.stores.has(policy.name)) {
      throw new Error(`store already registered: ${JSON.stringify(policy.name)}`);
    }
    // Build a fresh ENGINE-OWNED policy from copied, validated fields — never
    // share the caller's object.
    const owned: StorePolicy = Object.freeze({
      name: policy.name,
      location: policy.location,
      mode: policy.mode,
      retentionTicks: policy.retentionTicks,
      reason: policy.reason,
      requiresReviewer: policy.requiresReviewer ?? false,
      description: policy.description ?? "",
    });
    this.stores.set(policy.name, { policy: owned, records: new Map() });
  }

  addRecord(
    store: string,
    subject: string,
    recordId: string,
    content: Record<string, unknown>,
    opts: { createdAt?: number } = {},
  ): RecordMetadata {
    assertSubject(subject);
    assertRecordId(recordId);
    // Reject for a subject being erased OR already erased. The durable marker
    // persists across microtasks, so a deferred add after the sync flush is
    // rejected too.
    if (this.erasing.has(subject) || this.erased.has(subject)) {
      throw new Error(
        `subject ${JSON.stringify(subject)} is erased; explicit reactivation (a ` +
          `new lawful basis) is required to accept new data`,
      );
    }
    const state = this.stores.get(store);
    if (state === undefined) {
      throw new Error(`unknown store: ${JSON.stringify(store)}`);
    }
    const internal: Record_ = {
      store,
      subject,
      recordId,
      createdAt: opts.createdAt ?? this.clock(),
      content: structuredClone(content), // live, mutable, private copy
      tombstoned: false,
      tombstoneReason: null,
    };
    state.records.set(recordKey(subject, recordId), internal);
    return this.metadata(internal, state.policy);
  }

  private metadata(record: Record_, policy: StorePolicy): RecordMetadata {
    return deepFreeze({
      store: record.store,
      subject: record.subject,
      recordId: record.recordId,
      createdAt: record.createdAt,
      tombstoned: record.tombstoned,
      tombstoneReason: record.tombstoneReason,
      mode: policy.mode,
      retentionTicks: policy.retentionTicks,
      location: policy.location,
    });
  }

  // --- inspection (for callers/tests) -----------------------------------

  recordsFor(subject: string): RecordMetadata[] {
    const out: RecordMetadata[] = [];
    for (const state of this.stores.values()) {
      for (const record of state.records.values()) {
        if (record.subject === subject) out.push(this.metadata(record, state.policy));
      }
    }
    return out;
  }

  storeNames(): string[] {
    return [...this.stores.keys()];
  }

  // --- export ------------------------------------------------------------

  export(subject: string, opts: { actor: string }): ExportManifest {
    assertSubject(subject);
    assertActor(opts.actor);
    const copies: ExportCopy[] = [];
    for (const [name, state] of this.stores) {
      for (const record of state.records.values()) {
        if (record.subject === subject) {
          copies.push(
            deepFreeze({
              store: name,
              location: state.policy.location,
              recordId: record.recordId,
              tombstoned: record.tombstoned,
              content: structuredClone(record.content),
            }),
          );
        }
      }
    }
    const manifest = new ExportManifest(subject, Object.freeze(copies));
    this.log({
      actor: opts.actor,
      action: "export",
      subject,
      store: "*",
      scope: String(copies.length),
      result: "exported",
      reviewer: null,
      reason: "subject_request",
    });
    return manifest;
  }

  // --- erasure (delete / tombstone with retention exceptions) -----------

  /**
   * Delete or tombstone each copy per its store's retention policy.
   *
   * Reviewer trust boundary: `reviewer` is a TRUSTED, caller-supplied label —
   * this fake-store teaching engine RECORDS the reviewer identity, it does NOT
   * authenticate it (any in-process caller could pass `legal-team`, the same
   * in-process boundary documented for `actor` in consent). A PRODUCTION system
   * MUST bind `reviewer` to an authenticated approval capability (a verified
   * reviewer principal / signed approval carrying role + scope) derived from the
   * authorization layer — not a bare string.
   */
  erase(
    subject: string,
    opts: { actor: string; reviewer?: string | null },
  ): ErasureReport {
    assertSubject(subject);
    assertActor(opts.actor);
    const reviewer = opts.reviewer ?? null;
    if (reviewer !== null) assertReviewer(reviewer);
    if (this.erasing.has(subject)) {
      throw new Error(`erase already in progress for ${JSON.stringify(subject)}`);
    }

    const buffered: RightsAuditEntry[] = [];
    const outcomes: ErasureOutcome[] = [];
    this.erasing.add(subject);
    try {
      // Snapshot the exact records to erase BEFORE any mutation.
      const snapshot = new Map<string, Record_[]>();
      for (const [name, state] of this.stores) {
        snapshot.set(
          name,
          [...state.records.values()].filter((r) => r.subject === subject),
        );
      }
      // Fail closed on the snapshot: a reviewer-gated store with data needs one.
      for (const [name, state] of this.stores) {
        if (
          state.policy.requiresReviewer &&
          reviewer === null &&
          (snapshot.get(name)?.length ?? 0) > 0
        ) {
          throw new Error(
            `store '${state.policy.name}' requires a reviewer to erase ` +
              `(retention-exception / legal-hold sign-off)`,
          );
        }
      }

      for (const [name, state] of this.stores) {
        const records = snapshot.get(name) ?? [];
        if (records.length === 0) continue;

        let result: string;
        let action: string;
        let resultReviewer: string | null;
        let reason: string;
        if (state.policy.mode === "hard_delete") {
          for (const record of records) {
            scrub(record);
            state.records.delete(recordKey(record.subject, record.recordId));
          }
          result = "hard_deleted";
          action = "delete";
          resultReviewer = null;
          reason = "subject_request";
        } else {
          reason = state.policy.reason ?? "regulatory_retention";
          for (const record of records) {
            scrub(record);
            const tombstone: Record_ = {
              store: name,
              subject,
              recordId: record.recordId,
              createdAt: this.clock(),
              content: {},
              tombstoned: true,
              tombstoneReason: reason,
            };
            state.records.set(recordKey(subject, record.recordId), tombstone);
          }
          result = "tombstoned";
          action = "tombstone";
          resultReviewer = reviewer;
        }
        outcomes.push(
          Object.freeze({
            store: name,
            result,
            count: records.length,
            reviewer: resultReviewer,
            reason,
          }),
        );
        const entry = this.newEntry({
          actor: opts.actor,
          action,
          subject,
          store: name,
          scope: String(records.length),
          result,
          reviewer: resultReviewer,
          reason,
        });
        this.record(entry);
        buffered.push(entry);
      }

      // Commit the DURABLE erased marker BEFORE invoking any fallible external
      // sink, and KEEP it even if delivery fails. Data removal + the erased
      // marker are TERMINAL: a sink outage can be retried but must never
      // un-erase the subject or re-admit writes (a DEFERRED add after this
      // synchronous erase returns is also rejected by this marker).
      this.erased.add(subject);
      // Deliver the already-recorded audit via the outbox path — a sink
      // exception is captured, not propagated.
      for (const entry of buffered) this.deliver(entry);
    } finally {
      this.erasing.delete(subject);
    }
    return new ErasureReport(subject, Object.freeze(outcomes));
  }

  /**
   * Clear the erased marker so new data may be collected again — an AUTHORIZED,
   * AUDITED, erase-EXCLUSIVE transition.
   *
   * Erasure is terminal: clearing the marker is the ONLY way to re-admit data for
   * an erased subject, so it is deliberately gated:
   *
   * - It REQUIRES a new, validated `lawfulBasis` (an allowlisted lawful basis —
   *   you are re-collecting personal data, which needs a fresh basis) and a
   *   validated `actor`.
   * - It is REJECTED while ANY erasure is in progress, so a re-entrant audit sink
   *   invoked during an erase flush cannot clear the terminal marker mid-
   *   transaction and silently re-open collection.
   * - It RECORDS the transition (actor/time/subject/action=reactivate/basis) in
   *   the audit trail BEFORE the marker is cleared.
   *
   * Like `erase`'s reviewer, `actor`/`lawfulBasis` are trusted, caller-supplied
   * labels this teaching engine records but does not authenticate; production
   * MUST bind them to an authenticated approval capability, not a bare string.
   */
  reactivateSubject(
    subject: string,
    opts: { lawfulBasis: LawfulBasis; actor: string },
  ): void {
    assertSubject(subject);
    assertActor(opts.actor);
    assertLawfulBasis(opts.lawfulBasis);
    if (this.erasing.size > 0) {
      throw new Error(
        "cannot reactivate a subject while an erasure is in progress (the " +
          "terminal erased marker may only be cleared by this authorized, " +
          "audited path, never from a reentrant sink)",
      );
    }
    const entry = this.newEntry({
      actor: opts.actor,
      action: "reactivate",
      subject,
      store: "*",
      scope: "1",
      result: "reactivated",
      reviewer: null,
      reason: opts.lawfulBasis,
    });
    this.record(entry); // audit the transition BEFORE clearing the marker
    this.erased.delete(subject);
    this.deliver(entry);
  }

  // --- retention expiry --------------------------------------------------

  purgeExpired(now: number, opts: { actor: string }): Record<string, number> {
    assertActor(opts.actor);
    const purged: Record<string, number> = {};
    for (const [name, state] of this.stores) {
      const expired = [...state.records.values()].filter(
        (r) => r.createdAt + state.policy.retentionTicks <= now,
      );
      for (const record of expired) {
        scrub(record);
        state.records.delete(recordKey(record.subject, record.recordId));
      }
      if (expired.length > 0) {
        purged[name] = expired.length;
        this.log({
          actor: opts.actor,
          action: "expire",
          subject: "*",
          store: name,
          scope: String(expired.length),
          result: "purged",
          reviewer: null,
          reason: "retention_expiry",
        });
      }
    }
    return purged;
  }

  // --- audit -------------------------------------------------------------

  get auditLog(): readonly RightsAuditEntry[] {
    return [...this.audit];
  }

  auditRecords(): RightsAuditEntry[] {
    return this.audit.map((entry) => ({ ...entry }));
  }

  private newEntry(fields: Omit<RightsAuditEntry, "time">): RightsAuditEntry {
    return Object.freeze({ ...fields, time: this.clock() });
  }

  private record(entry: RightsAuditEntry): void {
    this.audit.push(entry);
  }

  private emit(entry: RightsAuditEntry): void {
    this.sink?.(entry);
  }

  /** Best-effort external delivery. The entry is ALREADY durably recorded in
   * `this.audit`; a sink exception is captured to the outbox for retry, never
   * propagated (a sink outage must not fail/reopen an erase). */
  private deliver(entry: RightsAuditEntry): void {
    try {
      this.emit(entry);
    } catch {
      this.pendingDelivery.push(entry);
    }
  }

  private log(fields: Omit<RightsAuditEntry, "time">): void {
    const entry = this.newEntry(fields);
    this.record(entry);
    this.deliver(entry);
  }

  /** Count of audit entries whose external sink delivery has failed so far. */
  get pendingAuditDeliveries(): number {
    return this.pendingDelivery.length;
  }

  /** Re-attempt delivery of outbox entries; return how many are still pending.
   * Only re-ships the durable audit record — never changes erased state. */
  retryAuditDelivery(): number {
    const pending = this.pendingDelivery.splice(0, this.pendingDelivery.length);
    for (const entry of pending) this.deliver(entry);
    return this.pendingDelivery.length;
  }
}

// --- A synthetic store catalogue (from the G1 data map) ---------------------

export const STORE_PRIMARY = "primary";
export const STORE_EMBEDDINGS = "embeddings";
export const STORE_CACHE = "cache";
export const STORE_FEEDBACK = "feedback";
export const STORE_HUMAN_REVIEW = "human_review";
export const STORE_JOBS = "jobs";

export const DEFAULT_STORE_POLICIES: readonly StorePolicy[] = [
  {
    name: STORE_PRIMARY,
    location: "app-db://subjects",
    mode: "hard_delete",
    retentionTicks: 730,
  },
  {
    name: STORE_EMBEDDINGS,
    location: "vector-index://chunks",
    mode: "hard_delete",
    retentionTicks: 730,
  },
  {
    name: STORE_CACHE,
    location: "cache://responses",
    mode: "hard_delete",
    retentionTicks: 7,
  },
  {
    name: STORE_FEEDBACK,
    location: "feedback-db://entries",
    mode: "hard_delete",
    retentionTicks: 365,
  },
  {
    name: STORE_HUMAN_REVIEW,
    location: "review-queue://escalations",
    mode: "tombstone",
    retentionTicks: 2555, // ~7 years
    reason: "regulatory_retention",
    requiresReviewer: true,
    description: "retained for dispute resolution / regulatory defence",
  },
  {
    name: STORE_JOBS,
    location: "jobs-db://index-jobs",
    mode: "hard_delete",
    retentionTicks: 30,
  },
];

// A recognisable marker so tests can prove raw content is gone after erasure.
export const RAW_MARKER = "raw-content-for";

export const SEEDED_STORES: readonly string[] = [
  STORE_PRIMARY,
  STORE_EMBEDDINGS,
  STORE_CACHE,
  STORE_FEEDBACK,
  STORE_HUMAN_REVIEW,
  STORE_JOBS,
];

export function buildDefaultEngine(
  opts: { clock?: Clock; sink?: AuditSink } = {},
): RightsEngine {
  const engine = new RightsEngine(opts);
  for (const policy of DEFAULT_STORE_POLICIES) engine.registerStore(policy);
  return engine;
}

/** Give `subject` one copy in every store (embeddings gets two chunks). */
export function seedSyntheticSubject(
  engine: RightsEngine,
  subject: string,
  opts: { createdAt?: number } = {},
): void {
  const createdAt = opts.createdAt ?? 0;
  const detail = { detail: `${RAW_MARKER}-${subject}` };
  const at = { createdAt };
  // Record ids are opaque tokens (prefix_hex); the store keys by (subject,
  // recordId) so the same ids reused across subjects stay distinct.
  engine.addRecord(STORE_PRIMARY, subject, "profile_0", detail, at);
  engine.addRecord(STORE_EMBEDDINGS, subject, "chunk_0", detail, at);
  engine.addRecord(STORE_EMBEDDINGS, subject, "chunk_1", detail, at);
  engine.addRecord(STORE_CACHE, subject, "resp_0", detail, at);
  engine.addRecord(STORE_FEEDBACK, subject, "fb_0", detail, at);
  engine.addRecord(STORE_HUMAN_REVIEW, subject, "esc_0", detail, at);
  engine.addRecord(STORE_JOBS, subject, "job_0", detail, at);
}
