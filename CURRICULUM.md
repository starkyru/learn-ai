# Curriculum — learn-ai

A detailed study plan for the full course. The module READMEs are the primary
source of truth for tasks and acceptance criteria; this document is the map.

---

## How to use this course

1. Read the module README before writing any code. It explains the *why*.
2. Do the 🟢 app task first. Get something working. Then come back for 🟡/🔴.
3. Run against two providers and notice what changes. The provider abstraction
   is a deliberate teaching tool — understand where it holds and where it leaks.
4. Use the `/tutor` CLI at any point to ask questions or run a graded exam on
   the module you just finished (see the Applied Projects section below).
5. Treat the "Done when" checklist as your definition of done — not the last
   line of code you write.

### Depth legend

| Tag | What it means |
|-----|---------------|
| 🟢 App | Use the ecosystem to build something that works. Every module has at least one. |
| 🟡 Balanced | Build the app AND implement one core piece by hand for intuition. |
| 🔴 Deep | Implement the machinery from scratch — no obvious library allowed. Where the real understanding lives. |

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
  standard, and why Anthropic needs its own adapter.
- Run a prompt against two different providers using the shared `get_provider()`
  abstraction.
- Watch streaming tokens arrive and understand time-to-first-token (TTFT).

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Hello, LLM | 🟢 | Run `hello.py` / `hello.ts` against two providers; see answer, model id, and token count. |
| 2 | Compare providers | 🟢 | Run `compare_providers` to send the same prompt to all four providers simultaneously; skips missing ones cleanly. |
| 3 | Streaming | 🟢 | Watch `streaming.py` / `streaming.ts` emit tokens progressively via `chat_stream()`. |

**Estimated time:** 1–2 hours

**Done when**

- [ ] `hello` ran against at least two providers; you saw answer + model + tokens.
- [ ] `compare_providers` runs cleanly even with some providers missing.
- [ ] `streaming` printed tokens incrementally.
- [ ] You can explain why one `OpenAICompatibleProvider` covers three vendors.

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | BPE tokenizer | 🔴 | Implement BPE train + encode + decode; `decode(encode(s)) == s` must hold. (Worked example to study.) |
| 2 | Cosine similarity | 🟡 | Implement cosine by hand and rank real embeddings from `provider.embed()`; similar sentences score higher. |
| 3 | Attention head | 🔴 | Fill in `softmax(QKᵀ/√dₖ)V` in `attention.py` / `attention.ts`; weight rows must sum to 1. |
| 4 | Samplers | 🔴 | Implement greedy, temperature, top-k, top-p in `sampling.py` / `sampling.ts`. |
| 5 | Bigram model | 🟡 | Build a count-based bigram predictor; observe that it is a (bad) language model. |

**Estimated time:** 4–6 hours (budget more if 🔴 tasks are new to you)

**Done when**

- [ ] `decode(encode(s)) == s` passes in Python and TypeScript.
- [ ] Cosine ranking puts same-topic sentences above unrelated ones.
- [ ] Attention weights' rows each sum to 1.
- [ ] Greedy/temperature/top-k/top-p behave as described.
- [ ] You can explain in one sentence each: token, embedding, attention, sampling.
- [ ] `pytest test_fundamentals.py` and `jest bpe.test.ts` pass.

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Chat & system prompts | 🟢 | Build a multi-turn REPL; history grows per turn; model stays in character with your system prompt. |
| 2 | Streaming | 🟢 | Implement streaming output with TTFT and words/second stats. |
| 3 | Tokens & cost | 🟡 | Count tokens via tiktoken; build a cost estimator; compare estimate to provider's reported usage. |
| 4 | Structured output | 🟢 | Extract a `Recipe` object from free text; validate with Pydantic / Zod; retry on parse failure. |
| 5 | Tool / function calling | 🟢 | Implement the tool loop directly against the OpenAI and Anthropic SDKs (below llm_core). |
| 6 | Retries & errors | 🟡 | Implement exponential backoff with jitter; never retry 401/400 errors. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Templates & roles | 🟢 | Build a `render_template` helper; summarise and classify with system/user roles. |
| 2 | Few-shot vs zero-shot | 🟡 | Compare 0-, 1-, 3-shot on a classification task; print accuracy table. |
| 3 | Chain-of-thought & self-consistency | 🟡 | Add CoT to math/logic tasks; sample N paths, majority-vote; compare to single-sample accuracy. |
| 4 | Output parsing & guardrails | 🟢 | Implement the repair loop: on parse failure append error + correction and retry. |
| 5 | Prompt eval harness | 🟡 | Run two prompt variants on `eval_dataset.json`; print ranked comparison table. |

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

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Vector store from scratch | 🔴 | Implement `add()`, `_cosine_similarity()`, and `query()` with brute-force top-k. |
| 2 | Real vector DB | 🟢 | Index the corpus into Chroma; compare results and performance to Task 1. |
| 3 | Chunking strategies | 🟡 | Implement fixed-size, sentence-based, and overlapping chunkers; compare retrieval quality per strategy. |
| 4 | Hybrid search | 🟡 | Add BM25 alongside dense retrieval; implement RRF fusion; show hybrid beats either alone on exact-match queries. |

