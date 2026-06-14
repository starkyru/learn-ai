# Module 13 — Fine-Tuning

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

Fine-tuning is what you do when prompting and RAG are not enough. This module
teaches you WHEN that moment actually arrives, how to do it cheaply (LoRA), and
what can go wrong (overfitting). By the end you will have prepared a real JSONL
training dataset, launched a hosted fine-tune via the OpenAI API, and implemented
the LoRA low-rank update by hand so the math is no longer magic.

---

## Concepts

### Prompt vs RAG vs fine-tune — the decision

Before writing a single line of fine-tuning code you need to ask: **is fine-tuning
actually the right tool?** The three main strategies are:

| Strategy | What it adds | When to reach for it |
| --- | --- | --- |
| **Prompting** | Nothing — uses the base model | New task, few/no examples, labels change often |
| **RAG** | External knowledge at inference time | Need up-to-date or private facts, knowledge is large |
| **Fine-tuning** | Persistent style/behaviour/task adaptation | Consistent tone, private schema, output format lock-in, speed |

The rule of thumb: **start with prompting, add RAG for knowledge, consider fine-tuning
only when you have hundreds of clean examples and a stable task definition that won't
change monthly.** Fine-tuning is expensive to re-do; a bad dataset produces a model
that confidently does the wrong thing.

### Supervised fine-tuning (SFT / instruction tuning)

SFT means taking a pre-trained base model and continuing to train it on
`(prompt, completion)` pairs that demonstrate the behaviour you want. This is
how GPT-3 became ChatGPT (InstructGPT): the base model already "knows" language,
SFT teaches it to follow instructions.

The JSONL format the OpenAI fine-tuning API expects:

```jsonl
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
```

Each line is one training example. The model is trained to predict the `assistant`
turn given the prior turns — the classic next-token prediction objective, just on
your examples instead of the web.

### LoRA — Low-Rank Adaptation

Fine-tuning all billions of parameters is expensive and slow. LoRA (Hu et al., 2021)
is the big idea that made local fine-tuning practical:

**The core insight:** During fine-tuning, the *change* in a weight matrix ΔW tends
to have low intrinsic rank. Instead of updating the full W (shape [d, d]), LoRA
represents the update as a product of two small matrices:

```
ΔW = B · A     where B ∈ ℝ^{d×r}, A ∈ ℝ^{r×d},  r ≪ d
```

Only B and A are trained; W stays frozen. The forward pass becomes:

```
output = W·x + B·A·x = (W + B·A)·x
```

**Parameter count comparison** for a weight matrix of shape [d, d] with rank r:

| Method | Parameters |
| --- | --- |
| Full fine-tune | d² |
| LoRA | 2·d·r |

For d=4096, r=16: full = 16.7M params; LoRA = 131K params — **127× fewer**.

**QLoRA** (Dettmers et al., 2023) adds quantization on top: the frozen base model
weights are stored in 4-bit precision to fit on a consumer GPU, while the LoRA
adapters train in bfloat16. This makes fine-tuning a 7B-parameter model possible
on a 16 GB GPU.

### Dataset quality and overfitting

The most common fine-tuning mistake is bad data quality:

- **Too few examples** (< 50–100): the model memorises examples and fails to generalise.
- **Inconsistent format**: if your assistant turns sometimes end with a period and
  sometimes don't, the model learns noise.
- **Label leakage**: if your eval set contains near-duplicates of your training set,
  your eval metrics are too optimistic.

Signs of overfitting: training loss keeps falling but validation loss stops falling
(or rises). The fix: more diverse data, or stop training earlier.

---

## Tasks

### Task 1 🟢 — Decide: prompt vs fine-tune

**Goal:** Build intuition for when fine-tuning pays off by running a narrow task
through a prompt-only baseline and a mock fine-tuned baseline, then comparing.

**Files:**
- `py/01_decide.py`
- `ts/01-decide.ts`

**Steps:**

1. Implement `prompt_baseline()` / `promptBaseline()` — call the LLM with a
   system prompt tailored to the narrow task (formal email rewriting).

2. Implement `mock_finetuned()` / `mockFineTuned()` — simulate what a fine-tuned
   model does with a few-shot prompt: 5 (input, output) examples embedded directly.
   This approximates fine-tuning without training.

3. Implement `score_formality()` / `scoreFormality()` — ask the LLM itself to rate
   the formality of an output on a 1–5 scale and parse the integer.

4. Run both approaches on 5 test inputs; print a comparison table.

5. Discuss in comments: would a real fine-tuned model do better than few-shot? When?

**Acceptance:**
- Both approaches run without error.
- A comparison table prints with formality scores for each input.
- Code comments explain the decision logic.

---

### Task 2 🟢 — Hosted SFT via OpenAI fine-tuning API

**Goal:** Prepare a real JSONL training file, submit it to OpenAI's fine-tuning
API, then call the resulting model and compare it to the base model.

**Files:**
- `py/02_hosted_sft.py`
- `ts/02-hosted-sft.ts`

