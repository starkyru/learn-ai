"""
Task 3 🔴 — A full pre-LN transformer DECODER block, FROM SCRATCH.

What you'll learn:
  - LayerNorm: normalize each row to mean 0 / variance 1, then scale+shift (γ, β).
    (Unlike BatchNorm, it normalizes across FEATURES per token — batch-size agnostic.)
  - GELU: the smooth activation used in GPT-family models (tanh approximation).
  - The position-wise feed-forward network (FFN): Linear -> GELU -> Linear, applied
    identically to every position, usually widening to 4× d_model in the middle.
  - The pre-LN residual block that GPT-2 and friends actually use:
        x = x + MHA(LN1(x), causal)      # attention sublayer + residual
        x = x + FFN(LN2(x))              # feed-forward sublayer + residual
    "Pre-LN" = normalize the INPUT to each sublayer; the residual path stays clean,
    which is why deep stacks train stably.

The math (README derives each step in plain English):

  LayerNorm, per row x (length d):
    mu   = mean(x)
    var  = mean((x - mu)^2)
    xhat = (x - mu) / sqrt(var + eps)
    out  = gamma * xhat + beta           (gamma, beta length d; elementwise)

  GELU (tanh approximation):
    gelu(x) = 0.5 * x * (1 + tanh( sqrt(2/pi) * (x + 0.044715 * x^3) ))

  FFN:
    h = gelu(x @ W1 + b1)                (x: (n,d) -> (n, d_ff))
    y = h @ W2 + b2                      ((n, d_ff) -> (n, d))

No ML library. Only numpy.

How to run:
  uv run python modules/01d-transformer/py/03_decoder_block.py

The harness builds seeded weights, stacks N=3 blocks, and prints the acceptance
evidence. `layer_norm`, `gelu`, `ffn`, and the block's `forward` are TODOs.
"""

from __future__ import annotations

import numpy as np

NEG_INF = -1e9


# ---------------------------------------------------------------------------
# Attention helpers (provided — copied from Task 1 so this file is self-contained)
# ---------------------------------------------------------------------------


def scaled_dot_product_attention(
    Q: np.ndarray, K: np.ndarray, V: np.ndarray, mask: np.ndarray | None = None
) -> np.ndarray:
    d_k = K.shape[-1]
    scores = Q @ K.T / np.sqrt(d_k)
    if mask is not None:
        scores = scores + mask
    scores = scores - scores.max(axis=-1, keepdims=True)
    exp_s = np.exp(scores)
    weights = exp_s / exp_s.sum(axis=-1, keepdims=True)
    return weights @ V


def causal_mask(n: int) -> np.ndarray:
    mask = np.zeros((n, n))
    mask[np.triu_indices(n, k=1)] = NEG_INF
    return mask


