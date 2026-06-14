# Module 15 — Reasoning & Test-Time Compute

Standard LLMs answer immediately: one forward pass, one output.
*Reasoning* models and *test-time compute* strategies spend extra computation at
inference time — before (or during) returning an answer — trading latency and cost
for correctness on hard multi-step problems.

This module makes the trade-off concrete: you'll compare a standard model against a
reasoning model, implement self-consistency and best-of-N sampling yourself, build a
self-refine loop, and finally plot the cost/accuracy curve so you can decide when the
extra compute is actually worth it.

---

## Concepts

### What are "reasoning models"?

OpenAI's o1/o3 family and Anthropic's *extended thinking* feature both allocate
extra compute to internal deliberation before producing the visible output.
The model generates a hidden "scratchpad" of chain-of-thought and only then
produces the final reply.

Key properties:
- **Higher accuracy** on hard math, code, and multi-step logic.
- **Higher latency and cost** — the hidden tokens still cost money (often at a premium).
- **Less controllable** — you cannot steer the internal reasoning; only the prompt.
- **Not always better** — for simple retrieval or single-step tasks, the overhead is pure waste.

### Extended (adaptive) thinking — Anthropic

Claude's extended thinking (`betas=["interleaved-thinking-2025-05-14"]`) lets the model
emit `<thinking>` blocks visible in the raw response before its final answer.
You control `budget_tokens` to cap the hidden reasoning budget.
Access via the `anthropic` SDK directly — `llm_core`'s `chat()` wrapper does not expose
the beta parameter. This is an intentional *beyond-the-abstraction* lesson.

### OpenAI reasoning models (o1, o3, o4-mini)

Pass `model="o4-mini"` (or `o1`, `o3-mini`) to the OpenAI SDK.
These models use `max_completion_tokens` instead of `max_tokens`.
There is no streaming for reasoning tokens; the visible `usage.completion_tokens_details`
shows how many tokens were spent reasoning vs. the visible output.
Set `reasoning_effort` (`"low"/"medium"/"high"`) to tune the compute budget.

### Test-time compute WITHOUT a reasoning model

You can approximate reasoning-model behaviour with any standard model:

| Strategy | Mechanism | Cost |
|---|---|---|
| **Deeper CoT** | Longer "think step by step" prompt | 1 × more output |
| **Self-consistency** | Sample N times, majority-vote | N × cost |
| **Best-of-N + verifier** | Sample N, score each with a verifier LLM, pick the top | ~2N × cost |

Self-consistency and best-of-N are especially powerful when you can write a cheap
verifier (a unit test, a math checker, a regex) — the verifier is the secret weapon.

### Self-refine / reflection