**Requires:** `OPENAI_API_KEY` in `.env`. This costs real money (typically $0.008/1K
tokens to train on gpt-4o-mini). The dataset in this task is tiny (~30 examples)
so the cost is under $0.50. Check current pricing at
https://platform.openai.com/docs/guides/fine-tuning before running.

**Steps:**

1. Implement `build_dataset()` / `buildDataset()` — create 30 training examples
   for a "formal email rewriter" task. Each example is a
   `{"messages": [...]}` dict. Write the result to `data/emails_train.jsonl`.

2. Implement `upload_and_finetune()` / `uploadAndFinetune()` — use the `openai` SDK
   directly (not llm-core) to:
   a. Upload the JSONL file via `client.files.create(purpose="fine-tune")`.
   b. Start a fine-tune job via `client.fine_tuning.jobs.create(...)`.
   c. Return the job id.

3. Implement `wait_for_job()` / `waitForJob()` — poll every 30 seconds until the
   job status is `"succeeded"` or `"failed"`. Print progress events.

4. Implement `compare_models()` / `compareModels()` — given the fine-tuned model id,
   call both `gpt-4o-mini` and the fine-tuned model on 3 test inputs and print
   side-by-side responses.

**Note on the TS mirror:** The `openai` npm package is installed. Use it directly —
`import OpenAI from "openai"`.

**Acceptance:**
- `build_dataset()` writes a valid JSONL file with 30 examples.
- The upload + fine-tune submission works (even if you cancel the job to save cost).
- Comparison table prints for at least 3 test inputs.

---

### Task 3 🟡 — LoRA / QLoRA locally (Python only)

**Goal:** Fine-tune a small model locally using PEFT + transformers. Understand the
mechanics of LoRA from the outside: which layers get adapters, how rank affects
parameter count.

**File:** `py/03_lora_local.py`

**Optional extra — requires:**
```bash
uv sync --extra finetune
```
This installs: `transformers`, `peft`, `datasets`, `accelerate`, `torch`.

**WARNING:** This task downloads model weights:
- `facebook/opt-125m` — ~250 MB (used in the stub)
- If you want to try a more capable model, `meta-llama/Llama-3.2-1B` needs ~2.5 GB
  and a HuggingFace account (`HF_TOKEN` in `.env`).

**Steps:**

1. Implement `load_model_and_tokenizer()` — load `facebook/opt-125m` with
   `transformers.AutoModelForCausalLM` and its tokenizer.

2. Implement `add_lora_adapters()` — use `peft.LoraConfig` and `peft.get_peft_model()`
   to wrap the model. Print trainable vs total parameter counts.

3. Implement `tokenize_dataset()` — tokenize a small list of `(prompt, completion)`
   pairs into the `input_ids`/`labels` format the trainer expects.

4. Implement `train()` — use `transformers.Trainer` with a small number of steps
   (5 for the stub, enough to see loss drop) and print the final loss.

5. Implement `compare_outputs()` — generate from the base model and the LoRA-adapted
   model on one test prompt; print both.

**TS note:** LoRA training is Python/CUDA territory. The TypeScript mirror is Task 2
(hosted SFT via the OpenAI API) — that's the practical equivalent for JS/TS engineers.

**Acceptance:**
- The script runs end-to-end with the `--extra finetune` deps.
- Trainable parameter count is much smaller than total (should be < 1%).
- Loss decreases over training steps.

---

### Task 4 🟡 — Dataset prep and overfitting eval

**Goal:** Format and clean a dataset, split into train/val/test, fine-tune (or
mock-fine-tune), and watch for overfitting by tracking val loss separately from
train loss.

**Files:**
- `py/04_dataset_eval.py`
- `ts/04-dataset-eval.ts`

**Steps:**

1. Implement `clean_example()` / `cleanExample()` — normalise whitespace, strip
   HTML tags, truncate to max 512 chars, enforce a consistent `assistant` turn
   format.

2. Implement `split_dataset()` / `splitDataset()` — shuffle (seed=42) and split
   into 70% train / 15% val / 15% test. Return three lists.

3. Implement `eval_on_split()` / `evalOnSplit()` — for each item in a split, run
   the LLM on the prompt and ask a judge LLM to score correctness (1–5). Return
   mean score.

4. Implement `overfitting_check()` / `overfittingCheck()` — given a series of
   (train_score, val_score) measurements over epochs, print a table and flag if
   val score stops improving while train score keeps rising.

5. Run on the email dataset from Task 2.

**Acceptance:**
- `clean_example()` handles None, HTML, and whitespace correctly.
- `split_dataset()` produces non-overlapping splits summing to 100%.
- A table of train vs val scores prints with a clear overfitting signal (even if mocked).

---

### Task 5 🔴 — Understand LoRA: implement the low-rank update

**Goal:** Implement the LoRA idea — represent ΔW as B·A — from scratch using only
numpy (Python) or plain arrays (TypeScript). No ML frameworks. Count how many
parameters you save and verify the forward pass numerically.

**Files:**
- `py/05_lora_scratch.py`
- `ts/05-lora-scratch.ts`

**The harness is runnable. You implement the TODO sections.**

