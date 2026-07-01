# Module 16 — Context Engineering

The context window is not unlimited — it is a scarce, metered budget.
Every token you put in costs money and time; every token you leave out is information
the model cannot use. _Context engineering_ is the art of spending that budget wisely.

By the end of this module you will have measured token counts precisely, cached a large
repeated prefix to save cost, compacted long conversations so they don't overflow, applied
map-reduce over a document too large to fit in one call, and submitted a batch of requests
at a discount.

---

## Concepts

### The context window as a budget

The context window is the maximum number of tokens (input + output combined) that a model
can process in a single call. Typical sizes in 2025:

| Model            | Context |
| ---------------- | ------- |
| gpt-4o-mini      | 128 K   |
| claude-haiku-4-5 | 200 K   |
| claude-opus-4-8  | 200 K   |
| gemini-1.5-pro   | 1 M     |

Exceeding the limit produces an error or silent truncation. You are responsible for managing it.
The limit is input + output, so a longer system prompt leaves less room for the user's document.

### Token counting

Tokens are sub-word units produced by the tokeniser. A rule of thumb: 1 token ≈ 3–4 English
characters. To count precisely:

- Python: `tiktoken` (for OpenAI models); the Anthropic SDK's `client.beta.messages.count_tokens()`.
- TypeScript: `@dqbd/tiktoken` (WASM port of tiktoken); Anthropic SDK `.beta.messages.countTokens()`.

Counting before sending a request lets you enforce budgets and choose a truncation strategy.

### Prompt caching

Making repeated calls with a large, unchanging prefix (a long system prompt, a big document,
tool definitions) normally re-charges the full input cost on every call. Prompt caching avoids this:

- **Anthropic** — mark cache breakpoints in the message list using `cache_control: {"type": "ephemeral"}`.
  The cache hit is visible in `usage.cache_read_input_tokens`. Cache TTL is 5 minutes.
- **OpenAI** — caching is automatic for inputs > 1024 tokens. No extra parameters needed.
  Cache reads appear in `usage.prompt_tokens_details.cached_tokens`.

Both providers charge a fraction of the normal input price for cache hits (often 10–20 % of
the full rate). This is a _beyond-the-abstraction_ feature: you must use the provider SDKs (Software Development Kits) directly.

### Conversation memory / compaction

In a long chat, the context window fills up with old turns. Two standard mitigations:

1. **Sliding window** — keep only the last K turns (simple; loses old context entirely).
2. **Running summary** — when the conversation exceeds a token budget, summarise the oldest
   turns into a short paragraph, replace them with the summary, and continue. The model
   retains the gist without the full verbatim history.

A hybrid ("keep the last K turns AND a running summary of everything older") is the most robust.

### Long-context strategies

Even with a 200 K context window, fitting an entire corpus is wasteful and often degrades quality.

**Map-reduce:**

1. _Map_: process each chunk independently (extract, summarise, answer).
2. _Reduce_: combine the chunk results into a final answer.

**Refine:**

1. Process chunk 1 → interim answer.
2. Process chunk 2 + interim answer → updated answer.
3. Repeat for all chunks.

**Lost in the middle:** LLMs (Large Language Models) recall information near the beginning and end of context better than
in the middle. Placing the most important content first (or last) outperforms putting it in the middle.

### Batch API

The Batch API (Application Programming Interface) lets you submit hundreds of requests in one API call, processed asynchronously
(typically within 24 hours). In return, providers typically charge 50 % of the live price.
Best for: eval runs, data extraction pipelines, bulk summarisation — any workload that is
not latency-sensitive.

- **OpenAI**: `client.batches.create(...)` with a JSONL (JSON Lines) file of requests. Poll `client.batches.retrieve(id)`.
- **Anthropic**: `client.beta.messages.batches.create(...)`. Poll `client.beta.messages.batches.retrieve(id)`.

This is beyond `llm_core`'s abstraction — use the SDKs directly.

