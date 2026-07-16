"""Validate the committed Task 4 release assets (deploy workflow + RUNBOOK).

These import the real readers from ``release_assets`` and assert against the REAL
files on disk — so the test fails if someone weakens the artifacts (e.g. adds a
``push:`` trigger to the deploy workflow, drops a staged-rollout job, or removes a
required RUNBOOK section).
"""

from __future__ import annotations

import release_assets as ra


def test_deploy_workflow_and_runbook_exist():
    assert ra.DEPLOY_WORKFLOW.is_file(), f"missing {ra.DEPLOY_WORKFLOW}"
    assert ra.RUNBOOK.is_file(), f"missing {ra.RUNBOOK}"


def test_deploy_workflow_is_opt_in_manual_only():
    # The load-bearing invariant: a deploy is MANUAL only, so the default CI path
    # (ci.yml) never needs a cloud account or provider secret. A push/pull_request
    # trigger here would break that — this test forbids it.
    text = ra.DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert ra.deploy_triggers(text) == {"workflow_dispatch"}


def test_deploy_workflow_has_the_staged_rollout_jobs():
    text = ra.DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    jobs = ra.deploy_job_names(text)
    for required in ra.REQUIRED_DEPLOY_JOBS:
        assert required in jobs, f"deploy.yml is missing the '{required}' job"


def test_deploy_workflow_references_the_runbook():
    text = ra.DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert "RUNBOOK.md" in text  # thresholds/rollback commands live there


def test_runbook_has_all_required_sections():
    text = ra.RUNBOOK.read_text(encoding="utf-8")
    assert ra.runbook_missing_sections(text) == []


def test_runbook_documents_a_concrete_rollback_command():
    # Rollback must be executable, not hand-wavy: the runbook names the real
    # migration rollback entrypoint so an operator can run it verbatim.
    text = ra.RUNBOOK.read_text(encoding="utf-8")
    assert "rollback(" in text  # m07b_service.migrations.rollback / migrations.ts
