"""Tests for the PII redaction policy + proof-of-redaction demo (Module 20b).

The load-bearing test proves that a *restricted* field's raw value reaches
NONE of the three egress surfaces — the prompt, the provider call, or the
structured log — while an allowed field survives and a confidential field is
recoverable only as the mask token. The provider is a real fake at the network
boundary; logs are captured with a real logging handler. No production logic is
re-implemented here.

Run:
    uv run pytest modules/20b-governance-privacy/py/test_redaction.py
"""

from __future__ import annotations

import json
import logging
from types import MappingProxyType

import pytest
from demo_redaction import LOGGER_NAME, build_prompt, run_redaction_demo
from fakes import RecordingProvider
from redaction import (
    _FACTORY_TOKEN,
    CLASSIFICATION,
    DEFAULT_POLICY,
    MASK_TOKEN,
    MAX_REDACTION_DEPTH,
    SYNTHETIC_SUBJECT,
    Action,
    DataClass,
    RedactedRecord,
    RedactionPolicy,
    is_redacted_record,
)

# --- pure policy behaviour ------------------------------------------------


def test_redact_masks_confidential_and_drops_restricted() -> None:
    redacted = DEFAULT_POLICY.redact(SYNTHETIC_SUBJECT)

    # Restricted -> removed entirely (key gone).
    for restricted in ("ssn", "date_of_birth", "auth_token"):
        assert restricted not in redacted

    # Confidential -> masked to the exact placeholder.
    assert redacted["email"] == "***"
    assert redacted["display_name"] == "***"
    assert redacted["phone"] == "***"

    # Allowed classes -> kept verbatim.
    assert redacted["support_topic"] == SYNTHETIC_SUBJECT["support_topic"]
    assert redacted["subject_id"] == "subj_0007"
    assert redacted["locale"] == "en-US"


def test_mask_token_is_exactly_three_stars() -> None:
    # Guards the mask format the rest of the system recognises.
    assert MASK_TOKEN == "***"


def test_unknown_field_fails_closed() -> None:
    # A field the policy never classified is treated as the most sensitive class.
    assert DEFAULT_POLICY.classify("mystery_field") is DataClass.RESTRICTED
    assert DEFAULT_POLICY.action_for("mystery_field") is Action.DROP
    # Identity equality now — compare the plain view.
    assert dict(DEFAULT_POLICY.redact({"mystery_field": "surprise"})) == {}


def test_redact_does_not_mutate_input() -> None:
    original = dict(SYNTHETIC_SUBJECT)
    DEFAULT_POLICY.redact(SYNTHETIC_SUBJECT)
    assert SYNTHETIC_SUBJECT == original


def test_dropped_fields_lists_exactly_the_restricted_keys() -> None:
    assert DEFAULT_POLICY.dropped_fields(SYNTHETIC_SUBJECT) == [
        "auth_token",
        "date_of_birth",
        "ssn",
    ]


def test_configurable_policy_can_widen_or_narrow() -> None:
    # Same data, stricter policy: confidential is dropped, not masked.
    strict = RedactionPolicy(
        classification=DEFAULT_POLICY.classification,
        allow=frozenset({DataClass.PUBLIC}),
        mask=frozenset(),
    )
    redacted = strict.redact(SYNTHETIC_SUBJECT)
    assert "email" not in redacted  # confidential now dropped
    assert "subject_id" not in redacted  # internal no longer allowed
    assert redacted["support_topic"] == SYNTHETIC_SUBJECT["support_topic"]


# --- proof of redaction across every egress surface -----------------------


