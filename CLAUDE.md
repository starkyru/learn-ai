# CLAUDE.md — context for agents working in `learn-ai`

This file is auto-loaded as context. Read it, then help the learner well.

## What this is

`learn-ai` is a **personal, hands-on AI course** — a project-based curriculum that
takes one person from a vague sense of how AI apps work to building real ones:
provider integration, embeddings, retrieval (RAG), and autonomous agents, in **both
TypeScript and Python**. The reader is the _learner_; you are their tutor/pair-programmer.
Favor teaching over just shipping code (see `/tutor` below).

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
└── docs/                   # cross-cutting docs (see docs/TUTOR_AND_EXAM.md)
```

The module map (24 modules): 00 Setup & Providers · 01 LLM Fundamentals ·
02 LLM Integration · 03 Prompting & Patterns · 04 Embeddings & Vectors · 05 RAG ·
06 Agents · 07 Advanced & Production · 08 Classification · 09 Computer Vision ·
10 Image Generation · 11 Document Ingestion · 12 Text-to-SQL · 13 Fine-tuning ·
14 Local Inference & Optimization · 15 Reasoning & Test-time Compute ·
16 Context Engineering · 17 MCP & Modern Agent APIs · 18 Computer Use ·
19 Audio & Speech · 20 AI Security · 21 LLMOps & Eval · 22 AI Product UX ·
23 Capstone. Plus two deep-dive companions: **05b Advanced RAG**
(`modules/05b-advanced-rag/`, extends module 05 — Contextual Retrieval, CRAG,
Self-RAG, GraphRAG; reference: `docs/ADVANCED_RAG.md`) and **06b LangGraph**
(`modules/06b-langgraph/`, extends module 06; reference: `docs/LANGGRAPH.md`).
Seven more companions extend modules 01, 06, and 13: **01b Classic ML Foundations**
(`modules/01b-ml-foundations/` — regression, bias–variance, regularisation,
ROC/AUC, k-means), **01c Deep Learning Essentials** (`modules/01c-deep-learning/`
— autograd/backprop, optimizers, initialisation, regularisation, RNN+BPTT),
**01d Transformer Architecture** (`modules/01d-transformer/` — multi-head
attention, masking, positional encoding, LayerNorm/residuals, KV cache,
encoder-vs-decoder/BERT-vs-GPT, plus RoPE/GQA/FlashAttention/MoE/scaling-laws
interview notes), **01e Trees & Ensembles** (`modules/01e-trees-ensembles/` —
CART decision trees, random forests, gradient boosting, bias–variance
decomposition), **01f Probability, Statistics & PCA**
(`modules/01f-stats-foundations/` — Bayes/naive Bayes, MLE ↔ cross-entropy,
hypothesis testing/A-B tests, PCA), and **13b Post-training & Alignment**
(`modules/13b-alignment/`, extends 13 — preference data/Elo, Bradley–Terry
reward model, RLHF + reward hacking, DPO) are all pure-from-scratch (numpy + TS,
no provider); **06c Agent Frameworks** (`modules/06c-agent-frameworks/` —
LangChain/CrewAI/AutoGen, extends 06/06b) is offline via a `--stub` model.
**Each module's `README.md` is the source of
truth** for what the learner is studying — read it before tutoring or quizzing on a topic.
(Some module READMEs may not be written yet; if one is missing, fall back to the root
`README.md` / `CURRICULUM.md` and say so rather than inventing content.)

> **Keep the docs in sync.** Whenever you add or remove a lesson (a new module,
> companion, or task), update **both** the root `README.md` (module table + deep-dive
> callouts) **and** `CURRICULUM.md` (the module section: title, learning objectives,
> tasks table, "Done when"). Don't leave a lesson that exists on disk but is missing or
> stale in these two docs.

## Depth-level convention (🟢 / 🟡 / 🔴)

Every module weaves three depth lanes; the learner picks a lane per module:

- 🟢 **App** — build something that works using the ecosystem/libraries.
- 🟡 **Balanced** — build the app _and_ implement one core piece by hand for intuition.
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

The provider swaps between OpenAI / Anthropic / Ollama / NVIDIA / LM Studio /
Gemini (six providers) via one env var — `OpenAICompatibleProvider` now covers
five of them (OpenAI, Ollama, NVIDIA, LM Studio, Gemini, all via the OpenAI-compatible
endpoint shape); only Anthropic needs its own adapter. Note: **Anthropic has no
embeddings endpoint** — `embed()` raises there; use `LLM_PROVIDER=openai` (or
`ollama`/`nvidia`/`lmstudio`/`gemini`) for embedding/RAG exercises. The
zero-cost path is Ollama (`ollama pull llama3.2 && ollama pull nomic-embed-text`)
or LM Studio (load a model, Start Server on port 1234). Gemini
(`LLM_PROVIDER=gemini`, `GEMINI_API_KEY`) has a free tier and does support embeddings.

## How to run things

- **Python:** `uv run python <path>.py` (e.g. `uv run python modules/00-setup/py/hello.py`).
  `uv sync` once; some modules need extras: `--extra` `vectors` (04, 05),
  `agents` (06), `production` (07, 22), `ml` (08), `vision` (09, local),
  `imagegen` (10, local), `ingest` (11), `finetune` (13, local), `mcp` (17),
  `browser` (18), `audio` (19, local), `telegram` (news-agent).
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

## Course-maintenance skills

- **`jd-gap-analysis`** (`.claude/skills/jd-gap-analysis/SKILL.md`) — give it a job
  description (pasted text or a URL) and it extracts the **AI/ML/GenAI** requirements,
  maps them against `CURRICULUM.md`, and reports the AI-only gaps (ranked, with suggested
  house-style modules). Use it to keep the course aligned to what employers ask for.

## When you help

- Be a tutor first: prefer hints, structure, and the next concrete step over dumping a
  full solution — unless the learner explicitly asks for the solution.
- Anchor answers to the module README, not to your own memory of how a tool behaves.
- Keep exercise code going through `llm_core` / `@learn-ai/llm-core`.

## Writing exercise scaffolds (TODO stubs)

Exercise files leave the pedagogically-core function as a stub (`raise NotImplementedError`
/ `throw new Error("TODO: ...")`). The TODO comment must **hint, not hand over a
copy-paste solution** — the learner should have to write the code, not just uncomment it.

- **Keep** (good hints): the value's TYPE (e.g. "build a `ChatMessage[]`", Python type
  hints), the return/object SHAPE, WHICH functions to call (`provider.chat`, `isYes`,
  `Promise.all`, `np.linalg.solve`, …), WHICH parameters matter (`temperature: 0`, a small
  `maxTokens`, `axis=1` — you may replace a giveaway magic value with `...`), and the
  concept / numbered steps / math formulas in the header docstring.
- **Remove** (spoilers): fully-assembled object/array literals, exact prompt STRINGS
  (describe their intent instead), the final `return <expression>`, and copy-paste chains
  like `xs.map(...).join(...)` (describe them in words). No line-for-line commented-out
  solution.
- Only edit comments on **unimplemented** stubs; never alter code the learner may have
  already solved. Keep the Python and TypeScript hints parallel.
