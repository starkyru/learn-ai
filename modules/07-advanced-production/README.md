# Module 07 — Advanced & Production

Getting an LLM (Large Language Model) to answer a question is easy. Making it do so **reliably,
observably, cheaply, and safely** — at a scale where you can sleep at night —
is the hard part. This module covers the engineering work that separates a
prototype from a production service.

---

## Concepts

### Why evals come first

You can't improve what you can't measure. Before optimising prompts, swapping
models, or adding features, you need a baseline. An eval harness gives you:

- A fixed test set that doesn't change between runs.
- A score per test case, so you know whether a change helped or hurt.
- A regression signal: if your average score drops, something broke.

**LLM-as-judge** is the practical answer for open-ended generation. Rather than
writing regex assertions for free-text outputs, you send the question, rubric,
and the model's answer to a _second_ LLM call and ask it to score 0–10. This
handles nuance that hard-coded checks can't. The trade-off: the judge itself can
be wrong, so review the rubrics carefully and validate the judge on known cases.

### Observability

Every LLM call in production should emit a structured record:

```json
{
  "id": "abc123",
  "timestamp": "2025-01-15T12:00:00Z",
  "provider": "openai",
  "model": "gpt-4o-mini",
  "input_tokens": 142,
  "output_tokens": 38,
  "latency_ms": 412,
  "estimated_cost_usd": 0.000044
}
```

JSONL (JSON Lines; newline-delimited JSON) is a fine starting format: one record per line,
easy to `grep`, easy to stream into a data warehouse. In production, use
**Langfuse** (open-source, self-hostable) or OpenTelemetry for sessions, user
grouping, alert thresholds, and dashboards.

Token counts let you catch context-window overflows before they happen and
track which prompts are the most expensive.

### Caching & cost control

LLM inference is expensive. A cache keyed on a deterministic hash of
`(model + messages + options)` returns the stored answer at near-zero cost for
repeated or templated prompts.

Key insight: the hash must cover _everything_ the provider sees. If your system
prompt changes, the cache misses — which is correct. If it's stable, you get a
free hit.

**Semantic caching** is the next step: embed the incoming prompt, find the
nearest cached prompt above a similarity threshold, and return that answer. This
handles paraphrased repeats. You'll have all the tools after module 04.

### Guardrails & safety

Guards belong on both sides of the LLM call:

**Input guards:**

- Empty or over-long input — reject early, don't waste tokens.
- Prompt injection — phrases like "ignore previous instructions" are a signal
  that a user is trying to override your system prompt.
- PII (Personally Identifiable Information) scrubbing — email addresses, phone numbers, SSNs should not leave your
  system to a third-party API (Application Programming Interface) without consent.

**Output guards:**

- Refusal detection — "I cannot help with that" is a valid answer, but your UI (User Interface)
  should handle it gracefully rather than showing an error.
- Schema validation — if you expect JSON, parse it and error early if it's not.
- PII echo scrubbing — models sometimes repeat user input verbatim; scrub the
  output too.

### Serving

An HTTP (HyperText Transfer Protocol) server is the final piece. The simplest production path:

- **Python**: FastAPI + Uvicorn. FastAPI's async support maps naturally onto
  async LLM calls and streaming responses.
- **TypeScript**: Node.js built-in `http` module (no framework needed for the
  basics) or Express for routing middleware.

Two endpoint patterns:

1. **Synchronous** (`POST /chat`): wait for the full response, return JSON.
   Simple for clients; higher perceived latency.
2. **Streaming** (`POST /chat/stream`): return tokens as they're generated via
   chunked transfer or Server-Sent Events (SSE). Lower perceived latency at the cost
   of slightly more complex client code.

---

## Setup

```bash
# Python — install FastAPI + uvicorn:
uv sync --extra production

# TypeScript — no extra deps beyond llm-core:
pnpm install
```

**Runtime files** created by the exercises:

| File                 | Created by                   |
| -------------------- | ---------------------------- |
| `llm-calls.jsonl`    | Task 2 observability logging |
| `prompt-cache.jsonl` | Task 3 caching               |

Both are listed in `.gitignore` (or should be — add them if needed).

---

## Tasks

### Task 1 — Eval harness + LLM-as-judge 🟡

**Goal:** Build a harness that runs a set of questions through your LLM system,
scores each answer with a judge LLM, and reports pass rate and average score.

**Steps (Python):**

1. Open `py/01_eval_harness.py`.
2. Add 3+ test cases to `TEST_CASES` (TODO 1).
3. Implement `run_system` to call the LLM with the test input (TODO 2).
4. Implement `judge_output` to score the answer against the rubric (TODO 3).
5. Implement the harness loop (TODO 4) and summary printing (TODO 5).
6. Run: `uv run python modules/07-advanced-production/py/01_eval_harness.py`

