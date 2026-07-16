"""Data-subject rights demo (Module 20b, Task 2).

Seeds one synthetic subject across every store, then: EXPORTS a manifest of all
copies -> ERASES (hard-delete where allowed, tombstone where a retention
exception applies, with a reviewer) -> exports again to show what remains ->
PURGES a past-retention record. Every action is structured-logged. Deterministic
and offline.

Run it::

    uv run python modules/20b-governance-privacy/py/rights_demo.py

Not legal advice — see the module README.
"""

from __future__ import annotations

import json
import logging

from rights import (
    RightsAuditEntry,
    build_default_engine,
    seed_synthetic_subject,
)

LOGGER_NAME = "m20b.rights"

SUBJECT = "subj_0007"
ACTOR = "privacy-service"
REVIEWER = "legal-team"


def _make_sink(logger: logging.Logger):
    def sink(entry: RightsAuditEntry) -> None:
        logger.info(json.dumps(entry.to_record(), sort_keys=True))

    return sink


def _print_manifest(engine, label: str) -> None:
    manifest = engine.export(SUBJECT, actor=ACTOR)
    print(f"\n{label} — {len(manifest.copies)} copies:")
    for copy in sorted(manifest.copies, key=lambda c: (c.store, c.record_id)):
        flag = " (TOMBSTONE)" if copy.tombstoned else ""
        print(f"  {copy.store:<13} {copy.location:<28} {copy.record_id}{flag}")


def run_demo(logger: logging.Logger | None = None) -> None:
    log = logger or logging.getLogger(LOGGER_NAME)
    engine = build_default_engine(sink=_make_sink(log))
    seed_synthetic_subject(engine, SUBJECT, created_at=0)

    _print_manifest(engine, "EXPORT (before erasure)")

    report = engine.erase(SUBJECT, actor=ACTOR, reviewer=REVIEWER)
    print("\nERASE outcomes:")
    for outcome in report.outcomes:
        rev = f" reviewer={outcome.reviewer}" if outcome.reviewer else ""
        print(f"  {outcome.store:<13} {outcome.result:<13} x{outcome.count}{rev}")

    _print_manifest(engine, "EXPORT (after erasure)")
    print(
        "  ^ hard-delete stores are gone; human_review keeps a TOMBSTONE under a "
        "documented retention exception — id + reason, no raw content."
    )

    # Retention expiry: even the retention-exception tombstone is purged once its
    # (long) retention period elapses. now is far in the future here.
    purged = engine.purge_expired(now=1_000_000, actor=ACTOR)
    print(f"\nPURGE (retention expiry) at now=1_000_000: {purged}")

    print(f"\nAudit log holds {len(engine.audit_log)} records (JSON lines above).")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_demo()


if __name__ == "__main__":
    main()
