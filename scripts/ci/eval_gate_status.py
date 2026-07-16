"""Decide whether the CI eval-gate should run — with an ENFORCED, downgrade-proof
activation marker.

The marker ``scripts/curriculum/ci_gates.json`` records each release gate's
``active`` flag and its entrypoint ``path``. Two enforcement layers close the
"silently disabled" gaps:

  FORWARD (current tree):
    - ``active: false`` and path ABSENT  → skip (green) — the intended pre-landing state.
    - path PRESENT                       → run the gate (present=true).
    - ``active: true`` and path ABSENT   → FAIL — a delete/rename after activation.

  DOWNGRADE (vs the PROTECTED BASE, via ``--base-ref``):
    A PR/push cannot turn OFF or remove a gate that was ACTIVE on the base branch.
    If the base marks the gate active, the current tree MUST keep it active AND its
    entrypoint present — otherwise FAIL. Without this a PR could set ``active:false``
    and delete the gate so the "required" job passes with all steps skipped.

Used by the workflow's ``eval-gate`` detect step:

    python3 scripts/ci/eval_gate_status.py [gate-id] [--base-ref REF]

It writes ``present=true|false`` to ``$GITHUB_OUTPUT`` (if set) and exits non-zero
for any enforced failure.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_DEFAULT_GATE_ID = "21b-release-gate"
_MARKER_RELPATH = "scripts/curriculum/ci_gates.json"


class BaseRefError(RuntimeError):
    """The protected base could not be read (fetch/parse failure) — fail closed."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def marker_path() -> Path:
    return repo_root() / _MARKER_RELPATH


def _gate_from_data(data: dict, gate_id: str) -> dict:
    for gate in data.get("gates", []):
        if gate.get("id") == gate_id:
            return gate
    return {}


def load_gate(gate_id: str, marker: Path | None = None) -> dict:
    """The gate record for ``gate_id`` from the working-tree marker, or ``{}``."""
    data = json.loads((marker or marker_path()).read_text(encoding="utf-8"))
    return _gate_from_data(data, gate_id)


def load_gate_from_ref(
    gate_id: str, ref: str, root: Path | None = None, *, require: bool = False
) -> dict:
    """The gate record from the marker at a git ``ref``, or ``{}``.

    Distinguishes three cases so it can FAIL CLOSED under ``require`` (used for
    pull_request events, where the base MUST be verifiable):

      - ref does NOT resolve (fetch failure / bad ref) → ``BaseRefError`` if
        ``require`` else ``{}``;
      - ref resolves but the marker is ABSENT there (first-time introduction of
        the marker) → ``{}`` (legitimate "no prior active gate");
      - ref resolves, marker present but UNPARSEABLE → ``BaseRefError`` if
        ``require`` else ``{}``.
    """
    base = root or repo_root()

    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True)
        except OSError as exc:
            raise BaseRefError(f"cannot run git: {exc}") from exc

    # 1. Does the base ref resolve? (A failed fetch leaves it unresolvable.)
    rev = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    if rev.returncode != 0:
        if require:
            raise BaseRefError(f"base ref {ref!r} is not available (fetch failure?)")
        return {}

    # 2. Read the marker at that (valid) ref.
    show = _git("show", f"{ref}:{_MARKER_RELPATH}")
    if show.returncode != 0:
        # Valid ref, but the marker did not exist there — legitimate first landing.
        return {}

    # 3. Parse it.
    try:
        data = json.loads(show.stdout)
    except json.JSONDecodeError as exc:
        if require:
            raise BaseRefError(f"base marker at {ref!r} is not valid JSON: {exc}") from exc
        return {}
    return _gate_from_data(data, gate_id)


def evaluate_gate(cur_gate: dict, base_gate: dict, root: Path) -> tuple[bool, str | None]:
    """Return ``(should_run, error)``.

    ``error`` is non-None for any enforced failure (forward: active+missing;
    downgrade: a base-active gate turned off or removed). ``should_run`` is True
    when the current entrypoint exists.
    """
    gate_id = cur_gate.get("id") or base_gate.get("id")
    rel = cur_gate.get("path") or base_gate.get("path")
    cur_active = bool(cur_gate.get("active"))
    base_active = bool(base_gate.get("active"))
    present = bool(rel) and (root / rel).is_file()

    if base_active and not cur_active:
        return False, (
            f"downgrade: gate '{gate_id}' was active on the base branch but is marked inactive here"
        )
    if base_active and not present:
        return False, (
            f"removal: gate '{gate_id}' was active on the base branch but its "
            f"entrypoint is missing now: {rel!r}"
        )
    if cur_active and not present:
        return False, (
            f"active but missing: gate '{gate_id}' is marked active but its "
            f"entrypoint is missing: {rel!r} (deleted or renamed?)"
        )
    return present, None


def _write_output(key: str, value: str) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval-gate activation status")
    parser.add_argument("gate_id", nargs="?", default=_DEFAULT_GATE_ID)
    parser.add_argument(
        "--base-ref",
        default=None,
        help="git ref of the protected base to compare against (downgrade guard)",
    )
    parser.add_argument(
        "--require-base",
        action="store_true",
        help="FAIL if the base ref/marker cannot be read (pull_request events)",
    )
    args = parser.parse_args(argv)

    cur_gate = load_gate(args.gate_id)
    try:
        base_gate = (
            load_gate_from_ref(args.gate_id, args.base_ref, require=args.require_base)
            if args.base_ref
            else {}
        )
    except BaseRefError as exc:
        print(f"::error::eval gate {args.gate_id!r}: cannot verify protected base: {exc}")
        _write_output("present", "false")
        return 1
    should_run, error = evaluate_gate(cur_gate, base_gate, repo_root())

    if error is not None:
        print(f"::error::eval gate {args.gate_id!r}: {error}")
        _write_output("present", "false")
        return 1

    if should_run:
        print(f"eval gate {args.gate_id!r}: entrypoint present — will run.")
    else:
        print(f"eval gate {args.gate_id!r}: not active and not present — skipping (green).")
    _write_output("present", "true" if should_run else "false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
