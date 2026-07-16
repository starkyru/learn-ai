"""Generate ``exercise_manifest.json`` by classifying every exercise entrypoint.

Run from the repo root:

    uv run python scripts/curriculum/build_manifest.py

The manifest is checked in; regenerate it whenever exercises are added, removed,
or their run requirements change, then review the diff. Classification is
deterministic and reproducible: it reads each file's source and applies the
precedence documented in :func:`classify` — it never executes the exercise.

The classification is intentionally CONSERVATIVE: a file is only ``offline`` when
its source shows no provider/network/heavy-download/stub markers at all. When in
doubt the file lands in a non-offline bucket with a reason, because the offline
bucket is the set the default CI smoke runner will actually execute.

Detection is anchored to real ``import``/``from ... import`` statements (not bare
words in prose), so a comment mentioning "transformers" or "datasets" does not
misclassify an otherwise-offline file.
"""

from __future__ import annotations

import re

from manifest import (
    ExerciseEntry,
    Manifest,
    iter_exercise_files,
    manifest_path,
    modules_root,
    repo_root,
    serialize_manifest,
)

# --- import extraction (anchored, not prose) -------------------------------

# Top-level package of each Python ``import x`` / ``from x import ...`` line.
_PY_IMPORT = re.compile(r"(?m)^[ \t]*(?:import|from)[ \t]+([A-Za-z_][\w]*)")
# Module specifier of each TS ``import ... from "spec"`` / ``import "spec"``.
_TS_IMPORT = re.compile(r"""(?:from|import)\s+["']([^"']+)["']""")

# Packages that pull a multi-GB local model/weights download.
_HEAVY_PKGS = {
    "torch",
    "torchvision",
    "diffusers",
    "transformers",
    "peft",
    "datasets",
    "accelerate",
    "faster_whisper",  # downloads Whisper weights on first use
}
# Python packages whose import means "this needs an external provider/service".
# ``huggingface_hub`` is here (not in _HEAVY_PKGS) because these exercises use its
# hosted ``InferenceClient`` (needs an HF token), not a local weights download.
_PROVIDER_PKGS = {
    "openai",
    "anthropic",
    "image_client",  # module 10's hosted image REST client (httpx + API keys)
    "huggingface_hub",
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_ollama",
    "langgraph",
}
_ENV_KEY = re.compile(
    r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|NVIDIA_API_KEY"
    r"|REPLICATE_API_TOKEN|STABILITY_API_KEY|\bIMAGE_PROVIDER\b"
)
# Residual outbound network that is not itself a provider call. Submodule- or
# call-qualified patterns live here (where the bare top-level import name would be
# ambiguous, e.g. urllib.request is network but urllib.parse is not). This is
# best-effort STATIC detection; the runtime socket denial in smoke_exercises.py is
# the actual guarantee.
_NETWORK = re.compile(
    r"\bhttpx\b|requests\.(?:get|post)|feedparser"
    r"|urllib\.request|http\.client"
    r"|asyncio\.open_connection|asyncio\.start_server|\.create_connection\("
    r"|\bWebSocket\b|\bfetch\("
)
# Python packages whose IMPORT signals outbound network. ``tiktoken`` belongs here
# (``get_encoding``/``encoding_for_model`` download the BPE-vocab blob on first
# use); the rest are network-specific stdlib/3rd-party modules. Import-anchored, so
# a comment mentioning "socket" does not trip an otherwise-offline file.
_NETWORK_PKGS = {
    "tiktoken",
    "socket",
    "aiohttp",
    "ftplib",
    "smtplib",
    "websockets",
}
_PY_STUB = re.compile(r"raise NotImplementedError|NotImplementedError\(")
_TS_STUB = re.compile(r"throw new Error\(")
# 06c/06d ship a deterministic ``--stub`` model, so their provider use is
# optional; they run offline once the learner core is implemented. This matches
# the literal CLI flag only, and ``build()`` appends ``--stub`` to the generated
# command for exactly these files, so classification and execution stay in
# lockstep (a solved file still runs its stub branch, never the provider branch).
_STUB_MODE = re.compile(r"--stub")

# import name → uv extra (unambiguous mappings only)
_EXTRA_BY_PKG = {
    "diffusers": "imagegen",
    "peft": "finetune",
    "datasets": "finetune",
    "faster_whisper": "audio",
    "soundfile": "audio",
    "playwright": "browser",
    "fastapi": "production",
    "uvicorn": "production",
    "langfuse": "production",
    "langgraph": "agents",
    "langchain": "agents",
    "langchain_core": "agents",
    "langchain_openai": "agents",
    "langchain_anthropic": "agents",
    "langchain_ollama": "agents",
    "sklearn": "ml",
    "chromadb": "vectors",
    "qdrant_client": "vectors",
    "rank_bm25": "vectors",
    "pypdf": "ingest",
    "bs4": "ingest",
    "lxml": "ingest",
    "fitz": "ingest",  # PyMuPDF imports as `fitz`
    "mcp": "mcp",
}
# torch/torchvision/transformers map to different extras per module family.
_TORCH_EXTRA_BY_PREFIX = {"09": "vision", "10": "imagegen", "13": "finetune"}

