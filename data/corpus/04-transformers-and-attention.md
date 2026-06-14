# Transformers and Attention

The Transformer architecture, introduced in the 2017 paper "Attention Is All You Need",
replaced recurrent networks as the dominant model for sequence tasks. Every major large
language model (LLM) — GPT, Claude, Llama, Gemini — is a Transformer.

## The attention mechanism

Attention lets a model weigh every token in the input when computing the representation
of any given token. For each token, three vectors are computed: a **query** (Q), a
**key** (K), and a **value** (V). The output for a token is a weighted sum of all
value vectors, where the weights come from the dot product of that token's query with
every other token's key, passed through a softmax.

```
Attention(Q, K, V) = softmax(QKᵀ / √d_k) V
```

`d_k` is the key dimension; the square-root scaling prevents dot products from growing
so large that the softmax saturates.

**Multi-head attention** runs several attention operations in parallel with different
learned projections, then concatenates and projects the results. Each head can
specialise: one might track syntactic agreement, another long-range coreference.

## Transformer blocks

A Transformer layer consists of:
1. Multi-head self-attention (with a residual connection + layer norm).
2. A feed-forward network applied position-wise (two linear layers with ReLU or GELU
   in between), again with a residual connection + layer norm.

**Positional encodings** (or learned positional embeddings) are added to the input
before the first layer, because attention itself is permutation-invariant and would
otherwise ignore token order.

## Decoder-only LLMs

LLMs like GPT and Llama use the decoder side only. They are trained autoregressively:
at each position, they predict the next token given all previous tokens. This is
achieved with **causal (masked) attention** — each token can only attend to tokens
that came before it, preventing the model from "looking ahead" during training.
