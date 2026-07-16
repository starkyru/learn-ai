/**
 * Tests for the data-subject rights engine (Module 20b, Task 2).
 *
 * The load-bearing tests prove that export reaches EVERY store (a store holding
 * data but missing from the manifest is a bug), and that erasure honours the
 * retention rules: hard-delete stores leave no trace, while a retention-exception
 * store keeps a tombstone (id + reason CODE, no raw content). Handles from
 * addRecord/recordsFor are metadata-only, so raw content is checked via export.
 *
 * Run: pnpm jest modules/20b-governance-privacy/ts/rights.test.ts
 */

import {
  buildDefaultEngine,
  RAW_MARKER,
  RightsEngine,
  seedSyntheticSubject,
  SEEDED_STORES,
  STORE_CACHE,
  STORE_HUMAN_REVIEW,
  STORE_PRIMARY,
  type ReasonCode,
  type RightsAuditEntry,
  type StorePolicy,
} from "./rights.js";

const SUBJECT = "subj_0007";
const ACTOR = "privacy-service";
const REVIEWER = "legal-team";
const SECRET = "top-secret-value";

const AUDIT_KEYS = [
  "action",
  "actor",
  "reason",
  "result",
  "reviewer",
  "scope",
  "store",
  "subject",
  "time",
];

function exportContentBlob(engine: RightsEngine, subject: string): string {
  return JSON.stringify(
    engine.export(subject, { actor: ACTOR }).copies.map((c) => c.content),
  );
}

describe("export", () => {
  test("lists every store and its location", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);

    const manifest = engine.export(SUBJECT, { actor: ACTOR });

    expect([...manifest.stores()].sort()).toEqual([...SEEDED_STORES].sort());
    const copies = manifest.copies.map((c) => `${c.store}/${c.recordId}`).sort();
    expect(copies).toEqual(
      [
        `${STORE_PRIMARY}/profile_0`,
        `embeddings/chunk_0`,
        `embeddings/chunk_1`,
        `${STORE_CACHE}/resp_0`,
        `feedback/fb_0`,
        `${STORE_HUMAN_REVIEW}/esc_0`,
        `jobs/job_0`,
      ].sort(),
    );
    expect(manifest.locations()[STORE_HUMAN_REVIEW]).toBe("review-queue://escalations");
    // An export deliberately carries content (the requester's own snapshot).
    expect(
      manifest.copies.some(
        (c) =>
          JSON.stringify(c.content) ===
          JSON.stringify({ detail: `${RAW_MARKER}-${SUBJECT}` }),
      ),
    ).toBe(true);
  });

  test("is scoped to the subject", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    seedSyntheticSubject(engine, "subj_9999");

    const manifest = engine.export(SUBJECT, { actor: ACTOR });
    expect(
      manifest.copies.every((c) => JSON.stringify(c.content).includes(`-${SUBJECT}`)),
    ).toBe(true);
  });
});

