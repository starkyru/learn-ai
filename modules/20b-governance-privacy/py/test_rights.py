"""Tests for the data-subject rights engine (Module 20b, Task 2).

The load-bearing tests prove that export reaches EVERY store (a store holding
data but missing from the manifest is a bug), and that erasure honours the
retention rules: hard-delete stores leave no trace, while a retention-exception
store keeps a tombstone (id + reason code, no raw content). Tests drive the real
engine; the only injected boundary is the audit sink (a list). Handles from
``add_record`` / ``records_for`` are metadata-only, so raw content is checked via
``export`` (which deliberately returns content).

Run:
    uv run pytest modules/20b-governance-privacy/py/test_rights.py
"""

from __future__ import annotations

import json
import threading
from dataclasses import FrozenInstanceError

import pytest
from rights import (
    RAW_MARKER,
    SEEDED_STORES,
    STORE_CACHE,
    STORE_HUMAN_REVIEW,
    STORE_PRIMARY,
    ReasonCode,
    RetentionMode,
    RightsAuditEntry,
    RightsEngine,
    StorePolicy,
    build_default_engine,
    seed_synthetic_subject,
)

SUBJECT = "subj_0007"
ACTOR = "privacy-service"
REVIEWER = "legal-team"
SECRET = "top-secret-value"

AUDIT_KEYS = {
    "actor",
    "time",
    "action",
    "subject",
    "store",
    "scope",
    "result",
    "reviewer",
    "reason",
}


def _export_content_blob(engine: RightsEngine, subject: str) -> str:
    manifest = engine.export(subject, actor=ACTOR)
    return json.dumps([dict(c.content) for c in manifest.copies])


# --- export ---------------------------------------------------------------


def test_export_lists_every_store_and_location() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)

    manifest = engine.export(SUBJECT, actor=ACTOR)

    assert manifest.stores() == set(SEEDED_STORES)
    assert {(c.store, c.record_id) for c in manifest.copies} == {
        (STORE_PRIMARY, "profile_0"),
        ("embeddings", "chunk_0"),
        ("embeddings", "chunk_1"),
        (STORE_CACHE, "resp_0"),
        ("feedback", "fb_0"),
        (STORE_HUMAN_REVIEW, "esc_0"),
        ("jobs", "job_0"),
    }
    assert manifest.locations()[STORE_HUMAN_REVIEW] == "review-queue://escalations"
    # An export deliberately carries content (the requester's own snapshot).
    assert any(dict(c.content) == {"detail": f"{RAW_MARKER}-{SUBJECT}"} for c in manifest.copies)


def test_export_scoped_to_the_subject() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)
    seed_synthetic_subject(engine, "subj_9999")

    manifest = engine.export(SUBJECT, actor=ACTOR)
    assert all(f"-{SUBJECT}" in json.dumps(dict(c.content)) for c in manifest.copies)


# --- erasure: hard-delete + tombstone exception ---------------------------


def test_erase_hard_deletes_and_tombstones_per_policy() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)

    report = engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)
    by_store = report.by_store()

    remaining_stores = {r.store for r in engine.records_for(SUBJECT)}
    assert STORE_PRIMARY not in remaining_stores
    assert "embeddings" not in remaining_stores
    assert STORE_CACHE not in remaining_stores
    assert by_store[STORE_PRIMARY].result == "hard_deleted"
    assert by_store["embeddings"].count == 2

    # Retention-exception store: a tombstone is kept (id + reason CODE).
    tombstones = [r for r in engine.records_for(SUBJECT) if r.store == STORE_HUMAN_REVIEW]
    assert len(tombstones) == 1
    tomb = tombstones[0]
    assert tomb.tombstoned is True
    assert tomb.tombstone_reason == "regulatory_retention"  # an allowlisted code
    assert by_store[STORE_HUMAN_REVIEW].result == "tombstoned"
    assert by_store[STORE_HUMAN_REVIEW].reviewer == REVIEWER
    assert by_store[STORE_HUMAN_REVIEW].reason == "regulatory_retention"


