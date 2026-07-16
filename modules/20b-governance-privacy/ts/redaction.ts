/**
 * PII classification + redaction policy (Module 20b, Task 1).
 *
 * Synthetic data only — nothing here is real. The lesson: classify every field
 * a feature touches, then REDACT anything above your allowed sensitivity
 * *before* the record can reach a prompt, a log line, a trace, or a third-party
 * provider.
 *
 * Habits worth internalising:
 * - **Fail closed.** A field the policy has never heard of is treated as the
 *   most sensitive class (`restricted`) and dropped. `restricted` is dropped
 *   UNCONDITIONALLY — no `allow` / `mask` / `defaultAction` setting forwards it.
 * - **Restricted != masked.** Confidential fields can be masked to a
 *   placeholder when a hint is useful; genuinely restricted data (secrets,
 *   government ids) should not leave the boundary at all — drop the key.
 * - **Only redacted data may egress.** `redact()` mints an immutable,
 *   deep-frozen `RedactedRecord` and records it in a private authenticity
 *   registry; the prompt builder accepts nothing else, so a caller cannot
 *   accidentally build a prompt from un-redacted (or later-mutated) input.
 *
 * Honest boundary: the immutability / authenticity guards prevent ACCIDENTAL
 * misuse, casual forgery, and post-creation mutation. They do NOT defend against
 * a hostile in-process caller — one can call the provider directly anyway.
 *
 * Scope: this is FIELD-NAME-level classification. It does NOT scan the *content*
 * of free-text values. A secret typed INTO an allowed free-text field (e.g. an
 * SSN inside `support_topic` prose), or a bare scalar sitting in a list with no
 * key, is NOT caught here — a production system needs content-level DLP for that,
 * which is a separate, larger, itself-imperfect concern outside this lesson's
 * scope. What this *does* guarantee is that nested structures are recursively
 * classified (with cycle + depth guards), so a restricted key hidden inside an
 * allowed field's object/array value cannot slip through (see
 * `RedactionPolicy.redact`).
 *
 * This is engineering practice, not legal advice. See the module README's
 * "Important boundary" section.
 */

import { createHash } from "node:crypto";

export type DataClass = "public" | "internal" | "confidential" | "restricted";

export type Action = "keep" | "mask" | "drop";

/** The placeholder a masked value collapses to. Fixed so it stays recognisable. */
export const MASK_TOKEN = "***";

/**
 * Recursion bound for the redaction walkers. Any legitimate record is far
 * shallower; a deeper (or cyclic) structure fails closed rather than blowing the
 * stack — a denial-of-service guard on untrusted input.
 */
export const MAX_REDACTION_DEPTH = 32;

// Phantom brand: a compile-time-only marker so `RedactedRecord` is opaque. It is
// NEVER present at runtime, so it can't be reflected/copied to forge a record.
declare const REDACTED_BRAND: unique symbol;

/** A record that has passed through `RedactionPolicy.redact()`. Opaque brand. */
export type RedactedRecord = Record<string, unknown> & {
  readonly [REDACTED_BRAND]: true;
};

// Authenticity registry: membership in this module-private WeakSet — NOT a
// reflected property — is what makes a record authentic. Copying symbols onto a
// foreign object cannot buy membership. Weak so records are collected normally.
const REDACTED_REGISTRY = new WeakSet<object>();

/** Recursively freeze a value (objects AND arrays) so a redacted record cannot
 * be mutated after the fact (e.g. a caller adding `ssn` back). */
function deepFreeze(value: unknown): void {
  if (value !== null && typeof value === "object" && !Object.isFrozen(value)) {
    for (const nested of Object.values(value)) deepFreeze(nested);
    Object.freeze(value);
  }
}

/** Deep-freeze, then register as authentic. Honest scope: an in-process adversary
 * can always call the provider directly — this guards ACCIDENTAL misuse,
 * casual forgery, and post-creation mutation, not a malicious co-process. */
function mintRedacted(obj: Record<string, unknown>): RedactedRecord {
  deepFreeze(obj); // freezes obj and every nested object/array
  REDACTED_REGISTRY.add(obj);
  return obj as RedactedRecord;
}

/** Runtime guard: was this object minted by `redact()`? Authenticity is WeakSet
 * membership — not a reflected symbol (uncopyable) — so a symbol-copy or an
 * `Object.create(redacted)` forgery is rejected. */
