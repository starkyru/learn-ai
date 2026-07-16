# Curriculum — learn-ai

A detailed study plan for the full course. The module READMEs are the primary
source of truth for tasks and acceptance criteria; this document is the map.

---

## How to use this course

1. Read the module README before writing any code. It explains the _why_.
2. Do the 🟢 app task first. Get something working. Then come back for 🟡/🔴.
3. Run against two providers and notice what changes. The provider abstraction
   is a deliberate teaching tool — understand where it holds and where it leaks.
4. Use the `/tutor` CLI at any point to ask questions or run a graded exam on
   the module you just finished (see the Applied Projects section below).
5. Treat the "Done when" checklist as your definition of done — not the last
   line of code you write.

### Depth legend

| Tag         | What it means                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------------------ |
| 🟢 App      | Use the ecosystem to build something that works. Every module has at least one.                        |
| 🟡 Balanced | Build the app AND implement one core piece by hand for intuition.                                      |
| 🔴 Deep     | Implement the machinery from scratch — no obvious library allowed. Where the real understanding lives. |

### Running exercises

```bash
# Python (from repo root)
uv run python modules/NN-name/py/script.py

# TypeScript (from repo root)
pnpm tsx modules/NN-name/ts/script.ts
```

---

## Module 00 — Setup & Providers

**Prerequisites:** git, Node.js ≥ 20, Python ≥ 3.11, uv, pnpm. At least one
provider key or a local Ollama install.

**Learning objectives**

- Understand what an LLM provider is and what the three core operations
  (`chat`, `chat_stream`, `embed`) look like over HTTP.
- Understand why the OpenAI `/v1/chat/completions` shape became a de-facto
  standard (OpenAI, Ollama, NVIDIA, LM Studio, and Gemini all speak it), and why
  Anthropic needs its own adapter.
- Run a prompt against two different providers using the shared `get_provider()`
  abstraction.
- Watch streaming tokens arrive and understand time-to-first-token (TTFT).

**Tasks**

| #   | Task              | Depth | What you do                                                                                                      |
| --- | ----------------- | ----- | ---------------------------------------------------------------------------------------------------------------- |
| 1   | Hello, LLM        | 🟢    | Run `hello.py` / `hello.ts` against two providers; see answer, model id, and token count.                        |
| 2   | Compare providers | 🟢    | Run `compare_providers` to send the same prompt to all six providers simultaneously; skips missing ones cleanly. |
| 3   | Streaming         | 🟢    | Watch `streaming.py` / `streaming.ts` emit tokens progressively via `chat_stream()`.                             |

**Estimated time:** 1–2 hours

**Done when**

- [ ] `hello` ran against at least two providers; you saw answer + model + tokens.
- [ ] `compare_providers` runs cleanly even with some providers missing.
- [ ] `streaming` printed tokens incrementally.
- [ ] You can explain why one `OpenAICompatibleProvider` covers five vendors (OpenAI, Ollama, NVIDIA, LM Studio, Gemini) and only Anthropic needs its own.

---

## Module 01 — LLM Fundamentals

**Prerequisites:** Module 00 working, NumPy (`uv sync`).

**Learning objectives**

- Build a BPE tokenizer from scratch and understand the sub-word tradeoff.
- Implement cosine similarity and see why it measures semantic closeness.
- Implement scaled dot-product attention (`softmax(QKᵀ/√dₖ)V`) and verify
  that weights sum to 1.
- Implement greedy, temperature, top-k, and top-p sampling from a logit vector.
- Understand a language model as a next-token predictor by building a bigram model.

**Tasks**

| #   | Task              | Depth | What you do                                                                                                |
| --- | ----------------- | ----- | ---------------------------------------------------------------------------------------------------------- |
| 1   | BPE tokenizer     | 🔴    | Implement BPE train + encode + decode; `decode(encode(s)) == s` must hold. (Worked example to study.)      |
| 2   | Cosine similarity | 🟡    | Implement cosine by hand and rank real embeddings from `provider.embed()`; similar sentences score higher. |
| 3   | Attention head    | 🔴    | Fill in `softmax(QKᵀ/√dₖ)V` in `attention.py` / `attention.ts`; weight rows must sum to 1.                 |
| 4   | Samplers          | 🔴    | Implement greedy, temperature, top-k, top-p in `sampling.py` / `sampling.ts`.                              |
| 5   | Bigram model      | 🟡    | Build a count-based bigram predictor; observe that it is a (bad) language model.                           |

**Estimated time:** 4–6 hours (budget more if 🔴 tasks are new to you)

**Done when**

- [ ] `decode(encode(s)) == s` passes in Python and TypeScript.
- [ ] Cosine ranking puts same-topic sentences above unrelated ones.
- [ ] Attention weights' rows each sum to 1.
- [ ] Greedy/temperature/top-k/top-p behave as described.
- [ ] You can explain in one sentence each: token, embedding, attention, sampling.
- [ ] `pytest test_fundamentals.py` and `jest bpe.test.ts` pass.

---

## Module 01b — Classic ML Foundations

**Prerequisites:** Module 01. NumPy (a base dependency — no extra needed). Pure
numpy (Python) / plain TypeScript, fully offline, deterministic — no provider,
no network, no LLM.

**Why:** The course jumps almost straight to LLMs, but every AI interview and a
lot of real debugging still leans on the classic-ML theory underneath. This
companion fills that gap without duplicating Module 08 (softmax, cross-entropy,
F1, confusion matrix); it focuses on regression, bias–variance & cross-validation,
regularisation, ROC/AUC, and k-means.

**Learning objectives**

- Fit linear regression two ways — the normal equation and gradient descent —
  and confirm they converge to the same weights.
- Reproduce the bias–variance U-curve, estimate test error with k-fold
  cross-validation, and tame overfitting with ridge (L2) regularisation.
- Train logistic regression with gradient descent and watch L2 shrink the weight norm.
- Build ROC/AUC ranking metrics and k-means clustering from scratch.

**Tasks**

| #   | Task                                   | Depth | What you do                                                                                                        |
| --- | -------------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | Linear regression (normal eq + GD)     | 🟡    | Implement `normal_equation` (solve, never invert), `predict`, `mse_loss`, `gradient_step`; GD matches closed form. |
| 2   | Bias–variance, cross-validation, ridge | 🔴    | Implement `kfold_indices`, `ridge_fit` (don't regularise the intercept), `cv_score`; find the CV-optimal degree.   |
| 3   | Logistic regression + L2               | 🟡    | Implement `sigmoid`, `bce_loss`, `predict_proba`, `gradient_step` with a bias-exempt L2 term.                      |
| 4   | ROC/AUC + k-means                      | 🟢    | Implement `roc_curve`, `auc` (trapezoid), and k-means `assign`/`update`/`inertia` from scratch.                    |

**Estimated time:** 4–6 hours

**Done when**

- [ ] Task 1: normal-equation and GD weights match, MSE is monotone, `R² > 0.9`.
- [ ] Task 2: CV-optimal degree is in [2, 6]; degree-12 shows the train ≪ CV gap; ridge lowers both `||w||` and CV MSE.
- [ ] Task 3: ≥ 95% train accuracy with monotone BCE loss; larger `λ` gives a smaller `||w||`.
- [ ] Task 4: AUC = 1.0 / 0.0 / ≈0.5 for perfect / reversed / random rankers; k-means recovers 3 distinct clusters with non-increasing inertia.

---

## Module 01c — Deep Learning Essentials

**Prerequisites:** Module 01 (and Module 01b helps). NumPy (a base dependency).
Pure numpy (Python) / plain arrays (TypeScript), offline, seeded and deterministic
— no ML framework, no network, no LLM.

**Why:** Modern LLM work sits on a stack of ideas that predate transformers:
backprop, optimizers, initialisation, regularisation, and the recurrent network.
This companion makes each concrete. It deliberately does not re-teach 2-D
convolution (module 09), a single attention head (module 01), or plain
softmax/GD (module 08).

**Learning objectives**

- Build a scalar autograd engine (micrograd-style) and train an MLP by
  backprop, verified against finite differences.
- Implement SGD / Momentum / Adam and He / Xavier init; demonstrate why ReLU
  beats sigmoid on vanishing gradients.
- Implement inverted dropout, batchnorm-forward, and the L2 gradient term, and
  show they close the generalisation gap.
- Implement a vanilla RNN cell and backprop-through-time (BPTT) on a char-level task.

**Tasks**

| #   | Task                  | Depth | What you do                                                                                                        |
| --- | --------------------- | ----- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | Autograd engine + MLP | 🔴    | Implement the `Value` op backward closures, reverse-topological `backward()`, and the SGD update; train XOR.       |
| 2   | Optimizers + init     | 🟡    | Implement `sgd`/`momentum`/`adam` updates and `he_init`/`xavier_init`; race them and run the vanishing-grad demo.  |
| 3   | Regularisation        | 🟡    | Implement `dropout_forward`, `batchnorm_forward`, and `l2_grad`; shrink the (train − test) accuracy gap.           |
| 4   | Vanilla RNN + BPTT    | 🔴    | Implement `rnn_step`, `forward` (unroll + store), and the BPTT `backward` (tanh grad + through-time accumulation). |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Task 1: XOR trains to loss < 0.05 with all 4 signs correct; `grad_check` matches within 1e-4.
- [ ] Task 2: Adam reaches the target loss in fewer epochs than SGD; ReLU first-layer grad norm > 5× sigmoid's.
- [ ] Task 3: batchnorm output has per-feature mean ≈ 0 / var ≈ 1; dropout + L2 give a smaller generalisation gap.
- [ ] Task 4: cross-entropy loss drops substantially and next-char accuracy ≥ 0.90 on the repeating pattern.

---

## Module 01d — Transformer Architecture

**Prerequisites:** Module 01 (the toy attention head) and Module 01c help.
NumPy (a base dependency). Pure numpy (Python) / plain arrays (TypeScript),
offline and deterministic — no provider, no network, no ML framework.

**Why:** Module 01 gave you a single toy attention head; this companion builds
the whole GPT-style decoder — multi-head self-attention with causal masking,
sinusoidal positional encoding, a pre-LN block, and the KV cache — then contrasts
it with the encoder-only (BERT) family and closes with interview notes on the
modern stack (RoPE, GQA/MQA, FlashAttention, MoE, scaling laws). This is the
course's most-asked interview material.

**Learning objectives**

- Implement scaled dot-product attention, a causal mask, and multi-head attention from scratch.
- Build the sinusoidal positional-encoding table and demonstrate why order matters.
- Assemble LayerNorm, GELU, an FFN, and residuals into a pre-LN decoder block and stack N of them.
- Implement incremental decoding with a KV cache and prove it equals the naive recompute.
- Contrast encoder-only (BERT, masked-LM) with decoder-only (GPT, next-token): same
  blocks, different mask + objective — and show only the bidirectional model can
  use right-context to recover a masked token.

**Tasks**

| #   | Task                                  | Depth | What you do                                                                                                                                                                                                 |
| --- | ------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Multi-head attention + causal masking | 🔴    | Implement `scaled_dot_product_attention` (stable softmax), `causal_mask`, and `multi_head_attention`.                                                                                                       |
| 2   | Sinusoidal positional encoding        | 🟡    | Implement `sinusoidal_encoding`; study the permutation-equivariance and locality checks the harness runs.                                                                                                   |
| 3   | Pre-LN decoder block                  | 🔴    | Implement `layer_norm`, `gelu`, `ffn`, and the pre-LN residual `TransformerBlock.forward`; stack N = 3.                                                                                                     |
| 4   | KV cache                              | 🟡    | Implement `decode_with_cache` (one key projection per step) and match the provided naive recompute.                                                                                                         |
| 5   | Encoder vs decoder (BERT vs GPT)      | 🟡    | Implement `full_attention` (no mask), `causal_attention`, `attention_mass_on_future`, and cosine-argmax `nearest_token`; only the bidirectional model recovers a masked token whose clue sits to its right. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Task 1: weight rows sum to 1, the causal mask zeroes future positions, and `h=1` MHA matches single-head SDPA.
- [ ] Task 2: PE shape/range correct; permutation-equivariance passes without PE and fails with PE; adjacent PE dot-product exceeds the endpoint pair.
- [ ] Task 3: LayerNorm rows have mean ≈ 0 / var ≈ 1; one block preserves shape; a 3-block stack produces finite output.
- [ ] Task 4: cached logits equal naive logits at every step; key-projection counts are `n` (cached) vs `n(n+1)/2` (naive).
- [ ] Task 5: causal future-attention mass is exactly 0 vs > 0.2 bidirectional; the bidirectional model recovers ≥ 4/5 masked tokens, the causal model strictly fewer.
- [ ] You can answer in one breath: "BERT vs GPT — what's actually different?" (mask + objective; the blocks are the same).

---

## Module 01e — Trees & Ensembles

**Prerequisites:** Module 01b. NumPy (a base dependency — no extra needed).
Pure numpy (Python) / plain TypeScript, fully offline, deterministic (fixed
seeds, synthetic data) — no provider, no network, no LLM. **No sklearn / no
xgboost** — that constraint is the point.

**Why:** The course covers linear models (01b) and deep nets (01c) but nothing
tree-based — and decision trees / random forests / gradient boosting are the
#1 classic-ML interview family and the default baseline for tabular data. This
companion builds CART, bagging, a random forest, and least-squares gradient
boosting from scratch, then measures the bias–variance decomposition that
explains why ensembles work.

**Learning objectives**

- Implement CART from scratch — Gini impurity, exhaustive midpoint split
  search, recursive growth, prediction — and show depth controlling the
  train−test overfitting gap.
- Implement bootstrap sampling (≈ 63.2% unique rows), bagging, and the
  random-forest feature-subsampling trick, and show the decorrelated ensemble
  beating both its average member and a single deep tree.
- Implement least-squares gradient boosting with regression stumps — knowing
  that the residual IS the negative gradient (gradient descent in function
  space) — with monotone train MSE, a validation U-curve, and early stopping.
- Compute the empirical bias–variance decomposition from an (M × N_test)
  prediction matrix and verify bias² + variance ≈ expected MSE − σ² for a
  stump, a deep tree, and bagged deep trees.

**Tasks**

| #   | Task                                  | Depth | What you do                                                                                                                         |
| --- | ------------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Decision tree (CART) from scratch     | 🔴    | Implement `gini`, `best_split` (every feature, every midpoint), recursive `build_tree`, `predict_one`; deep vs depth-3 overfit gap. |
| 2   | Bagging → random forest               | 🟡    | Implement `bootstrap_sample`, `train_forest` (bootstrap + per-split feature subset via the provided trainer), `forest_predict`.     |
| 3   | Gradient boosting with stumps         | 🔴    | Implement `fit_stump` (best two-leaf SSE split) and `boost` (residuals = negative gradient, lr·stump updates, early-stop pick).     |
| 4   | Empirical bias–variance decomposition | 🟢    | Implement `empirical_bias_variance` (bias² and variance from an M × N_test prediction matrix); stump vs deep vs bagged table.       |

**Estimated time:** 4–6 hours

**Done when**

- [ ] Task 1: gini(pure) = 0.0 and gini(50/50) = 0.5; unlimited tree hits train acc ≥ 0.99 with a train−test gap ≥ 0.10; the depth-3 tree has a smaller gap and test acc ≥ 0.80.
- [ ] Task 2: every bootstrap has duplicate indices with unique fraction ≈ 0.632; ensemble test accuracy ≥ mean individual tree and ≥ the single deep-tree baseline.
- [ ] Task 3: train MSE non-increasing; validation MSE bottoms out strictly before the last round (U-curve); boosted val MSE < 0.5 × the single-stump baseline.
- [ ] Task 4: stump highest bias², deep tree highest variance, bagging cuts deep-tree variance by > 40%; bias² + variance matches expected MSE − σ² within ± 0.03 for all three models.

---

## Module 01f — Probability, Statistics & PCA

**Prerequisites:** Module 01 (Module 01b helps). NumPy (a base dependency — no
extra needed). Pure numpy (Python) / plain TypeScript, fully offline,
deterministic (fixed seeds, synthetic data) — no provider, no network, no LLM.

**Why:** ML-engineer and data-science interviews lean on probability and
statistics the course never covers — Bayes' theorem (and the base-rate trap),
maximum likelihood (and why cross-entropy IS maximum likelihood), hypothesis
testing / A/B tests, and PCA for dimensionality reduction. This companion fills
that gap without duplicating Module 01b (ROC/AUC, k-means) or Module 08
(precision/recall/F1).

**Learning objectives**

- Apply Bayes' theorem to the classic medical-test question (posterior ≈ 0.16,
  not 95%) and scale the same rule into a Laplace-smoothed naive Bayes spam
  classifier working in log space.
