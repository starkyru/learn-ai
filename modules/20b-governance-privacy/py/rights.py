"""Data-subject rights engine (Module 20b, Task 2).

Synthetic data only — nothing here is real, and none of it is legal advice.

The teaching point: a subject's data lives in MANY stores (primary record, the
embedding index, caches, feedback, human-review queues, background jobs), so
export and erasure must reach ALL of them, not just the source record. Erasure
is not uniform either: some stores hard-delete, while a store under a documented
retention EXCEPTION (e.g. a legal-hold review record) keeps a TOMBSTONE — the id
and a reason code, never the raw content — and separately, records past their
retention period are PURGED.

Design discipline (reused from Task 1/2 and hardened here):

- **Metadata-only handles.** ``add_record`` / ``records_for`` return metadata
  (id, store, class, timestamps, retention) — NEVER the raw content. Only
  ``export`` returns content, as a deliberate point-in-time snapshot the
  requester legitimately owns.
- **Erase is a transaction with a WRITE BARRIER.** While a subject is being
  erased (and while its audit is flushed to the sink), any ``add_record`` for
  that subject is REJECTED — so a reentrant/racing add can't be swept or
  tombstoned-without-reviewer.
- **Reason CODES, not free text.** Audit reasons are an allowlisted enum so no
  PII-shaped free text can reach an audit record.
- **Engine-owned, validated policy.** Registration copies the policy fields into
  a fresh engine-owned instance (never retains the caller's object).
"""

from __future__ import annotations

import itertools
import re
import threading
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

# --- validation (mirrors consent.py — safe labels, never raw PII) -----------

# A subject is a STRICT opaque token: `subj_` + hex only. A prefix-only rule like
# `subj_[A-Za-z0-9_]+` would admit `subj_Alice_Smith` — an identifier that is
# itself PII — and persist it in the audit. `record_id` (a caller string that
# survives into a tombstone and audit) is likewise an opaque `word_hex` token.
_SUBJECT_RE = re.compile(r"subj_[0-9a-f]+")  # pseudonymous id, e.g. subj_0042
_RECORD_RE = re.compile(r"[a-z][a-z0-9]*_[0-9a-f]+")  # opaque token, e.g. rec_1a2b
_ACTOR_RE = re.compile(r"[a-z][a-z0-9]*(-[a-z0-9]+)*")  # service/role id, incl. reviewer
_STORE_RE = re.compile(r"[a-z][a-z0-9_]*")  # snake_case store id


def _require_subject(subject: str) -> None:
    if not isinstance(subject, str) or not _SUBJECT_RE.fullmatch(subject):
        raise ValueError(
            "subject must be an opaque pseudonymous token like 'subj_0042' "
            "(subj_ + hex only; a name/email/SSN suffix like 'subj_Alice_Smith' "
            f"is rejected); got {subject!r}"
        )


def _require_record_id(record_id: str) -> None:
    if not isinstance(record_id, str) or not _RECORD_RE.fullmatch(record_id):
        raise ValueError(
            "record_id must be an opaque token like 'rec_1a2b' (lowercase prefix "
            "+ '_' + hex; no free text / PII such as a name or SSN); got "
            f"{record_id!r}"
        )


def _require_actor(actor: str) -> None:
    if not isinstance(actor, str) or not _ACTOR_RE.fullmatch(actor):
        raise ValueError(
            "actor must be a service id like 'privacy-service' (starts with a "
            f"letter; not a digit-dash run), not free PII; got {actor!r}"
        )


def _require_reviewer(reviewer: str) -> None:
    if not isinstance(reviewer, str) or not _ACTOR_RE.fullmatch(reviewer):
        raise ValueError(
            "reviewer must be a role/service id like 'legal-team' (not a raw "
            f"person name); got {reviewer!r}"
        )


