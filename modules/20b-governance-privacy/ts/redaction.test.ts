/**
 * Tests for the PII redaction policy + proof-of-redaction demo (Module 20b).
 *
 * The load-bearing test proves a *restricted* field's raw value reaches NONE of
 * the three egress surfaces — the prompt, the provider call, or the structured
 * log — while an allowed field survives and a confidential field is recoverable
 * only as the mask token. The provider is a real fake at the network boundary;
 * the log is captured through the injected sink. No production logic is
 * re-implemented here.
 *
 * Run: pnpm jest modules/20b-governance-privacy/ts/redaction.test.ts
 */

import { RecordingProvider } from "./fakes.js";
import { buildPrompt, runRedactionDemo } from "./demo.js";
import {
  CLASSIFICATION,
  DEFAULT_POLICY,
  isRedactedRecord,
  MASK_TOKEN,
  MAX_REDACTION_DEPTH,
  RedactionPolicy,
  SYNTHETIC_SUBJECT,
  type DataClass,
  type RedactedRecord,
} from "./redaction.js";

describe("RedactionPolicy", () => {
  test("masks confidential and drops restricted", () => {
    const redacted = DEFAULT_POLICY.redact(SYNTHETIC_SUBJECT);

    for (const restricted of ["ssn", "date_of_birth", "auth_token"]) {
      expect(redacted).not.toHaveProperty(restricted);
    }

    expect(redacted.email).toBe("***");
    expect(redacted.display_name).toBe("***");
    expect(redacted.phone).toBe("***");

    expect(redacted.support_topic).toBe(SYNTHETIC_SUBJECT.support_topic);
    expect(redacted.subject_id).toBe("subj_0007");
    expect(redacted.locale).toBe("en-US");
  });

  test("mask token is exactly three stars", () => {
    expect(MASK_TOKEN).toBe("***");
  });

  test("unknown field fails closed (dropped, classified restricted)", () => {
    expect(DEFAULT_POLICY.classify("mystery_field")).toBe("restricted");
    expect(DEFAULT_POLICY.actionFor("mystery_field")).toBe("drop");
    expect(Object.keys(DEFAULT_POLICY.redact({ mystery_field: "surprise" }))).toEqual(
      [],
    );
  });

  test("a prototype key name does not resolve to an inherited method", () => {
    // Without an own-property guard, classify("toString") could return the
    // inherited function; it must fail closed to "restricted" instead.
    expect(DEFAULT_POLICY.classify("toString")).toBe("restricted");
    expect(Object.keys(DEFAULT_POLICY.redact({ toString: "x" }))).toEqual([]);
  });

  test("does not mutate the input record", () => {
    const before = JSON.stringify(SYNTHETIC_SUBJECT);
    DEFAULT_POLICY.redact(SYNTHETIC_SUBJECT);
    expect(JSON.stringify(SYNTHETIC_SUBJECT)).toBe(before);
  });

  test("droppedFields lists exactly the restricted keys", () => {
    expect(DEFAULT_POLICY.droppedFields(SYNTHETIC_SUBJECT)).toEqual([
      "auth_token",
      "date_of_birth",
      "ssn",
    ]);
  });

  test("a stricter policy can drop confidential and disallow internal", () => {
    const strict = new RedactionPolicy({
      classification: DEFAULT_POLICY.classification,
      allow: new Set(["public"]),
      mask: new Set(),
    });
    const redacted = strict.redact(SYNTHETIC_SUBJECT);
    expect(redacted).not.toHaveProperty("email");
    expect(redacted).not.toHaveProperty("subject_id");
    expect(redacted.support_topic).toBe(SYNTHETIC_SUBJECT.support_topic);
  });
});

