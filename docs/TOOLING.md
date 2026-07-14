# Tooling Reference

Everything you need to install, format, lint, test, and run code in this repo.

---

## One-time setup

### JavaScript / TypeScript

```bash
pnpm install
```

This installs all JS/TS dependencies **and** runs `husky` via the `prepare` script, which registers the Git hooks. You only need to do this once (or after `git clone`).

Build the shared TypeScript package before running any module:

```bash
pnpm build:core
```

### Python

```bash
uv sync
```

[uv](https://docs.astral.sh/uv/) creates a `.venv/` in the project root, installs `llm_core` as an editable package, and installs all dev tools (Ruff, pytest). The base install is intentionally light so this is fast.

#### Optional extras — install when you reach the module that needs them

| Extra        | Command                      | Used by                                          |
| ------------ | ---------------------------- | ------------------------------------------------ |
| `vectors`    | `uv sync --extra vectors`    | Modules 04, 05 (Chroma, Qdrant, BM25)            |
| `agents`     | `uv sync --extra agents`     | Modules 06, 06b (LangGraph)                      |
| `production` | `uv sync --extra production` | Modules 07, 07b, 22 (FastAPI, Uvicorn, Langfuse) |
| `ml`         | `uv sync --extra ml`         | Module 08 (scikit-learn)                         |
| `vision`     | `uv sync --extra vision`     | Module 09 local path                             |
| `imagegen`   | `uv sync --extra imagegen`   | Module 10 local Stable Diffusion path            |
| `ingest`     | `uv sync --extra ingest`     | Module 11 document/PDF parsing                   |
| `finetune`   | `uv sync --extra finetune`   | Module 13 local LoRA/QLoRA path                  |
| `audio`      | `uv sync --extra audio`      | Module 19 local speech path                      |
| `mcp`        | `uv sync --extra mcp`        | Module 17                                        |
| `browser`    | `uv sync --extra browser`    | Module 18; then install Playwright Chromium      |
| `telegram`   | `uv sync --extra telegram`   | `projects/news-agent`                            |

You can combine them: `uv sync --extra vectors --extra agents`.

### Recommended VSCode extensions

| Extension | ID                       | Purpose                           |
| --------- | ------------------------ | --------------------------------- |
| Prettier  | `esbenp.prettier-vscode` | Format JS/TS/JSON/MD/YAML on save |
| Ruff      | `charliermarsh.ruff`     | Format + lint Python on save      |
| Python    | `ms-python.python`       | Language support, test discovery  |

---

## Formatting

### JavaScript / TypeScript / JSON / Markdown / YAML

[Prettier](https://prettier.io) handles all of these. Config lives in `.prettierrc.json` (88-char width, double quotes, trailing commas, LF line endings).

```bash
pnpm format          # write in-place
pnpm format:check    # CI / check without writing
```

### Python

Ruff's formatter (a Black-compatible formatter) handles `.py` files.

```bash
uv run ruff format .          # write in-place
uv run ruff format --check .  # check without writing
```

### Format on save

The repo ships `.vscode/settings.json` (and `extensions.json`), so format-on-save works out of the box once you install the recommended extensions. `editor.formatOnSave` is on for all supported file types: Prettier is the default formatter for JS/TS/JSON/MD/YAML; Ruff is the formatter for Python.

Python save runs **format only** — deliberately **not** `source.fixAll.ruff` / `source.organizeImports.ruff`. Those auto-actions delete imports Ruff thinks are unused, which would silently strip the pre-provided imports in exercise scaffolds (e.g. `ChatMessage`) the moment you save, before you've written the TODO that uses them. Run `uv run ruff check --fix .` manually when you actually want that. If you personally want fix-on-save, add the `codeActionsOnSave` block to a local override (it stays out of the shared config).

### Editor-agnostic baseline (`.editorconfig`)

`.editorconfig` carries the indentation, charset, line-ending, and final-newline rules to **any** editor (JetBrains, Zed, Vim, VS Code with the EditorConfig extension), so you don't need Prettier/Ruff installed to match repo style. It mirrors them: 2-space indent (4 for Python), LF line endings, UTF-8, trim trailing whitespace (except Markdown, where two trailing spaces are a hard line break). Prettier and Ruff remain the source of truth for full formatting; `.editorconfig` is the lowest-common-denominator fallback.

---

## Linting

Ruff is the sole Python linter. It covers pycodestyle (E/W), Pyflakes (F), import sorting (I), pyupgrade (UP), and Bugbear (B).

```bash
uv run ruff check .           # report issues
uv run ruff check --fix .     # auto-fix where possible
```

There is no separate JS/TS linter configured — Prettier covers style and TypeScript's compiler (`pnpm typecheck`) catches type errors.

---

## Tests

### TypeScript — Jest

```bash
pnpm test
```

Jest uses `@swc/jest` for fast transpilation (no type-checking — that's `pnpm typecheck`). It scans `modules/` and `packages/` for files matching `**/*.test.ts`.

### Python — pytest

```bash
uv run pytest
```

pytest scans `modules/` and `packages/` for files matching `test_*.py` or `*_test.py` (`projects/` is excluded — run project tests explicitly). The `-q` flag is set by default in `pyproject.toml`.

### Course verification baseline

The two test commands are necessary but do not by themselves exercise every
provider-backed lesson. For a maintainer or release-facing capstone change, use
the complete verification ladder in
[`docs/COURSE_MAINTENANCE.md`](COURSE_MAINTENANCE.md): formatting, type checks,
tests, an offline/stub smoke path, then an opt-in bounded-cost eval gate.

---

## Running individual files

### TypeScript

```bash
pnpm tsx scripts/smoke.ts
# or any exercise file:
pnpm tsx modules/00-setup/ts/hello.ts
```

`tsx` transpiles on the fly via esbuild — no build step needed for one-off scripts.

### Python

```bash
uv run python scripts/smoke_test.py
# or any exercise file:
uv run python modules/00-setup/py/hello.py
```

`uv run` ensures the `.venv` is active and `llm_core` is on the path.

---

## Git hooks (Husky)

Hooks are registered automatically when you run `pnpm install` (via the `prepare` script). You should see `.husky/` in the repo root.

### pre-commit — lint-staged

Runs on every `git commit`. Only staged files are processed:

| Staged file pattern                  | Action                                              |
| ------------------------------------ | --------------------------------------------------- |
| `*.{ts,tsx,js,jsx,json,md,yaml,yml}` | `prettier --write`                                  |
| `*.py`                               | `uv run ruff format` then `uv run ruff check --fix` |

If Prettier or Ruff changes a file, the modified version is included in the commit automatically.

### pre-push — full test suites

Runs on every `git push`. Executes both test suites:

```text
→ jest (TypeScript)
→ pytest (Python)
```

pytest exit code 5 (no tests collected) is treated as success so an empty test suite doesn't block you.

### Emergency bypass

```bash
git commit --no-verify   # skip pre-commit
git push --no-verify     # skip pre-push
```

Use sparingly — the hooks exist to catch breakage before it lands.

---

## Troubleshooting

**Hook not firing after clone**
Run `pnpm install` — this re-runs `husky` via the `prepare` lifecycle script and registers the hooks in `.git/hooks/`.

**`ruff: command not found` in the hook**
Ruff lives in the uv dev group, not on your system PATH. The hooks call `uv run ruff ...`, which always uses the in-project `.venv`. If `uv` itself is missing, install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

**pytest or jest not found**
Both are in dev dependencies. Run `pnpm install` (JS) and `uv sync` (Python) to restore them.

**Import errors for `llm_core` in Python**
`uv sync` installs it as an editable package. If you see `ModuleNotFoundError: No module named 'llm_core'`, run `uv sync` again from the repo root.

**`@learn-ai/llm-core` not found in TS**
Run `pnpm build:core` to compile the TypeScript package before importing it.
