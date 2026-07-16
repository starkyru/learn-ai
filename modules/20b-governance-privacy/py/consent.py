"""Consent + lawful-basis engine (Module 20b, Task 2).

Synthetic data only — nothing here is real, and none of it is legal advice.

The teaching point: **consent is just ONE lawful basis among several.** A
processing activity is authorised only if *some* valid basis covers its *exact*
purpose. Consent can be withdrawn — and withdrawing it stops consent-based
processing for that purpose — but it does NOT revoke a *different* basis
(contract, legal obligation, …) that authorises the same purpose. Treating
consent as a universal on/off switch is the classic mistake this module guards
against.

Design notes:

- **Purpose limitation.** :meth:`ConsentEngine.can_process` checks the exact
  purpose only. Consent for purpose A never authorises purpose B — there is no
  "blanket consent."
- **Auditable decisions.** Every capture / withdraw / authorisation appends an
  :class:`AuditEntry` (actor, time, subject, purpose, basis, outcome, reason).
- **Safe logging (from Task 1).** The engine only ever handles a *pseudonymous*
  subject id and coarse purpose/basis labels — never raw PII. Keep it that way.
"""

from __future__ import annotations

import itertools
import re
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum


class LawfulBasis(str, Enum):
    """Lawful bases for processing. ``CONSENT`` is one option, not the default."""

    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    LEGITIMATE_INTEREST = "legitimate_interest"
    VITAL_INTEREST = "vital_interest"
    PUBLIC_TASK = "public_task"


class ConsentState(str, Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True)
class ProcessingActivity:
    """Declares that ``purpose`` is processed under ``basis``.

    A purpose may be declared under more than one basis (e.g. an activity resting
    on both ``contract`` and ``consent``); each declaration is one of these.
    """

    purpose: str
    basis: LawfulBasis
    description: str = ""


@dataclass(frozen=True)
class ConsentRecord:
    """Immutable consent decision for one (subject, purpose). Always ``CONSENT``.

    ``version`` is the policy/notice version in force at capture, recorded for
    the audit trail only — it is NOT enforced here: bumping a version does not
    auto-invalidate an existing consent. A system that needs re-consent on a
    version change must implement that check explicitly.
    """

    subject: str  # pseudonymous subject id
    purpose: str
    state: ConsentState
    version: str
    time: int
    basis: LawfulBasis = LawfulBasis.CONSENT


@dataclass(frozen=True)
class Decision:
    """Outcome of :meth:`ConsentEngine.can_process`."""

    allowed: bool
    basis: LawfulBasis | None  # which basis authorised it (None when denied)
    reason: str


@dataclass(frozen=True)
class GuardedResult:
    """Outcome of :meth:`ConsentEngine.guarded_process`.

    ``ran`` is True only if the re-check authorised the side effect and
    ``action`` was invoked; ``result`` is then its return value.
    """

    decision: Decision
    ran: bool
    result: object


@dataclass(frozen=True)
class AuditEntry:
    """One row of the append-only decision log. Fields are exactly the record."""

    actor: str
    time: int
    subject: str  # pseudonymous subject id — never a raw identifier
    purpose: str
    basis: LawfulBasis | None
    outcome: str  # "granted" | "withdrawn" | "allow" | "deny"
    reason: str

    def to_record(self) -> dict[str, object]:
        """Serialise to a plain, log-safe dict with exactly the required keys."""
        return {
            "actor": self.actor,
            "time": self.time,
            "subject": self.subject,
            "purpose": self.purpose,
            "basis": self.basis.value if self.basis is not None else None,
            "outcome": self.outcome,
            "reason": self.reason,
        }


def _tick_clock() -> Callable[[], int]:
    """A deterministic monotonic clock: 0, 1, 2, … (one tick per read)."""
    counter = itertools.count()
    return lambda: next(counter)


# Every value that reaches an audit entry must be a safe label, never raw PII.
# Patterns are matched with ``fullmatch`` so a trailing newline or an embedded
# control character is rejected (``re.match`` with ``$`` would let ``"x\n"``
# through, diverging from the TS RegExp and smuggling control chars into audit).
# ``actor``/``version`` use STRICT formats that must start with a letter/``v`` so
# an SSN- or phone-shaped run of digits and dashes (e.g. ``123-45-6789``) fails.
# A subject is a STRICT opaque token: `subj_` + hex only (mirrors rights.py). A
# looser `subj_[A-Za-z0-9_]+` would admit `subj_Alice_Smith` — an identifier that
# is itself PII — and persist it in the audit.
_SUBJECT_RE = re.compile(r"subj_[0-9a-f]+")  # pseudonymous id, e.g. subj_0042
_ACTOR_RE = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")  # service id, e.g. privacy-service
_PURPOSE_RE = re.compile(r"[a-z][a-z0-9_]*")  # snake_case purpose label
_VERSION_RE = re.compile(r"v?\d+(\.\d+)*")  # version label, e.g. v1, 1.2, 2026.07.01