def _require_store_name(name: str) -> None:
    if not isinstance(name, str) or not _STORE_RE.fullmatch(name):
        raise ValueError(
            "store name must be a snake_case label like 'human_review' (no raw "
            f"PII such as an email); got {name!r}"
        )


# Allowlisted lawful bases for RE-COLLECTING data after an erasure (mirrors the
# Task-2 consent bases). Reactivating an erased subject must name one, so erasure
# can only ever be reversed under a deliberate, recorded lawful basis.
_LAWFUL_BASES: frozenset[str] = frozenset(
    {
        "consent",
        "contract",
        "legal_obligation",
        "legitimate_interest",
        "vital_interest",
        "public_task",
    }
)


def _require_lawful_basis(basis: object) -> str:
    value = basis.value if isinstance(basis, Enum) else basis
    if not isinstance(value, str) or value not in _LAWFUL_BASES:
        raise ValueError(
            "lawful_basis must be an allowlisted lawful basis (e.g. 'consent', "
            f"'contract', 'legal_obligation'); got {basis!r}"
        )
    return value


def _deep_readonly(value: object) -> object:
    """Deep, read-only copy: mappings -> MappingProxyType, sequences -> tuples."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: _deep_readonly(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_readonly(v) for v in value)
    return value


# --- retention policy + records --------------------------------------------


class RetentionMode(str, Enum):
    HARD_DELETE = "hard_delete"  # erasure removes the record entirely
    TOMBSTONE = "tombstone"  # erasure keeps an id + reason code (retention exception)


class ReasonCode(str, Enum):
    """Allowlisted, non-PII reason codes. The ONLY reasons audit records carry.

    Human-readable rationale (if any) lives in ``StorePolicy.description``, which
    is NOT written to the audit trail.
    """

    LEGAL_HOLD = "legal_hold"
    REGULATORY_RETENTION = "regulatory_retention"
    SUBJECT_REQUEST = "subject_request"
    RETENTION_EXPIRY = "retention_expiry"


def _require_reason(reason: object) -> None:
    if not isinstance(reason, ReasonCode):
        raise ValueError(
            "reason must be an allowlisted ReasonCode (not free text that could "
            f"carry PII); got {reason!r}"
        )


@dataclass(frozen=True)
class StorePolicy:
    """How one store is located and how erasure/retention treat it."""

    name: str
    location: str  # storage location label, from the data map
    mode: RetentionMode
    retention_ticks: int  # a record older than this (by the clock) is purged
    reason: ReasonCode | None = None  # retention-exception CODE (TOMBSTONE stores)
    requires_reviewer: bool = False  # erasure needs a named reviewer sign-off
    description: str = ""  # human text — NOT written to the audit trail


@dataclass(frozen=True)
class Record:
    """LIVE internal record (mutable content). Never handed out directly."""

    store: str
    subject: str
    record_id: str
    created_at: int
    content: Mapping[str, object]  # synthetic; emptied once tombstoned/erased
    tombstoned: bool = False
    tombstone_reason: str | None = None


@dataclass(frozen=True)
class RecordMetadata:
    """A metadata-only view of a record — NO raw content. Safe to hand out."""

    store: str
    subject: str
    record_id: str
    created_at: int
    tombstoned: bool
    tombstone_reason: str | None
    mode: RetentionMode
    retention_ticks: int
    location: str


# --- export / erasure result types -----------------------------------------


@dataclass(frozen=True)
class ExportCopy:
    store: str
    location: str
    record_id: str
    tombstoned: bool
    content: Mapping[str, object]  # point-in-time copy the requester owns


@dataclass(frozen=True)
class ExportManifest:
    subject: str
    copies: tuple[ExportCopy, ...]

    def stores(self) -> set[str]:
        return {c.store for c in self.copies}

    def locations(self) -> dict[str, str]:
        return {c.store: c.location for c in self.copies}


@dataclass(frozen=True)
class ErasureOutcome:
    store: str
    result: str  # "hard_deleted" | "tombstoned"
    count: int
    reviewer: str | None
    reason: str  # a ReasonCode value


@dataclass(frozen=True)
class ErasureReport:
    subject: str
    outcomes: tuple[ErasureOutcome, ...]

    def by_store(self) -> dict[str, ErasureOutcome]:
        return {o.store: o for o in self.outcomes}


# --- audit trail (immutable, append-only, no raw content) -------------------


@dataclass(frozen=True)
class RightsAuditEntry:
    actor: str
    time: int
    action: str  # "export" | "delete" | "tombstone" | "expire"
    subject: str  # pseudonymous id, or "*" for a store-wide sweep
    store: str  # store name, or "*" for all stores
    scope: str  # what was covered, e.g. a record count
    result: str  # "exported" | "hard_deleted" | "tombstoned" | "purged"
    reviewer: str | None  # set only where the store requires review
    reason: str  # a ReasonCode value — never free text

    def to_record(self) -> dict[str, object]:
        return {
            "actor": self.actor,
            "time": self.time,
            "action": self.action,
            "subject": self.subject,
            "store": self.store,
            "scope": self.scope,
            "result": self.result,
            "reviewer": self.reviewer,
            "reason": self.reason,
        }


def _scrub(record: Record) -> None:
    """Empty a record's internal content in place (raw content unreachable)."""
    if isinstance(record.content, dict):
        record.content.clear()


