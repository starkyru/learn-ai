/**
 * Consent + lawful-basis engine (Module 20b, Task 2).
 *
 * Synthetic data only — nothing here is real, and none of it is legal advice.
 *
 * The teaching point: **consent is just ONE lawful basis among several.** A
 * processing activity is authorised only if *some* valid basis covers its
 * *exact* purpose. Consent can be withdrawn — and withdrawing it stops
 * consent-based processing for that purpose — but it does NOT revoke a
 * *different* basis (contract, legal obligation, …) that authorises the same
 * purpose. Treating consent as a universal on/off switch is the classic mistake
 * this module guards against.
 *
 * Design notes:
 * - **Purpose limitation.** `canProcess` checks the exact purpose only. Consent
 *   for purpose A never authorises purpose B — there is no "blanket consent."
 * - **Auditable decisions.** Every capture / withdraw / authorisation appends an
 *   `AuditEntry` (actor, time, subject, purpose, basis, outcome, reason).
 * - **Safe logging (from Task 1).** The engine only ever handles a *pseudonymous*
 *   subject id and coarse purpose/basis labels — never raw PII. Keep it that way.
 */

export type LawfulBasis =
  | "consent"
  | "contract"
  | "legal_obligation"
  | "legitimate_interest"
  | "vital_interest"
  | "public_task";

export type ConsentState = "granted" | "withdrawn";

/** Declares that `purpose` is processed under `basis`. A purpose may be declared
 * under more than one basis; each declaration is one of these. */
export interface ProcessingActivity {
  purpose: string;
  basis: LawfulBasis;
  description?: string;
}

/** Immutable consent decision for one (subject, purpose). Always `consent`. */
export interface ConsentRecord {
  subject: string; // pseudonymous subject id
  purpose: string;
  state: ConsentState;
  /** Policy/notice version in force at capture — recorded for the audit trail
   * only. It is NOT enforced here: bumping a version does not auto-invalidate an
   * existing consent. A production system that needs re-consent on version
   * change must implement that check explicitly. */
  version: string;
  time: number;
  basis: "consent";
}

/** Outcome of `canProcess`. */
export interface Decision {
  allowed: boolean;
  basis: LawfulBasis | null; // which basis authorised it (null when denied)
  reason: string;
}

/** One row of the append-only decision log — exactly these fields. */
export interface AuditEntry {
  actor: string;
  time: number;
  subject: string; // pseudonymous subject id — never a raw identifier
  purpose: string;
  basis: LawfulBasis | null;
  outcome: string; // "granted" | "withdrawn" | "allow" | "deny"
  reason: string;
}

export type Clock = () => number;
export type AuditSink = (entry: AuditEntry) => void;

/** A deterministic monotonic clock: 0, 1, 2, … (one tick per read). */
function tickClock(): Clock {
  let n = 0;
  return () => n++;
}

const VALID_BASES = new Set<string>([
  "consent",
  "contract",
  "legal_obligation",
  "legitimate_interest",
  "vital_interest",
  "public_task",
]);

// Every value that reaches an audit entry must be a safe label, never raw PII.
// The `^…$` anchors (no `m` flag) reject a trailing newline or embedded control
// character, matching Python's `fullmatch`. `actor`/`version` use STRICT formats
// that must start with a letter/`v`, so an SSN- or phone-shaped run of digits and
// dashes (e.g. `123-45-6789`) fails.
// A subject is a STRICT opaque token: `subj_` + hex only (mirrors rights.ts). A
// looser `subj_[A-Za-z0-9_]+` would admit `subj_Alice_Smith` — an identifier that
// is itself PII — and persist it in the audit.
const SUBJECT_PATTERN = /^subj_[0-9a-f]+$/; // pseudonymous id, e.g. subj_0042
const ACTOR_PATTERN = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/; // service id, e.g. privacy-service
const PURPOSE_PATTERN = /^[a-z][a-z0-9_]*$/; // snake_case purpose label
const VERSION_PATTERN = /^v?\d+(\.\d+)*$/; // version label, e.g. v1, 1.2, 2026.07.01

