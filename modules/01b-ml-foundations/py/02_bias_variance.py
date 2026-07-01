"""
Task 2 🔴 — Bias–variance tradeoff, k-fold CV, and ridge regularisation.

What you'll learn:
  - Why train error and generalisation error diverge (the U-curve)
  - Bias vs variance: underfitting (high bias) vs overfitting (high variance)
  - k-fold cross-validation as an honest estimate of generalisation error
  - Ridge (L2) regularisation: shrink weights to trade a little bias for a lot
    less variance — WITHOUT regularising the intercept

The math (README derives each step):

  Polynomial features:  for a scalar x, φ(x) = [1, x, x², …, x^d]  (degree d).
  Fitting degree-d least squares means solving the normal equation on Φ.

  Ordinary least squares:   w = (ΦᵀΦ)^{-1} Φᵀ y
  Ridge (L2) least squares: w = (ΦᵀΦ + λ R)^{-1} Φᵀ y
      where R = identity but with R[0,0] = 0 so the bias column (the "1"s)
      is NOT penalised. Penalising the intercept would bias predictions toward 0.

  Bias–variance decomposition of expected test error:
      E[(y - ŷ)²] = bias² + variance + irreducible_noise
    - Low degree → high bias (too simple, underfits both train and test).
    - High degree → high variance (fits noise; great train, poor test).

  k-fold CV: split data into k folds; for each fold, train on the other k-1 and
  score on the held-out fold; average the k MSEs. This estimates test error
  using only training data.

You implement three functions: kfold_indices, ridge_fit, cv_score. Everything
else — the true cubic, polynomial feature builder, the degree sweep, and the
printed U-curve — is provided and runnable.

How to run:
  uv run python modules/01b-ml-foundations/py/02_bias_variance.py
"""

from __future__ import annotations

import numpy as np

SEED = 11
N = 60  # samples
NOISE_STD = 0.6
MAX_DEGREE = 12
K_FOLDS = 5


# ---------------------------------------------------------------------------
# Synthetic data: a true cubic + noise  (provided)
# ---------------------------------------------------------------------------


def true_function(x: np.ndarray) -> np.ndarray:
    """The signal we're trying to recover: a cubic. Test error can't beat the noise."""
    return 0.5 * x**3 - 1.0 * x**2 + 0.5 * x + 2.0


def make_data() -> tuple[np.ndarray, np.ndarray]:
    """Return (x, y) with x in [-3, 3] and y = true_function(x) + gaussian noise."""
    rng = np.random.default_rng(SEED)
    x = np.sort(rng.uniform(-3.0, 3.0, size=N))
    y = true_function(x) + rng.normal(0.0, NOISE_STD, size=N)
    return x, y


# ---------------------------------------------------------------------------
# Polynomial features + prediction  (provided)
# ---------------------------------------------------------------------------


def poly_features(x: np.ndarray, degree: int) -> np.ndarray:
    """
    Build the design matrix Φ with columns [1, x, x², …, x^degree].

    Column 0 is the bias (all 1s). Shape: (len(x), degree + 1).
    """
    return np.vstack([x**p for p in range(degree + 1)]).T


