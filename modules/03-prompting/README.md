# Module 03 — Prompting & Patterns

The biggest leverage point in LLM (Large Language Model) applications isn't the model — it's the prompt.
But "prompt engineering" sounds like voodoo until you treat it empirically:
form a hypothesis, test it on a small labelled dataset, measure accuracy, pick the winner.

This module teaches prompt engineering as a discipline, not a dark art.
By the end you'll have a working eval harness that lets you compare two prompt variants
with numbers — the same principle behind Anthropic's and OpenAI's own prompt evaluations.

---

## Concepts

### Templates and roles

Raw string concatenation for prompts has invisible bugs (typo in a variable name = silent failure).
A tiny `render_template("Hello {{name}}", {"name": "Alice"})` helper makes the template shape
explicit and raises early on missing keys.

Roles:

- **system** — highest-trust instructions. Sets persona, constraints, output format.
  Users can't easily override this.
- **user** — the request. This is what the model "answers".
- **assistant** — the model's reply. In few-shot prompts, you inject _example_ assistant replies here.

### Few-shot vs zero-shot

**Zero-shot:** task description only. The model generalises from training.
**Few-shot:** task description + k `(user, assistant)` example pairs before the real query.
The model reads the pattern from the examples.

Trade-offs:

- More examples → usually better accuracy.
- More examples → more tokens → more cost.
- Diminishing returns beyond 5-10 examples.
- One well-chosen example often outperforms three mediocre ones.

### Chain-of-thought (CoT)

Asking the model to "think step by step" before answering forces it to surface intermediate
reasoning it would otherwise hide. This dramatically improves accuracy on tasks that require
multi-step logic, arithmetic, or causal reasoning.

Cost: CoT responses are much longer (more output tokens). Use it selectively on hard tasks.

### Self-consistency

Sample the same CoT prompt N times at `temperature > 0` (so each run takes a different
reasoning path) and majority-vote the final answer. Individual samples may err; voting
averages out the noise.

Cost: N × CoT tokens. Use when accuracy matters more than speed/cost.

### Output parsing & guardrails

The repair loop:

1. Send prompt.
2. Try to parse the output into the required format.
3. On failure: append the bad response + a correction message to the history.
4. Call the model again. Repeat up to max_retries.
5. Give up and raise after exhausting retries.

This pattern appears in every production LLM feature.

### Prompt eval harness

Without measurement, prompt engineering is guessing. The eval harness:

1. Load a labelled dataset (10 examples in `eval_dataset.json`).
2. Define prompt variants.
3. Run each variant on every example.
4. Score by accuracy (predicted label == expected label).
5. Print a comparison table. Pick the winner.

This is the same principle behind large-scale evaluations — just at a smaller scale you can
run locally in minutes.

---

## Tasks

### Task 1 🟢 — Templates & roles

**Goal:** Build a reusable prompt-template helper and test it with two tasks.

**Steps:**

1. Open `py/01_templates.py` and `ts/01-templates.ts`.
2. Implement `render_template` / `renderTemplate` — replace `{{key}}` placeholders.
   Raise on missing keys.
3. Implement `call_with_system` — a helper that sends a system + user message and returns the reply.
4. Use `TEMPLATES["summarise"]` to summarise the sample text in 2 sentences.
5. Use `TEMPLATES["classify"]` to classify three texts. Print the raw output — note any noise.

**Acceptance:**

- `render_template("Hello {{name}}", {"name": "Alice"})` → `"Hello Alice"`.
- Missing key raises a clear error.
- The summarise and classify calls return real model output.

---

### Task 2 🟡 — Few-shot vs zero-shot

**Goal:** Compare classification accuracy with 0, 1, and 3 examples; print a table.

**Steps:**

1. Open `py/02_few_shot.py` and `ts/02-few-shot.ts`.
2. Define 3 `FEW_SHOT_EXAMPLES` (one per class).
3. Implement `build_zero_shot_messages` and `build_few_shot_messages`.
4. For each test input, run all three variants and print results in a table.
5. Observe: do the labels improve? Does the model follow the format more strictly?

**Acceptance:**

- The table prints with 0-shot, 1-shot, and 3-shot results for each input.
- You can articulate why (or why not) few-shot helped for this task.

---

### Task 3 🟡 — Chain-of-thought & self-consistency

**Goal:** Implement CoT prompting and self-consistency voting on math/logic problems.

**Steps:**

1. Open `py/03_cot.py` and `ts/03-cot.ts`.
2. Implement `build_direct_prompt` (answer only, no reasoning).
3. Implement `build_cot_prompt` (think step by step, then "Final answer: X").
4. Implement `extract_final_answer` to parse the answer from the CoT response.
5. Implement `majority_vote(answers: list[str])`.
6. For each problem: run direct, single CoT, and self-consistency (N=3). Print results.

**Acceptance:**

- CoT responses contain visible reasoning steps.
- `extract_final_answer` correctly extracts the answer from the CoT text.
- `majority_vote` returns the most common answer from N samples.

---

### Task 4 🟢 — Output parsing & guardrails

**Goal:** Implement the repair loop for constrained output.

**Steps:**

1. Open `py/04_guardrails.py` and `ts/04-guardrails.ts`.
2. Implement `parse_label` / `parseLabel` — normalise and validate against VALID_LABELS.
3. Implement `classify_with_guardrails`:
   - Call `llm.chat(messages)`.
   - Try `parse_label`. On failure: append the bad response + correction message and retry.
   - After `max_retries` failures, raise.
4. Run on the demo inputs. Observe when the model misbehaves and whether the repair works.

**Acceptance:**

- On a bad output the retry loop fires (you see the "Attempt N: parse failed" log).
- After correction the model usually returns a valid label.
- The function raises cleanly after 3 failures.

---

### Task 5 🟡 — Prompt eval harness

**Goal:** Evaluate two prompt variants on `eval_dataset.json` and compare accuracy.

**Dataset:** `eval_dataset.json` — 10 labelled sentiment examples (positive/negative/neutral).

**Steps:**

1. Open `py/05_eval_harness.py` and `ts/05-eval-harness.ts`.
2. Define `variant_b_messages` / `VARIANTS[1].buildPrompt` — a different instruction style.
3. Implement `parse_output` — normalise the model's label to a clean string.
4. Implement `eval_variant` — run the variant on all 10 examples, score each, return results.
5. Call `print_results` to print the per-sample table and summary.
6. Compare variants. Which scores higher? Does the result match your hypothesis?

**Acceptance:**

- Both variants run on all 10 examples.
- The comparison table shows accuracy per variant.
- You can explain (one sentence) why the higher-scoring variant works better.

---

## Done when

- [ ] `render_template` raises a clear error on missing keys and substitutes correctly.
- [ ] You can compare two prompt variants on `eval_dataset.json` and pick the winner with numbers.

---

## Going deeper

- [Prompt Engineering Guide](https://www.promptingguide.ai/) — comprehensive reference
- [Chain-of-Thought Prompting (Wei et al. 2022)](https://arxiv.org/abs/2201.11903) — original CoT paper
- [Self-Consistency (Wang et al. 2022)](https://arxiv.org/abs/2203.11171) — majority-vote sampling
- [Large Language Models are Zero-Shot Reasoners (Kojima et al. 2022)](https://arxiv.org/abs/2205.11916) — "Let's think step by step"
- [HELM](https://crfm.stanford.edu/helm/latest/) — what large-scale prompt evaluation looks like
- Anthropic's [prompt engineering docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
