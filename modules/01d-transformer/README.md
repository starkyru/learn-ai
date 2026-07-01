# Module 01d — Transformer Architecture

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

Module 01 gave you a single toy attention head. This deep-dive companion builds the
**whole decoder** the way GPT (Generative Pre-trained Transformer)-style models are actually assembled: multi-head
self-attention with causal masking, sinusoidal positional encodings, a pre-LN (pre-Layer Normalization) block
(LayerNorm (Layer Normalization) + residual + feed-forward), and the KV cache (Key-Value cache) that makes generation fast.

Everything here is **pure numpy (Python) / plain arrays (TypeScript)**, offline, and
deterministic. No provider, no network, no ML (Machine Learning) framework — the point is to see the
machinery with nothing hidden. This is the course's most-asked interview material;
"explain the KV cache and attention masking" is Task 4.

---

## Concepts

### 1. Scaled dot-product attention

Attention lets every token pull information from every other token. Given three
matrices derived from the input — **queries** `Q`, **keys** `K`, **values** `V` —
the output is a weighted average of the value vectors, where the weights come from
how well each query matches each key:

```
scores  = Q @ Kᵀ / √d_k        # (n_q × n_k) raw affinities
weights = softmax(scores)       # row-wise; each row sums to 1
output  = weights @ V           # (n_q × d_v)
```

**Why divide by √d_k?** The dot product of two `d_k`-dimensional vectors has variance
proportional to `d_k`. Without scaling, large `d_k` pushes the scores into the tails
of the softmax, where gradients vanish and the distribution collapses onto one token.
Dividing by `√d_k` keeps the scores at unit scale so the softmax stays soft.

**Numerically stable softmax** — subtract the row max before exponentiating (same
result, no overflow):

```
softmax(z)_j = exp(z_j − max(z)) / Σ_k exp(z_k − max(z))
```

### 2. Causal masking

A decoder generates left-to-right, so position `i` must never attend to a _future_
position `j > i` (that would be cheating — looking at the answer). We enforce this
with an **additive mask** added to the scores before softmax:

```
mask[i, j] = 0        if j ≤ i     (allowed)
mask[i, j] = −∞       if j > i     (blocked)
```

`exp(−∞) = 0`, so every future weight becomes exactly 0 and the row still sums to 1
over the allowed positions. In code we use a large negative number (e.g. `−1e9`) as
a stand-in for `−∞`.

### 3. Multi-head attention

One attention head can only average things one way. **Multi-head** attention runs `h`
independent attention operations in parallel, each in its own `d_k = d_model / h`
subspace, so different heads can specialise (one tracks syntax, another long-range
coreference, etc.):

```
Q, K, V = X @ W_q,  X @ W_k,  X @ W_v      # each (n × d_model)
for each head h:  slice its d_k columns, run scaled dot-product attention
concat the h head outputs  →  (n × d_model)
output = concat @ W_o                       # final mix across heads
```

With `h = 1` and identity projections this collapses back to plain single-head
attention — a useful correctness check.

### 4. Positional encoding

Attention is **permutation-equivariant**: it has no notion of order. Shuffle the input
tokens and the outputs shuffle identically — "dog bites man" and "man bites dog" would
be indistinguishable. We inject order by **adding** a position-dependent vector to each
token embedding before attention. The sinusoidal PE (Positional Encoding) scheme:

```
PE[pos, 2i]   = sin( pos / 10000^(2i/d) )
PE[pos, 2i+1] = cos( pos / 10000^(2i/d) )
```

Even dimensions get sines, odd dimensions get cosines, and the wavelength grows
geometrically across the dimension axis (fast oscillation early, slow later). Two
consequences you'll verify: every value lies in `[−1, 1]`, and the **PE dot-product
is highest at zero distance and generally falls off for nearby offsets** — the
harness checks an adjacent pair against the sequence endpoint. (The decay isn't
strictly monotonic across _all_ position pairs — the sum of sinusoids can wobble —
but the local trend gives the model a smooth sense of distance.)

### 5. LayerNorm, residuals, and the feed-forward network

**LayerNorm** normalizes each token's feature vector to mean 0 / variance 1, then
applies a learned scale `γ` and shift `β` (unlike BatchNorm (Batch Normalization) it works per-token, so it's
independent of batch size):

```
μ    = mean(x)                    # over the feature axis, per row
σ²   = mean((x − μ)²)
x̂    = (x − μ) / √(σ² + ε)
out  = γ · x̂ + β
```

**GELU (Gaussian Error Linear Unit)** is the smooth activation used in GPT-family models (tanh approximation):

```
gelu(x) = 0.5 · x · (1 + tanh( √(2/π) · (x + 0.044715 · x³) ))
```

**FFN** (position-wise Feed-Forward Network) applies the same two-layer MLP (Multi-Layer Perceptron) to every
position, typically widening to `4 × d_model` in the middle:

```
h = gelu(x @ W1 + b1)      # (n × d_model) → (n × d_ff)
y = h @ W2 + b2            # (n × d_ff) → (n × d_model)
```

**Pre-LN block.** GPT-2 and successors normalize the _input_ to each sublayer and add a
residual connection around it. The clean residual path (input flows straight through,
sublayer only adds a correction) is what lets deep stacks train stably:

```
x = x + MHA(LN1(x), causal_mask)      # attention sublayer
x = x + FFN(LN2(x))                   # feed-forward sublayer
```

Stack `N` of these and you have a decoder.

### 6. The KV cache

Generation is autoregressive: one token at a time, each attending over the whole prefix
so far. The **naive** approach recomputes the keys and values for the _entire_ prefix at
every step — `1 + 2 + … + n = n(n+1)/2` key projections to emit `n` tokens (quadratic).
But the keys and values of old tokens never change.

The **KV cache** stores each token's `k` and `v` once. At step `t` you project only the
new token's `q, k, v`, append `k, v` to the cache, and attend the single new query over
all cached keys/values:

```
naive : n(n+1)/2 key projections   (recompute prefix each step)
cached : n key projections          (one new key per step)
```

Identical outputs, linear instead of quadratic work. This is why real LLM (Large Language Model) inference is
fast — and why longer context costs proportionally more memory (the cache grows).

---

## Tasks

### Task 1 🔴 — Multi-head self-attention with causal masking

**Goal:** Implement scaled dot-product attention, a causal mask, and multi-head
attention from scratch.

**Files:**

- `py/01_attention.py`
- `ts/01-attention.ts`

**Steps:**

1. Implement `scaled_dot_product_attention(Q, K, V, mask=None)` /
   `scaledDotProductAttention(Q, K, V, mask=null)`:
   - `scores = Q @ Kᵀ / √d_k`
   - add `mask` if provided
   - row-wise **numerically stable** softmax (subtract row max before `exp`)
   - `output = weights @ V`; return `(output, weights)`.

2. Implement `causal_mask(n)` / `causalMask(n)` — an `n × n` additive mask, `0` on and
   below the diagonal, `−∞` (use the provided `NEG_INF`) strictly above it.

3. Implement `multi_head_attention(...)` / `multiHeadAttention(...)` — project `X` to
   `Q, K, V`, split `d_model` into `h` heads of width `d_k`, run SDPA (Scaled Dot-Product Attention) per head,
   concatenate the head outputs, apply the output projection `W_o`.

**Acceptance:**

- Every attention-weight row sums to `1.0` (±1e-6).
- With the causal mask, position `i` has **zero** weight on any `j > i`.
- Multi-head with `h = 1` and identity projections is `allclose` to single-head SDPA.
- MHA (Multi-Head Attention) output shape is `(n, d_model)` and all values are finite.

---

### Task 2 🟡 — Sinusoidal positional encoding

**Goal:** Build the sinusoidal PE table and demonstrate why order matters.

**Files:**

- `py/02_positional_encoding.py`
- `ts/02-positional-encoding.ts`

**Steps:**

1. Implement `sinusoidal_encoding(max_len, d_model)` / `sinusoidalEncoding(maxLen, dModel)`:
   - `PE[pos, 2i]   = sin(pos / 10000^(2i/d))`
   - `PE[pos, 2i+1] = cos(pos / 10000^(2i/d))`
   - return shape `(max_len, d_model)`.

2. The harness runs the **permutation-equivariance experiment** for you: it takes a
   sequence and a fixed permutation of its rows, and runs self-attention with and
   without PE. Study the printed result — without PE the outputs are just a permutation
   of each other; adding PE by absolute slot breaks that symmetry.

3. The harness also runs the **locality check**: `PE[0]·PE[1]` (adjacent) vs
   `PE[0]·PE[n−1]` (far apart).

**Acceptance:**

- PE shape is `(max_len, d_model)` and every value lies in `[−1, 1]`.
- The permutation-equivariance test **passes without PE** (`out(perm(X)) == perm(out(X))`)
  and **fails with PE** (the outputs differ once order is encoded).
- The adjacent-pair PE dot-product `PE[0]·PE[1]` exceeds the endpoint pair
  `PE[0]·PE[n−1]` (a local decay, not strict monotonicity across all pairs).

---

### Task 3 🔴 — Pre-LN transformer decoder block

**Goal:** Assemble LayerNorm, GELU, an FFN, and residual connections into a decoder
block, then stack `N` of them.

**Files:**

- `py/03_decoder_block.py`
- `ts/03-decoder-block.ts`

The attention helpers from Task 1 are **copied into this file** so it is self-contained.

**Steps:**

1. Implement `layer_norm(x, gamma, beta, eps)` / `layerNorm(...)` — per-row
   `(x − μ) / √(σ² + ε) · γ + β` (population variance).