export function isRedactedRecord(value: unknown): value is RedactedRecord {
  return typeof value === "object" && value !== null && REDACTED_REGISTRY.has(value);
}

/** True only for a plain `{...}` record — excludes arrays, Map, Set, Date, class
 * instances, etc. so exotic objects fail closed rather than being recursed. */
function isPlainRecord(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object") return false;
  const proto = Object.getPrototypeOf(value);
  return proto === Object.prototype || proto === null;
}

/** A stable, non-plaintext code for an unexpected field NAME. For low-entropy
 * names a hash is correlatable, not anonymous — the point is only to keep a raw
 * (possibly PII) key out of the log. */
function shortCode(name: string): string {
  return createHash("sha256").update(name).digest("hex").slice(0, 8);
}

const VALID_DATA_CLASSES = new Set<string>([
  "public",
  "internal",
  "confidential",
  "restricted",
]);

export interface RedactionPolicyOptions {
  classification: Record<string, DataClass>;
  /** Classes allowed through verbatim. Default: public + internal. */
  allow?: ReadonlySet<DataClass>;
  /** Classes replaced with MASK_TOKEN. Default: confidential. */
  mask?: ReadonlySet<DataClass>;
  /** Action for KNOWN, non-restricted classes in neither set. Default: drop. */
  defaultAction?: Action;
}

export class RedactionPolicy {
  readonly classification: Record<string, DataClass>;
  readonly allow: ReadonlySet<DataClass>;
  readonly mask: ReadonlySet<DataClass>;
  readonly defaultAction: Action;

  constructor(opts: RedactionPolicyOptions) {
    // Defensive copy + freeze: a later mutation of the caller's map / sets (or
    // the exported CLASSIFICATION) cannot reclassify a field. Sets are copied so
    // external mutation of a passed Set cannot change behaviour.
    this.classification = Object.freeze({ ...opts.classification });
    this.allow = new Set<DataClass>(opts.allow ?? ["public", "internal"]);
    this.mask = new Set<DataClass>(opts.mask ?? ["confidential"]);
    this.defaultAction = opts.defaultAction ?? "drop";

    // Fail loud on a misconfiguration that would try to forward restricted data.
    if (this.allow.has("restricted") || this.mask.has("restricted")) {
      throw new Error(
        "RESTRICTED data is always dropped; it must not appear in `allow` or `mask`.",
      );
    }
  }

  classify(field: string): DataClass {
    // `Object.hasOwn` avoids the prototype chain, so a field named "toString"
    // cannot resolve to an inherited method — and unknown fields fail closed.
    if (!Object.hasOwn(this.classification, field)) return "restricted";
    const dataClass = this.classification[field];
    // An invalid/unknown runtime class also fails closed to restricted.
    return VALID_DATA_CLASSES.has(dataClass) ? dataClass : "restricted";
  }

  actionFor(field: string): Action {
    const dataClass = this.classify(field);
    // Restricted (incl. unknown -> restricted) is dropped unconditionally,
    // independent of allow / mask / defaultAction.
    if (dataClass === "restricted") return "drop";
    if (this.allow.has(dataClass)) return "keep";
    if (this.mask.has(dataClass)) return "mask";
    // Only KNOWN, non-restricted classes reach the configurable default.
    return this.defaultAction;
  }

  /**
   * Return a branded `RedactedRecord` safe to send onward (prompt / log /
   * provider).
   *
   * A KEEP field whose value is non-scalar is redacted RECURSIVELY (see
   * `walkValue`) so a restricted key nested inside an allowed field's
   * object/array value cannot leak. Recursion is bounded and cycle-guarded.
   */
  redact(record: Record<string, unknown>): RedactedRecord {
    const walked = this.walkMapping(record, 0, new Set<object>([record]));
    return mintRedacted(walked);
  }

