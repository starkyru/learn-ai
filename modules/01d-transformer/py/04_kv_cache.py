"""
Task 4 🟡 — The KV cache: why generation isn't O(n^2) per token.

What you'll learn:
  - How autoregressive decoding actually works: tokens are produced ONE AT A TIME,
    each attending over everything generated so far.
  - The naive way recomputes keys and values for the ENTIRE prefix at every step —
    O(n^2) key/value projections over a length-n generation. Wasteful: the keys and
    values for old tokens never change.
  - The KV cache stores each token's key and value ONCE. At step t you project only
    the new token's q, k, v, APPEND its k, v to the cache, and attend the single new
    query over ALL cached keys/values. That's O(n) projections total — the reason
    real LLM inference is fast (and the reason context length costs memory).

This is the module's most-asked interview topic: "explain the KV cache and attention
masking." You will prove the cached path yields IDENTICAL logits to the naive recompute.

The math (single-head causal self-attention):

  At step t (0-based), with the prefix x[0..t] already known:
    q_t     = x_t @ Wq                         (this token's query)
    k_i     = x_i @ Wk,  v_i = x_i @ Wv        for every i <= t
    scores  = q_t . k_i / sqrt(d)  for i in 0..t
    weights = softmax(scores)
    context = sum_i weights_i * v_i
    logits  = context @ Wo

  Naive:  recompute every k_i, v_i (i in 0..t) from scratch at each step t.
  Cached: k_i, v_i for i < t were computed at earlier steps and stored; only k_t, v_t
          are new. Append them; attend over the whole cache.

No ML library. Only numpy.

How to run:
  uv run python modules/01d-transformer/py/04_kv_cache.py

The harness feeds a length-n sequence one token at a time through both paths and
checks the per-step logits match. `decode_with_cache` and its op counting are TODOs.
"""

from __future__ import annotations

import numpy as np


def softmax(z: np.ndarray) -> np.ndarray:
    """Numerically-stable softmax over the last axis. Provided."""
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


# ---------------------------------------------------------------------------
# Naive path (provided): recompute the whole prefix every step.
# ---------------------------------------------------------------------------


def decode_naive(
    X: np.ndarray, Wq: np.ndarray, Wk: np.ndarray, Wv: np.ndarray, Wo: np.ndarray
) -> tuple[np.ndarray, int]:
    """
    Naive causal decoding: at each step t, RE-PROJECT keys/values for the whole
    prefix x[0..t] from scratch, then attend.

    Returns:
      logits    : (n, d_out) — the output logits at each step
      kv_ops    : number of key-projection operations performed (one per row
                  projected through Wk). For a length-n sequence this is
                  1 + 2 + ... + n = n(n+1)/2, because step t reprojects t+1 rows.

    This function is COMPLETE and serves as the ground truth. Study it, then make
    decode_with_cache produce identical logits with far fewer projections.
    """
    n, d = X.shape
    d_k = Wq.shape[1]
    logits_out = []
    kv_ops = 0

    for t in range(n):
        prefix = X[: t + 1]  # rows 0..t, shape (t+1, d)
        q_t = X[t] @ Wq  # (d_k,)  — just the new token's query
        K = prefix @ Wk  # (t+1, d_k)  — RE-PROJECTED every step
        V = prefix @ Wv  # (t+1, d_v)  — RE-PROJECTED every step
        kv_ops += t + 1  # projected t+1 key rows this step

        scores = (K @ q_t) / np.sqrt(d_k)  # (t+1,)
        weights = softmax(scores)  # (t+1,)
        context = weights @ V  # (d_v,)
        logits_out.append(context @ Wo)  # (d_out,)

    return np.array(logits_out), kv_ops


# ---------------------------------------------------------------------------
# Cached path — implement this
# ---------------------------------------------------------------------------


