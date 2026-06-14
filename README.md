# learn-ai — a hands-on course in LLMs, RAG, and agents

A personal, project-based curriculum that takes you from a *vague* sense of how
AI apps work to building real ones: provider integration, embeddings, retrieval
(RAG), and autonomous agents — in **both TypeScript and Python**.

You don't just read. Every module is code you run, break, and extend, with three
depth levels woven through:

| Depth | What it means | Where |
| --- | --- | --- |
| 🟢 **App** | Build something that works using the ecosystem. | every module |
| 🟡 **Balanced** | Build the app *and* implement one core piece by hand for intuition. | 01, 03, 04, 05, 07 |
| 🔴 **Deep** | Implement the machinery from scratch (tokenizer, attention, vector index, ReAct loop). | 01, 04, 06 |

Pick your lane per module, or do all three. The 🔴 deep tasks are optional but
they're where the real understanding lives.

---

## The map

| # | Module | You'll build | Core ideas |
| --- | --- | --- | --- |
| 00 | [Setup & Providers](modules/00-setup/) | "Hello LLM" across 4 providers | API keys, the provider abstraction, OpenAI-compatible APIs |
| 01 | [LLM Fundamentals](modules/01-fundamentals/) | A BPE tokenizer, cosine similarity, a toy attention head, samplers | tokens, embeddings, attention, sampling, what a "model" even is |
| 02 | [LLM Integration](modules/02-llm-integration/) | Streaming chat, JSON/structured output, tool calling, retries | the request/response loop, function calling, cost & tokens |
| 03 | [Prompting & Patterns](modules/03-prompting/) | A prompt library + evaluator | few-shot, chain-of-thought, self-consistency, prompt eval |
| 04 | [Embeddings & Vectors](modules/04-embeddings-vectors/) | An in-memory vector index from scratch, then Chroma/Qdrant | embeddings, ANN search, chunking, hybrid (BM25 + dense) search |
| 05 | [RAG](modules/05-rag/) | A full retrieval-augmented Q&A pipeline + eval | chunk→embed→retrieve→rerank→generate, citations, faithfulness |
| 06 | [Agents](modules/06-agents/) | A ReAct agent from scratch, then with LangGraph | tools, planning loops, memory, multi-agent |
| 07 | [Advanced & Production](modules/07-advanced-production/) | Eval harness, tracing, caching, a served API | LLM-as-judge, observability, cost control, deployment |
| 08 | [Classification](modules/08-classification/) | A text classifier 3 ways + a softmax/GD one from scratch | LLM zero-shot vs embeddings+ML vs trained head, metrics (F1) |
| 09 | [Computer Vision](modules/09-computer-vision/) | Image classification, CLIP zero-shot, multimodal-LLM vision, a convolution from scratch | pixels→features, CNN/ViT, CLIP, vision LLMs |
| 10 | [Image Generation](modules/10-image-generation/) | Text-to-image (hosted Stable Diffusion), img2img/inpainting, a toy diffusion sampler | diffusion process, latent space, U-Net, guidance |
| 11 | [Document Ingestion](modules/11-document-ingestion/) | A real RAG ingestion pipeline (PDF/HTML, cleaning, structure-aware chunking, incremental indexing) | the messy-data front-end RAG actually needs |
| 12 | [Text-to-SQL](modules/12-text-to-sql/) | NL→SQL over a real DB, with safety + hybrid routing | querying structured data, schema grounding, SQL guardrails |
| 13 | [Fine-tuning](modules/13-fine-tuning/) | Prompt vs RAG vs fine-tune; hosted SFT; LoRA from scratch; distillation | SFT, LoRA/QLoRA, dataset prep, when to fine-tune |
| 14 | [Local Inference & Optimization](modules/14-local-inference-optimization/) | Quantization & throughput benchmarks, a KV cache from scratch, model routing/fallbacks | quantization, KV cache, serving engines, load testing |
| 15 | [Reasoning & Test-time Compute](modules/15-reasoning-test-time-compute/) | Reasoning vs standard models, self-consistency, best-of-N, self-refine | extended thinking, spending compute at inference |
| 16 | [Context Engineering](modules/16-context-engineering/) | Token budgeting, prompt caching, memory compaction, map-reduce, batch API | using the context window as a scarce budget |
| 17 | [MCP & Modern Agent APIs](modules/17-mcp/) | A course MCP server + an agent that uses it; Responses API | Model Context Protocol, hosted tools, remote MCP |
| 18 | [Computer Use](modules/18-computer-use/) | A browser agent (vision + DOM grounded) with safety gates | computer-use models, automation, action allowlists |
| 19 | [Audio & Speech](modules/19-audio-speech/) | STT, TTS, a voice tutor; VAD/denoise; realtime | Whisper, TTS, voice agents, audio preprocessing |
| 20 | [AI Security](modules/20-ai-security/) | Attack then harden your own RAG agent; a red-team harness | OWASP LLM Top 10, prompt injection, excessive agency |
| 21 | [LLMOps & Eval](modules/21-llmops-eval/) | Versioned eval sets, a CI regression gate, monitoring, feedback loop | the eval lifecycle, regression gates, human review |
| 22 | [AI Product UX](modules/22-ai-product-ux/) | A real mini app: streaming UI, citations drill-down, feedback, approval flow | trust, failure states, "show sources", human-in-the-loop |
| 23 | [Capstone](modules/23-capstone/) | A RAG-powered agent app, end to end | everything above, integrated |