class _ListHandler(logging.Handler):
    """A real logging handler that keeps every formatted line in memory."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@pytest.fixture
def captured_logs() -> list[str]:
    logger = logging.getLogger(LOGGER_NAME)
    handler = _ListHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    prev_level, prev_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield handler.lines
    finally:
        # Resource cleanup: detach and close the handler, restore logger state.
        logger.removeHandler(handler)
        handler.close()
        logger.setLevel(prev_level)
        logger.propagate = prev_propagate


def test_restricted_value_reaches_no_egress_surface(captured_logs: list[str]) -> None:
    provider = RecordingProvider()
    logger = logging.getLogger(LOGGER_NAME)

    result = run_redaction_demo(SYNTHETIC_SUBJECT, provider, logger=logger)

    # Exactly one provider call happened.
    assert len(provider.calls) == 1
    provider_text = " ".join(m.content for m in provider.recorded_messages)
    log_text = "\n".join(captured_logs)

    raw_ssn = SYNTHETIC_SUBJECT["ssn"]
    raw_dob = SYNTHETIC_SUBJECT["date_of_birth"]
    raw_token = SYNTHETIC_SUBJECT["auth_token"]
    raw_email = SYNTHETIC_SUBJECT["email"]

    # (1) restricted raw values appear on NO surface: prompt, provider, or log.
    for surface in (result.prompt, provider_text, log_text):
        assert raw_ssn not in surface
        assert raw_dob not in surface
        assert raw_token not in surface
        # confidential raw value is likewise absent (it was masked).
        assert raw_email not in surface

    # (2) a redacted field is recoverable only as the mask token.
    assert MASK_TOKEN in result.prompt
    assert MASK_TOKEN in provider_text
    assert MASK_TOKEN in log_text

    # (3) an allowed field IS present verbatim on the outward surfaces.
    topic = SYNTHETIC_SUBJECT["support_topic"]
    assert topic in result.prompt
    assert topic in provider_text
    assert topic in log_text

    # The pseudonymous id is deliberately retained (useful, low-risk join key).
    assert "subj_0007" in log_text
    # The restricted *keys* never reach the prompt either.
    assert "ssn" not in result.prompt


def test_structured_log_is_json_with_action_audit(captured_logs: list[str]) -> None:
    provider = RecordingProvider()
    run_redaction_demo(SYNTHETIC_SUBJECT, provider, logger=logging.getLogger(LOGGER_NAME))

    assert len(captured_logs) == 1
    entry = json.loads(captured_logs[0])

    assert entry["event"] == "llm_request"
    assert entry["provider"] == "fake-recording"
    # Audit map records the action per field by NAME (names are safe to log).
    assert entry["field_actions"]["ssn"] == "drop"
    assert entry["field_actions"]["email"] == "mask"
    assert entry["field_actions"]["support_topic"] == "keep"
    assert entry["dropped_fields"] == ["auth_token", "date_of_birth", "ssn"]
    # The logged redacted record carries no restricted key and masks confidential.
    assert "ssn" not in entry["redacted"]
    assert entry["redacted"]["email"] == "***"


def test_nested_restricted_value_does_not_leak(captured_logs: list[str]) -> None:
    # Regression: a KEEP-class field whose value is a nested object must not
    # carry restricted content through. The nested "leaked_ssn"/"text" keys are
    # unclassified -> fail closed -> dropped; nested "locale" is allowed -> kept.
    provider = RecordingProvider()
    nested = {
        "support_topic": {
            "text": "reset password",
            "leaked_ssn": "999-99-9999",
            "locale": "en-US",
        },
        "subject_id": "subj_0007",
    }

    result = run_redaction_demo(nested, provider, logger=logging.getLogger(LOGGER_NAME))

    provider_text = " ".join(m.content for m in provider.recorded_messages)
    log_text = "\n".join(captured_logs)

    for surface in (result.prompt, provider_text, log_text):
        assert "999-99-9999" not in surface
        assert "leaked_ssn" not in surface

    # Recursion classified nested keys: only the allowed nested scalar survives.
    assert result.redacted["support_topic"] == {"locale": "en-US"}
    assert "en-US" in result.prompt
    # And the top-level allowed scalar is still there.
    assert result.redacted["subject_id"] == "subj_0007"


def test_nested_value_in_mask_and_list_fields_fails_closed() -> None:
    # A MASK field collapses whole, even when nested; a KEEP list is redacted
    # element-wise (nested restricted keys inside list items are dropped).
    record = {
        "email": {"primary": "jordan@example.invalid"},  # confidential -> mask whole
        "support_topic": [
            {"note": "hi", "ssn": "111-11-1111"},  # nested restricted key dropped
            "plain string",  # scalar element kept
        ],
    }
    redacted = DEFAULT_POLICY.redact(record)
    assert redacted["email"] == "***"
    # KEEP list -> read-only tuple; the nested restricted key was dropped.
    assert redacted["support_topic"] == ({}, "plain string")


def test_build_prompt_renders_a_redacted_record() -> None:
    # The only accepted input is a RedactedRecord from redact().
    redacted = DEFAULT_POLICY.redact(
        {
            "support_topic": "reset my password",
            "email": "x@example.invalid",
            "locale": "en-US",
        }
    )
    prompt = build_prompt(redacted)
    assert "support_topic: reset my password" in prompt
    assert "email: ***" in prompt  # confidential masked
    assert "locale: en-US" in prompt
    assert "x@example.invalid" not in prompt


# --- fail-closed configuration (Codex item 1) -----------------------------


def test_restricted_dropped_even_when_default_action_is_keep() -> None:
    # default_action=KEEP must NOT forward restricted/unknown fields.
    loose = RedactionPolicy(
        classification={},
        allow=frozenset(),
        mask=frozenset(),
        default_action=Action.KEEP,
    )
    assert loose.action_for("api_key") is Action.DROP  # unknown -> restricted
    assert dict(loose.redact({"api_key": "secret123"})) == {}


def test_policy_rejects_restricted_in_allow_or_mask() -> None:
    with pytest.raises(ValueError, match="RESTRICTED"):
        RedactionPolicy(
            classification={"ssn": DataClass.RESTRICTED},
            allow=frozenset({DataClass.RESTRICTED}),
        )
    with pytest.raises(ValueError, match="RESTRICTED"):
        RedactionPolicy(classification={}, mask=frozenset({DataClass.RESTRICTED}))


# --- prompt builder only accepts redacted data (Codex item 2) -------------


def test_build_prompt_rejects_raw_dict() -> None:
    # A plain (un-redacted) dict must be refused, so a prompt cannot be built
    # from data that never passed through the policy.
    with pytest.raises(TypeError, match="RedactedRecord"):
        build_prompt({"support_topic": "hi", "ssn": "123-45-6789"})  # type: ignore[arg-type]


# --- cycle / depth guards (Codex item 3) ----------------------------------


def test_cyclic_input_fails_closed_without_crash() -> None:
    cyclic: dict[str, object] = {}
    cyclic["support_topic"] = cyclic  # KEEP field references itself
    redacted = DEFAULT_POLICY.redact(cyclic)
    # The cycle is detected and collapsed to the mask token — no RecursionError.
    assert redacted["support_topic"] == MASK_TOKEN


def test_deeply_nested_input_is_bounded() -> None:
    deep: dict[str, object] = {}
    current = deep
    for _ in range(MAX_REDACTION_DEPTH + 50):
        child: dict[str, object] = {}
        current["support_topic"] = child
        current = child
    # Must complete without RecursionError; the depth guard trips somewhere,
    # leaving a mask token rather than recursing without bound. build_prompt
    # serialises the whole (read-only) tree, so the mask surfaces there.
    redacted = DEFAULT_POLICY.redact(deep)
    assert MASK_TOKEN in build_prompt(redacted)


# --- do not log raw untrusted keys (Codex item 4) -------------------------


def test_pii_used_as_key_is_not_logged_raw(captured_logs: list[str]) -> None:
    provider = RecordingProvider()
    record = {"alice@example.com": "some value", "support_topic": "hello"}

    result = run_redaction_demo(record, provider, logger=logging.getLogger(LOGGER_NAME))

    log_text = "\n".join(captured_logs)
    provider_text = " ".join(m.content for m in provider.recorded_messages)

    # The PII-shaped key and its dropped value appear on NO surface.
    for surface in (result.prompt, provider_text, log_text):
        assert "alice@example.com" not in surface
        assert "some value" not in surface

    # ...but the log still records that one unknown field was present.
    entry = json.loads(captured_logs[0])
    assert entry["unknown_fields"]["count"] == 1
    assert entry["unknown_fields"]["codes"]  # a stable non-reversible code, not the key


def test_unusual_unknown_key_dropped_and_not_logged(captured_logs: list[str]) -> None:
    provider = RecordingProvider()
    weird = "'; DROP TABLE users;--"
    record = {weird: "x", "support_topic": "hi"}

    result = run_redaction_demo(record, provider, logger=logging.getLogger(LOGGER_NAME))

    log_text = "\n".join(captured_logs)
    assert weird not in log_text
    assert weird not in result.prompt


# --- stronger adversarial fixtures (Codex item 5) -------------------------


def test_known_restricted_key_nested_under_allowed_is_dropped(
    captured_logs: list[str],
) -> None:
    # Proves recursion catches a KNOWN-restricted key (ssn), not only unknowns.
    provider = RecordingProvider()
    record = {
        "support_topic": {"ssn": "222-22-2222", "locale": "en-US"},
        "subject_id": "s",
    }

    result = run_redaction_demo(record, provider, logger=logging.getLogger(LOGGER_NAME))

    provider_text = " ".join(m.content for m in provider.recorded_messages)
    log_text = "\n".join(captured_logs)
    for surface in (result.prompt, provider_text, log_text):
        assert "222-22-2222" not in surface
    assert result.redacted["support_topic"] == {"locale": "en-US"}


def test_numeric_scalar_kept_and_numeric_restricted_dropped() -> None:
    record = {"support_topic": {"locale": 42, "ssn": 999999}}
    redacted = DEFAULT_POLICY.redact(record)
    # Numeric scalar under an allowed key survives; numeric restricted dropped.
    assert redacted["support_topic"] == {"locale": 42}


# --- documented limitation: NOT content scanning (Codex item 6) -----------


def test_secret_in_free_text_allowed_value_is_not_redacted() -> None:
    # DOCUMENTED LIMITATION (see module docstring): field-name classification
    # cannot catch a secret typed INTO an allowed free-text value. This is NOT
    # content/DLP scanning; real DLP is a separate concern. We assert the secret
    # SURVIVES so the limitation is honest and visible, not a false guarantee.
    record = {"support_topic": "my ssn is 555-55-5555", "subject_id": "s"}
    redacted = DEFAULT_POLICY.redact(record)
    assert "555-55-5555" in redacted["support_topic"]


# --- immutable + forgery-resistant RedactedRecord (Codex round 2) ----------


def test_redacted_record_cannot_be_constructed_directly() -> None:
    # Forging a "redacted" record from raw data must fail — only redact() can
    # mint one (it holds the private factory token).
    with pytest.raises(TypeError, match="cannot be constructed directly"):
        RedactedRecord({"auth_token": "secret"})


def test_redacted_record_is_read_only() -> None:
    redacted = DEFAULT_POLICY.redact({"support_topic": "hello"})

    # The Mapping interface exposes no setter: item assignment raises.
    with pytest.raises(TypeError):
        redacted["ssn"] = "111-11-1111"  # type: ignore[index]

    # The internal store is a read-only, deep-copied proxy — not a plain dict a
    # caller could reach in and mutate.
    assert isinstance(redacted._data, MappingProxyType)
    with pytest.raises(TypeError):
        redacted._data["ssn"] = "111-11-1111"  # type: ignore[index]

    # After the failed mutation attempts, no restricted field can have appeared.
    assert build_prompt(redacted).find("111-11-1111") == -1


# --- registry authenticity + deep immutability (Codex round 3) -------------


def test_redacted_record_data_cannot_be_reassigned() -> None:
    redacted = DEFAULT_POLICY.redact({"support_topic": "hello"})
    # The backing store is write-once — attribute assignment is blocked.
    with pytest.raises(AttributeError):
        redacted._data = {}  # type: ignore[misc]


def test_nested_containers_are_deeply_read_only() -> None:
    redacted = DEFAULT_POLICY.redact({"support_topic": {"locale": "en-US"}, "subject_id": "s"})
    nested = redacted["support_topic"]
    assert isinstance(nested, MappingProxyType)
    # Mutating a nested mapping cannot smuggle a field back into the prompt.
    with pytest.raises(TypeError):
        nested["ssn"] = "111-11-1111"  # type: ignore[index]
    assert "111-11-1111" not in build_prompt(redacted)


def test_subclass_instance_is_rejected_by_build_prompt() -> None:
    # Authenticity is an EXACT-type check (not isinstance), so a subclass — even
    # one built with the factory token — is rejected.
    class Sneaky(RedactedRecord):
        pass

    sneaky = Sneaky({"ssn": "111-11-1111"}, _token=_FACTORY_TOKEN)
    assert not is_redacted_record(sneaky)
    with pytest.raises(TypeError, match="RedactedRecord"):
        build_prompt(sneaky)


def test_token_constructed_record_not_in_registry_is_rejected() -> None:
    # A genuine RedactedRecord built directly with the token (bypassing redact())
    # is NOT authentic — authenticity is registry membership, not the token.
    forged = RedactedRecord({"ssn": "111-11-1111"}, _token=_FACTORY_TOKEN)
    assert type(forged) is RedactedRecord
    assert not is_redacted_record(forged)  # never registered by redact()
    with pytest.raises(TypeError, match="RedactedRecord"):
        build_prompt(forged)


def test_classification_mutation_after_construction_cannot_reclassify() -> None:
    cls = {"ssn": DataClass.RESTRICTED, "support_topic": DataClass.PUBLIC}
    policy = RedactionPolicy(classification=cls)
    # Mutate the caller's map after construction.
    cls["ssn"] = DataClass.PUBLIC
    assert policy.action_for("ssn") is Action.DROP  # the frozen copy is unaffected
    assert policy.classification is not cls
    assert isinstance(policy.classification, MappingProxyType)


def test_exported_classification_is_defensively_copied() -> None:
    # DEFAULT_POLICY holds a copy, so mutating the exported CLASSIFICATION cannot
    # reclassify a restricted field.
    assert DEFAULT_POLICY.classification is not CLASSIFICATION
    assert isinstance(DEFAULT_POLICY.classification, MappingProxyType)
    assert DEFAULT_POLICY.action_for("ssn") is Action.DROP


def test_invalid_runtime_class_fails_closed() -> None:
    # A classification value that isn't a DataClass is treated as restricted,
    # even under default_action=KEEP.
    bad = RedactionPolicy(
        classification={"weird": "banana"},  # type: ignore[dict-item]
        default_action=Action.KEEP,
    )
    assert bad.classify("weird") is DataClass.RESTRICTED
    assert bad.action_for("weird") is Action.DROP
