"""
Task 5 🔴 — KV cache intuition: cached vs uncached autoregressive loop.

What you'll learn:
  - Why attention is O(n²) without caching but amortised O(n) with it
  - The concrete computational savings the KV cache provides
  - How a toy autoregressive loop mirrors real transformer generation

The toy model:
  - A fixed random embedding matrix (E[token_id] = random vector of dim D)
  - A fixed random key projection matrix W_k ∈ ℝ^{D × D}
  - "Attention" = dot products of the new token's query with all past keys
  - NO learning — the weights are fixed. This is purely about the generation loop.

Two modes:
  UNCACHED: at step t, recompute ALL t key vectors from scratch.
  CACHED:   at step t, extend the cache with only the NEW token's key.

Computation count:
  Uncached total: 1 + 2 + ... + N = N*(N+1)/2
  Cached total:   N  (one key per step)

For N=100: uncached = 5,050 key computations; cached = 100. That's 50× fewer.
In real transformers the savings are even larger because each key computation
is a full matrix multiply, not a single vector projection.

How to run:
  uv run python modules/14-local-inference-optimization/py/05_kv_cache.py

The harness is RUNNABLE. You implement the marked TODO sections.
"""

from __future__ import annotations

import time
import numpy as np

# ---------------------------------------------------------------------------
# Toy model constants
# ---------------------------------------------------------------------------

DIM = 64         # embedding dimension
VOCAB_SIZE = 100  # toy vocabulary size
SEQ_LEN = 100    # sequence length to generate

# Fixed random matrices (weights are NOT learned in this toy — that's fine,
# we just need something to compute so we can measure the loop's work)
rng = np.random.default_rng(42)
EMBED_MATRIX = rng.standard_normal((VOCAB_SIZE, DIM)).astype(np.float32)  # [V, D]
W_K = rng.standard_normal((DIM, DIM)).astype(np.float32)                  # [D, D]
W_Q = rng.standard_normal((DIM, DIM)).astype(np.float32)                  # [D, D]

# "Generated" token sequence (fixed — we're not actually sampling, just benchmarking)
TOKENS = rng.integers(0, VOCAB_SIZE, size=SEQ_LEN).tolist()


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def embed(token_id: int) -> np.ndarray:
    """
    Return the embedding for `token_id`.

    Shape: [DIM]

    TODO: return EMBED_MATRIX[token_id].
    """
    # TODO: implement embed
    raise NotImplementedError("TODO: implement embed()")


def compute_key(token_id: int) -> np.ndarray:
    """
    Compute the key vector for `token_id`.

    Formula: k = W_K @ embed(token_id)
    Shape: [DIM]

    This represents the "project token to key space" operation in real attention.

    TODO: return W_K @ embed(token_id).
    """
    # TODO: implement compute_key
    raise NotImplementedError("TODO: implement compute_key()")


def compute_query(token_id: int) -> np.ndarray:
    """
    Compute the query vector for `token_id`.

    Formula: q = W_Q @ embed(token_id)
    Shape: [DIM]

    TODO: return W_Q @ embed(token_id).
    """
    # TODO: implement compute_query
    raise NotImplementedError("TODO: implement compute_query()")


# ---------------------------------------------------------------------------
# Attention — uncached
# ---------------------------------------------------------------------------


def attention_uncached(
    tokens_so_far: list[int],
    new_token_id: int,
) -> tuple[np.ndarray, int]:
    """
    Compute attention for `new_token_id` by recomputing ALL past key vectors.

    This is the NAIVE approach: at each step, we loop over every past token
    and recompute its key from scratch. This is O(t) key computations at step t.

    Returns:
      (attention_output, key_computations)

    `attention_output` is the weighted sum of past values (we reuse keys as
    values for simplicity). `key_computations` is the count of key vectors
    computed this step (= len(tokens_so_far) + 1 for the new token itself).

    TODO:
      1. Compute the query for new_token_id.
      2. For each token in tokens_so_far + [new_token_id], compute its key.
         Keep count: key_computations = len(tokens_so_far) + 1
      3. Stack keys into a matrix: K ∈ ℝ^{t × DIM}
      4. Compute attention scores: scores = K @ query (shape [t])
         Apply softmax: weights = exp(scores - max(scores)) / sum(...)
      5. Compute output: attention_output = weights @ K (shape [DIM])
      6. Return (attention_output, key_computations).
    """
    # TODO: implement attention_uncached
    raise NotImplementedError("TODO: implement attention_uncached()")


# ---------------------------------------------------------------------------
# Attention — cached
# ---------------------------------------------------------------------------


