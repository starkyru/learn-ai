"""Tests for the offline smoke runner and its in-process network tripwire.

Real code is imported and driven directly; the only mocked boundaries are the
filesystem (``tmp_path``) and env (``monkeypatch``). The escape/leak/kill/write
tests are the discriminating ones — each proves a specific hardening holds at
runtime, the kind of guarantee static analysis cannot give. The guard is a
tripwire for honest mistakes, not a sandbox (OS-level CI isolation is the real
boundary), so these assert the common in-process paths, not exhaustive denial.
"""

from __future__ import annotations

import os
import socket
import textwrap
import time
from pathlib import Path

import net_guard
import pytest
import smoke_exercises as sx
from manifest import ExerciseEntry, load_manifest, repo_root


def _entry(
    path: str,
    *,
    offline: str = "offline",
    artifacts: list[str] | None = None,
    timeout: int = 30,
    command: str | None = None,
) -> ExerciseEntry:
    language = "py" if path.endswith(".py") else "ts"
    default_cmd = f"uv run python {path}" if language == "py" else f"pnpm tsx {path}"
    return ExerciseEntry(
        path=path,
        module=path.split("/")[1],
        language=language,
        command=command or default_cmd,
        offline=offline,  # type: ignore[arg-type]
        timeout_s=timeout,
        expected_artifacts=artifacts or [],
        exclude_reason="" if offline == "offline" else "excluded for tests",
    )


def _write(root: Path, rel: str, body: str) -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


# --- net_guard: pure allow/deny logic --------------------------------------


def test_guard_denies_public_and_hostname() -> None:
    assert net_guard._is_loopback_host("1.2.3.4") is False
    assert net_guard._is_loopback_host("example.com") is False


def test_guard_allows_loopback_and_unspecified() -> None:
    assert net_guard._is_loopback_host("127.0.0.1") is True
    assert net_guard._is_loopback_host("127.9.9.9") is True  # 127.0.0.0/8
    assert net_guard._is_loopback_host("::1") is True
    assert net_guard._is_loopback_host("localhost") is True
    assert net_guard._is_loopback_host(None) is True
    assert net_guard._is_loopback_host("0.0.0.0") is True  # unspecified


def test_guard_addr_allowed_treats_string_as_unix() -> None:
    assert net_guard._addr_allowed(socket.AF_INET, "/tmp/x.sock") is True
    assert net_guard._addr_allowed(socket.AF_INET, ("1.2.3.4", 80)) is False


# --- env allowlist ----------------------------------------------------------


def test_child_env_allowlist_drops_secrets_and_proxies(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("HTTPS_PROXY", "http://user:pw@proxy:8080")
    monkeypatch.setenv("UV_INDEX_URL", "https://user:pw@index/simple")
    monkeypatch.setenv("PATH", "/usr/bin")

    env = sx._child_env()

    assert "OPENAI_API_KEY" not in env
    assert "HTTPS_PROXY" not in env
    assert "UV_INDEX_URL" not in env
    assert env["PATH"] == "/usr/bin"
    assert env["OFFLINE_SMOKE"] == "1"
    assert env["CI"] == "1"


def test_child_env_forwards_only_explicit_locale_keys(monkeypatch) -> None:
    # An LC_* wildcard would leak a secret named LC_*; only the explicit set passes.
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    monkeypatch.setenv("LC_SECRET", "leak-me")

    env = sx._child_env()

    assert env["LC_ALL"] == "C.UTF-8"
    assert "LC_SECRET" not in env


# --- the real offline entries ----------------------------------------------


def test_real_offline_entries_all_pass() -> None:
    root = repo_root()
    offline = [e for e in load_manifest().exercises if e.offline == "offline"]
    assert len(offline) >= 4

    results = sx.run_smoke(offline, root)

    non_passing = [(r.path, r.status, r.reason) for r in results if r.status != sx.PASSED]
    assert non_passing == [], non_passing


def test_real_run_leaves_no_seed_db_artifact() -> None:
    root = repo_root()
    offline = [e for e in load_manifest().exercises if e.offline == "offline"]
    sx.run_smoke(offline, root)
    assert not (root / "modules" / "12-text-to-sql" / "sales.db").exists()


# --- network violations: TCP connect ---------------------------------------


def test_python_tcp_connect_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/tcp.py",
        "import socket\nsocket.create_connection(('1.2.3.4', 80), timeout=1)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/tcp.py"), tmp_path)
    assert result.status == sx.VIOLATION, result
    assert net_guard.VIOLATION_SENTINEL in result.reason


