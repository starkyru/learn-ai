"""
Task 5 🔴 — Understand LoRA: implement the low-rank update from scratch.

What you'll learn:
  - The LoRA math at the level of matrix algebra (no magic, no framework)
  - Why B·A starts at zero (B initialised to zero, A random)
  - Exactly how many parameters LoRA saves vs full fine-tuning
  - Numerical verification that (W + B@A)@x equals W@x + B@(A@x)

No ML framework imports. Only numpy.

The math:
  A weight update ΔW ∈ ℝ^{d_out × d_in} has d_out * d_in parameters.
  LoRA represents it as ΔW = B · A  where:
    B ∈ ℝ^{d_out × r}   (r << d_out)
    A ∈ ℝ^{r  × d_in}   (r << d_in)

  B is initialised to zero.  So at the start of training, ΔW = 0 and the
  model's output is unchanged — a safe, stable starting point.

  A is initialised with small random values (standard normal * 0.01).

  At inference:
    adapted_output = W @ x + B @ A @ x
                   = (W + B @ A) @ x       ← same result, different order

  Parameter count:
    Full fine-tune : d_out * d_in
    LoRA           : r * d_in   (A)  +  d_out * r   (B)
                   = r * (d_in + d_out)

  For d=4096, r=16:
    Full   : 4096 * 4096 = 16,777,216
    LoRA   : 16 * (4096 + 4096) = 131,072
    Ratio  : 16.7M / 131K ≈ 128× fewer parameters

How to run:
  uv run python modules/13-fine-tuning/py/05_lora_scratch.py

The harness is RUNNABLE. You implement the marked TODO sections.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# LoRA initialisation
# ---------------------------------------------------------------------------


def lora_init(
    d_out: int,
    d_in: int,
    r: int,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Initialise LoRA adapter matrices A and B.

    Returns:
      A : shape [r, d_in]    — random normal * 0.01
      B : shape [d_out, r]   — zeros

    This initialisation is important:
      - B = 0 means ΔW = B@A = 0 at the start of training.
        The model's output is UNCHANGED at step 0, which makes fine-tuning stable.
      - A is non-zero so gradients flow immediately from step 1.

    TODO:
      1. Set numpy random seed to `seed`.
      2. A = np.random.randn(r, d_in) * 0.01
      3. B = np.zeros((d_out, r))
      4. Return (A, B).
    """
    # TODO: implement lora_init
    raise NotImplementedError("TODO: implement lora_init()")


# ---------------------------------------------------------------------------
# LoRA forward pass
# ---------------------------------------------------------------------------


def lora_forward(
    x: np.ndarray,   # shape [d_in] or [d_in, batch]
    W: np.ndarray,   # shape [d_out, d_in]   — frozen pre-trained weight
    A: np.ndarray,   # shape [r, d_in]
    B: np.ndarray,   # shape [d_out, r]
) -> np.ndarray:
    """
    Compute the LoRA-adapted output for input x.

    Formula:
      output = W @ x + B @ (A @ x)
             = (W + B @ A) @ x       ← mathematically identical

    TODO:
      Implement: return W @ x + B @ (A @ x)

    This is the heart of LoRA: the base weight W stays frozen; only B and A
    change during training, contributing a low-rank correction to the output.
    """
    # TODO: implement lora_forward
    raise NotImplementedError("TODO: implement lora_forward()")


# ---------------------------------------------------------------------------
# Parameter counting
# ---------------------------------------------------------------------------


def count_params(d_out: int, d_in: int, r: int) -> dict[str, int]:
    """
    Return parameter counts for full fine-tuning vs LoRA.

    Returns a dict with keys:
      "full" : d_out * d_in
      "lora" : r * (d_in + d_out)

    TODO: implement the two formulas.
    """
    # TODO: implement count_params
    raise NotImplementedError("TODO: implement count_params()")


# ---------------------------------------------------------------------------
# Numerical equivalence check
# ---------------------------------------------------------------------------


