/**
 * Tests for the consent + lawful-basis engine (Module 20b, Task 2).
 *
 * The load-bearing test proves consent is NOT a universal switch: withdrawing it
 * denies consent-based processing for a purpose, yet the SAME purpose stays
 * lawful when a different basis (contract/legal obligation) authorises it. Tests
 * call the real engine; the only injected boundary is the audit sink (an array).
 *
 * Run: pnpm jest modules/20b-governance-privacy/ts/consent.test.ts
 */

import {
  buildDefaultEngine,
  ConsentEngine,
  DEFAULT_ACTIVITIES,
  PURPOSE_ACCOUNT_SECURITY,
  PURPOSE_FRAUD_DETECTION,
  PURPOSE_MARKETING_EMAIL,
  PURPOSE_ORDER_FULFILMENT,
  PURPOSE_PRODUCT_ANALYTICS,
  type AuditEntry,
  type ConsentState,
  type LawfulBasis,
} from "./consent.js";

const SUBJECT = "subj_0042";
const OTHER = "subj_0099";
const ACTOR = "privacy-service";

const AUDIT_KEYS = [
  "actor",
  "basis",
  "outcome",
  "purpose",
  "reason",
  "subject",
  "time",
];

describe("purpose limitation", () => {
  test("a consented purpose is allowed via consent", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const decision = engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL);
    expect(decision.allowed).toBe(true);
    expect(decision.basis).toBe("consent");
  });

  test("blanket consent is rejected (consent for A does not authorise B)", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const decision = engine.canProcess(SUBJECT, PURPOSE_PRODUCT_ANALYTICS);
    expect(decision.allowed).toBe(false);
    expect(decision.basis).toBeNull();
    expect(decision.reason).toContain("consent");
  });

  test("an unregistered purpose is denied", () => {
    const engine = buildDefaultEngine();
    const decision = engine.canProcess(SUBJECT, "sell_to_third_party");
    expect(decision.allowed).toBe(false);
    expect(decision.basis).toBeNull();
    expect(decision.reason).toContain("no lawful basis");
  });

  test("consent is scoped to the subject", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL).allowed).toBe(true);
    expect(engine.canProcess(OTHER, PURPOSE_MARKETING_EMAIL).allowed).toBe(false);
  });
});

describe("non-consent bases", () => {
  test("contract allows without any consent", () => {
    const engine = buildDefaultEngine();
    const decision = engine.canProcess(SUBJECT, PURPOSE_ORDER_FULFILMENT);
    expect(decision.allowed).toBe(true);
    expect(decision.basis).toBe("contract");
    expect(engine.hasValidConsent(SUBJECT, PURPOSE_ORDER_FULFILMENT)).toBe(false);
  });

  test("legal obligation allows", () => {
    const engine = buildDefaultEngine();
    const decision = engine.canProcess(SUBJECT, PURPOSE_FRAUD_DETECTION);
    expect(decision.allowed).toBe(true);
    expect(decision.basis).toBe("legal_obligation");
  });
});

describe("withdrawal is not universal revocation", () => {
  test("withdrawal denies a consent-only purpose", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL).allowed).toBe(true);

    engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });

    const after = engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL);
    expect(after.allowed).toBe(false);
    expect(after.basis).toBeNull();
    expect(engine.hasValidConsent(SUBJECT, PURPOSE_MARKETING_EMAIL)).toBe(false);
  });

  test("withdrawal does NOT revoke a contract basis for the same purpose", () => {
    // account_security is authorised under BOTH consent and contract.
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, {
      actor: ACTOR,
      version: "v1",
    });

    const before = engine.canProcess(SUBJECT, PURPOSE_ACCOUNT_SECURITY);
    expect(before.allowed).toBe(true);
    expect(before.basis).toBe("consent"); // consent tried first

    engine.withdrawConsent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, { actor: ACTOR });

    // Consent-based authorisation is gone...
    expect(engine.hasValidConsent(SUBJECT, PURPOSE_ACCOUNT_SECURITY)).toBe(false);
    // ...but the SAME purpose is STILL allowed — now under contract.
    const after = engine.canProcess(SUBJECT, PURPOSE_ACCOUNT_SECURITY);
    expect(after.allowed).toBe(true);
    expect(after.basis).toBe("contract");
  });
});

