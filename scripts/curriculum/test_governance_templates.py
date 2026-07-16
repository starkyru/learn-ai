"""Validate the committed Module 20b governance templates.

Imports the real expectations from ``governance_templates`` and asserts against
the REAL files on disk — so dropping a template, a required section, or an index
link fails the test.
"""

from __future__ import annotations

import governance_templates as gt
import pytest


def test_templates_directory_exists():
    assert gt.TEMPLATES_DIR.is_dir(), f"missing {gt.TEMPLATES_DIR}"


@pytest.mark.parametrize("filename", gt.REQUIRED_TEMPLATES)
def test_template_exists(filename: str):
    assert (gt.TEMPLATES_DIR / filename).is_file(), f"missing template {filename}"


@pytest.mark.parametrize("filename", gt.REQUIRED_TEMPLATES)
def test_template_has_all_required_sections(filename: str):
    assert gt.missing_sections(filename) == []


def test_index_links_every_template():
    index = gt.index_links()
    for filename in gt.REQUIRED_TEMPLATES:
        assert filename in index, f"templates/README.md does not link {filename}"
