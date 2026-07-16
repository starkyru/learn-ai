"""Offline exercise smoke runner (network-restricted, defense-in-depth).

    uv run python scripts/curriculum/smoke_exercises.py

Loads the manifest, selects every ``offline`` entry, and runs each one in an
isolated temporary cwd with:

  - a MINIMAL ALLOWLISTED environment (PATH/HOME/locale/TMPDIR only) plus
    ``OFFLINE_SMOKE=1`` / ``CI=1`` — no provider keys, proxy URLs, or index
    credentials ever reach an offline child;
  - the per-entry ``timeout_s`` enforced — the child runs in its own process
    group (whose id is captured up front) and the WHOLE group is SIGKILLed on
    overrun, so orphaned grandchildren die even if the leader already exited;
  - an in-process network TRIPWIRE (Python :mod:`net_guard`, Node
    ``net_guard.cjs``); a child that trips a non-loopback connect / UDP send /
    DNS lookup is reported as a NETWORK VIOLATION.

Each entry must exit 0, produce its declared ``expected_artifacts`` (which must be
relative, repo-contained, and materialise as REGULAR files — not symlinks or
directories), and write NOTHING undeclared into the repo tree. Repo-write
detection snapshots the ENTIRE worktree TOPOLOGY before/after the run — every file
(content-hashed), directory (incl. empty ones), and symlink (by target, via
``lstat``, never followed), excluding only ``.git``/``node_modules``/``.venv`` and
the declared artifacts — and flags any added/changed/removed path. It is
git-INDEPENDENT and FAILS CLOSED: if the snapshot cannot be taken, the entry fails
(never a silent pass). Declared artifacts are cleaned and the temp cwd deleted, so
a run leaves the repo pristine.

HONEST LIMITATIONS — two, both accepted by the threat model (an honestly
MISCLASSIFIED exercise, not adversarial code):

  1. The network guard is a best-effort TRIPWIRE, NOT a sandbox: it only covers
     common in-process network paths in the direct child. It does not stop
     ``_socket``/``ctypes``, a fresh reimport, or a spawned subprocess.
  2. The timeout kills the direct child's process GROUP (captured up front). A
     descendant that deliberately calls ``setsid()`` detaches into a new group
     and ESCAPES the kill; full containment needs an OS-level cgroup/job object
     (Linux-only, privileged) and is intentionally out of scope here.

For both, the ENFORCING boundary is OS-level network isolation of the CI smoke
job: `.github/workflows/ci.yml` runs this whole process tree inside a network
namespace with no interfaces up (`unshare --net`), so even a spawned subprocess
that bypasses the in-process guard cannot reach the network. This runner's guard
+ secret-stripping + whole-worktree write detection + the static offline
classifier are the defense-in-depth layers behind that boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import check_structure
import net_guard
from manifest import ExerciseEntry, load_manifest, repo_root

CURRICULUM_DIR = Path(__file__).resolve().parent
NODE_GUARD = CURRICULUM_DIR / "net_guard.cjs"

PASSED = "passed"
FAILED = "failed"
VIOLATION = "violation"
TIMEOUT = "timeout"
SKIPPED = "skipped"

_FAILING = frozenset({FAILED, VIOLATION, TIMEOUT})

# The child inherits ONLY these exact keys. Everything else — provider secrets,
# HTTP(S)_PROXY / *_INDEX_URL creds, ambient config — is dropped. The locale set
# is explicit (NOT an ``LC_*`` wildcard, which would forward an ``LC_SECRET``).
# OFFLINE_SMOKE/CI/PYTHONPATH/PYTHONUTF8 are set fresh below.
_ENV_ALLOWLIST = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LC_MESSAGES",
        "LC_NUMERIC",
        "LC_TIME",
        "LC_COLLATE",
        "USER",
        "LOGNAME",
        "SHELL",
        "SYSTEMROOT",
        "PATHEXT",
        "COMSPEC",
    }
)

# Runs the target as ``__main__`` with the socket guard installed FIRST, argv and
# sys.path[0] set as if invoked directly. Passed to ``python -c``.
_PY_PREAMBLE = (
    "import os, sys, runpy\n"
    "import net_guard\n"
    "net_guard.install()\n"
    "target = os.path.abspath(sys.argv[1])\n"
    "sys.path.insert(0, os.path.dirname(target))\n"
    "sys.argv = [target, *sys.argv[2:]]\n"
    "runpy.run_path(target, run_name='__main__')\n"
)


# Directories skipped when snapshotting the worktree — ONLY external dependency,
# tool-cache, and VCS-control trees. Repo-OWNED output dirs (dist/build/site/…)
# are NOT excluded: a stray write there must be detected.
_SNAPSHOT_EXCLUDE_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        ".pnpm-store",
        ".ruff_cache",
        ".pytest_cache",
        "__pycache__",
        ".mypy_cache",
    }
)


class WorktreeSnapshotError(RuntimeError):
    """Raised when the worktree cannot be snapshotted (write detection fails closed)."""


@dataclass
class SmokeResult:
    path: str
    status: str
    reason: str = ""
    returncode: int | None = None
    duration_s: float = 0.0


def _flags_from_command(entry: ExerciseEntry) -> list[str]:
    """Extra CLI args after the path in the manifest command (e.g. ``--stub``).

    Raises if the command does not reference its own path — a silent mismatch
    could drop a required flag (``--stub``) and run the wrong branch.
    """
    tokens = shlex.split(entry.command)
    if entry.path not in tokens:
        raise ValueError(
            f"manifest command does not reference its path {entry.path!r}: {entry.command!r}"
        )
    idx = tokens.index(entry.path)
    return tokens[idx + 1 :]


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _ENV_ALLOWLIST}
    env["OFFLINE_SMOKE"] = "1"
    env["CI"] = "1"
    env["PYTHONUTF8"] = "1"  # deterministic UTF-8 I/O regardless of locale
    env["PYTHONPATH"] = str(CURRICULUM_DIR)  # fresh; only exposes net_guard
    if extra:
        env.update(extra)
    return env


def _tsx_binary() -> Path:
    """The tsx CLI from the runner's own repo (independent of the entry's root)."""
    return repo_root() / "node_modules" / ".bin" / "tsx"


def _tail(text: str | None, limit: int = 400) -> str:
    if not text:
        return ""
    return text.strip()[-limit:]


def _violation_line(output: str) -> str:
    for line in output.splitlines():
        if net_guard.VIOLATION_SENTINEL in line:
            return line.strip()
    return "outbound network attempted"


def _remove_path(path: Path) -> None:
    """Remove a file, symlink, or directory tree, raising on failure (fail loud)."""
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _remove_stray(path: Path) -> None:
    """Best-effort removal of an undeclared stray file / symlink / directory."""
    try:
        _remove_path(path)
    except OSError:
        pass


class ArtifactPathError(ValueError):
    """A declared artifact path is absolute or escapes the run root."""


def _validate_artifact_path(rel: str, root: Path) -> Path:
    """Return the absolute artifact path, rejecting absolute / ``..``-escaping ones.

    A manifest declaring an absolute path or one that traverses out of ``root``
    could make the runner stash/delete arbitrary files — reject it (fail closed).
    """
    candidate = Path(rel)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ArtifactPathError(f"artifact path must be relative and repo-contained: {rel!r}")
    resolved = (root / candidate).resolve()
    root_resolved = root.resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ArtifactPathError(f"artifact path escapes the run root: {rel!r}")
    return root / candidate


def _artifact_present(root: Path, cwd: Path, rel: str) -> bool:
    # A declared artifact must be a REGULAR FILE. ``lstat`` does not follow
    # symlinks, so a symlink pointing at some real file is NOT accepted, and a
    # directory named like the artifact is NOT a pass.
    for base in (root, cwd):
        try:
            mode = os.lstat(base / rel).st_mode
        except OSError:
            continue
        if stat.S_ISREG(mode):
            return True
    return False


def _stash_artifacts(declared_abs: list[Path], backup_dir: Path) -> dict[Path, Path]:
    """Move any pre-existing declared artifact aside so we can verify creation.

    Returns ``{artifact: backup}`` for restore. Raises ``OSError`` (fail loud) if
    an artifact cannot be moved — never silently deletes a learner's file.
    """
    backups: dict[Path, Path] = {}
    for index, artifact in enumerate(declared_abs):
        if artifact.exists() or artifact.is_symlink():
            backup = backup_dir / f"{index}_{artifact.name}"
            shutil.move(str(artifact), str(backup))
            backups[artifact] = backup
    return backups


def _restore_artifacts(declared_abs: list[Path], backups: dict[Path, Path]) -> list[str]:
    """Remove the run's declared outputs and restore pre-existing originals.

    Returns a list of failure messages (fail loud): the caller turns a non-empty
    list into a FAILED result so leftover residue can never pass silently.
    """
    errors: list[str] = []
    for artifact in declared_abs:
        try:
            _remove_path(artifact)
        except OSError as exc:
            errors.append(f"cleanup {artifact.name}: {exc}")
    for artifact, backup in backups.items():
        try:
            shutil.move(str(backup), str(artifact))
        except OSError as exc:
            errors.append(f"restore {artifact.name}: {exc}")
    return errors


def _kill_process_group(pgid: int) -> None:
    """SIGKILL a captured process-group id (never re-derive from a dead pid)."""
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, AttributeError, OSError):
        pass


def _wait_group_gone(pgid: int, timeout: float = 5.0) -> bool:
    """Poll until the process group has no members (or give up after timeout)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except (ProcessLookupError, OSError, AttributeError):
            return True
        time.sleep(0.05)
    return False