def decode_with_cache(
    X: np.ndarray, Wq: np.ndarray, Wk: np.ndarray, Wv: np.ndarray, Wo: np.ndarray
) -> tuple[np.ndarray, int]:
    """
    Incremental causal decoding with a KV cache.

    Maintain a growing list of cached keys and values. At each step t:
      - project ONLY the new token x[t] into q_t, k_t, v_t
      - APPEND k_t, v_t to the cache
      - attend q_t over ALL cached keys/values (the causal prefix, for free)

    Returns:
      logits : (n, d_out) — must equal decode_naive's logits exactly
      kv_ops : number of key-projection operations. With the cache you project
               exactly ONE new key per step, so for a length-n sequence kv_ops == n.

    TODO: implement.
      1. d_k = Wq.shape[1]. Initialise empty caches:
           K_cache = []   # will hold each token's key vector (d_k,)
           V_cache = []   # will hold each token's value vector (d_v,)
         and kv_ops = 0, logits_out = [].
      2. For t in range(len(X)):
           x_t = X[t]                       # the one new token, shape (d,)
           q_t = x_t @ Wq                   # (d_k,)
           k_t = x_t @ Wk                   # (d_k,)   — ONE key projection
           v_t = x_t @ Wv                   # (d_v,)
           kv_ops += 1                      # exactly one new key this step
           K_cache.append(k_t)
           V_cache.append(v_t)
           K = np.array(K_cache)            # (t+1, d_k) — old keys reused, not recomputed
           V = np.array(V_cache)            # (t+1, d_v)
           scores  = (K @ q_t) / sqrt(d_k)  # (t+1,)
           weights = softmax(scores)        # (t+1,)
           context = weights @ V            # (d_v,)
           logits_out.append(context @ Wo)  # (d_out,)
      3. return np.array(logits_out), kv_ops
    """
    # TODO: implement incremental decoding with a KV cache
    raise NotImplementedError("TODO: implement decode_with_cache()")


# ---------------------------------------------------------------------------
# Harness — complete, do not edit
# ---------------------------------------------------------------------------


def seeded_weights(rows: int, cols: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, 1.0 / np.sqrt(rows), (rows, cols))


def main() -> None:
    rng = np.random.default_rng(0)
    n = 7  # sequence length
    d = 8  # model dim
    d_k = 8  # key/query/value dim
    d_out = 8  # output dim

    X = rng.standard_normal((n, d))
    Wq = seeded_weights(d, d_k, 1)
    Wk = seeded_weights(d, d_k, 2)
    Wv = seeded_weights(d, d_k, 3)
    Wo = seeded_weights(d_k, d_out, 4)

    print("=" * 66)
    print("Task 4 — KV cache: incremental decoding vs naive recompute")
    print("=" * 66)
    print(f"  sequence length n={n}  d={d}  d_k={d_k}\n")

    logits_naive, ops_naive = decode_naive(X, Wq, Wk, Wv, Wo)
    logits_cached, ops_cached = decode_with_cache(X, Wq, Wk, Wv, Wo)

    # ── Check 1: identical per-step logits ────────────────────────────────────
    per_step_ok = True
    print("[1] Per-step logit agreement (naive vs cached):")
    for t in range(n):
        same = np.allclose(logits_naive[t], logits_cached[t], atol=1e-5)
        per_step_ok = per_step_ok and same
        diff = float(np.max(np.abs(logits_naive[t] - logits_cached[t])))
        print(f"    step {t}: match={same}  max|Δ|={diff:.2e}")
    all_ok = bool(np.allclose(logits_naive, logits_cached, atol=1e-5))
    print(f"    all steps identical: {all_ok}\n")

    # ── Check 2: op-count comparison ──────────────────────────────────────────
    expected_naive = n * (n + 1) // 2
    print("[2] Key-projection operation counts:")
    print(
        f"    naive  (recompute prefix each step): {ops_naive}   expected n(n+1)/2 = {expected_naive}"
    )
    print(f"    cached (one new key per step)      : {ops_cached}   expected n = {n}")
    ops_ok = ops_naive == expected_naive and ops_cached == n
    speedup = ops_naive / max(ops_cached, 1)
    print(f"    cache saves {ops_naive - ops_cached} projections ({speedup:.1f}x fewer)\n")

    assert all_ok, "cached logits must equal naive logits at every step"
    assert per_step_ok, "each step's logits must match within atol=1e-5"
    assert ops_ok, "op counts must be n (cached) and n(n+1)/2 (naive)"
    print("All checks passed. ✅")


if __name__ == "__main__":
    main()