**Estimated time:** 4–6 hours

**Done when**

- [ ] `_cosine_similarity([1,0], [1,0])` returns 1.0; `([1,0], [0,1])` returns 0.0.
- [ ] Chroma indexes 8 documents and returns correct top-3 without errors.
- [ ] Each chunker returns non-empty chunks; overlapping produces at least as many as fixed-size.
- [ ] BM25-only finds exact-match docs that dense retrieval misses; hybrid catches both.

---

## Module 05 — RAG

**Prerequisites:** Module 04 complete. `uv sync --extra vectors`.

**Learning objectives**

- Build a complete retrieve → rerank → generate pipeline with inline citations.
- Implement LLM reranking and HyDE (Hypothetical Document Embeddings).
- Evaluate RAG quality: faithfulness, context relevance, and answer relevance.
- Understand the failure modes of RAG (retrieval miss, hallucination, citation drift).

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Naive RAG end-to-end | 🟢 | retrieve → generate; answer includes `[Source N]` citations. |
| 2 | Better retrieval | 🟡 | Add LLM reranking and HyDE; compare retrieval precision before/after. |
| 3 | RAG eval | 🟡 | Implement faithfulness, context-relevance, and answer-relevance LLM-as-judge scores over a test set. |
| 4 | Citations & attribution | 🟢 | Output structured JSON with per-claim citations; validate and flag invalid or missing citations. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] End-to-end RAG returns a cited answer for any question over your corpus.
- [ ] Reranking changes which top-3 chunks are used (visible in output).
- [ ] Eval script prints faithfulness / context-relevance / answer-relevance scores without manual input.
- [ ] The HNSW hallucination case scores faithfulness < 1.0 (hallucination detected).

---

## Module 06 — Agents

**Prerequisites:** Modules 02–05. `uv sync --extra agents` for LangGraph.

**Learning objectives**

- Build a ReAct agent from scratch using only `provider.chat()` and plain text parsing.
- Use native structured tool calling (OpenAI and Anthropic APIs directly).
- Add persistent scratchpad memory that survives restarts.
- Re-implement the same agent with LangGraph's state machine model.
- Build a planner-worker multi-agent architecture.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | ReAct loop from scratch | 🔴 | Implement parser, tool dispatch, and the full Thought→Action→Observation loop; works on Ollama. |
| 2 | Native tool calling | 🟢 | Re-implement with structured tool schemas; run on OpenAI and Anthropic; compare format differences. |
| 3 | Memory | 🟡 | Add a `scratchpad.json` the agent writes structured notes to; history stays within `MAX_HISTORY_TURNS`. |
| 4 | LangGraph agent | 🟢 | Re-build as a typed state machine; map each node back to your from-scratch loop. |
| 5 | Multi-agent | 🟡 | Planner decomposes a question → workers run in parallel → synthesiser combines results. |

**Estimated time:** 6–8 hours

**Done when**

- [ ] From-scratch ReAct solves a multi-step question on Ollama (Task 1).
- [ ] Native tool calling works on OpenAI and Anthropic (Task 2).
- [ ] Scratchpad persists across restarts; history is bounded (Task 3).
- [ ] LangGraph graph produces the same answer as Task 1 (Task 4).
- [ ] Multi-agent: planner JSON → workers → synthesiser (Task 5).

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | LLM-as-judge eval | 🟡 | Write a judge prompt; score responses for faithfulness and relevance; calibrate against human labels. |
| 2 | Observability / tracing | 🟢 | Wrap every LLM call to log model, tokens, latency, and cost to JSONL; display a per-request cost breakdown. |
| 3 | Caching & cost control | 🟡 | Cache responses by SHA-256 hash; hit the cache on repeated queries; print actual vs. saved cost. |
| 4 | Guardrails & safety | 🟢 | Add prompt-injection detection, PII scrubbing, and refusal detection; block or scrub before/after the model. |
| 5 | Serving | 🟢 | Expose the agent via FastAPI (Python) or Node http (TypeScript); return `answer`, `citations`, `latency_ms`; add a streaming `/chat/stream` SSE endpoint. |

