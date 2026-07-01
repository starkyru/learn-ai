# Module 02 — LLM Integration

In module 00 you sent a single message and got a reply.
Here you learn everything that happens _around_ that call in a real application:
conversation history, streaming UX (User Experience), cost accounting, structured data extraction,
tool calling, and making your code resilient to flaky APIs (Application Programming Interfaces).

By the end you'll have working implementations of structured-output extraction
and a tool-calling agent turn — the two patterns that appear in almost every
production LLM (Large Language Model) feature.

---

## Concepts

### The request/response loop

Every `chat()` call is stateless on the server side.
The model has no memory between calls.
"Memory" = you sending the full conversation history every time.
The history is a list of `{role, content}` messages: `system → user → assistant → user → …`

The **context window** is the maximum total tokens (input + output) the model can process at once.
Exceeding it causes truncation or an error — managing it is your responsibility.

### Streaming

Instead of waiting for the full response, streaming returns tokens as they're generated via
Server-Sent Events (SSE). The SDK (Software Development Kit) converts SSE into a Python iterator / TS async iterable.
**Time-to-first-token (TTFT)** is the latency the user actually _perceives_;
total generation time matters for throughput but TTFT matters for feel.

### Tokens and cost

LLMs process _tokens_, not words. A token is roughly 3-4 characters of English text.
`tiktoken` (used for GPT (Generative Pre-trained Transformer) models) lets you count tokens client-side.
Cost = `(input_tokens / 1_000_000) × price_in + (output_tokens / 1_000_000) × price_out`.
Prices vary by an order of magnitude between models — making this concrete is the goal of task 3.

### Structured output

Asking a model to return JSON (JavaScript Object Notation) requires:

1. A prompt that describes the exact schema.
2. A parser (`json.loads` / `JSON.parse`) that handles markdown fences and other noise.
3. A validator (Pydantic / Zod) that gives you a typed object and catches missing/wrong fields.
4. A retry or repair loop for when parsing fails.

JSON mode (supported by OpenAI and Ollama) forces valid JSON output but not a specific schema;
schema-constrained decoding (supported by some providers) goes further. For maximum portability,
prompt-based extraction + Pydantic/Zod validation works everywhere.

### Tool / function calling — going beyond llm_core

`llm_core`'s `chat()` wraps the common subset of all provider APIs.
Tool calling requires richer request shapes — tool definitions, `tool_choice`, result messages —
that don't fit a one-size-fits-all wrapper.
This is **intentional**: the abstraction leaks here to teach you _where_ it leaks and why.

The tool loop:

```
you → [messages + tool defs] → model
model → [tool_call: name + args JSON]
you → execute the tool locally
you → [messages + tool result] → model
model → [final text answer]
```

OpenAI and Anthropic use different wire formats (different JSON keys, different role for tool results)
but the loop logic is identical.

### Retries and errors

LLM API calls fail:

- **429 Rate Limit** — back off and retry.
- **500 / 502 / 503 Server Error** — usually transient; retry.
- **401 Unauthorized** — your API key is wrong; retrying won't help.
- **400 Bad Request** — malformed payload; retrying won't help.

Exponential backoff with jitter: `delay = base × 2^attempt + random(0, base)`.
The OpenAI and Anthropic SDKs retry automatically (2 times by default) — this exercise
teaches the pattern so you can tune it and apply it to any remote call.

---

## Tasks

### Task 1 🟢 — Chat & system prompts

**Goal:** Build a multi-turn chat loop that maintains history and uses a system prompt.

**Steps:**

1. Open `py/01_chat.py` and `ts/01-chat.ts`.
2. Follow the TODOs to define a system prompt and initialise the history.
3. In the chat loop, append the user message, call `llm.chat(history)`, append the reply, and print it.
4. Run the file and have a 3-turn conversation. Observe that the model remembers what you said earlier.
5. (Stretch) Print the full history at the end — see the context growing.

**Acceptance:**

- The assistant responds in character with your system prompt.
- Earlier turns are referenced in later replies (context is preserved).
- Typing "exit" ends the loop cleanly.

---

### Task 2 🟢 — Streaming

**Goal:** Render tokens live as they arrive; measure time-to-first-token.

**Steps:**

1. Open `py/02_streaming.py` and `ts/02-streaming.ts`.
2. Use `llm.chat_stream()` / `llm.chatStream()` and iterate over chunks.
3. Write each chunk to stdout without a newline (so they appear inline).
4. Record `start_time`, `first_token_time`, and `end_time`; print stats.
5. Compare TTFT and total time across providers.

**Acceptance:**

- Tokens appear progressively, not all at once.
- TTFT, total time, and approximate words/second are printed.

---

### Task 3 🟡 — Tokens & cost

**Goal:** Count tokens with tiktoken; build a cost estimator; compare models.

**Steps:**

1. Open `py/03_tokens_cost.py` and `ts/03-tokens-cost.ts`.
2. Implement `count_tokens` using tiktoken (Python) or `@dqbd/tiktoken` (TS).
   - Python: `tiktoken.get_encoding("cl100k_base")`.
   - TS: `get_encoding("cl100k_base")` from `@dqbd/tiktoken` — remember to call `.free()` on the encoder.
3. Implement `estimate_cost` using the price table provided.
4. Make a real API call and compare your tiktoken estimate to `result.usage`.
5. Print the cost comparison table for all models.