def test_erase_removes_all_raw_content_leaving_only_the_tombstone_shell() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)

    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)

    # export (which returns content) shows no raw marker survives anywhere.
    assert RAW_MARKER not in _export_content_blob(engine, SUBJECT)


def test_erase_without_reviewer_is_refused_and_atomic() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)

    before = {(r.store, r.record_id) for r in engine.records_for(SUBJECT)}
    with pytest.raises(ValueError, match="requires a reviewer"):
        engine.erase(SUBJECT, actor=ACTOR)  # no reviewer for the legal-hold store
    after = {(r.store, r.record_id) for r in engine.records_for(SUBJECT)}
    assert after == before  # nothing was deleted


def test_erase_without_review_store_needs_no_reviewer() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})
    report = engine.erase(SUBJECT, actor=ACTOR)
    assert report.by_store()[STORE_PRIMARY].result == "hard_deleted"
    assert engine.records_for(SUBJECT) == ()


# --- retention expiry -----------------------------------------------------


def test_retention_expiry_purges_past_retention_records() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_CACHE, SUBJECT, "old_0", {"detail": "x"}, created_at=0)
    engine.add_record(STORE_CACHE, SUBJECT, "new_0", {"detail": "x"}, created_at=100)

    purged = engine.purge_expired(now=50, actor=ACTOR)
    assert purged == {STORE_CACHE: 1}

    remaining = {r.record_id for r in engine.records_for(SUBJECT)}
    assert remaining == {"new_0"}


def test_retention_expiry_eventually_purges_the_tombstone() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)
    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)

    assert engine.purge_expired(now=100, actor=ACTOR) == {}
    assert any(r.store == STORE_HUMAN_REVIEW for r in engine.records_for(SUBJECT))
    assert engine.purge_expired(now=1_000_000, actor=ACTOR) == {STORE_HUMAN_REVIEW: 1}
    assert engine.records_for(SUBJECT) == ()


# --- auditability ---------------------------------------------------------


def test_audit_records_have_exactly_the_required_fields() -> None:
    captured: list[RightsAuditEntry] = []
    engine = build_default_engine(sink=captured.append)
    seed_synthetic_subject(engine, SUBJECT)

    engine.export(SUBJECT, actor=ACTOR)
    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)

    assert [e.to_record() for e in captured] == engine.audit_records()
    for record in engine.audit_records():
        assert set(record.keys()) == AUDIT_KEYS
        assert record["actor"] == ACTOR

    records = engine.audit_records()
    export_rec = next(r for r in records if r["action"] == "export")
    assert export_rec["result"] == "exported"
    assert export_rec["store"] == "*"
    assert export_rec["reason"] == "subject_request"

    tombstone_rec = next(r for r in records if r["action"] == "tombstone")
    assert tombstone_rec["store"] == STORE_HUMAN_REVIEW
    assert tombstone_rec["result"] == "tombstoned"
    assert tombstone_rec["reviewer"] == REVIEWER
    assert tombstone_rec["reason"] == "regulatory_retention"

    delete_rec = next(r for r in records if r["action"] == "delete")
    assert delete_rec["reviewer"] is None
    assert delete_rec["reason"] == "subject_request"


def test_audit_records_carry_no_raw_content() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)
    engine.export(SUBJECT, actor=ACTOR)
    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)
    engine.purge_expired(now=1_000_000, actor=ACTOR)

    blob = json.dumps(engine.audit_records())
    assert RAW_MARKER not in blob
    assert "@" not in blob  # no email-shaped PII


def test_audit_log_is_an_immutable_snapshot() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)
    engine.export(SUBJECT, actor=ACTOR)

    log = engine.audit_log
    assert isinstance(log, tuple)
    assert engine.audit_log is not engine.audit_log
    with pytest.raises(FrozenInstanceError):
        log[0].actor = "attacker"  # type: ignore[misc]
    assert engine.audit_log[0].actor == ACTOR


