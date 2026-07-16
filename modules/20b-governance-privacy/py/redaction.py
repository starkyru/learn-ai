"""PII classification + redaction policy (Module 20b, Task 1).

Synthetic data only — nothing here is real. The lesson: classify every field a
feature touches, then REDACT anything above your allowed sensitivity *before*
the record can reach a prompt, a log line, a trace, or a third-party provider.

Habits worth internalising:

- **Fail closed.** A field the policy has never heard of — or one carrying an
  invalid/unknown class — is treated as ``restricted`` and dropped. ``restricted``
  is dropped UNCONDITIONALLY — no ``allow`` / ``mask`` / ``default_action``
  setting can forward it.
- **Restricted != masked.** Confidential fields can be masked to a placeholder
  when a hint is useful; genuinely restricted data (secrets, government ids)
  should not leave the boundary at all — drop the key entirely.
- **Only redacted data may egress.** :meth:`RedactionPolicy.redact` mints an
  immutable :class:`RedactedRecord` and records it in a private registry; the
  prompt builder accepts nothing else, so a caller cannot accidentally build a
  prompt from un-redacted (or later-mutated) input.

Scope: this is FIELD-NAME-level classification. It does NOT scan the *content*
of free-text values. A secret typed INTO an allowed free-text field (e.g. an SSN
inside ``support_topic`` prose), or a bare scalar sitting in a list with no key,
is NOT caught here — a production system needs content-level DLP for that, which
is a separate, larger, itself-imperfect concern outside this lesson's scope.
What this *does* guarantee is that nested structures are recursively classified
(with cycle + depth guards), so a restricted key hidden inside an allowed field's
object/array value cannot slip through (see :meth:`RedactionPolicy.redact`).

Honest boundary: the immutability / authenticity guards below prevent ACCIDENTAL
misuse, casual forgery, and post-creation mutation. They do NOT defend against a
hostile in-process caller that deliberately subclasses and overrides dunders or
reaches into module internals — that is impossible in an in-process language, and
such a caller can call the provider directly anyway.

This is engineering practice, not legal advice. See the module README's
"Important boundary" section.
"""

from __future__ import annotations

import hashlib
import weakref
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType

# The placeholder a masked value collapses to. Kept deliberately boring and
# fixed so downstream code (and tests) can recognise "this was redacted".
MASK_TOKEN = "***"

# Recursion bound for the redaction walkers. Any legitimate record is far
# shallower; a deeper (or cyclic) structure fails closed rather than blowing the
# stack — a denial-of-service guard on untrusted input.
MAX_REDACTION_DEPTH = 32


class DataClass(str, Enum):
    """Sensitivity lanes, least → most sensitive."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Action(str, Enum):
    """What redaction does to a field's value."""

    KEEP = "keep"  # pass the raw value through unchanged
    MASK = "mask"  # replace the value with MASK_TOKEN, keep the key
    DROP = "drop"  # remove the key entirely


# Ordering used only for human-readable reporting; the policy itself is driven
# by explicit set membership, not by rank comparisons.
SENSITIVITY_ORDER: tuple[DataClass, ...] = (
    DataClass.PUBLIC,
    DataClass.INTERNAL,
    DataClass.CONFIDENTIAL,
    DataClass.RESTRICTED,
)