describe("consent lifecycle + audit", () => {
  test("capture then withdraw updates state and carries the version forward", () => {
    const engine = buildDefaultEngine();
    const granted = engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v2",
    });
    expect(granted.state).toBe("granted");
    expect(granted.basis).toBe("consent");
    expect(granted.version).toBe("v2");

    const withdrawn = engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
    });
    expect(withdrawn.state).toBe("withdrawn");
    expect(withdrawn.version).toBe("v2");
  });

  test("an injected clock orders records deterministically", () => {
    const ticks = [10, 11, 12];
    let i = 0;
    const engine = buildDefaultEngine({ clock: () => ticks[i++] });
    const captured = engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(captured.time).toBe(10);
    engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL); // consumes tick 11
    expect(engine.auditLog[engine.auditLog.length - 1].time).toBe(11);
  });

  test("audit records have exactly the required fields and a pseudonymous subject", () => {
    const captured: AuditEntry[] = [];
    const engine = buildDefaultEngine({ sink: (e) => captured.push(e) });
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });
    engine.canProcess(SUBJECT, PURPOSE_PRODUCT_ANALYTICS, { actor: ACTOR }); // deny

    // The sink saw every entry, identical to the stored log.
    expect(captured).toEqual(engine.auditRecords());

    for (const record of engine.auditRecords()) {
      expect(Object.keys(record).sort()).toEqual(AUDIT_KEYS);
      expect(record.subject).toBe(SUBJECT); // pseudonymous id only
      expect(record.actor).toBe(ACTOR);
    }

    const [captureRec, allowRec, denyRec] = engine.auditRecords();
    expect(captureRec.outcome).toBe("granted");
    expect(captureRec.basis).toBe("consent");
    expect(allowRec.outcome).toBe("allow");
    expect(allowRec.basis).toBe("consent");
    expect(denyRec.outcome).toBe("deny");
    expect(denyRec.basis).toBeNull();
  });

  test("audit records carry no raw identifier", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });
    for (const record of engine.auditRecords()) {
      for (const value of Object.values(record)) {
        expect(String(value)).not.toContain("@");
        expect(String(value)).not.toContain("123-45-6789");
      }
    }
  });

  test("basesFor de-duplicates and the default catalogue is dual-basis", () => {
    const engine = new ConsentEngine();
    engine.registerActivity({ purpose: PURPOSE_ORDER_FULFILMENT, basis: "contract" });
    engine.registerActivity({ purpose: PURPOSE_ORDER_FULFILMENT, basis: "contract" });
    expect(engine.basesFor(PURPOSE_ORDER_FULFILMENT)).toEqual(["contract"]);
    expect(engine.basesFor("unknown")).toEqual([]);

    const purposes = DEFAULT_ACTIVITIES.map((a) => a.purpose);
    expect(purposes).toContain(PURPOSE_ACCOUNT_SECURITY);
    expect(buildDefaultEngine().basesFor(PURPOSE_ACCOUNT_SECURITY)).toEqual([
      "consent",
      "contract",
    ]);
  });

  test("auditLog getter returns a defensive copy (append-only trail can't be tampered)", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const snapshot = engine.auditLog;
    const before = snapshot.length;

    // `readonly` is erased at runtime; try to push a forged entry onto what the
    // getter returned.
    (snapshot as AuditEntry[]).push({
      actor: "attacker",
      time: 999,
      subject: "x",
      purpose: "y",
      basis: null,
      outcome: "allow",
      reason: "forged",
    });

    // A subsequent read is unaffected — the trail was not tampered with.
    expect(engine.auditLog.length).toBe(before);
    expect(engine.auditLog.map((e) => e.actor)).not.toContain("attacker");
  });
});