def multi_head_attention(
    X: np.ndarray,
    Wq: np.ndarray,
    Wk: np.ndarray,
    Wv: np.ndarray,
    Wo: np.ndarray,
    num_heads: int,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    n, d_model = X.shape
    d_k = d_model // num_heads
    Q, K, V = X @ Wq, X @ Wk, X @ Wv
    heads = []
    for h in range(num_heads):
        cols = slice(h * d_k, (h + 1) * d_k)
        heads.append(scaled_dot_product_attention(Q[:, cols], K[:, cols], V[:, cols], mask))
    concat = np.concatenate(heads, axis=1)
    return concat @ Wo


# ---------------------------------------------------------------------------
# Core functions — implement these
# ---------------------------------------------------------------------------


def layer_norm(x: np.ndarray, gamma: np.ndarray, beta: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    """
    Row-wise layer normalization.

    For each row (a token's feature vector):
      mu   = mean over the row
      var  = mean of (x - mu)^2 over the row     (population variance, not sample)
      xhat = (x - mu) / sqrt(var + eps)
      out  = gamma * xhat + beta                 (elementwise; gamma, beta length d)

    Args:
      x     : (n, d)
      gamma : (d,) scale
      beta  : (d,) shift
    Returns: (n, d)

    Note: with gamma=1, beta=0 each output row has mean ~0 and variance ~1.

    TODO: implement. Per row (i.e. reduce along axis=1 with keepdims=True so it
    broadcasts): compute the row mean mu, then the population variance (mean of
    the squared deviations from mu — no Bessel/n-1 correction). Normalise with
    (x - mu) / sqrt(var + eps), then apply the affine scale-and-shift using gamma
    and beta (both length d, elementwise) and return the result.
    """
    # TODO: implement layer norm
    raise NotImplementedError("TODO: implement layer_norm()")


def gelu(x: np.ndarray) -> np.ndarray:
    """
    GELU activation (tanh approximation).

      gelu(x) = 0.5 * x * (1 + tanh( sqrt(2/pi) * (x + 0.044715 * x^3) ))

    TODO: implement using the formula above (np.tanh, np.sqrt, np.pi).
    """
    # TODO: implement gelu
    raise NotImplementedError("TODO: implement gelu()")


def ffn(
    x: np.ndarray, W1: np.ndarray, b1: np.ndarray, W2: np.ndarray, b2: np.ndarray
) -> np.ndarray:
    """
    Position-wise feed-forward network: Linear -> GELU -> Linear.

      h = gelu(x @ W1 + b1)     # (n, d) -> (n, d_ff)
      y = h @ W2 + b2           # (n, d_ff) -> (n, d)

    Applied identically to every row (position).

    TODO: implement the two linear layers with GELU between them.
    """
    # TODO: implement feed-forward network
    raise NotImplementedError("TODO: implement ffn()")


# ---------------------------------------------------------------------------
# Transformer decoder block
# ---------------------------------------------------------------------------


class TransformerBlock:
    """
    Pre-LN transformer decoder block.

      x = x + MHA(LN1(x), causal_mask)      # attention sublayer + residual
      x = x + FFN(LN2(x))                  # feed-forward sublayer + residual

    All weights are supplied by the harness (seeded) so the block is deterministic.
    """

    def __init__(self, params: dict, num_heads: int) -> None:
        self.p = params
        self.num_heads = num_heads

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Run one pre-LN decoder block over x of shape (n, d_model).

        p = self.p holds: Wq, Wk, Wv, Wo (each d×d), gamma1/beta1, gamma2/beta2
        (each length d), and W1,b1,W2,b2 for the FFN.

        TODO: implement the two pre-LN sublayers (build the causal_mask from the
        sequence length x.shape[0] first):
          - Attention sublayer: layer_norm the input with gamma1/beta1, feed that
            through multi_head_attention (Wq/Wk/Wv/Wo, self.num_heads, the mask),
            and ADD the result back onto x (the residual connection).
          - Feed-forward sublayer: layer_norm the running x with gamma2/beta2, feed
            that through ffn (W1/b1/W2/b2), and again ADD it back onto x.
          - Return the updated x. Note the pattern is x = x + sublayer(LN(x)) both
            times — the residual path is never normalised.
        """
        # TODO: implement the pre-LN decoder block
        raise NotImplementedError("TODO: implement TransformerBlock.forward()")


# ---------------------------------------------------------------------------
# Harness — complete, do not edit
# ---------------------------------------------------------------------------


def make_block_params(d_model: int, d_ff: int, seed: int) -> dict:
    """Deterministic weights for one block."""
    rng = np.random.default_rng(seed)
    s_attn = 1.0 / np.sqrt(d_model)
    s_ff = 1.0 / np.sqrt(d_model)
    s_ff2 = 1.0 / np.sqrt(d_ff)
    return {
        "Wq": rng.normal(0, s_attn, (d_model, d_model)),
        "Wk": rng.normal(0, s_attn, (d_model, d_model)),
        "Wv": rng.normal(0, s_attn, (d_model, d_model)),
        "Wo": rng.normal(0, s_attn, (d_model, d_model)),
        "gamma1": np.ones(d_model),
        "beta1": np.zeros(d_model),
        "gamma2": np.ones(d_model),
        "beta2": np.zeros(d_model),
        "W1": rng.normal(0, s_ff, (d_model, d_ff)),
        "b1": np.zeros(d_ff),
        "W2": rng.normal(0, s_ff2, (d_ff, d_model)),
        "b2": np.zeros(d_model),
    }


def main() -> None:
    rng = np.random.default_rng(0)
    n = 5
    d_model = 16
    d_ff = 64
    num_heads = 4
    num_layers = 3

    print("=" * 66)
    print("Task 3 — Pre-LN transformer decoder block")
    print("=" * 66)
    print(f"  n={n}  d_model={d_model}  d_ff={d_ff}  heads={num_heads}  layers={num_layers}\n")

    # ── Check 1: layer_norm produces mean 0 / var 1 per row (before gamma/beta) ─
    x = rng.standard_normal((n, d_model)) * 3.0 + 5.0  # deliberately off-center
    ones = np.ones(d_model)
    zeros = np.zeros(d_model)
    normed = layer_norm(x, ones, zeros)
    row_means = normed.mean(axis=1)
    row_vars = normed.var(axis=1)
    print("[1] LayerNorm row means:", np.round(row_means, 6))
    print("    LayerNorm row vars :", np.round(row_vars, 6))
    mean_ok = np.allclose(row_means, 0.0, atol=1e-6)
    var_ok = np.allclose(row_vars, 1.0, atol=1e-5)
    print(f"    mean ~ 0: {mean_ok}   var ~ 1: {var_ok}\n")

    # ── Check 2: a single block preserves the input shape ─────────────────────
    params = [make_block_params(d_model, d_ff, seed=100 + i) for i in range(num_layers)]
    block0 = TransformerBlock(params[0], num_heads)
    x0 = rng.standard_normal((n, d_model))
    y0 = block0.forward(x0)
    shape_ok = y0.shape == (n, d_model)
    print(f"[2] One block: input {x0.shape} -> output {y0.shape}   shape preserved: {shape_ok}\n")

    # ── Check 3: stack N=3 blocks; output is finite ───────────────────────────
    h = rng.standard_normal((n, d_model))
    for i in range(num_layers):
        h = TransformerBlock(params[i], num_heads).forward(h)
    finite_ok = bool(np.all(np.isfinite(h)))
    print(f"[3] Stacked {num_layers} blocks: output shape {h.shape}")
    print(f"    all outputs finite: {finite_ok}")
    print(f"    output row-0 (rounded): {np.round(h[0], 3)}\n")

    assert mean_ok, "LayerNorm rows must have mean ~ 0"
    assert var_ok, "LayerNorm rows must have variance ~ 1"
    assert shape_ok, "a block must preserve input shape"
    assert finite_ok, "stacked blocks must output finite numbers"
    print("All checks passed. ✅")


if __name__ == "__main__":
    main()
