"""Tests for the consent + lawful-basis engine (Module 20b, Task 2).

The load-bearing test proves consent is NOT a universal switch: withdrawing it
denies consent-based processing for a purpose, yet the SAME purpose stays lawful
when a different basis (contract/legal obligation) authorises it. Tests call the
real engine; the only injected boundary is the audit sink (a list).

Run:
    uv run pytest modules/20b-governance-privacy/py/test_consent.py
"""

from __future__ import annotations

import threading
from dataclasses import FrozenInstanceError

import pytest
from consent import (
    DEFAULT_ACTIVITIES,
    PURPOSE_ACCOUNT_SECURITY,
    PURPOSE_FRAUD_DETECTION,
    PURPOSE_MARKETING_EMAIL,
    PURPOSE_ORDER_FULFILMENT,
    PURPOSE_PRODUCT_ANALYTICS,
    AuditEntry,
    ConsentEngine,
    ConsentState,
    LawfulBasis,
    ProcessingActivity,
    build_default_engine,
)

SUBJECT = "subj_0042"
OTHER = "subj_0099"
ACTOR = "privacy-service"

AUDIT_KEYS = {"actor", "time", "subject", "purpose", "basis", "outcome", "reason"}


# --- purpose limitation ---------------------------------------------------


def test_consented_purpose_is_allowed_via_consent() -> None:
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")

    decision = engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL)
    assert decision.allowed is True
    assert decision.basis is LawfulBasis.CONSENT


def test_blanket_consent_is_rejected() -> None:
    # Consent for marketing must NOT authorise a different (analytics) purpose.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")

    decision = engine.can_process(SUBJECT, PURPOSE_PRODUCT_ANALYTICS)
    assert decision.allowed is False
    assert decision.basis is None
    assert "consent" in decision.reason


def test_unregistered_purpose_is_denied() -> None:
    engine = build_default_engine()
    decision = engine.can_process(SUBJECT, "sell_to_third_party")
    assert decision.allowed is False
    assert decision.basis is None
    assert "no lawful basis" in decision.reason


def test_consent_is_scoped_to_the_subject() -> None:
    # One subject's consent does not authorise processing another subject.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    assert engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL).allowed is True
    assert engine.can_process(OTHER, PURPOSE_MARKETING_EMAIL).allowed is False


# --- non-consent bases do not need consent --------------------------------


def test_contract_basis_allows_without_any_consent() -> None:
    engine = build_default_engine()
    decision = engine.can_process(SUBJECT, PURPOSE_ORDER_FULFILMENT)
    assert decision.allowed is True
    assert decision.basis is LawfulBasis.CONTRACT
    assert engine.has_valid_consent(SUBJECT, PURPOSE_ORDER_FULFILMENT) is False


def test_legal_obligation_basis_allows() -> None:
    engine = build_default_engine()
    decision = engine.can_process(SUBJECT, PURPOSE_FRAUD_DETECTION)
    assert decision.allowed is True
    assert decision.basis is LawfulBasis.LEGAL_OBLIGATION


# --- THE load-bearing case: withdrawal != revoking every basis ------------


def test_withdrawal_denies_consent_only_purpose() -> None:
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    assert engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL).allowed is True

    engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)

    after = engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL)
    assert after.allowed is False  # consent-only purpose is now denied
    assert after.basis is None
    assert engine.has_valid_consent(SUBJECT, PURPOSE_MARKETING_EMAIL) is False


def test_withdrawal_does_not_revoke_contract_basis() -> None:
    # account_security is authorised under BOTH consent and contract.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, actor=ACTOR, version="v1")

    before = engine.can_process(SUBJECT, PURPOSE_ACCOUNT_SECURITY)
    assert before.allowed is True
    assert before.basis is LawfulBasis.CONSENT  # consent tried first

    engine.withdraw_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, actor=ACTOR)

    # Consent-based authorisation is gone...
    assert engine.has_valid_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY) is False
    # ...but the SAME purpose is STILL allowed — now under contract.
    after = engine.can_process(SUBJECT, PURPOSE_ACCOUNT_SECURITY)
    assert after.allowed is True
    assert after.basis is LawfulBasis.CONTRACT


# --- consent lifecycle details --------------------------------------------