Draft → critique → revise is a three-turn loop that mimics how a human reviews
their own work. Even a single iteration frequently improves factual accuracy, clarity,
and completeness on open-ended tasks. Multiple iterations usually converge quickly
(the gain from iteration 3 is rarely worth iteration 2's cost).

### The cost/latency vs. quality curve

Plotting accuracy against compute (tokens × price) reveals:
- A steep improvement phase (going from 0-shot to CoT or 1 reasoning pass).
- A plateau where extra compute yields diminishing returns.
- Occasional regressions at very high N (majority vote can amplify the wrong answer
  if the verifier or sampling distribution is biased).

Understanding where your task sits on this curve is the engineering decision.

---

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for extended-thinking tasks |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Base model for Anthropic calls |
| `OPENAI_API_KEY` | — | Required for OpenAI reasoning model tasks |
| `OPENAI_REASONING_MODEL` | `o4-mini` | The reasoning model to compare against |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | The standard model to compare against |
| `LLM_PROVIDER` | `ollama` | Default provider for tasks that use `get_provider()` |

No changes to `.env.example` are needed — document your values in your local `.env`.

---

## Tasks

### Task 1 🟢 — Reasoning vs standard model

**Goal:** Send the same hard multi-step problem to a standard model and a reasoning
model. Compare correctness, token counts, and wall-clock latency side by side.

**Steps:**
1. Open `py/01_reasoning_vs_standard.py` / `ts/01-reasoning-vs-standard.ts`.
2. Implement `call_standard(question)` — use `get_provider("openai")` with
   `gpt-4o-mini` (or your default provider).
3. Implement `call_reasoning(question)` — use the OpenAI SDK directly with `o4-mini`
   and `reasoning_effort="medium"`, OR use the Anthropic SDK with `extended_thinking`.
4. For each test problem, call both, record latency, and print a comparison table.

**Acceptance:**
- Both implementations return an answer for each test problem.
- The table shows model, answer, input tokens, output tokens, latency (ms).
- You can articulate in one sentence why the reasoning model does (or does not) score better.

---

### Task 2 🟡 — Test-time compute without a reasoning model

**Goal:** Implement self-consistency (sample N, majority vote) and best-of-N with a
verifier to raise accuracy on a standard model without upgrading to a reasoning model.

**Steps:**
1. Open `py/02_test_time_compute.py` / `ts/02-test-time-compute.ts`.
2. Implement `self_consistency(question, n)` — sample N CoT completions at
   `temperature=0.8`, extract the final answer from each, return `majority_vote(answers)`.
3. Implement a simple `verify(question, answer)` — call the LLM with a short prompt
   "Is this answer correct? Reply YES or NO." using temperature=0.
4. Implement `best_of_n(question, n)` — sample N answers, run the verifier on each,
   return the first answer that the verifier approves (or the majority-vote fallback).
5. Run all three strategies (1-shot, self-consistency, best-of-N) on the test problems
   and print accuracy + total tokens used.

**Acceptance:**
- `self_consistency` samples exactly N times and uses majority vote.
- `best_of_n` calls the verifier and returns the approved answer.
- The output table shows strategy, correct/total, tokens spent.

---

### Task 3 🟡 — Self-refine / reflection

**Goal:** Build a draft → critique → revise loop; measure whether each iteration improves the answer.

**Steps:**
1. Open `py/03_self_refine.py` / `ts/03-self-refine.ts`.
2. Implement `draft(task)` — generate an initial answer.
3. Implement `critique(task, draft_text)` — ask the model "What is wrong or missing
   in this answer? Be specific and list issues." Return the critique text.
4. Implement `revise(task, draft_text, critique_text)` — ask the model to produce an
   improved answer given the critique. Return the revised text.
5. Run the loop for `MAX_ITERATIONS` (default 2), printing each draft → critique → revision.
6. Compare the original draft to the final revision on a rubric (length, specificity, any
   factual changes). Even a simple "did it change?" is a valid start.

**Acceptance:**
- Each iteration produces a visible critique and a revised answer.
- After `MAX_ITERATIONS` the final answer is printed alongside the original draft.
- You can observe (and describe) at least one concrete improvement in the revision.

---

### Task 4 🟢 — Cost / latency of reasoning strategies

**Goal:** Produce a summary table (or ASCII chart) showing tokens used and wall time
for each strategy from Tasks 1–3, making the trade-off tangible.

**Steps:**
1. Open `py/04_cost_latency.py` / `ts/04-cost-latency.ts`.
2. Import or copy the functions you built in Tasks 1–3 (or call them as subprocesses).
3. Run each strategy on a fixed benchmark set of 3 problems.
4. For each run, record: strategy name, total input tokens, total output tokens,
   wall time (ms), number of correct answers.
5. Compute estimated cost using a price table (see module 02's price table for reference).
6. Print a table sorted by cost. Annotate the "sweet spot" (best accuracy-per-dollar).

**Acceptance:**
- The table has at least 4 rows (standard, CoT, self-consistency-3, best-of-3, reasoning-model).
- Costs and latencies are real measured values, not hard-coded estimates.
- You can point to the row with the best accuracy-per-dollar.

---

## Done when

- [ ] Task 1: a side-by-side table comparing standard vs. reasoning model on at least 2 problems.
- [ ] Task 2: self-consistency and best-of-N are implemented and show accuracy rising with N.
- [ ] Task 3: the self-refine loop runs for 2 iterations and produces a visibly improved answer.
- [ ] Task 4: cost/latency table covers all strategies; you can name the sweet spot for a given budget.

---

## Going deeper

- [Chain-of-Thought Prompting (Wei et al. 2022)](https://arxiv.org/abs/2201.11903)
- [Self-Consistency (Wang et al. 2022)](https://arxiv.org/abs/2203.11171)
- [Self-Refine (Madaan et al. 2023)](https://arxiv.org/abs/2303.17651)
- [Let's Verify Step by Step (Lightman et al. 2023)](https://arxiv.org/abs/2305.20050) — process reward models
- [Scaling LLM Test-Time Compute (Snell et al. 2024)](https://arxiv.org/abs/2408.03314)
- [OpenAI o1 system card](https://openai.com/index/openai-o1-system-card/)
- [Anthropic extended thinking docs](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking)
- [OpenAI reasoning models guide](https://platform.openai.com/docs/guides/reasoning)