**Estimated time:** 5–6 hours

**Done when**

- [ ] Eval harness prints faithfulness and relevance scores reproducibly.
- [ ] Every LLM call logs latency and token cost; total cost is summed per session.
- [ ] Cache hits skip the model call; savings are quantified.
- [ ] API returns a valid JSON response on `POST /chat`; streaming works with `curl -N`.

---

## Module 08 — Classification

**Prerequisites:** Modules 00–04 (embeddings for the embedding classifier).

**Learning objectives**

- Use LLM zero-shot prompting for text classification; understand its limits.
- Use embeddings + a classic ML classifier (logistic regression, k-NN) for classification.
- Implement softmax + gradient descent from scratch to understand the classifier training loop.
- Evaluate classifiers properly: precision, recall, F1, confusion matrix.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | LLM zero-shot / few-shot classifier | 🟢 | Classify text with a prompt; measure accuracy and per-class F1; compare zero-shot vs few-shot. |
| 2 | Embeddings + classic ML | 🟡 | Embed inputs; train a k-NN classifier; compare to zero-shot. |
| 3 | Evaluation | 🟡 | Compute precision, recall, F1, and a confusion matrix; compare classifiers on the same test set. |
| 4 | Softmax + GD from scratch | 🔴 | Implement forward pass, cross-entropy loss, and gradient descent update manually; loss must decrease. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Image classification | 🟢 | Classify images with a pretrained model; see top-5 class probabilities. |
| 2 | CLIP zero-shot | 🟢 | Classify images with CLIP using only text prompts; change the label list and watch the ranking change. |
| 3 | Multimodal LLM vision | 🟡 | Pass images to a vision-capable LLM via raw vendor SDK; ask questions; compare to CLIP. |
| 4 | Convolution from scratch | 🔴 | Implement 2D cross-correlation; apply Sobel and blur kernels; verify output matches reference. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Text-to-image | 🟢 | Generate images with varied prompts and seeds; save PNGs. |
| 2 | Prompt craft & parameter sweep | 🟡 | Sweep guidance_scale and steps; save a grid; understand negative prompts. |
| 3 | img2img & inpainting | 🟡 | Transform an input image with img2img; edit a masked region with inpainting. |
| 4 | Toy diffusion from scratch | 🔴 | Implement forward noising and DDPM reverse step in NumPy; generated 2D points should match training distribution. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] At least two PNGs from different seeds saved (Task 1).
- [ ] Parameter sweep grid saved; you can explain what guidance_scale does (Task 2).
- [ ] `img2img_output.png` and `inpaint_output.png` saved (Task 3).
- [ ] Toy diffusion generates points that look like the training distribution (Task 4).

---

## Module 11 — Document Ingestion

**Prerequisites:** Module 05 (RAG). `uv add pypdf beautifulsoup4 httpx` (Python); `pnpm install` (TypeScript — picks up pdf-parse, cheerio).

**Learning objectives**

- Parse PDF, HTML, and Markdown into normalised Document records.
- Clean and normalise extracted text: strip boilerplate, collapse whitespace, deduplicate paragraphs.
- Chunk documents by section/heading structure rather than by arbitrary character counts.
- Implement incremental indexing with a content-hash manifest to skip unchanged documents.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Parse documents | 🟢 | Extract text from PDF, HTML, and Markdown; normalise to a Document record; strip nav/footer noise from HTML. |
| 2 | Clean & normalize | 🟡 | Strip Markdown syntax, collapse whitespace, remove boilerplate lines, deduplicate near-identical paragraphs. |
| 3 | Structure-aware chunking | 🟡 | Detect ATX heading boundaries; emit one chunk per section; sub-chunk long sections; prepend heading to every sub-chunk. |
| 4 | Incremental indexing | 🟢 | Hash each document; skip unchanged ones on re-run; maintain a manifest JSON; prune stale entries. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] `parse_document()` handles `.md` and `.html` without error; HTML strips nav/footer.
- [ ] Cleaned HTML has no nav/footer text; cleaned Markdown has no `#`/`**` chars.
- [ ] Section-aware chunks carry `metadata.section` and respect heading boundaries.
- [ ] Second incremental-indexing run shows 0 new / 0 changed / N skipped.

