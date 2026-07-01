"""
Task 1 🟡 — Linear regression: the normal equation AND gradient descent.

What you'll learn:
  - The closed-form "normal equation" solution: w = (XᵀX)^{-1} Xᵀy
  - How to solve it stably with np.linalg.solve (never form the inverse)
  - Gradient descent for MSE: the same answer, found iteratively
  - R² (coefficient of determination) as a scale-free goodness-of-fit score

The math (README derives each step):

  Model:            ŷ = X w         (bias absorbed as a column of 1s in X)
  Loss (MSE):       L(w) = (1/N) · ||X w - y||²
  Gradient of MSE:  ∇L  = (2/N) · Xᵀ (X w - y)
  Setting ∇L = 0 :  XᵀX w = Xᵀ y   →   the "normal equation"

  Gradient-descent update:   w ← w - lr · ∇L

  R²:   1 - SS_res / SS_tot ,  where
        SS_res = Σ (y_i - ŷ_i)²   (what the model still gets wrong)
        SS_tot = Σ (y_i - ȳ)²     (variance around the mean baseline)
        R² = 1 → perfect ; R² = 0 → no better than predicting the mean.

You implement the four core numpy functions (normal_equation, predict,
mse_loss, gradient_step). Everything else — synthetic data, standardisation,
the training loop, and the R² report — is provided and runnable.

How to run:
  uv run python modules/01b-ml-foundations/py/01_linear_regression.py
"""

from __future__ import annotations

import numpy as np

SEED = 7
N = 200  # samples
D = 3  # real features (a bias column is prepended → design matrix is N×(D+1))


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Generate  y = X_raw @ w_true + b_true + gaussian_noise.

    Returns:
      X_raw  : (N, D) raw feature matrix (unstandardised)
      y      : (N,)   targets
      w_true : (D,)   the weights we secretly used
      b_true : float  the intercept we secretly used
    """
    rng = np.random.default_rng(SEED)
    X_raw = rng.normal(0.0, 1.0, size=(N, D))
    w_true = np.array([2.0, -3.0, 0.5])
    b_true = 4.0
    noise = rng.normal(0.0, 0.5, size=N)
    y = X_raw @ w_true + b_true + noise
    return X_raw, y, w_true, b_true


def standardize(X: np.ndarray) -> np.ndarray:
    """Zero-mean, unit-variance per column. Keeps gradient descent well-scaled."""
    mean = X.mean(axis=0, keepdims=True)
    std = X.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    return (X - mean) / std


def add_bias_column(X: np.ndarray) -> np.ndarray:
    """Prepend a column of 1s so w[0] plays the role of the intercept b."""
    ones = np.ones((X.shape[0], 1), dtype=X.dtype)
    return np.hstack([ones, X])


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def normal_equation(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    Closed-form least squares:  w = (XᵀX)^{-1} Xᵀ y.

    IMPORTANT: never compute the inverse explicitly (np.linalg.inv is slower and
    numerically worse). Instead assemble the linear system  (XᵀX) w = Xᵀy  and
    hand it to np.linalg.solve, which does an LU factorisation.

    X here already includes the bias column (shape N×(D+1)); the returned w has
    length D+1, with w[0] the intercept.

    TODO: implement.
      1. A = X.T @ X            # shape (D+1, D+1)
      2. b = X.T @ y            # shape (D+1,)
      3. return np.linalg.solve(A, b)
    """
    # TODO: implement the normal equation via np.linalg.solve
    raise NotImplementedError("TODO: implement normal_equation()")