class _FakeStore:
    """A fake in-memory store keyed by ``(subject, record_id)``.

    Keying by ``record_id`` alone would let two different subjects that reuse the
    same id silently overwrite each other; the composite key keeps them distinct.
    """

    def __init__(self, policy: StorePolicy) -> None:
        self.policy = policy
        self._records: dict[tuple[str, str], Record] = {}

    def put(self, record: Record) -> None:
        self._records[(record.subject, record.record_id)] = record

    def delete(self, subject: str, record_id: str) -> None:
        self._records.pop((subject, record_id), None)

    def subject_records(self, subject: str) -> list[Record]:
        return [r for r in self._records.values() if r.subject == subject]

    def all_records(self) -> list[Record]:
        return list(self._records.values())


# --- engine -----------------------------------------------------------------


class RightsEngine:
    """Export, erase/tombstone, and expire a subject's data across all stores."""

    def __init__(
        self,
        *,
        clock: Callable[[], int] | None = None,
        sink: Callable[[RightsAuditEntry], None] | None = None,
    ) -> None:
        self._clock = clock or _default_clock()
        self._sink = sink
        self._stores: dict[str, _FakeStore] = {}
        self._audit: list[RightsAuditEntry] = []
        self._lock = threading.RLock()
        # Subjects whose erasure (incl. audit flush) is in progress — the
        # in-transaction write barrier.
        self._erasing: set[str] = set()
        # DURABLE erased-subject marker that OUTLIVES the erase transaction. A
        # transient in-progress flag would let a writer that was WAITING on the
        # lock slip in the instant the flag clears; this marker persists, so any
        # add for an erased subject is rejected until an explicit reactivation.
        self._erased: set[str] = set()
        # Outbox: audit entries whose external sink delivery failed. The entries
        # are already durably recorded in ``self._audit``; this is a retry queue
        # so a sink outage never fails/reopens an erase.
        self._pending_delivery: list[RightsAuditEntry] = []

    # --- setup -------------------------------------------------------------

    def register_store(self, policy: StorePolicy) -> None:
        _require_store_name(policy.name)
        if policy.reason is not None:
            _require_reason(policy.reason)
        if policy.name in self._stores:
            raise ValueError(f"store already registered: {policy.name!r}")
        # Build a fresh ENGINE-OWNED policy from validated fields; never retain
        # the caller's object (a frozen dataclass still yields to
        # object.__setattr__, so a retained reference could be tampered with).
        owned = StorePolicy(
            name=policy.name,
            location=policy.location,
            mode=policy.mode,
            retention_ticks=policy.retention_ticks,
            reason=policy.reason,
            requires_reviewer=policy.requires_reviewer,
            description=policy.description,
        )
        self._stores[policy.name] = _FakeStore(owned)

    def add_record(
        self,
        store: str,
        subject: str,
        record_id: str,
        content: Mapping[str, object],
        *,
        created_at: int | None = None,
    ) -> RecordMetadata:
        _require_subject(subject)
        _require_record_id(record_id)
        with self._lock:
            # Re-check the erased state AFTER acquiring the lock, so a writer
            # that queued/waited during an erase cannot slip past once the
            # in-progress flag clears — the durable marker is still set.
            if subject in self._erasing or subject in self._erased:
                raise RuntimeError(
                    f"subject {subject!r} is erased; explicit reactivation (a new "
                    "lawful basis) is required to accept new data"
                )
            if store not in self._stores:
                raise KeyError(f"unknown store: {store!r}")
            internal = Record(
                store=store,
                subject=subject,
                record_id=record_id,
                created_at=self._clock() if created_at is None else created_at,
                content=deepcopy(dict(content)),  # live, mutable, private copy
            )
            self._stores[store].put(internal)
            return self._metadata(internal, self._stores[store].policy)

    def _metadata(self, record: Record, policy: StorePolicy) -> RecordMetadata:
        return RecordMetadata(
            store=record.store,
            subject=record.subject,
            record_id=record.record_id,
            created_at=record.created_at,
            tombstoned=record.tombstoned,
            tombstone_reason=record.tombstone_reason,
            mode=policy.mode,
            retention_ticks=policy.retention_ticks,
            location=policy.location,
        )

    # --- inspection (for callers/tests) -----------------------------------

    def records_for(self, subject: str) -> tuple[RecordMetadata, ...]:
        """Metadata-only — never raw content (use ``export`` for content)."""
        with self._lock:
            return tuple(
                self._metadata(r, store.policy)
                for store in self._stores.values()
                for r in store.subject_records(subject)
            )

    def store_names(self) -> tuple[str, ...]:
        return tuple(self._stores)

    # --- export ------------------------------------------------------------

    def export(self, subject: str, *, actor: str) -> ExportManifest:
        """List EVERY known copy of ``subject``'s data across all stores.

        Unlike ``records_for``, an export DELIBERATELY includes each copy's
        content — it is the point-in-time snapshot the subject asked for and now
        legitimately owns (a retained export is the requester's own copy).
        """
        _require_subject(subject)
        _require_actor(actor)
        copies: list[ExportCopy] = []
        with self._lock:
            for name, store in self._stores.items():
                for record in store.subject_records(subject):
                    copies.append(
                        ExportCopy(
                            store=name,
                            location=store.policy.location,
                            record_id=record.record_id,
                            tombstoned=record.tombstoned,
                            content=_deep_readonly(deepcopy(dict(record.content))),
                        )
                    )
        manifest = ExportManifest(subject=subject, copies=tuple(copies))
        self._log(
            actor=actor,
            action="export",
            subject=subject,
            store="*",
            scope=str(len(manifest.copies)),
            result="exported",
            reviewer=None,
            reason=ReasonCode.SUBJECT_REQUEST.value,
        )
        return manifest

    # --- erasure (delete / tombstone with retention exceptions) -----------

    def erase(self, subject: str, *, actor: str, reviewer: str | None = None) -> ErasureReport:
        """Delete or tombstone each copy per its store's retention policy.

        A locked TRANSACTION guarded by a per-subject WRITE BARRIER: for the whole
        duration (mutation AND the audit-sink flush) any ``add_record`` for this
        subject is rejected, so a reentrant/racing add cannot be swept or
        tombstoned-without-review. The external sink is not called during the
        mutation window; buffered entries are flushed afterwards while the barrier
        is still up. A reviewer-gated store refuses to erase without a reviewer
        (checked up front on a snapshot, so a partial erasure never happens).

        Reviewer trust boundary: ``reviewer`` here is a TRUSTED, caller-supplied
        label — this fake-store teaching engine records the reviewer identity, it
        does NOT authenticate it (any in-process caller could pass ``legal-team``,
        the same in-process boundary documented for ``actor`` in consent). A
        PRODUCTION system MUST bind ``reviewer`` to an authenticated approval
        capability (a verified reviewer principal / signed approval carrying role
        + scope) derived from the authorization layer — not a bare string.
        """
        _require_subject(subject)
        _require_actor(actor)
        if reviewer is not None:
            _require_reviewer(reviewer)

        outcomes: list[ErasureOutcome] = []
        buffered: list[RightsAuditEntry] = []
        with self._lock:
            if subject in self._erasing:
                raise RuntimeError(f"erase already in progress for {subject!r}")
            self._erasing.add(subject)
            try:
                snapshot: dict[str, list[Record]] = {
                    name: list(store.subject_records(subject))
                    for name, store in self._stores.items()
                }
                for name, store in self._stores.items():
                    if store.policy.requires_reviewer and reviewer is None and snapshot[name]:
                        raise ValueError(
                            f"store '{store.policy.name}' requires a reviewer to erase "
                            "(retention-exception / legal-hold sign-off)"
                        )

                for name, store in self._stores.items():
                    records = snapshot[name]
                    if not records:
                        continue
                    if store.policy.mode is RetentionMode.HARD_DELETE:
                        for record in records:
                            _scrub(record)
                            store.delete(record.subject, record.record_id)
                        reason = ReasonCode.SUBJECT_REQUEST.value
                        outcome = ErasureOutcome(name, "hard_deleted", len(records), None, reason)
                        action, result_reviewer = "delete", None
                    else:  # TOMBSTONE — retention exception
                        reason = (store.policy.reason or ReasonCode.REGULATORY_RETENTION).value
                        for record in records:
                            _scrub(record)
                            store.put(
                                Record(
                                    store=name,
                                    subject=subject,
                                    record_id=record.record_id,
                                    created_at=self._clock(),
                                    content={},
                                    tombstoned=True,
                                    tombstone_reason=reason,
                                )
                            )
                        outcome = ErasureOutcome(name, "tombstoned", len(records), reviewer, reason)
                        action, result_reviewer = "tombstone", reviewer
                    outcomes.append(outcome)
                    entry = self._new_entry(
                        actor=actor,
                        action=action,
                        subject=subject,
                        store=name,
                        scope=str(len(records)),
                        result=outcome.result,
                        reviewer=result_reviewer,
                        reason=reason,
                    )
                    self._record(entry)
                    buffered.append(entry)

                # Commit the DURABLE erased marker BEFORE invoking any fallible
                # external sink, and KEEP it even if delivery fails. Data removal
                # + the erased marker are TERMINAL: a sink outage can be retried
                # but must never un-erase the subject or re-admit writes. (Also
                # protects the flush window: an add sees `_erased` and is rejected.)
                self._erased.add(subject)
                # Deliver the already-recorded audit to the external sink via the
                # outbox path; a sink exception is captured, not propagated.
                for entry in buffered:
                    self._deliver(entry)
            finally:
                self._erasing.discard(subject)
        return ErasureReport(subject=subject, outcomes=tuple(outcomes))

    def reactivate_subject(self, subject: str, *, lawful_basis: str, actor: str) -> None:
        """Clear the erased marker so new data may be collected again — an
        AUTHORIZED, AUDITED, erase-EXCLUSIVE transition.

        Erasure is terminal: clearing the marker is the ONLY way to re-admit data
        for an erased subject, so it is deliberately gated:

        - It REQUIRES a new, validated ``lawful_basis`` (an allowlisted lawful
          basis — you are re-collecting personal data, which needs a fresh basis)
          and a validated ``actor``.
        - It is REJECTED while ANY erasure is in progress, so a re-entrant audit
          sink invoked during an erase flush cannot clear the terminal marker
          mid-transaction and silently re-open collection.
        - It RECORDS the transition (actor/time/subject/action=reactivate/basis)
          in the audit trail BEFORE the marker is cleared.

        Like ``erase``'s reviewer, ``actor`` and ``lawful_basis`` are trusted,
        caller-supplied labels this teaching engine records but does not
        authenticate; a production system MUST bind them to an authenticated
        approval capability, not a bare string.
        """
        _require_subject(subject)
        _require_actor(actor)
        basis = _require_lawful_basis(lawful_basis)
        with self._lock:
            if self._erasing:
                raise RuntimeError(
                    "cannot reactivate a subject while an erasure is in progress "
                    "(the terminal erased marker may only be cleared by this "
                    "authorized, audited path, never from a reentrant sink)"
                )
            entry = self._new_entry(
                actor=actor,
                action="reactivate",
                subject=subject,
                store="*",
                scope="1",
                result="reactivated",
                reviewer=None,
                reason=basis,
            )
            self._record(entry)  # audit the transition BEFORE clearing the marker
            self._erased.discard(subject)
        self._deliver(entry)

    # --- retention expiry --------------------------------------------------

    def purge_expired(self, now: int, *, actor: str) -> dict[str, int]:
        """Purge records whose retention period has elapsed by ``now``."""
        _require_actor(actor)
        purged: dict[str, int] = {}
        results: list[tuple[str, int]] = []
        with self._lock:
            for name, store in self._stores.items():
                expired = [
                    r
                    for r in store.all_records()
                    if r.created_at + store.policy.retention_ticks <= now
                ]
                for record in expired:
                    _scrub(record)
                    store.delete(record.subject, record.record_id)
                if expired:
                    purged[name] = len(expired)
                    results.append((name, len(expired)))
        for name, count in results:
            self._log(
                actor=actor,
                action="expire",
                subject="*",
                store=name,
                scope=str(count),
                result="purged",
                reviewer=None,
                reason=ReasonCode.RETENTION_EXPIRY.value,
            )
        return purged

    # --- audit -------------------------------------------------------------

    @property
    def audit_log(self) -> tuple[RightsAuditEntry, ...]:
        return tuple(self._audit)

    def audit_records(self) -> list[dict[str, object]]:
        return [entry.to_record() for entry in self._audit]

    def _new_entry(
        self,
        *,
        actor: str,
        action: str,
        subject: str,
        store: str,
        scope: str,
        result: str,
        reviewer: str | None,
        reason: str,
    ) -> RightsAuditEntry:
        return RightsAuditEntry(
            actor=actor,
            time=self._clock(),
            action=action,
            subject=subject,
            store=store,
            scope=scope,
            result=result,
            reviewer=reviewer,
            reason=reason,
        )

    def _record(self, entry: RightsAuditEntry) -> None:
        self._audit.append(entry)

    def _emit(self, entry: RightsAuditEntry) -> None:
        if self._sink is not None:
            self._sink(entry)

    def _deliver(self, entry: RightsAuditEntry) -> None:
        """Best-effort external delivery. The entry is ALREADY durably recorded
        in ``self._audit``; a sink exception is captured to the outbox so it can
        be retried, never propagated (a sink outage must not fail/reopen an erase).
        """
        try:
            self._emit(entry)
        except Exception:  # noqa: BLE001 — any sink failure is retryable, not fatal
            self._pending_delivery.append(entry)

    def _log(self, **fields: object) -> None:
        entry = self._new_entry(**fields)  # type: ignore[arg-type]
        self._record(entry)
        self._deliver(entry)

    @property
    def pending_audit_deliveries(self) -> int:
        """Count of audit entries whose external sink delivery has failed so far."""
        with self._lock:
            return len(self._pending_delivery)

    def retry_audit_delivery(self) -> int:
        """Re-attempt delivery of outbox entries; return how many are still pending.

        Only re-ships the durable audit record — it never changes erased state.
        """
        with self._lock:
            pending, self._pending_delivery = self._pending_delivery, []
        for entry in pending:
            self._deliver(entry)
        return self.pending_audit_deliveries