describe("proof of redaction across every egress surface", () => {
  test("a restricted value reaches no surface; allowed survives, confidential masks", async () => {
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];

    const result = await runRedactionDemo(SYNTHETIC_SUBJECT, provider, {
      log: (record) => logs.push(record),
    });

    expect(provider.calls).toHaveLength(1);
    const providerText = provider.recordedMessages.map((m) => m.content).join(" ");
    const logText = logs.map((r) => JSON.stringify(r)).join("\n");

    const rawSsn = SYNTHETIC_SUBJECT.ssn;
    const rawDob = SYNTHETIC_SUBJECT.date_of_birth;
    const rawToken = SYNTHETIC_SUBJECT.auth_token;
    const rawEmail = SYNTHETIC_SUBJECT.email;

    // (1) restricted (and masked-confidential) raw values appear on NO surface.
    for (const surface of [result.prompt, providerText, logText]) {
      expect(surface).not.toContain(rawSsn);
      expect(surface).not.toContain(rawDob);
      expect(surface).not.toContain(rawToken);
      expect(surface).not.toContain(rawEmail);
    }

    // (2) a redacted field is recoverable only as the mask token.
    expect(result.prompt).toContain(MASK_TOKEN);
    expect(providerText).toContain(MASK_TOKEN);
    expect(logText).toContain(MASK_TOKEN);

    // (3) an allowed field IS present verbatim on the outward surfaces.
    const topic = SYNTHETIC_SUBJECT.support_topic;
    expect(result.prompt).toContain(topic);
    expect(providerText).toContain(topic);
    expect(logText).toContain(topic);

    // Pseudonymous id deliberately retained; restricted *key* never in prompt.
    expect(logText).toContain("subj_0007");
    expect(result.prompt).not.toContain("ssn");
  });

  test("the structured log is a JSON-serialisable action audit", async () => {
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];

    await runRedactionDemo(SYNTHETIC_SUBJECT, provider, {
      log: (record) => logs.push(record),
    });

    expect(logs).toHaveLength(1);
    const entry = logs[0];
    expect(entry.event).toBe("llm_request");
    expect(entry.provider).toBe("fake-recording");

    const actions = entry.field_actions as Record<string, string>;
    expect(actions.ssn).toBe("drop");
    expect(actions.email).toBe("mask");
    expect(actions.support_topic).toBe("keep");

    expect(entry.dropped_fields).toEqual(["auth_token", "date_of_birth", "ssn"]);

    const redacted = entry.redacted as Record<string, unknown>;
    expect(redacted).not.toHaveProperty("ssn");
    expect(redacted.email).toBe("***");
  });

  test("a nested restricted value does not leak through any surface", async () => {
    // Regression: a KEEP-class field whose value is a nested object must not
    // carry restricted content through. Nested "leaked_ssn"/"text" are
    // unclassified -> fail closed -> dropped; nested "locale" is allowed -> kept.
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];
    const nested = {
      support_topic: {
        text: "reset password",
        leaked_ssn: "999-99-9999",
        locale: "en-US",
      },
      subject_id: "subj_0007",
    };

    const result = await runRedactionDemo(nested, provider, {
      log: (record) => logs.push(record),
    });

    const providerText = provider.recordedMessages.map((m) => m.content).join(" ");
    const logText = logs.map((r) => JSON.stringify(r)).join("\n");

    for (const surface of [result.prompt, providerText, logText]) {
      expect(surface).not.toContain("999-99-9999");
      expect(surface).not.toContain("leaked_ssn");
    }

    // Recursion classified nested keys: only the allowed nested scalar survives.
    expect(result.redacted.support_topic).toEqual({ locale: "en-US" });
    expect(result.prompt).toContain("en-US");
    expect(result.redacted.subject_id).toBe("subj_0007");
  });

  test("a MASK object collapses whole and a KEEP array is redacted element-wise", () => {
    const record = {
      email: { primary: "jordan@example.invalid" }, // confidential -> mask whole
      support_topic: [
        { note: "hi", ssn: "111-11-1111" }, // nested restricted key dropped
        "plain string", // scalar element kept
      ],
    };
    const redacted = DEFAULT_POLICY.redact(record);
    expect(redacted.email).toBe("***");
    expect(redacted.support_topic).toEqual([{}, "plain string"]);
  });
});

describe("buildPrompt", () => {
  test("renders a redacted record's surviving fields", () => {
    const redacted = DEFAULT_POLICY.redact({
      support_topic: "reset my password",
      email: "jordan@example.invalid",
      locale: "en-US",
    });
    const prompt = buildPrompt(redacted);
    expect(prompt).toContain("support_topic: reset my password");
    expect(prompt).toContain("email: ***"); // confidential masked
    expect(prompt).toContain("locale: en-US");
    expect(prompt).not.toContain("jordan@example.invalid");
  });

  test("rejects an un-redacted raw object at runtime", () => {
    // The type system already forbids this; the runtime guard catches a caller
    // that cast past it, so a prompt can never be built from un-redacted data.
    expect(() =>
      buildPrompt({
        support_topic: "hi",
        ssn: "123-45-6789",
      } as unknown as RedactedRecord),
    ).toThrow(/RedactedRecord/);
  });
});