---

## Module 12 — Text-to-SQL

**Prerequisites:** Modules 00–02. SQLite (stdlib). `pnpm install` picks up better-sqlite3 for TypeScript.

**Learning objectives**

- Generate SQL from natural-language questions with schema-grounded prompting.
- Auto-generate schema descriptions from a live database (table names, columns, sample rows, FK hints).
- Validate generated SQL for safety: read-only whitelist, stacked-query injection rejection.
- Self-repair broken SQL in a multi-turn conversation; route questions between SQL and RAG.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | NL→SQL | 🟢 | Generate SQL from a question, execute it, print the rows. |
| 2 | Schema-aware prompting | 🟡 | Auto-generate schema description from live DB; add sample rows and JOIN hints; handle multi-table questions. |
| 3 | Safety & repair | 🟡 | Validate read-only; reject stacked queries; self-repair on DB errors (up to `max_retries`). |
| 4 | Hybrid routing | 🟢 | Classify intent (sql/vector/both); dispatch to SQL or RAG accordingly; handle ambiguous questions. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Decide: prompt vs fine-tune | 🟢 | Run a narrow task through a prompt baseline and a mock fine-tuned baseline; compare formality scores. |
| 2 | Hosted SFT via OpenAI API | 🟢 | Build a 30-example JSONL dataset, upload, launch a fine-tune job, compare the fine-tuned model to the base. |
| 3 | LoRA / QLoRA locally (Python) | 🟡 | Use PEFT + transformers to add LoRA adapters to a small model; print trainable vs total parameters. |
| 4 | Dataset prep & overfitting eval | 🟡 | Clean examples, split train/val/test, track val score separately from train score, flag overfitting. |
| 5 | Understand LoRA from scratch | 🔴 | Implement `B@A` low-rank update in numpy/plain arrays; verify equivalence; print param savings table. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] `01_decide` / `01-decide` runs and prints a comparison table (Task 1).
- [ ] Valid JSONL file written and fine-tune job submitted (Task 2).
- [ ] Trainable parameter count < 1 % of total (Task 3, with finetune extra).
- [ ] Train vs val score table printed with overfitting signal (Task 4).
- [ ] Equivalence check passes; param savings table correct (Task 5).

---

## Module 14 — Local Inference & Optimization

**Prerequisites:** Module 00 (Ollama). No extra deps for default path; `uv sync --extra llama-cpp` optional.

**Learning objectives**

- Measure tokens per second on local models; understand the throughput vs. latency tradeoff.
- Compare quantization levels (fp16 vs Q4) for size, speed, and quality.
- Measure TTFT with streaming and aggregate throughput with concurrent requests.
- Understand KV caching by implementing a toy cached vs. uncached autoregressive loop.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Run local models and measure tokens/sec | 🟢 | Benchmark Ollama; print min/max/mean tokens/sec; print engine guide table. |
| 2 | Quantization: size vs speed vs quality | 🟡 | Compare two quantization levels; measure speed and LLM-judge quality; print comparison table. |
| 3 | Throughput vs latency: batching | 🟡 | Measure TTFT via streaming; fire N concurrent requests; show aggregate throughput > sequential. |
| 4 | Serving engines: pick by use case | 🟢 | Implement `recommend_engine()`; print four-engine comparison table; run same prompt against available engines. |
| 5 | KV cache intuition | 🔴 | Implement cached vs uncached toy autoregressive loop; measure speedup; verify O(n) vs O(n²) key computations. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] `01_run_local` / `01-run-local` runs against Ollama and prints tokens/sec.
- [ ] Quantization comparison table printed with measured speed numbers (Task 2).
- [ ] Concurrent throughput measurably higher than sequential (Task 3).
- [ ] KV cache: cached key computations = N; uncached = N*(N+1)/2 (Task 5).

---

## Module 15 — Reasoning & Test-time Compute

