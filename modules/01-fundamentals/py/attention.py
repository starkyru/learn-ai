"""attention.py — scaled dot-product self-attention (Task 3, 🔴 STUB).

What it teaches:
    The single most important operation in a transformer. You'll implement
        Attention(Q, K, V) = softmax( (Q @ Kᵀ) / √dₖ ) @ V
    using numpy. See README Concept 3 for the full derivation. Fill in the
    TODOs; the scaffold below checks your work.

How to run (from the repo root):
    uv run python modules/01-fundamentals/py/attention.py
"""

from __future__ import annotations

import numpy as np


def softmax(x: np.ndarray) -> np.ndarray:
    """Row-wise softmax: softmax(x)ᵢ = exp(xᵢ) / Σ exp(xⱼ), per row.

    TODO:
      1. Subtract the per-row max (keepdims=True) BEFORE exp, for numerical
         stability. This doesn't change the result but prevents overflow.
      2. Exponentiate.
      3. Divide each row by its row-sum (keepdims=True) so each row sums to 1.

    Input shape: (n, n). Output shape: (n, n), each ROW summing to 1.
    """
    raise NotImplementedError("Implement row-wise softmax — see the docstring TODOs.")


def attention(Q: np.ndarray, K: np.ndarray, V: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Scaled dot-product attention.

    Args:
        Q: queries, shape (n, dₖ)
        K: keys,    shape (n, dₖ)
        V: values,  shape (n, dᵥ)
    Returns:
        (output, weights):
            weights: (n, n), the attention weights (each row sums to 1)
            output:  (n, dᵥ), the attention-weighted mix of value vectors

    TODO:
      1. dₖ = K.shape[-1].
      2. scores = Q @ K.T          # (n, n) raw dot-product affinities
      3. scores = scores / sqrt(dₖ)   # the "scaled" in scaled dot-product
      4. weights = softmax(scores)    # row-wise; uses the function above
      5. output = weights @ V         # (n, dᵥ)
      6. return output, weights
    """
    raise NotImplementedError("Implement scaled dot-product attention — see the TODOs.")


def main() -> None:
    rng = np.random.default_rng(0)
    seq_len, d_k, d_v = 4, 8, 8
    Q = rng.standard_normal((seq_len, d_k))
    K = rng.standard_normal((seq_len, d_k))
    V = rng.standard_normal((seq_len, d_v))

    output, weights = attention(Q, K, V)

    print("Attention weights (each row should sum to 1):")
    print(np.round(weights, 3))
    print("\nRow sums:", np.round(weights.sum(axis=1), 6))
    print("\nOutput shape:", output.shape, "(expected (seq_len, d_v))")

    assert weights.shape == (seq_len, seq_len), "weights must be (n, n)"
    assert output.shape == (seq_len, d_v), "output must be (n, d_v)"
    assert np.allclose(weights.sum(axis=1), 1.0), "each weight row must sum to 1"
    print("\nAll checks passed. ✅")


if __name__ == "__main__":
    main()