def test_capture_then_withdraw_updates_state() -> None:
    engine = build_default_engine()
    granted = engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v2")
    assert granted.state is ConsentState.GRANTED
    assert granted.basis is LawfulBasis.CONSENT
    assert granted.version == "v2"

    withdrawn = engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)
    assert withdrawn.state is ConsentState.WITHDRAWN
    assert withdrawn.version == "v2"  # carries the withdrawn version forward


def test_deterministic_clock_orders_records() -> None:
    ticks = iter([10, 11, 12])
    engine = build_default_engine(clock=lambda: next(ticks))
    captured = engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    decision_entry_time = engine.audit_log[-1].time  # capture entry at tick 10
    assert captured.time == 10
    assert decision_entry_time == 10
    engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL)  # consumes tick 11
    assert engine.audit_log[-1].time == 11


# --- auditability ----------------------------------------------------------


def test_audit_record_has_exactly_the_required_fields() -> None:
    captured: list[AuditEntry] = []
    engine = build_default_engine(sink=captured.append)
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)
    engine.can_process(SUBJECT, PURPOSE_PRODUCT_ANALYTICS, actor=ACTOR)  # a deny

    # The sink saw every entry, in order, identical to the stored log.
    assert [e.to_record() for e in captured] == engine.audit_records()

    for record in engine.audit_records():
        assert set(record.keys()) == AUDIT_KEYS  # exactly — no extra/raw fields
        assert record["subject"] == SUBJECT  # pseudonymous id only
        assert record["actor"] == ACTOR

    capture_rec, allow_rec, deny_rec = engine.audit_records()
    assert capture_rec["outcome"] == "granted"
    assert capture_rec["basis"] == "consent"
    assert allow_rec["outcome"] == "allow"
    assert allow_rec["basis"] == "consent"
    assert deny_rec["outcome"] == "deny"
    assert deny_rec["basis"] is None


def test_audit_records_carry_no_raw_identifier() -> None:
    # Subjects are identified by a pseudonymous id, so no raw email/SSN appears.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL)
    for record in engine.audit_records():
        for value in record.values():
            assert "@" not in str(value)  # no email
            assert "123-45-6789" not in str(value)  # no SSN-like value


def test_bases_for_reflects_registration() -> None:
    engine = ConsentEngine()
    engine.register_activity(ProcessingActivity(PURPOSE_ORDER_FULFILMENT, LawfulBasis.CONTRACT))
    engine.register_activity(ProcessingActivity(PURPOSE_ORDER_FULFILMENT, LawfulBasis.CONTRACT))
    # De-duplicated.
    assert engine.bases_for(PURPOSE_ORDER_FULFILMENT) == (LawfulBasis.CONTRACT,)
    assert engine.bases_for("unknown") == ()


def test_default_catalogue_covers_the_dual_basis_purpose() -> None:
    # Guards the fixture the load-bearing test relies on.
    purposes = {a.purpose for a in DEFAULT_ACTIVITIES}
    assert PURPOSE_ACCOUNT_SECURITY in purposes
    engine = build_default_engine()
    assert engine.bases_for(PURPOSE_ACCOUNT_SECURITY) == (
        LawfulBasis.CONSENT,
        LawfulBasis.CONTRACT,
    )


def test_audit_log_is_an_immutable_snapshot() -> None:
    # The audit trail is append-only: a caller cannot tamper with what the
    # getter returns and change a later read.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")

    log = engine.audit_log
    assert isinstance(log, tuple)  # a snapshot tuple, not the live list
    # Each read is a fresh snapshot object.
    assert engine.audit_log is not engine.audit_log
    # Entries are frozen dataclasses — cannot be mutated in place.
    with pytest.raises(FrozenInstanceError):
        log[0].actor = "attacker"  # type: ignore[misc]
    # A subsequent read is unaffected by any tampering attempt.
    assert engine.audit_log[0].actor == ACTOR


# --- Codex round 1: immutable shared state + input validation --------------


def test_returned_consent_record_is_immutable_post_withdrawal() -> None:
    # Mutating the record returned by withdraw() back to granted must not
    # re-enable consent-based processing.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    withdrawn = engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)

    with pytest.raises(FrozenInstanceError):
        withdrawn.state = ConsentState.GRANTED  # type: ignore[misc]

    assert engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR).allowed is False


