"""Tests for the curriculum-structure checker.

Each checker rule is exercised with a tiny synthetic ``tmp_path`` fixture (the
only mocked boundary is the filesystem). The real rule functions are imported
and called directly — no reimplementation, no mocking the unit under test. The
final two tests run the real checker against the real repo and assert it passes.
"""

from __future__ import annotations

import json
from pathlib import Path

import check_structure as cs
from manifest import ExerciseEntry, Manifest


def _entry(path: str, offline: str = "offline", reason: str = "") -> ExerciseEntry:
    language = "py" if path.endswith(".py") else "ts"
    command = f"uv run python {path}" if language == "py" else f"pnpm tsx {path}"
    return ExerciseEntry(
        path=path,
        module=path.split("/")[1],
        language=language,
        command=command,
        offline=offline,  # type: ignore[arg-type]
        timeout_s=30,
        exclude_reason=reason,
    )


_GOOD_README = "## Tasks\n\n### Task 1 — Do a thing\n\n**Done when** it works.\n"


def _make_module(modules_dir: Path, slug: str, readme: str = _GOOD_README) -> Path:
    module_dir = modules_dir / slug
    module_dir.mkdir(parents=True)
    (module_dir / "README.md").write_text(readme, encoding="utf-8")
    return module_dir


# --- manifest-complete -----------------------------------------------------


