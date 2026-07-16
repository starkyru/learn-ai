"""Machine-readable exercise manifest: schema, loader, and enumerator.

This module owns the pydantic schema for ``exercise_manifest.json`` (so the
manifest is validated, not free-form) plus the helpers the structure checker and
the (T1.2) offline smoke runner build on.

## What the manifest is

``exercise_manifest.json`` enumerates every runnable exercise entrypoint under
``modules/**/{py,ts}/``. Each entry records how to run the file and whether it is
safe to run in the default, offline, no-secrets CI path.

## The four ``offline`` buckets

Only files in the ``offline`` bucket are meant to be smoke-run by default CI.
The other three buckets each explain *why* a file is excluded (and every one of
them therefore carries a non-empty ``exclude_reason``):

- ``offline``  — runs to completion deterministically with **no** provider key,
  **no** network, and **no** large/native download. Safe for default CI.
- ``provider`` — needs an external service or network: an LLM/embedding provider
  key, a running MCP server, or another outbound HTTP call. Never run by default.
- ``download`` — needs a large or native local install before it can run: model
  weights (torch/diffusers/transformers/peft), a Playwright browser binary, or a
  native npm dependency that is not in the default install.
- ``stub``     — an unsolved learner scaffold. It raises ``NotImplementedError``
  (Python) or throws a TODO ``Error`` (TypeScript) until the learner implements
  the core; it would run offline once solved, but as shipped it does not do real
  work, so it is not part of the default smoke set.

The offline↔``exclude_reason`` business rule (offline ⇒ empty reason; anything
else ⇒ non-empty reason) is intentionally enforced by the *checker*
(``check_structure.py``), not by this schema, so that individual rule can be unit
tested against real :class:`ExerciseEntry` objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

OfflineStatus = Literal["offline", "provider", "download", "stub"]
Language = Literal["py", "ts"]

#: Language subdirectories under each module that hold runnable exercises.
EXERCISE_DIRS: tuple[str, ...] = ("py", "ts")


def repo_root() -> Path:
    """Absolute path to the repository root (``scripts/curriculum`` → up two)."""
    return Path(__file__).resolve().parents[2]


def modules_root() -> Path:
    """Absolute path to the ``modules/`` directory."""
    return repo_root() / "modules"


def manifest_path() -> Path:
    """Absolute path to the committed ``exercise_manifest.json``."""
    return Path(__file__).resolve().parent / "exercise_manifest.json"


#: Directory names that never hold registrable exercises (both languages).
_EXCLUDED_DIRS = frozenset({"__pycache__", "node_modules", "__tests__", "tests"})


def is_exercise_file(path: Path) -> bool:
    """True if ``path`` is a runnable exercise entrypoint we must register.

    Excludes, for BOTH languages:
      - dotfiles;
      - test infrastructure: ``conftest.py`` and anything under a ``__tests__/``
        or ``tests/`` directory;
      - Python test files (``test_*.py`` / ``*_test.py``);
      - TypeScript test files (``test_*.ts`` / ``*.test.ts`` / ``*.spec.ts``).

    ``__pycache__`` / ``node_modules`` / ``__tests__`` / ``tests`` are also
    filtered by the directory walk in :func:`iter_exercise_files`.
    """
    name = path.name
    if name.startswith("."):
        return False
    if name == "conftest.py" or _EXCLUDED_DIRS.intersection(path.parts):
        return False
    if path.suffix == ".py":
        return not (name.startswith("test_") or name.endswith("_test.py"))
    if path.suffix == ".ts":
        return not (name.startswith("test_") or name.endswith((".test.ts", ".spec.ts")))
    return False


def iter_exercise_files(root: Path) -> list[Path]:
    """Every runnable exercise entrypoint directly under ``<root>/*/{py,ts}/`` (sorted).

    This is the single source of truth for "what must appear in the manifest",
    shared by the generator and the completeness check so they cannot drift.

    Collection is NON-recursive: only files placed directly in a module's ``py/``
    or ``ts/`` directory are exercise entrypoints. Nested subdirectories are an
    application's internal structure (e.g. module 07b's ``py/m07b_service/``
    package, ``ts/src/`` app code, and ``ts/test/`` helpers) — those are library
    modules that cannot be run standalone (relative imports, a server bind, or a
    required argv) and are verified by that module's pytest/jest suites, not by
    the per-file offline smoke runner. Registering them would make the smoke run
    execute non-entrypoints and fail spuriously.
    """
    results: list[Path] = []
    if not root.is_dir():
        return results
    for module_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for lang in EXERCISE_DIRS:
            lang_dir = module_dir / lang
            if not lang_dir.is_dir():
                continue
            for candidate in sorted(lang_dir.iterdir()):
                if not candidate.is_file():
                    continue
                if _EXCLUDED_DIRS.intersection(candidate.parts):
                    continue
                if is_exercise_file(candidate):
                    results.append(candidate)
    return results


class ExerciseEntry(BaseModel):
    """One runnable exercise entrypoint and how/whether CI can run it."""

    model_config = ConfigDict(extra="forbid")

    path: str
    module: str
    language: Language
    command: str
    extras: list[str] = []
    offline: OfflineStatus
    expected_artifacts: list[str] = []
    timeout_s: int
    exclude_reason: str = ""

    @field_validator("timeout_s")
    @classmethod
    def _positive_timeout(cls, value: int) -> int:
        if value < 1:
            raise ValueError(f"timeout_s must be >= 1, got {value}")
        return value

    @field_validator("path")
    @classmethod
    def _path_shape(cls, value: str) -> str:
        if not value.startswith("modules/"):
            raise ValueError(f"path must be repo-relative under modules/: {value!r}")
        if value.endswith(".py") == value.endswith(".ts"):
            # exactly one of the two suffixes must hold
            raise ValueError(f"path must end in .py or .ts: {value!r}")
        return value

    @model_validator(mode="after")
    def _cross_field(self) -> ExerciseEntry:
        expected_lang: Language = "py" if self.path.endswith(".py") else "ts"
        if self.language != expected_lang:
            raise ValueError(
                f"language {self.language!r} does not match extension of {self.path!r}"
            )
        parts = self.path.split("/")
        if len(parts) < 3 or parts[1] != self.module:
            raise ValueError(f"module {self.module!r} is inconsistent with path {self.path!r}")
        if self.path not in self.command:
            raise ValueError(
                f"command must reference the exercise path {self.path!r}: {self.command!r}"
            )
        return self


class Manifest(BaseModel):
    """The whole manifest: a version tag and the list of exercises."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    exercises: list[ExerciseEntry]

    @model_validator(mode="after")
    def _no_duplicate_paths(self) -> Manifest:
        seen: set[str] = set()
        for entry in self.exercises:
            if entry.path in seen:
                raise ValueError(f"duplicate manifest entry for path: {entry.path}")
            seen.add(entry.path)
        return self

    def paths(self) -> set[str]:
        """Set of every registered exercise path."""
        return {entry.path for entry in self.exercises}


def load_manifest(path: Path | None = None) -> Manifest:
    """Load and validate the manifest JSON into a :class:`Manifest`.

    Raises ``pydantic.ValidationError`` if the file violates the schema and
    ``json.JSONDecodeError`` if it is not valid JSON.
    """
    target = path or manifest_path()
    data = json.loads(target.read_text(encoding="utf-8"))
    return Manifest.model_validate(data)


def serialize_manifest(manifest: Manifest) -> str:
    """Canonical on-disk text form of a manifest.

    This is the SINGLE serializer used both by the generator's writer and the
    drift check, so a byte comparison between "regenerated from source" and the
    committed file can never fail merely on formatting (indent/inline/newline).
    """
    return json.dumps(manifest.model_dump(), indent=2, ensure_ascii=False) + "\n"
