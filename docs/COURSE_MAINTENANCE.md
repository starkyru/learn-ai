# Course Maintenance & Parity Policy

This document keeps `learn-ai` honest as the curriculum grows. It is for course
maintainers and contributors; learners should use a module README as the source
of truth for a particular lesson.

## Scope labels

Every task must be marked as one of:

- **TS + Python:** runnable scaffolds and acceptance criteria exist in both.
- **Python-first / TypeScript-first:** one implementation is intentionally the
  teaching path; the module explains why and offers an equivalent study route.
- **Concept-only:** no runnable scaffold exists yet. It must not be presented as
  a completed runnable exercise.

Platform-specific SDK lessons may be language-first, but the root course map and
module README must say so before the learner reaches the task.

The declared scope is machine-tracked and enforced, not just prose:

- [`scripts/curriculum/language_support.json`](../scripts/curriculum/language_support.json)
  is the language-support matrix — one `{ "py": bool, "ts": bool }` per module.
  The `language-matrix` check in `check_structure.py` fails if it drifts from the
  actual `py/` / `ts/` exercise directories in either direction (a module missing
  from the matrix, an entry with no dir, or a flag disagreeing with reality).
- [`scripts/curriculum/parity_policy.json`](../scripts/curriculum/parity_policy.json)
  registers every module that does **not** ship both languages, each with a
  rationale, owner, target milestone, and equivalent learning path. The
  `parity-policy` check fails if such a module has no complete entry — so an
  intentional gap is a reviewed decision, not silent drift.

### Current intentional parity exceptions

Module 10 now has TS + Python for all four tasks. Tasks 1–3 are direct ports
(text-to-image, parameter sweep, img2img/inpainting), and the TS Tasks 2–3 ship
a deterministic offline stub (`IMAGE_STUB`/`OFFLINE_SMOKE`) so CI can run them
with no key or network.

Task 4 is an **intentional, documented divergence** rather than a direct port:
the Python side is the from-scratch NumPy toy-diffusion sampler
(`py/toy_diffusion.py` — the 🔴 maths path), while the TypeScript side is its
safety/evaluation counterpart (`ts/safety_eval.ts` — a prompt-safety filter,
C2PA-style attribution metadata, and a filter-evaluation harness, mapping to
README Concept 11). Both are 🔴 and fully offline/deterministic; the module
README states this mapping before the learner reaches the task. This is a
reviewed equivalence (matching learning outcomes in different-but-parallel
exercises), not a parity backlog. Module 10 carries an informational
`parity_policy.json` entry recording this Task 4 divergence.

The **capstone (module 23)** ships no exercises at all: it is open-ended, and the
learner builds the project in either language. Its `parity_policy.json` entry
records this as language-neutral by design — the one module the matrix marks
`{ "py": false, "ts": false }` — not a missing port.

## Definition of done for a new lesson

- Module README has prerequisites, concepts, numbered tasks, acceptance
  criteria, and a “Done when” checklist.
- Root `README.md` and `CURRICULUM.md` link to the lesson and place it in a
  route/schedule.
- Every runnable exercise declares its dependencies in the correct workspace
  manifest and runs through the shared provider abstraction unless the lesson
  explicitly teaches its boundary.
- Offline paths are deterministic where possible; hosted paths disclose cost,
  keys, and expected downloads.
- TS/Python scope is declared and verified: add the module to
  `scripts/curriculum/language_support.json`, and if it does not ship both
  languages, add a complete `scripts/curriculum/parity_policy.json` entry. Both
  are enforced by `check_structure.py` (`language-matrix`, `parity-policy`).
- The exercise is covered by a targeted test, deterministic self-check, or
  documented manual acceptance test.

## Verification ladder

Run the light checks on every documentation or scaffold change:

