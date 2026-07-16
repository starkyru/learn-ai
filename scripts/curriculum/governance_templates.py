"""Locate + structurally validate the Module 20b reusable governance templates.

The 20b lesson ships fill-in-the-blank governance artifacts (data inventory,
retention schedule, DPIA, model/data card, licence/use decisions, incident &
recourse, accessibility & fairness). This module exposes the expected set and the
required sections per template so ``test_governance_templates.py`` can assert the
REAL files carry them — a template that loses a required section (say the model
card drops "prohibited uses") fails the test.

Dependency-free (no Markdown parser): a required section is matched as a
case-insensitive substring, which is enough to pin the headings/columns.
"""

from __future__ import annotations

from pathlib import Path

# scripts/curriculum/governance_templates.py -> parents[2] == the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "modules" / "20b-governance-privacy" / "templates"

# filename -> the (lower-cased) section markers it must contain.
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "DATA_INVENTORY.md": (
        "data stores",
        "data flow",
        "minimisation",
        "retention",
        "deletion",
        "owner",
    ),
    "RETENTION_SCHEDULE.md": (
        "schedule",
        "retention period",
        "deletion",
        "exception",
        "review",
    ),
    "DPIA.md": (
        "processing description",
        "necessity",
        "lawful basis",
        "risks to individuals",
        "mitigation",
        "sign-off",
    ),
    "MODEL_AND_DATA_CARD.md": (
        "purpose",
        "model",
        "data",
        "content types",
        "known limitations",
        "prohibited uses",
        "escalation",
        "monitoring",
        "review date",
    ),
    "LICENCE_AND_USE_DECISIONS.md": (
        "source licences",
        "attribution",
        "generated content",
        "redistribution",
        "provider terms",
    ),
    "INCIDENT_AND_RECOURSE.md": (
        "severity",
        "response steps",
        "notification",
        "recourse",
        "appeal",
        "post-incident review",
    ),
    "ACCESSIBILITY_AND_FAIRNESS.md": (
        "representative user scenarios",
        "accessibility checks",
        "fairness",
        "harm",
        "escalation",
        "appeal",
        "tracking",
    ),
}

# The templates every governance concern needs shipped — the keys above.
REQUIRED_TEMPLATES = tuple(REQUIRED_SECTIONS)


def missing_sections(filename: str) -> list[str]:
    """Required sections absent from ``filename`` (case-insensitive substring match).

    Returns the filename itself in a one-item list marker form is avoided — instead
    a missing FILE raises via the caller's existence check; here we assume the file
    exists and only report absent sections.
    """
    text = (TEMPLATES_DIR / filename).read_text(encoding="utf-8").lower()
    return [section for section in REQUIRED_SECTIONS[filename] if section not in text]


def index_links() -> str:
    """The templates index (README) text, for asserting it links every template."""
    return (TEMPLATES_DIR / "README.md").read_text(encoding="utf-8")
