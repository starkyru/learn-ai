"""Tests for the exercise manifest: pydantic schema + the real committed file.

These import the real ``manifest`` module (no reimplemented logic) and assert
against hand-written expected values, not values recomputed by the code under
test.
"""

from __future__ import annotations

from pathlib import Path

import build_manifest as bm
import pytest
from manifest import (
    ExerciseEntry,
    Manifest,
    is_exercise_file,
    iter_exercise_files,
    load_manifest,
    modules_root,
    repo_root,
)
from pydantic import ValidationError


def _entry(path: str, offline: str = "offline", reason: str = "", **over: object) -> ExerciseEntry:
    module = path.split("/")[1]
    language = "py" if path.endswith(".py") else "ts"
    command = over.pop("command", None) or (
        f"uv run python {path}" if language == "py" else f"pnpm tsx {path}"
    )
    return ExerciseEntry(
        path=path,
        module=module,
        language=language,
        command=str(command),
        offline=offline,  # type: ignore[arg-type]
        timeout_s=int(over.pop("timeout_s", 30)),
        exclude_reason=reason,
        extras=list(over.pop("extras", [])),  # type: ignore[arg-type]
        expected_artifacts=list(over.pop("expected_artifacts", [])),  # type: ignore[arg-type]
    )


# --- the real committed manifest -------------------------------------------


def test_real_manifest_loads_and_validates() -> None:
    manifest = load_manifest()
    assert manifest.version == 1
    assert len(manifest.exercises) > 100


def test_real_manifest_registers_every_on_disk_entrypoint() -> None:
    manifest = load_manifest()
    root = repo_root()
    on_disk = {p.relative_to(root).as_posix() for p in iter_exercise_files(modules_root())}
    # Exact set equality: no unregistered file, no phantom entry.
    assert manifest.paths() == on_disk


def test_real_manifest_exclude_reason_invariant() -> None:
    for entry in load_manifest().exercises:
        if entry.offline == "offline":
            assert entry.exclude_reason == "", entry.path
        else:
            assert entry.exclude_reason.strip(), entry.path


# Hand-verified classifications, each tied to a concrete source marker:
#  offline  = self-contained (bpe worked example / sqlite seed)
#  stub     = raises NotImplementedError / throws TODO until solved
#  provider = calls a provider (get_provider / hosted client) or an MCP server
#  download = imports a heavy local stack (torch/peft) or needs a browser binary
_EXPECTED_STATUS = {
    "modules/01-fundamentals/py/bpe.py": "offline",
    "modules/12-text-to-sql/py/seed_db.py": "offline",
    "modules/13-fine-tuning/ts/03-lora-local-note.ts": "offline",
    "modules/01b-ml-foundations/py/01_linear_regression.py": "stub",
    "modules/06c-agent-frameworks/py/01_lcel.py": "stub",
    "modules/10-image-generation/py/toy_diffusion.py": "stub",
    "modules/05-rag/py/01_naive_rag.py": "provider",
    "modules/17-mcp/py/02_use_mcp_server.py": "provider",
    # only external dependency is tiktoken (no get_provider) → network → provider
    "modules/16-context-engineering/py/06_tool_offloading.py": "provider",
    "modules/13-fine-tuning/py/03_lora_local.py": "download",
    "modules/18-computer-use/py/01_browser_basics.py": "download",
}


def test_real_manifest_known_classifications() -> None:
    by_path = {e.path: e for e in load_manifest().exercises}
    for path, expected in _EXPECTED_STATUS.items():
        assert by_path[path].offline == expected, path


def test_seed_db_offline_declares_sqlite_artifact() -> None:
    by_path = {e.path: e for e in load_manifest().exercises}
    entry = by_path["modules/12-text-to-sql/py/seed_db.py"]
    assert entry.offline == "offline"
    assert entry.expected_artifacts == ["modules/12-text-to-sql/sales.db"]


def test_real_manifest_commands_reference_their_path_and_language() -> None:
    for entry in load_manifest().exercises:
        assert entry.path in entry.command
        if entry.language == "py":
            assert entry.command.startswith("uv run ")
            assert " python " in entry.command
        else:
            assert entry.command.startswith("pnpm tsx ")


def test_stub_mode_entries_pass_the_stub_flag() -> None:
    # 06c/06d ship a `--stub` mode; the generated command must actually pass it,
    # so classification (which suppresses provider for these) matches execution.
    by_path = {e.path: e for e in load_manifest().exercises}
    entry = by_path["modules/06c-agent-frameworks/py/01_lcel.py"]
    assert entry.offline == "stub"
    assert entry.command.endswith(" --stub")


def test_offline_bpe_command_has_no_stub_flag() -> None:
    by_path = {e.path: e for e in load_manifest().exercises}
    assert by_path["modules/01-fundamentals/py/bpe.py"].command == (
        "uv run python modules/01-fundamentals/py/bpe.py"
    )


def test_committed_manifest_bytes_match_generated() -> None:
    # The committed file must be byte-identical to a fresh regeneration through
    # the one canonical serializer — the same invariant the drift check enforces.
    from manifest import manifest_path, serialize_manifest

    generated = serialize_manifest(bm.build())
    assert generated == manifest_path().read_text(encoding="utf-8")


# --- classifier behaviour (import the real classify) -----------------------