2. Implement `gelu(x)` — the tanh approximation
   `0.5·x·(1 + tanh(√(2/π)·(x + 0.044715·x³)))`.

3. Implement `ffn(x, W1, b1, W2, b2)` — `Linear → GELU → Linear`.

4. Implement `TransformerBlock.forward(x)` — the pre-LN residual block:
   - `x = x + MHA(LN1(x), causal_mask)`
   - `x = x + FFN(LN2(x))`

5. The harness stacks `N = 3` blocks and prints the result.

**Acceptance:**

- `layer_norm` output per row has mean ≈ 0 (±1e-6) and variance ≈ 1 (±1e-5) before
  `γ/β` are applied (identity `γ=1, β=0`).
- One block preserves the input shape `(n, d_model)`.
- Stacking `N = 3` blocks runs and produces all-finite output.

---

### Task 4 🟡 — The KV cache

**Goal:** Implement incremental causal decoding with a KV cache and prove it equals the
naive recompute — at a fraction of the work.

**Files:**

- `py/04_kv_cache.py`
- `ts/04-kv-cache.ts`

The naive recompute path (`decode_naive` / `decodeNaive`) is **provided** as ground
truth. You implement the cached path.

**Steps:**

1. Implement `decode_with_cache(X, Wq, Wk, Wv, Wo)` / `decodeWithCache(...)`:
   - keep growing `K_cache` and `V_cache` lists
   - at each step `t`: project **only** the new token `X[t]` into `q_t, k_t, v_t`
   - **append** `k_t, v_t` to the cache (old entries are reused, not recomputed)
   - attend `q_t` over all cached keys/values; append `context @ Wo` to the logits
   - count exactly **one** key projection per step.

2. Compare against `decode_naive`, which reprojects the whole prefix each step and
   counts `n(n+1)/2` key projections.

**Acceptance:**

- Cached logits equal naive logits at **every** step (`allclose`, `atol = 1e-5`).
- Key-projection op count is **n** for cached vs **n(n+1)/2** for naive — both printed.

---

## Done when

- [ ] `01_attention` / `01-attention` runs: weight rows sum to 1, the causal mask zeroes
      out future positions, and `h=1` MHA matches single-head SDPA.
- [ ] `02_positional_encoding` / `02-positional-encoding` prints the PE shape/range, the
      permutation-equivariance result (passes without PE, fails with PE), and the
      locality check.
- [ ] `03_decoder_block` / `03-decoder-block` shows LayerNorm rows with mean≈0/var≈1, a
      shape-preserving block, and a finite output from a 3-block stack.
- [ ] `04_kv_cache` / `04-kv-cache` shows identical per-step logits and prints the
      `n` vs `n(n+1)/2` key-projection counts.

---

## How this maps to a real transformer

| Piece you built here           | In a production LLM                                                                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| `scaled_dot_product_attention` | The kernel every attention library optimizes (FlashAttention fuses these steps)                                     |
| `causal_mask`                  | Applied by every decoder; batched/packed sequences also use padding masks                                           |
| `multi_head_attention`         | 12–128 heads in real models; often with grouped-query attention to shrink the KV cache                              |
| `sinusoidal_encoding`          | Replaced in modern models by RoPE (Rotary Positional Embedding) / ALiBi, but the "add order info" idea is identical |
| pre-LN `TransformerBlock`      | The repeated unit; GPT-2 = 12 layers, GPT-3 = 96                                                                    |
| KV cache                       | Exactly what `use_cache=True` / paged-attention servers do at inference                                             |

---

## Going deeper

- **"Attention Is All You Need"** — the original transformer paper:
  <https://arxiv.org/abs/1706.03762>
- **The Illustrated Transformer** — Jay Alammar's diagram-first walkthrough:
  <https://jalammar.github.io/illustrated-transformer/>
- **Karpathy, "Let's build GPT: from scratch, in code, spelled out"** — the canonical
  from-scratch video: <https://www.youtube.com/watch?v=kCc8FmEb1nY>
- **nanoGPT** — a minimal, readable GPT implementation:
  <https://github.com/karpathy/nanoGPT>
- **"The Annotated Transformer"** — Harvard NLP (Natural Language Processing)'s line-by-line PyTorch version:
  <https://nlp.seas.harvard.edu/annotated-transformer/>
- **RoPE (Rotary Positional Embeddings)** — what modern models use instead of
  sinusoidal PE: <https://arxiv.org/abs/2104.09864>

---

## Environment

No env vars, no provider, no network — these exercises are pure numpy / plain TS and run
fully offline.

- **Python:** `uv run python modules/01d-transformer/py/01_attention.py` (numpy is a base
  dependency; no extra needed).
- **TypeScript:** `pnpm build:core` once, then
  `pnpm tsx modules/01d-transformer/ts/01-attention.ts`.