function assertValidBasis(basis: string): asserts basis is LawfulBasis {
  if (!VALID_BASES.has(basis)) {
    throw new Error(`unknown lawful basis: ${JSON.stringify(basis)}`);
  }
}

function assertPseudonymousSubject(subject: string): void {
  if (typeof subject !== "string" || !SUBJECT_PATTERN.test(subject)) {
    throw new Error(
      `subject must be an opaque pseudonymous token like 'subj_0042' (subj_ + ` +
        `hex only; a name/email/SSN suffix like 'subj_Alice_Smith' is rejected); ` +
        `got ${JSON.stringify(subject)}`,
    );
  }
}

function assertSafeActor(actor: string): void {
  // Must start with a letter, so an SSN/phone-shaped digit-dash run is rejected.
  if (typeof actor !== "string" || !ACTOR_PATTERN.test(actor)) {
    throw new Error(
      `actor must be a service id like 'privacy-service' (starts with a letter; ` +
        `not a digit-dash run), not free PII; got ${JSON.stringify(actor)}`,
    );
  }
}

function assertSafePurpose(purpose: string): void {
  if (typeof purpose !== "string" || !PURPOSE_PATTERN.test(purpose)) {
    throw new Error(
      `purpose must be a snake_case label like 'marketing_email' (no raw PII); ` +
        `got ${JSON.stringify(purpose)}`,
    );
  }
}

function assertSafeVersion(version: string): void {
  // A dotted/semver-style label, so an SSN-shaped '123-45-6789' is rejected.
  if (typeof version !== "string" || !VERSION_PATTERN.test(version)) {
    throw new Error(
      `version must be a version label like 'v1', '1.2', or '2026.07.01' ` +
        `(digits/dots, optional leading 'v'; no raw PII); got ${JSON.stringify(version)}`,
    );
  }
}

/**
 * Note on `actor`: every method takes a free-form `actor` string for the audit
 * record. In production this must be derived from an authenticated caller
 * identity, not passed in by the caller — here it is a plain parameter for the
 * exercise.
 */
export class ConsentEngine {
  private readonly clock: Clock;
  private readonly sink?: AuditSink;
  private readonly activities = new Map<string, LawfulBasis[]>();
  private readonly consents = new Map<string, ConsentRecord>();
  private readonly audit: AuditEntry[] = [];

  constructor(opts: { clock?: Clock; sink?: AuditSink } = {}) {
    this.clock = opts.clock ?? tickClock();
    this.sink = opts.sink;
  }

  // --- registration ------------------------------------------------------

  registerActivity(activity: ProcessingActivity): void {
    // Reject a runtime-invalid basis or an unsafe purpose label (static types
    // can be bypassed) so malformed config can never authorise processing it
    // shouldn't, nor write raw PII to the audit trail.
    assertSafePurpose(activity.purpose);
    assertValidBasis(activity.basis);
    const bases = this.activities.get(activity.purpose) ?? [];
    if (!bases.includes(activity.basis)) bases.push(activity.basis);
    this.activities.set(activity.purpose, bases);
  }

  registerActivities(activities: Iterable<ProcessingActivity>): void {
    for (const activity of activities) this.registerActivity(activity);
  }

  basesFor(purpose: string): LawfulBasis[] {
    return [...(this.activities.get(purpose) ?? [])];
  }

  // --- consent lifecycle -------------------------------------------------

  captureConsent(
    subject: string,
    purpose: string,
    opts: { actor: string; version: string },
  ): ConsentRecord {
    assertPseudonymousSubject(subject);
    assertSafeActor(opts.actor);
    assertSafePurpose(purpose);
    assertSafeVersion(opts.version);
    // Frozen at rest AND on return, so a caller cannot mutate `.state` back to
    // "granted" after withdrawal (or otherwise tamper with the stored record).
    const record: ConsentRecord = Object.freeze({
      subject,
      purpose,
      state: "granted",
      version: opts.version,
      time: this.clock(),
      basis: "consent",
    });
    this.consents.set(this.key(subject, purpose), record);
    this.log({
      actor: opts.actor,
      time: record.time,
      subject,
      purpose,
      basis: "consent",
      outcome: "granted",
      reason: `consent captured (version ${opts.version})`,
    });
    return record;
  }