describe("erasure: hard-delete + tombstone exception", () => {
  test("hard-deletes and tombstones per policy", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);

    const report = engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });
    const byStore = report.byStore();

    const remaining = new Set(engine.recordsFor(SUBJECT).map((r) => r.store));
    expect(remaining.has(STORE_PRIMARY)).toBe(false);
    expect(remaining.has("embeddings")).toBe(false);
    expect(remaining.has(STORE_CACHE)).toBe(false);
    expect(byStore[STORE_PRIMARY].result).toBe("hard_deleted");
    expect(byStore.embeddings.count).toBe(2);

    const tombstones = engine
      .recordsFor(SUBJECT)
      .filter((r) => r.store === STORE_HUMAN_REVIEW);
    expect(tombstones).toHaveLength(1);
    expect(tombstones[0].tombstoned).toBe(true);
    expect(tombstones[0].tombstoneReason).toBe("regulatory_retention"); // a code
    expect(byStore[STORE_HUMAN_REVIEW].result).toBe("tombstoned");
    expect(byStore[STORE_HUMAN_REVIEW].reviewer).toBe(REVIEWER);
    expect(byStore[STORE_HUMAN_REVIEW].reason).toBe("regulatory_retention");
  });

  test("removes all raw content leaving only the tombstone shell", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });

    expect(exportContentBlob(engine, SUBJECT)).not.toContain(RAW_MARKER);
  });

  test("refuses to erase a reviewer-gated store without a reviewer (atomic)", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);

    const before = engine
      .recordsFor(SUBJECT)
      .map((r) => `${r.store}/${r.recordId}`)
      .sort();
    expect(() => engine.erase(SUBJECT, { actor: ACTOR })).toThrow(
      /requires a reviewer/,
    );
    const after = engine
      .recordsFor(SUBJECT)
      .map((r) => `${r.store}/${r.recordId}`)
      .sort();
    expect(after).toEqual(before); // nothing was deleted
  });

  test("a subject with only hard-delete data needs no reviewer", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });
    const report = engine.erase(SUBJECT, { actor: ACTOR });
    expect(report.byStore()[STORE_PRIMARY].result).toBe("hard_deleted");
    expect(engine.recordsFor(SUBJECT)).toEqual([]);
  });
});

describe("retention expiry", () => {
  test("purges past-retention records", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_CACHE, SUBJECT, "old_0", { detail: "x" }, { createdAt: 0 });
    engine.addRecord(
      STORE_CACHE,
      SUBJECT,
      "new_0",
      { detail: "x" },
      { createdAt: 100 },
    );

    const purged = engine.purgeExpired(50, { actor: ACTOR });
    expect(purged).toEqual({ [STORE_CACHE]: 1 });
    expect(engine.recordsFor(SUBJECT).map((r) => r.recordId)).toEqual(["new_0"]);
  });

  test("eventually purges the tombstone", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });

    expect(engine.purgeExpired(100, { actor: ACTOR })).toEqual({});
    expect(engine.recordsFor(SUBJECT).some((r) => r.store === STORE_HUMAN_REVIEW)).toBe(
      true,
    );
    expect(engine.purgeExpired(1_000_000, { actor: ACTOR })).toEqual({
      [STORE_HUMAN_REVIEW]: 1,
    });
    expect(engine.recordsFor(SUBJECT)).toEqual([]);
  });
});

describe("auditability", () => {
  test("audit records have exactly the required fields", () => {
    const captured: RightsAuditEntry[] = [];
    const engine = buildDefaultEngine({ sink: (e) => captured.push(e) });
    seedSyntheticSubject(engine, SUBJECT);

    engine.export(SUBJECT, { actor: ACTOR });
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });

    expect(captured).toEqual(engine.auditRecords());
    for (const record of engine.auditRecords()) {
      expect(Object.keys(record).sort()).toEqual(AUDIT_KEYS);
      expect(record.actor).toBe(ACTOR);
    }

    const records = engine.auditRecords();
    const exportRec = records.find((r) => r.action === "export")!;
    expect(exportRec.result).toBe("exported");
    expect(exportRec.store).toBe("*");
    expect(exportRec.reason).toBe("subject_request");

    const tombstoneRec = records.find((r) => r.action === "tombstone")!;
    expect(tombstoneRec.store).toBe(STORE_HUMAN_REVIEW);
    expect(tombstoneRec.result).toBe("tombstoned");
    expect(tombstoneRec.reviewer).toBe(REVIEWER);
    expect(tombstoneRec.reason).toBe("regulatory_retention");

    const deleteRec = records.find((r) => r.action === "delete")!;
    expect(deleteRec.reviewer).toBeNull();
    expect(deleteRec.reason).toBe("subject_request");
  });

  test("audit records carry no raw content", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    engine.export(SUBJECT, { actor: ACTOR });
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });
    engine.purgeExpired(1_000_000, { actor: ACTOR });

    const blob = JSON.stringify(engine.auditRecords());
    expect(blob).not.toContain(RAW_MARKER);
    expect(blob).not.toContain("@");
  });

  test("audit log getter returns a defensive copy of frozen entries", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    engine.export(SUBJECT, { actor: ACTOR });

    const snapshot = engine.auditLog;
    const before = snapshot.length;
    (snapshot as RightsAuditEntry[]).push({
      actor: "attacker",
      time: 999,
      action: "export",
      subject: "x",
      store: "*",
      scope: "0",
      result: "exported",
      reviewer: null,
      reason: "subject_request",
    });
    expect(engine.auditLog.length).toBe(before);

    const entry = engine.auditLog[0];
    try {
      (entry as { actor: string }).actor = "attacker";
    } catch {
      /* frozen */
    }
    expect(engine.auditLog[0].actor).toBe(ACTOR);
  });
});