# --- validation (reused discipline) ---------------------------------------


def test_pii_shaped_subject_and_actor_rejected() -> None:
    engine = build_default_engine()
    seed_synthetic_subject(engine, SUBJECT)
    with pytest.raises(ValueError, match="subject"):
        engine.export("alice@example.com", actor=ACTOR)
    with pytest.raises(ValueError, match="actor"):
        engine.export(SUBJECT, actor="123-45-6789")
    with pytest.raises(ValueError, match="reviewer"):
        engine.erase(SUBJECT, actor=ACTOR, reviewer="Alice Smith")


def test_custom_policy_can_be_registered() -> None:
    engine = RightsEngine()
    engine.register_store(StorePolicy("notes", "notes-db://x", RetentionMode.HARD_DELETE, 10))
    engine.add_record("notes", SUBJECT, "n_1", {"detail": "x"})
    assert engine.export(SUBJECT, actor=ACTOR).stores() == {"notes"}


# --- BLOCKER: composite keying ---------------------------------------------


def test_two_subjects_same_record_id_do_not_collide() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, "subj_aaa", "shared_0", {"detail": "a"})
    engine.add_record(STORE_PRIMARY, "subj_bbb", "shared_0", {"detail": "b"})

    manifest_a = engine.export("subj_aaa", actor=ACTOR)
    manifest_b = engine.export("subj_bbb", actor=ACTOR)

    assert manifest_a.stores() == {STORE_PRIMARY}
    assert {c.record_id for c in manifest_a.copies} == {"shared_0"}
    assert manifest_b.stores() == {STORE_PRIMARY}
    assert {c.record_id for c in manifest_b.copies} == {"shared_0"}
    assert len(engine.records_for("subj_aaa")) == 1
    assert len(engine.records_for("subj_bbb")) == 1
    # Contents are distinct (no overwrite) — via export, which returns content.
    assert dict(manifest_a.copies[0].content) == {"detail": "a"}
    assert dict(manifest_b.copies[0].content) == {"detail": "b"}


# --- CRITICAL: erase write barrier -----------------------------------------


def test_write_barrier_rejects_reentrant_adds_and_leaves_nothing() -> None:
    # A sink that tries to sneak a raw record back in on EVERY delete/tombstone
    # audit (including the flush) must be REJECTED, so nothing raw survives and
    # nothing is tombstoned without a reviewer.
    holder: dict[str, RightsEngine] = {}
    rejected = {"count": 0}
    captured: list[RightsAuditEntry] = []

    def sink(entry: RightsAuditEntry) -> None:
        captured.append(entry)
        if entry.action in ("delete", "tombstone"):
            try:
                holder["engine"].add_record(
                    STORE_PRIMARY, SUBJECT, f"sneak_{entry.time:x}", {"detail": SECRET}
                )
            except RuntimeError:
                rejected["count"] += 1

    engine = build_default_engine(sink=sink)
    holder["engine"] = engine
    seed_synthetic_subject(engine, SUBJECT)

    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)

    assert rejected["count"] >= 1  # the reentrant adds were rejected by the barrier
    blob = _export_content_blob(engine, SUBJECT)
    assert SECRET not in blob
    assert RAW_MARKER not in blob
    assert not any(e.action == "tombstone" and e.reviewer is None for e in captured)


def test_add_record_is_rejected_during_erasure() -> None:
    # Directly: a same-thread reentrant add for the erasing subject raises.
    holder: dict[str, RightsEngine] = {}
    outcome = {"raised": False}

    def sink(entry: RightsAuditEntry) -> None:
        if entry.action == "delete":
            try:
                holder["engine"].add_record(STORE_PRIMARY, SUBJECT, "x_0", {"detail": SECRET})
            except RuntimeError:
                outcome["raised"] = True

    engine = build_default_engine(sink=sink)
    holder["engine"] = engine
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})
    engine.erase(SUBJECT, actor=ACTOR)
    assert outcome["raised"] is True


# --- high: metadata-only handles -------------------------------------------


