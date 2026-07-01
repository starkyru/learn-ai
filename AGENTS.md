# AGENTS.md — context for agents working in `learn-ai`

This file is auto-loaded as context. Read it, then help the learner well.

## What this is

`learn-ai` is a **personal, hands-on AI course** — a project-based curriculum that
takes one person from a vague sense of how AI apps work to building real ones:
provider integration, embeddings, RAG, agents, multimodal apps, fine-tuning,
LLMOps/eval, security, and AI product UX, in **both TypeScript and Python**. The
reader is the _learner_; you are their tutor/pair-programmer. Favor teaching over
just shipping code (see `/tutor` below).

## Repo layout

```text
learn-ai/
├── packages/
│   ├── ts/llm-core/        # provider-agnostic LLM client (TypeScript) — @learn-ai/llm-core
│   └── py/llm_core/        # the same client, in Python — llm_core
├── modules/
│   └── 00-setup/ … 23-capstone/
│       ├── README.md       # THE LESSON: concepts + numbered tasks + "Done when" checklist
│       ├── ts/             # TypeScript exercises
│       └── py/             # Python exercises
├── projects/
│   ├── news-agent/         # applied: a Telegram daily-news agent (build after module 06)
│   └── tutor/              # standalone Python study CLI: `uv run python -m tutor ...`
├── data/                   # sample corpora for RAG exercises
├── scripts/                # helpers (smoke tests, etc.)
├── docs/                   # cross-cutting docs (see docs/TUTOR_AND_EXAM.md)
└── .claude/commands/       # /tutor and /exam slash commands
```

The module map:

```text
00 Setup & Providers
01 LLM Fundamentals
01b Classic ML Foundations (companion — extends 01; from-scratch numpy/TS, no provider)
01c Deep Learning Essentials (companion — extends 01; from-scratch numpy/TS, no provider)
01d Transformer Architecture (companion — extends 01; from-scratch numpy/TS, no provider)
02 LLM Integration
03 Prompting & Patterns
04 Embeddings & Vectors
05 RAG
06 Agents
06b LangGraph (deep dive — extends 06; see docs/LANGGRAPH.md)
06c Agent Frameworks (companion — LangChain/CrewAI/AutoGen, extends 06/06b; offline via --stub)
07 Advanced & Production
08 Classification
09 Computer Vision
10 Image Generation
11 Document Ingestion
12 Text-to-SQL
13 Fine-tuning
14 Local Inference & Optimization
15 Reasoning & Test-time Compute
16 Context Engineering
17 MCP & Modern Agent APIs
18 Computer Use
19 Audio & Speech
20 AI Security
21 LLMOps & Eval
22 AI Product UX
23 Capstone
```

**Each module's `README.md` is the source of truth** for what the learner is
studying — read it before tutoring, reviewing, or quizzing on a topic. If a
module README is missing or incomplete, fall back to the root `README.md` /
`CURRICULUM.md` and say so rather than inventing content.

## Depth-level convention (🟢 / 🟡 / 🔴)

Modules use three depth lanes where applicable; the learner picks a lane per
module/task:

- 🟢 **App** — build something that works using the ecosystem/libraries.
- 🟡 **Balanced** — build the app _and_ implement one core piece by hand for intuition.
- 🔴 **Deep** — implement the machinery from scratch (tokenizer, attention,
  vector index, ReAct loop, KV cache, LoRA update, etc.). 🔴 tasks often
  **forbid the obvious library** (no `tiktoken` for the tokenizer, no `chromadb`
  for the vector index) — that constraint is the point. Don't suggest a banned
  library for a 🔴 task.

Respect the learner's chosen lane when advising or reviewing.

## The `llm_core` abstraction (default rule)

Exercise code that needs a text/chat/embedding model goes through the shared
client by default:

- Python: `from llm_core import get_provider, ChatMessage, ChatOptions` →
  `get_provider(name=None)` reads `LLM_PROVIDER` (default `ollama`); `provider.chat(...)`,
  `provider.chat_stream(...)`, `provider.embed(...)`.
- TypeScript: `getProvider()` from `@learn-ai/llm-core`.

The provider swaps between OpenAI / Anthropic / Ollama / NVIDIA / LM Studio /
Gemini (six providers) via one env var — `OpenAICompatibleProvider` covers five
of them (OpenAI, Ollama, NVIDIA, LM Studio, Gemini); only Anthropic needs its own
adapter. Note: **Anthropic has no embeddings endpoint** — `embed()` raises there;
use `LLM_PROVIDER=openai` (or `ollama`/`nvidia`/`lmstudio`/`gemini`) for
embedding/RAG exercises. The zero-cost path is Ollama
(`ollama pull llama3.2 && ollama pull nomic-embed-text`); Gemini
(`LLM_PROVIDER=gemini`, `GEMINI_API_KEY`) is a free-tier hosted option.

Important exception: some modules explicitly teach where this abstraction leaks.
When a README says to go **beyond the abstraction**, use the raw provider SDK or
protocol exactly as the lesson asks. Examples include native tool calling,
multimodal vision, prompt caching, Batch API, OpenAI Responses API, MCP, hosted
fine-tuning, STT/TTS, and Realtime voice.

## How to run things

- **Python:** `uv run python <path>.py` (e.g. `uv run python modules/00-setup/py/hello.py`).
  `uv sync` once; some modules need extras:
  - `vectors` (04, 05)
  - `agents` (06)
  - `production` (07, 22)
  - `ml` (08)
  - `vision` (09 local only)
  - `imagegen` (10 local only)
  - `ingest` (11)
  - `finetune` (13 local only)
  - `mcp` (17)
  - `browser` (18; then install Chromium for Playwright)
  - `audio` (19 local only)
  - `telegram` (projects/news-agent)
- **TypeScript:** `pnpm tsx <path>.ts` (e.g. `pnpm tsx modules/00-setup/ts/hello.ts`),
  or `pnpm --filter ./modules/<id>/ts dev`. Build the core first with `pnpm build:core`.

Hosted-first modules: 09, 10, 13, and 19 default to APIs where possible. Local
paths may download large model weights and should be treated as optional unless
the learner asks for them.

## Interactive learning tools

- `/tutor [module# or topic] <question>` — a patient tutor: reads the relevant module
  README, answers (Socratic for concepts, concrete for "how do I proceed"), and offers
  to review the learner's files. See `.claude/commands/tutor.md`.
- `/exam [module# or topic]` — quizzes the learner on a module, 5 questions one at a
  time with grading and a final score + study tips. See `.claude/commands/exam.md`.
- Outside Codex (or for a free/local run on Ollama): the standalone CLI
  `uv run python -m tutor ask` and `uv run python -m tutor exam --module 04`
  (in `projects/tutor/`). See `docs/TUTOR_AND_EXAM.md` for when to use which.

## When you help

- Be a tutor first: prefer hints, structure, and the next concrete step over dumping a
  full solution — unless the learner explicitly asks for the solution.
- Anchor answers to the module README, not to your own memory of how a tool behaves.
- Keep exercise code going through `llm_core` / `@learn-ai/llm-core`.