def test_typescript_tcp_connect_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/tcp.ts",
        'import net from "node:net";\n'
        'const s = net.connect(80, "1.2.3.4");\n'
        's.on("error", () => {});\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/tcp.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


# --- network violations: UDP -----------------------------------------------


def test_python_udp_sendto_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/udp.py",
        "import socket\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
        "s.sendto(b'x', ('1.2.3.4', 53))\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/udp.py"), tmp_path)
    assert result.status == sx.VIOLATION, result
    assert "sendto" in result.reason


def test_typescript_udp_send_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/udp.ts",
        'import dgram from "node:dgram";\n'
        'const s = dgram.createSocket("udp4");\n'
        's.send(Buffer.from("x"), 53, "1.2.3.4", () => {});\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/udp.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_typescript_udp_connect_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/udpc.ts",
        'import dgram from "node:dgram";\n'
        'const s = dgram.createSocket("udp4");\n'
        's.connect(53, "1.2.3.4");\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/udpc.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


# --- network violations: DNS -----------------------------------------------


def test_python_dns_getaddrinfo_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/dns.py",
        "import socket\nsocket.getaddrinfo('example.com', 80)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/dns.py"), tmp_path)
    assert result.status == sx.VIOLATION, result
    assert "getaddrinfo" in result.reason


def test_python_gethostbyname_ex_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/ghbnex.py",
        "import socket\nsocket.gethostbyname_ex('example.com')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/ghbnex.py"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_python_gethostbyaddr_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/ghba.py",
        "import socket\nsocket.gethostbyaddr('1.2.3.4')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/ghba.py"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_python_getnameinfo_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/gni.py",
        "import socket\nsocket.getnameinfo(('1.2.3.4', 80), 0)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/gni.py"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_typescript_dns_lookup_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/dns.ts",
        'import dns from "node:dns";\ndns.lookup("example.com", () => {});\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/dns.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_typescript_dns_reverse_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/rev.ts",
        'import dns from "node:dns";\ndns.reverse("1.2.3.4", () => {});\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/rev.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_typescript_dns_lookupservice_public_is_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/ts/svc.ts",
        'import dns from "node:dns";\ndns.lookupService("1.2.3.4", 80, () => {});\n',
    )
    result = sx.run_entry(_entry("modules/99-x/ts/svc.ts"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_python_loopback_dns_is_allowed(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/loop_dns.py",
        "import socket\nassert socket.getaddrinfo('localhost', 80)\nprint('ok')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/loop_dns.py"), tmp_path)
    assert result.status == sx.PASSED, result


# --- reload resilience ------------------------------------------------------


def test_python_reload_socket_then_connect_is_still_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/reload.py",
        "import importlib, socket\n"
        "importlib.reload(socket)\n"
        "socket.create_connection(('1.2.3.4', 80), timeout=1)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/reload.py"), tmp_path)
    assert result.status == sx.VIOLATION, result


def test_python_loopback_connect_is_not_a_violation(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "modules/99-x/py/loop.py",
        "import socket\nsocket.create_connection(('127.0.0.1', 1), timeout=1)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/loop.py"), tmp_path)
    assert result.status != sx.VIOLATION
    assert result.status == sx.FAILED  # connection refused, no listener


# --- secret stripping (end to end) -----------------------------------------