describe("validation (reused discipline)", () => {
  test("PII-shaped subject/actor/reviewer are rejected", () => {
    const engine = buildDefaultEngine();
    seedSyntheticSubject(engine, SUBJECT);
    expect(() => engine.export("alice@example.com", { actor: ACTOR })).toThrow(
      /subject/,
    );
    expect(() => engine.export(SUBJECT, { actor: "123-45-6789" })).toThrow(/actor/);
    expect(() =>
      engine.erase(SUBJECT, { actor: ACTOR, reviewer: "Alice Smith" }),
    ).toThrow(/reviewer/);
  });

  test("a custom store can be registered", () => {
    const engine = new RightsEngine();
    engine.registerStore({
      name: "notes",
      location: "notes-db://x",
      mode: "hard_delete",
      retentionTicks: 10,
    });
    engine.addRecord("notes", SUBJECT, "n_1", { detail: "x" });
    expect([...engine.export(SUBJECT, { actor: ACTOR }).stores()]).toEqual(["notes"]);
  });
});

describe("BLOCKER: composite keying", () => {
  test("two subjects with the same record id do not collide", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, "subj_aaa", "shared_0", { detail: "a" });
    engine.addRecord(STORE_PRIMARY, "subj_bbb", "shared_0", { detail: "b" });

    const manifestA = engine.export("subj_aaa", { actor: ACTOR });
    const manifestB = engine.export("subj_bbb", { actor: ACTOR });

    expect([...manifestA.stores()]).toEqual([STORE_PRIMARY]);
    expect(manifestA.copies.map((c) => c.recordId)).toEqual(["shared_0"]);
    expect([...manifestB.stores()]).toEqual([STORE_PRIMARY]);
    expect(manifestB.copies.map((c) => c.recordId)).toEqual(["shared_0"]);
    expect(engine.recordsFor("subj_aaa")).toHaveLength(1);
    expect(engine.recordsFor("subj_bbb")).toHaveLength(1);
    // Contents distinct (no overwrite) — via export, which returns content.
    expect(manifestA.copies[0].content).toEqual({ detail: "a" });
    expect(manifestB.copies[0].content).toEqual({ detail: "b" });
  });
});

describe("CRITICAL: erase write barrier", () => {
  test("a sink that adds on every audit is rejected and leaves nothing", () => {
    let engine!: RightsEngine;
    const captured: RightsAuditEntry[] = [];
    const rejected = { n: 0 };
    const sink = (entry: RightsAuditEntry): void => {
      captured.push(entry);
      if (entry.action === "delete" || entry.action === "tombstone") {
        try {
          engine.addRecord(STORE_PRIMARY, SUBJECT, `sneak_${entry.time.toString(16)}`, {
            detail: SECRET,
          });
        } catch {
          rejected.n += 1;
        }
      }
    };
    engine = buildDefaultEngine({ sink });
    seedSyntheticSubject(engine, SUBJECT);

    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });

    expect(rejected.n).toBeGreaterThanOrEqual(1); // reentrant adds were rejected
    expect(exportContentBlob(engine, SUBJECT)).not.toContain(SECRET);
    expect(exportContentBlob(engine, SUBJECT)).not.toContain(RAW_MARKER);
    expect(captured.some((e) => e.action === "tombstone" && e.reviewer === null)).toBe(
      false,
    );
  });

  test("addRecord is rejected during erasure", () => {
    let engine!: RightsEngine;
    let raised = false;
    const sink = (entry: RightsAuditEntry): void => {
      if (entry.action === "delete") {
        try {
          engine.addRecord(STORE_PRIMARY, SUBJECT, "x_0", { detail: SECRET });
        } catch {
          raised = true;
        }
      }
    };
    engine = buildDefaultEngine({ sink });
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });
    engine.erase(SUBJECT, { actor: ACTOR });
    expect(raised).toBe(true);
  });
});