def _normalize_basis(basis: object) -> LawfulBasis:
    """Coerce/validate a declared basis to a :class:`LawfulBasis`.

    Accepts a member or a valid string value; rejects anything else so a bogus
    basis can never reach evaluation (where it would crash or wrongly allow).
    """
    if isinstance(basis, LawfulBasis):
        return basis
    try:
        return LawfulBasis(basis)
    except ValueError:
        raise ValueError(f"unknown lawful basis: {basis!r}") from None


def _require_subject(subject: str) -> None:
    if not isinstance(subject, str) or not _SUBJECT_RE.fullmatch(subject):
        raise ValueError(
            "subject must be an opaque pseudonymous token like 'subj_0042' "
            "(subj_ + hex only; a name/email/SSN suffix like 'subj_Alice_Smith' "
            f"is rejected); got {subject!r}"
        )


def _require_actor(actor: str) -> None:
    # Must start with a letter, so an SSN/phone-shaped digit-dash run is rejected.
    if not isinstance(actor, str) or not _ACTOR_RE.fullmatch(actor):
        raise ValueError(
            "actor must be a service id like 'privacy-service' (starts with a "
            f"letter; not a digit-dash run), not free PII; got {actor!r}"
        )


def _require_purpose(purpose: str) -> None:
    if not isinstance(purpose, str) or not _PURPOSE_RE.fullmatch(purpose):
        raise ValueError(
            "purpose must be a snake_case label like 'marketing_email' (no raw "
            f"PII); got {purpose!r}"
        )


def _require_version(version: str) -> None:
    # A dotted/semver-style label, so an SSN-shaped '123-45-6789' is rejected.
    if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
        raise ValueError(
            "version must be a version label like 'v1', '1.2', or '2026.07.01' "
            f"(digits/dots, optional leading 'v'; no raw PII); got {version!r}"
        )