  private walkMapping(
    record: Record<string, unknown>,
    depth: number,
    seen: Set<object>,
  ): Record<string, unknown> {
    if (depth > MAX_REDACTION_DEPTH) return {}; // over-depth -> fail closed
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(record)) {
      const action = this.actionFor(key);
      if (action === "keep") out[key] = this.walkValue(value, depth + 1, seen);
      else if (action === "mask") out[key] = MASK_TOKEN;
      // "drop" -> omit the key entirely.
    }
    return out;
  }

  /**
   * Recursively make a KEEP-class value safe.
   *
   * - Scalars (string/number/boolean/null/undefined) pass through unchanged.
   * - Plain records are re-classified key-by-key with this same policy.
   * - Arrays are redacted element-wise.
   * - Over-depth, a reference cycle, or an exotic object (Map, Set, Date, class
   *   instance, bigint, ...) all fail closed to MASK_TOKEN.
   */
  private walkValue(value: unknown, depth: number, seen: Set<object>): unknown {
    if (depth > MAX_REDACTION_DEPTH) return MASK_TOKEN;
    if (value === null || value === undefined) return value;
    const kind = typeof value;
    if (kind === "string" || kind === "number" || kind === "boolean") {
      return value;
    }
    if (Array.isArray(value)) {
      if (seen.has(value)) return MASK_TOKEN; // ancestor cycle -> fail closed
      seen.add(value);
      try {
        return value.map((item) => this.walkValue(item, depth + 1, seen));
      } finally {
        seen.delete(value);
      }
    }
    if (isPlainRecord(value)) {
      if (seen.has(value)) return MASK_TOKEN; // ancestor cycle -> fail closed
      seen.add(value);
      try {
        return this.walkMapping(value, depth, seen);
      } finally {
        seen.delete(value);
      }
    }
    return MASK_TOKEN;
  }

  /**
   * Actions for KNOWN (classified) field names only — safe to log. Unknown
   * field NAMES are omitted because a user-supplied key can itself be PII;
   * summarise those with `unknownFieldDigest`.
   */
  knownFieldActions(record: Record<string, unknown>): Record<string, Action> {
    const out: Record<string, Action> = {};
    for (const key of Object.keys(record)) {
      if (Object.hasOwn(this.classification, key)) out[key] = this.actionFor(key);
    }
    return out;
  }

  /** Non-reversible summary of UNKNOWN field names — never the raw key. */
  unknownFieldDigest(record: Record<string, unknown>): {
    count: number;
    codes: string[];
  } {
    const unknown = Object.keys(record).filter(
      (key) => !Object.hasOwn(this.classification, key),
    );
    return { count: unknown.length, codes: unknown.map(shortCode).sort() };
  }

  /**
   * Field names redaction removes entirely (sorted).
   *
   * WARNING: returns RAW keys, including unknown/untrusted ones. Use only where
   * keys are trusted schema names; do NOT log verbatim for arbitrary input
   * (use `unknownFieldDigest` there).
   */
  droppedFields(record: Record<string, unknown>): string[] {
    return Object.keys(record)
      .filter((key) => this.actionFor(key) === "drop")
      .sort();
  }

  /**
   * Per-field {name: action} map over ALL keys, including raw unknown ones.
   *
   * WARNING: same caveat as `droppedFields`. For logging untrusted input prefer
   * `knownFieldActions` + `unknownFieldDigest`.
   */
  fieldActions(record: Record<string, unknown>): Record<string, Action> {
    const out: Record<string, Action> = {};
    for (const key of Object.keys(record)) out[key] = this.actionFor(key);
    return out;
  }
}

// --- A concrete synthetic subject + the default policy for the demo ---------
//
// Every value below is fabricated. The SSN, phone, and token are invalid and
// point at reserved/example ranges on purpose.

export const CLASSIFICATION: Record<string, DataClass> = {
  subject_id: "internal", // pseudonymous stable id — safe to log/join
  support_topic: "public", // the actual task text the model needs
  locale: "public", // affects wording, not identity
  display_name: "confidential", // direct identifier — mask it
  email: "confidential",
  phone: "confidential",
  ssn: "restricted", // government id — must never egress
  date_of_birth: "restricted",
  auth_token: "restricted", // secret — must never egress
};

export const DEFAULT_POLICY = new RedactionPolicy({
  classification: CLASSIFICATION,
});

export const SYNTHETIC_SUBJECT: Record<string, string> = {
  subject_id: "subj_0007",
  support_topic: "How do I export my invoices for last quarter?",
  locale: "en-US",
  display_name: "Jordan Rivera",
  email: "jordan.rivera@example.invalid",
  phone: "+1-555-0142",
  ssn: "123-45-6789",
  date_of_birth: "1990-04-12",
  auth_token: "sk-fake-DO-NOT-USE-abcdef123456",
};