```bash
pnpm format:check
pnpm typecheck
pnpm test
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

For a runnable module change, also run its offline path or deterministic
`--stub` mode. Provider-backed checks should be opt-in, cost-capped, and use
secrets only from the CI secret store.

## CI baseline

The repository runs the verification ladder in an active, maintainer-owned
GitHub Actions workflow — [`.github/workflows/ci.yml`](../.github/workflows/ci.yml),
the **source of truth** for CI — not only local Husky hooks. It runs on every
push and pull request, is deterministic and OFFLINE, and references NO
`secrets.*`, so provider keys are unavailable to all jobs by default. Its jobs:

- `js` — pnpm build · type-check · jest + Prettier on the clean/new paths;
- `py` — `uv run pytest` (the `modules` + `packages` testpaths) + Ruff on the
  clean/new paths;
- `curriculum` — `check_structure.py` (manifest completeness/drift/override +
  structure) and the curriculum + CI-helper unit tests
  (`pytest scripts/curriculum scripts/ci`);
- `smoke` — runs every offline exercise under the network tripwire with a
  secret-free env and publishes a summary;
- `control-char-scan` — fails on C0 control chars / NUL in tracked source; and
- `eval-gate` — a documented, OFFLINE release gate that activates when Module 21b
  lands (it never fails on the not-yet-present path).

Lint/format is scoped to the clean/new paths (`packages`, `scripts/curriculum`,
and the 07b/20b/21b runnable dirs once they land), NOT repo-wide: the module
scaffolds intentionally carry unused imports and unformatted code ("skip lint
cleanup"), so a repo-wide gate would be permanently red.

A release-facing project additionally needs a protected, bounded-cost eval-gate
using a dedicated provider key (Module 21's `eval-gate.yml` is the learner
example of that provider-backed variant — add its job to the active workflow
rather than copying standalone YAML), artifact retention for eval reports, and a
staging smoke test before promotion. The offline `smoke` job installs deps with
network, then runs the exercise process tree inside an OS-level network namespace
with no interfaces up (`unshare --net`) — the enforcing no-egress boundary — and
FAILS CLOSED if no namespace can be created (it never runs the smoke unsandboxed
in CI). The in-process tripwire and a secret-free, allowlisted env are
defense-in-depth. Gate activation is governed by a committed marker
(`scripts/curriculum/ci_gates.json`): once a release gate is marked active, CI
fails if its entrypoint is missing, and the detect step compares the marker
against the protected base branch, so a PR cannot downgrade an active gate to
inactive or delete it to skip the required job.

## CI integrity / branch protection

A workflow cannot protect against edits to **itself**: a pull request runs the
PR's own copy of `.github/workflows/ci.yml` and `scripts/ci/*`, so a PR could
rewrite the detect logic (or the required job) to pass while disabling a gate.
The workflow-internal downgrade guard is therefore **defense-in-depth**; the
actual enforcement boundary is GitHub repo governance. Configure the repository
(these are settings, not code) as follows:

- **Protect `main`** with a branch-protection rule / ruleset.
- **Require pull-request review** before merge (no direct pushes to `main`).
- **Require status checks to pass** and mark the CI jobs — at least `js`, `py`,
  `curriculum`, `smoke`, `control-char-scan`, and `eval-gate` — as **required
  status checks** (so a PR cannot merge with them red or removed).
- **Require CODEOWNERS review**: `.github/CODEOWNERS` designates an owner for
  every path that could turn a required check into a no-op — the CI surface
  (`.github/**`), the helper scripts (`scripts/ci/**`), the curriculum-QA and
  smoke-runner implementation (`scripts/curriculum/**`), the gate activation
  marker (`scripts/curriculum/ci_gates.json`), AND the release-gate
  implementation closure (`modules/21b-evaluation-reliability/**`). Enable
  "Require review from Code Owners" so a PR cannot change any of these — including
  replacing `gate.py` (or something it imports) with an exit-0 no-op — without the
  owner's approval.
- **Dismiss stale approvals on new commits** and disallow force-pushes to `main`.

With these settings, a PR cannot silently disable OR no-op a required gate:
turning it off, or gutting its implementation, needs both an owner's CODEOWNERS
approval and passing the base-branch downgrade guard.

## Documentation-only additions

Modules 07b, 20b, and 21b currently define the required lessons, tasks, and
acceptance criteria. Add their language-specific scaffolds before claiming they
are runnable TS + Python modules. Until then, they are curriculum specifications
that learners can apply to the capstone in either language.