_TIMEOUT_BY_BUCKET = {"offline": 60, "stub": 30, "provider": 120, "download": 600}

# Files that write known artifacts (only offline entries need these accurate).
_ARTIFACTS: dict[str, list[str]] = {
    "modules/12-text-to-sql/py/seed_db.py": ["modules/12-text-to-sql/sales.db"],
}

# Explicit classifications for scaffolds the import heuristics cannot see —
# e.g. framework tasks that leave every real import inside TODO comments, so
# nothing importable is present yet even though the solved exercise needs a
# provider. Maps repo-relative path → (offline_status, exclude_reason, extras).
_OVERRIDES: dict[str, tuple[str, str, list[str]]] = {
    # bpe.py is a WORKED from-scratch tokenizer that runs fully offline. It
    # imports tiktoken ONLY for an optional comparison, which the file now skips
    # when OFFLINE_SMOKE / CI is set (so no network download is attempted). The
    # classifier otherwise buckets any tiktoken user as `provider`; this override
    # keeps the core exercise in the offline smoke set. NOTE: the T1.2 runner must
    # export OFFLINE_SMOKE=1 for offline entries. Offline entries must carry an
    # EMPTY exclude_reason, so the rationale lives here in this comment.
    "modules/01-fundamentals/py/bpe.py": ("offline", "", []),  # see OVERRIDE_SOURCE_GUARDS
    "modules/06-agents/py/04_framework.py": (
        "provider",
        "LangGraph/LangChain agent scaffold (imports live in TODO comments): "
        "needs the `agents` extra and an LLM provider once implemented; excluded "
        "from offline CI.",
        ["agents"],
    ),
    "modules/06-agents/ts/04-framework.ts": (
        "provider",
        "LangGraph/LangChain agent scaffold (imports live in TODO comments): "
        "needs an LLM provider once implemented; excluded from offline CI.",
        [],
    ),
}

# An override that force-classifies a file `offline` only stays SOUND while the
# file keeps the CI-safety property that justified it. Each entry maps a file to
# ``(guard_token, guarded_import)``:
#   - guard_token    — a substring that MUST remain in the source (e.g. bpe.py's
#                      ``OFFLINE_SMOKE`` env guard around its tiktoken call);
#   - guarded_import — the single import the guard neutralises (``tiktoken``).
# The structure checker fails (FATAL) if the token disappears OR if the file, with
# the guarded import removed, would STILL classify as non-offline — i.e. it gained
# some OTHER network/provider trigger (httpx/get_provider/…) the guard does not
# cover. So a force-offline override can never silently mask unsafe code.
OVERRIDE_SOURCE_GUARDS: dict[str, tuple[str, str]] = {
    "modules/01-fundamentals/py/bpe.py": ("OFFLINE_SMOKE", "tiktoken"),
}


def _module_prefix(slug: str) -> str:
    match = re.match(r"(\d+[a-z]?)-", slug)
    return match.group(1) if match else slug


def override_residual_status(rel: str, source: str, guarded_import: str) -> str:
    """The offline-status ``source`` would have with ``guarded_import`` removed.

    Runs the real :func:`classify` on the source but with the guarded import
    dropped from the detected set, so the one trigger the guard is allowed to
    cover (e.g. tiktoken's network download) is discounted. Any OTHER
    provider/network trigger still shows through, so a force-offline override can
    require this to be ``"offline"`` before it is honoured.
    """
    slug = rel.split("/")[1]
    language = "py" if rel.endswith(".py") else "ts"
    imports = _py_imports(source) if language == "py" else _ts_specifiers(source)
    stub_mode = bool(_STUB_MODE.search(source))
    status, _ = classify(slug, language, source, imports - {guarded_import}, stub_mode)
    return status


def _py_imports(text: str) -> set[str]:
    return set(_PY_IMPORT.findall(text))


def _ts_specifiers(text: str) -> set[str]:
    return set(_TS_IMPORT.findall(text))


def detect_extras(slug: str, language: str, imports: set[str]) -> list[str]:
    """The ``uv --extra`` names a Python exercise needs (TS never uses extras)."""
    if language != "py":
        return []
    found: set[str] = set()
    for pkg in imports:
        if pkg in _EXTRA_BY_PKG:
            found.add(_EXTRA_BY_PKG[pkg])
        if pkg in {"torch", "torchvision", "transformers"}:
            found.add(_TORCH_EXTRA_BY_PREFIX.get(_module_prefix(slug)[:2], "vision"))
    if slug.startswith("17-"):
        found.add("mcp")
    if slug.startswith("18-"):
        found.add("browser")
    return sorted(found)