- Compute closed-form MLEs for Gaussian and Bernoulli data, verify them by
  grid-searching the NLLs, and show minimising MSE ≡ Gaussian MLE and
  minimising binary cross-entropy ≡ Bernoulli MLE.
- Build the two-proportion z-test and CI for an A/B test, then simulate the
  Type I error rate (≈ α), empirical power, and the multiple-testing trap.
- Implement PCA from scratch (center → covariance → eigendecomposition → sort
  → project → reconstruct) and recover the 2-D plane hiding in 10-D data.

**Tasks**

| #   | Task                         | Depth | What you do                                                                                                                             |
| --- | ---------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Bayes' theorem + naive Bayes | 🟡    | Implement `bayes_posterior` (the base-rate trap), `fit_naive_bayes` (Laplace-smoothed log-likelihoods), `predict_log_posterior`.        |
| 2   | MLE & the loss connection    | 🟡    | Implement `gaussian_mle`, `bernoulli_mle`, `nll_gaussian`, `nll_bernoulli`; grid searches show MSE ≡ Gaussian NLL, BCE ≡ Bernoulli NLL. |
| 3   | Hypothesis testing & A/B     | 🟢    | Implement `normal_cdf`, `two_proportion_ztest` (pooled SE), `confidence_interval_diff`; simulate α, power, and multiple testing.        |
| 4   | PCA from scratch             | 🔴    | Implement `center`, `covariance_matrix`, `pca_fit` (sort eigenpairs descending), `project`, `reconstruct`, `explained_variance_ratio`.  |

**Estimated time:** 4–6 hours

**Done when**

- [ ] Task 1: medical-test posterior within ±0.005 of ≈ 0.161; held-out spam/ham accuracy ≥ 0.9; obvious spam doc gets P(spam) > 0.9.
- [ ] Task 2: NLL grid argmins land within one grid step of the closed-form MLEs; MSE argmin == Gaussian-NLL argmin; BCE argmin == Bernoulli-NLL argmin.
- [ ] Task 3: worked A/B example gives p < 0.05 with a CI excluding 0; A/A false-positive rate ≈ 0.05 (±0.02); power reported; the 20-metric A/A demo finds ≥ 1 spurious hit.
- [ ] Task 4: components orthonormal; top-2 explained variance ≥ 0.9; reconstruction MSE strictly decreases k = 1 → 2 → 5; k = 10 recovers X.

---

## Module 02 — LLM Integration

**Prerequisites:** Module 00. Pydantic (Python base deps), Zod (in ts/package.json).

**Learning objectives**

- Build a multi-turn chat loop that preserves conversation history.
- Implement streaming output and measure TTFT vs. total generation time.
- Count tokens with tiktoken and estimate API cost accurately.
- Extract typed, validated structured data (Pydantic / Zod) from free-form LLM output.
- Implement the manual tool-calling loop for both OpenAI-style and Anthropic-style APIs.
- Implement exponential-backoff retry logic that distinguishes retriable from permanent errors.

**Tasks**

| #   | Task                    | Depth | What you do                                                                                        |
| --- | ----------------------- | ----- | -------------------------------------------------------------------------------------------------- |
| 1   | Chat & system prompts   | 🟢    | Build a multi-turn REPL; history grows per turn; model stays in character with your system prompt. |
| 2   | Streaming               | 🟢    | Implement streaming output with TTFT and words/second stats.                                       |
| 3   | Tokens & cost           | 🟡    | Count tokens via tiktoken; build a cost estimator; compare estimate to provider's reported usage.  |
| 4   | Structured output       | 🟢    | Extract a `Recipe` object from free text; validate with Pydantic / Zod; retry on parse failure.    |
| 5   | Tool / function calling | 🟢    | Implement the tool loop directly against the OpenAI and Anthropic SDKs (below llm_core).           |
| 6   | Retries & errors        | 🟡    | Implement exponential backoff with jitter; never retry 401/400 errors.                             |

**Estimated time:** 4–5 hours

**Done when**

- [ ] Multi-turn chat remembers earlier turns; system prompt is respected.
- [ ] `parse_recipe` returns a typed validated object; self-corrects on bad JSON.
- [ ] Tool loop: model calls `get_weather`, you execute it, model uses the result.
- [ ] Both tasks work with at least one provider.

---

## Module 03 — Prompting & Patterns

**Prerequisites:** Modules 00–02.

**Learning objectives**

- Write and evaluate few-shot prompts; measure how example count affects quality.
- Apply chain-of-thought (CoT) prompting to improve multi-step reasoning.
- Implement self-consistency: sample N CoT paths and majority-vote the answer.
- Build a prompt-template helper and output-repair loop.
- Build a systematic prompt evaluator that scores prompt variants against a test set.

**Tasks**

| #   | Task                                | Depth | What you do                                                                                    |
| --- | ----------------------------------- | ----- | ---------------------------------------------------------------------------------------------- |
| 1   | Templates & roles                   | 🟢    | Build a `render_template` helper; summarise and classify with system/user roles.               |
| 2   | Few-shot vs zero-shot               | 🟡    | Compare 0-, 1-, 3-shot on a classification task; print accuracy table.                         |
| 3   | Chain-of-thought & self-consistency | 🟡    | Add CoT to math/logic tasks; sample N paths, majority-vote; compare to single-sample accuracy. |
| 4   | Output parsing & guardrails         | 🟢    | Implement the repair loop: on parse failure append error + correction and retry.               |
| 5   | Prompt eval harness                 | 🟡    | Run two prompt variants on `eval_dataset.json`; print ranked comparison table.                 |

**Estimated time:** 3–4 hours

**Done when**

- [ ] `render_template` raises a clear error on missing keys and substitutes correctly.
- [ ] You can compare two prompt variants on `eval_dataset.json` and pick the winner with numbers.

---

## Module 04 — Embeddings & Vectors

**Prerequisites:** Modules 00–02. `uv sync --extra vectors` (chromadb, sentence-transformers, rank-bm25).

**Learning objectives**

- Implement a brute-force vector store from scratch using cosine similarity.
- Use a production vector database (ChromaDB, optionally Qdrant) with HNSW indexing.
- Understand and implement three chunking strategies; see how chunk size affects retrieval.
- Implement hybrid search: dense + BM25, fused with Reciprocal Rank Fusion (RRF).
- Chunk at semantic breakpoints (embedding-distance percentile) instead of fixed counts.

**Tasks**

| #   | Task                      | Depth | What you do                                                                                                                |
| --- | ------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | Vector store from scratch | 🔴    | Implement `add()`, `_cosine_similarity()`, and `query()` with brute-force top-k.                                           |
| 2   | Real vector DB            | 🟢    | Index the corpus into Chroma; compare results and performance to Task 1.                                                   |
| 3   | Chunking strategies       | 🟡    | Implement fixed-size, sentence-based, and overlapping chunkers; compare retrieval quality per strategy.                    |
| 4   | Hybrid search             | 🟡    | Add BM25 alongside dense retrieval; implement RRF fusion; show hybrid beats either alone on exact-match queries.           |
| 5   | Semantic chunking         | 🟡    | Split at semantic breakpoints: embed sentences, threshold `1−cosine` gaps at a percentile; boundaries follow topic shifts. |

**Estimated time:** 4–6 hours

**Done when**

- [ ] `_cosine_similarity([1,0], [1,0])` returns 1.0; `([1,0], [0,1])` returns 0.0.
- [ ] Chroma indexes 8 documents and returns correct top-3 without errors.
- [ ] Each chunker returns non-empty chunks; overlapping produces at least as many as fixed-size.
- [ ] BM25-only finds exact-match docs that dense retrieval misses; hybrid catches both.
- [ ] Semantic chunker splits a two-topic doc at the topic boundary, not mid-topic.

---

## Module 05 — RAG

**Prerequisites:** Module 04 complete. `uv sync --extra vectors`.

**Learning objectives**

- Build a complete retrieve → rerank → generate pipeline with inline citations.
- Implement LLM reranking and HyDE (Hypothetical Document Embeddings).
- Evaluate RAG quality: faithfulness, context relevance, and answer relevance.
- Understand the failure modes of RAG (retrieval miss, hallucination, citation drift).
- Close the query/answer gap at index time with Reverse HyDE (per-chunk question generation).

**Tasks**

| #   | Task                    | Depth | What you do                                                                                                                 |
| --- | ----------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------- |
| 1   | Naive RAG end-to-end    | 🟢    | retrieve → generate; answer includes `[Source N]` citations.                                                                |
| 2   | Better retrieval        | 🟡    | Add LLM reranking and HyDE; compare retrieval precision before/after.                                                       |
| 3   | RAG eval                | 🟡    | Implement faithfulness, context-relevance, and answer-relevance LLM-as-judge scores over a test set.                        |
| 4   | Citations & attribution | 🟢    | Output structured JSON with per-claim citations; validate and flag invalid or missing citations.                            |
| 5   | Reverse HyDE            | 🟡    | Generate the questions each chunk answers at index time, embed them, retrieve question-to-question — no per-query LLM call. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] End-to-end RAG returns a cited answer for any question over your corpus.
- [ ] Reranking changes which top-3 chunks are used (visible in output).
- [ ] Eval script prints faithfulness / context-relevance / answer-relevance scores without manual input.
- [ ] The HNSW hallucination case scores faithfulness < 1.0 (hallucination detected).
- [ ] Reverse HyDE indexes per-chunk question vectors and retrieves by question-to-question match.

---

## Module 05b — Advanced RAG Architectures

**Prerequisites:** Module 05 (Tasks 1–2). No new deps — `uv sync` is enough; the
graph in Task 4 is hand-rolled. The embedding task (1) needs a provider with
`embed()` (`LLM_PROVIDER=openai`/`ollama`/`nvidia`/`lmstudio`); chat-only tasks
(2–4) run on any provider. Reference: [`docs/ADVANCED_RAG.md`](docs/ADVANCED_RAG.md).

**Estimated time:** 4–6 hours.

**Why:** Module 05 builds _naive_ RAG — an open loop that retrieves once, trusts
the result, and generates. The four architectures here each add the feedback loop
or structure it lacks: fix the chunk before embedding, grade retrieval and
self-correct, gate retrieval adaptively and check groundedness, or swap the flat
vector list for a graph to answer multi-hop questions.

**Learning objectives**

- Explain why a human-readable chunk can be unretrievable, and fix it with
  Contextual Retrieval (embed an augmented chunk, show the original).
- Grade retrieval into Correct/Incorrect/Ambiguous and self-correct (CRAG).
- Gate retrieval per query and critique groundedness with reflection tokens (Self-RAG).
- Build a knowledge graph by hand and answer a multi-hop question by traversal (GraphRAG).

| #   | Task                  | Depth | What you build                                                                                           |
| --- | --------------------- | ----- | -------------------------------------------------------------------------------------------------------- |
| 1   | Contextual Retrieval  | 🟡    | Per-chunk context generation; compare a naive vs contextual index on context-poor queries.               |
| 2   | Corrective RAG (CRAG) | 🟡    | A retrieval evaluator + query rewrite + web-search fallback; route in- vs out-of-corpus queries.         |
| 3   | Self-RAG              | 🟡    | Emulated `Retrieve`/`IsRel`/`IsSup` reflection tokens; adaptive retrieval + support check.               |
| 4   | GraphRAG (multi-hop)  | 🔴    | LLM triple extraction → adjacency-dict graph → BFS subgraph → answer a 2-hop question. No graph library. |

**Done when**

- [ ] Contextual index out-ranks the naive index on a context-poor query (Task 1).
- [ ] An in-corpus query routes to Correct; an out-of-corpus query routes to Incorrect → fallback (Task 2).
- [ ] A closed-book query skips retrieval; a corpus query filters irrelevant passages and reports `IsSup` (Task 3).
- [ ] A 2-hop question is answered from the hand-built graph, printing the connecting path (Task 4).