describe("metadata-only handles + engine-owned policy", () => {
  test("addRecord and recordsFor are metadata-only; export returns content", () => {
    const engine = buildDefaultEngine();
    const handle = engine.addRecord(STORE_PRIMARY, SUBJECT, "r_1", { detail: SECRET });
    expect(Object.hasOwn(handle, "content")).toBe(false); // no raw content
    expect(handle.recordId).toBe("r_1");
    expect(handle.mode).toBe("hard_delete");

    const meta = engine.recordsFor(SUBJECT)[0];
    expect(Object.hasOwn(meta, "content")).toBe(false);

    const manifest = engine.export(SUBJECT, { actor: ACTOR });
    expect(manifest.copies[0].content).toEqual({ detail: SECRET });

    engine.erase(SUBJECT, { actor: ACTOR });
    expect(Object.hasOwn(handle, "content")).toBe(false); // still nothing
    expect(engine.recordsFor(SUBJECT)).toEqual([]);
  });

  test("exported content is deep-frozen (a returned copy can't mutate the store)", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, SUBJECT, "r_1", { detail: { nested: "x" } });
    const copy = engine.export(SUBJECT, { actor: ACTOR }).copies[0];
    expect(Object.isFrozen(copy.content)).toBe(true);
    expect(Object.isFrozen(copy.content.detail)).toBe(true);
    try {
      (copy.content as { detail: unknown }).detail = "hacked";
    } catch {
      /* frozen */
    }
    expect(engine.export(SUBJECT, { actor: ACTOR }).copies[0].content).toEqual({
      detail: { nested: "x" },
    });
  });

  test("register store rejects a duplicate id", () => {
    const engine = buildDefaultEngine();
    expect(() =>
      engine.registerStore({
        name: STORE_PRIMARY,
        location: "x",
        mode: "hard_delete",
        retentionTicks: 1,
      }),
    ).toThrow(/already registered/);
  });

  test("mutating a passed policy after registration cannot flip requiresReviewer", () => {
    const engine = new RightsEngine();
    const policy: StorePolicy = {
      name: "escalations",
      location: "review://x",
      mode: "tombstone",
      retentionTicks: 100,
      reason: "legal_hold",
      requiresReviewer: true,
    };
    engine.registerStore(policy);
    // Tamper with the caller's object AFTER registration.
    policy.requiresReviewer = false;
    policy.mode = "hard_delete";
    engine.addRecord("escalations", SUBJECT, "e_1", { detail: SECRET });
    // The engine holds an owned frozen copy, so the reviewer gate still applies.
    expect(() => engine.erase(SUBJECT, { actor: ACTOR })).toThrow(
      /requires a reviewer/,
    );
  });

  test("a PII-shaped store name is rejected at registration", () => {
    const engine = new RightsEngine();
    expect(() =>
      engine.registerStore({
        name: "alice@example.com",
        location: "loc",
        mode: "hard_delete",
        retentionTicks: 10,
      }),
    ).toThrow(/store name/);
  });

  test("reason must be an allowlisted code (free text rejected)", () => {
    const engine = new RightsEngine();
    expect(() =>
      engine.registerStore({
        name: "legalhold",
        location: "loc",
        mode: "tombstone",
        retentionTicks: 10,
        reason: "call (212) 555-1234" as ReasonCode,
        requiresReviewer: true,
      }),
    ).toThrow(/ReasonCode/);

    engine.registerStore({
      name: "legalhold",
      location: "loc",
      mode: "tombstone",
      retentionTicks: 10,
      reason: "legal_hold",
      requiresReviewer: true,
    });
    engine.addRecord("legalhold", SUBJECT, "x_0", { detail: "y" });
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });
    expect(engine.auditRecords().map((r) => r.reason)).toContain("legal_hold");
  });
});