def _default_clock() -> Callable[[], int]:
    counter = itertools.count()
    return lambda: next(counter)


# --- A synthetic store catalogue (from the G1 data map) ---------------------

STORE_PRIMARY = "primary"
STORE_EMBEDDINGS = "embeddings"
STORE_CACHE = "cache"
STORE_FEEDBACK = "feedback"
STORE_HUMAN_REVIEW = "human_review"
STORE_JOBS = "jobs"

DEFAULT_STORE_POLICIES: tuple[StorePolicy, ...] = (
    StorePolicy(STORE_PRIMARY, "app-db://subjects", RetentionMode.HARD_DELETE, 730),
    StorePolicy(STORE_EMBEDDINGS, "vector-index://chunks", RetentionMode.HARD_DELETE, 730),
    StorePolicy(STORE_CACHE, "cache://responses", RetentionMode.HARD_DELETE, 7),
    StorePolicy(STORE_FEEDBACK, "feedback-db://entries", RetentionMode.HARD_DELETE, 365),
    StorePolicy(
        STORE_HUMAN_REVIEW,
        "review-queue://escalations",
        RetentionMode.TOMBSTONE,
        2555,  # ~7 years
        reason=ReasonCode.REGULATORY_RETENTION,
        requires_reviewer=True,
        description="retained for dispute resolution / regulatory defence",
    ),
    StorePolicy(STORE_JOBS, "jobs-db://index-jobs", RetentionMode.HARD_DELETE, 30),
)