def test_registering_a_bogus_basis_is_rejected() -> None:
    engine = ConsentEngine()
    with pytest.raises(ValueError, match="unknown lawful basis"):
        engine.register_activity(ProcessingActivity("p", "bogus"))  # type: ignore[arg-type]
    # Nothing got registered, so the purpose is denied (no allow-when-deny).
    assert engine.can_process(SUBJECT, "p", actor=ACTOR).allowed is False


def test_valid_string_basis_is_accepted_and_normalised() -> None:
    engine = ConsentEngine()
    engine.register_activity(ProcessingActivity("p", "contract"))  # type: ignore[arg-type]
    assert engine.bases_for("p") == (LawfulBasis.CONTRACT,)
    assert engine.can_process(SUBJECT, "p", actor=ACTOR).basis is LawfulBasis.CONTRACT


def test_raw_pii_subject_is_rejected_and_not_audited() -> None:
    captured: list[AuditEntry] = []
    engine = build_default_engine(sink=captured.append)
    # `subj_Alice_Smith` / `subj_00FF` carry the prefix but are NOT hex — the old
    # `subj_[A-Za-z0-9_]+` rule wrongly admitted them; hex-only now rejects them.
    for bad in (
        "alice@example.com",
        "123-45-6789",
        "Alice Smith",
        "user 7",
        "subj_Alice_Smith",
        "subj_00FF",
    ):
        with pytest.raises(ValueError, match="pseudonymous"):
            engine.capture_consent(bad, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
        with pytest.raises(ValueError, match="pseudonymous"):
            engine.can_process(bad, PURPOSE_MARKETING_EMAIL, actor=ACTOR)

    assert captured == []  # nothing reached the audit sink

    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    assert engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR).allowed is True


def test_unsafe_actor_is_rejected() -> None:
    engine = build_default_engine()
    with pytest.raises(ValueError, match="actor"):
        engine.capture_consent(
            SUBJECT, PURPOSE_MARKETING_EMAIL, actor="alice@example.com", version="v1"
        )
    with pytest.raises(ValueError, match="actor"):
        engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor="alice@example.com")


def test_sink_cannot_tamper_with_the_stored_audit_entry() -> None:
    def tampering_sink(entry: AuditEntry) -> None:
        with pytest.raises(FrozenInstanceError):
            entry.actor = "attacker"  # type: ignore[misc]

    engine = build_default_engine(sink=tampering_sink)
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    assert engine.audit_log[0].actor == ACTOR


# --- Codex round 2: validate all audit inputs, TOCTOU, anchor parity -------


def test_pii_shaped_purpose_and_version_are_rejected_and_not_audited() -> None:
    captured: list[AuditEntry] = []
    engine = build_default_engine(sink=captured.append)
    with pytest.raises(ValueError, match="purpose"):
        engine.capture_consent(SUBJECT, "alice@example.com", actor=ACTOR, version="v1")
    with pytest.raises(ValueError, match="purpose"):
        engine.can_process(SUBJECT, "alice@example.com", actor=ACTOR)
    with pytest.raises(ValueError, match="version"):
        engine.capture_consent(
            SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="alice@example.com"
        )
    assert captured == []  # no raw PII reached the audit sink


def test_guarded_process_denies_after_withdrawal() -> None:
    # A cached allow must not survive a withdrawal: guarded_process re-checks.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    assert engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR).allowed is True
    engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)

    ran = {"count": 0}

    def action() -> str:
        ran["count"] += 1
        return "processed"

    result = engine.guarded_process(SUBJECT, PURPOSE_MARKETING_EMAIL, action, actor=ACTOR)
    assert result.ran is False
    assert result.result is None
    assert result.decision.allowed is False
    assert ran["count"] == 0  # the side effect never ran


def test_guarded_process_runs_action_when_authorised() -> None:
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")
    result = engine.guarded_process(
        SUBJECT, PURPOSE_MARKETING_EMAIL, lambda: "processed", actor=ACTOR
    )
    assert result.ran is True
    assert result.result == "processed"