describe("an identifier itself can be PII", () => {
  test("a PII record id is rejected; a tombstone keeps only the opaque id", () => {
    const engine = buildDefaultEngine();
    expect(() =>
      engine.addRecord(STORE_HUMAN_REVIEW, SUBJECT, "Alice Smith SSN 123-45-6789", {
        detail: "x",
      }),
    ).toThrow(/recordId/);

    engine.addRecord(STORE_HUMAN_REVIEW, SUBJECT, "esc_0", { detail: SECRET });
    engine.erase(SUBJECT, { actor: ACTOR, reviewer: REVIEWER });
    const tombs = engine.recordsFor(SUBJECT);
    expect(tombs).toHaveLength(1);
    expect(tombs[0].recordId).toBe("esc_0"); // opaque token — no PII survives
    const blob = JSON.stringify(engine.auditRecords());
    expect(blob).not.toContain("Alice");
    expect(blob).not.toContain("123-45-6789");
  });

  test("a subject with a name-in-the-suffix is rejected", () => {
    const engine = buildDefaultEngine();
    expect(() => engine.export("subj_Alice_Smith", { actor: ACTOR })).toThrow(
      /subject/,
    );
    expect(() =>
      engine.addRecord(STORE_PRIMARY, "subj_Alice_Smith", "r_0", { detail: "x" }),
    ).toThrow(/subject/);
    // A hex opaque token is accepted.
    engine.addRecord(STORE_PRIMARY, "subj_dead", "r_0", { detail: "x" });
    expect([...engine.export("subj_dead", { actor: ACTOR }).stores()]).toEqual([
      STORE_PRIMARY,
    ]);
  });
});