**Acceptance:**

- `count_tokens` uses tiktoken, not a word-count approximation.
- The cost table prints with correct values for at least 3 models.
- Your tiktoken estimate is within ~5% of the provider's reported count.

---

### Task 4 🟢 — Structured output

**Goal:** Extract typed data from free-form text using Pydantic (Python) or Zod (TS).

**Note:** Pydantic is in the base Python deps. Zod is added to `ts/package.json` for this module.

**Steps:**

1. Open `py/04_structured_output.py` and `ts/04-structured-output.ts`.
2. Review the `Recipe` schema (Pydantic model / Zod object).
3. Implement `build_prompt` — embed the schema description in the system message.
4. Implement `parse_recipe`:
   - Strip markdown code fences (` ```json ... ``` `).
   - Parse JSON.
   - Validate with Pydantic `model_validate` / Zod `parse`.
5. Call the LLM at `temperature=0.1`, parse the result, pretty-print it.
6. Add a retry loop: on parse failure, tell the model what went wrong and ask it to fix the JSON.

**Acceptance:**

- The function returns a typed, validated `Recipe` / `z.infer<typeof RecipeSchema>` object.
- On a bad model response the retry loop runs and the model self-corrects.

---

### Task 5 🟢 — Tool / function calling

**Goal:** Implement the manual tool loop using the raw OpenAI and Anthropic SDKs.

**Why not llm_core?** `llm_core.chat()` has no parameter for tool definitions or tool results —
those shapes vary per provider. Task 5 is explicitly about dropping down to the raw SDK.

**Run it free / locally (Ollama or LM Studio):** Part A speaks the raw OpenAI wire format,
and both Ollama and LM Studio are OpenAI-compatible — so the same `openai` SDK code works
against them with **no changes**, just env vars:

| Server    | Env                                               | Default endpoint            |
| --------- | ------------------------------------------------- | --------------------------- |
| LM Studio | `LLM_PROVIDER=lmstudio` (+ `LMSTUDIO_CHAT_MODEL`) | `http://localhost:1234/v1`  |
| Ollama    | `LLM_PROVIDER=ollama` (+ `OLLAMA_CHAT_MODEL`)     | `http://localhost:11434/v1` |

> **Tool calling depends on the _model_, not the server.** Use a tool-tuned instruct model
> (Qwen2.5-Instruct, Llama-3.1/3.2-Instruct, Mistral-Nemo). Small or heavily quantized models
> often skip the tool call or return malformed argument JSON. If `finish_reason` looks off on a
> local model, gate on `message.tool_calls?.length` instead. (LM Studio: load the model, then
> **Start Server** so `:1234` is live; Ollama: `ollama pull llama3.2` first.) **Part B (Anthropic)
> uses its own SDK and wire format — it has no local equivalent here.**

**Steps:**

1. Open `py/05_tool_calling.py` and `ts/05-tool-calling.ts`.
2. **Part A (OpenAI-style):**
   - Fill in `WEATHER_TOOL` / `weatherToolDefinition` with the JSON Schema for `get_weather`.
   - Call `client.chat.completions.create(...)` with `tools` and `tool_choice: "auto"`.
   - Check `finish_reason == "tool_calls"` (OpenAI) or the equivalent.
   - Execute the tool, append the tool result message, call the API again.
   - Print the final answer.
3. **Part B (Anthropic-style):**
   - Repeat the loop using the `anthropic` SDK's different format.
   - Note: Anthropic tool results go inside a `user` message, not a top-level `tool` role.
4. Ask a question that requires looking up two cities — the model should call the tool twice.

**Acceptance:**

- The model correctly calls `get_weather` and incorporates the result in its final answer.
- Both OpenAI-style and Anthropic-style loops work (if you have both keys).
- The conversation shows: initial call → tool call → tool result → final answer.

---

### Task 6 🟡 — Retries & errors

**Goal:** Wrap LLM calls with exponential backoff; distinguish retriable from permanent errors.

**Steps:**

1. Open `py/06_retries.py` and `ts/06-retries.ts`.
2. Implement `is_retriable(error)` — return True for 429/5xx, False for 401/400.
3. Implement `with_retry(fn, max_retries, base_ms)` using the exponential backoff algorithm.
4. Run Test 1 (flaky → success) and Test 2 (permanent → fail immediately) to validate.
5. Wrap `llm.chat()` with `with_retry` and run Test 3 against a real provider.

**Acceptance:**

- `with_retry` retries up to `max_retries` times for 429/5xx errors.
- `with_retry` does NOT retry for 401/400 errors.
- The delay roughly doubles between each attempt (check the log output).

---

## Done when

- [ ] Task 4: you can pass arbitrary text to `parse_recipe` and get a validated Python/TS object back.
- [ ] Task 5: the model calls `get_weather`, you execute it, and the model uses the result in its reply.
- [ ] Both tasks work with at least one provider.

---

## Going deeper

- [OpenAI function calling guide](https://platform.openai.com/docs/guides/function-calling)
- [Anthropic tool use guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [tiktoken repo](https://github.com/openai/tiktoken) — how BPE (Byte-Pair Encoding) tokenization works
- [Zod documentation](https://zod.dev/) — schema-first TypeScript validation
- [Pydantic v2 docs](https://docs.pydantic.dev/latest/) — Python data validation
- OpenAI cookbook: [How to count tokens](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