---

## Module 06 — Agents

**Prerequisites:** Modules 02–05. `uv sync --extra agents` for LangGraph.

**Learning objectives**

- Build a ReAct agent from scratch using only `provider.chat()` and plain text parsing.
- Use native structured tool calling (OpenAI and Anthropic APIs directly).
- Add persistent scratchpad memory that survives restarts.
- Re-implement the same agent with LangGraph's state machine model.
- Build a planner-worker multi-agent architecture.
- Harden the loop with production stop conditions: iteration cap, timeout, a goal predicate distinct from "the model stopped", stuck detection, and idempotent side-effecting tools.

**Tasks**

| #   | Task                    | Depth | What you do                                                                                                                                                                                              |
| --- | ----------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | ReAct loop from scratch | 🔴    | Implement parser, tool dispatch, and the full Thought→Action→Observation loop; works on Ollama.                                                                                                          |
| 2   | Native tool calling     | 🟢    | Re-implement with structured tool schemas; run on OpenAI and Anthropic; compare format differences.                                                                                                      |
| 3   | Memory                  | 🟡    | Add a `scratchpad.json` the agent writes structured notes to; history stays within `MAX_HISTORY_TURNS`.                                                                                                  |
| 4   | LangGraph agent         | 🟢    | Re-build as a typed state machine; map each node back to your from-scratch loop.                                                                                                                         |
| 5   | Multi-agent             | 🟡    | Planner decomposes a question → workers run in parallel → synthesiser combines results.                                                                                                                  |
| 6   | Harden the loop         | 🟡    | Guarded loop: iteration cap, fake-clock timeout, goal predicate ≠ terminal message, stuck detection (repeat + A/B oscillation), idempotency-keyed at-most-once side effects; deterministic via `--stub`. |

**Estimated time:** 7–9 hours

**Done when**

- [ ] From-scratch ReAct solves a multi-step question on Ollama (Task 1).
- [ ] Native tool calling works on OpenAI and Anthropic (Task 2).
- [ ] Scratchpad persists across restarts; history is bounded (Task 3).
- [ ] LangGraph graph produces the same answer as Task 1 (Task 4).
- [ ] Multi-agent: planner JSON → workers → synthesiser (Task 5).
- [ ] Task 6: stuck run exits early with a diagnostic; a clarifying terminal message counts as incomplete, not success; the fake clock trips the timeout; the outbox holds exactly one email despite a retry.

---

## Module 06b — LangGraph deep dive

**Prerequisites:** Module 06 (Tasks 1 and 4). `uv sync --extra agents` (now bundles
langgraph + langchain-core + the ollama/openai/anthropic chat-model adapters + the
sqlite checkpointer). Free path: `ollama pull llama3.2`. TS: `pnpm install`. Switch
provider with `LANGGRAPH_MODEL_PROVIDER`.

**Why:** Module 06 Task 4 is enough to _recognise_ LangGraph; it is not enough to
answer "have you used it in production?" Those interviews are about persistence,
human-in-the-loop, streaming, subgraphs, multi-agent handoff, and time travel.
This module is that depth. Reference: [`docs/LANGGRAPH.md`](docs/LANGGRAPH.md).

**Learning objectives**

- Explain state as channels + reducers and predict how each merges.
- Rebuild the ReAct loop with `ToolNode`/`tools_condition`/`create_react_agent`.
- Add durable memory with a checkpointer + `thread_id`; survive a restart.
- Gate a tool behind a human approval with `interrupt()` / `Command(resume=…)`.
- Stream a graph three ways (updates / values / token-level messages).
- Compose a compiled agent as a subgraph with an isolated private channel.
- Route between specialist workers with `Command(goto=…)` handoff.
- Replay, fork, and edit-then-continue over checkpoints (time travel).

| #   | Task                   | Depth | What you build                                                                               |
| --- | ---------------------- | ----- | -------------------------------------------------------------------------------------------- |
| 1   | State & reducers       | 🟡    | A graph with append / sum / overwrite channels; predict each merge before running.           |
| 2   | Conditional + ToolNode | 🟢    | ReAct built 3 ways: hand-wired router → `tools_condition` → `create_react_agent`, all equal. |
| 3   | Persistence            | 🟡    | Checkpointer + `thread_id`; memory across turns and across a process restart (Sqlite saver). |
| 4   | Human-in-the-loop      | 🔴    | `interrupt()` before a `send_email` tool; approve/deny via `Command(resume=…)`.              |
| 5   | Streaming              | 🟢    | `updates`, `values`, and token-level `messages` streaming from a multi-node graph.           |
| 6   | Subgraphs              | 🟡    | A compiled ReAct agent run as one node in a parent graph; private channel stays isolated.    |
| 7   | Supervisor multi-agent | 🔴    | A supervisor routes between researcher + mathematician via `Command(goto=…)` handoff.        |
| 8   | Time travel            | 🟡    | `get_state_history`, fork from an old checkpoint, `update_state` then continue.              |

**Estimated time:** 5–7 hours

**Done when**

- [ ] You can name each channel's reducer and predict its merge (Task 1).
- [ ] ReAct rebuilt hand-wired, with `tools_condition`, and `create_react_agent` — all equal (Task 2).
- [ ] Same `thread_id` remembers; different doesn't; persistent saver survives restart (Task 3).
- [ ] A tool cannot fire without an explicit `Command(resume="approve")` (Task 4).
- [ ] `updates` / `values` / token-level `messages` streaming all demonstrated (Task 5).
- [ ] A compiled agent runs as a subgraph with an isolated private channel (Task 6).
- [ ] A supervisor routes between two workers via `Command(goto=…)` and ends (Task 7).
- [ ] List checkpoints, fork from an old one, edit-then-continue (Task 8).

---

## Module 06c — Agent Frameworks: LangChain, CrewAI, AutoGen, LlamaIndex, Semantic Kernel

**Prerequisites:** Module 06 (Tasks 1 & 4). No new deps. A chat model is needed
**only** on the non-`--stub` path (`get_provider()` / `getProvider()`, default
`ollama`); every task runs offline via a `--stub` deterministic fake model with
exact assertions. Reference: the module README's "Framework cheat-sheet".

**Why:** Module 06 built an agent loop from scratch and 06b went deep on
LangGraph, but interviews and real teams also ask about LangChain, CrewAI,
AutoGen, LlamaIndex, and Semantic Kernel. Rather than teach five APIs by rote,
you reimplement each framework's core abstraction (~60–100 lines) through a plain
`model(messages) -> text` function, then map each class back to the real
library's API. The lesson: a "framework" is mostly orchestration around one model
call.

**Learning objectives**

- Reimplement LangChain's LCEL (`prompt | model | parser`) as function
  composition over `Runnable`s.
- Reimplement `ConversationBufferMemory` and a bag-of-words cosine retriever, and
  wire them into a tiny RAG chain.
- Reimplement CrewAI's `Agent` / `Task` / `Crew` as a fold that threads context
  through role-grounded model calls.
- Reimplement AutoGen's group chat as a bounded round-robin loop over a shared
  transcript with a termination signal.
- Reimplement LlamaIndex's `VectorStoreIndex` → query engine as
  retrieve-then-synthesize over Nodes (offline bag-of-words cosine).
- Reimplement Semantic Kernel's `Kernel` as a registry of named semantic/native
  functions you invoke by name and chain into a pipeline.

**Tasks**

| #   | Task                                                       | Depth | What you do                                                                                                                       |
| --- | ---------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------- |
| 1   | LCEL runnable (`prompt \| model \| parser`)                | 🟢    | Implement `Runnable.pipe` (flatten sequences), `RunnableSequence.invoke` (fold left), and `PromptTemplate.format`.                |
| 2   | Memory + retriever (a tiny RAG chain)                      | 🟡    | Implement buffer memory, `cosine` over count vectors, top-k `get_relevant`, and the RAG prompt builder.                           |
| 3   | CrewAI crew (roles → tasks → crew)                         | 🟡    | Implement `Agent.execute` (role-grounded prompt) and `Crew.kickoff` (sequential fold threading each output).                      |
| 4   | AutoGen group chat                                         | 🟡    | Implement `ConversableAgent.generate_reply` and the round-robin `GroupChatManager.run` with `max_round`/TERMINATE.                |
| 5   | LlamaIndex query engine (Documents → index → query engine) | 🟡    | Implement `VectorStoreIndex.retrieve` (top-k by cosine over Nodes) and `QueryEngine.query` (retrieve → synthesis prompt → model). |
| 6   | Semantic Kernel (named functions + chaining)               | 🟡    | Implement a `Kernel` that registers a semantic function + a native function, invokes them by name, and chains them sequentially.  |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Task 1: `--stub` chain returns the parsed reply for the formatted prompt, and the 3-step ordering assertions pass.
- [ ] Task 2: retriever returns the right doc, both turns are in memory, and the last prompt contains the retrieved context + prior turn.
- [ ] Task 3: the crew returns the writer's output, and the writer's `context_in` is exactly the researcher's output.
- [ ] Task 4: the transcript is correctly labelled, terminates early on `"TERMINATE"` (3 messages), and never exceeds `max_round`.
- [ ] Task 5: the index chunks 3 documents into 6 nodes, the top node for the Eiffel-Tower query is correct, and the synthesis prompt contains the retrieved node text.
- [ ] Task 6: the kernel invokes a native and a semantic function by name and chains them into a sequential pipeline.
- [ ] You can name the real library API each of your classes maps to.

---

## Module 06d — Agent Memory

**Prerequisites:** Module 06 (Tasks 1 & 3 — the loop and the scratchpad); 06b
(checkpointer) helps but isn't required. No new deps. Everything runs offline
via a `--stub` deterministic fake model with exact assertions; the live path
goes through `get_provider()` / `getProvider()` (default `ollama`).

**Why:** Module 06 gave the agent one memory (a scratchpad) and 06b gave durable
thread persistence — but production agents and interviews distinguish a whole
taxonomy: episodic (conversation history), semantic (knowledge base), procedural
(workflow patterns), entity, and summary memory, plus the discipline of
_managing_ memory (encode → store → retrieve → inject → forget) rather than just
reading it. Memory-augmented (memory happens to the agent) vs memory-aware (the
harness manages its cognitive state) is the framing.

**Learning objectives**

- Run the memory lifecycle: reads before the model call, writes after; keep
  threads isolated and injection bounded.
- Mitigate noisy retrieval with a relevance threshold and stale facts with
  update-on-write upserts.