def attention_cached(
    kv_cache: list[np.ndarray],
    new_token_id: int,
) -> tuple[np.ndarray, list[np.ndarray], int]:
    """
    Compute attention for `new_token_id` using the KV cache.

    This is the EFFICIENT approach: past keys are already computed and stored
    in `kv_cache`. We only compute 1 new key for the new token.

    Returns:
      (attention_output, updated_kv_cache, key_computations)

    `key_computations` is ALWAYS 1: just the new token's key.

    TODO:
      1. Compute query for new_token_id.
      2. Compute key for new_token_id (1 computation only).
      3. Append it to a copy of kv_cache to get updated_cache.
      4. Stack all keys: K = np.stack(updated_cache)  [t × DIM]
      5. Compute attention scores, softmax weights, output — same as uncached.
      6. Return (attention_output, updated_cache, 1).
    """
    # TODO: implement attention_cached
    raise NotImplementedError("TODO: implement attention_cached()")


# ---------------------------------------------------------------------------
# Full generation loops
# ---------------------------------------------------------------------------


def generate_uncached(tokens: list[int]) -> tuple[float, int]:
    """
    Run the full generation loop WITHOUT KV cache.

    For each new token (from index 1 onwards), call attention_uncached with
    all prior tokens.

    Returns (elapsed_seconds, total_key_computations).

    TODO:
      1. Start timer.
      2. total_key_comps = 0
      3. For t in range(1, len(tokens)):
           _, comps = attention_uncached(tokens[:t], tokens[t])
           total_key_comps += comps
      4. Return (elapsed, total_key_comps).
    """
    # TODO: implement generate_uncached
    raise NotImplementedError("TODO: implement generate_uncached()")


def generate_cached(tokens: list[int]) -> tuple[float, int]:
    """
    Run the full generation loop WITH KV cache.

    Maintain a growing kv_cache list. At each step, pass the current cache
    and get back the updated one.

    Returns (elapsed_seconds, total_key_computations).

    TODO:
      1. Start timer.
      2. kv_cache = []
         total_key_comps = 0
      3. For t in range(len(tokens)):
           _, kv_cache, comps = attention_cached(kv_cache, tokens[t])
           total_key_comps += comps
      4. Return (elapsed, total_key_comps).
    """
    # TODO: implement generate_cached
    raise NotImplementedError("TODO: implement generate_cached()")


# ---------------------------------------------------------------------------
# Speedup measurement
# ---------------------------------------------------------------------------


def measure_speedup(tokens: list[int]) -> None:
    """
    Generate the sequence twice (uncached and cached) and report the speedup.

    Also verify:
      - Uncached total key computations == N*(N+1)/2
      - Cached total key computations == N

    TODO:
      1. Run generate_uncached(tokens) and generate_cached(tokens).
      2. Print a table:
           Mode        | Key computations | Time (s) | Speedup
           Uncached    | 5050             | 0.234    | 1.0×
           Cached      | 100              | 0.012    | 19.5×
      3. Verify expected counts with assert statements.
    """
    n = len(tokens)
    expected_uncached = n * (n + 1) // 2
    expected_cached = n
    # TODO: implement measure_speedup
    raise NotImplementedError("TODO: implement measure_speedup()")


# ---------------------------------------------------------------------------
# Harness — RUNNABLE, do not modify
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("KV CACHE INTUITION")
    print("=" * 60)

    print(f"\nSequence length : {SEQ_LEN}")
    print(f"Embedding dim   : {DIM}")
    print(f"Expected uncached key computations: {SEQ_LEN * (SEQ_LEN + 1) // 2:,}")
    print(f"Expected cached key computations  : {SEQ_LEN}")
    print(f"Theoretical savings: {SEQ_LEN * (SEQ_LEN + 1) // 2 / SEQ_LEN:.1f}× fewer")

    print("\nRunning uncached and cached loops...")
    measure_speedup(TOKENS)

    print(
        "\nKey insight: in a real transformer, each 'key computation' is a full"
        "\nmatrix multiply (token embedding × Wk). For a 7B model with 32 attention"
        "\nheads × 128-dim keys × 4096-dim embeddings, this is ~17M FLOPs per token."
        "\nCaching saves all of that for past tokens."
        "\n"
        "\nWhy context length is quadratic without KV cache:"
        "\n  At step t: O(t) attention work"
        "\n  Total for N steps: O(N²)"
        "\nWith KV cache:"
        "\n  At step t: O(1) new key + O(t) dot products"
        "\n  But key COMPUTATION is only O(N) total."
    )


if __name__ == "__main__":
    main()
