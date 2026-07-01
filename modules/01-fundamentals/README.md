# Module 01 — LLM Fundamentals

This is the load-bearing module. It's the least immediately "useful" — you won't
ship anything — but everything later (embeddings, RAG (Retrieval-Augmented Generation), agents) rests on the
intuitions you build here. Don't skip it.

By the end you'll have, **by hand**, a byte-pair-encoding tokenizer, cosine
similarity over real embeddings, and scaffolds for an attention head and four
samplers. The point isn't to reinvent these — it's that once you've written
`softmax(QKᵀ/√d)V` yourself, "attention" stops being a magic word.

---

## Concepts

### 1. Tokens & tokenization

Models don't read characters or words. They read **tokens** — integer ids drawn
from a fixed vocabulary, where each id stands for a chunk of text (often a
sub-word). `" tokenization"` might be one token; `" antidisestablishmentarianism"`
might be five. Before anything reaches the network, your text is _tokenized_
into ids; afterwards the predicted ids are _decoded_ back to text.

Why sub-words and not whole words? A whole-word vocabulary can't spell anything
it never saw (every typo, every new name = unknown). A character vocabulary
never has unknowns but makes sequences brutally long. **Byte-Pair Encoding
(BPE)** is the compromise everyone uses: start from bytes/characters, then
repeatedly merge the most frequent adjacent pair into a new token. Common words
collapse to one token; rare words gracefully fall back to pieces; nothing is
ever truly unknown because you can always drop to bytes.

This matters in practice: token count = cost and = context-window budget.
"Make it shorter" sometimes means "use fewer tokens", which isn't the same as
"fewer characters" (whitespace, casing, and rare words all cost extra).

> **Task 1 builds BPE from scratch.** You'll train merges on a tiny corpus,
> then `encode` / `decode` and round-trip text losslessly.

### 2. Embeddings & vector similarity

An **embedding** is a fixed-length vector of floats that represents a piece of
text's _meaning_. The model is trained so that texts with similar meaning land
near each other in this high-dimensional space. "How do I reset my password?"
and "I forgot my login" end up close; "the cat sat on the mat" ends up far away.

"Near" is measured by **cosine similarity** — the cosine of the angle between
two vectors, ignoring their length:

```
cos(a, b) = (a · b) / (‖a‖ · ‖b‖)
```

- `a · b` is the dot product: `Σ aᵢbᵢ`.
- `‖a‖` is the magnitude: `√(Σ aᵢ²)`.
- Result is in `[-1, 1]`: **1** = same direction (very similar), **0** =
  orthogonal (unrelated), **-1** = opposite.

We divide out the magnitudes because we care about _direction_ (meaning), not
how long the vector happens to be. This single function is the engine of
semantic search and RAG (modules 04–05).

> **Task 2 implements cosine by hand** and ranks ~6 real sentences embedded via
> `provider.embed()`, so you _see_ semantically close sentences score higher.

### 3. Attention (scaled dot-product)

Attention is how a transformer lets each token "look at" other tokens and pull
in relevant context. For each token you compute three vectors via learned
projections:

- **Q** (query): what this token is looking for.
- **K** (key): what each token offers.
- **V** (value): the actual content each token contributes.

The output for a token is a _weighted average of all the V vectors_, where the
weights come from how well this token's Q matches each token's K:

```
Attention(Q, K, V) = softmax( (Q · Kᵀ) / √dₖ ) · V
```

Step by step, for sequence length `n` and head dim `dₖ`:

1. `scores = Q @ Kᵀ` → an `n × n` matrix; `scores[i][j]` is how much token _i_
   attends to token _j_ (a raw dot product).
2. **Scale** by `1/√dₖ`. Without this, large `dₖ` makes dot products huge, which
   pushes softmax into a near one-hot regime with vanishing gradients. The √dₖ
   keeps the variance sane.
3. **softmax** each row → the weights for row _i_ are non-negative and sum to 1.
   `softmax(x)ᵢ = exp(xᵢ) / Σⱼ exp(xⱼ)`. (Subtract the row max before `exp` for
   numerical stability — same result, no overflow.)
4. `output = weights @ V` → each token's output is the attention-weighted mix of
   all value vectors.

That's _one head_. Real models run many heads in parallel (each can specialise:
syntax, coreference, etc.) and stack many layers. But the core is the four steps
above, and they're just matrix multiplies plus a softmax.

