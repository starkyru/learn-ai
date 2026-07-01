"""
Task 2 🟡 — Sinusoidal positional encoding, and why order matters.

What you'll learn:
  - Self-attention alone is PERMUTATION-EQUIVARIANT: shuffle the input tokens and
    the outputs shuffle the same way. The mechanism has no idea what ORDER the
    tokens came in. "dog bites man" and "man bites dog" would be indistinguishable.
  - Positional encoding fixes this by adding a unique, position-dependent vector
    to each token's embedding BEFORE attention. Now the input to attention differs
    by more than a permutation, so the outputs genuinely differ.

The math (README derives this in plain English):

  For position pos (0-based) and dimension index i (0-based), with model dim d:

    PE[pos, 2i]   = sin( pos / 10000^(2i/d) )
    PE[pos, 2i+1] = cos( pos / 10000^(2i/d) )

  Even columns get a sine, odd columns get a cosine, and the wavelength grows
  geometrically across the dimension axis (fast-oscillating early dims, slow
  later dims). Every position gets a distinct fingerprint, and nearby positions
  have similar fingerprints (high dot-product) while far positions do not.

No ML library. Only numpy.

How to run:
  uv run python modules/01d-transformer/py/02_positional_encoding.py

The harness runs the permutation-equivariance experiment and the locality check.
`sinusoidal_encoding` is left as a TODO for you.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Core function — implement this
# ---------------------------------------------------------------------------


def sinusoidal_encoding(max_len: int, d_model: int) -> np.ndarray:
    """
    Build the (max_len, d_model) sinusoidal positional-encoding table.

      PE[pos, 2i]   = sin( pos / 10000^(2i/d_model) )
      PE[pos, 2i+1] = cos( pos / 10000^(2i/d_model) )

    d_model is assumed even. Every value lies in [-1, 1] (sin/cos range).

    Returns: float64 array of shape (max_len, d_model).

    TODO: implement.
      1. positions = np.arange(max_len)[:, None]            shape (max_len, 1)
      2. For the paired index i in 0..d_model/2-1, the divisor is
           div = 10000 ** (2i / d_model)
         Build these for all even columns at once:
           even_i = np.arange(0, d_model, 2)                # 0,2,4,... length d_model/2
           div_term = 10000.0 ** (even_i / d_model)         # note: even_i = 2i
      3. angles = positions / div_term                      shape (max_len, d_model/2)
      4. pe = np.zeros((max_len, d_model))
         pe[:, 0::2] = np.sin(angles)     # even columns
         pe[:, 1::2] = np.cos(angles)     # odd columns
      5. return pe
    """
    # TODO: implement sinusoidal positional encoding
    raise NotImplementedError("TODO: implement sinusoidal_encoding()")


# ---------------------------------------------------------------------------
# Attention (provided — from Task 1, self-contained here)
# ---------------------------------------------------------------------------


def scaled_dot_product_attention(X: np.ndarray) -> np.ndarray:
    """Plain self-attention SDPA(X, X, X) — output only. Provided."""
    d_k = X.shape[-1]
    scores = X @ X.T / np.sqrt(d_k)
    scores = scores - scores.max(axis=-1, keepdims=True)
    exp_s = np.exp(scores)
    weights = exp_s / exp_s.sum(axis=-1, keepdims=True)
    return weights @ X


# ---------------------------------------------------------------------------
# Harness — complete, do not edit
# ---------------------------------------------------------------------------


def main() -> None:
    rng = np.random.default_rng(0)
    n = 6  # sequence length
    d_model = 16  # model dim (even)

    print("=" * 66)
    print("Task 2 — Sinusoidal positional encoding & why order matters")
    print("=" * 66)

    # ── Build the PE table and inspect it ─────────────────────────────────────
    pe = sinusoidal_encoding(max_len=n, d_model=d_model)
    print(f"\n[shape] PE shape: {pe.shape}  (expected ({n}, {d_model}))")
    print(f"[range] PE min={pe.min():.4f}  max={pe.max():.4f}  (expected within [-1, 1])")
    in_range = pe.min() >= -1.0 - 1e-9 and pe.max() <= 1.0 + 1e-9

    # ── Permutation-equivariance experiment ───────────────────────────────────
    # A random token-embedding sequence and a fixed permutation of its rows.
    X = rng.standard_normal((n, d_model))
    perm = rng.permutation(n)
    X_perm = X[perm]

    # (a) WITHOUT positional encoding:
    #     attention on the permuted input is exactly the permutation of attention
    #     on the original input. i.e. out_perm == out[perm].  Order is invisible.
    out = scaled_dot_product_attention(X)
    out_perm = scaled_dot_product_attention(X_perm)
    equivariant = np.allclose(out_perm, out[perm], atol=1e-9)
    print("\n[no PE] attention is permutation-equivariant?")
    print(f"        out(perm(X)) == perm(out(X)) : {equivariant}")

    # (b) WITH positional encoding added before attention:
    #     the same permutation now scrambles which PE each token receives, so the
    #     outputs are NO LONGER a clean permutation of each other. Order matters.
    Xp = X + pe
    Xp_perm = X_perm + pe  # PE is added by absolute slot, NOT permuted with tokens
    out_pe = scaled_dot_product_attention(Xp)
    out_pe_perm = scaled_dot_product_attention(Xp_perm)
    equivariant_with_pe = np.allclose(out_pe_perm, out_pe[perm], atol=1e-9)
    print("\n[with PE] still permutation-equivariant?")
    print(f"          out(perm(X)+PE) == perm(out(X+PE)) : {equivariant_with_pe}")
    print("          (should be FALSE — PE breaks the symmetry, encoding order)")

    # ── Locality check: nearby positions have higher PE dot-product ───────────
    # Compare PE[0]·PE[1] (adjacent) vs PE[0]·PE[n-1] (far apart).
    near = float(pe[0] @ pe[1])
    far = float(pe[0] @ pe[n - 1])
    locality_ok = near > far
    print(f"\n[locality] PE[0]·PE[1] (near) = {near:.4f}")
    print(f"           PE[0]·PE[{n - 1}] (far)  = {far:.4f}")
    print(f"           near > far : {locality_ok}")

    assert in_range, "PE values must lie in [-1, 1]"
    assert equivariant, "without PE, attention must be permutation-equivariant"
    assert not equivariant_with_pe, "with PE, the outputs must differ (order encoded)"
    assert locality_ok, "nearby positions must have higher PE dot-product than far ones"
    print("\nAll checks passed. ✅")


if __name__ == "__main__":
    main()