class ConsentEngine:
    """Registers activities, captures/withdraws consent, and authorises purposes.

    ``clock`` is injectable for deterministic tests; ``sink`` (if given) receives
    each :class:`AuditEntry` as it is appended, mirroring Task 1's log sink.

    Note on ``actor``: every method takes a free-form ``actor`` string for the
    audit record. In production this must be derived from an authenticated caller
    identity, not passed in by the caller — here it is a plain parameter for the
    exercise.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], int] | None = None,
        sink: Callable[[AuditEntry], None] | None = None,
    ) -> None:
        self._clock = clock or _tick_clock()
        self._sink = sink
        # Serialises the consent store across threads. Re-entrant (RLock) so a
        # re-entrant sink/action on the SAME thread does not deadlock. See
        # `guarded_process` for why it wraps the final check + dispatch.
        self._lock = threading.RLock()
        # purpose -> ordered list of bases that authorise it
        self._activities: dict[str, list[LawfulBasis]] = {}
        # (subject, purpose) -> current consent record
        self._consents: dict[tuple[str, str], ConsentRecord] = {}
        self._audit: list[AuditEntry] = []

    # --- registration ------------------------------------------------------

    def register_activity(self, activity: ProcessingActivity) -> None:
        # Reject a runtime-invalid basis or an unsafe purpose label (static types
        # can be bypassed) so malformed config can never authorise processing it
        # shouldn't, nor write raw PII to the audit trail.
        _require_purpose(activity.purpose)
        basis = _normalize_basis(activity.basis)
        bases = self._activities.setdefault(activity.purpose, [])
        if basis not in bases:
            bases.append(basis)

    def register_activities(self, activities: Iterable[ProcessingActivity]) -> None:
        for activity in activities:
            self.register_activity(activity)

    def bases_for(self, purpose: str) -> tuple[LawfulBasis, ...]:
        return tuple(self._activities.get(purpose, ()))

    # --- consent lifecycle -------------------------------------------------

    def capture_consent(
        self, subject: str, purpose: str, *, actor: str, version: str
    ) -> ConsentRecord:
        _require_subject(subject)
        _require_actor(actor)
        _require_purpose(purpose)
        _require_version(version)
        # Hold the lock so this commit cannot interleave a guarded_process
        # final-check + dispatch on another thread.
        with self._lock:
            record = ConsentRecord(
                subject=subject,
                purpose=purpose,
                state=ConsentState.GRANTED,
                version=version,
                time=self._clock(),
            )
            self._consents[(subject, purpose)] = record
            self._log(
                actor=actor,
                time=record.time,
                subject=subject,
                purpose=purpose,
                basis=LawfulBasis.CONSENT,
                outcome="granted",
                reason=f"consent captured (version {version})",
            )
        return record

    def withdraw_consent(self, subject: str, purpose: str, *, actor: str) -> ConsentRecord:
        _require_subject(subject)
        _require_actor(actor)
        _require_purpose(purpose)
        # Take the same lock as guarded_process, so a withdrawal cannot commit
        # between another thread's final authorisation check and its dispatch.
        with self._lock:
            previous = self._consents.get((subject, purpose))
            version = previous.version if previous is not None else "none"
            record = ConsentRecord(
                subject=subject,
                purpose=purpose,
                state=ConsentState.WITHDRAWN,
                version=version,
                time=self._clock(),
            )
            self._consents[(subject, purpose)] = record
            self._log(
                actor=actor,
                time=record.time,
                subject=subject,
                purpose=purpose,
                basis=LawfulBasis.CONSENT,
                outcome="withdrawn",
                reason="consent withdrawn",
            )
        return record

    def has_valid_consent(self, subject: str, purpose: str) -> bool:
        record = self._consents.get((subject, purpose))
        return record is not None and record.state is ConsentState.GRANTED

    # --- purpose-limited authorisation ------------------------------------

    def can_process(self, subject: str, purpose: str, *, actor: str = "system") -> Decision:
        """Authorise processing ``subject``'s data for the EXACT ``purpose``.

        Allowed iff some registered basis for that purpose is currently valid: a
        ``CONSENT`` basis needs a granted (not withdrawn) consent record; any
        non-consent basis authorises by its declaration. Consent for a different
        purpose never helps — no blanket consent.

        This is a POINT-IN-TIME decision. Do NOT cache the boolean and act on it
        later: a subject may withdraw consent between the check and the side
        effect (a time-of-check/time-of-use gap). Re-check at the side-effect
        boundary — see :meth:`guarded_process`, which does exactly that.
        """
        _require_subject(subject)
        _require_actor(actor)
        _require_purpose(purpose)
        bases = self._activities.get(purpose, [])
        decision = self._evaluate(subject, purpose, bases)
        self._log(
            actor=actor,
            time=self._clock(),
            subject=subject,
            purpose=purpose,
            basis=decision.basis,
            outcome="allow" if decision.allowed else "deny",
            reason=decision.reason,
        )
        return decision

    def guarded_process(
        self,
        subject: str,
        purpose: str,
        action: Callable[[], object],
        *,
        actor: str = "system",
    ) -> GuardedResult:
        """Re-check authorisation atomically, then run ``action`` only if allowed.

        Binds the consent check to the side effect: it calls :meth:`can_process`
        immediately before invoking ``action`` and refuses to run it when not
        currently authorised, so a stale earlier allow cannot be replayed after a
        withdrawal. (Deliberately simple — a real system may need a stronger
        capability/transaction boundary.)

        ``can_process`` invokes the audit sink, and a synchronous sink could
        withdraw consent re-entrantly during that call. So the gate is a FINAL
        bare re-check of CURRENT state (:meth:`_is_authorised_now`, which does NOT
        call the sink) taken IMMEDIATELY before dispatch — nothing runs between
        that check and ``action()``, so the sink cannot invalidate it afterwards.

        Python has real threads, so the final check AND the dispatch are done
        while holding ``self._lock`` — the same lock ``capture_consent`` /
        ``withdraw_consent`` take — so a CONCURRENT withdrawal on another thread
        cannot commit between the check and the side effect; the two serialize.
        """
        decision = self.can_process(subject, purpose, actor=actor)
        if not decision.allowed:
            return GuardedResult(decision=decision, ran=False, result=None)
        with self._lock:
            if not self._is_authorised_now(subject, purpose):
                revoked = Decision(False, None, "authorisation revoked before dispatch")
                self._log(
                    actor=actor,
                    time=self._clock(),
                    subject=subject,
                    purpose=purpose,
                    basis=None,
                    outcome="deny",
                    reason=revoked.reason,
                )
                return GuardedResult(decision=revoked, ran=False, result=None)
            # Lock held across the check above AND the dispatch below: no other
            # thread's capture/withdraw can interleave here.
            return GuardedResult(decision=decision, ran=True, result=action())

    def _is_authorised_now(self, subject: str, purpose: str) -> bool:
        """Bare, side-effect-free authorisation check of CURRENT state (no sink)."""
        bases = self._activities.get(purpose, [])
        return self._evaluate(subject, purpose, bases).allowed

    def _evaluate(self, subject: str, purpose: str, bases: list[LawfulBasis]) -> Decision:
        if not bases:
            return Decision(False, None, f"no lawful basis registered for purpose '{purpose}'")
        for basis in bases:
            if basis is LawfulBasis.CONSENT:
                if self.has_valid_consent(subject, purpose):
                    return Decision(True, basis, f"authorised by consent for purpose '{purpose}'")
            else:
                # A non-consent basis authorises by declaration; it is unaffected
                # by whether consent was ever granted or has been withdrawn.
                return Decision(True, basis, f"authorised by {basis.value} for purpose '{purpose}'")
        return Decision(
            False,
            None,
            f"purpose '{purpose}' relies on consent, which is not currently granted",
        )

    # --- audit -------------------------------------------------------------

    @property
    def audit_log(self) -> tuple[AuditEntry, ...]:
        return tuple(self._audit)

    def audit_records(self) -> list[dict[str, object]]:
        """The audit log as plain, log-safe dicts."""
        return [entry.to_record() for entry in self._audit]

    def _log(
        self,
        *,
        actor: str,
        time: int,
        subject: str,
        purpose: str,
        basis: LawfulBasis | None,
        outcome: str,
        reason: str,
    ) -> None:
        entry = AuditEntry(
            actor=actor,
            time=time,
            subject=subject,
            purpose=purpose,
            basis=basis,
            outcome=outcome,
            reason=reason,
        )
        self._audit.append(entry)
        if self._sink is not None:
            self._sink(entry)


# --- A synthetic activity catalogue for the demo/tests ----------------------
#
# Purposes are coarse labels; subjects are pseudonymous ids. Note that
# "account_security" is authorised under BOTH consent and a non-consent basis —
# that is the case that shows withdrawal does not revoke the other basis.

PURPOSE_MARKETING_EMAIL = "marketing_email"
PURPOSE_PRODUCT_ANALYTICS = "product_analytics"
PURPOSE_ORDER_FULFILMENT = "order_fulfilment"
PURPOSE_FRAUD_DETECTION = "fraud_detection"
PURPOSE_ACCOUNT_SECURITY = "account_security"

DEFAULT_ACTIVITIES: tuple[ProcessingActivity, ...] = (
    ProcessingActivity(PURPOSE_MARKETING_EMAIL, LawfulBasis.CONSENT, "send marketing email"),
    ProcessingActivity(PURPOSE_PRODUCT_ANALYTICS, LawfulBasis.CONSENT, "optional analytics"),
    ProcessingActivity(PURPOSE_ORDER_FULFILMENT, LawfulBasis.CONTRACT, "ship the order"),
    ProcessingActivity(PURPOSE_FRAUD_DETECTION, LawfulBasis.LEGAL_OBLIGATION, "AML/fraud checks"),
    # Same purpose, two bases (consent listed first so the demo shows the
    # authorising basis SHIFT from consent to contract on withdrawal). Contract
    # keeps the purpose lawful even after consent is pulled. Basis precedence is
    # a policy choice; here consent is tried first, contract is the fallback.
    ProcessingActivity(PURPOSE_ACCOUNT_SECURITY, LawfulBasis.CONSENT, "optional extra checks"),
    ProcessingActivity(PURPOSE_ACCOUNT_SECURITY, LawfulBasis.CONTRACT, "secure the account"),
)


def build_default_engine(
    *,
    clock: Callable[[], int] | None = None,
    sink: Callable[[AuditEntry], None] | None = None,
) -> ConsentEngine:
    engine = ConsentEngine(clock=clock, sink=sink)
    engine.register_activities(DEFAULT_ACTIVITIES)
    return engine
