"""
Task 3 🔴 — Gradient boosting (least squares) with decision stumps.

What you'll learn:
  - Boosting = building a strong model as a SUM of weak ones, each trained to
    fix what the running sum still gets wrong.
  - For squared-error loss the "what's still wrong" is literally the residual
    y - F(x) — and the residual IS the negative gradient of the loss w.r.t.
    the model's outputs. Boosting is gradient descent in function space.
  - The learning rate (shrinkage) ν: smaller steps, more rounds, better
    generalisation.
  - Early stopping: train MSE falls forever, validation MSE traces a U-curve —
    you stop at its bottom.

The math (README derives each step):

  Model after m rounds:      F_m(x) = F_0 + ν · Σ_{k=1..m} h_k(x),  F_0 = ȳ
  Squared-error loss:        L = ½ Σ_i (y_i - F(x_i))²
  Its negative gradient:     -∂L/∂F(x_i) = y_i - F(x_i)   ← the residual!
  Each round:                h_m = fit_stump(x, y - F_{m-1});  F_m = F_{m-1} + ν·h_m

  A regression STUMP is the weakest tree: one threshold t, two leaf values —
      h(x) = mean(r | x ≤ t)  if x ≤ t   else   mean(r | x > t)
  The best t minimises the two-sided SSE:
      SSE(t) = Σ_{x≤t} (r - mean_left)² + Σ_{x>t} (r - mean_right)²

You implement: fit_stump and boost (including recording per-round train/val
MSE and picking the best round by validation MSE — early stopping). The noisy
1-D sinusoid data, stump_predict, the truncated-model predictor, and the
harness are provided and runnable.

How to run:
  uv run python modules/01e-trees-ensembles/py/03_gradient_boosting.py
"""

from __future__ import annotations

import numpy as np