def predict(Phi: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Linear prediction ŷ = Φ w."""
    return Phi @ w


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean squared error."""
    return float(np.mean((y_true - y_pred) ** 2))


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def kfold_indices(n: int, k: int, seed: int = SEED) -> list[np.ndarray]:
    """
    Split indices 0..n-1 into k folds of (nearly) equal size.

    Shuffle a permutation of 0..n-1 with a seeded RNG, then chop it into k
    contiguous chunks. Return a list of k index arrays (the folds).

    TODO: implement.
      - Build a seeded RNG with np.random.default_rng(seed) and get a random
        permutation of 0..n-1 from it.
      - Split that permutation into k roughly-equal folds and return them as a
        list of arrays. Either np.array_split (contiguous chunks) or a strided
        slice like perm[i::k] works — both are valid k-fold splits.
    """
    # TODO: implement the k-fold index split
    raise NotImplementedError("TODO: implement kfold_indices()")


def ridge_fit(Phi: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """
    Ridge (L2-regularised) least squares.

    w = (ΦᵀΦ + λ R)^{-1} Φᵀ y

    R is the identity EXCEPT R[0, 0] = 0, so the bias/intercept column (column 0
    of Φ, which is all 1s) is NOT penalised. lam == 0 recovers ordinary least
    squares.

    Solve the linear system with np.linalg.solve — never form the inverse.

    TODO: implement.
      - Build the penalty matrix R = np.eye(d) but with R[0, 0] = 0.0 so the
        intercept column is not penalised.
      - Assemble the coefficient matrix ΦᵀΦ + λ·R and the right-hand side Φᵀy.
      - Solve that system with np.linalg.solve and return the weights.
    """
    # TODO: implement ridge regression via np.linalg.solve
    raise NotImplementedError("TODO: implement ridge_fit()")


def cv_score(x: np.ndarray, y: np.ndarray, degree: int, lam: float, k: int = K_FOLDS) -> float:
    """
    k-fold cross-validated MSE for a given polynomial degree and ridge lambda.

    For each fold f:
      - the held-out (validation) set is fold f
      - the training set is every OTHER fold concatenated
      - build poly_features on the TRAIN x, ridge_fit, then score MSE on VAL
    Return the mean of the k validation MSEs.

    TODO: implement.
      - Get the folds from kfold_indices(len(x), k).
      - For each fold f: treat it as the validation indices, and concatenate
        every OTHER fold into the training indices.
      - Build poly_features(degree) on the training x, ridge_fit with lam, then
        score mse() on the validation x/y using predict().
      - Return the mean of the per-fold validation MSEs as a float.
    """
    # TODO: implement k-fold CV scoring
    raise NotImplementedError("TODO: implement cv_score()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 2 — Bias–variance, cross-validation, and ridge regularisation\n")

    x, y = make_data()
    print(f"  Data: N={N}   true function: 0.5x³ - x² + 0.5x + 2   noise σ={NOISE_STD}\n")

    # ── Degree sweep: train MSE vs CV MSE (plain OLS, lam=0) ──────────────────
    print("[1/2] Degree sweep (plain least squares, no regularisation):\n")
    print(f"  {'degree':>6} | {'train MSE':>10} | {'CV MSE':>10} | {'||w||':>10}")
    print(f"  {'-' * 6}-+-{'-' * 10}-+-{'-' * 10}-+-{'-' * 10}")

    train_mses: list[float] = []
    cv_mses: list[float] = []
    w_norms: list[float] = []
    for degree in range(1, MAX_DEGREE + 1):
        Phi = poly_features(x, degree)
        w = ridge_fit(Phi, y, lam=0.0)
        tr = mse(y, predict(Phi, w))
        cv = cv_score(x, y, degree, lam=0.0)
        wn = float(np.linalg.norm(w))
        train_mses.append(tr)
        cv_mses.append(cv)
        w_norms.append(wn)
        print(f"  {degree:>6} | {tr:>10.4f} | {cv:>10.4f} | {wn:>10.2f}")

    best_degree = int(np.argmin(cv_mses)) + 1  # +1 because degrees start at 1
    print(f"\n  CV-optimal degree: {best_degree}  (lowest CV MSE)")
    print("  Notice: train MSE keeps falling, but CV MSE bottoms out then rises —")
    print("  that upswing is overfitting (variance) at high degree.\n")

    # ── Ridge at the overfit degree ──────────────────────────────────────────
    overfit_degree = MAX_DEGREE
    print(f"[2/2] Ridge regularisation at the overfit degree ({overfit_degree}):\n")
    print(f"  {'lambda':>10} | {'CV MSE':>10} | {'||w||':>12}")
    print(f"  {'-' * 10}-+-{'-' * 10}-+-{'-' * 12}")

    Phi_of = poly_features(x, overfit_degree)
    lambdas = [0.0, 0.01, 0.1, 1.0, 10.0]
    ridge_cv: list[float] = []
    ridge_wn: list[float] = []
    for lam in lambdas:
        w = ridge_fit(Phi_of, y, lam)
        cv = cv_score(x, y, overfit_degree, lam)
        wn = float(np.linalg.norm(w))
        ridge_cv.append(cv)
        ridge_wn.append(wn)
        print(f"  {lam:>10.2f} | {cv:>10.4f} | {wn:>12.2f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    cv_plain_deg12 = cv_mses[MAX_DEGREE - 1]
    train_plain_deg12 = train_mses[MAX_DEGREE - 1]
    wn_plain_deg12 = w_norms[MAX_DEGREE - 1]

    # Pick the best ridge (lam > 0) at degree 12.
    best_ridge_i = 1 + int(np.argmin(ridge_cv[1:]))
    best_ridge_cv = ridge_cv[best_ridge_i]
    best_ridge_wn = ridge_wn[best_ridge_i]
    best_ridge_lam = lambdas[best_ridge_i]

    print("\nAcceptance:")
    ok_degree = 2 <= best_degree <= 6
    ok_overfit = train_plain_deg12 * 3 < cv_plain_deg12  # train MSE << CV MSE
    ok_ridge_wn = best_ridge_wn < wn_plain_deg12
    ok_ridge_cv = best_ridge_cv < cv_plain_deg12

    print(f"  [{'x' if ok_degree else ' '}] CV-optimal degree in [2, 6]  (got {best_degree})")
    print(
        f"  [{'x' if ok_overfit else ' '}] Degree-12 overfits: train MSE << CV MSE  "
        f"({train_plain_deg12:.4f} vs {cv_plain_deg12:.4f})"
    )
    print(
        f"  [{'x' if ok_ridge_wn else ' '}] Ridge (λ={best_ridge_lam}) shrinks ||w|| at degree 12  "
        f"({best_ridge_wn:.2f} < {wn_plain_deg12:.2f})"
    )
    print(
        f"  [{'x' if ok_ridge_cv else ' '}] Ridge (λ={best_ridge_lam}) lowers CV MSE at degree 12  "
        f"({best_ridge_cv:.4f} < {cv_plain_deg12:.4f})"
    )

    if ok_degree and ok_overfit and ok_ridge_wn and ok_ridge_cv:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