- Extract and merge entity records; compact old turns into summaries with
  just-in-time expansion (mark, don't delete).
- Compose everything into a `MemoryManager` that holds context under a hard
  token budget across turns and evicts stale records by TTL.

**Tasks**

| #   | Task                                           | Depth | What you do                                                                                                                                                            |
| --- | ---------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Episodic memory + the read/write lifecycle     | 🟢    | Implement `read_episodic` / `write_episodic` / `build_context`: per-thread JSON-file history, reads before the model call, writes after; `last_n` injection bound.     |
| 2   | Semantic memory with a relevance threshold     | 🟡    | Implement `cosine`, thresholded top-k `retrieve`, and `upsert`: threshold 0 lets a near-miss distractor leak, the tuned threshold filters it; upsert never duplicates. |
| 3   | Entity memory + summary memory (JIT expansion) | 🟡    | Implement `extract_entities` (model → JSON, parse + validate), `merge_entities`, `summarise_turns` (mark `archived_by`, don't delete), `expand_summary` (verbatim).    |
| 4   | The MemoryManager: composed lifecycle + TTL    | 🔴    | Implement `assemble_context` (episodic → semantic → entities → summaries under a token budget), `finalize_turn` (write path + compaction), `evict_stale` (fake clock). |

**Estimated time:** 3–5 hours

**Done when**

- [ ] Task 1: isolated threads, preserved order, 4+4 store entries, `last_n` bound respected.
- [ ] Task 2: distractor leaks at threshold 0, is filtered at the tuned threshold; upsert replaces (not duplicates) the changed fact.
- [ ] Task 3: merged entities recalled across a restart; compaction shrinks the context; `expand_summary` recovers the verbatim originals.
- [ ] Task 4: context stays under budget on all 6 turns while the baseline overruns; the stale record is evicted at the right tick; the turn-1 entity is still cited in turn 6.
- [ ] You can explain memory-augmented vs memory-aware, name the five memory types with their lookup mechanisms, and say which operations are programmatic vs agent-triggered.

---

## Module 07 — Advanced & Production

**Prerequisites:** Modules 05–06. `uv sync --extra production`.

**Learning objectives**

- Build an LLM-as-judge eval harness with faithfulness, relevance, and answer-quality metrics.
- Add structured observability: trace every LLM call with latency, tokens, and cost.
- Implement prompt/response caching (exact-hash) to skip redundant LLM calls.
- Add prompt-injection guardrails and PII scrubbing to a system prompt.
- Serve an agent behind a production-ready API endpoint with synchronous and streaming paths.

**Tasks**

| #   | Task                         | Depth | What you do                                                                                                                                                        |
| --- | ---------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | LLM-as-judge eval            | 🟡    | Write a judge prompt; score responses for faithfulness and relevance; calibrate against human labels.                                                              |
| 2   | Observability / tracing      | 🟢    | Wrap every LLM call to log model, tokens, latency, and cost to JSONL; display a per-request cost breakdown.                                                        |
| 3   | Caching & cost control       | 🟡    | Cache responses by SHA-256 hash; hit the cache on repeated queries; print actual vs. saved cost.                                                                   |
| 4   | Guardrails & safety          | 🟢    | Add prompt-injection detection, PII scrubbing, and refusal detection; block or scrub before/after the model.                                                       |
| 5   | Serving                      | 🟢    | Expose the agent via FastAPI (Python) or Node http (TypeScript); return `answer`, `citations`, `latency_ms`; add a streaming `/chat/stream` SSE endpoint.          |
| 6   | Langfuse: production tracing | 🟡    | Swap Task 2's hand-rolled JSONL tracer for Langfuse behind a tracer-agnostic interface; group all calls under one trace/session; runs offline via a `LocalTracer`. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Eval harness prints faithfulness and relevance scores reproducibly.
- [ ] Every LLM call logs latency and token cost; total cost is summed per session.
- [ ] Cache hits skip the model call; savings are quantified.
- [ ] API returns a valid JSON response on `POST /chat`; streaming works with `curl -N`.
- [ ] Task 6 runs offline (prints a trace tree, one trace/session); adding Langfuse keys sends the same data to the hosted UI with no code change.

---

## Module 07b — Delivery & AI Service Operations

**Prerequisites:** Module 07. Module 11 helps for ingestion workers; Module 20
helps for threat modelling. This is a documentation-first capstone deep dive;
apply it in either language before deploying beyond localhost. Full lesson:
[`modules/07b-delivery-operations/README.md`](modules/07b-delivery-operations/README.md).

**Learning objectives**

- Package an AI API reproducibly; configure it safely without baking in secrets.
- Add authentication, authorisation, tenant isolation, timeouts, rate limits,
  queues, and idempotency.
- Ship through CI, staging, monitored rollout, and a documented rollback.

| #   | Task                 | Depth | What you do                                                                                      |
| --- | -------------------- | ----- | ------------------------------------------------------------------------------------------------ |
| 1   | Containerise API     | 🟢    | Docker/Compose, non-root service, health/readiness endpoints, runtime configuration only.        |
| 2   | Identity + tenants   | 🟡    | Authenticate, authorise, filter retrieval by tenant before it runs, and audit decisions.         |
| 3   | Reliability envelope | 🟡    | Bound dependencies; add concurrency/rate limits, circuit breaker, durable jobs, and idempotency. |
| 4   | Release runbook      | 🟢    | CI + eval gate → staging smoke test → limited rollout → rollback thresholds and command.         |

**Estimated time:** 5–7 hours (plus deployment-platform setup).

**Done when**

- [ ] A clean clone can run a containerised service without leaking credentials.
- [ ] Cross-tenant retrieval, repeated side effects, and provider outage paths are tested.
- [ ] CI, staging, rollout evidence, owners, and rollback are documented.

---

## Module 08 — Classification

**Prerequisites:** Modules 00–04 (embeddings for the embedding classifier).

**Learning objectives**

- Use LLM zero-shot prompting for text classification; understand its limits.
- Use embeddings + a classic ML classifier (logistic regression, k-NN) for classification.
- Implement softmax + gradient descent from scratch to understand the classifier training loop.
- Evaluate classifiers properly: precision, recall, F1, confusion matrix.

**Tasks**

| #   | Task                                | Depth | What you do                                                                                           |
| --- | ----------------------------------- | ----- | ----------------------------------------------------------------------------------------------------- |
| 1   | LLM zero-shot / few-shot classifier | 🟢    | Classify text with a prompt; measure accuracy and per-class F1; compare zero-shot vs few-shot.        |
| 2   | Embeddings + classic ML             | 🟡    | Embed inputs; train a k-NN classifier; compare to zero-shot.                                          |
| 3   | Evaluation                          | 🟡    | Compute precision, recall, F1, and a confusion matrix; compare classifiers on the same test set.      |
| 4   | Softmax + GD from scratch           | 🔴    | Implement forward pass, cross-entropy loss, and gradient descent update manually; loss must decrease. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] Zero-shot and embedding classifiers both run on the same dataset; F1 scores printed.
- [ ] From-scratch softmax + GD loss decreases over training steps.
- [ ] Confusion matrix reveals which class pairs are hardest.
- [ ] You can explain the precision–recall tradeoff in one sentence.

---

## Module 09 — Computer Vision

**Prerequisites:** Modules 00–04. `uv sync --extra vision` (pillow, transformers, torch). Hosted-first module; local optional.

**Learning objectives**

- Classify images with a pretrained ViT/CNN model via a hosted API.
- Use CLIP for zero-shot image classification without any fine-tuning.
- Use a multimodal LLM to answer questions about images via the raw vendor SDK.
- Implement a 2D convolution from scratch to understand how features are extracted.

**Tasks**

| #   | Task                     | Depth | What you do                                                                                            |
| --- | ------------------------ | ----- | ------------------------------------------------------------------------------------------------------ |
| 1   | Image classification     | 🟢    | Classify images with a pretrained model; see top-5 class probabilities.                                |
| 2   | CLIP zero-shot           | 🟢    | Classify images with CLIP using only text prompts; change the label list and watch the ranking change. |
| 3   | Multimodal LLM vision    | 🟡    | Pass images to a vision-capable LLM via raw vendor SDK; ask questions; compare to CLIP.                |
| 4   | Convolution from scratch | 🔴    | Implement 2D cross-correlation; apply Sobel and blur kernels; verify output matches reference.         |

**Estimated time:** 4–5 hours

**Done when**

- [ ] Pretrained model returns sensible top-5 classes for your test images.
- [ ] CLIP correctly ranks labels with only text prompts; no retraining.
- [ ] Multimodal LLM answers a descriptive question about an image.
- [ ] From-scratch convolution sanity-check passes; output images are visually correct.

---

## Module 10 — Image Generation

**Prerequisites:** Module 09. A Stable Diffusion API key (Replicate, HuggingFace, Stability AI, or NVIDIA NIM). Hosted-first module; local optional.

**Learning objectives**

- Generate images via a hosted Stable Diffusion API; understand prompt, steps, CFG, and seed.
- Sweep guidance_scale and num_inference_steps; understand negative prompts.
- Experiment with img2img and inpainting.
- Understand the diffusion forward/reverse process via a toy NumPy implementation.

**Tasks**

| #   | Task                           | Depth | What you do                                                                                                       |
| --- | ------------------------------ | ----- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | Text-to-image                  | 🟢    | Generate images with varied prompts and seeds; save PNGs.                                                         |
| 2   | Prompt craft & parameter sweep | 🟡    | Sweep guidance_scale and steps; save a grid; understand negative prompts.                                         |
| 3   | img2img & inpainting           | 🟡    | Transform an input image with img2img; edit a masked region with inpainting.                                      |
| 4   | Toy diffusion from scratch     | 🔴    | Implement forward noising and DDPM reverse step in NumPy; generated 2D points should match training distribution. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] At least two PNGs from different seeds saved (Task 1).
- [ ] Parameter sweep grid saved; you can explain what guidance_scale does (Task 2).
- [ ] `img2img_output.png` and `inpaint_output.png` saved (Task 3).
- [ ] Toy diffusion generates points that look like the training distribution (Task 4).

---

## Module 11 — Document Ingestion

**Prerequisites:** Module 05 (RAG). `uv sync --extra ingest` (Python — pypdf, beautifulsoup4, lxml, pymupdf; Task 6 also needs the `openai`/`anthropic` SDK); `pnpm install` (TypeScript — picks up pdf-parse, cheerio).

**Learning objectives**

- Parse PDF, HTML, and Markdown into normalised Document records.
- Clean and normalise extracted text: strip boilerplate, collapse whitespace, deduplicate paragraphs.
- Chunk documents by section/heading structure rather than by arbitrary character counts.
- Implement incremental indexing with a content-hash manifest to skip unchanged documents.
- Attach per-document ACL metadata at ingestion and enforce it at retrieval time (permissions-aware RAG with citations).
- Retrieve over PDF pages as images (caption → embed → retrieve → answer over pixels) when the text layer fails.

**Tasks**

| #   | Task                        | Depth | What you do                                                                                                                                      |
| --- | --------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Parse documents             | 🟢    | Extract text from PDF, HTML, and Markdown; normalise to a Document record; strip nav/footer noise from HTML.                                     |
| 2   | Clean & normalize           | 🟡    | Strip Markdown syntax, collapse whitespace, remove boilerplate lines, deduplicate near-identical paragraphs.                                     |
| 3   | Structure-aware chunking    | 🟡    | Detect ATX heading boundaries; emit one chunk per section; sub-chunk long sections; prepend heading to every sub-chunk.                          |
| 4   | Incremental indexing        | 🟢    | Hash each document; skip unchanged ones on re-run; maintain a manifest JSON; prune stale entries.                                                |
| 5   | Permissions-aware retrieval | 🟡    | Tag chunks with ACLs (owner/groups/visibility) at ingestion; enforce at retrieval via pre- and post-filter; carry source/section/page citations. |
| 6   | Multimodal PDF retrieval    | 🟡    | Render pages to images; caption with a vision LLM; embed captions; retrieve the table page; answer the figure over the page image.               |

**Estimated time:** 5–6 hours

**Done when**

- [ ] `parse_document()` handles `.md` and `.html` without error; HTML strips nav/footer.
- [ ] Cleaned HTML has no nav/footer text; cleaned Markdown has no `#`/`**` chars.
- [ ] Section-aware chunks carry `metadata.section` and respect heading boundaries.
- [ ] Second incremental-indexing run shows 0 new / 0 changed / N skipped.
- [ ] `retrieve_for_user()` enforces ACLs: guest cannot see private/group docs; pre- and post-filter agree.
- [ ] Every retrieval result includes a citation with source + section (+ page for PDFs).
- [ ] Multimodal retrieval indexes page images, retrieves the table page for a revenue query, and reads the figure from the image.

---

## Module 12 — Text-to-SQL

**Prerequisites:** Modules 00–02. SQLite (stdlib). `pnpm install` picks up better-sqlite3 for TypeScript.

**Learning objectives**

- Generate SQL from natural-language questions with schema-grounded prompting.
- Auto-generate schema descriptions from a live database (table names, columns, sample rows, FK hints).
- Validate generated SQL for safety: read-only whitelist, stacked-query injection rejection.
- Self-repair broken SQL in a multi-turn conversation; route questions between SQL and RAG.

**Tasks**

| #   | Task                   | Depth | What you do                                                                                                  |
| --- | ---------------------- | ----- | ------------------------------------------------------------------------------------------------------------ |
| 1   | NL→SQL                 | 🟢    | Generate SQL from a question, execute it, print the rows.                                                    |
| 2   | Schema-aware prompting | 🟡    | Auto-generate schema description from live DB; add sample rows and JOIN hints; handle multi-table questions. |
| 3   | Safety & repair        | 🟡    | Validate read-only; reject stacked queries; self-repair on DB errors (up to `max_retries`).                  |
| 4   | Hybrid routing         | 🟢    | Classify intent (sql/vector/both); dispatch to SQL or RAG accordingly; handle ambiguous questions.           |

**Estimated time:** 4–5 hours

**Done when**

- [ ] `seed_db.py` / `seed-db.ts` builds `sales.db` with 8 customers, 10 products, 20 orders.
- [ ] All 4 NL questions answered with valid SQL and rows (Task 1).
- [ ] Adversarial inputs blocked; `UnsafeSQLError` raised (Task 3).
- [ ] Routing classification printed; SQL questions produce rows; RAG questions produce text (Task 4).

---

## Module 13 — Fine-tuning

**Prerequisites:** Modules 00–02. `OPENAI_API_KEY` for Task 2. `uv sync --extra finetune` for Task 3 (optional, heavy). Hosted-first module.

**Learning objectives**

- Decide when fine-tuning is worth the cost vs. prompting or RAG.
- Prepare a JSONL training dataset and launch a hosted SFT job via the OpenAI API.
- Understand LoRA (Low-Rank Adaptation) by implementing the low-rank update from scratch.
- Detect overfitting by tracking train vs. validation loss curves.

**Tasks**

| #   | Task                            | Depth | What you do                                                                                                 |
| --- | ------------------------------- | ----- | ----------------------------------------------------------------------------------------------------------- |
| 1   | Decide: prompt vs fine-tune     | 🟢    | Run a narrow task through a prompt baseline and a mock fine-tuned baseline; compare formality scores.       |
| 2   | Hosted SFT via OpenAI API       | 🟢    | Build a 30-example JSONL dataset, upload, launch a fine-tune job, compare the fine-tuned model to the base. |
| 3   | LoRA / QLoRA locally (Python)   | 🟡    | Use PEFT + transformers to add LoRA adapters to a small model; print trainable vs total parameters.         |
| 4   | Dataset prep & overfitting eval | 🟡    | Clean examples, split train/val/test, track val score separately from train score, flag overfitting.        |
| 5   | Understand LoRA from scratch    | 🔴    | Implement `B@A` low-rank update in numpy/plain arrays; verify equivalence; print param savings table.       |

**Estimated time:** 5–7 hours

**Done when**

- [ ] `01_decide` / `01-decide` runs and prints a comparison table (Task 1).
- [ ] Valid JSONL file written and fine-tune job submitted (Task 2).
- [ ] Trainable parameter count < 1 % of total (Task 3, with finetune extra).
- [ ] Train vs val score table printed with overfitting signal (Task 4).
- [ ] Equivalence check passes; param savings table correct (Task 5).

---

## Module 13b — Post-training & Alignment (RLHF & DPO)

**Prerequisites:** Module 13 (and Module 01b helps). NumPy (a base dependency —
no extra needed). Pure numpy (Python) / plain TypeScript, fully offline,
deterministic — no provider, no network, no LLM.

**Why:** "How is ChatGPT actually trained?" — pretraining → SFT → preference
optimization (RLHF or DPO) — is a top LLM interview question, and module 13
stops at SFT. This companion builds the missing stage from scratch on toy
models: "responses" are synthetic feature vectors scored by a hidden true
reward, and the policies are small tabular softmaxes, so every algorithm stays
visible — preference data → reward model → RLHF (with its failure mode, reward
hacking) → DPO.

**Learning objectives**

- Aggregate noisy pairwise preferences into win-rate matrices and Elo ratings
  (the Chatbot Arena mechanics) and recover a true quality ordering.
- Train a Bradley–Terry reward model on (chosen, rejected) pairs and verify it
  recovers the hidden reward direction.