def verify_equivalence(
    W: np.ndarray,
    A: np.ndarray,
    B: np.ndarray,
    x: np.ndarray,
    tol: float = 1e-9,
) -> bool:
    """
    Check that (W + B@A) @ x equals W @ x + B @ (A @ x) to within `tol`.

    These two expressions are algebraically identical but floating-point
    arithmetic can introduce tiny differences. They should be << 1e-9.

    Returns True if the max absolute difference is < tol.

    TODO:
      1. Compute out1 = (W + B @ A) @ x
      2. Compute out2 = W @ x + B @ (A @ x)
      3. Return np.max(np.abs(out1 - out2)) < tol
    """
    # TODO: implement verify_equivalence
    raise NotImplementedError("TODO: implement verify_equivalence()")


# ---------------------------------------------------------------------------
# Zero-at-init check
# ---------------------------------------------------------------------------


def verify_zero_at_init(
    W: np.ndarray,
    A: np.ndarray,
    B: np.ndarray,
    x: np.ndarray,
) -> bool:
    """
    Verify that a freshly initialised LoRA adapter contributes zero change.

    Because B is all-zeros at initialisation, B @ A is the zero matrix, and
    the LoRA term B @ (A @ x) is the zero vector. The output of lora_forward
    should equal W @ x exactly.

    Returns True if the LoRA correction is exactly zero.

    TODO:
      1. correction = B @ (A @ x)
      2. Return np.allclose(correction, np.zeros_like(correction))
    """
    # TODO: implement verify_zero_at_init
    raise NotImplementedError("TODO: implement verify_zero_at_init()")


# ---------------------------------------------------------------------------
# Parameter savings table
# ---------------------------------------------------------------------------


def param_savings_table() -> None:
    """
    Print a table showing full vs LoRA parameter counts and savings ratio
    for a range of typical model dimensions and ranks.

    Rows: d = 512, 1024, 2048, 4096
    Cols: r = 4, 8, 16, 64

    Format:
      d=512   r=4    full=262,144   lora=4,096   savings=64.0x
      d=512   r=8    full=262,144   lora=8,192   savings=32.0x
      ...

    TODO:
      1. For each (d, r) in the cross product of dims and ranks:
         a. Compute params = count_params(d, d, r)
         b. Print a formatted line.
    """
    dims = [512, 1024, 2048, 4096]
    ranks = [4, 8, 16, 64]
    # TODO: implement param_savings_table
    raise NotImplementedError("TODO: implement param_savings_table()")


# ---------------------------------------------------------------------------
# Harness — RUNNABLE, do not modify
# ---------------------------------------------------------------------------


def main() -> None:
    print("=" * 60)
    print("LoRA FROM SCRATCH")
    print("=" * 60)

    # Small dimensions for fast testing
    d_out, d_in, r = 64, 64, 8

    # Frozen pre-trained weight
    rng = np.random.default_rng(0)
    W = rng.standard_normal((d_out, d_in)).astype(np.float64)
    x = rng.standard_normal(d_in).astype(np.float64)

    print(f"\n1. Initialising LoRA (d_out={d_out}, d_in={d_in}, r={r})...")
    A, B = lora_init(d_out, d_in, r, seed=42)
    print(f"   A shape: {A.shape}, B shape: {B.shape}")
    print(f"   A stats: mean={A.mean():.4f}, std={A.std():.4f}")
    print(f"   B is all zeros: {np.all(B == 0)}")

    print("\n2. Checking zero-at-init property...")
    ok = verify_zero_at_init(W, A, B, x)
    print(f"   LoRA correction is zero at init: {ok}")
    assert ok, "B should be all zeros so the LoRA term is zero at init!"

    print("\n3. Forward pass...")
    out = lora_forward(x, W, A, B)
    print(f"   Output shape: {out.shape}, norm: {np.linalg.norm(out):.4f}")

    print("\n4. Numerical equivalence check...")
    ok = verify_equivalence(W, A, B, x)
    print(f"   (W + B@A)@x  ==  W@x + B@(A@x): {ok}")
    assert ok, "Equivalence check failed — check your matrix multiply order!"

    print("\n5. Parameter savings:")
    params = count_params(d_out, d_in, r)
    print(f"   Full fine-tune: {params['full']:,} params")
    print(f"   LoRA (r={r}):    {params['lora']:,} params")
    print(f"   Savings: {params['full'] / params['lora']:.1f}x")

    print("\n6. Parameter savings table:")
    param_savings_table()

    print("\nAll checks passed!")


if __name__ == "__main__":
    main()
