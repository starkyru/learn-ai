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

### Current intentional parity exception

Module 10 has TS + Python for Task 1. Tasks 2–4 currently have Python runnable
scaffolds only: parameter sweep, img2img/inpainting, and toy diffusion. The
lesson labels this explicitly; TypeScript parity remains a curriculum backlog,
not an implied implementation promise.

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
- TS/Python scope is declared and verified.
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

The repository should run the verification ladder in GitHub Actions and should
not rely only on local Husky hooks. A release-facing project additionally needs:

- a build/type/lint/test job;
- an offline exercise-smoke job;
- a protected, bounded-cost eval-gate job using a dedicated provider key;
- artifact retention for eval reports; and
- a staging smoke test before promotion.

Module 21 includes a learner-copyable eval-gate example. A maintainer-owned
workflow should become the source of truth once the course chooses its CI
provider and secret policy.

## Documentation-only additions

Modules 07b, 20b, and 21b currently define the required lessons, tasks, and
acceptance criteria. Add their language-specific scaffolds before claiming they
are runnable TS + Python modules. Until then, they are curriculum specifications
that learners can apply to the capstone in either language.