- Implement REINFORCE with a baseline for the KL-regularized RLHF objective,
  and demonstrate reward hacking (Goodhart's law) with and without the KL leash.
- Derive and implement the DPO loss and its analytic gradient, verified by a
  finite-difference grad check.

**Tasks**

| #   | Task                              | Depth | What you do                                                                                                                          |
| --- | --------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Preference data: win rates & Elo  | 🟢    | Implement `win_rate_matrix`, `elo_update`, `run_elo`; replay a noisy match log and recover the true model ordering.                  |
| 2   | Reward model (Bradley–Terry)      | 🟡    | Implement `bt_prob`, `bt_loss`, `bt_grad_step`; train a linear RM on noisy pairs, check ranking accuracy + cosine to w\*.            |
| 3   | RLHF (REINFORCE) + reward hacking | 🔴    | Implement `softmax`, `reinforce_step`, `kl_divergence`; optimize an imperfect RM with/without the KL leash, watch Goodhart.          |
| 4   | DPO from scratch                  | 🔴    | Implement `dpo_loss` and the analytic `dpo_grad` (finite-difference checked); train on pairs, watch the implicit reward margin grow. |

**Estimated time:** 4–6 hours

**Done when**

- [ ] Task 1: win-rate matrix consistent, Elo ordering matches true quality, best model clearly on top.
- [ ] Task 2: held-out ranking accuracy ≥ 0.9, cosine(θ, w\*) ≥ 0.9, monotone BT loss.
- [ ] Task 3: no-KL run shows the Goodhart collapse (true reward below its peak, proxy at max, P(exploit) > 0.9); KL run keeps true reward ≥ 0.9× peak with KL < 1.0 and P(exploit) < 0.3.
- [ ] Task 4: grad check < 1e-5; P(chosen) − P(rejected) > 0.2; monotone DPO loss; KL(π‖π_ref) < 1.5.
- [ ] You can derive the DPO loss from the RLHF objective and name RLAIF, KTO, IPO, GRPO.

---

## Module 14 — Local Inference & Optimization

**Prerequisites:** Module 00 (Ollama). No extra deps for default path; `uv sync --extra finetune` (llama-cpp-python et al.) optional for the local path.

**Learning objectives**

- Measure tokens per second on local models; understand the throughput vs. latency tradeoff.
- Compare quantization levels (fp16 vs Q4) for size, speed, and quality.
- Measure TTFT with streaming and aggregate throughput with concurrent requests.
- Understand KV caching by implementing a toy cached vs. uncached autoregressive loop.

**Tasks**

| #   | Task                                    | Depth | What you do                                                                                                    |
| --- | --------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------- |
| 1   | Run local models and measure tokens/sec | 🟢    | Benchmark Ollama; print min/max/mean tokens/sec; print engine guide table.                                     |
| 2   | Quantization: size vs speed vs quality  | 🟡    | Compare two quantization levels; measure speed and LLM-judge quality; print comparison table.                  |
| 3   | Throughput vs latency: batching         | 🟡    | Measure TTFT via streaming; fire N concurrent requests; show aggregate throughput > sequential.                |
| 4   | Serving engines: pick by use case       | 🟢    | Implement `recommend_engine()`; print four-engine comparison table; run same prompt against available engines. |
| 5   | KV cache intuition                      | 🔴    | Implement cached vs uncached toy autoregressive loop; measure speedup; verify O(n) vs O(n²) key computations.  |

**Estimated time:** 4–5 hours

**Done when**

- [ ] `01_run_local` / `01-run-local` runs against Ollama and prints tokens/sec.
- [ ] Quantization comparison table printed with measured speed numbers (Task 2).
- [ ] Concurrent throughput measurably higher than sequential (Task 3).
- [ ] KV cache: cached key computations = N; uncached = N\*(N+1)/2 (Task 5).

---

## Module 15 — Reasoning & Test-time Compute

**Prerequisites:** Modules 00–03. `OPENAI_API_KEY` (o4-mini) and/or `ANTHROPIC_API_KEY` (extended thinking).

**Learning objectives**

- Compare a standard model to a reasoning model on hard multi-step problems.
- Implement self-consistency (sample N CoT paths, majority-vote) and best-of-N with a verifier.
- Build a draft → critique → revise self-refine loop.
- Plot the cost/accuracy curve and identify the accuracy-per-dollar sweet spot.

**Tasks**

| #   | Task                                        | Depth | What you do                                                                               |
| --- | ------------------------------------------- | ----- | ----------------------------------------------------------------------------------------- |
| 1   | Reasoning vs standard model                 | 🟢    | Side-by-side comparison table: model, answer, tokens, latency for the same hard problems. |
| 2   | Test-time compute without a reasoning model | 🟡    | Implement self-consistency and best-of-N with a verifier; show accuracy rising with N.    |
| 3   | Self-refine / reflection                    | 🟡    | Implement draft → critique → revise loop; run 2 iterations; observe concrete improvement. |
| 4   | Cost / latency of reasoning strategies      | 🟢    | Measure all strategies; print table sorted by cost; annotate the sweet spot.              |

**Estimated time:** 3–5 hours

**Done when**

- [ ] Side-by-side table comparing standard vs. reasoning model on ≥ 2 problems (Task 1).
- [ ] Self-consistency and best-of-N show accuracy rising with N (Task 2).
- [ ] Self-refine loop runs 2 iterations; revision is concretely better (Task 3).
- [ ] Cost/latency table covers all strategies; sweet spot annotated (Task 4).

---

## Module 16 — Context Engineering

**Prerequisites:** Modules 00–02. No extras needed (tiktoken is a base dependency). `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` for caching/batch tasks.

**Learning objectives**

- Count tokens precisely with tiktoken; enforce token budgets with three truncation strategies.
- Use provider prompt caching (Anthropic `cache_control`, OpenAI automatic) to cut cost on repeated prefixes.
- Compact long conversations with a running summary to prevent context overflow.
- Apply map-reduce and refine over documents too large for a single call; demonstrate "lost in the middle".
- Submit batch requests at 50 % cost via the OpenAI or Anthropic Batch API.
- Offload bulky tool outputs from an agent loop's history to a tool-log store with on-demand retrieval; keep message history append-only so prompt-cache prefixes survive.

**Tasks**

| #   | Task                             | Depth | What you do                                                                                                                                 |
| --- | -------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Token budgeting                  | 🟢    | Count tokens; implement head/tail/middle-out truncation; print results table.                                                               |
| 2   | Prompt caching                   | 🟢    | Make repeated calls with a large prefix; observe cache hits in `usage`; measure cost saving.                                                |
| 3   | Conversation memory / compaction | 🟡    | Summarise oldest turns when budget exceeded; verify compaction fires and context stays in budget.                                           |
| 4   | Long-context strategies          | 🟡    | Implement map-reduce and refine over chunked document; demonstrate lost-in-the-middle recall.                                               |
| 5   | Batch API                        | 🟢    | Submit 5 requests via Batch API; poll until complete; print results and estimated savings.                                                  |
| 6   | Tool-output offloading           | 🟡    | Offload large tool outputs to a log store; keep one-line references in history; retrieve on demand; compare context growth vs a naive loop. |

**Estimated time:** 5–6 hours

**Done when**

- [ ] `count_tokens` uses tiktoken; all three truncation strategies print a results table (Task 1).
- [ ] Second call shows a non-zero cache hit and lower estimated cost (Task 2).
- [ ] Compaction fires; context stays within budget; coherence preserved (Task 3).
- [ ] Map-reduce and refine both produce answers; lost-in-the-middle demonstrated (Task 4).
- [ ] Batch job completes; results printed; cost savings calculated (Task 5).
- [ ] Task 6: offloaded loop stays far under the naive loop's final token count; `read_tool_log` round-trips payloads exactly; the final answer recovers a fact that lives only in a stored payload.

---

## Module 17 — MCP & Modern Agent APIs

**Prerequisites:** Modules 02, 06. `uv sync --extra mcp`. `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.

**Learning objectives**

- Use the OpenAI Responses API (response chaining, hosted tools) and Anthropic tool use SDK.
- Connect an MCP client to an existing server via stdio; discover and call tools.
- Build an MCP server that exposes `search_docs`, `read_module`, and `run_exam_question`.
- Wire MCP tools into an agent loop that dynamically fetches schemas at runtime.
- Expose an MCP server over HTTP/SSE and understand its security implications.
- Fix tool-schema overload with semantic tool discovery: index augmented tool descriptions, retrieve only the top-k relevant schemas per query.

**Tasks**

| #   | Task                         | Depth | What you do                                                                                                                                                                    |
| --- | ---------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Modern agent APIs            | 🟢    | Use OpenAI Responses API and Anthropic tool use to answer a two-part question; compare to module 06 manual loop.                                                               |
| 2   | Use an MCP server            | 🟢    | Connect client to an existing server via stdio; list tools; call one tool.                                                                                                     |
| 3   | Build the course MCP server  | 🟢    | Build stdio MCP server with `search_docs`, `read_module`, `run_exam_question`; all three tools work when tested.                                                               |
| 4   | Wire MCP tools into an agent | 🟡    | Fetch tool schemas dynamically from the course server; run OpenAI and Anthropic agent loops using MCP tools.                                                                   |
| 5   | Remote MCP + security        | 🟡    | Expose the server over HTTP/SSE; add bearer-token auth; explain five security threats.                                                                                         |
| 6   | Semantic tool discovery      | 🟡    | Index LLM-augmented tool descriptions in a vector store; retrieve top-3 schemas per query; beat the full-20-schema baseline on selection accuracy at < 25 % of the token cost. |

**Estimated time:** 6–8 hours

**Done when**

- [ ] Both OpenAI Responses API and Anthropic correctly answer a two-part question with tools (Task 1).
- [ ] Task 2 client connects to an existing server, lists tools, calls one.
- [ ] Task 3 server's three tools work when tested with the Task 2 client.
- [ ] Task 4 agent answers course-related questions using dynamically fetched MCP schemas.
- [ ] Task 5 server reachable over HTTP/SSE; client lists and calls tools over the network.
- [ ] Task 6 toolbox: top-3 retrieval beats the full-schema-list baseline on selection accuracy at < 25 % of the schema token cost; script prints "All acceptance checks passed."

---

## Module 18 — Computer Use

**Prerequisites:** Modules 06, 09. `uv sync --extra browser` + `uv run playwright install chromium`. `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for vision tasks.

**Learning objectives**

- Drive a headless Chromium browser with Playwright: navigate, read content, take screenshots.
- Build a vision-grounded browser agent (screenshot → multimodal LLM → action → repeat).
- Build a DOM/accessibility-tree agent; compare cost and reliability to the vision agent.
- Add a safety layer: domain allowlist, risk classification, human confirmation gate, injection sanitisation.

**Tasks**

| #   | Task                          | Depth | What you do                                                                                    |
| --- | ----------------------------- | ----- | ---------------------------------------------------------------------------------------------- |
| 1   | Browser automation basics     | 🟢    | Navigate to a URL; read title and text; count links; take a screenshot.                        |
| 2   | Vision-grounded browser agent | 🟡    | Multi-step agent using screenshots + multimodal LLM to decide actions; step PNGs saved.        |
| 3   | DOM/accessibility agent       | 🟡    | Same task without screenshots; use a11y tree (text); compare token cost to vision agent.       |
| 4   | Computer use & safety         | 🟢    | Domain allowlist, risk classification, human confirmation gate, prompt-injection sanitisation. |

**Estimated time:** 5–6 hours

**Done when**

- [ ] Browser navigation works; screenshot saved (Task 1).
- [ ] Vision agent completes a 2–3 step goal; step screenshots saved (Task 2).
- [ ] DOM/a11y agent completes the same goal without screenshots (Task 3).
- [ ] Safety layer blocks untrusted domains, classifies high-risk actions, strips injections (Task 4).

---

## Module 19 — Audio & Speech

**Prerequisites:** Modules 00–02. `OPENAI_API_KEY`. `uv sync --extra audio` for mic mode. Hosted-first module.

**Learning objectives**

- Transcribe an audio clip with OpenAI Whisper; optionally run faster-whisper locally.
- Synthesise speech from text with the OpenAI TTS API; understand voice, model, and speed options.
- Chain STT → RAG retrieval → LLM → TTS into a complete voice-tutor loop.
- Implement energy-based Voice Activity Detection (VAD) from scratch; understand diarisation concepts.
- Understand the OpenAI Realtime API and when it beats the three-step batch pipeline.

**Tasks**

| #   | Task                      | Depth | What you do                                                                                            |
| --- | ------------------------- | ----- | ------------------------------------------------------------------------------------------------------ |
| 1   | Speech-to-text            | 🟢    | Transcribe an audio clip with hosted Whisper; optionally run faster-whisper locally.                   |
| 2   | Text-to-speech            | 🟢    | Synthesise speech from text; save as MP3; try different voices, models, and speed.                     |
| 3   | Voice tutor loop          | 🟡    | Chain STT → RAG over module READMEs → LLM → TTS; answer a spoken question with a spoken answer.        |
| 4   | Audio preprocessing & VAD | 🟡    | Implement energy-based VAD from scratch; trim silence; optionally apply noise reduction.               |
| 5   | Realtime voice            | 🟢    | Run dry-run mode; explain Realtime API latency advantage; optionally implement live WebSocket session. |

**Estimated time:** 4–6 hours

**Done when**

- [ ] Transcribed an audio clip with hosted Whisper (Task 1).
- [ ] `assets/output.mp3` exists and contains audible speech (Task 2).
- [ ] Voice tutor returns a spoken answer drawn from module READMEs (Task 3).
- [ ] Energy-based VAD implemented; `sample_trimmed.wav` is shorter than original (Task 4).
- [ ] Can explain Realtime API trade-offs vs. batch pipeline (Task 5).

---

## Module 20 — AI Security

**Prerequisites:** Modules 02–07 (agents, RAG, eval). No extra deps.

**Learning objectives**

- Perform and defend against direct prompt injection; measure hardening improvement with a scorecard.
- Poison a RAG knowledge base and demonstrate indirect injection; apply content-provenance mitigations.
- Demonstrate excessive-agency risk (over-privileged agent deleting files); apply least-privilege + approval gate.
- Run a systematic red-team harness with LLM-as-judge scoring.
- Demonstrate vector-store data poisoning and system-prompt leakage; map findings to OWASP LLM Top 10.

**Tasks**

| #   | Task                                        | Depth | What you do                                                                                                            |
| --- | ------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------- |
| 1   | Direct prompt injection: attack then defend | 🔴    | Build a naive assistant, inject it, add layered defences; print a scorecard showing improvement.                       |
| 2   | Indirect injection via RAG / tools          | 🔴    | Poison a retrieved document; demonstrate `<leak>` exfiltration; harden with `[UNTRUSTED]` labelling and output filter. |
| 3   | Excessive agency & approval gates           | 🟡    | Over-privileged agent deletes sandbox files; least-privilege + approval gate prevents the same action.                 |
| 4   | Red-team harness                            | 🟡    | Run 8 attack prompts against a simple assistant; score with LLM judge; show score improvement after hardening.         |
| 5   | Vector weaknesses + OWASP mapping           | 🟢    | Demonstrate data poisoning and system-prompt leakage via cosine similarity; map all findings to OWASP LLM Top 10.      |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Scorecard shows naive vs hardened success rates; hardened blocks ≥ 5 of 7 attacks (Task 1).
- [ ] `<leak>` tags appear in naive RAG output; hardened version redacts them (Task 2).
- [ ] Over-privileged agent deletes all files; least-privilege + gate prevents deletion (Task 3).
- [ ] Red-team harness scorecard printed; score improves after applying defences (Task 4).
- [ ] Vector poisoning and prompt leakage demonstrated; OWASP Top 10 fully mapped (Task 5).

---

## Module 20b — AI Governance, Privacy & Responsible Product Practice

**Prerequisites:** Modules 11 and 20; Module 21 helps for evidence and
monitoring. This documentation-first capstone deep dive is not legal advice.
Full lesson:
[`modules/20b-governance-privacy/README.md`](modules/20b-governance-privacy/README.md).

**Learning objectives**

- Map data through prompts, vectors, logs, caches, vendors, and deletion.
- Minimise collection; define retention, rights, audit, licence, and ownership decisions.
- Test inclusive, accessible, accountable user paths and escalation/recourse.

| #   | Task                     | Depth | What you do                                                                                     |
| --- | ------------------------ | ----- | ----------------------------------------------------------------------------------------------- |
| 1   | Data map + minimisation  | 🟢    | Classify every store/hop, name purpose/owner/retention, then remove or redact unnecessary data. |
| 2   | Rights + auditability    | 🟡    | Build a synthetic-data export/delete workflow across primary and derived artifacts.             |
| 3   | Model + data card        | 🟢    | Document purpose, versions, licences, limitations, prohibited uses, monitoring, and escalation. |
| 4   | Inclusive accountable UX | 🟡    | Test representative scenarios and accessibility; turn a discrepancy into a product/eval case.   |

**Estimated time:** 4–6 hours.

**Done when**

- [ ] Every store has a purpose, access rule, retention/deletion rule, and owner.
- [ ] Export/delete and audit paths work for synthetic data.
- [ ] A reviewed model/data card, escalation path, and accessibility findings exist.

---

## Module 21 — LLMOps & Eval

**Prerequisites:** Modules 05–07 (eval harness, observability). No extra deps.

**Learning objectives**

- Load a versioned eval dataset and score each case with exact-match, contains, and LLM-as-judge graders.
- Run multi-variant experiments; compare run files and pick a winner with numbers.
- Build a regression gate script that exits non-zero in CI when a metric drops below a threshold.
- Route low-confidence outputs to a human review queue; fold labels back into the eval set.
- Parse JSONL observability logs; compute p50/p95 latency, error rate, and cost; emit alerts.

**Tasks**

| #   | Task                         | Depth | What you do                                                                                              |
| --- | ---------------------------- | ----- | -------------------------------------------------------------------------------------------------------- |
| 1   | Versioned eval set + graders | 🟢    | Load versioned eval set; run three grader types; write a results JSON file.                              |
| 2   | Experiments                  | 🟡    | Run two prompt-version variants; compare runs; declare a winner with numbers.                            |
| 3   | Regression gate in CI        | 🟡    | Script exits non-zero when metric < threshold; integrate into GitHub Actions or Husky pre-push.          |
| 4   | Human review + feedback loop | 🟡    | Route low-confidence outputs to a JSONL queue; label interactively; merge approved labels into eval set. |
| 5   | Production monitoring        | 🟢    | Parse JSONL logs; compute p50/p95 latency, error rate, cost; print report with alerts.                   |

**Estimated time:** 5–6 hours

**Done when**

- [ ] All 5 eval cases scored; `results/run_*.json` written (Task 1).
- [ ] Two prompt-version runs compared; winner declared with numbers (Task 2).
- [ ] `--threshold 0.99` exits non-zero; `--threshold 0.01` exits zero (Task 3).
- [ ] Review queue written; `--merge` bumps eval set version and adds cases (Task 4).
- [ ] Demo log parsed; report printed with latency stats and alerts (Task 5).

---

## Module 21b — Evaluation Science & Agent Reliability

**Prerequisites:** Modules 05, 06, and 21. This documentation-first capstone
deep dive turns the eval lifecycle into credible release evidence. Full lesson:
[`modules/21b-evaluation-reliability/README.md`](modules/21b-evaluation-reliability/README.md).

**Learning objectives**

- Measure retrieval, answer quality, and agent behavior separately.
- Build held-out gold-evidence benchmarks and quantify comparison uncertainty.
- Check judge agreement and deterministically test tool trajectories and policy gates.

| #   | Task                    | Depth | What you do                                                                                            |
| --- | ----------------------- | ----- | ------------------------------------------------------------------------------------------------------ |
| 1   | Retrieval benchmark     | 🟡    | Label gold chunks; implement Recall@k, MRR, NDCG and compare dense/hybrid/reranked retrieval.          |
| 2   | Claim + citation eval   | 🟡    | Grade atomic claims, support, citation validity, and task success separately.                          |
| 3   | Uncertainty + agreement | 🟢    | Compare paired variants with bootstrap intervals, practical thresholds, and judge disagreement queues. |
| 4   | Agent trajectory suite  | 🔴    | Assert tool/argument/approval/retry/idempotency/termination behavior with deterministic fakes.         |

**Estimated time:** 5–7 hours.

**Done when**

- [ ] Development and held-out evidence sets, retriever metrics, and failure reports exist.
- [ ] Variant promotion can be “inconclusive” and judge disagreements are reviewed.
- [ ] Policy-violating trajectories fail even when the final text looks correct.

---

## Module 22 — AI Product UX

**Prerequisites:** Modules 05–07 (RAG, serving). `uv sync --extra production`.

**Learning objectives**

- Stream tokens to the browser via Server-Sent Events (SSE); understand the typed event protocol.
- Surface citations as inspectable source chips with a drill-down panel.
- Render confidence states (high/medium/low badges) and distinct failure states (loading, error, empty).
- Capture user feedback (thumbs up/down, "looks wrong" text) and store it for the eval flywheel.
- Implement an approval flow with one-time tokens for risky AI-triggered actions.

**Tasks**

| #   | Task                            | Depth | What you do                                                                                             |
| --- | ------------------------------- | ----- | ------------------------------------------------------------------------------------------------------- |
| 1   | Streaming UI                    | 🟢    | Ask a question; watch tokens stream live; blinking cursor disappears on finish.                         |
| 2   | Citations + source drill-down   | 🟢    | Source chips appear after every answer; clicking one opens a panel with title, URL, content.            |
| 3   | Confidence + failure states     | 🟡    | Render loading, error, and low-confidence states; integrate LLM-judge faithfulness as confidence score. |
| 4   | Feedback capture                | 🟢    | 👍/👎 and "looks wrong" feedback stored in JSONL; confirmation message appears and disappears.          |
| 5   | Approval flow for risky actions | 🟡    | Modal shows action description + payload; approve/reject both logged; expired tokens return "expired".  |

**Estimated time:** 4–5 hours

**Done when**

- [ ] Tokens stream live; cursor disappears on finish (Task 1).
- [ ] Source chips appear; clicking one opens the drill-down panel (Task 2).
- [ ] Loading, error, and low-confidence states all render correctly (Task 3).
- [ ] `feedback.jsonl` grows with each rating; "looks wrong" stores the note (Task 4).
- [ ] Modal appears for risky action; approve/reject both logged; expired token returns "expired" (Task 5).

---

## Module 23 — Capstone

**Prerequisites:** All previous modules, especially 04, 05, 06, 07/07b, 11,
20/20b, 21/21b, and 22. Apply the documentation-first production deep dives to
any capstone that handles other people's data or is deployed beyond localhost.

**Learning objectives**

- Integrate retrieval, document ingestion, generation, agents, security, eval, and UX into a single end-to-end application.
- Make deliberate architectural decisions and justify them against the constraints.
- Evaluate your own work honestly against a rubric that covers all six production dimensions.
- Ship something you would actually use.

**Tracks**

| Option          | What you build                                                                                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A (recommended) | Documentation / Q&A assistant: document ingestion (11) + hybrid RAG (04/05) + agent + tools (06/17) + delivery (07/07b) + security/governance (20/20b) + release evidence (21/21b) + streaming UI (22) |
| B               | Research / news agent: planner + workers + synthesis + eval gate + security hardening                                                                                                                  |
| C               | Multimodal assistant: vision (09) + document ingestion (11) + RAG + conversational agent + eval                                                                                                        |

**Milestone plan (Option A)**

| Milestone                           | Done when                                                                                                                                                                                                                                                                                       |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1 — Ingest                         | Top-3 passages for 5 hand-crafted questions are all on-topic. Draws on modules 04, 11.                                                                                                                                                                                                          |
| M2 — Hybrid retrieve + rerank       | Hybrid beats dense-only MRR@5. Draws on modules 04, 05.                                                                                                                                                                                                                                         |
| M3 — Generator with citations       | 5/5 answers include a valid citation; none contradict passages. Draws on module 05.                                                                                                                                                                                                             |
| M4 — Agent + tools                  | Agent answers a 2-hop question requiring two retrieval steps. Draws on modules 06, 17.                                                                                                                                                                                                          |
| M5 — Eval harness + served API + UX | Eval pass rate ≥ 70 %; API returns `{answer, citations, latency_ms}`; streaming UI live. Draws on modules 07, 20, 21, 22.                                                                                                                                                                       |
| M6 — Accountable release            | Deployed staging revision (image digest + config revision) recorded; cross-tenant boundary test passes; migration-from-empty + rollback exercise evidenced per the 07b RUNBOOK; data map, model/data card, held-out retrieval evidence, and agent-policy suite. Draws on modules 07b, 20b, 21b. |

**Estimated time:** 10–20 hours (open-ended)

**Done when**

- [ ] A runnable app covers at least four rubric dimensions.
- [ ] Automated eval script prints a score without manual intervention.
- [ ] App uses `get_provider()` / `getProvider()` — no hardcoded vendors.
- [ ] Provider can be swapped by changing one env var.
- [ ] Self-evaluation rubric filled in with honest scores (target ≥ 15/24).
- [ ] If deployed or handling other people's data: M6 release evidence is
      complete — a recorded staging revision, a cross-tenant boundary test,
      migration-from-empty evidence, and a rollback exercise (per the 07b RUNBOOK).

---

## Applied Projects

### `projects/news-agent` — Telegram daily news digest

A Telegram bot that an LLM agent drives to collect news on a topic you choose,
curate the most important stories, and post a daily digest. It is a complete
end-to-end example of modules 02 + 04 + 05 + 06 in production.

**When to build it:** after Module 06 (you need agents). It is also an excellent
reference to study before the capstone.

```bash
# install the telegram extra
uv sync --extra telegram

# set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
# then:
uv run python -m news_agent        # run once
# or start the scheduler for daily posts at NEWS_POST_HOUR
```

Study `projects/news-agent/news_agent/`:

| File              | What it teaches                   |
| ----------------- | --------------------------------- |
| `pipeline.py`     | Orchestration — the "outer loop"  |
| `sources.py`      | Retrieval from RSS / Google News  |
| `agent.py`        | Two-step LLM agent (rank + write) |
| `telegram_bot.py` | Integration / serving layer       |
| `scheduler.py`    | Production scheduling pattern     |

---

### `projects/tutor` — Study CLI (`/tutor` and `/exam`)

A lightweight RAG + LLM-as-judge CLI for studying this course. Ask questions
about any module, or take a graded exam. Usable from day one; most valuable
after modules 05 and 07 when you can read its source and understand how it works.

**When to use it:** any time. Study it after Module 05 (RAG) and Module 07
(LLM-as-judge) to see the patterns you built used in a real tool.

```bash
# interactive Q&A
uv run python -m tutor ask

# graded exam on module 04
uv run python -m tutor exam --module 04

# or use the Claude Code slash commands (inside Claude Code):
# /tutor   — starts the ask REPL
# /exam    — starts a graded exam
```

---

## Choose a route

There is no single "finish the course" path. Pick **one of four independently
usable routes** by the outcome you want. Each route names its goal, the
background it assumes, the provider/hardware it needs, the portfolio artifact you
end with, and the route to take next. Every companion and deep dive is
accounted for in exactly this way — it is either **scheduled inside a route** or
**explicitly excluded with a pointer to the route that owns it**. Nothing is
silently dropped.

### How the time budget works

The hours below are **not** one lump estimate. Each lesson's time splits into
four buckets that are published and summed **separately**, because they are the
things that surprise people:

- **Exercise-only** — writing and running the tasks. (This equals each module's
  "Estimated time" above.)
- **Setup/debug** — reading the README, installing extras, and debugging.
- **Provider/cloud** — provisioning hosted keys, cloud/deploy setup, waiting on
  hosted jobs, or heavy local downloads _beyond_ the free Ollama baseline. On the
  fully-local/offline path this bucket trends toward its minimum.
- **Capstone** — open-ended integration work (module 23 only).

Every number here is generated from and CI-verified against a single source,
[`scripts/curriculum/module_times.json`](scripts/curriculum/module_times.json),
by [`scripts/curriculum/check_route_hours.py`](scripts/curriculum/check_route_hours.py)
(run it with `--report` to regenerate). If a module estimate changes, the check
fails until these totals are updated — so a learner never reconciles conflicting
numbers. These are honest ranges for planning, not guarantees, and nothing here
is legal or financial advice.

### Route hours at a glance

Totals in hours (min–max), each bucket summed separately across the route's lessons:

| Route                | Lessons | Exercise-only | Setup/debug | Provider/cloud | Capstone |
| -------------------- | ------- | ------------- | ----------- | -------------- | -------- |
| **Core app-builder** | 27      | 114–153       | 28–52.5     | 11–22          | 10–20    |
| **ML foundations**   | 5       | 22–32         | 6–11        | 0              | 0        |
| **Agent systems**    | 12      | 55–74         | 14.5–25.5   | 4.75–9.5       | 10–20    |
| **Model training**   | 5       | 20–28         | 4.5–9       | 2.25–4.5       | 0        |

### Route decision guidance

| Route            | Learner goal                                            | Assumed background                          | Provider / hardware                                      | Portfolio artifact                                         | Next route                          |
| ---------------- | ------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------- |
| Core app-builder | Ship a working, evaluated, deployable AI app end to end | Programming; no ML background needed        | One provider (free Ollama works); hosted keys optional   | A deployed RAG-agent app with eval and release evidence    | Agent systems, or Model training    |
| ML foundations   | Build the classic-ML / DL / transformer math by hand    | Module 01; comfort with NumPy and calculus  | None — pure offline NumPy + TypeScript                   | A from-scratch ML repo (regression → autograd → GPT block) | Model training, or Agent systems    |
| Agent systems    | Build and ship production, multi-framework agents       | Core modules 02–07 (RAG + agents + serving) | Chat provider (Ollama free path); paid keys for 17/18    | A deployed multi-agent service with an offline eval gate   | Model training, or Core app-builder |
| Model training   | Fine-tune, align, and optimise your own models          | ML foundations route + core modules 00–04   | Hosted SFT key (13); optional GPU for local LoRA/serving | A fine-tuned + DPO-aligned model with training evidence    | Agent systems, or Core app-builder  |

---

## Route 1 — Core app-builder

**Goal:** take one person from "I vaguely know how AI apps work" to shipping a
working, evaluated, deployable RAG-and-agents application.

**This is the existing ~20-week main sequence, labelled.** It covers all 24
numbered modules (00–23) plus the three production deep dives already scheduled
into it: **07b** (delivery), **20b** (governance), and **21b** (evaluation
science) — 27 lessons in total.

- **Assumed background:** general programming. No ML/maths background required.
- **Weekly workload:** the week-by-week table below assumes ~6–8 hours most weeks
  and more for the capstone (~20–23 calendar weeks at that pace). Its exercise
  time alone is 114–153 h; budget the setup/debug, provider/cloud, and capstone
  buckets on top (see the at-a-glance table). At a lighter ~5 h/week, stretch it
  across ~30–35 weeks.
- **Selected modalities:** the modality modules (**09** vision, **10** image
  generation, **18** computer use, **19** audio) are pick-what-your-capstone-needs.
  The hour budget assumes you touch all four; if you commit to one modality,
  subtract the others' exercise-only hours (~4–6 h each).
- **Required provider/hardware:** any one provider. The **free Ollama path**
  completes the majority of modules; a few benefit from a hosted key (09/10
  vision & image APIs, 13 hosted SFT, 15 reasoning models, 17/18 tool/vision).
- **Portfolio artifact:** a deployed, tenant-aware RAG-agent app with an eval
  harness, streaming UI, and a release runbook (module 23, Option A).
- **Next route:** **Agent systems** to go deep on multi-agent production, or
  **Model training** to own the model layer.

**Companions this route intentionally excludes** (each is the spine of another
route, so nothing is lost — just deferred):

| Excluded companion(s)   | Why deferred here                                               | Route that owns it |
| ----------------------- | --------------------------------------------------------------- | ------------------ |
| 01b, 01c, 01d, 01e, 01f | Classic-ML / DL / transformer theory, not needed to ship an app | **ML foundations** |
| 05b, 06b, 06c, 06d      | Advanced RAG + agent depth (LangGraph, frameworks, memory)      | **Agent systems**  |
| 13b                     | Post-training & alignment (RLHF/DPO)                            | **Model training** |

### Core app-builder — week-by-week

| Week | Module(s)                                      | Notes                                                                          |
| ---- | ---------------------------------------------- | ------------------------------------------------------------------------------ |
| 1    | 00 Setup, 01 Fundamentals                      | Don't rush 01 — it pays dividends in every later module.                       |
| 2    | 01 Fundamentals (continued)                    | Finish all 🔴 tasks; run the tests.                                            |
| 3    | 02 LLM Integration                             | Tool calling and structured output are the most reused patterns in the course. |
| 4    | 03 Prompting & Patterns                        | Lighter module; good time to catch up.                                         |
| 5    | 04 Embeddings & Vectors                        | Budget time for Task 1 (from scratch) — it's the foundation of RAG.            |
| 6    | 05 RAG                                         | The heart of the course. Take the full week.                                   |
| 7    | 06 Agents                                      | Task 1 (ReAct from scratch) is where the most learning happens.                |
| 8    | 06 Agents (continued) + news-agent             | Build the news-agent project this week.                                        |
| 9    | 07 Advanced & Production                       | Eval harness first — you'll need it for the capstone.                          |
| 10   | 07b Delivery & Service Operations              | Containerise, add identity/tenant boundaries, and write the release runbook.   |
| 11   | 08 Classification                              | Lighter module; good recovery week.                                            |
| 12   | 09 Computer Vision, 10 Image Generation        | Choose one modality first; do both only if you have time.                      |
| 13   | 11 Document Ingestion, 12 Text-to-SQL          | Two focused modules; no heavy prerequisites beyond 05.                         |
| 14   | 13 Fine-tuning                                 | Budget the hosted task; local LoRA is optional and heavy.                      |
| 15   | 14 Local Inference & Optimization              | Mostly Ollama-based; Task 5 (KV cache) is the 🔴 payoff.                       |
| 16   | 15 Reasoning & Test-time Compute               | Needs an o-series or extended-thinking key for full experience.                |
| 17   | 16 Context Engineering, 17 MCP                 | Context budgeting + modern agent APIs — directly useful for the capstone.      |
| 18   | 18 Computer Use, 19 Audio & Speech             | More specialised; select the modality your capstone needs.                     |
| 19   | 20 AI Security                                 | Essential before production work.                                              |
| 20   | 20b Governance, Privacy & Responsible Practice | Data map, rights workflow, model/data card, and user recourse.                 |
| 21   | 21 LLMOps & Eval                               | Versioned metrics, review queue, and monitoring.                               |
| 22   | 21b Evaluation Science, 22 Product UX          | Add held-out evidence and trajectory tests; surface trustworthy UX.            |
| 23   | 23 Capstone                                    | Build M1–M3 first, then M4–M6; the full week is a minimum.                     |

**Pacing variants.** _Fast / app-only:_ do 🟢 tasks only (skip the 🔴 from-scratch
tasks in 01, 04, 06, 08, 10, 13, 14, 20), treat 13's local LoRA and 19's mic mode
as optional, and compress to ~10–14 intensive weeks — this trims exercise-only
hours toward the low end. _Deep / from-scratch:_ do every 🔴 task, add the "Going
deeper" references, write tests for every implementation, and take the exercise
budget toward its high end over ~30+ weeks.

---

## Route 2 — ML foundations

**Goal:** build the classic-ML, deep-learning, and transformer machinery by hand
— the theory AI/ML interviews probe and the course's LLM modules otherwise
assume. Five pure-from-scratch companions (**01b, 01c, 01d, 01e, 01f**).

- **Assumed background:** Module 01 (the toy tokenizer/attention head), comfort
  with NumPy, and first-year calculus/linear algebra.
- **Required provider/hardware:** **none.** Every task is offline, seeded, and
  deterministic — pure NumPy (Python) and plain TypeScript, no provider, no
  network, no ML framework. This is why the provider/cloud and capstone buckets
  are 0.
- **Time budget:** 22–32 h exercise-only plus 6–11 h reading/debug (see the
  at-a-glance table).
- **Prerequisite order** (each companion states its own prereqs):

  1. **01b** Classic ML Foundations — regression, bias–variance, ridge, CV,
     ROC/AUC, k-means. _(needs 01)_
  2. **01e** Trees & Ensembles — CART, random forests, gradient boosting.
     _(needs 01b)_
  3. **01f** Probability, Statistics & PCA — Bayes/naive Bayes, MLE↔cross-entropy,
     A/B tests, PCA. _(needs 01; 01b helps)_
  4. **01c** Deep Learning Essentials — autograd/backprop, optimizers, init,
     regularisation, RNN+BPTT. _(needs 01; 01b helps)_
  5. **01d** Transformer Architecture — multi-head attention + masking, positional
     encoding, pre-LN blocks, KV cache, BERT-vs-GPT. _(needs 01; 01c helps)_

  01e and 01f are independent of the 01c→01d deep-learning line; do them right
  after 01b or interleave. **Practice checkpoints:** each companion's "Done when"
  checklist is the checkpoint — clear it (grad-checks, monotone losses,
  bias²+variance reconciliation, cached==naive logits) before moving on.

- **Portfolio artifact:** a from-scratch ML repository — linear/logistic
  regression, an autograd engine training an MLP, trees + boosting, PCA, and a
  GPT-style decoder block with a KV cache — each verified against a numerical
  check.
- **Next route:** **Model training** (which assumes this maths), or **Agent
  systems** if you want to build rather than train.

---

## Route 3 — Agent systems

**Goal:** go from a from-scratch ReAct loop to a production, multi-framework,
memory-aware agent service that ships behind a release gate. Twelve lessons:
**05b** (advanced RAG), **06 / 06b / 06c / 06d** (agents, LangGraph, frameworks,
memory), **16** (context engineering), **17** (MCP), **18** (computer use),
**21 / 21b** (evaluation & agent reliability), **07b** (delivery), and **23**
(capstone).

- **Assumed background:** the Core app-builder route through module 07 — you need
  **02–05** (integration + RAG) before 06, and **07** (eval harness,
  observability, serving) before 07b/21. Those live in Core and are the assumed
  prerequisites, not re-counted here.
- **Dependencies within the route:** 05b needs 05; 06b/06c/06d each need 06;
  17 needs 02+06; 18 needs 06+09; 21 needs 05–07; 21b needs 05+06+21; 07b needs
  07; 23 needs everything. Suggested order: **06 → 06b → 06c → 06d → 05b → 16 →
  17 → 18 → 21 → 21b → 07b → 23**.
- **Required provider/hardware:** a chat provider — the **free Ollama path** runs
  06's from-scratch loop and the `--stub` offline tasks in 06c/06d. Native tool
  calling (06 Task 2), MCP (17), and computer-use vision (18) want an
  OpenAI/Anthropic key; 07b/23 add a deploy target.
- **Time budget:** 55–74 h exercise-only, 14.5–25.5 h setup/debug, 4.75–9.5 h
  provider/cloud, plus the 10–20 h capstone.
- **Portfolio artifact:** a deployed multi-agent service (supervisor + workers +
  tools over MCP, bounded memory, human-in-the-loop approval) with a deterministic
  offline trajectory/safety suite as its release gate.
- **Next route:** **Model training** to own the model layer, or back to **Core
  app-builder** to fill in any skipped modality/production modules.

---

## Route 4 — Model training

**Goal:** own the model layer — decide when to train, run a hosted fine-tune,
implement LoRA and DPO from scratch, and optimise local inference. Five lessons:
**08** (classification), **13** (fine-tuning), **13b** (post-training &
alignment), **14** (local inference), **15** (reasoning & test-time compute).

- **Assumed background:** the **ML foundations** route (01b–01f) is the
  prerequisite — 13b's reward model, RLHF, and DPO build directly on that maths —
  plus core modules **00–04** for provider access and embeddings. These are cited
  prerequisites, not re-counted in this route's hours.
- **Required provider/hardware:**
  - **Hosted:** an `OPENAI_API_KEY` for the hosted SFT job (13 Task 2) and o-series
    reasoning (15); this is the reason the provider/cloud bucket is nonzero.
  - **Local (optional, heavy):** a GPU for LoRA/QLoRA (13 Task 3, `--extra
finetune`) and llama.cpp/quantised serving (14). The from-scratch tasks
    (13 LoRA math, 13b RLHF/DPO, 14 KV cache) run offline on CPU with no GPU.
- **Time budget:** 20–28 h exercise-only, 4.5–9 h setup/debug, 2.25–4.5 h
  provider/cloud, no capstone.
- **Portfolio artifact:** a fine-tuned model compared against its base with
  train/val curves, a from-scratch LoRA equivalence check, a quantization
  size/speed/quality benchmark, and a DPO-aligned toy policy with a reward-hacking
  demo.
- **Next route:** **Agent systems** to put a trained model to work, or **Core
  app-builder** to ship it in a product.

---

## Glossary

**Attention** — the mechanism by which a transformer lets each token attend to
all other tokens. Computed as `softmax(QKᵀ/√dₖ)V`. The weights tell you which
tokens each position "looks at" to build its representation.

**Approval gate** — a UX and safety pattern in which a risky AI-triggered action
(sending email, deleting data, making a payment) is paused and requires explicit
human confirmation before execution. A one-time token is issued at request time
and consumed at approval time. Essential for agentic systems with side effects.

**ANN (Approximate Nearest Neighbour)** — an algorithm (e.g. HNSW) that finds
the closest vectors to a query without comparing against every vector in the
index. Fast enough for millions of vectors at the cost of occasionally missing
the true nearest neighbour.

**Agent** — a loop where an LLM decides what to do, a tool executes, the result
feeds back as an observation, and the LLM decides again until done.

**Agent loop** — the repeating cycle a harness runs within one agent turn:
assemble context (system prompt, history, memory, tool outputs) → invoke the
model to decide → act (tool call, answer, state write) → append the trace and
repeat until a stop condition ends the run. Exists because long-horizon tasks
can't complete in a single forward pass. Built from scratch in module 06;
hardened (stop conditions, stuck detection, idempotency) in module 06 Task 6.

**A/B test** — comparing two variants on live traffic and using a statistical
test (e.g. a two-proportion z-test) to decide whether the observed difference is
real or noise. Requires understanding p-values, confidence intervals, power, and
the multiple-testing trap. Built from scratch in module 01f.

**Bagging vs boosting** — the two ways to combine many weak models. Bagging
(random forests) trains trees independently on bootstrap resamples and averages
them — it reduces _variance_. Boosting (gradient boosting, XGBoost) trains
learners sequentially, each fitting the previous ensemble's residuals — it
reduces _bias_. Module 01e builds both from scratch.

**BPE (Byte-Pair Encoding)** — the tokenization algorithm used by most modern
LLMs. Starts from characters or bytes and repeatedly merges the most frequent
adjacent pair into a new token. Handles rare words gracefully without an
out-of-vocabulary problem.

**Calibration** — how well a classifier's scores behave as probabilities: among
samples given `p = 0.8`, about 80 % should actually be positive. Neural nets are
typically overconfident; fix post-hoc with Platt or temperature scaling. See
module 08's interview notes.

**Chunk** — a segment of a larger document produced by a chunker. Smaller chunks
give more precise retrieval; larger chunks give more context per result. Structure-aware
chunkers split on heading boundaries rather than arbitrary character counts.

**CLIP** — a multimodal model trained to align images and text in a shared
embedding space. Enables zero-shot image classification by comparing image
embeddings to text-label embeddings.

**Computer use** — the capability of an LLM agent to control a GUI (browser,
OS desktop) by taking screenshots, classifying visual state, and emitting
structured actions (clicks, keypresses). Anthropic's computer-use beta adds
`computer_20241022`, `bash_20241022`, and `text_editor_20241022` tool types.

**Context window** — the maximum total tokens (input + output) a model can
process in one call. Exceeding it causes truncation or an error. Context-window
budget management (counting, truncation, compaction, caching) is the subject of
module 16.

**Context window budget** — the discipline of tracking how many tokens each part
of a prompt costs (system, documents, history, tools) and applying truncation or
compaction strategies before exceeding the model's limit.

**Continual learning** — a model acquiring new knowledge from a stream of data
over time without full retraining and without catastrophic forgetting. The
bridge between the agent loop (which generates experience as memory) and the
training loop (which bakes experience into weights): in-session "learning" is
retrieval, not weight updates. See module 06's interview notes and module 13b.

**Continuous batching** — iteration-level scheduling in LLM serving engines
(vLLM, TGI): finished sequences leave the batch after every decode step and
queued requests join immediately, keeping the GPU full. The biggest single
throughput win in production serving. See module 14's interview notes.

**Cosine similarity** — `dot(a, b) / (|a| × |b|)`. Measures the angle between
two vectors regardless of their magnitude. The standard distance metric for
embedding retrieval.

**Decision tree (CART)** — a classifier/regressor built by greedily choosing the
feature-threshold split that most reduces impurity (Gini), recursing until a
depth or leaf-size limit. Interpretable, fast, and the building block of random
forests and gradient boosting. Built from scratch in module 01e.

**Diffusion** — the class of generative model that learns to reverse a noising
process. During training, noise is added to images in steps (forward process);
the model learns to denoise (reverse process). Used in Stable Diffusion.

**Diarisation (speaker diarisation)** — the task of segmenting an audio stream
by speaker identity ("who spoke when?") without knowing the speakers in advance.
Used to produce per-speaker transcripts from multi-person recordings.

**Distillation (knowledge distillation)** — training a smaller "student" model
to mimic the output distribution of a larger "teacher" model. Reduces model size
and inference cost while preserving most of the teacher's quality. Used in models
like Stable Video Diffusion Turbo and many quantised LLMs.

**Document ingestion** — the pipeline that converts raw documents (PDF, HTML,
Markdown, DOCX) into clean, structured text chunks ready for embedding and
retrieval. The real engineering work of a RAG project: ~80 % of quality depends
on ingestion, not the LLM.

**DPO (Direct Preference Optimization)** — preference tuning that skips the
reward model and RL loop: the RLHF objective's closed-form optimal policy is
inverted so the LM's own log-probability ratios act as the implicit reward, and
a Bradley–Terry loss is applied directly to (chosen, rejected) pairs. Built from
scratch in module 13b.

**Drift** — production degradation with no code change. Data drift: the input
distribution moves. Concept drift: the correct answer moves (stale corpus).
Upstream drift: a hosted provider silently changes the model behind an alias.
Detect by comparing reference vs live windows (PSI, KS test, embedding
distance). See module 21's interview notes.

**Embedding** — a fixed-length vector of floats representing the meaning of a
text (or image). Semantically similar inputs land near each other in the vector
space.

**Encoder-only vs decoder-only** — same transformer blocks, different mask and
training objective. Encoder-only (BERT): bidirectional attention + masked-LM →
representations/embeddings, can't generate. Decoder-only (GPT): causal mask +
next-token prediction → generation. Encoder–decoder (T5) bolts both together.
Module 01d Task 5 demonstrates the difference concretely.

**Eval gate** — a CI step (script that exits non-zero) that blocks merging or
deploying if a quality metric falls below a threshold. Equivalent to a unit test
but for LLM output quality. See module 21.

**F1 score** — the harmonic mean of precision and recall: `2 × P × R / (P + R)`.
Useful when classes are imbalanced and you care about both false positives and
false negatives.

**Fine-tuning** — training a pretrained model on a smaller, task-specific
dataset to adapt its behaviour. More expensive than prompting but can achieve
higher accuracy on narrow tasks.

**Hallucination** — when an LLM generates plausible-sounding but factually
incorrect content not grounded in the provided context.

**HNSW (Hierarchical Navigable Small World)** — the ANN algorithm used by most
production vector databases (Chroma, Qdrant, Weaviate). Builds a multi-layer
graph that enables sub-linear search time.

**Hybrid search** — combining dense (embedding) retrieval with sparse (BM25 /
keyword) retrieval and merging the ranked lists (e.g. via RRF). Catches both
semantic matches and exact-match queries.

**Idempotency (tool calls)** — assigning each side-effecting tool call a stable
key before execution so a retry after a transient failure (network error, rate
limit) is deduplicated instead of firing twice (double email, double payment).
Harness-level engineering, not model-level. Module 06 Task 6.

**KV cache** — in autoregressive generation, a cache of key (K) and value (V)
matrices for all past tokens. Avoids re-computing attention over the full history
at each step, reducing per-token cost from O(n) to O(1) in the attention layer.
The price: KV cache memory grows with sequence length and is the main reason
long-context inference is expensive.

**LLM-as-judge** — using an LLM to evaluate another LLM's output. The judge is
prompted to rate faithfulness, relevance, or quality on a scale. Cheaper than
human annotation; calibration is important.

**LLMOps** — the operational discipline around deploying and maintaining LLM
systems: versioned eval sets, regression gates, experiment tracking, human review
queues, production monitoring, and cost control. Covered in module 21.

**LoRA (Low-Rank Adaptation)** — a parameter-efficient fine-tuning technique
that freezes the base model and adds a small number of trainable low-rank
matrices (ΔW = B·A, rank r ≪ d). Enables fine-tuning on consumer hardware at
~100× fewer parameters than full fine-tuning.

**Logistic regression** — a linear classifier that applies softmax to a linear
transformation of the input. Trainable with gradient descent. When the input is
an embedding, it produces a strong baseline classifier.

**MCP (Model Context Protocol)** — an open standard (Anthropic, 2024) for
exposing tools, resources, and prompts to any LLM application. A single MCP
server is instantly usable by any MCP client (Claude Code, OpenAI Responses API,
LangGraph, etc.). Runs over stdio (subprocess) or HTTP/SSE (remote/multi-client).

**Memory-aware agent** — an agent whose harness actively manages its cognitive
state — encode, store, retrieve, inject, forget — across memory types (episodic
history, semantic knowledge, procedural workflows, entities, summaries), as
opposed to a merely memory-augmented agent that only has context injected into
it. The subject of module 06d.

**MLE (Maximum Likelihood Estimation)** — pick the parameters that maximize the
probability of the observed data. Minimizing cross-entropy _is_ MLE under a
Bernoulli/categorical model, and minimizing MSE is MLE under Gaussian noise —
the reason those losses are the defaults. Module 01f makes the link concrete.

**MoE (Mixture of Experts)** — a transformer variant where each FFN is replaced
by E expert FFNs plus a router that activates only the top-k per token, so total
parameters (capacity) grow without growing per-token FLOPs. Mixtral 8×7B: ~47 B
total, ~13 B active. See module 01d's interview notes.

**Multimodal** — a model or application that processes more than one modality
(e.g. text + images). GPT-4o and Claude 3+ are multimodal LLMs.

**NDCG (Normalized Discounted Cumulative Gain)** — retrieval metric for graded
relevance: gains are discounted by `1/log₂(rank+1)` and normalized by the ideal
ordering. Use recall@k to tune the retriever, MRR when one good chunk is enough,
NDCG when relevance is graded. See module 05's retrieval-metrics notes.

**OWASP LLM Top 10** — a community-maintained list of the ten most critical
security risks specific to LLM-integrated applications. Key entries include
Prompt Injection (LLM01), Excessive Agency (LLM08), and Sensitive Information
Disclosure (LLM06). The 2025 edition is the current reference; see module 20.

**PagedAttention** — vLLM's virtual-memory trick for the KV cache: split it into
fixed-size blocks with a per-request block table, allocate on demand, share
blocks across requests with a common prefix. Cuts cache waste from ~60–80 % to
<4 %, enabling the large batches continuous batching needs. See module 14's
interview notes.

**PCA (Principal Component Analysis)** — dimensionality reduction by projecting
data onto the top eigenvectors of its covariance matrix (the directions of
maximum variance). Used to visualise embeddings in 2-D and to de-noise features.
Built from scratch in module 01f.

**Prompt caching** — a provider feature that stores the KV cache of a long
repeated prefix (system prompt, large document, tool definitions) so subsequent
calls re-use it at a fraction of the normal input token cost. Anthropic uses
explicit `cache_control` breakpoints; OpenAI caches automatically for inputs

> 1024 tokens.

**Prompt injection** — an attack where malicious content in the input (e.g. a
retrieved document, a web page) overrides the system prompt or tricks the model
into unintended behaviour. Direct injection targets the user message; indirect
injection hides instructions in retrieved content.

**Quantization** — reducing the numerical precision of a model's weights (e.g.
from 32-bit float to 4-bit integer). Dramatically reduces memory usage at a
small quality cost. Makes large models runnable on consumer hardware. GGUF is
the common quantised format for llama.cpp/Ollama.

