"""Locate + structurally validate the Task 4 release assets.

The Module 07b delivery lesson ships two release artifacts that must stay honest:
a **deploy workflow** (`.github/workflows/deploy.yml`) and an operational
**RUNBOOK** (`modules/07b-delivery-operations/RUNBOOK.md`). This module exposes
small readers/validators over the REAL files so `test_release_assets.py` can
assert their load-bearing invariants — most importantly that the deploy workflow
is **opt-in** (manual `workflow_dispatch` only, never `push`/`pull_request`), so
the default CI path needs no cloud account or provider secret.

Deliberately dependency-free (no PyYAML): the curriculum CI job installs base
deps only, so the workflow's trigger block is parsed with a tiny top-level-block
reader rather than a YAML library.
"""

from __future__ import annotations

from pathlib import Path

# scripts/curriculum/release_assets.py -> parents[2] == the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
RUNBOOK = REPO_ROOT / "modules" / "07b-delivery-operations" / "RUNBOOK.md"

# The staged-rollout jobs the deploy workflow must define, in sequence.
REQUIRED_DEPLOY_JOBS = ("gate", "deploy-staging", "canary", "rollback")

# The operational sections the RUNBOOK must carry (matched case-insensitively).
REQUIRED_RUNBOOK_SECTIONS = (
    "owners",
    "dashboards",
    "alerts",
    "canary thresholds",
    "rollback",
    "recovery",
    "incident review",
)

# GitHub-Actions trigger keys we distinguish; a deploy template must use ONLY the
# manual one.
_KNOWN_TRIGGERS = (
    "workflow_dispatch",
    "push",
    "pull_request",
    "schedule",
    "workflow_call",
)


def _block_under(text: str, key: str) -> str:
    """Return the lines nested under a top-level ``key:`` (until the next top key).

    A top-level key starts at column 0; its block is every following line that is
    indented (or blank). Enough to read a workflow's ``on:`` / ``jobs:`` block
    without a YAML parser.
    """
    lines = text.splitlines()
    inside = False
    out: list[str] = []
    for line in lines:
        if not inside:
            if not line.startswith((" ", "\t")) and (
                line.rstrip() == f"{key}:" or line.startswith(f"{key}:")
            ):
                inside = True
            continue
        if line and not line[0].isspace():  # next top-level key -> block ended
            break
        out.append(line)
    return "\n".join(out)


def deploy_triggers(text: str) -> set[str]:
    """The set of trigger keys declared directly under the workflow's ``on:``.

    Only DIRECT children (exactly two-space indent) count, so nested keys such as
    ``inputs:`` under ``workflow_dispatch:`` are not mistaken for triggers.
    """
    block = _block_under(text, "on")
    found: set[str] = set()
    for line in block.splitlines():
        if line[:2] == "  " and (len(line) < 3 or line[2] != " "):
            key = line.strip().rstrip(":").split(":")[0].strip()
            if key in _KNOWN_TRIGGERS:
                found.add(key)
    return found


def deploy_job_names(text: str) -> set[str]:
    """The job ids declared under the workflow's top-level ``jobs:`` (2-space indent)."""
    block = _block_under(text, "jobs")
    names: set[str] = set()
    for line in block.splitlines():
        if line[:2] == "  " and (len(line) < 3 or line[2] != " ") and line.rstrip().endswith(":"):
            names.add(line.strip().rstrip(":"))
    return names


def runbook_missing_sections(text: str) -> list[str]:
    """Required RUNBOOK sections that are absent (case-insensitive substring match)."""
    lowered = text.lower()
    return [section for section in REQUIRED_RUNBOOK_SECTIONS if section not in lowered]
