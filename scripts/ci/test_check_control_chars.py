"""Tests for the control-char scanner.

Imports the REAL scanner functions (no reimplemented logic) and drives them with
synthetic files. Lives under ``scripts/ci`` and is run explicitly
(``uv run pytest scripts/ci``) — the default ``testpaths`` are modules+packages.
"""

from __future__ import annotations

import os
from pathlib import Path

import check_control_chars as cc


def _write(path: Path, data: bytes) -> bytes:
    path.write_bytes(data)
    return os.fsencode(path)  # scanner works on bytes paths (from `git ls-files -z`)


def test_nul_byte_is_flagged(tmp_path: Path) -> None:
    bad = _write(tmp_path / "bad.json", b'{"x": "a\x00b"}\n')
    assert cc.offending_files([bad]) == [os.fsdecode(bad)]


def test_other_c0_control_char_is_flagged(tmp_path: Path) -> None:
    # 0x07 (BEL) is a C0 control that is not TAB/LF/CR.
    bad = _write(tmp_path / "bad.py", b"x = 1  # \x07 bell\n")
    assert cc.offending_files([bad]) == [os.fsdecode(bad)]


def test_tab_lf_cr_are_allowed(tmp_path: Path) -> None:
    ok = _write(tmp_path / "ok.md", b"# title\r\n\tindented line\n")
    assert cc.offending_files([ok]) == []


def test_clean_file_is_not_flagged(tmp_path: Path) -> None:
    ok = _write(tmp_path / "ok.ts", b"export const x = 1;\n")
    assert cc.offending_files([ok]) == []


def test_unreadable_path_is_skipped_not_crashed(tmp_path: Path) -> None:
    missing = os.fsencode(tmp_path / "nope.py")
    assert cc.offending_files([missing]) == []


def test_husky_shim_with_nul_is_flagged(tmp_path: Path) -> None:
    # A husky shim is an extensionless shell script — offending_files reads bytes
    # regardless of extension, so a NUL in a tracked shim is caught.
    shim = _write(tmp_path / "pre-commit", b"#!/usr/bin/env sh\n\x00 pnpm foo\n")
    assert cc.offending_files([shim]) == [os.fsdecode(shim)]


def test_scanner_config_covers_toml_and_all_husky() -> None:
    assert "*.toml" in cc._EXTENSIONS
    assert ".husky" in cc._EXTRA_PATHSPECS  # scans ALL tracked .husky/** files


def test_real_repo_scans_husky_hooks() -> None:
    # The real tracked tree's husky hooks are actually in the scan set.
    tracked = {os.fsdecode(f) for f in cc.tracked_files()}
    assert ".husky/pre-commit" in tracked
    assert ".husky/pre-push" in tracked


def test_real_repo_tree_is_clean() -> None:
    # The scanner over the real tracked tree returns exit 0 (no control chars).
    assert cc.tracked_files()  # non-empty
    assert cc.main() == 0
