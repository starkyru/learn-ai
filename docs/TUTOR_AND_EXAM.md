# Learn interactively: `/tutor`, `/exam`, and the `tutor` CLI

This course ships **two** ways to study interactively — a tutor that answers
questions and advises your next coding step, and an exam that quizzes you on a
module and grades you. Both are **grounded in the module READMEs** (the lessons),
so they teach *this* course, not generic AI trivia.

You get them in two forms:

| | **Claude Code slash commands** | **Standalone CLI** |
| --- | --- | --- |
| What | `/tutor`, `/exam` | `uv run python -m tutor ask` / `exam` |
| Where | Inside Claude Code, in this repo | Any terminal — no Claude Code needed |
| Model | Whatever Claude Code is running | Whatever `LLM_PROVIDER` is set to |
| Cost | Per your Claude Code plan | **Free** on local Ollama (default) |
| Can read your files | **Yes** — reads & reviews your exercise code | No (works only from the READMEs) |
| Best for | Deep help while coding; code review | Quick study/quiz, offline, zero-cost |

**Rule of thumb:** if you're in Claude Code and want help *with your actual
code*, use the slash commands. If you just want to study or self-test — especially
free and local — use the CLI.

---

## Option A — Claude Code slash commands

These are prompt files in `.claude/commands/`. Type them in Claude Code while
you're in this repo.

### `/tutor [module# or topic] <question>`

A patient tutor. It reads the relevant module README, then:

- For **concept** questions it's *Socratic* — gives you the intuition and a nudge
  rather than a wall of text.
- For **"how do I proceed"** questions it's *concrete* — an ordered plan of what to
  implement next, common pitfalls, and the command to run to verify.
- It will offer to **read and review your files** in that module against the
  "Done when" checklist.
- It won't dump the full solution unless you ask.

Examples:

```text
/tutor 04 how do embeddings turn text into vectors I can compare?
/tutor 05 I implemented chunk→embed→retrieve, what do I build next?
/tutor 01 review my BPE tokenizer
```

### `/exam <module# or topic>`

An interactive quiz on one module. It reads the README, then asks **5 questions
one at a time** (a mix of conceptual, "what would this code do", and small coding
prompts), **waiting for your answer** before each next question. It grades each
answer with brief feedback and finishes with a **score out of 5** plus a study
recommendation pointing at specific README sections.

Examples:

```text
/exam 04
/exam rag
```

---

## Option B — the standalone `tutor` CLI

Lives in [`projects/tutor/`](../projects/tutor/). Same two ideas, but it runs in
any terminal and talks to models through the course's `llm_core` client — so it
runs **free on a local Ollama model** by default (or any provider you configure
via `LLM_PROVIDER`). It can't see your code; it works purely from the module
READMEs.

```bash
uv sync                       # once, from the repo root
ollama pull llama3.2          # zero-cost path
ollama pull nomic-embed-text  # optional, improves question retrieval

cd projects/tutor             # run it from its own dir (like the news-agent)

# Q&A REPL — ask anything; it grounds answers in the most relevant README(s)
uv run python -m tutor ask
uv run python -m tutor ask --module 05     # focus a module

# Graded quiz on a module (by id, slug, or topic)
uv run python -m tutor exam --module 04
uv run python -m tutor exam --module rag --num 3 --difficulty hard

# See what modules exist
uv run python -m tutor modules
```

Inside the `ask` REPL: `:module <id>` to focus a module, `:modules` to list them,
`:help` for commands, `:quit` to exit.

The CLI is also a **worked example** of the patterns you build in the course: a
light **RAG** retrieval step (find the right README) feeding the answer, and
**LLM-as-judge** grading in exam mode. After modules 05 (RAG) and 07 (production),
read `projects/tutor/tutor/content.py` and `exam.py` — they'll make sense.

---

## How the tutor answers questions and quizzes you

Both forms follow the same shape:

1. **Find the module.** From your topic/number, locate `modules/<id>/README.md`.
   (The CLI uses keyword/embedding similarity to auto-pick; the slash command
   reasons about it. If a README isn't written yet, both say so and fall back to
   the root `README.md` / `CURRICULUM.md` rather than inventing content.)
2. **Ground in the README.** That lesson text is fed in as context, so answers
   and quiz questions match what *this* course actually teaches — including its
   conventions: the `llm_core` / `@learn-ai/llm-core` abstraction, the depth lanes
   (🟢 app / 🟡 balanced / 🔴 from-scratch), and how to run things
   (`uv run python …`, `pnpm tsx …`).
3. **Tutor:** explain at the right level **and** advise the concrete next coding
   step. **Exam:** generate questions, ask them one at a time, grade your answers,
   and report a score with study tips that point you back to the README.

---

## Which should I use?

- **Stuck while coding, want a review of your files** → `/tutor` in Claude Code.
- **Want to be quizzed and shown where you're weak** → either `/exam` or
  `uv run python -m tutor exam`.
- **Offline, on a plane, or keeping it free/local** → the `tutor` CLI on Ollama.
- **Just exploring a concept** → either; the CLI's `ask` REPL is a fast loop.