**Hosted-first** (default to APIs, optional local heavy path documented): modules **09, 10** (vision/diffusion), **13** (fine-tuning), **19** (audio). Nothing multi-GB downloads unless you opt in.

**Applied projects** (in [`projects/`](projects/)):

- [`projects/news-agent`](projects/news-agent/) — a Telegram bot that an agent
  drives to collect news on a topic you choose and post a daily digest. Build it
  after module 06; it pulls together integration, agents, tools, and scheduling
  into something you'll actually run. (`uv run python -m news_agent --dry-run` to
  try it with no Telegram setup.)
- [`projects/tutor`](projects/tutor/) — your study buddy: a **Q&A mode** to ask
  about the project and how to proceed, and an **exam mode** that quizzes you on a
  module and grades you. Runs free on Ollama. Usable from day one. There are also
  Claude Code slash commands `/tutor` and `/exam` if you're in Claude Code — see
  [`docs/TUTOR_AND_EXAM.md`](docs/TUTOR_AND_EXAM.md).

Read [`CURRICULUM.md`](CURRICULUM.md) for the detailed week-by-week plan,
prerequisites, and "you're done when…" checklists.

---

## Repo layout

```text
learn-ai/
├── packages/
│   ├── ts/llm-core/        # provider-agnostic LLM client (TypeScript)
│   └── py/llm_core/        # the same, in Python
├── modules/
│   ├── 00-setup/ … 23-capstone/   # 24 modules
│   │   ├── README.md       # the lesson + tasks + "done when" checklist
│   │   ├── ts/             # TypeScript exercises
│   │   └── py/             # Python exercises
├── projects/
│   ├── news-agent/         # the Telegram daily-news agent
│   └── tutor/              # Q&A + exam study CLI
├── docs/                   # TOOLING.md, TUTOR_AND_EXAM.md
├── data/                   # sample corpora for RAG exercises
├── scripts/                # helpers (smoke tests, etc.)
└── .claude/commands/       # /tutor and /exam slash commands
```

The two `llm-core` packages are the spine of the course: you write exercises
against one small interface and swap OpenAI ↔ Claude ↔ Ollama ↔ NVIDIA by
changing a single env var. Understanding *why* that abstraction is possible (and
where it leaks) is module 00–02.

---

## Setup (do this once)

### 1. Clone & secrets

```bash
cp .env.example .env
# edit .env — you only need keys for the providers you'll use.
# Zero-cost path: install Ollama and leave LLM_PROVIDER=ollama.
```

### 2. Pick a free or paid path

| Path | Cost | Setup |
| --- | --- | --- |
| **Ollama** (recommended to start) | free | [Install Ollama](https://ollama.com), then `ollama pull llama3.2 && ollama pull nomic-embed-text` |
| **NVIDIA NIM** | free tier | get a key at [build.nvidia.com](https://build.nvidia.com) → `NVIDIA_API_KEY` in `.env` |
| **OpenAI** | paid (~$5 covers the course) | key at [platform.openai.com](https://platform.openai.com/api-keys) |
| **Anthropic** | paid | key at [console.anthropic.com](https://console.anthropic.com); set `ANTHROPIC_MODEL=claude-haiku-4-5` for cheap iteration |

### 3. Python

```bash
# uv (https://docs.astral.sh/uv/) manages the env + the editable llm_core install.
uv sync
uv run python scripts/smoke_test.py        # verifies your provider works
```

Some modules need extras: `uv sync --extra` `vectors` (04, 05), `agents` (06),
`production` (07, 22), `ml` (08), `vision` (09, local only), `imagegen` (10,
local only), `ingest` (11), `mcp` (17), `browser` (18), `finetune` (13, local
only), `audio` (19, local only), `telegram` (news-agent). The `vision`,
`imagegen`, `finetune`, and `audio` extras are optional — those modules default
to hosted APIs.

### 4. TypeScript

```bash
pnpm install
pnpm build:core
pnpm --filter ./modules/00-setup/ts dev      # or: cd modules/00-setup/ts && pnpm dev
```

---

## How to work through it

1. `cd modules/00-setup` and read the `README.md`. Each module README is the
   lesson — concepts first, then numbered tasks with acceptance criteria.
2. Do the 🟢 app task to get something working, then circle back for 🟡/🔴.
3. Run the same exercise against two different providers and notice what changes.
4. Don't skip module 01 even though it's the least "useful" — it's the load-bearing
   intuition for everything after.

Suggested pace: ~1 module/week part-time. Modules 04→05→06 are the heart; budget
extra time there.

---

## Conventions

- Exercises that need a model use `getProvider()` / `get_provider()` from
  `llm-core`. Never hardcode a provider in exercise code.
- Each task folder has its own short `README` / docstring explaining *what* and
  *why* — treat writing those notes as part of the exercise.
- 🔴 "from scratch" tasks forbid the obvious library (no `tiktoken` for the
  tokenizer task, no `chromadb` for the vector-index task) — that's the point.