def test_add_record_and_records_for_are_metadata_only() -> None:
    engine = build_default_engine()
    handle = engine.add_record(STORE_PRIMARY, SUBJECT, "r_1", {"detail": SECRET})
    # No raw content on the returned handle — metadata only.
    assert not hasattr(handle, "content")
    assert handle.record_id == "r_1"
    assert handle.store == STORE_PRIMARY
    assert handle.mode is RetentionMode.HARD_DELETE

    meta = engine.records_for(SUBJECT)[0]
    assert not hasattr(meta, "content")

    # export DOES return content (the requester's point-in-time snapshot).
    manifest = engine.export(SUBJECT, actor=ACTOR)
    assert dict(manifest.copies[0].content) == {"detail": SECRET}

    # A retained handle still exposes no content after erase scrubs the store.
    engine.erase(SUBJECT, actor=ACTOR)
    assert not hasattr(handle, "content")
    assert engine.records_for(SUBJECT) == ()


def test_exported_content_is_deeply_immutable() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, SUBJECT, "r_1", {"detail": {"nested": "x"}})
    copy = engine.export(SUBJECT, actor=ACTOR).copies[0]
    with pytest.raises(TypeError):
        copy.content["detail"] = "hacked"  # type: ignore[index]
    with pytest.raises(TypeError):
        copy.content["detail"]["nested"] = "hacked"  # type: ignore[index]  # nested too


# --- high: reason codes ----------------------------------------------------


def test_reason_must_be_an_allowlisted_code() -> None:
    engine = RightsEngine()
    # Free-text / phone-shaped reason -> rejected (only ReasonCode allowed).
    with pytest.raises(ValueError, match="ReasonCode"):
        engine.register_store(
            StorePolicy(
                "legalhold",
                "loc",
                RetentionMode.TOMBSTONE,
                10,
                reason="call (212) 555-1234",  # type: ignore[arg-type]
                requires_reviewer=True,
            )
        )
    # A valid code is accepted and appears in the audit trail.
    engine.register_store(
        StorePolicy(
            "legalhold",
            "loc",
            RetentionMode.TOMBSTONE,
            10,
            reason=ReasonCode.LEGAL_HOLD,
            requires_reviewer=True,
        )
    )
    engine.add_record("legalhold", SUBJECT, "x_0", {"detail": "y"})
    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)
    assert "legal_hold" in {r["reason"] for r in engine.audit_records()}


# --- high: engine-owned policy (setattr tamper) ----------------------------


def test_register_store_rejects_duplicate() -> None:
    engine = build_default_engine()
    with pytest.raises(ValueError, match="already registered"):
        engine.register_store(StorePolicy(STORE_PRIMARY, "x", RetentionMode.HARD_DELETE, 1))


def test_store_policy_is_immutable() -> None:
    policy = StorePolicy(STORE_PRIMARY, "loc", RetentionMode.TOMBSTONE, 10, requires_reviewer=True)
    with pytest.raises(FrozenInstanceError):
        policy.requires_reviewer = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        policy.mode = RetentionMode.HARD_DELETE  # type: ignore[misc]


def test_setattr_policy_tamper_after_registration_is_blocked() -> None:
    engine = RightsEngine()
    caller_policy = StorePolicy(
        "escalations",
        "review://x",
        RetentionMode.TOMBSTONE,
        100,
        reason=ReasonCode.LEGAL_HOLD,
        requires_reviewer=True,
    )
    engine.register_store(caller_policy)
    # Bypass the frozen dataclass on the RETAINED instance.
    object.__setattr__(caller_policy, "requires_reviewer", False)
    engine.add_record("escalations", SUBJECT, "e_1", {"detail": "x"})
    # The engine holds its OWN copy, so the reviewer gate still applies.
    with pytest.raises(ValueError, match="requires a reviewer"):
        engine.erase(SUBJECT, actor=ACTOR)