**Prerequisites:** Modules 00–03. `OPENAI_API_KEY` (o4-mini) and/or `ANTHROPIC_API_KEY` (extended thinking).

**Learning objectives**

- Compare a standard model to a reasoning model on hard multi-step problems.
- Implement self-consistency (sample N CoT paths, majority-vote) and best-of-N with a verifier.
- Build a draft → critique → revise self-refine loop.
- Plot the cost/accuracy curve and identify the accuracy-per-dollar sweet spot.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Reasoning vs standard model | 🟢 | Side-by-side comparison table: model, answer, tokens, latency for the same hard problems. |
| 2 | Test-time compute without a reasoning model | 🟡 | Implement self-consistency and best-of-N with a verifier; show accuracy rising with N. |
| 3 | Self-refine / reflection | 🟡 | Implement draft → critique → revise loop; run 2 iterations; observe concrete improvement. |
| 4 | Cost / latency of reasoning strategies | 🟢 | Measure all strategies; print table sorted by cost; annotate the sweet spot. |

**Estimated time:** 3–5 hours

**Done when**

- [ ] Side-by-side table comparing standard vs. reasoning model on ≥ 2 problems (Task 1).
- [ ] Self-consistency and best-of-N show accuracy rising with N (Task 2).
- [ ] Self-refine loop runs 2 iterations; revision is concretely better (Task 3).
- [ ] Cost/latency table covers all strategies; sweet spot annotated (Task 4).

---

## Module 16 — Context Engineering

**Prerequisites:** Modules 00–02. `uv sync --extra context` (tiktoken). `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` for caching/batch tasks.

**Learning objectives**

- Count tokens precisely with tiktoken; enforce token budgets with three truncation strategies.
- Use provider prompt caching (Anthropic `cache_control`, OpenAI automatic) to cut cost on repeated prefixes.
- Compact long conversations with a running summary to prevent context overflow.
- Apply map-reduce and refine over documents too large for a single call; demonstrate "lost in the middle".
- Submit batch requests at 50 % cost via the OpenAI or Anthropic Batch API.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Token budgeting | 🟢 | Count tokens; implement head/tail/middle-out truncation; print results table. |
| 2 | Prompt caching | 🟢 | Make repeated calls with a large prefix; observe cache hits in `usage`; measure cost saving. |
| 3 | Conversation memory / compaction | 🟡 | Summarise oldest turns when budget exceeded; verify compaction fires and context stays in budget. |
| 4 | Long-context strategies | 🟡 | Implement map-reduce and refine over chunked document; demonstrate lost-in-the-middle recall. |
| 5 | Batch API | 🟢 | Submit 5 requests via Batch API; poll until complete; print results and estimated savings. |

**Estimated time:** 4–5 hours

**Done when**

- [ ] `count_tokens` uses tiktoken; all three truncation strategies print a results table (Task 1).
- [ ] Second call shows a non-zero cache hit and lower estimated cost (Task 2).
- [ ] Compaction fires; context stays within budget; coherence preserved (Task 3).
- [ ] Map-reduce and refine both produce answers; lost-in-the-middle demonstrated (Task 4).
- [ ] Batch job completes; results printed; cost savings calculated (Task 5).

---

## Module 17 — MCP & Modern Agent APIs

**Prerequisites:** Modules 02, 06. `uv sync --extra mcp`. `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.

**Learning objectives**

- Use the OpenAI Responses API (response chaining, hosted tools) and Anthropic tool use SDK.
- Connect an MCP client to an existing server via stdio; discover and call tools.
- Build an MCP server that exposes `search_docs`, `read_module`, and `run_exam_question`.
- Wire MCP tools into an agent loop that dynamically fetches schemas at runtime.
- Expose an MCP server over HTTP/SSE and understand its security implications.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Modern agent APIs | 🟢 | Use OpenAI Responses API and Anthropic tool use to answer a two-part question; compare to module 06 manual loop. |
| 2 | Use an MCP server | 🟢 | Connect client to an existing server via stdio; list tools; call one tool. |
| 3 | Build the course MCP server | 🟢 | Build stdio MCP server with `search_docs`, `read_module`, `run_exam_question`; all three tools work when tested. |
| 4 | Wire MCP tools into an agent | 🟡 | Fetch tool schemas dynamically from the course server; run OpenAI and Anthropic agent loops using MCP tools. |
| 5 | Remote MCP + security | 🟡 | Expose the server over HTTP/SSE; add bearer-token auth; explain five security threats. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Both OpenAI Responses API and Anthropic correctly answer a two-part question with tools (Task 1).
- [ ] Task 2 client connects to an existing server, lists tools, calls one.
- [ ] Task 3 server's three tools work when tested with the Task 2 client.
- [ ] Task 4 agent answers course-related questions using dynamically fetched MCP schemas.
- [ ] Task 5 server reachable over HTTP/SSE; client lists and calls tools over the network.

---

## Module 18 — Computer Use

**Prerequisites:** Modules 06, 09. `uv sync --extra browser` + `uv run playwright install chromium`. `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for vision tasks.

