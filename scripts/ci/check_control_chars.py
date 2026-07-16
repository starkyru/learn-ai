"""Fail if any tracked source text file contains a C0 control char / NUL.

Used by the CI ``control-char-scan`` job. C0 controls (0x00-0x1F) are rejected
EXCEPT TAB (0x09), LF (0x0A), and CR (0x0D); NUL (0x00) is included in the reject
set. Only tracked text-source extensions are scanned (binary/data trees are not
tracked as these extensions), so the scan is fast and portable (stdlib only).

    python3 scripts/ci/check_control_chars.py
"""

from __future__ import annotations

import re
import subprocess
import sys

_EXTENSIONS = (
    "*.ts",
    "*.tsx",
    "*.py",
    "*.md",
    "*.json",
    "*.yml",
    "*.yaml",
    "*.sql",
    "*.toml",
)
# Pathspecs for extensionless tracked source-text trees the globs would miss —
# ALL tracked files under .husky/ (top-level hooks AND any nested husky shims).
_EXTRA_PATHSPECS = (".husky",)
# C0 controls minus TAB (09) / LF (0a) / CR (0d); NUL (00) is in range.
_BAD = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def tracked_files() -> list[bytes]:
    out = subprocess.run(
        ["git", "ls-files", "-z", *_EXTENSIONS, *_EXTRA_PATHSPECS],
        capture_output=True,
        check=True,
    ).stdout
    # A path can match both an extension glob and a pathspec — dedupe, keep order.
    seen: set[bytes] = set()
    files: list[bytes] = []
    for f in out.split(b"\0"):
        if f and f not in seen:
            seen.add(f)
            files.append(f)
    return files


def offending_files(files: list[bytes]) -> list[str]:
    bad: list[str] = []
    for path in files:
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        if _BAD.search(data):
            bad.append(path.decode("utf-8", "replace"))
    return bad


def main() -> int:
    files = tracked_files()
    bad = offending_files(files)
    print(f"scanned {len(files)} tracked source text files")
    if bad:
        print("::error::C0 control char / NUL found in tracked source text:")
        for name in bad:
            print(f"  {name}")
        return 1
    print("OK: no C0 control chars / NUL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