def classify(
    slug: str, language: str, text: str, imports: set[str], stub_mode: bool
) -> tuple[str, str]:
    """Return ``(offline_status, exclude_reason)`` for one file.

    ``stub_mode`` is passed in (not recomputed) so it stays in lockstep with the
    ``--stub`` flag ``build()`` appends to the command: buckets are only
    suppressed for files whose command actually runs the deterministic stub path.

    Precedence (strongest, most permanent blocker wins) — a file matching an
    earlier rule takes that bucket even if it also matches later ones:

    1. heavy import       → ``download`` (needs model weights)
    2. computer-use / Playwright → ``download`` (browser binary + live web)
    3. native npm dep     → ``download`` (e.g. better-sqlite3, not installed)
    4. MCP module         → ``provider`` (needs an MCP server + a provider)
    5. provider required  → ``provider`` (a ``--stub`` escape hatch defers this)
    6. residual network   → ``provider`` (non-deterministic outbound HTTP,
       including tiktoken's vocab download)
    7. learner stub       → ``stub``
    8. otherwise          → ``offline``
    """
    is_py = language == "py"
    has_stub = bool((_PY_STUB if is_py else _TS_STUB).search(text))
    stub_suffix = " It is also an unsolved learner stub." if has_stub else ""

    if is_py:
        needs_provider = bool(
            "get_provider" in text or (imports & _PROVIDER_PKGS) or _ENV_KEY.search(text)
        )
        heavy = bool(imports & _HEAVY_PKGS)
        native_dep = False
        network = bool(_NETWORK.search(text)) or bool(imports & _NETWORK_PKGS)
    else:
        needs_provider = bool(
            "getProvider" in text
            or any(
                s == "openai" or "langchain" in s or "langgraph" in s or "image_client" in s
                for s in imports
            )
            or _ENV_KEY.search(text)
        )
        heavy = False
        native_dep = "better-sqlite3" in imports
        network = bool(_NETWORK.search(text))

    if heavy:
        return (
            "download",
            "Local model path: needs a heavy extra and a multi-GB model/weights "
            "download (torch/transformers/diffusers/peft). Excluded from offline CI." + stub_suffix,
        )
    if slug.startswith("18-") or "playwright" in imports:
        return (
            "download",
            "Needs a Playwright browser binary (`playwright install`) and live web "
            "access; not part of the default offline CI." + stub_suffix,
        )
    if native_dep:
        return (
            "download",
            "Imports the native `better-sqlite3` dependency, which is not in the "
            "default install; excluded from offline CI." + stub_suffix,
        )
    if slug.startswith("17-") or "mcp" in imports:
        return (
            "provider",
            "Needs a running MCP server and an LLM provider; not part of the "
            "default offline CI." + stub_suffix,
        )
    if needs_provider and not stub_mode:
        return (
            "provider",
            "Calls an LLM/embedding provider (needs a provider key or endpoint), "
            "so it is excluded from the default offline CI." + stub_suffix,
        )
    if network and not stub_mode:
        return (
            "provider",
            "Makes outbound network calls (e.g. httpx or a tiktoken vocab "
            "download), so it is not deterministic offline and is excluded from "
            "the default CI." + stub_suffix,
        )
    if has_stub:
        return (
            "stub",
            "Unsolved learner scaffold: raises NotImplementedError / throws a TODO "
            "error until the core is implemented. Runs offline once solved.",
        )
    return ("offline", "")


def build() -> Manifest:
    root = repo_root()
    entries: list[ExerciseEntry] = []
    for file_path in iter_exercise_files(modules_root()):
        rel = file_path.relative_to(root).as_posix()
        slug = file_path.relative_to(modules_root()).parts[0]
        language = "py" if file_path.suffix == ".py" else "ts"
        text = file_path.read_text(encoding="utf-8", errors="replace")
        imports = _py_imports(text) if language == "py" else _ts_specifiers(text)
        stub_mode = bool(_STUB_MODE.search(text))

        if rel in _OVERRIDES:
            offline, reason, extras = _OVERRIDES[rel]
        else:
            extras = detect_extras(slug, language, imports)
            offline, reason = classify(slug, language, text, imports, stub_mode)

        # Keep the command in lockstep with _STUB_MODE suppression: files whose
        # classification relies on the deterministic stub path actually pass it.
        stub_flag = " --stub" if stub_mode else ""
        if language == "py":
            extra_flags = "".join(f"--extra {name} " for name in extras)
            command = f"uv run {extra_flags}python {rel}{stub_flag}"
        else:
            command = f"pnpm tsx {rel}{stub_flag}"

        artifacts = _ARTIFACTS.get(rel, []) if offline == "offline" else []

        entries.append(
            ExerciseEntry(
                path=rel,
                module=slug,
                language=language,
                command=command,
                extras=extras,
                offline=offline,  # type: ignore[arg-type]
                expected_artifacts=artifacts,
                timeout_s=_TIMEOUT_BY_BUCKET[offline],
                exclude_reason=reason,
            )
        )
    return Manifest(version=1, exercises=entries)


def main() -> None:
    manifest = build()
    manifest_path().write_text(serialize_manifest(manifest), encoding="utf-8")
    counts: dict[str, int] = {}
    for entry in manifest.exercises:
        counts[entry.offline] = counts.get(entry.offline, 0) + 1
    print(f"Wrote {len(manifest.exercises)} entries to {manifest_path()}")
    for bucket in ("offline", "provider", "download", "stub"):
        print(f"  {bucket:9} {counts.get(bucket, 0)}")


if __name__ == "__main__":
    main()