**Learning objectives**

- Drive a headless Chromium browser with Playwright: navigate, read content, take screenshots.
- Build a vision-grounded browser agent (screenshot → multimodal LLM → action → repeat).
- Build a DOM/accessibility-tree agent; compare cost and reliability to the vision agent.
- Add a safety layer: domain allowlist, risk classification, human confirmation gate, injection sanitisation.

**Tasks**

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Browser automation basics | 🟢 | Navigate to a URL; read title and text; count links; take a screenshot. |
| 2 | Vision-grounded browser agent | 🟡 | Multi-step agent using screenshots + multimodal LLM to decide actions; step PNGs saved. |
| 3 | DOM/accessibility agent | 🟡 | Same task without screenshots; use a11y tree (text); compare token cost to vision agent. |
| 4 | Computer use & safety | 🟢 | Domain allowlist, risk classification, human confirmation gate, prompt-injection sanitisation. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Speech-to-text | 🟢 | Transcribe an audio clip with hosted Whisper; optionally run faster-whisper locally. |
| 2 | Text-to-speech | 🟢 | Synthesise speech from text; save as MP3; try different voices, models, and speed. |
| 3 | Voice tutor loop | 🟡 | Chain STT → RAG over module READMEs → LLM → TTS; answer a spoken question with a spoken answer. |
| 4 | Audio preprocessing & VAD | 🟡 | Implement energy-based VAD from scratch; trim silence; optionally apply noise reduction. |
| 5 | Realtime voice | 🟢 | Run dry-run mode; explain Realtime API latency advantage; optionally implement live WebSocket session. |

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Direct prompt injection: attack then defend | 🔴 | Build a naive assistant, inject it, add layered defences; print a scorecard showing improvement. |
| 2 | Indirect injection via RAG / tools | 🔴 | Poison a retrieved document; demonstrate `<leak>` exfiltration; harden with `[UNTRUSTED]` labelling and output filter. |
| 3 | Excessive agency & approval gates | 🟡 | Over-privileged agent deletes sandbox files; least-privilege + approval gate prevents the same action. |
| 4 | Red-team harness | 🟡 | Run 8 attack prompts against a simple assistant; score with LLM judge; show score improvement after hardening. |
| 5 | Vector weaknesses + OWASP mapping | 🟢 | Demonstrate data poisoning and system-prompt leakage via cosine similarity; map all findings to OWASP LLM Top 10. |

**Estimated time:** 5–7 hours

**Done when**

- [ ] Scorecard shows naive vs hardened success rates; hardened blocks ≥ 5 of 7 attacks (Task 1).
- [ ] `<leak>` tags appear in naive RAG output; hardened version redacts them (Task 2).
- [ ] Over-privileged agent deletes all files; least-privilege + gate prevents deletion (Task 3).
- [ ] Red-team harness scorecard printed; score improves after applying defences (Task 4).
- [ ] Vector poisoning and prompt leakage demonstrated; OWASP Top 10 fully mapped (Task 5).

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Versioned eval set + graders | 🟢 | Load versioned eval set; run three grader types; write a results JSON file. |
| 2 | Experiments | 🟡 | Run two prompt-version variants; compare runs; declare a winner with numbers. |
| 3 | Regression gate in CI | 🟡 | Script exits non-zero when metric < threshold; integrate into GitHub Actions or Husky pre-push. |
| 4 | Human review + feedback loop | 🟡 | Route low-confidence outputs to a JSONL queue; label interactively; merge approved labels into eval set. |
| 5 | Production monitoring | 🟢 | Parse JSONL logs; compute p50/p95 latency, error rate, cost; print report with alerts. |

**Estimated time:** 5–6 hours

**Done when**