def test_classify_flags_tiktoken_user_as_provider() -> None:
    # A file whose only external dependency is tiktoken must NOT be offline: its
    # get_encoding()/encoding_for_model() download the vocab blob over the network.
    source = "import tiktoken\nenc = tiktoken.get_encoding('cl100k_base')\n"
    status, reason = bm.classify("01-fundamentals", "py", source, {"tiktoken"}, False)
    assert status == "provider"
    assert "tiktoken" in reason or "network" in reason.lower()


def test_classify_stub_mode_only_suppresses_when_flag_passed() -> None:
    # get_provider + NotImplementedError: with the --stub path active it is a
    # stub (runs offline once solved); without it, it needs a provider.
    source = "from llm_core import get_provider\nraise NotImplementedError\n"
    assert bm.classify("06c-agent-frameworks", "py", source, set(), True)[0] == "stub"
    assert bm.classify("06c-agent-frameworks", "py", source, set(), False)[0] == "provider"


# --- pydantic schema enforcement -------------------------------------------


def test_valid_entry_constructs() -> None:
    entry = _entry("modules/04-x/py/a.py", offline="stub", reason="todo")
    assert entry.language == "py"
    assert entry.module == "04-x"


def test_invalid_offline_value_rejected() -> None:
    with pytest.raises(ValidationError):
        _entry("modules/04-x/py/a.py", offline="sometimes")


def test_language_extension_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        ExerciseEntry(
            path="modules/04-x/py/a.py",
            module="04-x",
            language="ts",  # mismatches .py
            command="uv run python modules/04-x/py/a.py",
            offline="offline",
            timeout_s=30,
        )


def test_command_must_reference_path_rejected() -> None:
    with pytest.raises(ValidationError):
        ExerciseEntry(
            path="modules/04-x/py/a.py",
            module="04-x",
            language="py",
            command="uv run python modules/04-x/py/OTHER.py",
            offline="offline",
            timeout_s=30,
        )


def test_module_must_match_path_rejected() -> None:
    with pytest.raises(ValidationError):
        ExerciseEntry(
            path="modules/04-x/py/a.py",
            module="99-wrong",
            language="py",
            command="uv run python modules/04-x/py/a.py",
            offline="offline",
            timeout_s=30,
        )


def test_path_must_be_under_modules_rejected() -> None:
    with pytest.raises(ValidationError):
        _entry("scripts/foo.py")


def test_non_positive_timeout_rejected() -> None:
    with pytest.raises(ValidationError):
        _entry("modules/04-x/py/a.py", timeout_s=0)


def test_manifest_rejects_duplicate_paths() -> None:
    dup = _entry("modules/04-x/py/a.py")
    with pytest.raises(ValidationError):
        Manifest(exercises=[dup, dup])


def test_manifest_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Manifest.model_validate({"version": 1, "exercises": [], "surprise": True})


# --- enumerator / file-filter rules ----------------------------------------


def test_is_exercise_file_rules() -> None:
    assert is_exercise_file(Path("m/py/foo.py"))
    assert is_exercise_file(Path("m/ts/foo.ts"))
    assert not is_exercise_file(Path("m/py/test_foo.py"))
    assert not is_exercise_file(Path("m/py/foo_test.py"))
    assert not is_exercise_file(Path("m/ts/foo.test.ts"))
    assert not is_exercise_file(Path("m/ts/foo.spec.ts"))
    assert not is_exercise_file(Path("m/py/.hidden.py"))
    assert not is_exercise_file(Path("m/README.md"))
    # TS test files (both `test_*.ts` and `*.test.ts`) are excluded too
    assert not is_exercise_file(Path("m/ts/test_foo.ts"))
    # test infrastructure sibling tasks may add — must never be registered
    assert not is_exercise_file(Path("m/py/conftest.py"))
    assert not is_exercise_file(Path("m/py/__tests__/helper.py"))
    assert not is_exercise_file(Path("m/ts/__tests__/helper.ts"))
    assert not is_exercise_file(Path("m/py/tests/helper.py"))
    assert not is_exercise_file(Path("m/ts/tests/helper.ts"))


def test_iter_exercise_files_filters_tests_and_vendor(tmp_path: Path) -> None:
    root = tmp_path / "modules"
    py = root / "04-x" / "py"
    ts = root / "04-x" / "ts"
    py.mkdir(parents=True)
    ts.mkdir(parents=True)
    (py / "foo.py").write_text("x", encoding="utf-8")
    (py / "test_foo.py").write_text("x", encoding="utf-8")
    (py / "conftest.py").write_text("x", encoding="utf-8")
    (py / "__pycache__").mkdir()
    (py / "__pycache__" / "cached.py").write_text("x", encoding="utf-8")
    (py / "__tests__").mkdir()
    (py / "__tests__" / "helper.py").write_text("x", encoding="utf-8")
    (py / "tests").mkdir()
    (py / "tests" / "unit.py").write_text("x", encoding="utf-8")
    (ts / "a.ts").write_text("x", encoding="utf-8")
    (ts / "a.test.ts").write_text("x", encoding="utf-8")
    (ts / "test_a.ts").write_text("x", encoding="utf-8")
    (ts / "node_modules").mkdir()
    (ts / "node_modules" / "dep.ts").write_text("x", encoding="utf-8")
    (ts / "tests").mkdir()
    (ts / "tests" / "unit.ts").write_text("x", encoding="utf-8")

    found = {p.name for p in iter_exercise_files(root)}
    assert found == {"foo.py", "a.ts"}