describe("hardening (Codex review)", () => {
  test("restricted is dropped even when defaultAction is keep", () => {
    const loose = new RedactionPolicy({
      classification: {},
      allow: new Set(),
      mask: new Set(),
      defaultAction: "keep",
    });
    expect(loose.actionFor("api_key")).toBe("drop"); // unknown -> restricted
    expect(Object.keys(loose.redact({ api_key: "secret123" }))).toEqual([]);
  });

  test("policy construction rejects restricted in allow or mask", () => {
    expect(
      () =>
        new RedactionPolicy({
          classification: {},
          allow: new Set(["restricted"]),
        }),
    ).toThrow(/RESTRICTED/);
    expect(
      () =>
        new RedactionPolicy({
          classification: {},
          mask: new Set(["restricted"]),
        }),
    ).toThrow(/RESTRICTED/);
  });

  test("a cyclic input fails closed without crashing", () => {
    const cyclic: Record<string, unknown> = {};
    cyclic.support_topic = cyclic; // KEEP field references itself
    const redacted = DEFAULT_POLICY.redact(cyclic);
    expect(redacted.support_topic).toBe(MASK_TOKEN);
  });

  test("a very deep input is bounded (no stack overflow)", () => {
    let cursor: Record<string, unknown> = {};
    const root = cursor;
    for (let i = 0; i < MAX_REDACTION_DEPTH + 50; i++) {
      const child: Record<string, unknown> = {};
      cursor.support_topic = child;
      cursor = child;
    }
    const redacted = DEFAULT_POLICY.redact(root);
    expect(JSON.stringify(redacted)).toContain(MASK_TOKEN);
  });

  test("a PII-shaped key is never written to any surface", async () => {
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];
    const record = { "alice@example.com": "some value", support_topic: "hello" };

    const result = await runRedactionDemo(record, provider, {
      log: (r) => logs.push(r),
    });

    const providerText = provider.recordedMessages.map((m) => m.content).join(" ");
    const logText = logs.map((r) => JSON.stringify(r)).join("\n");
    for (const surface of [result.prompt, providerText, logText]) {
      expect(surface).not.toContain("alice@example.com");
      expect(surface).not.toContain("some value");
    }

    const unknown = logs[0].unknown_fields as { count: number; codes: string[] };
    expect(unknown.count).toBe(1);
    expect(unknown.codes).toHaveLength(1); // a stable code, not the raw key
  });

  test("an unusual unknown key is dropped and not logged", async () => {
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];
    const weird = "'; DROP TABLE users;--";
    const record = { [weird]: "x", support_topic: "hi" };

    const result = await runRedactionDemo(record, provider, {
      log: (r) => logs.push(r),
    });

    const logText = logs.map((r) => JSON.stringify(r)).join("\n");
    expect(logText).not.toContain(weird);
    expect(result.prompt).not.toContain(weird);
  });

  test("a KNOWN restricted key nested under an allowed field is dropped", async () => {
    const provider = new RecordingProvider();
    const logs: Record<string, unknown>[] = [];
    const record = {
      support_topic: { ssn: "222-22-2222", locale: "en-US" },
      subject_id: "s",
    };

    const result = await runRedactionDemo(record, provider, {
      log: (r) => logs.push(r),
    });

    const providerText = provider.recordedMessages.map((m) => m.content).join(" ");
    const logText = logs.map((r) => JSON.stringify(r)).join("\n");
    for (const surface of [result.prompt, providerText, logText]) {
      expect(surface).not.toContain("222-22-2222");
    }
    expect(result.redacted.support_topic).toEqual({ locale: "en-US" });
  });

  test("a numeric scalar is kept and a numeric restricted value dropped", () => {
    const redacted = DEFAULT_POLICY.redact({
      support_topic: { locale: 42, ssn: 999999 },
    });
    expect(redacted.support_topic).toEqual({ locale: 42 });
  });

  test("a secret in an allowed free-text value is NOT redacted (documented limit)", () => {
    // Field-name classification cannot catch a secret typed INTO an allowed
    // free-text value. This is NOT content/DLP scanning; asserting it SURVIVES
    // keeps the limitation honest rather than implying a false guarantee.
    const redacted = DEFAULT_POLICY.redact({
      support_topic: "my ssn is 555-55-5555",
      subject_id: "s",
    });
    expect(redacted.support_topic).toContain("555-55-5555");
  });
});

