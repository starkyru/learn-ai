"""Curriculum-structure checker (CLI).

    uv run python scripts/curriculum/check_structure.py

Exit code 0 = pass (no FATAL findings), non-zero = fail. WARN findings are
printed but never fail the build — the design goal is "green today, tightenable
later": the machine-enforceable invariants are FATAL, and the softer content
checks report as WARN until the curriculum is cleaned up.

## Rules and severity

FATAL (fail the build):
  - manifest-schema     ``exercise_manifest.json`` loads and validates against
                        the pydantic schema (types, enum, path shape, no dupes).
  - manifest-complete   every runnable entrypoint under ``modules/**/{py,ts}/``
                        has exactly one manifest entry, and every entry points at
                        a file that exists. An UNREGISTERED exercise is a failure.
  - manifest-drift      the committed manifest is byte-identical to one
                        regenerated from CURRENT source, so a file that later
                        gains a provider/network/tiktoken import cannot keep an
                        offline classification without the checker noticing.
  - override-guard      any file force-classified via ``_OVERRIDES`` still
                        contains the source token that justified it (e.g.
                        bpe.py's ``OFFLINE_SMOKE`` guard).
  - exclude-reason      ``offline == "offline"`` ⇒ empty ``exclude_reason``;
                        any other bucket ⇒ non-empty ``exclude_reason``.
  - readme-links        internal relative links in module READMEs resolve to
                        real files (dead links fail).
  - language-matrix     ``language_support.json`` matches the on-disk py/ts
                        exercise dirs for every module, both directions (a module
                        missing from the matrix, a matrix entry with no dir, or a
                        py/ts flag disagreeing with reality all fail).
  - parity-policy       any module NOT shipping both languages has a complete
                        ``parity_policy.json`` entry (rationale, owner, target
                        milestone, equivalent learning path) — an intentional gap
                        must be a reviewed decision, not drift.

WARN (reported, non-fatal):
  - readme-structure    each module README has task headings and a
                        "Done when"/"Acceptance" section.
  - module-map          ``modules/*`` on disk agrees with the README module refs
                        and the ``CURRICULUM.md`` "## Module <id>" headings.
  - language-support    a README that advertises a ``py/`` or ``ts/`` path has a
                        matching directory with files (or labels itself
                        Python-first / TypeScript-first).

Every rule is a pure function of explicit paths/objects so it can be unit tested
against synthetic ``tmp_path`` fixtures. Run with ``--strict`` to also fail on
WARN findings (used to tighten CI later).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import build_manifest
from manifest import (
    Manifest,
    is_exercise_file,
    iter_exercise_files,
    load_manifest,
    repo_root,
    serialize_manifest,
)
from pydantic import ValidationError

FATAL = "FATAL"
WARN = "WARN"

_TASK_HEADING = re.compile(r"(?im)^#{2,4}\s+(?:Task\s+\d+|Tasks|Milestone)\b")
_TASK_TABLE = re.compile(r"(?im)^\|\s*Milestone\b")
_DONE_WHEN = re.compile(r"(?i)\b(done when|acceptance)\b")
_MD_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
_README_MODULE_REF = re.compile(r"modules/([0-9]+[a-z]?-[a-z0-9-]+)")
_CURRICULUM_MODULE_HEADING = re.compile(r"(?m)^#{2,}\s+Module\s+([0-9]+[a-z]?)\b")
_LANG_FIRST_LABEL = re.compile(
    r"(?i)(python-first|typescript-first|ts-first|python-only|typescript-only)"
)


@dataclass(frozen=True)
class Finding:
    severity: str
    rule: str
    message: str


def _module_prefix(slug: str) -> str:
    match = re.match(r"(\d+[a-z]?)-", slug)
    return match.group(1) if match else slug


def module_dirs(modules_dir: Path) -> list[Path]:
    """Module directories (those containing a README.md), sorted."""
    if not modules_dir.is_dir():
        return []
    return sorted(p for p in modules_dir.iterdir() if p.is_dir() and (p / "README.md").is_file())


# --- FATAL rules -----------------------------------------------------------


def check_manifest_schema(manifest_file: Path) -> tuple[Manifest | None, list[Finding]]:
    """Load + validate the manifest. Returns the manifest (or None) and findings."""
    try:
        manifest = load_manifest(manifest_file)
    except FileNotFoundError:
        return None, [Finding(FATAL, "manifest-schema", f"manifest is missing: {manifest_file}")]
    except ValidationError as exc:
        return None, [Finding(FATAL, "manifest-schema", f"manifest failed validation: {exc}")]
    except ValueError as exc:  # includes json.JSONDecodeError
        return None, [Finding(FATAL, "manifest-schema", f"manifest is not valid JSON: {exc}")]
    return manifest, []


def check_manifest_completeness(modules_dir: Path, root: Path, manifest: Manifest) -> list[Finding]:
    """Every on-disk entrypoint is registered and every entry exists on disk."""
    on_disk = {p.relative_to(root).as_posix() for p in iter_exercise_files(modules_dir)}
    registered = manifest.paths()

    findings: list[Finding] = []
    for missing in sorted(on_disk - registered):
        findings.append(
            Finding(
                FATAL,
                "manifest-complete",
                f"unregistered exercise (add it to the manifest): {missing}",
            )
        )
    for extra in sorted(registered - on_disk):
        findings.append(
            Finding(
                FATAL,
                "manifest-complete",
                f"manifest entry points to a missing file: {extra}",
            )
        )
    return findings


def check_exclude_reasons(manifest: Manifest) -> list[Finding]:
    """offline ⇒ empty reason; provider/download/stub ⇒ non-empty reason."""
    findings: list[Finding] = []
    for entry in manifest.exercises:
        has_reason = bool(entry.exclude_reason.strip())
        if entry.offline == "offline" and has_reason:
            findings.append(
                Finding(
                    FATAL,
                    "exclude-reason",
                    f"offline entry must have an empty exclude_reason: {entry.path}",
                )
            )
        if entry.offline != "offline" and not has_reason:
            findings.append(
                Finding(
                    FATAL,
                    "exclude-reason",
                    f"{entry.offline} entry needs an exclude_reason: {entry.path}",
                )
            )
    return findings


def check_manifest_drift(manifest_file: Path) -> list[Finding]:
    """The committed manifest is byte-identical to one regenerated from source.

    Re-derives classifications with the same logic as ``build_manifest.build()``
    and the same canonical serializer, then compares bytes. This catches an
    ``offline`` file that later gains a provider/network/tiktoken import: it would
    reclassify on regeneration, so the committed file drifts and this fails.
    """
    try:
        committed = manifest_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [Finding(FATAL, "manifest-drift", f"manifest is missing: {manifest_file}")]
    generated = serialize_manifest(build_manifest.build())
    if generated != committed:
        return [
            Finding(
                FATAL,
                "manifest-drift",
                "committed exercise_manifest.json is stale: it differs from the "
                "manifest regenerated from current source. Run "
                "`uv run python scripts/curriculum/build_manifest.py` and review.",
            )
        ]
    return []


def check_override_guards(root: Path) -> list[Finding]:
    """Offline-forcing overrides are still SOUND, not just present.

    Two independent conditions must hold for each override, and either failing is
    FATAL — because ``build()`` applies the override UNCONDITIONALLY, so neither
    completeness nor drift can catch an override that has quietly become unsafe:

      1. the guard token is still in the source (its CI-safety guard survives);
      2. with the guarded import neutralised, the file still classifies
         ``offline`` — i.e. it has NOT gained some other network/provider trigger
         (httpx/get_provider/…) that the guard does not cover.
    """
    findings: list[Finding] = []
    for rel, (token, guarded_import) in build_manifest.OVERRIDE_SOURCE_GUARDS.items():
        source_file = root / rel
        try:
            source = source_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            findings.append(Finding(FATAL, "override-guard", f"override target is missing: {rel}"))
            continue
        if token not in source:
            findings.append(
                Finding(
                    FATAL,
                    "override-guard",
                    f"{rel} is force-classified via _OVERRIDES but no longer "
                    f"contains the required guard {token!r}; its offline "
                    "classification may now be unsafe.",
                )
            )
            continue
        residual = build_manifest.override_residual_status(rel, source, guarded_import)
        if residual != "offline":
            findings.append(
                Finding(
                    FATAL,
                    "override-guard",
                    f"{rel} is force-classified offline, but classify() finds a "
                    f"non-offline trigger ({residual}) beyond the guarded "
                    f"{guarded_import!r} call; the override is unsafe until that "
                    "trigger is removed or itself guarded.",
                )
            )
    return findings


def _iter_internal_links(text: str) -> list[str]:
    """Relative link targets from a markdown file (skips external/anchor links)."""
    targets: list[str] = []
    for raw in _MD_LINK.findall(text):
        stripped = raw.strip()
        target = stripped.split()[0].strip("<>") if stripped else ""
        if not target or target.startswith("#"):
            continue
        low = target.lower()
        if "://" in low or low.startswith(("mailto:", "tel:")):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if target:
            targets.append(target)
    return targets


def check_readme_links(modules_dir: Path, root: Path) -> list[Finding]:
    """Internal relative links in module READMEs resolve to real files."""
    findings: list[Finding] = []
    for module_dir in module_dirs(modules_dir):
        readme = module_dir / "README.md"
        text = readme.read_text(encoding="utf-8", errors="replace")
        for target in _iter_internal_links(text):
            base = root if target.startswith("/") else readme.parent
            resolved = (base / target.lstrip("/")).resolve()
            if not resolved.exists():
                findings.append(
                    Finding(
                        FATAL,
                        "readme-links",
                        f"dead link in {readme.relative_to(root)}: {target}",
                    )
                )
    return findings


# --- WARN rules ------------------------------------------------------------


def check_readme_structure(modules_dir: Path, root: Path) -> list[Finding]:
    """Each module README has task headings and a Done-when/Acceptance section."""
    findings: list[Finding] = []
    for module_dir in module_dirs(modules_dir):
        readme = module_dir / "README.md"
        text = readme.read_text(encoding="utf-8", errors="replace")
        rel = readme.relative_to(root)
        if not (_TASK_HEADING.search(text) or _TASK_TABLE.search(text)):
            findings.append(Finding(WARN, "readme-structure", f"{rel}: no Task/Milestone headings"))
        if not _DONE_WHEN.search(text):
            findings.append(
                Finding(
                    WARN,
                    "readme-structure",
                    f"{rel}: no 'Done when'/'Acceptance' section",
                )
            )
    return findings


def check_module_map(modules_dir: Path, readme_path: Path, curriculum_path: Path) -> list[Finding]:
    """modules/* on disk ⇄ README module refs ⇄ CURRICULUM 'Module <id>' headings."""
    findings: list[Finding] = []
    disk_slugs = {d.name for d in module_dirs(modules_dir)}
    disk_ids = {_module_prefix(s) for s in disk_slugs}

    readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
    readme_slugs = set(_README_MODULE_REF.findall(readme_text))

    curriculum_text = curriculum_path.read_text(encoding="utf-8", errors="replace")
    curriculum_ids = set(_CURRICULUM_MODULE_HEADING.findall(curriculum_text))

    for slug in sorted(disk_slugs - readme_slugs):
        findings.append(Finding(WARN, "module-map", f"module on disk not linked in README: {slug}"))
    for slug in sorted(readme_slugs - disk_slugs):
        findings.append(
            Finding(WARN, "module-map", f"README links a module dir that is absent: {slug}")
        )
    for mid in sorted(disk_ids - curriculum_ids):
        findings.append(
            Finding(WARN, "module-map", f"module on disk has no CURRICULUM section: {mid}")
        )
    for mid in sorted(curriculum_ids - disk_ids):
        findings.append(
            Finding(WARN, "module-map", f"CURRICULUM lists a module with no dir: {mid}")
        )
    return findings


def check_language_support(modules_dir: Path, root: Path) -> list[Finding]:
    """README-advertised py/ts paths have a matching dir with files."""
    findings: list[Finding] = []
    for module_dir in module_dirs(modules_dir):
        readme = module_dir / "README.md"
        text = readme.read_text(encoding="utf-8", errors="replace")
        rel = readme.relative_to(root)
        slug = module_dir.name
        labeled = bool(_LANG_FIRST_LABEL.search(text))
        for lang in ("py", "ts"):
            claims = bool(
                re.search(rf"modules/{re.escape(slug)}/{lang}/", text)
                or re.search(rf"(?<![\w-]){lang}/\w", text)
            )
            lang_dir = module_dir / lang
            has_files = lang_dir.is_dir() and any(
                is_exercise_file(f) for f in lang_dir.rglob("*") if f.is_file()
            )
            if claims and not has_files and not labeled:
                findings.append(
                    Finding(
                        WARN,
                        "language-support",
                        f"{rel}: advertises a {lang}/ path but no {lang}/ exercises exist",
                    )
                )
    return findings


def _actual_support(module_dir: Path) -> dict[str, bool]:
    """Which languages ship runnable exercises for this module (rglob over py/ ts/).

    Uses :func:`is_exercise_file`, so tests, dotfiles, ``node_modules``, and
    ``__pycache__`` are ignored — a module with only a ``ts/package.json`` and no
    ``.ts`` exercise counts as NOT offering TypeScript (e.g. the open-ended
    capstone). Recursive so a nested app package (07b's ``py/m07b_service/``,
    ``ts/src/``) still counts as offering that language.
    """
    support: dict[str, bool] = {}
    for lang in ("py", "ts"):
        lang_dir = module_dir / lang
        support[lang] = lang_dir.is_dir() and any(
            is_exercise_file(f) for f in lang_dir.rglob("*") if f.is_file()
        )
    return support


def check_language_matrix(modules_dir: Path, matrix_path: Path) -> list[Finding]:
    """The committed language-support matrix matches the on-disk exercise dirs.

    ``language_support.json`` is the single source of truth for which languages
    each module offers. This pins it to reality in BOTH directions: every module
    has an entry, every entry names a real module, and each entry's ``py``/``ts``
    booleans equal what actually ships — so the matrix cannot silently rot when a
    language is added or removed (the same "no drift" guarantee the manifest has).
    """
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [Finding(FATAL, "language-matrix", f"matrix is missing: {matrix_path}")]
    except ValueError as exc:
        return [Finding(FATAL, "language-matrix", f"matrix is not valid JSON: {exc}")]

    findings: list[Finding] = []
    disk = {d.name: _actual_support(d) for d in module_dirs(modules_dir)}
    for slug in sorted(set(matrix) - set(disk)):
        findings.append(
            Finding(FATAL, "language-matrix", f"matrix lists a module with no dir: {slug}")
        )
    for slug in sorted(set(disk) - set(matrix)):
        findings.append(
            Finding(FATAL, "language-matrix", f"module on disk missing from the matrix: {slug}")
        )
    for slug in sorted(set(matrix) & set(disk)):
        entry = matrix[slug]
        for lang in ("py", "ts"):
            declared = bool(entry.get(lang)) if isinstance(entry, dict) else None
            if declared != disk[slug][lang]:
                findings.append(
                    Finding(
                        FATAL,
                        "language-matrix",
                        f"{slug}: matrix says {lang}={declared} but disk has "
                        f"{lang}={disk[slug][lang]}",
                    )
                )
    return findings


def check_parity_policy(modules_dir: Path, policy_path: Path) -> list[Finding]:
    """Every module NOT shipping both languages has a complete parity-policy entry.

    A module that does not offer BOTH Python and TypeScript (single-language, or an
    open-ended module with neither) must justify it in ``parity_policy.json`` with a
    rationale, owner, target milestone, and an equivalent learning path for the
    other language — so an intentional gap is a reviewed decision, not silent drift.
    Extra (informational) entries for full-parity modules are allowed, but every
    entry must reference a real module.
    """
    required = ("rationale", "owner", "target_milestone", "equivalent_path")
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [Finding(FATAL, "parity-policy", f"parity policy is missing: {policy_path}")]
    except ValueError as exc:
        return [Finding(FATAL, "parity-policy", f"parity policy is not valid JSON: {exc}")]

    findings: list[Finding] = []
    disk = {d.name: _actual_support(d) for d in module_dirs(modules_dir)}
    for slug in sorted(set(policy) - set(disk)):
        findings.append(
            Finding(FATAL, "parity-policy", f"policy names a module with no dir: {slug}")
        )
    for slug, support in sorted(disk.items()):
        if support["py"] and support["ts"]:
            continue  # full parity — no exception needed
        entry = policy.get(slug)
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    FATAL,
                    "parity-policy",
                    f"{slug}: not full py+ts parity and has no parity_policy.json entry",
                )
            )
            continue
        missing = [field for field in required if not str(entry.get(field, "")).strip()]
        if missing:
            findings.append(
                Finding(
                    FATAL,
                    "parity-policy",
                    f"{slug}: parity_policy entry missing field(s): {', '.join(missing)}",
                )
            )
    return findings


# --- driver ----------------------------------------------------------------


def run_checks(root: Path | None = None) -> list[Finding]:
    """Run every rule against a repo root and return all findings."""
    base = root or repo_root()
    modules_dir = base / "modules"
    manifest_file = base / "scripts" / "curriculum" / "exercise_manifest.json"
    matrix_file = base / "scripts" / "curriculum" / "language_support.json"
    policy_file = base / "scripts" / "curriculum" / "parity_policy.json"

    findings: list[Finding] = []
    manifest, schema_findings = check_manifest_schema(manifest_file)
    findings.extend(schema_findings)
    if manifest is not None:
        findings.extend(check_manifest_completeness(modules_dir, base, manifest))
        findings.extend(check_exclude_reasons(manifest))
    findings.extend(check_manifest_drift(manifest_file))
    findings.extend(check_override_guards(base))
    findings.extend(check_readme_links(modules_dir, base))
    findings.extend(check_readme_structure(modules_dir, base))
    findings.extend(check_module_map(modules_dir, base / "README.md", base / "CURRICULUM.md"))
    findings.extend(check_language_support(modules_dir, base))
    findings.extend(check_language_matrix(modules_dir, matrix_file))
    findings.extend(check_parity_policy(modules_dir, policy_file))
    return findings


def _emit(items: list[Finding]) -> None:
    by_rule: dict[str, list[Finding]] = {}
    for f in items:
        by_rule.setdefault(f.rule, []).append(f)
    for rule in sorted(by_rule):
        print(f"  [{by_rule[rule][0].severity}] {rule}")
        for f in by_rule[rule]:
            print(f"      - {f.message}")


def report(findings: list[Finding], strict: bool) -> int:
    fatal = [f for f in findings if f.severity == FATAL]
    warn = [f for f in findings if f.severity == WARN]

    if warn:
        print(f"WARN findings ({len(warn)}):")
        _emit(warn)
    if fatal:
        print(f"FATAL findings ({len(fatal)}):")
        _emit(fatal)

    failing = fatal + (warn if strict else [])
    if failing:
        print(f"\ncheck_structure: FAIL ({len(failing)} blocking finding(s))")
        return 1
    print(f"\ncheck_structure: PASS ({len(warn)} warning(s), 0 fatal)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Curriculum-structure checker")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also fail on WARN findings (for tightening CI later)",
    )
    args = parser.parse_args(argv)
    findings = run_checks()
    return report(findings, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