- [ ] All 5 eval cases scored; `results/run_*.json` written (Task 1).
- [ ] Two prompt-version runs compared; winner declared with numbers (Task 2).
- [ ] `--threshold 0.99` exits non-zero; `--threshold 0.01` exits zero (Task 3).
- [ ] Review queue written; `--merge` bumps eval set version and adds cases (Task 4).
- [ ] Demo log parsed; report printed with latency stats and alerts (Task 5).

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

| # | Task | Depth | What you do |
|---|------|-------|-------------|
| 1 | Streaming UI | 🟢 | Ask a question; watch tokens stream live; blinking cursor disappears on finish. |
| 2 | Citations + source drill-down | 🟢 | Source chips appear after every answer; clicking one opens a panel with title, URL, content. |
| 3 | Confidence + failure states | 🟡 | Render loading, error, and low-confidence states; integrate LLM-judge faithfulness as confidence score. |
| 4 | Feedback capture | 🟢 | 👍/👎 and "looks wrong" feedback stored in JSONL; confirmation message appears and disappears. |
| 5 | Approval flow for risky actions | 🟡 | Modal shows action description + payload; approve/reject both logged; expired tokens return "expired". |

**Estimated time:** 4–5 hours

**Done when**

- [ ] Tokens stream live; cursor disappears on finish (Task 1).
- [ ] Source chips appear; clicking one opens the drill-down panel (Task 2).
- [ ] Loading, error, and low-confidence states all render correctly (Task 3).
- [ ] `feedback.jsonl` grows with each rating; "looks wrong" stores the note (Task 4).
- [ ] Modal appears for risky action; approve/reject both logged; expired token returns "expired" (Task 5).

---

## Module 23 — Capstone

**Prerequisites:** All previous modules (especially 04, 05, 06, 07, 11, 20, 21, 22).

**Learning objectives**

- Integrate retrieval, document ingestion, generation, agents, security, eval, and UX into a single end-to-end application.
- Make deliberate architectural decisions and justify them against the constraints.
- Evaluate your own work honestly against a rubric that covers all six production dimensions.
- Ship something you would actually use.

**Tracks**

| Option | What you build |
|--------|----------------|
| A (recommended) | Documentation / Q&A assistant: document ingestion (11) + hybrid RAG (04/05) + agent + tools (06/17) + eval gate (07/21) + streaming UI (22) + security (20) |
| B | Research / news agent: planner + workers + synthesis + eval gate + security hardening |
| C | Multimodal assistant: vision (09) + document ingestion (11) + RAG + conversational agent + eval |

**Milestone plan (Option A)**

| Milestone | Done when |
|-----------|-----------|
| M1 — Ingest | Top-3 passages for 5 hand-crafted questions are all on-topic. Draws on modules 04, 11. |
| M2 — Hybrid retrieve + rerank | Hybrid beats dense-only MRR@5. Draws on modules 04, 05. |
| M3 — Generator with citations | 5/5 answers include a valid citation; none contradict passages. Draws on module 05. |
| M4 — Agent + tools | Agent answers a 2-hop question requiring two retrieval steps. Draws on modules 06, 17. |
| M5 — Eval harness + served API + UX | Eval pass rate ≥ 70 %; API returns `{answer, citations, latency_ms}`; streaming UI live. Draws on modules 07, 20, 21, 22. |

**Estimated time:** 10–20 hours (open-ended)

**Done when**

- [ ] A runnable app covers at least four rubric dimensions.
- [ ] Automated eval script prints a score without manual intervention.
- [ ] App uses `get_provider()` / `getProvider()` — no hardcoded vendors.
- [ ] Provider can be swapped by changing one env var.
- [ ] Self-evaluation rubric filled in with honest scores (target ≥ 15/24).

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

| File | What it teaches |
|------|-----------------|
| `pipeline.py` | Orchestration — the "outer loop" |
| `sources.py` | Retrieval from RSS / Google News |
| `agent.py` | Two-step LLM agent (rank + write) |
| `telegram_bot.py` | Integration / serving layer |
| `scheduler.py` | Production scheduling pattern |

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

## Suggested schedule

~20 weeks part-time (4–6 hours per week). Adjust to your pace.