describe("immutable + forgery-resistant RedactedRecord (Codex round 2)", () => {
  test("a returned redacted record is deep-frozen and cannot gain a field", () => {
    const redacted = DEFAULT_POLICY.redact({
      support_topic: { locale: "en-US" },
    });
    expect(Object.isFrozen(redacted)).toBe(true);
    expect(Object.isFrozen(redacted.support_topic)).toBe(true); // nested too

    // Attempt to add a restricted field after the fact (frozen -> no-op/throws).
    try {
      (redacted as Record<string, unknown>).ssn = "111-11-1111";
    } catch {
      /* strict mode throws; sloppy silently ignores — either is acceptable */
    }
    expect(Object.hasOwn(redacted, "ssn")).toBe(false);
    expect(buildPrompt(redacted)).not.toContain("111-11-1111");
  });

  test("buildPrompt rejects an Object.create() forgery", () => {
    const redacted = DEFAULT_POLICY.redact({ support_topic: "hello" });
    // A new object that inherits from a real record, plus its own raw field.
    const forged = Object.create(redacted) as RedactedRecord;
    (forged as Record<string, unknown>).ssn = "111-11-1111";

    // Not the same object -> not in the registry -> rejected.
    expect(isRedactedRecord(forged)).toBe(false);
    expect(() => buildPrompt(forged)).toThrow(/RedactedRecord/);
  });
});

describe("registry authenticity + config freeze (Codex round 3)", () => {
  test("a symbol-copy forgery is rejected (registry membership, not a reflected brand)", () => {
    const real = DEFAULT_POLICY.redact({ support_topic: "hello" });
    // Copy every own symbol from a real record onto a foreign object with a raw
    // restricted field. (There is no runtime brand symbol, so this copies
    // nothing — but even if there were, membership is what counts.)
    const fake: Record<string | symbol, unknown> = { ssn: "111-11-1111" };
    for (const s of Object.getOwnPropertySymbols(real)) {
      fake[s] = (real as Record<symbol, unknown>)[s];
    }
    expect(isRedactedRecord(fake)).toBe(false);
    expect(() => buildPrompt(fake as unknown as RedactedRecord)).toThrow(
      /RedactedRecord/,
    );
  });

  test("nested arrays are deep-frozen too", () => {
    const redacted = DEFAULT_POLICY.redact({
      support_topic: [{ locale: "en-US" }, "note"],
    });
    const arr = redacted.support_topic as unknown[];
    expect(Object.isFrozen(arr)).toBe(true);
    expect(Object.isFrozen(arr[0])).toBe(true);
  });

  test("mutating classification after construction cannot reclassify restricted", () => {
    const cls: Record<string, DataClass> = {
      ssn: "restricted",
      support_topic: "public",
    };
    const policy = new RedactionPolicy({ classification: cls });
    cls.ssn = "public"; // mutate the caller's map after construction
    expect(policy.actionFor("ssn")).toBe("drop"); // frozen copy is unaffected
    expect(Object.isFrozen(policy.classification)).toBe(true);
  });

  test("mutating the exported CLASSIFICATION cannot reclassify DEFAULT_POLICY", () => {
    expect(DEFAULT_POLICY.classification).not.toBe(CLASSIFICATION);
    expect(Object.isFrozen(DEFAULT_POLICY.classification)).toBe(true);
    expect(DEFAULT_POLICY.actionFor("ssn")).toBe("drop");
  });

  test("an invalid runtime class fails closed to restricted", () => {
    const bad = new RedactionPolicy({
      classification: { weird: "banana" as DataClass },
      defaultAction: "keep",
    });
    expect(bad.classify("weird")).toBe("restricted");
    expect(bad.actionFor("weird")).toBe("drop");
  });
});