describe("immutable shared state + input validation (Codex round 1)", () => {
  test("mutating the returned withdrawal record does not re-enable processing", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const withdrawn = engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
    });

    // Frozen — attempting to flip it back to "granted" is a no-op/throws.
    try {
      (withdrawn as { state: ConsentState }).state = "granted";
    } catch {
      /* strict mode throws */
    }
    expect(withdrawn.state).toBe("withdrawn");
    expect(engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL).allowed).toBe(false);
  });

  test("registering a bogus basis is rejected (no allow-when-deny)", () => {
    const engine = new ConsentEngine();
    expect(() =>
      engine.registerActivity({ purpose: "p", basis: "bogus" as LawfulBasis }),
    ).toThrow(/unknown lawful basis/);
    // The purpose was never registered -> denied, not wrongly allowed.
    expect(engine.canProcess(SUBJECT, "p").allowed).toBe(false);
  });

  test("a raw-PII subject is rejected and never reaches the audit sink", () => {
    const captured: AuditEntry[] = [];
    const engine = buildDefaultEngine({ sink: (e) => captured.push(e) });
    // `subj_Alice_Smith` / `subj_00FF` carry the prefix but are NOT hex — the old
    // `subj_[A-Za-z0-9_]+` rule wrongly admitted them; hex-only now rejects them.
    for (const bad of [
      "alice@example.com",
      "123-45-6789",
      "Alice Smith",
      "user 7",
      "subj_Alice_Smith",
      "subj_00FF",
    ]) {
      expect(() =>
        engine.captureConsent(bad, PURPOSE_MARKETING_EMAIL, {
          actor: ACTOR,
          version: "v1",
        }),
      ).toThrow(/pseudonymous/);
      expect(() =>
        engine.canProcess(bad, PURPOSE_MARKETING_EMAIL, { actor: ACTOR }),
      ).toThrow(/pseudonymous/);
    }
    expect(captured).toEqual([]);

    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(
      engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR }).allowed,
    ).toBe(true);
  });

  test("an unsafe actor is rejected", () => {
    const engine = buildDefaultEngine();
    expect(() =>
      engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
        actor: "alice@example.com",
        version: "v1",
      }),
    ).toThrow(/actor/);
  });

  test("stored audit entries are frozen (a reader cannot rewrite them)", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const entry = engine.auditLog[0];
    try {
      (entry as { actor: string }).actor = "attacker";
    } catch {
      /* frozen */
    }
    expect(engine.auditLog[0].actor).toBe(ACTOR);
  });

  test("a sink mutating its argument cannot rewrite the stored audit trail", () => {
    const engine = buildDefaultEngine({
      sink: (entry) => {
        try {
          (entry as { actor: string }).actor = "attacker";
        } catch {
          /* frozen */
        }
      },
    });
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(engine.auditLog[0].actor).toBe(ACTOR);
  });
});