**RAG (Retrieval-Augmented Generation)** — the pattern of retrieving relevant
passages from a knowledge base and including them in the LLM's context so it
can answer with grounded, cited information rather than hallucinating.

**ReAct** — a prompting pattern (Reason + Act) where the model emits structured
`Thought / Action / Action Input` lines that the agent loop parses to decide
which tool to call.

**Reasoning model** — a class of LLM (e.g. OpenAI o1/o3/o4, Anthropic extended
thinking) that allocates extra compute to internal deliberation before producing
a visible answer. Higher accuracy on hard multi-step problems at higher latency
and cost. See module 15.

**Reranking** — a second retrieval stage that takes the top-k candidates from
a fast retriever and scores them with a more accurate but slower model
(cross-encoder or LLM). Improves precision without sacrificing recall.

**Responses API** — OpenAI's agent-platform API (January 2025) that adds
response chaining via `previous_response_id`, hosted tools (web_search,
code_interpreter, file_search), and a remote MCP connector. Covered in module 17.

**Reward model** — a model trained on pairwise human preferences (Bradley–Terry:
`P(a ≻ b) = σ(r_a − r_b)`) to score responses, standing in for the human during
RLHF. Imperfect by construction — optimizing hard against it causes reward
hacking (Goodhart's law), which is why RLHF keeps a KL leash to the reference
policy. Built from scratch in module 13b.

**RLHF (Reinforcement Learning from Human Feedback)** — the post-training stage
that turns an SFT model into an aligned assistant: collect preference pairs,
train a reward model, then optimize the policy with RL (PPO in production)
against `reward − β·KL(π‖π_ref)`. The pipeline behind ChatGPT-style models;
module 13b builds a toy version end to end, reward hacking included.

**Scaling laws** — empirical power laws relating loss to parameters, data, and
compute (Kaplan et al.); Chinchilla showed compute-optimal training wants ~20
tokens per parameter, and modern models deliberately overtrain past that because
inference cost dominates. See module 01d's interview notes.

**Semantic tool discovery** — indexing tool definitions in a vector store
(embedding LLM-augmented descriptions, not just signatures) and passing only the
top-k relevant schemas to the model per query, instead of enumerating every
tool. Fixes tool-schema overload: selection accuracy drops and token cost climbs
as the schema list grows. Module 17 Task 6.

**Speculative decoding** — a small draft model proposes k tokens, the target
model verifies them in one parallel forward pass, and a rejection-sampling rule
keeps the output distribution exactly the target's. Lossless 2–3× decode
speedup. See module 14's interview notes.

**Streaming UX** — the product pattern of displaying LLM output token-by-token
as it is generated, rather than waiting for the complete response. Dramatically
reduces perceived latency. Implemented via Server-Sent Events (SSE) or WebSockets.
See module 22.

**Temperature** — a sampling parameter that divides logits before softmax.
`T < 1` makes output more deterministic; `T > 1` makes it more random.
`T = 0` is approximately greedy.

**Test-time compute** — spending extra computation at inference time (before or
during the answer) to improve correctness: chain-of-thought, self-consistency,
best-of-N sampling, self-refine loops, or full reasoning-model deliberation.
See module 15.

**Text-to-SQL** — the task of converting a natural-language question into a
valid SQL query given a database schema. Requires schema-grounded prompting,
safety validation (read-only whitelist, stacked-query rejection), and self-repair
on execution errors. Covered in module 12.

**Token** — the basic unit a language model processes. Typically a sub-word
chunk; common words are one token, rare words may be several. Cost and context
window are measured in tokens.

**Tool calling** — the mechanism by which an LLM requests the execution of an
external function. The model returns a structured call (name + arguments); the
host executes it and returns the result as a new message.

**Tool-output offloading** — persisting a bulky tool result to a log store and
injecting only a one-line reference (`[Tool Log #id] …`) plus a `read_tool_log`
tool into context, so later loop iterations stop re-carrying thousands of stale
tokens. Keeps agent-loop context flat instead of monotonically growing. Module
16 Task 6.

**Top-p (nucleus sampling)** — keep the smallest set of tokens whose cumulative
probability ≥ p, renormalise, and sample. Adapts the cutoff to the distribution
shape dynamically.

**VAD (Voice Activity Detection)** — the signal-processing task of classifying
which frames of an audio stream contain speech vs. silence. An energy-based
baseline computes RMS per frame and thresholds against peak energy. More
sophisticated approaches (WebRTC VAD, Silero) use GMM or LSTM models.

**Vector DB** — a database optimised for storing and querying high-dimensional
vectors via ANN search, with support for persistence, metadata filtering, and
multi-tenancy. Examples: Chroma, Qdrant, Weaviate, Pinecone.