> **Task 3 is a stub.** The scaffold and TODOs are in `attention.py` /
> `attention.ts`; the math above is what you need to fill them in.

### 4. Sampling (turning logits into a token)

The model's final layer outputs a **logit** per vocabulary token — an
unnormalised score. To pick the next token you first turn logits into a
probability distribution with softmax, then _sample_ from it. How you sample
controls how "creative" vs. "focused" the output is:

- **Greedy** (argmax): always take the highest-probability token. Deterministic,
  can get repetitive/boring.
- **Temperature**: divide logits by `T` before softmax. `T < 1` sharpens the
  distribution (more confident, more deterministic); `T > 1` flattens it (more
  random, more diverse); `T → 0` approaches greedy.
- **Top-k**: keep only the `k` highest-probability tokens, renormalise, sample
  from those. Caps how far down the tail you can fall.
- **Top-p (nucleus)**: sort by probability, keep the smallest set whose
  cumulative probability ≥ `p`, renormalise, sample. Adapts the cutoff to the
  distribution's shape (a confident step keeps few tokens, an uncertain one
  keeps many).

In practice you combine them (e.g. temperature + top-p). Understanding them
demystifies the `temperature` / `top_p` knobs you'll set on every API (Application Programming Interface) call.

> **Task 4 is a stub.** Implement all four in `sampling.py` / `sampling.ts`.

### 5. What _is_ a "language model"?

Strip away the hype and a language model is one thing: **a next-token
predictor**. Given a sequence of tokens, it outputs a probability distribution
over what the next token is. Generation is just: predict a distribution → sample
one token (section 4) → append it → repeat. "Understanding", "reasoning", and
"chat" are all emergent behaviours of doing that extremely well over a huge
vocabulary and context.

The simplest possible version is a **bigram model**: count how often each token
follows each other token in a corpus, and predict the next token from those
counts alone (no neural network, no attention). It's a terrible language model —
but it's a _real_ one, and writing it makes "prediction from context" concrete.

> **Task 5** is a README exercise + an optional `bigram.py` stub. From there the
> ladder to a real transformer is just: bigger context (attention instead of
> "previous one token") + learned representations (embeddings) + many layers.

---

## How to run

**Python** (from the repo root):

```bash
uv run python modules/01-fundamentals/py/bpe.py        # Task 1 (worked)
uv run python modules/01-fundamentals/py/cosine.py     # Task 2 (worked, needs a provider for embeddings)
uv run python modules/01-fundamentals/py/attention.py  # Task 3 (stub — fill in the TODOs)
uv run python modules/01-fundamentals/py/sampling.py   # Task 4 (stub)
uv run python modules/01-fundamentals/py/bigram.py     # Task 5 (optional stub)
uv run pytest modules/01-fundamentals/py/test_fundamentals.py
```

**TypeScript** (from the repo root):

```bash
pnpm tsx modules/01-fundamentals/ts/bpe.ts
pnpm tsx modules/01-fundamentals/ts/cosine.ts
pnpm tsx modules/01-fundamentals/ts/attention.ts
pnpm tsx modules/01-fundamentals/ts/sampling.ts
pnpm tsx modules/01-fundamentals/ts/bigram.ts
pnpm jest modules/01-fundamentals/ts/bpe.test.ts
```

---

## Tasks

### Task 1 — BPE tokenizer from scratch 🔴 (WORKED)

**Goal:** implement byte-pair encoding — train merges on a small corpus, then
`encode(str) -> ids` and `decode(ids) -> str` that round-trip losslessly.

**Steps**

1. Read `bpe.py` / `bpe.ts`. Start from the **byte** level (256 base tokens) so
   _any_ input is representable — no unknown tokens, ever.
2. Follow `train`: count adjacent pairs, merge the most frequent into a new
   token id, repeat `num_merges` times, recording the merge order.
3. Trace `encode`: it applies the learned merges in the order they were learned;
   `decode`: it maps ids back to byte sequences and UTF-8-decodes.
4. Run it: print the trained vocab size, encode a sample, decode it back, and
   confirm `decode(encode(s)) == s`.
5. Read the **tiktoken comparison** section at the bottom of `bpe.py` (tiktoken
   is allowed **only** here, for comparison) and note how your token counts
   differ from a production tokenizer's.