  withdrawConsent(
    subject: string,
    purpose: string,
    opts: { actor: string },
  ): ConsentRecord {
    assertPseudonymousSubject(subject);
    assertSafeActor(opts.actor);
    assertSafePurpose(purpose);
    const previous = this.consents.get(this.key(subject, purpose));
    const record: ConsentRecord = Object.freeze({
      subject,
      purpose,
      state: "withdrawn",
      version: previous?.version ?? "none",
      time: this.clock(),
      basis: "consent",
    });
    this.consents.set(this.key(subject, purpose), record);
    this.log({
      actor: opts.actor,
      time: record.time,
      subject,
      purpose,
      basis: "consent",
      outcome: "withdrawn",
      reason: "consent withdrawn",
    });
    return record;
  }

  hasValidConsent(subject: string, purpose: string): boolean {
    const record = this.consents.get(this.key(subject, purpose));
    return record !== undefined && record.state === "granted";
  }

  // --- purpose-limited authorisation ------------------------------------

  /**
   * Authorise processing `subject`'s data for the EXACT `purpose`. Allowed iff
   * some registered basis is currently valid: a `consent` basis needs a granted
   * (not withdrawn) record; any non-consent basis authorises by its declaration.
   * Consent for a different purpose never helps — no blanket consent.
   *
   * This is a POINT-IN-TIME decision. Do NOT cache the boolean and act on it
   * later: a subject may withdraw consent between the check and the side effect
   * (a time-of-check/time-of-use gap). Re-check at the side-effect boundary —
   * see `guardedProcess`, which does exactly that.
   */
  canProcess(
    subject: string,
    purpose: string,
    opts: { actor?: string } = {},
  ): Decision {
    const actor = opts.actor ?? "system";
    assertPseudonymousSubject(subject);
    assertSafeActor(actor);
    assertSafePurpose(purpose);
    const bases = this.activities.get(purpose) ?? [];
    const decision = this.evaluate(subject, purpose, bases);
    this.log({
      actor,
      time: this.clock(),
      subject,
      purpose,
      basis: decision.basis,
      outcome: decision.allowed ? "allow" : "deny",
      reason: decision.reason,
    });
    return decision;
  }

  /**
   * Re-check authorisation atomically, then run `action` only if allowed.
   *
   * Binds the consent check to the side effect: it calls `canProcess`
   * immediately before invoking `action` and refuses to run it when not
   * currently authorised, so a stale earlier allow cannot be replayed after a
   * withdrawal. (Deliberately simple — a real system may need a stronger
   * capability/transaction boundary.)
   *
   * `canProcess` invokes the audit sink, and a synchronous sink could withdraw
   * consent re-entrantly during that call. So the gate is a FINAL bare re-check
   * of CURRENT state (`isAuthorisedNow`, which does NOT call the sink) taken
   * IMMEDIATELY before dispatch — nothing runs between that check and `action()`,
   * so the sink cannot invalidate it afterwards.
   *
   * No lock is needed: JS runs on a single-threaded event loop, so this
   * synchronous re-check → dispatch cannot be interleaved by another thread
   * (unlike Python, whose `ConsentEngine` holds an RLock across the same window).
   */
  guardedProcess<T>(
    subject: string,
    purpose: string,
    action: () => T,
    opts: { actor?: string } = {},
  ): { decision: Decision; ran: boolean; result: T | null } {
    const decision = this.canProcess(subject, purpose, opts);
    if (!decision.allowed) {
      return { decision, ran: false, result: null };
    }
    if (!this.isAuthorisedNow(subject, purpose)) {
      const revoked: Decision = {
        allowed: false,
        basis: null,
        reason: "authorisation revoked before dispatch",
      };
      this.log({
        actor: opts.actor ?? "system",
        time: this.clock(),
        subject,
        purpose,
        basis: null,
        outcome: "deny",
        reason: revoked.reason,
      });
      return { decision: revoked, ran: false, result: null };
    }
    // No sink callback between the check above and the dispatch below.
    return { decision, ran: true, result: action() };
  }