**Steps (TypeScript):**

1. Open `ts/01-eval-harness.ts`. Follow the same TODOs 1–5.
2. Run: `pnpm tsx modules/07-advanced-production/ts/01-eval-harness.ts`

**Acceptance:**

- All test cases run and produce a score.
- Summary prints pass rate, average score, and average latency.
- Changing the system prompt changes the scores.

---

### Task 2 — Observability 🟢

**Goal:** Wrap every LLM call in a logger that writes structured JSONL entries
with timing, token counts, and cost estimates.

**Steps (Python):**

1. Open `py/02_observability.py`.
2. Implement `append_log` (TODO 1) and `estimate_cost` (TODO 2).
3. Implement `observed_chat` with try/except/finally so it always logs (TODO 3).
4. Run the main function and inspect `llm-calls.jsonl` (TODO 4).

**Steps (TypeScript):**

1. Open `ts/02-observability.ts`. Follow TODOs 1–4.
2. Run: `pnpm tsx modules/07-advanced-production/ts/02-observability.ts`
3. `cat modules/07-advanced-production/llm-calls.jsonl | python -m json.tool`

**Acceptance:**

- Every call produces a JSONL line with at minimum: id, timestamp, model,
  latency_ms, and response_text.
- The summary shows total estimated cost for the session.

---

### Task 3 — Caching & cost control 🟡

**Goal:** Add a prompt/response cache so repeated queries return instantly at
zero cost, and track actual vs. saved costs.

**Steps (Python):**

1. Open `py/03_caching.py`.
2. Implement `load_cache` and `save_to_cache` (TODOs 1–2).
3. Implement `cache_key` using SHA-256 (TODO 3).
4. Implement `add_cost` (TODO 4) and `cached_chat` (TODO 5).
5. Run: see "[HIT]" on repeated questions with near-zero latency.
6. Print cost summary (TODO 6).

**Steps (TypeScript):**

1. Open `ts/03-caching.ts`. Follow TODOs 1–6.

**Acceptance:**

- Second call for the same question shows `[HIT]` with < 5 ms latency.
- Cost summary shows non-zero `savedCostUsd` after cache hits.
- Delete `prompt-cache.jsonl` and re-run to verify cold cache misses.

---

### Task 4 — Guardrails & safety 🟢

**Goal:** Wrap LLM calls with input validation, PII scrubbing, and output
validation so your service is safe to expose.

**Steps (Python):**

1. Open `py/04_guardrails.py`.
2. Implement `scrub_pii` (TODO 1), `validate_input` (TODO 2),
   `validate_output` (TODO 3), `guarded_chat` (TODO 4).
3. Run and verify each test case produces the right result (TODO 5).

**Steps (TypeScript):**

1. Open `ts/04-guardrails.ts`. Follow TODOs 1–5.

**Acceptance:**

- Empty input is blocked.
- Injection attempt is blocked.
- Email in user message is scrubbed before reaching the model.
- Refusal is detected and returned as a graceful blocked result.
- Normal questions pass through and return answers.

---

### Task 5 — Serve it 🟢

**Goal:** Expose your LLM pipeline as an HTTP service with health check,
synchronous chat, and streaming endpoints.

**Steps (Python):**

1. `uv sync --extra production` to install FastAPI + uvicorn.
2. Open `py/05_serve.py`. Implement TODOs 2–6 (FastAPI app, routes).
3. Run: `uv run python modules/07-advanced-production/py/05_serve.py`
4. Test:
   ```bash
   curl http://localhost:3000/health
   curl -X POST http://localhost:3000/chat \
        -H "Content-Type: application/json" \
        -d '{"message": "What is the capital of France?"}'
   curl -X POST http://localhost:3000/chat/stream \
        -H "Content-Type: application/json" \
        -d '{"message": "Explain recursion in 3 sentences."}'
   ```

**Steps (TypeScript):**

1. Open `ts/05-serve.ts`. Implement TODOs 1–5 (Node.js http server).
2. Run: `pnpm tsx modules/07-advanced-production/ts/05-serve.ts`
3. Same curl commands work (same port, same paths).

**Acceptance:**

- `GET /health` returns `{ "status": "ok" }`.
- `POST /chat` returns a JSON response with the answer text.
- `POST /chat/stream` streams tokens as they arrive (visible with `curl -N`).

---

### Task 6 🟡 — Langfuse: production tracing