def test_provider_secrets_are_stripped_from_child(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("HTTPS_PROXY", "http://user:pw@host:8080")
    _write(
        tmp_path,
        "modules/99-x/py/env.py",
        "import os, sys\n"
        "leaked = [k for k in ('OPENAI_API_KEY', 'HTTPS_PROXY') if k in os.environ]\n"
        "sys.exit(0 if not leaked else 9)\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/env.py"), tmp_path)
    assert result.status == sx.PASSED, result


# --- timeout kills the whole process group ---------------------------------


def test_timeout_kills_grandchild_even_after_leader_exits(tmp_path: Path) -> None:
    # The leader spawns a grandchild (inheriting the pipes) then EXITS. The parent
    # runner blocks in communicate() until the grandchild also closes them, so the
    # timeout fires and the CAPTURED process-group id — not a re-derived pgid of
    # the now-dead leader — is what kills the grandchild.
    marker = tmp_path / "grandchild.log"
    grandchild = (
        "import time\n"
        "while True:\n"
        f"    with open(r'{marker}', 'a') as f:\n"
        "        f.write('x')\n"
        "    time.sleep(0.05)\n"
    )
    body = textwrap.dedent(f"""
        import subprocess, sys
        subprocess.Popen([sys.executable, "-c", {grandchild!r}])
        sys.exit(0)
    """)
    _write(tmp_path, "modules/99-x/py/spawn.py", body)

    result = sx.run_entry(_entry("modules/99-x/py/spawn.py", timeout=1), tmp_path)
    assert result.status == sx.TIMEOUT

    time.sleep(0.5)
    size_after_kill = marker.stat().st_size if marker.exists() else 0
    time.sleep(1.0)
    size_later = marker.stat().st_size if marker.exists() else 0
    assert size_later == size_after_kill  # grandchild stopped writing → dead


# --- exit code / artifacts / undeclared writes -----------------------------