  /** Bare, side-effect-free authorisation check of CURRENT state (no sink). */
  private isAuthorisedNow(subject: string, purpose: string): boolean {
    const bases = this.activities.get(purpose) ?? [];
    return this.evaluate(subject, purpose, bases).allowed;
  }

  private evaluate(subject: string, purpose: string, bases: LawfulBasis[]): Decision {
    if (bases.length === 0) {
      return {
        allowed: false,
        basis: null,
        reason: `no lawful basis registered for purpose '${purpose}'`,
      };
    }
    for (const basis of bases) {
      if (basis === "consent") {
        if (this.hasValidConsent(subject, purpose)) {
          return {
            allowed: true,
            basis,
            reason: `authorised by consent for purpose '${purpose}'`,
          };
        }
      } else {
        // A non-consent basis authorises by declaration; it is unaffected by
        // whether consent was ever granted or has been withdrawn.
        return {
          allowed: true,
          basis,
          reason: `authorised by ${basis} for purpose '${purpose}'`,
        };
      }
    }
    return {
      allowed: false,
      basis: null,
      reason: `purpose '${purpose}' relies on consent, which is not currently granted`,
    };
  }

  // --- audit -------------------------------------------------------------

  get auditLog(): readonly AuditEntry[] {
    // Defensive copy — `readonly` is erased at runtime, so returning the live
    // array would let a caller push/overwrite the append-only trail.
    return [...this.audit];
  }

  auditRecords(): AuditEntry[] {
    return this.audit.map((entry) => ({ ...entry }));
  }

  private key(subject: string, purpose: string): string {
    // subject/purpose are opaque labels; JSON.stringify keeps the composite
    // key unambiguous without a delimiter that a label might contain.
    return JSON.stringify([subject, purpose]);
  }

  private log(entry: AuditEntry): void {
    // Freeze before storing AND before handing to the sink, so neither a later
    // reader (`auditLog[0].actor = …`) nor a sink mutating its argument can
    // rewrite the append-only trail.
    const frozen = Object.freeze(entry);
    this.audit.push(frozen);
    this.sink?.(frozen);
  }
}

// --- A synthetic activity catalogue for the demo/tests ----------------------

export const PURPOSE_MARKETING_EMAIL = "marketing_email";
export const PURPOSE_PRODUCT_ANALYTICS = "product_analytics";
export const PURPOSE_ORDER_FULFILMENT = "order_fulfilment";
export const PURPOSE_FRAUD_DETECTION = "fraud_detection";
export const PURPOSE_ACCOUNT_SECURITY = "account_security";

export const DEFAULT_ACTIVITIES: readonly ProcessingActivity[] = [
  {
    purpose: PURPOSE_MARKETING_EMAIL,
    basis: "consent",
    description: "send marketing email",
  },
  {
    purpose: PURPOSE_PRODUCT_ANALYTICS,
    basis: "consent",
    description: "optional analytics",
  },
  {
    purpose: PURPOSE_ORDER_FULFILMENT,
    basis: "contract",
    description: "ship the order",
  },
  {
    purpose: PURPOSE_FRAUD_DETECTION,
    basis: "legal_obligation",
    description: "AML/fraud checks",
  },
  // Same purpose, two bases (consent first so the demo shows the authorising
  // basis SHIFT from consent to contract on withdrawal). Basis precedence is a
  // policy choice; here consent is tried first, contract is the fallback.
  {
    purpose: PURPOSE_ACCOUNT_SECURITY,
    basis: "consent",
    description: "optional extra checks",
  },
  {
    purpose: PURPOSE_ACCOUNT_SECURITY,
    basis: "contract",
    description: "secure the account",
  },
];

export function buildDefaultEngine(
  opts: { clock?: Clock; sink?: AuditSink } = {},
): ConsentEngine {
  const engine = new ConsentEngine(opts);
  engine.registerActivities(DEFAULT_ACTIVITIES);
  return engine;
}