def _drain(proc: subprocess.Popen[str]) -> tuple[str, str]:
    try:
        return proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            return proc.communicate(timeout=5)
        except (subprocess.TimeoutExpired, ValueError):
            return "", ""


def _content_hash(path: Path) -> str:
    """SHA-256 of a file's CONTENT. Raises ``OSError`` on any stat/read failure.

    Content only — no size+mtime shortcut — so a same-size rewrite that restores
    the original mtime is still detected.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_fingerprint(path: Path) -> tuple[str, str]:
    """Type + content fingerprint of one path via ``lstat`` (does not follow links).

    ``("file", sha256)`` for a regular file, ``("symlink", target)`` for a
    symlink, ``("dir", "")`` for a directory, ``("other", mode)`` for anything
    else. Raises ``OSError`` on failure so the snapshot fails closed.
    """
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return ("symlink", os.readlink(path))
    if stat.S_ISDIR(mode):
        return ("dir", "")
    if stat.S_ISREG(mode):
        return ("file", _content_hash(path))
    return ("other", oct(stat.S_IFMT(mode)))


def _snapshot_worktree(root: Path, declared: list[str]) -> dict[str, tuple[str, str]]:
    """{repo_relative_path: (type, fingerprint)} for the whole worktree TOPOLOGY.

    Git-INDEPENDENT and the basis for FAIL-CLOSED write detection. It excludes
    only external/tool/VCS dirs and the declared artifacts, but records EVERY
    other file (content-hashed), directory (including empty ones), and symlink
    (by link target, via ``lstat`` — never followed) so a stray write ANYWHERE —
    a new/overwritten file, a new empty dir, or a created/replaced symlink — is
    caught. Any stat/read error OR walk error raises
    :class:`WorktreeSnapshotError` (never a silent partial snapshot).
    """
    declared_set = set(declared)
    snapshot: dict[str, tuple[str, str]] = {}

    def _on_walk_error(exc: OSError) -> None:
        raise WorktreeSnapshotError(f"cannot walk worktree: {exc}") from exc

    def _record(path: Path) -> None:
        rel = path.relative_to(root).as_posix()
        if rel in declared_set:
            return
        snapshot[rel] = _entry_fingerprint(path)

    try:
        for dirpath, dirnames, filenames in os.walk(
            root, onerror=_on_walk_error, followlinks=False
        ):
            dirnames[:] = [d for d in dirnames if d not in _SNAPSHOT_EXCLUDE_DIRS]
            base = Path(dirpath)
            if base != root:  # every real (descended) directory, incl. empty ones
                _record(base)
            # symlinked dirs appear in dirnames but are NOT descended → record here
            for name in dirnames:
                child = base / name
                if child.is_symlink():
                    _record(child)
            for name in filenames:  # regular files + symlinks-to-files
                _record(base / name)
    except OSError as exc:
        raise WorktreeSnapshotError(f"cannot snapshot worktree: {exc}") from exc
    return snapshot


def _diff_snapshots(
    before: dict[str, tuple[str, str]], after: dict[str, tuple[str, str]]
) -> list[tuple[str, bool]]:
    """Undeclared changes as ``(repo_relative_path, is_new)`` (sorted)."""
    changes: list[tuple[str, bool]] = []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) != after.get(rel):
            changes.append((rel, rel not in before))
    return changes


def _execute(
    entry: ExerciseEntry,
    root: Path,
    target: Path,
    flags: list[str],
    declared: list[str],
    before_snapshot: dict[str, tuple[str, str]],
    tmp_cwd: Path,
) -> SmokeResult:
    """Run the child, enforce the timeout/network/write checks, and classify."""
    if entry.language == "py":
        cmd = [sys.executable, "-c", _PY_PREAMBLE, str(target), *flags]
        env = _child_env()
    else:
        guard = shlex.quote(str(NODE_GUARD))
        cmd = [str(_tsx_binary()), str(target), *flags]
        env = _child_env({"NODE_OPTIONS": f"--require {guard}"})

    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=tmp_cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    # start_new_session makes the child a group leader: pgid == its pid. Capture
    # it now and kill THAT id later — never re-derive from a pid that may already
    # be a reaped zombie.
    pgid = proc.pid
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=entry.timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_group(pgid)
        stdout, stderr = _drain(proc)
    finally:
        _kill_process_group(pgid)  # reap lingering grandchildren on clean exit too
    _wait_group_gone(pgid)
    duration = time.monotonic() - started
    combined = (stdout or "") + "\n" + (stderr or "")

    try:
        after_snapshot = _snapshot_worktree(root, declared)
    except WorktreeSnapshotError as exc:
        return SmokeResult(
            entry.path, FAILED, f"could not verify repo state: {exc}", proc.returncode, duration
        )
    undeclared = _diff_snapshots(before_snapshot, after_snapshot)
    # Clean any NEW stray path (file, empty dir, or symlink) so the repo stays
    # pristine; sorted order removes a parent dir before its (already-gone) kids.
    for path, is_new in undeclared:
        if is_new:
            _remove_stray(root / path)

    if timed_out:
        return SmokeResult(
            entry.path, TIMEOUT, f"exceeded timeout_s={entry.timeout_s}", None, duration
        )
    if net_guard.VIOLATION_SENTINEL in combined:
        return SmokeResult(
            entry.path, VIOLATION, _violation_line(combined), proc.returncode, duration
        )
    if proc.returncode != 0:
        return SmokeResult(
            entry.path,
            FAILED,
            f"exit {proc.returncode}: {_tail(stderr)}",
            proc.returncode,
            duration,
        )
    if undeclared:
        paths = ", ".join(path for path, _ in undeclared)
        return SmokeResult(entry.path, FAILED, f"undeclared repo write(s): {paths}", 0, duration)
    missing = [a for a in declared if not _artifact_present(root, tmp_cwd, a)]
    if missing:
        return SmokeResult(
            entry.path, FAILED, f"missing expected_artifacts: {missing}", 0, duration
        )
    return SmokeResult(entry.path, PASSED, "", 0, duration)


def run_entry(entry: ExerciseEntry, root: Path) -> SmokeResult:
    """Run one offline entry under the network tripwire in an isolated temp cwd.

    Smoke means EXIT 0, NO undeclared repo write, and declared artifacts present —
    a shallow "it runs offline and produces its outputs" check, not a correctness
    proof. Deeper correctness is each module's own unit tests' job; where cheap,
    an offline exercise should self-assert its documented acceptance so a silent
    regression still fails smoke (see e.g. bpe.py's round-trip assert).
    """
    target = root / entry.path
    if not target.exists():
        return SmokeResult(entry.path, SKIPPED, reason="target file does not exist")
    if entry.offline != "offline":
        return SmokeResult(entry.path, SKIPPED, reason=f"not offline ({entry.offline})")

    flags = _flags_from_command(entry)
    declared = list(entry.expected_artifacts)
    try:
        declared_abs = [_validate_artifact_path(a, root) for a in declared]
    except ArtifactPathError as exc:
        return SmokeResult(entry.path, FAILED, f"invalid declared artifact path: {exc}")

    backup_dir = Path(tempfile.mkdtemp(prefix="smoke_bkp_"))
    try:
        backups = _stash_artifacts(declared_abs, backup_dir)
    except OSError as exc:
        shutil.rmtree(backup_dir, ignore_errors=True)
        return SmokeResult(entry.path, FAILED, f"could not prepare declared artifact: {exc}")

    try:
        before_snapshot = _snapshot_worktree(root, declared)
    except WorktreeSnapshotError as exc:
        _restore_artifacts([], backups)
        shutil.rmtree(backup_dir, ignore_errors=True)
        return SmokeResult(entry.path, FAILED, f"could not verify repo state: {exc}")

    tmp_cwd = Path(tempfile.mkdtemp(prefix="smoke_"))
    try:
        result = _execute(entry, root, target, flags, declared, before_snapshot, tmp_cwd)
    finally:
        cleanup_errors = _restore_artifacts(declared_abs, backups)
        shutil.rmtree(backup_dir, ignore_errors=True)
        shutil.rmtree(tmp_cwd, ignore_errors=True)

    if cleanup_errors and result.status == PASSED:
        return SmokeResult(
            entry.path,
            FAILED,
            f"artifact cleanup failed: {'; '.join(cleanup_errors)}",
            result.returncode,
            result.duration_s,
        )
    return result


def run_smoke(entries: list[ExerciseEntry], root: Path) -> list[SmokeResult]:
    """Run every supplied entry; one entry's crash fails only that entry."""
    results: list[SmokeResult] = []
    for entry in entries:
        try:
            results.append(run_entry(entry, root))
        except Exception as exc:  # noqa: BLE001 — isolate a bad entry from the batch
            results.append(SmokeResult(entry.path, FAILED, reason=f"runner error: {exc}"))
    return results


def _completeness_failures(root: Path) -> list[str]:
    """Reuse the checker: an unregistered exercise is a smoke failure."""
    manifest = load_manifest()
    findings = check_structure.check_manifest_completeness(root / "modules", root, manifest)
    return [f.message for f in findings]


def report(results: list[SmokeResult], completeness: list[str]) -> int:
    counts = Counter(r.status for r in results)
    print("Offline exercise smoke run")
    for result in sorted(results, key=lambda r: r.path):
        line = f"  [{result.status.upper():9}] {result.path}"
        if result.reason:
            line += f" — {result.reason}"
        print(line)

    if completeness:
        print("Manifest completeness failures (unregistered / missing):")
        for message in completeness:
            print(f"  - {message}")

    summary = ", ".join(
        f"{counts.get(status, 0)} {status}"
        for status in (PASSED, FAILED, VIOLATION, TIMEOUT, SKIPPED)
    )
    print(f"Summary: {summary}")

    failing = [r for r in results if r.status in _FAILING]
    if failing or completeness:
        print(f"smoke: FAIL ({len(failing)} failing entr(y/ies))")
        return 1
    print("smoke: PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline exercise smoke runner")
    parser.parse_args(argv)
    root = repo_root()
    manifest = load_manifest()
    offline = [e for e in manifest.exercises if e.offline == "offline"]
    results = run_smoke(offline, root)
    completeness = _completeness_failures(root)
    return report(results, completeness)


if __name__ == "__main__":
    sys.exit(main())
