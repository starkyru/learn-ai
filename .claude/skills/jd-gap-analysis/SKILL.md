---
name: jd-gap-analysis
description: >-
  Analyze a job description (pasted text OR a URL) and find the AI/ML/GenAI topics it
  requires that this learn-ai course does NOT yet cover. Use when the user shares a job
  posting / JD / role requirements and asks what's missing, what to add, for a gap
  analysis, or to "align the course to this job." Extracts AI-related requirements ONLY
  (frameworks, RAG, agents, fine-tuning, evals, guardrails, serving, etc.), maps them to
  the course's actual coverage, and reports ranked gaps with concrete module suggestions.
argument-hint: <job description text OR a URL to a posting>
---

# JD → course gap analysis (AI topics only)

Goal: given a job description, tell the learner which **AI/ML/GenAI** skills the role
wants that this `learn-ai` course does not yet teach — and where each gap would slot in.
Ignore everything that is not an AI/ML topic.

The input (`$ARGUMENTS` / the args passed to the skill) is either raw JD **text** or a
**URL**. If it is empty, ask the user to paste the JD text or give a URL, then stop.

## Step 1 — Get the JD text

- **Pasted text** → use it directly.
- **URL** → fetch it:
  1. Try `WebFetch(url, "Extract the full job description: responsibilities, requirements,
tech stack, nice-to-haves. Return the raw text.")`.
  2. Many job pages (LinkedIn, Greenhouse, Lever, Workday, company SPAs) are
     JavaScript-rendered, so `WebFetch` returns only a title/shell. If the result looks
     empty or truncated, render it with the chrome-devtools MCP:
     `new_page(url)` → wait → `evaluate_script(() => document.body.innerText)` and use that
     text. (See how this repo's own gap analysis rendered a SPA curriculum.)
  3. If the page is behind a login wall (common for LinkedIn) or a captcha, say so and ask
     the user to paste the JD text instead. Do not guess the contents.

## Step 2 — Extract the AI-related requirements ONLY

Scan the JD and pull out concrete AI/ML/GenAI items. **Keep** anything in these families:

- **Agent frameworks / orchestration:** LangChain (LCEL, memory, retrievers), LlamaIndex,
  Semantic Kernel, CrewAI, AutoGen, LangGraph, DSPy, Haystack, agent orchestration,
  workflow automation, multi-agent, tool use / function calling, ReAct, planning, MCP.
- **RAG / retrieval:** embeddings, vector databases (Chroma, Qdrant, Pinecone, pgvector,
  Weaviate, FAISS), chunking, reranking, hybrid search (BM25 + dense), HyDE, GraphRAG,
  contextual retrieval, citations/attribution.
- **LLM integration / prompting:** prompt engineering, few-shot, chain-of-thought,
  self-consistency, context engineering / optimization, structured output, streaming,
  prompt caching, token/cost management.
- **Fine-tuning / training:** SFT, LoRA / QLoRA / PEFT, RLHF, DPO, distillation, dataset
  prep, overfitting/eval.
- **Eval / quality / safety:** LLM-as-judge, evaluation frameworks, guardrails,
  prompt-injection defense, PII/DLP, OWASP LLM Top 10, red-teaming, hallucination
  detection, human-in-the-loop validation.
- **LLMOps / observability / serving:** tracing (Langfuse, LangSmith, OpenTelemetry),
  monitoring, regression gates, model routing/fallbacks, quantization, local inference,
  KV cache, serving AI behind an API (FastAPI/streaming/SSE for AI), batch APIs.
- **Modalities:** computer vision, multimodal LLMs, CLIP, image generation / diffusion,
  audio / speech (STT/TTS, Whisper, realtime, VAD), computer use / browser agents.
- **Foundations / theory (often interview-tested):** transformers/attention, tokenizers,
  classic ML (regression, bias-variance, metrics), deep learning (backprop, CNN, RNN),
  reasoning / test-time compute, classification.
- **Providers / models:** OpenAI, Anthropic/Claude, Gemini, Llama/Ollama, NVIDIA NIM,
  reasoning models, model selection/cost tradeoffs.

**Drop** (not AI gaps): general software engineering (git, REST, microservices, Docker,
Kubernetes, CI/CD, cloud basics) unless it is specifically _AI-serving_ infra; programming
language proficiency; databases/SQL basics (unless text-to-SQL over an LLM); frontend
frameworks; years of experience; soft skills; degrees; non-AI domain knowledge
(healthcare, finance, etc.) — note the domain, but it is not itself a course topic.

Produce a clean list of the AI requirements you extracted (deduplicated, normalized to the
vocabulary above).

## Step 3 — Load what the course already covers

The course's coverage is authoritative in these files — read them, do not rely on memory:

- `CURRICULUM.md` — the module map + per-module tasks and "Done when" (the source of truth).
- `README.md` — the module table + the deep-dive companions (05b, 06b, 06c, 01b/01c/01d).
- `docs/GLOSSARY.md` — every abbreviation the course uses (quick check for whether a term
  appears at all).
- `grep -ri "<topic>" modules/*/README.md` — confirm depth for a specific topic before
  calling it covered or a gap.

Current coverage at a glance (verify against `CURRICULUM.md`, which may have grown):
00 setup/providers · 01 fundamentals · 01b classic ML · 01c deep learning · 01d transformers ·
02 integration · 03 prompting · 04 embeddings/vectors · 05 RAG · 05b advanced RAG ·
06 agents · 06b LangGraph · 06c agent frameworks (LangChain/CrewAI/AutoGen/LlamaIndex/Semantic
Kernel) · 07 production (eval, tracing incl. Langfuse, caching, guardrails, serving) ·
08 classification · 09 vision · 10 image gen · 11 ingestion · 12 text-to-SQL · 13 fine-tuning ·
14 local inference/opt · 15 reasoning/test-time compute · 16 context engineering · 17 MCP ·
18 computer use · 19 audio/speech · 20 AI security · 21 LLMOps/eval · 22 product UX · 23 capstone.

## Step 4 — Map and report

For each extracted AI requirement, classify:

- **Covered** — cite the module/task (e.g. "RAG → module 05; hybrid search → module 04
  Task 4"). Quote the specific task if you can.
- **Partial** — touched but not to the depth the JD implies; say what's thin.
- **GAP** — not taught.

Output, in this order:

1. **One-line summary** — role focus + how many AI requirements, how many gaps.
2. **Coverage table** — `| JD AI requirement | Status | Where (module/task) |`.
3. **Ranked GAPS** — most-important first. For each: what it is, why the role needs it, and
   a concrete suggestion for a new module/task **in this repo's house style**:
   - depth lanes 🟢 app / 🟡 balanced / 🔴 from-scratch;
   - both TypeScript **and** Python;
   - exercise code goes through `llm_core` / `@learn-ai/llm-core` (never a hardcoded vendor);
   - a README with tasks + "Done when";
   - TODO stubs that **hint**, not hand over the solution (see the "Writing exercise
     scaffolds" rule in `CLAUDE.md`).
4. **Non-AI note** — one line listing notable non-AI asks you deliberately excluded, and the
   role's domain, so the user knows they weren't missed — just out of scope.

## Step 5 — Offer to implement

Ask whether to implement the top gap(s). If yes, follow the repo's established workflow:
build in a git workspace/worktree based on `main`, keep py/ts parallel, verify each
exercise runs (temp-fill the TODOs, run, check acceptance), adversarially review, then
merge into the working branch. Wire any new module into `README.md` and `CURRICULUM.md`.

## Rules

- **AI topics only.** A generic backend/devops/soft-skill requirement is never a "gap."
- **Cite, don't assert.** Anchor every "covered" to a module/task; anchor every "gap" to
  the absence of it in `CURRICULUM.md` / `modules/`. Never invent coverage.
- If the course already covers something the JD names by a different word (e.g. JD says
  "LangSmith", course teaches tracing via Langfuse in module 07), mark it **Covered
  (equivalent)** and name the equivalent.