def test_nonzero_exit_is_failed(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/boom.py", "import sys\nsys.exit(3)\n")
    result = sx.run_entry(_entry("modules/99-x/py/boom.py"), tmp_path)
    assert result.status == sx.FAILED
    assert result.returncode == 3


def test_missing_declared_artifact_is_failed(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/quiet.py", "print('did nothing')\n")
    entry = _entry("modules/99-x/py/quiet.py", artifacts=["modules/99-x/out.txt"])
    result = sx.run_entry(entry, tmp_path)
    assert result.status == sx.FAILED
    assert "missing expected_artifacts" in result.reason


def test_cwd_artifact_present_passes_in_isolation(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/writer.py", "open('out.txt', 'w').write('hi')\n")
    entry = _entry("modules/99-x/py/writer.py", artifacts=["out.txt"])
    result = sx.run_entry(entry, tmp_path)
    assert result.status == sx.PASSED


def test_undeclared_new_repo_write_is_failed_and_cleaned(tmp_path: Path) -> None:
    # Git-independent: no git init; the whole-worktree hash detects the new file.
    _write(
        tmp_path,
        "modules/99-x/py/stray_writer.py",
        "import os\nopen(os.path.join(os.path.dirname(__file__), 'stray.txt'), 'w').write('x')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/stray_writer.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "undeclared repo write" in result.reason
    assert not (tmp_path / "modules/99-x/py/stray.txt").exists()  # cleaned up


def test_undeclared_overwrite_in_a_different_module_is_failed(tmp_path: Path) -> None:
    # An exercise in module 99-x overwrites a PRE-EXISTING file in module 88-y.
    # A module-subtree-only check would miss this; the whole-worktree hash catches
    # it. No git needed.
    victim = _write(tmp_path, "modules/88-y/py/victim.txt", "ORIGINAL\n")
    _write(
        tmp_path,
        "modules/99-x/py/over.py",
        f"open(r'{victim}', 'w').write('OVERWRITTEN\\n')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/over.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "undeclared repo write" in result.reason
    assert "modules/88-y/py/victim.txt" in result.reason


def test_repo_write_detection_fails_closed(tmp_path, monkeypatch) -> None:
    # If the worktree snapshot cannot be taken, the entry FAILS (never a silent
    # pass) — the git-independent detection has no fail-open path.
    _write(tmp_path, "modules/99-x/py/ok.py", "print('ok')\n")

    def boom(root, declared):
        raise sx.WorktreeSnapshotError("simulated snapshot failure")

    monkeypatch.setattr(sx, "_snapshot_worktree", boom)

    result = sx.run_entry(_entry("modules/99-x/py/ok.py"), tmp_path)
    assert result.status == sx.FAILED
    assert "could not verify repo state" in result.reason


def test_write_under_repo_owned_output_dir_is_failed(tmp_path: Path) -> None:
    # site/ is a REPO-OWNED output dir (the docs build) — it must NOT be excluded.
    (tmp_path / "site").mkdir()
    (tmp_path / "site" / "index.html").write_text("old", encoding="utf-8")
    _write(
        tmp_path,
        "modules/99-x/py/site_writer.py",
        f"open(r'{tmp_path / 'site' / 'stray.html'}', 'w').write('leak')\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/site_writer.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "site/stray.html" in result.reason


def test_snapshot_fails_closed_on_unreadable_file(tmp_path: Path) -> None:
    if os.name != "posix" or (hasattr(os, "geteuid") and os.geteuid() == 0):
        pytest.skip("chmod-based unreadable file requires a non-root POSIX host")
    _write(tmp_path, "modules/99-x/py/ok.py", "print('ok')\n")
    secret = _write(tmp_path, "modules/99-x/py/secret.dat", "topsecret\n")
    os.chmod(secret, 0)
    try:
        result = sx.run_entry(_entry("modules/99-x/py/ok.py"), tmp_path)
    finally:
        os.chmod(secret, 0o644)

    assert result.status == sx.FAILED
    assert "could not verify repo state" in result.reason


def test_large_same_size_mtime_restored_rewrite_is_detected(tmp_path: Path) -> None:
    # A >8 MiB file overwritten with the SAME size and its mtime restored: the old
    # size+mtime fingerprint would miss it; content hashing catches it.
    big = _write(tmp_path, "modules/88-y/data.bin", "A" * (9 * 1024 * 1024))
    _write(
        tmp_path,
        "modules/99-x/py/rewrite.py",
        f"import os\n"
        f"p = r'{big}'\n"
        f"st = os.stat(p)\n"
        f"open(p, 'w').write('B' * (9 * 1024 * 1024))\n"
        f"os.utime(p, (st.st_atime, st.st_mtime))\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/rewrite.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "modules/88-y/data.bin" in result.reason


def test_empty_directory_artifact_is_not_a_pass(tmp_path: Path) -> None:
    # An exercise that creates its declared artifact as an empty DIRECTORY must
    # NOT pass, and the directory must not be left behind.
    _write(
        tmp_path,
        "modules/12-x/py/seed.py",
        "import os\nos.makedirs(os.path.join(os.path.dirname(__file__), '..', 'out.db'))\n",
    )
    entry = _entry("modules/12-x/py/seed.py", artifacts=["modules/12-x/out.db"])
    result = sx.run_entry(entry, tmp_path)

    assert result.status == sx.FAILED
    assert "missing expected_artifacts" in result.reason
    assert not (tmp_path / "modules/12-x/out.db").exists()  # residue removed


def test_artifact_cleanup_failure_fails_the_entry(tmp_path, monkeypatch) -> None:
    # A cleanup/restore failure must turn an otherwise-passing entry into FAILED,
    # never a silent pass that leaves residue.
    _write(tmp_path, "modules/99-x/py/ok.py", "print('ok')\n")
    monkeypatch.setattr(sx, "_restore_artifacts", lambda declared_abs, backups: ["cleanup boom"])

    result = sx.run_entry(_entry("modules/99-x/py/ok.py"), tmp_path)
    assert result.status == sx.FAILED
    assert "artifact cleanup failed" in result.reason


def test_empty_directory_write_is_detected_and_removed(tmp_path: Path) -> None:
    # An exercise that creates an empty repo directory (no files) must be caught
    # by the topology snapshot and the directory removed.
    _write(
        tmp_path,
        "modules/99-x/py/mkdir.py",
        "import os\nos.makedirs(os.path.join(os.path.dirname(__file__), 'newdir'))\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/mkdir.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "undeclared repo write" in result.reason
    assert "modules/99-x/py/newdir" in result.reason
    assert not (tmp_path / "modules/99-x/py/newdir").exists()  # removed


def test_symlinked_directory_write_is_detected(tmp_path: Path) -> None:
    (tmp_path / "modules" / "88-y").mkdir(parents=True)
    target = tmp_path / "modules" / "88-y"
    _write(
        tmp_path,
        "modules/99-x/py/symdir.py",
        f"import os\nos.symlink(r'{target}', os.path.join(os.path.dirname(__file__), 'link'))\n",
    )
    result = sx.run_entry(_entry("modules/99-x/py/symdir.py"), tmp_path)

    assert result.status == sx.FAILED
    assert "undeclared repo write" in result.reason
    assert not (tmp_path / "modules/99-x/py/link").is_symlink()  # removed


def test_symlink_declared_artifact_is_not_a_pass(tmp_path: Path) -> None:
    # A declared artifact implemented as a SYMLINK to some real file is not the
    # produced output — lstat rejects it, so the entry fails as "missing".
    real = _write(tmp_path, "modules/12-x/real.txt", "hi")
    _write(
        tmp_path,
        "modules/12-x/py/sym.py",
        f"import os\n"
        f"link = os.path.join(os.path.dirname(__file__), '..', 'out.db')\n"
        f"os.symlink(r'{real}', link)\n",
    )
    entry = _entry("modules/12-x/py/sym.py", artifacts=["modules/12-x/out.db"])
    result = sx.run_entry(entry, tmp_path)

    assert result.status == sx.FAILED
    assert "missing expected_artifacts" in result.reason


def test_absolute_artifact_path_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/ok.py", "print('ok')\n")
    entry = _entry("modules/99-x/py/ok.py", artifacts=["/etc/passwd"])
    result = sx.run_entry(entry, tmp_path)

    assert result.status == sx.FAILED
    assert "invalid declared artifact path" in result.reason


def test_dotdot_traversal_artifact_path_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/ok.py", "print('ok')\n")
    entry = _entry("modules/99-x/py/ok.py", artifacts=["../../etc/x"])
    result = sx.run_entry(entry, tmp_path)

    assert result.status == sx.FAILED
    assert "invalid declared artifact path" in result.reason


# --- flags / batch isolation -----------------------------------------------


def test_flags_from_command_extracts_stub_flag() -> None:
    entry = _entry(
        "modules/06c-agent-frameworks/py/01_lcel.py",
        offline="stub",
        command="uv run python modules/06c-agent-frameworks/py/01_lcel.py --stub",
    )
    assert sx._flags_from_command(entry) == ["--stub"]


def test_flags_from_command_raises_on_path_mismatch() -> None:
    bad = ExerciseEntry.model_construct(
        path="modules/99-x/py/a.py",
        module="99-x",
        language="py",
        command="uv run python modules/99-x/py/OTHER.py",
        offline="offline",
        timeout_s=30,
        extras=[],
        expected_artifacts=[],
        exclude_reason="",
    )
    try:
        sx._flags_from_command(bad)
    except ValueError as exc:
        assert "does not reference its path" in str(exc)
    else:
        raise AssertionError("expected ValueError on path/command mismatch")


def test_batch_isolates_a_missing_target(tmp_path: Path) -> None:
    _write(tmp_path, "modules/99-x/py/present.py", "print('ok')\n")
    entries = [
        _entry("modules/99-x/py/present.py"),
        _entry("modules/99-x/py/absent.py"),  # file not created
    ]
    results = {r.path: r for r in sx.run_smoke(entries, tmp_path)}
    assert results["modules/99-x/py/present.py"].status == sx.PASSED
    assert results["modules/99-x/py/absent.py"].status == sx.SKIPPED


# --- driver ----------------------------------------------------------------


def test_main_on_real_repo_exits_zero() -> None:
    assert sx.main([]) == 0