@pytest.mark.parametrize("bad", ["subj_0042\n", "subj_0042\x00", "subj 0042", "subj_0042\r"])
def test_subject_with_newline_or_control_char_is_rejected(bad: str) -> None:
    # fullmatch rejects a trailing newline / control char (re.match+$ would not).
    engine = build_default_engine()
    with pytest.raises(ValueError, match="pseudonymous"):
        engine.capture_consent(bad, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")


def test_actor_purpose_version_with_trailing_newline_rejected() -> None:
    engine = build_default_engine()
    with pytest.raises(ValueError, match="actor"):
        engine.capture_consent(
            SUBJECT, PURPOSE_MARKETING_EMAIL, actor="privacy-service\n", version="v1"
        )
    with pytest.raises(ValueError, match="purpose"):
        engine.capture_consent(SUBJECT, "marketing_email\n", actor=ACTOR, version="v1")
    with pytest.raises(ValueError, match="version"):
        engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1\n")


# --- Codex round 3: strict actor/version formats + atomic guard ------------


def test_ssn_or_phone_shaped_version_and_actor_are_rejected() -> None:
    captured: list[AuditEntry] = []
    engine = build_default_engine(sink=captured.append)
    for bad_version in ("123-45-6789", "555-0142", "123-456-7890"):
        with pytest.raises(ValueError, match="version"):
            engine.capture_consent(
                SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version=bad_version
            )
    for bad_actor in ("123-45-6789", "555-0142"):
        with pytest.raises(ValueError, match="actor"):
            engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=bad_actor, version="v1")
    assert captured == []  # no SSN/phone-shaped value reached the audit sink

    # Valid strict formats still pass.
    engine.capture_consent(
        SUBJECT, PURPOSE_MARKETING_EMAIL, actor="privacy-service", version="2026.07.01"
    )
    engine.capture_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, actor="privacy-service", version="v1")


def test_reentrant_sink_withdrawal_blocks_execution() -> None:
    # A synchronous audit sink that withdraws consent during can_process's log
    # must not let a stale allow dispatch: the final atomic re-check catches it.
    holder: dict[str, ConsentEngine] = {}
    state = {"withdrawn": False}

    def sink(entry: AuditEntry) -> None:
        if entry.outcome == "allow" and not state["withdrawn"]:
            state["withdrawn"] = True
            holder["engine"].withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)

    engine = build_default_engine(sink=sink)
    holder["engine"] = engine
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")

    ran = {"count": 0}

    def action() -> str:
        ran["count"] += 1
        return "processed"

    result = engine.guarded_process(SUBJECT, PURPOSE_MARKETING_EMAIL, action, actor=ACTOR)
    assert result.ran is False  # final re-check caught the re-entrant withdrawal
    assert result.result is None
    assert result.decision.allowed is False
    assert ran["count"] == 0  # the side effect never ran


def test_guarded_process_serialises_concurrent_withdrawal() -> None:
    # A concurrent thread that withdraws consent DURING the guarded window must
    # not let the action run after the withdrawal commits. The RLock serialises
    # the final check + dispatch against withdraw_consent, so the action always
    # runs while consent is still granted, and the withdrawal commits only after.
    engine = build_default_engine()
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="v1")

    action_entered = threading.Event()
    withdrew = threading.Event()
    observations: dict[str, object] = {}

    def action() -> str:
        # Running inside guarded_process, under the lock. Signal the withdrawer.
        action_entered.set()
        # Give a concurrent withdrawal a chance to commit. It can't while we hold
        # the lock, so this times out and consent is still granted below; without
        # the lock the withdrawal commits and this returns early.
        withdrew.wait(timeout=0.5)
        observations["consent_at_action"] = engine.has_valid_consent(
            SUBJECT, PURPOSE_MARKETING_EMAIL
        )
        return "processed"

    def withdrawer() -> None:
        action_entered.wait(timeout=2)
        engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)
        withdrew.set()

    thread = threading.Thread(target=withdrawer)
    thread.start()
    try:
        result = engine.guarded_process(SUBJECT, PURPOSE_MARKETING_EMAIL, action, actor=ACTOR)
    finally:
        thread.join(timeout=2)

    # The action ran atomically while consent was still granted...
    assert result.ran is True
    assert observations["consent_at_action"] is True
    # ...and the concurrent withdrawal committed only after the action finished.
    assert thread.is_alive() is False
    assert engine.has_valid_consent(SUBJECT, PURPOSE_MARKETING_EMAIL) is False
