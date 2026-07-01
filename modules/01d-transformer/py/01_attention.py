"""
Task 1 🔴 — Multi-head self-attention with causal masking, FROM SCRATCH.

What you'll learn:
  - Scaled dot-product attention: the core operation of every transformer
  - Why we divide by sqrt(d_k) (keeps softmax gradients healthy)
  - Causal masking: how a decoder is stopped from "seeing the future"
  - Multi-head attention: split d_model into h independent subspaces, attend
    in each, concatenate, then project back

The math (README derives each step in plain English):

  Scaled dot-product attention, for queries Q, keys K, values V:

    scores = Q @ K.T / sqrt(d_k)          shape (n_q, n_k)
    scores = scores + mask                 mask is 0 or -inf per entry
    weights = softmax(scores)              row-wise, each row sums to 1
    output  = weights @ V                  shape (n_q, d_v)

  Causal mask (additive form): an (n, n) matrix that is 0 on and below the
  diagonal and -inf above it. Adding it before softmax drives the weight on
  every "future" position j > i to exactly 0.

  Multi-head attention with h heads and model dim d_model (d_k = d_model / h):
    - project X -> Q, K, V  (weights provided, seeded)
    - reshape each into h heads of width d_k
    - run scaled dot-product attention independently in each head
    - concatenate the h head outputs back to width d_model
    - apply an output projection W_o

No ML library. Only numpy.

How to run:
  uv run python modules/01d-transformer/py/01_attention.py

The harness builds seeded projection weights, runs the checks, and prints the
acceptance evidence. The three core functions are left as TODOs for you.
"""

from __future__ import annotations

import numpy as np

NEG_INF = -1e9  # a large negative number; "-inf" for masking purposes


# ---------------------------------------------------------------------------
# Core functions — implement these
# ---------------------------------------------------------------------------