**Goal:** Replace Task 2's hand-rolled JSONL tracer with **Langfuse**, the
industry-standard open-source LLM-observability platform. Task 2 taught you the
_shape_ of a trace (input, output, model, tokens, latency, cost); this task
sends that same data to a managed backend that gives you **traces**, **sessions**
(grouped conversations), **dashboards**, and **cost roll-ups** for free — no
JSONL to grep, no dashboard to build.

The teaching move here is a tracer-**agnostic** interface: your app is
instrumented once against a small `Tracer`, and you swap the backend at runtime.
With no keys set it uses a `LocalTracer` that prints an indented trace tree —
so the exercise is fully runnable offline, no Langfuse account required.

**Contrast with Task 2:**

|               | Task 2 (hand-rolled)    | Task 6 (Langfuse)                        |
| ------------- | ----------------------- | ---------------------------------------- |
| Storage       | local `llm-calls.jsonl` | managed platform (hosted or self-hosted) |
| Grouping      | none                    | traces + sessions                        |
| Dashboards    | you build them          | built in                                 |
| Cost tracking | you sum it              | rolled up per session/model/user         |

**Files:** `py/06_langfuse_tracing.py`, `ts/06-langfuse-tracing.ts`.

**Environment variables (all optional — absent ⇒ offline `LocalTracer`):**

| Var                   | Meaning                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------- |
| `LANGFUSE_PUBLIC_KEY` | project public key (`pk-lf-…`) — enables the hosted tracer                               |
| `LANGFUSE_SECRET_KEY` | project secret key (`sk-lf-…`)                                                           |
| `LANGFUSE_HOST`       | API host; defaults to `https://cloud.langfuse.com` (set to your own URL if self-hosting) |

Get free keys at <https://cloud.langfuse.com> (or self-host with Docker).

**Steps (Python):**

1. `uv sync --extra production` (installs `langfuse`).
2. Open `py/06_langfuse_tracing.py`. Implement `estimate_cost` (TODO 1), the
   generation-instrumentation in `traced_chat` (TODO 2), and
   `LocalTracer.generation` (TODO 3). The `LangfuseTracer` body is provided
   complete — study it for correct SDK (Software Development Kit) usage.
3. Run offline: `uv run python modules/07-advanced-production/py/06_langfuse_tracing.py`
   — prints a trace tree and a session cost summary.
4. (Optional) `export LANGFUSE_PUBLIC_KEY=… LANGFUSE_SECRET_KEY=…` and re-run to
   see the same data in the hosted UI.

**Steps (TypeScript):**

1. From `modules/07-advanced-production/ts`: `pnpm add langfuse@^3.0.0`.
2. Open `ts/06-langfuse-tracing.ts`. Implement TODOs 1–3 (same as Python).
3. Run: `pnpm tsx modules/07-advanced-production/ts/06-langfuse-tracing.ts`.

**Acceptance:**

- With no keys set, the demo prints an indented trace tree (trace → generations
  with model, latency, tokens, cost) and a session total — with no network call.
- All 3 questions are recorded under **one** trace/session.
- Setting `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` switches to the hosted
  tracer with no other code change.

---

## Done when

- [ ] Task 1: eval harness runs all test cases and prints pass rate + scores.
- [ ] Task 2: every LLM call writes a JSONL line; session cost total is visible.
- [ ] Task 3: repeated questions hit the cache; cost savings are quantified.
- [ ] Task 4: injection attempts blocked, PII scrubbed, refusals handled.
- [ ] Task 5: the service responds correctly to all three curl examples above.
- [ ] Task 6: the demo runs offline, prints a trace tree, and groups all calls
      under one trace/session; adding Langfuse keys sends the same data to the UI.

---

## Going deeper

- **Langfuse**: open-source LLM observability platform with session tracing, user
  grouping, and a score dashboard. Drop-in replacement for the JSONL logger — you
  build it in **Task 6**. Docs: <https://langfuse.com/docs> (SDK reference:
  <https://langfuse.com/docs/sdk/python> / <https://langfuse.com/docs/sdk/typescript>).
- **OpenTelemetry**: industry-standard distributed tracing — useful when your LLM
  service is one node in a larger microservice graph.
- **Semantic caching**: embed incoming prompts and find nearest cached embeddings
  above a threshold. Handles paraphrased repeats that exact-hash caches miss.
- **Structured outputs**: OpenAI's `response_format: { type: "json_schema" }` and
  Anthropic's tool-use mode guarantee valid JSON output — stronger than output
  validation after the fact.
- **Red-teaming**: systematic adversarial testing to find guardrail bypasses.
  Automate it: run an "attacker" LLM that generates injection attempts against
  your guarded pipeline and measure the block rate.