**Acceptance:** `decode(encode(s)) == s` for the sample text in both languages,
and you can explain why byte-level BPE never produces an "unknown" token.

### Task 2 — Embeddings & cosine similarity 🟡 (WORKED)

**Goal:** implement cosine similarity by hand; embed ~6 sentences via
`provider.embed()`; print a similarity matrix and nearest-neighbour ranking that
shows semantically close sentences scoring higher.

**Steps**

1. Read `cosine.py` / `cosine.ts`: `dot`, `norm`, and `cosine` are written from
   first principles (no numpy / no library).
2. The script embeds 6 sentences (works with Ollama's `nomic-embed-text` by
   default — `ollama pull nomic-embed-text`). **Note:** Anthropic has no
   embeddings endpoint; use ollama / openai / nvidia.
3. It prints a full 6×6 similarity matrix and, for one query sentence, its
   nearest neighbours sorted by cosine.

**Acceptance:** sentences about the same topic score visibly higher than
unrelated ones; `cosine(v, v) ≈ 1`.

### Task 3 — Attention head 🔴 (STUB)

**Goal:** implement scaled dot-product self-attention.

**Steps**

1. Open `attention.py` (numpy) / `attention.ts` (plain arrays).
2. Fill in the TODOs using the math in **Concept 3**: `softmax(QKᵀ/√dₖ)V`.
   Implement a numerically stable `softmax` (subtract the row max).
3. Run the file; the scaffold prints the attention weights and output and checks
   that each weight row sums to 1.

**Acceptance:** each softmax row sums to ~1.0 and the output has shape
`(seq_len, dₖ)`.

### Task 4 — Samplers 🔴 (STUB)

**Goal:** implement `greedy`, `temperature`, `top_k`, and `top_p` (nucleus)
sampling over a probability/logit vector.

**Steps**

1. Open `sampling.py` / `sampling.ts`. A `softmax` helper is provided.
2. Implement each function per **Concept 4**. Greedy returns the argmax;
   the others return a sampled index (seed the RNG so runs are reproducible).
3. Run the file; the scaffold prints which token each sampler picks on a small
   example distribution.

**Acceptance:** greedy always returns the argmax; lowering temperature
concentrates picks on the top tokens; top-k / top-p never select a token outside
their kept set.

### Task 5 — What is a model 🟡 (optional STUB)

**Goal:** make "next-token prediction" concrete with a count-based **bigram**
model.

**Steps**

1. Open `bigram.py`. Fill in the TODOs: count token→next-token frequencies in a
   small corpus, then generate by sampling the next token from those counts.
2. Observe that it produces locally-plausible, globally-nonsense text — and that
   this _is_ a (bad) language model. A transformer is this idea with a much
   longer memory and learned representations.

**Acceptance:** it generates a short sequence by repeatedly predicting the next
token from the previous one.

---

## Done when

- [ ] `decode(encode(s)) == s` passes in both Python and TypeScript (Task 1).
- [ ] Your cosine ranking puts same-topic sentences above unrelated ones (Task 2).
- [ ] Your attention weights' rows each sum to 1 (Task 3).
- [ ] Greedy/temperature/top-k/top-p behave as described (Task 4).
- [ ] You can explain, in one sentence each: token, embedding, attention, sampling.
- [ ] `pytest test_fundamentals.py` and `jest bpe.test.ts` pass.

---

## Going deeper

- **Karpathy — [Let's build GPT (video)](https://www.youtube.com/watch?v=kCc8FmEb1nY)** and **[nanoGPT](https://github.com/karpathy/nanoGPT)** / **[minBPE](https://github.com/karpathy/minbpe)**. The single best way to internalise this module.
- **3Blue1Brown — [Neural networks series](https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi)** (incl. the transformer / attention episodes). Best visual intuition.
- **[The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/)** — diagrams for Q/K/V and multi-head attention.
- **[Hugging Face LLM Course](https://huggingface.co/learn/llm-course)** — tokenizers, embeddings, transformers hands-on.
- **[tinygrad](https://github.com/tinygrad/tinygrad)** — a tiny autograd/NN framework worth reading once you've done the from-scratch tasks.
- **[Attention Is All You Need](https://arxiv.org/abs/1706.03762)** — the original transformer paper; readable after this module.