def scaled_dot_product_attention(
    Q: np.ndarray, K: np.ndarray, V: np.ndarray, mask: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """
    Scaled dot-product attention.

    Args:
      Q : queries, shape (n_q, d_k)
      K : keys,    shape (n_k, d_k)
      V : values,  shape (n_k, d_v)
      mask : optional additive mask of shape (n_q, n_k). Entries are 0 (keep) or
             a large negative number (block). Added to the scores BEFORE softmax.

    Returns:
      (output, weights)
        weights : (n_q, n_k), each row a probability distribution summing to 1
        output  : (n_q, d_v), the attention-weighted mix of value vectors

    The softmax must be numerically stable: subtract the per-row max before exp().

    TODO: implement. Steps:
      - Form the raw scores as Q @ K.T, then scale by dividing by sqrt(d_k)
        (d_k = K.shape[-1]). Result is (n_q, n_k).
      - If a mask was passed, add it to the scores (it blocks entries before softmax).
      - Apply a row-wise stable softmax: subtract the per-row max
        (axis=-1, keepdims=True) before np.exp, then normalise each row by its sum
        (again axis=-1, keepdims=True) so every row sums to 1.
      - Multiply the weights by V to get the (n_q, d_v) output.
      - Return the (output, weights) pair.
    """
    # TODO: implement scaled dot-product attention
    raise NotImplementedError("TODO: implement scaled_dot_product_attention()")


def causal_mask(n: int) -> np.ndarray:
    """
    Build an (n, n) additive causal mask.

    Entry [i, j] is:
      0        if j <= i   (position i is allowed to attend to position j)
      -inf     if j >  i   (position i must NOT attend to a future position)

    Adding this to the pre-softmax scores makes every "future" weight exp(-inf)=0.

    Use NEG_INF (defined above) as the stand-in for -inf.

    TODO: implement. Start from a zeros (n, n) array and set the strictly-upper-
    triangular entries (the future, j > i) to NEG_INF, leaving the diagonal and
    below at 0. Hint: np.triu(..., k=1) selects entries strictly above the diagonal.
    """
    # TODO: implement causal mask
    raise NotImplementedError("TODO: implement causal_mask()")


def multi_head_attention(
    X: np.ndarray,
    Wq: np.ndarray,
    Wk: np.ndarray,
    Wv: np.ndarray,
    Wo: np.ndarray,
    num_heads: int,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Multi-head self-attention.

    Args:
      X  : input, shape (n, d_model)
      Wq, Wk, Wv : projection weights, each shape (d_model, d_model)
      Wo : output projection, shape (d_model, d_model)
      num_heads : h; must divide d_model evenly. d_k = d_model / h.
      mask : optional additive mask of shape (n, n), applied inside every head.

    Returns:
      output, shape (n, d_model)

    TODO: implement. Steps:
      - Compute d_k = d_model // num_heads.
      - Project the input once into Q, K, V (each X @ W..., shape (n, d_model)).
      - For each head, take that head's contiguous block of d_k columns from Q, K, V
        (head h owns columns h*d_k .. (h+1)*d_k) and run
        scaled_dot_product_attention on those slices, passing the mask through.
        Keep just the output of each head.
      - Concatenate the per-head outputs along the feature axis (axis=1) back to
        width d_model (np.concatenate).
      - Apply the output projection Wo to the concatenation and return it.
    """
    # TODO: implement multi-head attention
    raise NotImplementedError("TODO: implement multi_head_attention()")


# ---------------------------------------------------------------------------
# Harness — complete, do not edit
# ---------------------------------------------------------------------------


def seeded_weights(d_model: int, seed: int) -> np.ndarray:
    """Deterministic projection matrix, Xavier-ish scale."""
    rng = np.random.default_rng(seed)
    scale = 1.0 / np.sqrt(d_model)
    return rng.normal(0.0, scale, (d_model, d_model)).astype(np.float64)


def main() -> None:
    rng = np.random.default_rng(0)
    n = 5  # sequence length
    d_model = 8  # model dimension
    h = 4  # number of heads (d_k = 2)

    X = rng.standard_normal((n, d_model))
    Wq = seeded_weights(d_model, 1)
    Wk = seeded_weights(d_model, 2)
    Wv = seeded_weights(d_model, 3)
    Wo = seeded_weights(d_model, 4)
    identity = np.eye(d_model)

    print("=" * 66)
    print("Task 1 — Multi-head self-attention with causal masking")
    print("=" * 66)
    print(f"  n={n}  d_model={d_model}  num_heads={h}  d_k={d_model // h}\n")

    # ── Check 1: attention weight rows sum to 1 ───────────────────────────────
    Q = rng.standard_normal((n, d_model))
    K = rng.standard_normal((n, d_model))
    V = rng.standard_normal((n, d_model))
    _, weights = scaled_dot_product_attention(Q, K, V)
    row_sums = weights.sum(axis=1)
    print("[1] Attention weight row sums:", np.round(row_sums, 6))
    rows_ok = np.allclose(row_sums, 1.0, atol=1e-6)
    print(f"    rows sum to 1 (+/-1e-6): {rows_ok}\n")

    # ── Check 2: causal mask zeroes out the future ────────────────────────────
    mask = causal_mask(n)
    _, cweights = scaled_dot_product_attention(Q, K, V, mask)
    # For every query position i, weight on any j > i must be ~0.
    upper = np.triu(cweights, k=1)
    causal_ok = np.allclose(upper, 0.0, atol=1e-9)
    print("[2] Causal attention weights (upper triangle should be all 0):")
    print(np.round(cweights, 3))
    print(f"    no attention to future positions (j>i == 0): {causal_ok}\n")

    # ── Check 3: h=1 multi-head equals single-head SDPA ───────────────────────
    # With identity projections and one head, MHA reduces to plain SDPA(X,X,X).
    mha_1 = multi_head_attention(X, identity, identity, identity, identity, num_heads=1)
    sdpa_out, _ = scaled_dot_product_attention(X, X, X)
    single_ok = np.allclose(mha_1, sdpa_out, atol=1e-9)
    print(f"[3] MHA(h=1, identity weights) == single-head SDPA: {single_ok}\n")

    # ── Check 4: shapes ───────────────────────────────────────────────────────
    out = multi_head_attention(X, Wq, Wk, Wv, Wo, num_heads=h, mask=causal_mask(n))
    shape_ok = out.shape == (n, d_model)
    print(f"[4] MHA output shape: {out.shape}  (expected ({n}, {d_model}))  ok={shape_ok}")
    print(f"    all outputs finite: {np.all(np.isfinite(out))}\n")

    assert rows_ok, "attention weight rows must sum to 1"
    assert causal_ok, "causal mask must zero out attention to future positions"
    assert single_ok, "MHA with h=1 and identity weights must equal single-head SDPA"
    assert shape_ok, "MHA output shape must be (n, d_model)"
    print("All checks passed. ✅")


if __name__ == "__main__":
    main()
