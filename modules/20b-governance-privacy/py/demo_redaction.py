"""Proof-of-redaction demo (Module 20b, Task 1).

Pipeline: redact a synthetic subject record -> build a prompt from ONLY the
survivors -> structured-log the request -> "send" it to a provider. The provider
is the shared ``llm_core`` interface; a deterministic ``RecordingProvider`` is
injected so the run is offline and a test can inspect what crossed the boundary.

Run it::

    uv run python modules/20b-governance-privacy/py/demo_redaction.py
    uv run python modules/20b-governance-privacy/py/demo_redaction.py --real  # uses get_provider()

Not legal advice — see the module README.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from fakes import RecordingProvider
from llm_core import ChatMessage, ChatOptions
from redaction import (
    DEFAULT_POLICY,
    SYNTHETIC_SUBJECT,
    RedactedRecord,
    RedactionPolicy,
    is_redacted_record,
)

LOGGER_NAME = "m20b.redaction"

SYSTEM_PROMPT = (
    "You are a customer-support assistant. Use only the fields provided between "
    "the <subject_fields> tags. Do not ask for or infer any identifier that is "
    "not present."
)


@dataclass
class DemoResult:
    redacted: RedactedRecord
    prompt: str
    messages: list[ChatMessage]
    reply: str
    dropped: list[str]


def _to_jsonable(value: object) -> object:
    """Convert a (read-only) redacted value to a JSON-serialisable form.

    A RedactedRecord's nested values are ``MappingProxyType`` / tuples, which
    ``json`` cannot encode directly — turn them back into dicts / lists.
    """
    if isinstance(value, Mapping):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def _render(value: object) -> str:
    """Serialise a (already-redacted) value for the prompt line.

    Non-scalars are JSON-encoded so a surviving nested field is visible rather
    than rendered as an opaque object repr.
    """
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(_to_jsonable(value), sort_keys=True)
    return str(value)


def build_prompt(redacted: RedactedRecord) -> str:
    """Assemble a prompt from an already-redacted record.

    Requires a :class:`RedactedRecord` (produced only by
    :meth:`RedactionPolicy.redact`) so a caller cannot build a prompt directly
    from un-redacted data. Values live inside a labelled, delimited block; with
    real (non-synthetic) input you would additionally escape/validate values so
    a field cannot forge the closing delimiter (a prompt-injection safeguard).
    """
    # Authenticity = minted by redact() (exact type + registry membership), not
    # isinstance. Honest scope: an in-process adversary can bypass this by calling
    # the provider directly; the guard catches ACCIDENTAL misuse and casual
    # forgery — building a prompt from data that never went through redact().
    if not is_redacted_record(redacted):
        raise TypeError(
            "build_prompt requires a RedactedRecord from RedactionPolicy.redact(); "
            f"refusing un-redacted {type(redacted).__name__}."
        )
    body = "\n".join(f"- {key}: {_render(value)}" for key, value in sorted(redacted.items()))
    return (
        "<subject_fields>\n"
        f"{body}\n"
        "</subject_fields>\n"
        "Answer the subject's support_topic in one short paragraph."
    )


def run_redaction_demo(
    record: Mapping[str, object],
    provider: object,
    *,
    policy: RedactionPolicy = DEFAULT_POLICY,
    logger: logging.Logger | None = None,
) -> DemoResult:
    """Redact ``record``, log the request, and send it through ``provider``.

    ``provider`` must satisfy the shared ``LLMProvider`` interface (a real client
    from ``get_provider()`` or an injected fake). Nothing above the allowed
    sensitivity is placed in the prompt, the log, or the provider call.
    """
    log = logger or logging.getLogger(LOGGER_NAME)

    redacted = policy.redact(record)
    prompt = build_prompt(redacted)
    messages = [
        ChatMessage("system", SYSTEM_PROMPT),
        ChatMessage("user", prompt),
    ]

    # Audit only KNOWN (schema) field names — a user-supplied key may itself be
    # PII, so unknown keys are summarised as a count + non-reversible codes and
    # never written raw. `dropped` lists only known dropped fields for the same
    # reason.
    known_actions = policy.known_field_actions(record)
    dropped = sorted(name for name, action in known_actions.items() if action == "drop")

    # Structured request log: known field names + actions, the unknown-field
    # digest, and the already-redacted record (masked/kept values only; dropped
    # and restricted values are, by construction, absent).
    log.info(
        json.dumps(
            {
                "event": "llm_request",
                "provider": getattr(provider, "name", "unknown"),
                "model": getattr(provider, "chat_model", "unknown"),
                "field_actions": known_actions,
                "dropped_fields": dropped,
                "unknown_fields": policy.unknown_field_digest(record),
                "redacted": _to_jsonable(redacted),
                "prompt_chars": len(prompt),
            },
            sort_keys=True,
        )
    )

    result = provider.chat(messages, ChatOptions(temperature=0, max_tokens=256))
    return DemoResult(
        redacted=redacted,
        prompt=prompt,
        messages=messages,
        reply=result.text,
        dropped=dropped,
    )


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real",
        action="store_true",
        help="use the shared client get_provider() instead of the offline fake",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.real:
        from llm_core import get_provider

        provider: object = get_provider()
    else:
        provider = RecordingProvider()

    result = run_redaction_demo(SYNTHETIC_SUBJECT, provider)

    print("\n--- dropped (never left the boundary) ---")
    print(", ".join(result.dropped))
    print("\n--- prompt actually sent ---")
    print(result.prompt)
    print("\n--- provider reply ---")
    print(result.reply)


if __name__ == "__main__":
    _main()