def test_completeness_flags_unregistered_exercise(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    module = _make_module(modules_dir, "04-x")
    (module / "py").mkdir()
    (module / "py" / "foo.py").write_text("print(1)", encoding="utf-8")

    findings = cs.check_manifest_completeness(modules_dir, root, Manifest(exercises=[]))

    assert len(findings) == 1
    assert findings[0].rule == "manifest-complete"
    assert findings[0].severity == cs.FATAL
    assert "unregistered" in findings[0].message
    assert "modules/04-x/py/foo.py" in findings[0].message


def test_completeness_flags_manifest_entry_without_file(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "04-x")  # module exists, but the py file does not
    manifest = Manifest(exercises=[_entry("modules/04-x/py/foo.py")])

    findings = cs.check_manifest_completeness(modules_dir, root, manifest)

    assert len(findings) == 1
    assert findings[0].severity == cs.FATAL
    assert "missing file" in findings[0].message
    assert "modules/04-x/py/foo.py" in findings[0].message


def test_completeness_passes_when_exact_match(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    module = _make_module(modules_dir, "04-x")
    (module / "py").mkdir()
    (module / "py" / "foo.py").write_text("print(1)", encoding="utf-8")
    manifest = Manifest(exercises=[_entry("modules/04-x/py/foo.py")])

    assert cs.check_manifest_completeness(modules_dir, root, manifest) == []


# --- exclude-reason --------------------------------------------------------


def test_provider_entry_without_reason_fails() -> None:
    manifest = Manifest(exercises=[_entry("modules/04-x/py/a.py", offline="provider", reason="")])

    findings = cs.check_exclude_reasons(manifest)

    assert len(findings) == 1
    assert findings[0].rule == "exclude-reason"
    assert findings[0].severity == cs.FATAL
    assert "provider entry needs an exclude_reason" in findings[0].message


def test_offline_entry_with_reason_fails() -> None:
    manifest = Manifest(
        exercises=[_entry("modules/04-x/py/a.py", offline="offline", reason="oops")]
    )

    findings = cs.check_exclude_reasons(manifest)

    assert len(findings) == 1
    assert "must have an empty exclude_reason" in findings[0].message


def test_exclude_reasons_valid_mix_passes() -> None:
    manifest = Manifest(
        exercises=[
            _entry("modules/04-x/py/a.py", offline="offline", reason=""),
            _entry("modules/04-x/py/b.py", offline="stub", reason="not solved yet"),
            _entry("modules/04-x/py/c.py", offline="download", reason="needs weights"),
        ]
    )

    assert cs.check_exclude_reasons(manifest) == []


# --- readme-links ----------------------------------------------------------


def test_dead_internal_link_flagged(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "04-x", readme="See [notes](./missing.md).\n")

    findings = cs.check_readme_links(modules_dir, root)

    assert len(findings) == 1
    assert findings[0].rule == "readme-links"
    assert findings[0].severity == cs.FATAL
    assert "missing.md" in findings[0].message


def test_valid_internal_link_ok(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    module = _make_module(modules_dir, "04-x", readme="See [notes](./notes.md).\n")
    (module / "notes.md").write_text("hi", encoding="utf-8")

    assert cs.check_readme_links(modules_dir, root) == []


def test_external_and_anchor_links_ignored(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    readme = "[a](https://x.com) [b](#section) [c](mailto:x@y.z)\n"
    _make_module(modules_dir, "04-x", readme=readme)

    assert cs.check_readme_links(modules_dir, root) == []


# --- readme-structure ------------------------------------------------------


def test_missing_done_when_warns(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "04-x", readme="## Tasks\n### Task 1 — x\nprose only\n")

    findings = cs.check_readme_structure(modules_dir, root)

    assert [f.severity for f in findings] == [cs.WARN]
    assert "Done when" in findings[0].message


def test_missing_task_headings_warns(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "04-x", readme="Just prose. Acceptance: it works.\n")

    findings = cs.check_readme_structure(modules_dir, root)

    assert [f.severity for f in findings] == [cs.WARN]
    assert "Task/Milestone" in findings[0].message


def test_well_formed_readme_has_no_structure_warnings(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "04-x")  # uses _GOOD_README

    assert cs.check_readme_structure(modules_dir, root) == []


# --- module-map ------------------------------------------------------------


def test_module_on_disk_missing_from_readme_warns(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "07-foo")
    (root / "README.md").write_text("no module references here\n", encoding="utf-8")
    (root / "CURRICULUM.md").write_text("## Module 07 — Foo\n", encoding="utf-8")

    findings = cs.check_module_map(modules_dir, root / "README.md", root / "CURRICULUM.md")

    assert any(
        f.rule == "module-map"
        and f.severity == cs.WARN
        and "not linked in README" in f.message
        and "07-foo" in f.message
        for f in findings
    )


def test_module_map_consistent_passes(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    _make_module(modules_dir, "07-foo")
    (root / "README.md").write_text("see modules/07-foo/README.md\n", encoding="utf-8")
    (root / "CURRICULUM.md").write_text("## Module 07 — Foo\n", encoding="utf-8")

    assert cs.check_module_map(modules_dir, root / "README.md", root / "CURRICULUM.md") == []


# --- language-support ------------------------------------------------------


def test_advertised_language_path_without_files_warns(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    readme = "Run modules/07-foo/ts/x.ts.\n### Task 1\n**Done when** ok\n"
    _make_module(modules_dir, "07-foo", readme=readme)

    findings = cs.check_language_support(modules_dir, root)

    assert any(
        f.rule == "language-support" and f.severity == cs.WARN and "ts/ path" in f.message
        for f in findings
    )


def test_advertised_language_path_with_files_ok(tmp_path: Path) -> None:
    root = tmp_path
    modules_dir = root / "modules"
    readme = "Run modules/07-foo/ts/x.ts.\n### Task 1\n**Done when** ok\n"
    module = _make_module(modules_dir, "07-foo", readme=readme)
    (module / "ts").mkdir()
    (module / "ts" / "x.ts").write_text("console.log(1)", encoding="utf-8")

    assert cs.check_language_support(modules_dir, root) == []


# --- manifest-schema -------------------------------------------------------


def test_schema_check_reports_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "m.json"
    bad.write_text("{ not json", encoding="utf-8")

    manifest, findings = cs.check_manifest_schema(bad)

    assert manifest is None
    assert len(findings) == 1
    assert findings[0].rule == "manifest-schema"
    assert findings[0].severity == cs.FATAL


def test_schema_check_reports_missing_file(tmp_path: Path) -> None:
    manifest, findings = cs.check_manifest_schema(tmp_path / "nope.json")

    assert manifest is None
    assert findings[0].rule == "manifest-schema"


def test_schema_check_accepts_valid_manifest(tmp_path: Path) -> None:
    good = tmp_path / "m.json"
    payload = Manifest(exercises=[_entry("modules/04-x/py/a.py")]).model_dump()
    good.write_text(json.dumps(payload), encoding="utf-8")

    manifest, findings = cs.check_manifest_schema(good)

    assert findings == []
    assert manifest is not None
    assert manifest.paths() == {"modules/04-x/py/a.py"}


# --- manifest-drift --------------------------------------------------------


def test_drift_check_passes_on_committed_manifest() -> None:
    from manifest import manifest_path

    assert cs.check_manifest_drift(manifest_path()) == []


def test_drift_check_flags_a_stale_manifest(tmp_path: Path) -> None:
    # A manifest whose bytes differ from a fresh regeneration must be flagged.
    stale = tmp_path / "exercise_manifest.json"
    stale.write_text('{"version": 1, "exercises": []}\n', encoding="utf-8")

    findings = cs.check_manifest_drift(stale)

    assert len(findings) == 1
    assert findings[0].rule == "manifest-drift"
    assert findings[0].severity == cs.FATAL


def test_drift_check_reports_missing_manifest(tmp_path: Path) -> None:
    findings = cs.check_manifest_drift(tmp_path / "nope.json")
    assert findings[0].rule == "manifest-drift"
    assert findings[0].severity == cs.FATAL


# --- override-guard --------------------------------------------------------


def test_override_guards_pass_on_real_repo() -> None:
    from manifest import repo_root

    assert cs.check_override_guards(repo_root()) == []


def _write_override_target(root: Path, rel: str, body: str) -> Path:
    target = root / rel
    target.parent.mkdir(parents=True)
    target.write_text(body, encoding="utf-8")
    return target


def test_override_guard_fails_when_source_token_removed(tmp_path: Path) -> None:
    import build_manifest

    # A guarded override target WITHOUT its required token must fire.
    rel, (token, _guarded) = next(iter(build_manifest.OVERRIDE_SOURCE_GUARDS.items()))
    _write_override_target(tmp_path, rel, "# guard removed on purpose\nprint('hi')\n")

    findings = cs.check_override_guards(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "override-guard"
    assert findings[0].severity == cs.FATAL
    assert token in findings[0].message
    assert rel in findings[0].message


def test_override_guard_passes_when_only_guarded_trigger_present(tmp_path: Path) -> None:
    import build_manifest

    # Token present AND the only network trigger is the guarded import (tiktoken).
    rel, (token, guarded) = next(iter(build_manifest.OVERRIDE_SOURCE_GUARDS.items()))
    body = f"import os\nimport {guarded}\n# {token} guard around the {guarded} call\n"
    _write_override_target(tmp_path, rel, body)

    assert cs.check_override_guards(tmp_path) == []


def test_override_guard_fails_on_unguarded_extra_trigger(tmp_path: Path) -> None:
    import build_manifest

    # Token KEPT, but the file also gained an UNguarded network import (httpx):
    # neutralising the guarded import is not enough, so the override is unsafe.
    rel, (token, guarded) = next(iter(build_manifest.OVERRIDE_SOURCE_GUARDS.items()))
    body = f"import os\nimport httpx\nimport {guarded}\n# {token} guard only covers {guarded}\n"
    _write_override_target(tmp_path, rel, body)

    findings = cs.check_override_guards(tmp_path)

    assert len(findings) == 1
    assert findings[0].rule == "override-guard"
    assert findings[0].severity == cs.FATAL
    assert "non-offline trigger" in findings[0].message
    assert rel in findings[0].message


# --- language-matrix + parity-policy ---------------------------------------


def _ex(module_dir: Path, lang: str, name: str = "ex") -> None:
    """Create a runnable exercise file under ``module_dir/<lang>/``."""
    lang_dir = module_dir / lang
    lang_dir.mkdir(exist_ok=True)
    suffix = "py" if lang == "py" else "ts"
    (lang_dir / f"{name}.{suffix}").write_text("x = 1\n", encoding="utf-8")


def _write_json(path: Path, obj: object) -> Path:
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _complete_policy_entry() -> dict[str, str]:
    return {
        "rationale": "intentional",
        "owner": "maintainer",
        "target_milestone": "n/a",
        "equivalent_path": "the other language path",
    }


def test_language_matrix_matches_disk_passes(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "04-x")
    _ex(module, "py")
    _ex(module, "ts")
    matrix = _write_json(tmp_path / "m.json", {"04-x": {"py": True, "ts": True}})

    assert cs.check_language_matrix(modules_dir, matrix) == []


def test_language_matrix_flags_module_absent_from_matrix(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "04-x")
    _ex(module, "py")
    _ex(module, "ts")
    matrix = _write_json(tmp_path / "m.json", {})  # module on disk, not in matrix

    findings = cs.check_language_matrix(modules_dir, matrix)
    assert [f.rule for f in findings] == ["language-matrix"]
    assert findings[0].severity == cs.FATAL
    assert "missing from the matrix" in findings[0].message


def test_language_matrix_flags_matrix_entry_with_no_dir(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    _make_module(modules_dir, "04-x")  # only 04-x exists on disk
    (modules_dir / "04-x" / "py").mkdir()
    _ex(modules_dir / "04-x", "py")
    _ex(modules_dir / "04-x", "ts")
    matrix = _write_json(
        tmp_path / "m.json",
        {"04-x": {"py": True, "ts": True}, "99-ghost": {"py": True, "ts": True}},
    )

    findings = cs.check_language_matrix(modules_dir, matrix)
    assert any("no dir: 99-ghost" in f.message for f in findings)
    assert all(f.severity == cs.FATAL for f in findings)


def test_language_matrix_flags_flag_disagreeing_with_disk(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "04-x")
    _ex(module, "py")  # only Python ships; no ts exercise
    matrix = _write_json(tmp_path / "m.json", {"04-x": {"py": True, "ts": True}})

    findings = cs.check_language_matrix(modules_dir, matrix)
    assert len(findings) == 1
    assert "matrix says ts=True but disk has ts=False" in findings[0].message


def test_language_matrix_reports_missing_file(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    _make_module(modules_dir, "04-x")
    findings = cs.check_language_matrix(modules_dir, tmp_path / "absent.json")
    assert findings[0].rule == "language-matrix"
    assert "missing" in findings[0].message


def test_parity_policy_full_parity_needs_no_entry(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "04-x")
    _ex(module, "py")
    _ex(module, "ts")
    policy = _write_json(tmp_path / "p.json", {})  # empty is fine for a full-parity module

    assert cs.check_parity_policy(modules_dir, policy) == []


def test_parity_policy_single_language_without_entry_fails(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "10-x")
    _ex(module, "py")  # Python-only, no policy entry
    policy = _write_json(tmp_path / "p.json", {})

    findings = cs.check_parity_policy(modules_dir, policy)
    assert len(findings) == 1
    assert findings[0].severity == cs.FATAL
    assert "no parity_policy.json entry" in findings[0].message


def test_parity_policy_single_language_with_complete_entry_passes(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "10-x")
    _ex(module, "py")
    policy = _write_json(tmp_path / "p.json", {"10-x": _complete_policy_entry()})

    assert cs.check_parity_policy(modules_dir, policy) == []


def test_parity_policy_entry_missing_a_field_fails(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "10-x")
    _ex(module, "py")
    entry = _complete_policy_entry()
    del entry["owner"]
    policy = _write_json(tmp_path / "p.json", {"10-x": entry})

    findings = cs.check_parity_policy(modules_dir, policy)
    assert len(findings) == 1
    assert "missing field(s): owner" in findings[0].message


def test_parity_policy_flags_entry_for_missing_module(tmp_path: Path) -> None:
    modules_dir = tmp_path / "modules"
    module = _make_module(modules_dir, "04-x")
    _ex(module, "py")
    _ex(module, "ts")
    policy = _write_json(tmp_path / "p.json", {"99-ghost": _complete_policy_entry()})

    findings = cs.check_parity_policy(modules_dir, policy)
    assert any("no dir: 99-ghost" in f.message for f in findings)


# --- the real repo ---------------------------------------------------------


def test_real_repo_has_no_fatal_findings() -> None:
    fatal = [f for f in cs.run_checks() if f.severity == cs.FATAL]
    assert fatal == [], fatal


def test_main_on_real_repo_exits_zero() -> None:
    assert cs.main([]) == 0