SEED = 33
N_TRAIN = 80
N_VAL = 150
NOISE_STD = 0.35
N_ROUNDS = 500
LR = 0.3  # shrinkage ν


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    1-D regression:  y = sin(2x) + ε,  x uniform in [-3, 3],  ε ~ N(0, 0.35²).
    A small train set (80 points) so that enough boosting rounds visibly
    overfit. Returns: x_train, y_train, x_val, y_val.
    """
    rng = np.random.default_rng(SEED)
    x = rng.uniform(-3.0, 3.0, size=N_TRAIN + N_VAL)
    y = np.sin(2.0 * x) + rng.normal(0.0, NOISE_STD, size=x.size)
    return x[:N_TRAIN], y[:N_TRAIN], x[N_TRAIN:], y[N_TRAIN:]


def stump_predict(stump: tuple[float, float, float], x: np.ndarray) -> np.ndarray:
    """
    Evaluate a stump (threshold, left_value, right_value) on every point:
    left_value where x ≤ threshold, right_value elsewhere.  (provided)
    """
    t, left_v, right_v = stump
    return np.where(x <= t, left_v, right_v)


def boosted_predict(
    f0: float, stumps: list[tuple[float, float, float]], x: np.ndarray, lr: float, n: int
) -> np.ndarray:
    """Evaluate the boosted model truncated at n rounds: F0 + lr·Σ_{k<n} h_k(x)."""
    F = np.full(x.shape, f0)
    for stump in stumps[:n]:
        F = F + lr * stump_predict(stump, x)
    return F


def mse(pred: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((pred - y) ** 2))


# ---------------------------------------------------------------------------
# Core functions — YOU implement these two
# ---------------------------------------------------------------------------


def fit_stump(x: np.ndarray, residuals: np.ndarray) -> tuple[float, float, float]:
    """
    Fit the best single-threshold regression stump to (x, residuals).

    Candidate thresholds = midpoints between consecutive sorted unique x
    values. For each threshold t the two leaf values are the MEANS of the
    residuals on each side (the SSE-optimal constant per side); the stump's
    score is the summed SSE of both sides. Return the argmin.

    Returns: (threshold, left_value, right_value) — floats.

    TODO: implement.
      1. Sort the unique x values; midpoints of consecutive pairs are the
         candidate thresholds.
      2. For each t: mask the points with x ≤ t, take each side's residual
         mean, and score the split by the two-sided SSE formula above (skip a
         side-emptying t — midpoints of unique values never produce one).
      3. Track the best (t, left_mean, right_mean) and return it.
    """
    # TODO: implement the stump search
    raise NotImplementedError("TODO: implement fit_stump()")


def boost(
    x: np.ndarray,
    y: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    n_rounds: int,
    lr: float,
) -> tuple[float, list[tuple[float, float, float]], list[float], list[float], int]:
    """
    Least-squares gradient boosting with stumps + early-stopping pick.

    Algorithm:
      F0 = mean of y (the best constant); running predictions F_train, F_val
      start there. Each round:
        1. residuals = y - F_train          (the negative gradient!)
        2. h = fit_stump(x, residuals)
        3. F_train += lr · h(x);  F_val += lr · h(x_val)   (stump_predict)
        4. record mse(F_train, y) and mse(F_val, y_val)
      After the loop, the BEST round = the 1-based index of the smallest
      recorded validation MSE (np.argmin) — that's where early stopping
      would halt.

    Returns: (f0, stumps, train_mse, val_mse, best_round)
      f0         : float — the initial constant prediction
      stumps     : list of n_rounds (threshold, left, right) tuples
      train_mse  : list of n_rounds floats (after each round)
      val_mse    : list of n_rounds floats
      best_round : int in [1, n_rounds] — argmin of val_mse, 1-based

    TODO: implement (follow the numbered algorithm above).
    """
    # TODO: implement the boosting loop + early-stopping pick
    raise NotImplementedError("TODO: implement boost()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 3 — Gradient boosting (least squares) with stumps\n")

    x_train, y_train, x_val, y_val = make_data()
    print(f"  Data: y = sin(2x) + N(0, {NOISE_STD}²), {N_TRAIN} train / {N_VAL} val\n")

    # ── Baseline: one lonely stump ───────────────────────────────────────────
    print("[1/2] Baseline: a single stump fit to y...")
    lone = fit_stump(x_train, y_train)
    lone_val = mse(stump_predict(lone, x_val), y_val)
    print(f"  stump: threshold = {lone[0]:+.3f}, leaves = ({lone[1]:+.3f}, {lone[2]:+.3f})")
    print(f"  val MSE = {lone_val:.4f}\n")

    # ── Boosting ─────────────────────────────────────────────────────────────
    print(f"[2/2] Boosting: {N_ROUNDS} rounds, lr = {LR}...")
    f0, stumps, train_mse, val_mse, best_round = boost(x_train, y_train, x_val, y_val, N_ROUNDS, LR)
    print(f"  F0 (mean of y) = {f0:+.4f}")
    for r in (1, 5, 20, 50, 100, best_round, N_ROUNDS):
        print(
            f"  round {r:>4}: train MSE = {train_mse[r - 1]:.4f}   val MSE = {val_mse[r - 1]:.4f}"
        )

    best_val = val_mse[best_round - 1]
    final_val = val_mse[-1]
    boosted_best = mse(boosted_predict(f0, stumps, x_val, LR, best_round), y_val)
    monotone = all(train_mse[i + 1] <= train_mse[i] + 1e-9 for i in range(len(train_mse) - 1))
    print(f"\n  best round (early stop) = {best_round}  (val MSE = {best_val:.4f})")
    print(f"  final round val MSE     = {final_val:.4f}  (the U-curve turned back up)")
    print(f"  train MSE non-increasing = {monotone}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_monotone = monotone
    ok_ucurve = best_round < N_ROUNDS and final_val > best_val + 1e-6
    ok_beats_stump = boosted_best < 0.5 * lone_val
    print(f"  [{'x' if ok_monotone else ' '}] train MSE non-increasing over all rounds")
    print(
        f"  [{'x' if ok_ucurve else ' '}] val MSE bottoms out BEFORE the last round "
        f"(round {best_round} < {N_ROUNDS}; U-curve visible)"
    )
    print(
        f"  [{'x' if ok_beats_stump else ' '}] boosted val MSE ≪ single-stump val MSE "
        f"({boosted_best:.4f} < 0.5 × {lone_val:.4f})"
    )

    if ok_monotone and ok_ucurve and ok_beats_stump:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