| Week | Module(s) | Notes |
|------|-----------|-------|
| 1 | 00 Setup, 01 Fundamentals | Don't rush 01 — it pays dividends in every later module. |
| 2 | 01 Fundamentals (continued) | Finish all 🔴 tasks; run the tests. |
| 3 | 02 LLM Integration | Tool calling and structured output are the most reused patterns in the course. |
| 4 | 03 Prompting & Patterns | Lighter module; good time to catch up. |
| 5 | 04 Embeddings & Vectors | Budget time for Task 1 (from scratch) — it's the foundation of RAG. |
| 6 | 05 RAG | The heart of the course. Take the full week. |
| 7 | 06 Agents | Task 1 (ReAct from scratch) is where the most learning happens. |
| 8 | 06 Agents (continued) + news-agent | Build the news-agent project this week. |
| 9 | 07 Advanced & Production | Eval harness first — you'll need it for the capstone. |
| 10 | 08 Classification | Lighter module; good recovery week. |
| 11 | 09 Computer Vision, 10 Image Generation | Can be done in parallel if comfortable. |
| 12 | 11 Document Ingestion, 12 Text-to-SQL | Two focused modules; no heavy prerequisites beyond 05. |
| 13 | 13 Fine-tuning | Budget the OpenAI fine-tune cost (~$0.50); Task 5 (LoRA from scratch) takes the most time. |
| 14 | 14 Local Inference & Optimization | Mostly Ollama-based; Task 5 (KV cache) is the 🔴 payoff. |
| 15 | 15 Reasoning & Test-time Compute | Needs an o-series or extended-thinking key for full experience. |
| 16 | 16 Context Engineering, 17 MCP | Context budgeting + modern agent APIs — directly useful for the capstone. |
| 17 | 18 Computer Use, 19 Audio & Speech | More specialised; both are hosted-first and can be done quickly at 🟢 depth. |
| 18 | 20 AI Security | Essential before building anything production-worthy. |
| 19 | 21 LLMOps & Eval, 22 AI Product UX | The eval gate and UX patterns feed directly into the capstone. |
| 20 | 23 Capstone | Open-ended; the full week is a minimum. Build M1–M3 first, then M4–M5. |

---

## Learning-path variants

### Fast / app-only path (9–10 weeks)

Focus on 🟢 tasks only. Skip or skim 🔴 tasks.

| Week | Modules |
|------|---------|
| 1 | 00, 01 (🟢 only: BPE read-only, cosine worked) |
| 2 | 02, 03 |
| 3 | 04 (Task 2 Chroma; skip Task 1 scratch), 05 |
| 4 | 06 (Tasks 2, 4; skip Task 1 scratch) |
| 5 | 07, 08 (🟢 only) |
| 6 | 09, 10, 11 |
| 7 | 12, 13 (Tasks 1–2 only), 14 (Tasks 1, 4) |
| 8 | 15–17 (🟢 tasks only), 18, 19 (🟢 tasks) |
| 9 | 20–22 (🟢 tasks only) |
| 10 | 23 Capstone (Option A, M1–M3 only) |

Skip 🔴 tasks in modules 01, 08, 10, 13, 14, 20. Treat modules 13 (local LoRA) and 19 (mic mode) as optional.

### Deep / from-scratch path (24+ weeks)

Do every 🔴 task. Add the "Going deeper" references after each module. Write
tests for every implementation. Run the eval harnesses across two providers.
Build the capstone to ≥ 20/24 on the rubric with a CI eval gate.

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

**BPE (Byte-Pair Encoding)** — the tokenization algorithm used by most modern
LLMs. Starts from characters or bytes and repeatedly merges the most frequent
adjacent pair into a new token. Handles rare words gracefully without an
out-of-vocabulary problem.

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

**Cosine similarity** — `dot(a, b) / (|a| × |b|)`. Measures the angle between
two vectors regardless of their magnitude. The standard distance metric for
embedding retrieval.

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

**Embedding** — a fixed-length vector of floats representing the meaning of a
text (or image). Semantically similar inputs land near each other in the vector
space.

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

**Multimodal** — a model or application that processes more than one modality
(e.g. text + images). GPT-4o and Claude 3+ are multimodal LLMs.

**OWASP LLM Top 10** — a community-maintained list of the ten most critical
security risks specific to LLM-integrated applications. Key entries include
Prompt Injection (LLM01), Excessive Agency (LLM08), and Sensitive Information
Disclosure (LLM06). The 2025 edition is the current reference; see module 20.

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