def test_pii_shaped_store_name_rejected() -> None:
    engine = RightsEngine()
    with pytest.raises(ValueError, match="store name"):
        engine.register_store(
            StorePolicy("alice@example.com", "loc", RetentionMode.HARD_DELETE, 10)
        )


# --- an identifier itself can be PII ---------------------------------------


def test_pii_record_id_rejected_and_tombstone_keeps_opaque_id() -> None:
    engine = build_default_engine()
    # A caller-supplied record_id that is itself PII is rejected outright.
    with pytest.raises(ValueError, match="record_id"):
        engine.add_record(
            STORE_HUMAN_REVIEW, SUBJECT, "Alice Smith SSN 123-45-6789", {"detail": "x"}
        )
    # A valid opaque id is accepted; after a reviewer-approved tombstone erase the
    # RETAINED id is opaque-only, and no PII reaches the audit trail.
    engine.add_record(STORE_HUMAN_REVIEW, SUBJECT, "esc_0", {"detail": SECRET})
    engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)
    tombs = engine.records_for(SUBJECT)
    assert len(tombs) == 1
    assert tombs[0].record_id == "esc_0"  # opaque token — no PII survives
    blob = json.dumps(engine.audit_records())
    assert "Alice" not in blob
    assert "123-45-6789" not in blob


def test_pii_suffix_subject_is_rejected() -> None:
    engine = build_default_engine()
    # A prefix-only rule would admit this name-in-the-suffix identifier.
    with pytest.raises(ValueError, match="subject"):
        engine.export("subj_Alice_Smith", actor=ACTOR)
    with pytest.raises(ValueError, match="subject"):
        engine.add_record(STORE_PRIMARY, "subj_Alice_Smith", "r_0", {"detail": "x"})
    # A hex opaque token is accepted.
    engine.add_record(STORE_PRIMARY, "subj_dead", "r_0", {"detail": "x"})
    assert engine.export("subj_dead", actor=ACTOR).stores() == {STORE_PRIMARY}


# --- durable erased marker (a write that races the erase) ------------------


def test_queued_writer_after_erase_is_rejected() -> None:
    # A background thread that calls add_record DURING erase blocks on the lock,
    # then acquires it AFTER the in-progress flag drops. The DURABLE erased
    # marker must still reject it, so no raw record survives a "successful" erase.
    holder: dict[str, RightsEngine] = {}
    started = threading.Event()
    result: dict[str, bool] = {}

    def worker() -> None:
        started.set()
        try:
            holder["engine"].add_record(STORE_PRIMARY, SUBJECT, "sneak_0", {"detail": SECRET})
            result["added"] = True
        except RuntimeError:
            result["rejected"] = True

    thread = threading.Thread(target=worker)

    def sink(entry: RightsAuditEntry) -> None:
        if entry.action == "delete" and not thread.is_alive() and "started" not in result:
            result["started"] = True
            thread.start()
            started.wait(timeout=2)  # the worker is running and about to block on the lock

    engine = build_default_engine(sink=sink)
    holder["engine"] = engine
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})

    engine.erase(SUBJECT, actor=ACTOR)
    thread.join(timeout=2)

    assert result.get("rejected") is True  # the queued add was rejected post-erase
    assert result.get("added") is not True
    assert [r for r in engine.records_for(SUBJECT) if not r.tombstoned] == []


def test_add_after_erase_is_rejected_until_reactivation() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})
    engine.erase(SUBJECT, actor=ACTOR)

    # Erasure is final: a later add for the erased subject is rejected...
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})

    # ...until an explicit reactivation (a deliberate new lawful basis + actor).
    engine.reactivate_subject(SUBJECT, lawful_basis="contract", actor=ACTOR)
    engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})
    assert len(engine.records_for(SUBJECT)) == 1


