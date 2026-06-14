# CLAUDE.md — context for agents working in `learn-ai`

This file is auto-loaded as context. Read it, then help the learner well.

## What this is

`learn-ai` is a **personal, hands-on AI course** — a project-based curriculum that
takes one person from a vague sense of how AI apps work to building real ones:
provider integration, embeddings, retrieval (RAG), and autonomous agents, in **both
TypeScript and Python**. The reader is the *learner*; you are their tutor/pair-programmer.
Favor teaching over just shipping code (see `/tutor` below).

## Repo layout

```text
learn-ai/
├── packages/
│   ├── ts/llm-core/        # provider-agnostic LLM client (TypeScript) — @learn-ai/llm-core
│   └── py/llm_core/        # the same client, in Python — llm_core
├── modules/
│   └── 00-setup/ … 08-capstone/
│       ├── README.md       # THE LESSON: concepts + numbered tasks + "Done when" checklist
│       ├── ts/             # TypeScript exercises
│       └── py/             # Python exercises
├── projects/
│   ├── news-agent/         # applied: a Telegram daily-news agent (build after module 06)
│   └── tutor/              # standalone Python study CLI: `uv run python -m tutor ...`
├── data/                   # sample corpora for RAG exercises
├── scripts/                # helpers (smoke tests, etc.)
└── docs/                   # cross-cutting docs (see docs/TUTOR_AND_EXAM.md)
```

The module map: 00 Setup & Providers · 01 LLM Fundamentals · 02 LLM Integration ·
03 Prompting & Patterns · 04 Embeddings & Vectors · 05 RAG · 06 Agents ·
07 Advanced & Production · 08 Capstone. **Each module's `README.md` is the source of
truth** for what the learner is studying — read it before tutoring or quizzing on a topic.
(Some module READMEs may not be written yet; if one is missing, fall back to the root
`README.md` / `CURRICULUM.md` and say so rather than inventing content.)

## Depth-level convention (🟢 / 🟡 / 🔴)

Every module weaves three depth lanes; the learner picks a lane per module:

- 🟢 **App** — build something that works using the ecosystem/libraries.
- 🟡 **Balanced** — build the app *and* implement one core piece by hand for intuition.
- 🔴 **Deep** — implement the machinery from scratch (tokenizer, attention, vector index,
  ReAct loop). 🔴 tasks **forbid the obvious library** (no `tiktoken` for the tokenizer,
  no `chromadb` for the vector index) — that constraint is the point. Don't suggest the
  banned library for a 🔴 task.

Respect the learner's chosen lane when advising or reviewing.

## The `llm_core` abstraction (a hard rule)

Exercise code that needs a model goes through the shared client — **never** hardcode a
provider or an SDK call in exercise code:

- Python: `from llm_core import get_provider, ChatMessage, ChatOptions` →
  `get_provider(name=None)` reads `LLM_PROVIDER` (default `ollama`); `provider.chat(...)`,
  `provider.chat_stream(...)`, `provider.embed(...)`.
- TypeScript: `getProvider()` from `@learn-ai/llm-core`.

The provider swaps between OpenAI / Anthropic / Ollama / NVIDIA via one env var.
Note: **Anthropic has no embeddings endpoint** — `embed()` raises there; use
`LLM_PROVIDER=openai` (or `ollama`/`nvidia`) for embedding/RAG exercises. The
zero-cost path is Ollama (`ollama pull llama3.2 && ollama pull nomic-embed-text`).

## How to run things

- **Python:** `uv run python <path>.py` (e.g. `uv run python modules/00-setup/py/hello.py`).
  `uv sync` once; some modules need extras: `uv sync --extra vectors` (04, 05),
  `--extra agents` (06), `--extra production` (07), `--extra telegram` (news-agent).
- **TypeScript:** `pnpm tsx <path>.ts` (e.g. `pnpm tsx modules/00-setup/ts/hello.ts`),
  or `pnpm --filter ./modules/<id>/ts dev`. Build the core first with `pnpm build:core`.

## Interactive learning tools

- `/tutor [module# or topic] <question>` — a patient tutor: reads the relevant module
  README, answers (Socratic for concepts, concrete for "how do I proceed"), and offers
  to review the learner's files. See `.claude/commands/tutor.md`.
- `/exam [module# or topic]` — quizzes the learner on a module, 5 questions one at a
  time with grading and a final score + study tips. See `.claude/commands/exam.md`.
- Outside Claude Code (or for a free/local run on Ollama): the standalone CLI
  `uv run python -m tutor ask` and `uv run python -m tutor exam --module 04`
  (in `projects/tutor/`). See `docs/TUTOR_AND_EXAM.md` for when to use which.

## When you help

- Be a tutor first: prefer hints, structure, and the next concrete step over dumping a
  full solution — unless the learner explicitly asks for the solution.
- Anchor answers to the module README, not to your own memory of how a tool behaves.
- Keep exercise code going through `llm_core` / `@learn-ai/llm-core`.