**Steps:**

1. Implement `lora_init()` / `loraInit()` — initialise matrices:
   - `A` : shape [r, d_in] — random normal, small std (e.g. 0.01)
   - `B` : shape [d_out, r] — zeros (standard LoRA init: B=0 so ΔW starts at zero)

2. Implement `lora_forward()` / `loraForward()` — compute the LoRA-adapted output:
   ```
   output = W @ x + (B @ A) @ x    # or equivalently (W + B@A) @ x
   ```

3. Implement `count_params()` / `countParams()` — return
   `{"full": d_in * d_out, "lora": r * (d_in + d_out)}`.

4. Implement `verify_equivalence()` / `verifyEquivalence()` — check numerically that
   `(W + B@A) @ x` equals `W @ x + B @ (A @ x)` to within 1e-9.

5. Implement `param_savings_table()` / `paramSavingsTable()` — print a table showing
   full vs LoRA param counts and savings ratio for d=512/1024/4096, r=4/8/16/64.

**Acceptance:**
- The equivalence check passes (numpy `allclose` or a manual absolute-diff check).
- The param table prints and shows the right counts.
- No ML framework imports (numpy/plain arrays only).
- B@A output is exactly zero on a freshly initialised LoRA (because B=0).

---

### Task 6 🟡 — Distillation: teacher labels a dataset, student learns from it

**Goal:** Use a big LLM (the "teacher") to label a small dataset, train a
cheap embedding-based classifier (the "student") on those labels, then compare
the student's accuracy, latency, and cost-per-query against calling the teacher
on every request.

**Files:**
- `py/06_distillation.py`
- `ts/06-distillation.ts`

**Steps:**
1. Implement `llm_label()` / `llmLabel()` — call the teacher LLM with
   `max_tokens=5, temperature=0` to label each text as `positive`, `negative`,
   or `neutral`. Parse the response; default to `neutral` on unexpected output.
2. Implement `train_student()` / `trainStudent()` — embed all teacher-labelled
   examples in one `provider.embed()` call; store embeddings + labels in a
   `StudentClassifier`.
3. Implement `student_predict()` / `studentPredict()` — kNN over cosine
   similarities: find top-k nearest training embeddings, return the majority label.
4. Implement `evaluate()` / `evaluate()` — time both the student and teacher on
   the hold-out test set; compute accuracy and per-query latency for each.
5. Run the harness and compare the printed table: student vs teacher accuracy
   and latency. Discuss in comments when this tradeoff makes sense.

**Acceptance:**
- `llm_label()` returns one label per text; all labels are in `["positive", "negative", "neutral"]`.
- `train_student()` produces a `StudentClassifier` with one embedding per labelled example.
- `student_predict()` returns a valid label for every test input.
- `evaluate()` prints a table with accuracy and per-query latency for both models.
- Student latency is measurably lower than teacher latency.

---

## Done when

- [ ] `01_decide` / `01-decide` runs and prints a comparison table.
- [ ] `02_hosted_sft` / `02-hosted-sft` writes a valid JSONL file and (optionally)
      launches a real fine-tune job.
- [ ] `03_lora_local` runs with `--extra finetune` and shows trainable param count
      much smaller than total.
- [ ] `04_dataset_eval` / `04-dataset-eval` splits a dataset, evaluates on val,
      and flags overfitting.
- [ ] `05_lora_scratch` / `05-lora-scratch` passes the equivalence check and prints
      a param savings table with correct numbers.
- [ ] `06_distillation` / `06-distillation` prints a student vs teacher comparison
      table with accuracy and latency columns.
- [ ] You can answer: when would you fine-tune instead of prompting? What is rank r?
- [ ] You can answer: when does distillation make sense vs always calling the teacher?

---

## Going deeper

- [LoRA paper (Hu et al., 2021)](https://arxiv.org/abs/2106.09685) — the original,
  surprisingly readable.
- [QLoRA paper (Dettmers et al., 2023)](https://arxiv.org/abs/2305.14314) — how to
  fine-tune a 65B model on one GPU.
- [OpenAI fine-tuning guide](https://platform.openai.com/docs/guides/fine-tuning) —
  practical walkthrough for hosted SFT.
- [HuggingFace PEFT docs](https://huggingface.co/docs/peft/index) — the library
  behind Task 3.
- [Karpathy — "Let's build GPT from scratch"](https://youtu.be/kCc8FmEb1nY) — watch
  before Task 5 if the attention math is fuzzy.
- [Axolotl](https://github.com/OpenAccess-AI-Collective/axolotl) — production LoRA
  fine-tuning toolkit if you want to go beyond the stub.

---

## Environment variables

```bash
# Required for Task 2 (hosted SFT):
OPENAI_API_KEY=sk-...

# Optional for Task 3 (gated HuggingFace models):
HF_TOKEN=hf_...
```

## Python extras

```bash
# Task 3 only — heavy, optional, Mac-compatible:
uv sync --extra finetune
# Installs: torch, transformers, peft, datasets, accelerate
# Expect ~3-5 GB of downloads on first run.
```