def predict(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    """
    Linear prediction:  ŷ = X @ w.

    X includes the bias column, so no separate intercept term is needed.

    TODO: implement (one line: X @ w).
    """
    # TODO: implement the linear prediction
    raise NotImplementedError("TODO: implement predict()")


def mse_loss(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """
    Mean squared error:  L = (1/N) · Σ (ŷ_i - y_i)².

    TODO: implement.
      1. resid = predict(X, w) - y
      2. return float(np.mean(resid ** 2))
    """
    # TODO: implement mean squared error
    raise NotImplementedError("TODO: implement mse_loss()")


def gradient_step(X: np.ndarray, y: np.ndarray, w: np.ndarray, lr: float) -> np.ndarray:
    """
    One gradient-descent step for MSE.

    Gradient:   ∇L = (2/N) · Xᵀ (X w - y)
    Update:     w_new = w - lr · ∇L

    Return the UPDATED weight vector (do not mutate the input in place — the
    training loop reassigns w = gradient_step(...)).

    TODO: implement.
      1. N = X.shape[0]
      2. resid = predict(X, w) - y          # shape (N,)
      3. grad  = (2.0 / N) * (X.T @ resid)  # shape (D+1,)
      4. return w - lr * grad
    """
    # TODO: implement one gradient-descent update
    raise NotImplementedError("TODO: implement gradient_step()")


# ---------------------------------------------------------------------------
# R²  (provided — uses your predict())
# ---------------------------------------------------------------------------


def r_squared(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """R² = 1 - SS_res / SS_tot. 1.0 is perfect, 0.0 is mean-baseline."""
    y_hat = predict(X, w)
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return 1.0 - ss_res / ss_tot


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 1 — Linear regression: normal equation vs gradient descent\n")

    X_raw, y, w_true, b_true = make_data()
    print(f"  Data: N={N}, D={D}")
    print(f"  True weights: {w_true}   True bias: {b_true}")

    # Standardise features, then add the bias column.
    X = add_bias_column(standardize(X_raw))
    print(f"  Design matrix (with bias col): {X.shape}\n")

    # ── Closed form ──────────────────────────────────────────────────────────
    print("[1/2] Normal equation (closed form)...")
    w_normal = normal_equation(X, y)
    print(f"  w_normal = {np.round(w_normal, 4)}")
    print(f"  MSE      = {mse_loss(X, y, w_normal):.4f}")
    print(f"  R²       = {r_squared(X, y, w_normal):.4f}\n")

    # ── Gradient descent ─────────────────────────────────────────────────────
    print("[2/2] Gradient descent...")
    rng = np.random.default_rng(SEED)
    w_gd = rng.normal(0.0, 0.1, size=X.shape[1])  # small random init
    lr = 0.1
    epochs = 300

    loss_history: list[float] = []
    for _ in range(epochs):
        loss_history.append(mse_loss(X, y, w_gd))
        w_gd = gradient_step(X, y, w_gd, lr)

    final_loss = mse_loss(X, y, w_gd)

    # Is the loss monotonically decreasing over the first 30 epochs?
    first30 = loss_history[:30]
    monotonic = all(first30[i + 1] <= first30[i] + 1e-9 for i in range(len(first30) - 1))

    # How close did GD get to the closed-form optimum?
    dist = float(np.linalg.norm(w_gd - w_normal))
    r2_gd = r_squared(X, y, w_gd)

    for e in (1, 10, 50, 150, epochs):
        print(f"  epoch {e:>4}: MSE={loss_history[e - 1]:.4f}")
    print(f"\n  w_gd     = {np.round(w_gd, 4)}")
    print(f"  final MSE (GD)          = {final_loss:.4f}")
    print(f"  ||w_gd - w_normal||     = {dist:.4f}")
    print(f"  R² (GD)                 = {r2_gd:.4f}")
    print(f"  loss monotone (first 30)= {monotonic}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_converge = dist < 0.1
    ok_monotone = monotonic
    ok_r2 = r2_gd > 0.9
    print(
        f"  [{'x' if ok_converge else ' '}] GD converges to normal eq  (||Δw|| = {dist:.4f} < 0.1)"
    )
    print(f"  [{'x' if ok_monotone else ' '}] MSE decreases monotonically over first 30 epochs")
    print(f"  [{'x' if ok_r2 else ' '}] R² > 0.9  (R² = {r2_gd:.4f})")

    if ok_converge and ok_monotone and ok_r2:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