describe("durable erased marker (a write that races the erase)", () => {
  test("a microtask add scheduled during erase is rejected", async () => {
    // A sink that queueMicrotasks an addRecord: it runs AFTER the synchronous
    // erase clears the transient flag. The DURABLE marker must still reject it.
    let engine!: RightsEngine;
    const result: { rejected?: boolean; added?: boolean } = {};
    let scheduled = false;
    const sink = (entry: RightsAuditEntry): void => {
      if (entry.action === "delete" && !scheduled) {
        scheduled = true;
        queueMicrotask(() => {
          try {
            engine.addRecord(STORE_PRIMARY, SUBJECT, "sneak_0", { detail: SECRET });
            result.added = true;
          } catch {
            result.rejected = true;
          }
        });
      }
    };
    engine = buildDefaultEngine({ sink });
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });

    engine.erase(SUBJECT, { actor: ACTOR });
    // Let the deferred microtask run.
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(result.rejected).toBe(true);
    expect(result.added).not.toBe(true);
    expect(engine.recordsFor(SUBJECT).filter((r) => !r.tombstoned)).toEqual([]);
  });

  test("an add after erase is rejected until reactivation", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });
    engine.erase(SUBJECT, { actor: ACTOR });

    // Erasure is final: a later add for the erased subject is rejected...
    expect(() =>
      engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" }),
    ).toThrow(/is erased/);

    // ...until an explicit reactivation (a deliberate new lawful basis + actor).
    engine.reactivateSubject(SUBJECT, { lawfulBasis: "contract", actor: ACTOR });
    engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" });
    expect(engine.recordsFor(SUBJECT)).toHaveLength(1);
  });

  test("a sink failure during erase does not reopen collection", () => {
    // If the audit sink THROWS during the erase flush, the erase's data removal
    // AND the durable erased marker must still be terminal — a later add is still
    // rejected and the failed delivery is retryable, not fatal.
    const sink = (entry: RightsAuditEntry): void => {
      if (entry.action === "delete" || entry.action === "tombstone") {
        throw new Error("audit vendor outage");
      }
    };
    const engine = buildDefaultEngine({ sink });
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: SECRET });

    engine.erase(SUBJECT, { actor: ACTOR }); // sink throws on the delete entry — not fatal

    expect(engine.recordsFor(SUBJECT)).toEqual([]);
    expect(engine.auditRecords().some((r) => r.action === "delete")).toBe(true);
    expect(engine.pendingAuditDeliveries).toBeGreaterThanOrEqual(1);

    // The erased marker survived the sink failure: a later add is REJECTED.
    expect(() =>
      engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" }),
    ).toThrow(/is erased/);
  });

  test("a reentrant sink cannot reactivate during erase", async () => {
    // A re-entrant audit sink that calls reactivate DURING the erase flush must be
    // REJECTED — the terminal erased marker cannot be cleared mid-transaction, so
    // the subject stays erased and even a deferred microtask add is refused.
    let engine!: RightsEngine;
    const seen: { tried?: boolean; rejected?: boolean; added?: boolean } = {};
    const sink = (entry: RightsAuditEntry): void => {
      if (entry.action === "delete" && !seen.tried) {
        seen.tried = true;
        try {
          engine.reactivateSubject(SUBJECT, {
            lawfulBasis: "contract",
            actor: ACTOR,
          });
        } catch {
          seen.rejected = true;
        }
        queueMicrotask(() => {
          try {
            engine.addRecord(STORE_PRIMARY, SUBJECT, "sneak_0", {
              detail: SECRET,
            });
            seen.added = true;
          } catch {
            /* still rejected — expected */
          }
        });
      }
    };
    engine = buildDefaultEngine({ sink });
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: SECRET });

    engine.erase(SUBJECT, { actor: ACTOR });
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(seen.rejected).toBe(true); // the reentrant reactivate was rejected
    expect(seen.added).not.toBe(true); // the deferred add stayed rejected
    expect(engine.auditRecords().some((r) => r.action === "reactivate")).toBe(false);
    expect(engine.recordsFor(SUBJECT)).toEqual([]);
  });

  test("a legitimate reactivation is audited then admits data", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });
    engine.erase(SUBJECT, { actor: ACTOR });
    expect(() =>
      engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" }),
    ).toThrow(/is erased/);

    engine.reactivateSubject(SUBJECT, { lawfulBasis: "contract", actor: ACTOR });

    const reactivations = engine
      .auditRecords()
      .filter((r) => r.action === "reactivate");
    expect(reactivations).toHaveLength(1);
    expect(reactivations[0].subject).toBe(SUBJECT);
    expect(reactivations[0].actor).toBe(ACTOR);
    expect(reactivations[0].reason).toBe("contract");
    expect(reactivations[0].result).toBe("reactivated");

    engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" });
    expect(engine.recordsFor(SUBJECT)).toHaveLength(1);
  });

  test("reactivation requires a lawful basis and a valid actor", () => {
    const engine = buildDefaultEngine();
    engine.addRecord(STORE_PRIMARY, SUBJECT, "p_0", { detail: "x" });
    engine.erase(SUBJECT, { actor: ACTOR });

    // An invalid lawful basis is rejected...
    expect(() =>
      engine.reactivateSubject(SUBJECT, {
        lawfulBasis: "whatever" as never,
        actor: ACTOR,
      }),
    ).toThrow(/lawful_basis/);
    // ...and a PII-shaped actor is rejected.
    expect(() =>
      engine.reactivateSubject(SUBJECT, {
        lawfulBasis: "contract",
        actor: "123-45-6789",
      }),
    ).toThrow(/actor/);

    // Neither rejected attempt cleared the marker or wrote an audit entry.
    expect(engine.auditRecords().some((r) => r.action === "reactivate")).toBe(false);
    expect(() =>
      engine.addRecord(STORE_PRIMARY, SUBJECT, "q_0", { detail: "y" }),
    ).toThrow(/is erased/);
  });
});