describe("validate all audit inputs + TOCTOU + anchor parity (Codex round 2)", () => {
  test("a PII-shaped purpose or version is rejected and never audited", () => {
    const captured: AuditEntry[] = [];
    const engine = buildDefaultEngine({ sink: (e) => captured.push(e) });
    expect(() =>
      engine.captureConsent(SUBJECT, "alice@example.com", {
        actor: ACTOR,
        version: "v1",
      }),
    ).toThrow(/purpose/);
    expect(() =>
      engine.canProcess(SUBJECT, "alice@example.com", { actor: ACTOR }),
    ).toThrow(/purpose/);
    expect(() =>
      engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
        actor: ACTOR,
        version: "alice@example.com",
      }),
    ).toThrow(/version/);
    expect(captured).toEqual([]);
  });

  test("guardedProcess does not run the action after withdrawal", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    expect(
      engine.canProcess(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR }).allowed,
    ).toBe(true);
    engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });

    let ran = 0;
    const result = engine.guardedProcess(
      SUBJECT,
      PURPOSE_MARKETING_EMAIL,
      () => {
        ran += 1;
        return "processed";
      },
      { actor: ACTOR },
    );
    expect(result.ran).toBe(false);
    expect(result.result).toBeNull();
    expect(result.decision.allowed).toBe(false);
    expect(ran).toBe(0); // the side effect never ran
  });

  test("guardedProcess runs the action when authorised", () => {
    const engine = buildDefaultEngine();
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });
    const result = engine.guardedProcess(
      SUBJECT,
      PURPOSE_MARKETING_EMAIL,
      () => "processed",
      { actor: ACTOR },
    );
    expect(result.ran).toBe(true);
    expect(result.result).toBe("processed");
  });

  test.each(["subj_0042\n", "subj_0042\x00", "subj 0042", "subj_0042\r"])(
    "a subject with a newline/control char is rejected: %j",
    (bad) => {
      const engine = buildDefaultEngine();
      expect(() =>
        engine.captureConsent(bad, PURPOSE_MARKETING_EMAIL, {
          actor: ACTOR,
          version: "v1",
        }),
      ).toThrow(/pseudonymous/);
    },
  );

  test("trailing-newline actor/purpose/version are rejected (parity with Python)", () => {
    const engine = buildDefaultEngine();
    expect(() =>
      engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
        actor: "privacy-service\n",
        version: "v1",
      }),
    ).toThrow(/actor/);
    expect(() =>
      engine.captureConsent(SUBJECT, "marketing_email\n", {
        actor: ACTOR,
        version: "v1",
      }),
    ).toThrow(/purpose/);
    expect(() =>
      engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
        actor: ACTOR,
        version: "v1\n",
      }),
    ).toThrow(/version/);
  });
});

describe("strict actor/version formats + atomic guard (Codex round 3)", () => {
  test("SSN/phone-shaped version and actor are rejected before any audit write", () => {
    const captured: AuditEntry[] = [];
    const engine = buildDefaultEngine({ sink: (e) => captured.push(e) });
    for (const badVersion of ["123-45-6789", "555-0142", "123-456-7890"]) {
      expect(() =>
        engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
          actor: ACTOR,
          version: badVersion,
        }),
      ).toThrow(/version/);
    }
    for (const badActor of ["123-45-6789", "555-0142"]) {
      expect(() =>
        engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
          actor: badActor,
          version: "v1",
        }),
      ).toThrow(/actor/);
    }
    expect(captured).toEqual([]);

    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: "privacy-service",
      version: "2026.07.01",
    });
    expect(engine.auditLog.length).toBe(1);
  });

  test("a re-entrant sink withdrawal blocks execution", () => {
    let engine!: ConsentEngine;
    let withdrawnOnce = false;
    const sink = (entry: AuditEntry): void => {
      if (entry.outcome === "allow" && !withdrawnOnce) {
        withdrawnOnce = true;
        engine.withdrawConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, { actor: ACTOR });
      }
    };
    engine = buildDefaultEngine({ sink });
    engine.captureConsent(SUBJECT, PURPOSE_MARKETING_EMAIL, {
      actor: ACTOR,
      version: "v1",
    });

    let ran = 0;
    const result = engine.guardedProcess(
      SUBJECT,
      PURPOSE_MARKETING_EMAIL,
      () => {
        ran += 1;
        return "processed";
      },
      { actor: ACTOR },
    );
    expect(result.ran).toBe(false); // final re-check caught the re-entrant withdrawal
    expect(result.result).toBeNull();
    expect(result.decision.allowed).toBe(false);
    expect(ran).toBe(0); // the side effect never ran
  });
});