---

## Environment variables

| Var                 | Default           | Purpose                                           |
| ------------------- | ----------------- | ------------------------------------------------- |
| `OPENAI_API_KEY`    | —                 | OpenAI token counting, caching, and batch         |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini`     | Model for OpenAI tasks                            |
| `ANTHROPIC_API_KEY` | —                 | Anthropic prompt caching and batch                |
| `ANTHROPIC_MODEL`   | `claude-opus-4-8` | Model for Anthropic tasks                         |
| `LLM_PROVIDER`      | `ollama`          | Default provider for tasks using `get_provider()` |

No changes to `.env.example` are needed — add values to your local `.env`.

### Extra Python dependencies

Task 1 uses `tiktoken` for token counting:

```bash
uv sync --extra context
```

Add `context = ["tiktoken>=0.7"]` to `pyproject.toml` if the extra is not already present.
For TypeScript, `@dqbd/tiktoken` is included in `ts/package.json`.

---

## Tasks

### Task 1 🟢 — Token budgeting

**Goal:** Count tokens precisely; fit a prompt to a token budget; compare truncation strategies.

**Steps:**

1. Open `py/01_token_budgeting.py` / `ts/01-token-budgeting.ts`.
2. Implement `count_tokens(text)` using tiktoken (`cl100k_base` encoding).
3. Implement `truncate_head(text, max_tokens)` — keep the first `max_tokens` tokens (drop tail).
4. Implement `truncate_tail(text, max_tokens)` — keep the last `max_tokens` tokens (drop head).
5. Implement `truncate_middle_out(text, max_tokens)` — keep the first and last quarter of the
   budget and drop content from the middle.
6. Run all three strategies on a long sample text. Print: original token count, strategy, result
   token count, and which part of the original was lost.

**Acceptance:**

- `count_tokens` uses tiktoken, not a word-count approximation.
- Each truncation strategy stays at or below `max_tokens`.
- The output table shows all three strategies and what was lost.

---

### Task 2 🟢 — Prompt caching

**Goal:** Use provider prompt caching to cut cost and latency on a repeated large prefix;
measure cache hits via the `usage` field.

> **Beyond the abstraction** — `llm_core.chat()` does not expose caching parameters.
> Use the `anthropic` or `openai` SDK directly for this task.

**Steps:**

1. Open `py/02_prompt_caching.py` / `ts/02-prompt-caching.ts`.
2. Build a large system prompt (> 1024 tokens) — include a long document or a lengthy instruction set.
3. **Anthropic path**: add `cache_control: {"type": "ephemeral"}` to the system message block.
   Make the same call twice; on the second call observe `usage.cache_read_input_tokens > 0`.
4. **OpenAI path**: make the same call twice with input > 1024 tokens.
   On the second call observe `usage.prompt_tokens_details.cached_tokens > 0`.
5. Print: call number, input tokens (uncached), cached tokens, output tokens, estimated cost.

**Acceptance:**

- The second call shows a non-zero cache hit.
- Estimated cost of the second call is lower than the first.
- You can explain (one sentence) why the cache TTL matters for real workloads.

---

### Task 3 🟡 — Conversation memory / compaction

**Goal:** Summarise old turns when a chat grows past a token budget; keep answers coherent.

**Steps:**

1. Open `py/03_memory_compaction.py` / `ts/03-memory-compaction.ts`.
2. Implement `count_history_tokens(messages)` — sum `count_tokens` across all messages.
3. Implement `summarise_turns(turns, llm)` — ask the model to produce a 2–3 sentence
   summary of the conversation so far. Return a single `ChatMessage(role="system", content="Summary: …")`.
4. Implement `maybe_compact(messages, budget, llm)`:
   - If `count_history_tokens(messages) > budget`, find the oldest non-system turns,
     summarise them, replace them with the summary message, and return the new message list.
   - Otherwise return messages unchanged.
5. Run a simulated 15-turn conversation that eventually exceeds the budget.
   After each compaction, ask a question about an early turn — observe whether the model still knows it.

**Acceptance:**

- Compaction fires when the budget is exceeded.
- After compaction the context fits within the budget.
- The model can still answer questions about summarised turns (loosely — it may paraphrase).

---

### Task 4 🟡 — Long-context strategies

**Goal:** Apply map-reduce and refine over a document too large to fit in a single call;
observe the "lost in the middle" effect.

**Steps:**

1. Open `py/04_long_context.py` / `ts/04-long-context.ts`.
2. Generate or load a long document (at least 4 chunks of ≥ 500 tokens each).
   The `LONG_DOCUMENT` constant in the starter is sufficient.
3. Implement `split_into_chunks(text, max_tokens_per_chunk)` — split by `count_tokens`.
4. Implement `map_reduce(chunks, question, llm)`:
   - _Map_: for each chunk, ask "Based on this excerpt, answer: {question}" — collect mini-answers.
   - _Reduce_: combine all mini-answers into a final answer with one more LLM call.
5. Implement `refine(chunks, question, llm)`:
   - Start with an empty interim answer.
   - For each chunk, send: interim + chunk + question → updated interim.
   - Return the final interim.
6. Demonstrate "lost in the middle": plant a unique fact (a name, a number) in the first chunk,
   the middle chunk, and the last chunk. Ask the model about all three. Print recall accuracy.

**Acceptance:**

- `split_into_chunks` produces chunks at or below `max_tokens_per_chunk`.
- `map_reduce` and `refine` both return a coherent final answer.
- The lost-in-the-middle demo shows which placement (first/middle/last) is recalled most reliably.

---

### Task 5 🟢 — Batch API

**Goal:** Submit multiple requests via the Batch API and poll for results; compare cost vs live calls.

> **Beyond the abstraction** — use the `anthropic` or `openai` SDK directly.

**Steps:**

1. Open `py/05_batch_api.py` / `ts/05-batch-api.ts`.
2. Prepare a list of 5 classification or summarisation requests.
3. **OpenAI path**: write a JSONL file of requests; call `client.batches.create()`;
   poll `client.batches.retrieve(id)` until `status == "completed"`.
   Retrieve the output file; parse and print results.
4. **Anthropic path**: call `client.beta.messages.batches.create(requests=[...])`;
   poll `client.beta.messages.batches.retrieve(id)` until `processing_status == "ended"`;
   iterate `client.beta.messages.batches.results(id)` to collect results.
5. Print: request id, result text, and total processing time.
6. Estimate the cost saving vs making the same calls live.

**Acceptance:**

- Batch is submitted, polled, and results are printed without manual intervention.
- Cost savings (50 % discount) are printed.
- You can articulate when batching beats live calls and when it doesn't.

---

## Done when

- [ ] Task 1: `count_tokens` uses tiktoken; all three truncation strategies print a results table.
- [ ] Task 2: second call shows a cache hit and lower estimated cost than the first call.
- [ ] Task 3: compaction fires; the context stays within budget; coherence is preserved.
- [ ] Task 4: map-reduce and refine both produce answers; lost-in-the-middle is demonstrated.
- [ ] Task 5: batch job completes, results are printed, and cost savings are calculated.

---

## Going deeper

- [Anthropic prompt caching guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [OpenAI prompt caching guide](https://platform.openai.com/docs/guides/prompt-caching)
- [OpenAI Batch API guide](https://platform.openai.com/docs/guides/batch)
- [Anthropic Message Batches API](https://docs.anthropic.com/en/docs/build-with-claude/message-batches)
- [Lost in the Middle (Liu et al. 2023)](https://arxiv.org/abs/2307.03172)
- [tiktoken](https://github.com/openai/tiktoken)
- [MemGPT (Packer et al. 2023)](https://arxiv.org/abs/2310.08560) — LLM with external memory for infinite context