def test_sink_failure_during_erase_does_not_reopen_collection() -> None:
    # If the external audit sink RAISES during the erase flush, the erase's data
    # removal AND the durable erased marker must still be terminal — a later add
    # is still rejected and the failed delivery is retryable, not fatal.
    delivered: list[RightsAuditEntry] = []

    def sink(entry: RightsAuditEntry) -> None:
        if entry.action in ("delete", "tombstone"):
            raise RuntimeError("audit vendor outage")
        delivered.append(entry)

    engine = build_default_engine(sink=sink)
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": SECRET})

    engine.erase(SUBJECT, actor=ACTOR)  # sink raises on the delete entry — not fatal

    # Data is gone, and the audit is still durably recorded despite delivery failing.
    assert engine.records_for(SUBJECT) == ()
    assert any(r["action"] == "delete" for r in engine.audit_records())
    assert engine.pending_audit_deliveries >= 1  # the failed delivery is queued

    # The erased marker survived the sink failure: a later add is REJECTED.
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})

    # The failed delivery can be retried once the sink recovers — without ever
    # changing the erased state.
    engine._sink = delivered.append  # type: ignore[attr-defined]  # "recovered" sink
    assert engine.retry_audit_delivery() == 0
    assert any(e.action == "delete" for e in delivered)
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})


def test_reentrant_sink_cannot_reactivate_during_erase() -> None:
    # A re-entrant audit sink that calls reactivate DURING the erase flush must be
    # REJECTED — the terminal erased marker cannot be cleared mid-transaction, so
    # the subject stays erased and no later add re-admits raw data.
    holder: dict[str, RightsEngine] = {}
    seen: dict[str, bool] = {}

    def sink(entry: RightsAuditEntry) -> None:
        if entry.action == "delete" and not seen.get("tried"):
            seen["tried"] = True
            try:
                holder["engine"].reactivate_subject(SUBJECT, lawful_basis="contract", actor=ACTOR)
            except RuntimeError:
                seen["rejected"] = True

    engine = build_default_engine(sink=sink)
    holder["engine"] = engine
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": SECRET})

    engine.erase(SUBJECT, actor=ACTOR)

    assert seen.get("rejected") is True  # the reentrant reactivate was rejected
    # Subject stays erased: no reactivation audit entry, and a later add is refused.
    assert not any(r["action"] == "reactivate" for r in engine.audit_records())
    assert engine.records_for(SUBJECT) == ()
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})


def test_legitimate_reactivation_is_audited_then_admits_data() -> None:
    # A reactivation OUTSIDE any erase, with a valid lawful basis + actor, is
    # allowed — and only after it emits a reactivation audit entry does add work.
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})
    engine.erase(SUBJECT, actor=ACTOR)
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})

    engine.reactivate_subject(SUBJECT, lawful_basis="contract", actor=ACTOR)

    reactivations = [r for r in engine.audit_records() if r["action"] == "reactivate"]
    assert len(reactivations) == 1
    assert reactivations[0]["subject"] == SUBJECT
    assert reactivations[0]["actor"] == ACTOR
    assert reactivations[0]["reason"] == "contract"
    assert reactivations[0]["result"] == "reactivated"

    engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})
    assert len(engine.records_for(SUBJECT)) == 1


def test_reactivation_requires_lawful_basis_and_valid_actor() -> None:
    engine = build_default_engine()
    engine.add_record(STORE_PRIMARY, SUBJECT, "p_0", {"detail": "x"})
    engine.erase(SUBJECT, actor=ACTOR)

    # An invalid/absent lawful basis is rejected...
    with pytest.raises(ValueError, match="lawful_basis"):
        engine.reactivate_subject(SUBJECT, lawful_basis="whatever", actor=ACTOR)
    # ...and a PII-shaped actor is rejected.
    with pytest.raises(ValueError, match="actor"):
        engine.reactivate_subject(SUBJECT, lawful_basis="contract", actor="123-45-6789")

    # Neither rejected attempt cleared the marker or wrote an audit entry.
    assert not any(r["action"] == "reactivate" for r in engine.audit_records())
    with pytest.raises(RuntimeError, match="erased"):
        engine.add_record(STORE_PRIMARY, SUBJECT, "q_0", {"detail": "y"})
