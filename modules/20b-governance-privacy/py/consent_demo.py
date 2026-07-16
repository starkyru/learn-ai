"""Consent + lawful-basis demo (Module 20b, Task 2).

Walks one synthetic subject through: register activities -> capture consent ->
authorise several purposes -> withdraw consent -> re-authorise. It prints each
decision and structured-logs the audit trail, then shows consent GATING an
actual (fake) model call. Deterministic and offline.

Run it::

    uv run python modules/20b-governance-privacy/py/consent_demo.py

Not legal advice — see the module README.
"""

from __future__ import annotations

import json
import logging

from consent import (
    PURPOSE_ACCOUNT_SECURITY,
    PURPOSE_MARKETING_EMAIL,
    PURPOSE_ORDER_FULFILMENT,
    PURPOSE_PRODUCT_ANALYTICS,
    AuditEntry,
    build_default_engine,
)
from fakes import RecordingProvider
from llm_core import ChatMessage, ChatOptions

LOGGER_NAME = "m20b.consent"

# A pseudonymous subject id (never a raw identifier).
SUBJECT = "subj_0042"
ACTOR = "privacy-service"


def _make_sink(logger: logging.Logger):
    def sink(entry: AuditEntry) -> None:
        logger.info(json.dumps(entry.to_record(), sort_keys=True))

    return sink


def _describe(engine, subject: str, purpose: str) -> str:
    decision = engine.can_process(subject, purpose, actor=ACTOR)
    verb = "ALLOW" if decision.allowed else "DENY "
    basis = decision.basis.value if decision.basis is not None else "-"
    return f"  {verb} {purpose:<18} basis={basis:<16} {decision.reason}"


def run_demo(logger: logging.Logger | None = None) -> None:
    log = logger or logging.getLogger(LOGGER_NAME)
    engine = build_default_engine(sink=_make_sink(log))

    # The subject opts in to marketing and to the optional account-security check.
    engine.capture_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR, version="2026.07.01")
    engine.capture_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, actor=ACTOR, version="2026.07.01")

    print("\nAfter capturing consent (marketing + account_security):")
    for purpose in (
        PURPOSE_MARKETING_EMAIL,
        PURPOSE_ORDER_FULFILMENT,  # contract — no consent needed
        PURPOSE_PRODUCT_ANALYTICS,  # consent-only, never granted -> deny
        PURPOSE_ACCOUNT_SECURITY,  # allowed via consent (contract also present)
    ):
        print(_describe(engine, SUBJECT, purpose))

    # A consent-gated processing call: draft a marketing email ONLY if allowed.
    _gated_marketing_draft(engine, log)

    # The subject withdraws consent for both purposes.
    engine.withdraw_consent(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)
    engine.withdraw_consent(SUBJECT, PURPOSE_ACCOUNT_SECURITY, actor=ACTOR)

    print("\nAfter withdrawing consent for both:")
    for purpose in (PURPOSE_MARKETING_EMAIL, PURPOSE_ACCOUNT_SECURITY):
        print(_describe(engine, SUBJECT, purpose))
    print(
        "  ^ marketing is now DENIED (consent-only); account_security is STILL "
        "ALLOWED under contract — withdrawal did not revoke the other basis."
    )

    print(f"\nAudit log holds {len(engine.audit_log)} records (see the JSON lines above).")


def _gated_marketing_draft(engine, log: logging.Logger) -> None:
    decision = engine.can_process(SUBJECT, PURPOSE_MARKETING_EMAIL, actor=ACTOR)
    if not decision.allowed:
        print("\n[gated call] marketing draft SKIPPED — not authorised.")
        return
    provider = RecordingProvider()
    messages = [
        ChatMessage("system", "You draft short, opt-in marketing emails."),
        ChatMessage("user", f"Draft a one-line note for subject {SUBJECT}."),
    ]
    result = provider.chat(messages, ChatOptions(temperature=0, max_tokens=64))
    print(f"\n[gated call] authorised by {decision.basis.value}; model said: {result.text}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_demo()


if __name__ == "__main__":
    main()