def _deep_readonly(value: object) -> object:
    """Return a deep, read-only copy: mappings -> MappingProxyType, sequences ->
    tuples, scalars unchanged. Nothing in the result can be mutated in place."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: _deep_readonly(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_readonly(v) for v in value)
    return value


# Module-private construction token. Only redact() holds it, so RedactedRecord
# __init__ refuses casual direct construction.
_FACTORY_TOKEN = object()


class RedactedRecord(Mapping[str, object]):
    """A deeply-immutable mapping minted by :meth:`RedactionPolicy.redact`.

    Obtain one ONLY via ``redact()`` — direct construction raises. The backing
    store is a deep, read-only copy (nested mappings are ``MappingProxyType``,
    nested sequences are tuples), attribute assignment is blocked, and identity —
    not content — is used for equality/hash so instances can live in the private
    authenticity registry. Use :func:`is_redacted_record` to check authenticity;
    ``isinstance`` is deliberately NOT the check (it would admit subclasses).
    """

    __slots__ = ("_data", "__weakref__")

    # Identity semantics: a record equals only itself. (Content equality would
    # be inconsistent with an identity-keyed weakref registry.)
    __eq__ = object.__eq__
    __hash__ = object.__hash__

    def __init__(self, data: Mapping[str, object], *, _token: object = None) -> None:
        if _token is not _FACTORY_TOKEN:
            raise TypeError(
                "RedactedRecord cannot be constructed directly; obtain one from "
                "RedactionPolicy.redact()."
            )
        object.__setattr__(self, "_data", _deep_readonly(dict(data)))

    # Block post-construction mutation of the instance (including reassigning
    # the backing store).
    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("RedactedRecord is immutable")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("RedactedRecord is immutable")

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"RedactedRecord({dict(self._data)!r})"


# Private registry of authentic records. Authenticity is MEMBERSHIP here — not a
# reflected attribute a caller could copy onto a foreign object. Weak so records
# are collected normally.
_REDACTED_REGISTRY: weakref.WeakSet[RedactedRecord] = weakref.WeakSet()


def is_redacted_record(value: object) -> bool:
    """True only for a record minted by ``redact()``.

    Requires EXACT type (so a subclass is rejected) AND registry membership (so a
    token-constructed or otherwise-forged instance that never went through
    ``redact()`` is rejected). See the module docstring's honest boundary.
    """
    return type(value) is RedactedRecord and value in _REDACTED_REGISTRY


def _short_code(name: str) -> str:
    """A stable, non-plaintext code for an unexpected field NAME.

    Lets you correlate the same unknown key across runs without writing it in
    the clear. For low-entropy names a hash is correlatable, not anonymous — the
    point is only to keep a raw (possibly PII) key out of the log.
    """
    return hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True)
class RedactionPolicy:
    """Maps field names to a :class:`DataClass`, then to a redaction action.

    ``allow`` classes pass through verbatim; ``mask`` classes collapse to
    :data:`MASK_TOKEN`; known non-restricted classes in neither set take
    ``default_action``. ``RESTRICTED`` — including any field missing from
    ``classification`` or carrying an invalid class — is ALWAYS dropped, whatever
    ``default_action`` says. A policy that tries to ``allow`` or ``mask``
    ``RESTRICTED`` is rejected. The classification map and action sets are
    defensively copied + frozen at construction, so mutating the caller's objects
    afterwards cannot reclassify a field.
    """

    classification: Mapping[str, DataClass]
    allow: frozenset[DataClass] = field(
        default_factory=lambda: frozenset({DataClass.PUBLIC, DataClass.INTERNAL})
    )
    mask: frozenset[DataClass] = field(default_factory=lambda: frozenset({DataClass.CONFIDENTIAL}))
    default_action: Action = Action.DROP

    def __post_init__(self) -> None:
        # Fail loud on a misconfiguration that would try to forward restricted
        # data. (The action logic below also enforces this defensively.)
        if DataClass.RESTRICTED in (frozenset(self.allow) | frozenset(self.mask)):
            raise ValueError(
                "RESTRICTED data is always dropped; it must not appear in `allow` or `mask`."
            )
        # Defensive copy + freeze: a later mutation of the caller's classification
        # map / sets (or the exported CLASSIFICATION) cannot reclassify a field.
        object.__setattr__(self, "classification", MappingProxyType(dict(self.classification)))
        object.__setattr__(self, "allow", frozenset(self.allow))
        object.__setattr__(self, "mask", frozenset(self.mask))

    def classify(self, field_name: str) -> DataClass:
        data_class = self.classification.get(field_name)
        # Missing OR an invalid/unknown runtime class -> restricted. Fail closed.
        return data_class if isinstance(data_class, DataClass) else DataClass.RESTRICTED

    def action_for(self, field_name: str) -> Action:
        data_class = self.classify(field_name)
        # Restricted (incl. unknown -> restricted) is dropped unconditionally,
        # independent of allow / mask / default_action.
        if data_class is DataClass.RESTRICTED:
            return Action.DROP
        if data_class in self.allow:
            return Action.KEEP
        if data_class in self.mask:
            return Action.MASK
        # Only KNOWN, non-restricted classes reach the configurable default.
        return self.default_action

    def redact(self, record: Mapping[str, object]) -> RedactedRecord:
        """Mint an immutable :class:`RedactedRecord` safe to send onward.

        Keeps allowed fields, masks masked fields, drops the rest. A KEEP field
        whose value is non-scalar is redacted RECURSIVELY (see
        :meth:`_walk_value`) so a restricted key nested inside an allowed field's
        object/array value cannot leak. Recursion is bounded and cycle-guarded.
        The input is never mutated; the result is registered as authentic.
        """
        walked = self._walk_mapping(record, depth=0, seen=frozenset({id(record)}))
        result = RedactedRecord(walked, _token=_FACTORY_TOKEN)
        _REDACTED_REGISTRY.add(result)
        return result

    def _walk_mapping(
        self, record: Mapping[str, object], depth: int, seen: frozenset[int]
    ) -> dict[str, object]:
        if depth > MAX_REDACTION_DEPTH:
            return {}  # over-depth -> fail closed (drop the whole sub-tree)
        out: dict[str, object] = {}
        for key, value in record.items():
            action = self.action_for(key)
            if action is Action.KEEP:
                out[key] = self._walk_value(value, depth + 1, seen)
            elif action is Action.MASK:
                # Collapse the whole (possibly nested) value — nothing survives.
                out[key] = MASK_TOKEN
            # Action.DROP -> omit the key entirely.
        return out

    def _walk_value(self, value: object, depth: int, seen: frozenset[int]) -> object:
        """Recursively make a KEEP-class value safe.

        - Scalars (str/int/float/bool/None) pass through unchanged.
        - Mappings are re-classified key-by-key with this same policy.
        - Lists/tuples are redacted element-wise.
        - Over-depth, a reference cycle, or an un-classifiable shape (set, bytes,
          custom object) all fail closed to MASK_TOKEN.
        """
        if depth > MAX_REDACTION_DEPTH:
            return MASK_TOKEN
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Mapping):
            if id(value) in seen:  # ancestor cycle -> fail closed
                return MASK_TOKEN
            return self._walk_mapping(value, depth, seen | {id(value)})
        if isinstance(value, (list, tuple)):
            if id(value) in seen:  # ancestor cycle -> fail closed
                return MASK_TOKEN
            child_seen = seen | {id(value)}
            return [self._walk_value(item, depth + 1, child_seen) for item in value]
        # Un-classifiable shape — do not pass raw. Fail closed.
        return MASK_TOKEN

    def known_field_actions(self, record: Mapping[str, object]) -> dict[str, str]:
        """Actions for KNOWN (classified) field names only — safe to log.

        Unknown field NAMES are omitted because a user-supplied key can itself be
        PII (e.g. an email used as a key); summarise those with
        :meth:`unknown_field_digest` instead.
        """
        return {k: self.action_for(k).value for k in record if k in self.classification}

    def unknown_field_digest(self, record: Mapping[str, object]) -> dict[str, object]:
        """Non-reversible summary of UNKNOWN field names — never the raw key."""
        unknown = [k for k in record if k not in self.classification]
        return {"count": len(unknown), "codes": sorted(_short_code(k) for k in unknown)}

    def dropped_fields(self, record: Mapping[str, object]) -> list[str]:
        """Field names redaction removes entirely (sorted).

        WARNING: this returns RAW keys, including unknown/untrusted ones. Use it
        only where keys are trusted schema names; do NOT log it verbatim for
        arbitrary input (use :meth:`unknown_field_digest` there).
        """
        return sorted(k for k in record if self.action_for(k) is Action.DROP)

    def field_actions(self, record: Mapping[str, object]) -> dict[str, str]:
        """Per-field {name: action} map over ALL keys, including raw unknown ones.

        WARNING: same caveat as :meth:`dropped_fields` — raw keys. For logging
        untrusted input, prefer :meth:`known_field_actions` +
        :meth:`unknown_field_digest`.
        """
        return {k: self.action_for(k).value for k in record}


# --- A concrete synthetic subject + the default policy for the demo ---------
#
# Every value below is fabricated. The SSN, phone, and token are not valid and
# point at reserved/example ranges on purpose.

CLASSIFICATION: dict[str, DataClass] = {
    "subject_id": DataClass.INTERNAL,  # pseudonymous stable id — safe to log/join
    "support_topic": DataClass.PUBLIC,  # the actual task text the model needs
    "locale": DataClass.PUBLIC,  # affects wording, not identity
    "display_name": DataClass.CONFIDENTIAL,  # direct identifier — mask it
    "email": DataClass.CONFIDENTIAL,
    "phone": DataClass.CONFIDENTIAL,
    "ssn": DataClass.RESTRICTED,  # government id — must never egress
    "date_of_birth": DataClass.RESTRICTED,
    "auth_token": DataClass.RESTRICTED,  # secret — must never egress
}

DEFAULT_POLICY = RedactionPolicy(classification=CLASSIFICATION)

SYNTHETIC_SUBJECT: dict[str, str] = {
    "subject_id": "subj_0007",
    "support_topic": "How do I export my invoices for last quarter?",
    "locale": "en-US",
    "display_name": "Jordan Rivera",
    "email": "jordan.rivera@example.invalid",
    "phone": "+1-555-0142",
    "ssn": "123-45-6789",
    "date_of_birth": "1990-04-12",
    "auth_token": "sk-fake-DO-NOT-USE-abcdef123456",
}
