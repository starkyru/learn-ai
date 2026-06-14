# tutor — a study CLI for the learn-ai course

A small, standalone command-line tutor for this course. It does two things, both
grounded in the course's module READMEs:

- **`ask`** — an interactive Q&A REPL. Ask anything about the course; it explains
  the concept at the right level and tells you **how to proceed with the coding**.
- **`exam`** — a graded quiz on a module: it generates questions from that
  module's README, asks them one at a time, then grades your answers and gives a
  score plus study tips.

It runs **without Claude Code** and **for free on a local Ollama model** — it
talks to models through the course's provider-agnostic `llm_core` client, so it
works against whatever `LLM_PROVIDER` you've configured (Ollama, OpenAI,
Anthropic, NVIDIA).

> It's also a deliberate worked example: a light **RAG** pipeline (discover +
> retrieve the relevant README) plus **LLM-as-judge** grading — the same
> patterns you build by hand in **module 05 (RAG)** and **module 07 (production)**.
> After those modules, come back and read the source; it'll click.

## Setup

No extra install — it uses the course's root environment and the shared client.

```bash
uv sync                       # once, from the repo root
# zero-cost path: install Ollama and pull a model
ollama pull llama3.2
# embeddings improve retrieval but are optional (the CLI falls back to keywords):
ollama pull nomic-embed-text
```

Leave `LLM_PROVIDER=ollama` in your `.env` for the free/local path, or set it to
`openai` / `anthropic` / `nvidia` to use a hosted model.

## Usage

Run these from this directory (`projects/tutor/`), the same way you run the
`news-agent` project — `python -m tutor` looks for the `tutor` package in the
current directory:

```bash
cd projects/tutor

# Interactive Q&A REPL (auto-picks the most relevant module per question)
uv run python -m tutor ask

# Focus a module from the start
uv run python -m tutor ask --module 05

# Take a graded 5-question exam on a module (by id, slug, or topic)
uv run python -m tutor exam --module 04
uv run python -m tutor exam --module rag --num 3 --difficulty hard

# List the modules discovered in this repo
uv run python -m tutor modules
```

### REPL commands (inside `ask`)

| Command          | What it does                                         |
| ---------------- | ---------------------------------------------------- |
| `:module <id>`   | Focus a module (e.g. `:module 04`)                   |
| `:module`        | Clear focus — auto-select per question again         |
| `:modules`       | List discovered modules                              |
| `:help`          | Show commands                                        |
| `:quit` / `:q`   | Exit                                                 |

### `exam` flags

| Flag                  | Default  | Meaning                                  |
| --------------------- | -------- | ---------------------------------------- |
| `--module, -m`        | required | Module id (`04`), slug (`05-rag`), topic |
| `--num, -n`           | `5`      | Number of questions                      |
| `--difficulty, -d`    | `medium` | `easy` \| `medium` \| `hard`             |

## Notes & robustness

- Missing module READMEs are handled gracefully (the course is built up over
  time). `ask` warns and answers generally; `exam` lists what's available.
- Embeddings are used for retrieval when the provider supports them; otherwise it
  falls back to keyword overlap (so it still works on Anthropic, which has no
  embeddings endpoint, or when `nomic-embed-text` isn't pulled).
- Streaming is used for answers when available, with a non-streaming fallback.
- Small local models sometimes return messy JSON for the exam; parsing is
  tolerant of code fences and surrounding prose. If generation fails, lower
  `--num` or use a stronger provider.
- `Ctrl-C` exits cleanly; interrupting an exam grades what you've answered so far.

## Two ways to learn interactively

This CLI is the "outside Claude Code / free on Ollama" option. When you *are* in
Claude Code, the `/tutor` and `/exam` slash commands do the same thing with the
full agent (and it can read and review your actual exercise files). See
[`docs/TUTOR_AND_EXAM.md`](../../docs/TUTOR_AND_EXAM.md) for when to use which.