# A recognisable marker so tests can prove raw content is gone after erasure.
RAW_MARKER = "raw-content-for"


def build_default_engine(
    *,
    clock: Callable[[], int] | None = None,
    sink: Callable[[RightsAuditEntry], None] | None = None,
) -> RightsEngine:
    engine = RightsEngine(clock=clock, sink=sink)
    for policy in DEFAULT_STORE_POLICIES:
        engine.register_store(policy)
    return engine


def seed_synthetic_subject(engine: RightsEngine, subject: str, *, created_at: int = 0) -> None:
    """Give ``subject`` one copy in every store (embeddings gets two chunks).

    Record ids are opaque tokens (``prefix_hex``) — the store keys by
    ``(subject, record_id)`` so the same ids reused across subjects stay distinct.
    """
    detail = {"detail": f"{RAW_MARKER}-{subject}"}
    engine.add_record(STORE_PRIMARY, subject, "profile_0", detail, created_at=created_at)
    engine.add_record(STORE_EMBEDDINGS, subject, "chunk_0", detail, created_at=created_at)
    engine.add_record(STORE_EMBEDDINGS, subject, "chunk_1", detail, created_at=created_at)
    engine.add_record(STORE_CACHE, subject, "resp_0", detail, created_at=created_at)
    engine.add_record(STORE_FEEDBACK, subject, "fb_0", detail, created_at=created_at)
    engine.add_record(STORE_HUMAN_REVIEW, subject, "esc_0", detail, created_at=created_at)
    engine.add_record(STORE_JOBS, subject, "job_0", detail, created_at=created_at)


# All stores that seed_synthetic_subject populates (for export assertions).
SEEDED_STORES: frozenset[str] = frozenset(
    {
        STORE_PRIMARY,
        STORE_EMBEDDINGS,
        STORE_CACHE,
        STORE_FEEDBACK,
        STORE_HUMAN_REVIEW,
        STORE_JOBS,
    }
)
