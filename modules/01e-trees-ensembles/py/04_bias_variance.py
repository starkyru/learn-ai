"""
Task 4 🟢 — Empirical bias–variance decomposition of tree models.

What you'll learn:
  - The decomposition from Module 01b — E[(y - ŷ)²] = bias² + variance + noise
    — measured EMPIRICALLY: train the same model class on M independently
    resampled training sets and watch how its predictions scatter.
  - Why a stump is a high-BIAS model (too rigid to bend with the data) while a
    deep tree is a high-VARIANCE model (bends with every noise wiggle).
  - Why bagging works: averaging bootstrapped deep trees slashes variance
    while barely touching bias — the whole reason random forests exist.

The math (README derives each step):

  Fix a test point x with clean target f(x). Train M models on M resampled
  training sets; call their predictions ŷ_1 … ŷ_M and their mean ȳ̂(x).

      bias²(x)    = ( ȳ̂(x) - f(x) )²
      variance(x) = (1/M) Σ_m ( ŷ_m(x) - ȳ̂(x) )²

  Average both over the test points to get one bias² and one variance per
  model class. Against NOISY test labels y = f(x) + ε, ε ~ N(0, σ²):

      E[ (y - ŷ)² ]  =  bias²  +  variance  +  σ²
      →  bias² + variance  ≈  expected MSE − σ²      (the harness checks this)

You implement ONE function: empirical_bias_variance(predictions, y_true) —
the decomposition math itself. Everything else — the data machinery, a
compact regression-tree trainer, the three model classes (stump / deep tree /
bagged deep trees), and the comparison table — is provided and runnable.

How to run:
  uv run python modules/01e-trees-ensembles/py/04_bias_variance.py
"""

from __future__ import annotations

import numpy as np

SEED = 42
M = 60  # number of resampled training sets (→ M trained models per class)
N_TRAIN = 60  # points per training set
N_TEST = 200  # fixed test grid
NOISE_STD = 0.3  # σ of the label noise
N_BAG = 20  # bootstrapped trees per bagged model


def f_true(x: np.ndarray) -> np.ndarray:
    """The clean target function the noisy data is drawn around."""
    return np.sin(2.0 * x)


# ---------------------------------------------------------------------------
# Regression-tree trainer  (provided — do not edit)
#
# A compact CART for 1-D regression: splits minimise the two-sided SSE of the
# residuals around each side's mean; leaves predict the mean. max_depth=1
# gives a stump; max_depth=None grows until pure/exhausted.
# ---------------------------------------------------------------------------


def train_reg_tree(
    x: np.ndarray,
    y: np.ndarray,
    depth: int = 0,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
) -> dict:
    def leaf() -> dict:
        return {"leaf": True, "value": float(y.mean())}

    if (max_depth is not None and depth >= max_depth) or y.size < 2 * min_samples_leaf:
        return leaf()
    vals = np.unique(x)
    if len(vals) < 2:
        return leaf()
    parent_sse = float(np.sum((y - y.mean()) ** 2))
    best_sse, best_t = parent_sse - 1e-12, None
    for k in range(len(vals) - 1):
        t = (vals[k] + vals[k + 1]) / 2.0
        left = x <= t
        if left.sum() < min_samples_leaf or (~left).sum() < min_samples_leaf:
            continue
        sse = float(
            np.sum((y[left] - y[left].mean()) ** 2) + np.sum((y[~left] - y[~left].mean()) ** 2)
        )
        if sse < best_sse:
            best_sse, best_t = sse, t
    if best_t is None:
        return leaf()
    left = x <= best_t
    return {
        "leaf": False,
        "threshold": float(best_t),
        "left": train_reg_tree(x[left], y[left], depth + 1, max_depth, min_samples_leaf),
        "right": train_reg_tree(x[~left], y[~left], depth + 1, max_depth, min_samples_leaf),
    }


def reg_tree_predict(tree: dict, x: np.ndarray) -> np.ndarray:
    out = np.empty(x.shape)
    for i, xi in enumerate(x):
        node = tree
        while not node["leaf"]:
            node = node["left"] if xi <= node["threshold"] else node["right"]
        out[i] = node["value"]
    return out


# ---------------------------------------------------------------------------
# Resampling machinery + the three model classes  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_training_set(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """One fresh draw from the generative process: x ~ U[-3,3], y = f(x) + ε."""
    x = rng.uniform(-3.0, 3.0, size=N_TRAIN)
    y = f_true(x) + rng.normal(0.0, NOISE_STD, size=N_TRAIN)
    return x, y


def fit_stump_model(
    rng: np.random.Generator, x: np.ndarray, y: np.ndarray, x_test: np.ndarray
) -> np.ndarray:
    tree = train_reg_tree(x, y, max_depth=1)
    return reg_tree_predict(tree, x_test)


def fit_deep_model(
    rng: np.random.Generator, x: np.ndarray, y: np.ndarray, x_test: np.ndarray
) -> np.ndarray:
    tree = train_reg_tree(x, y, max_depth=None, min_samples_leaf=1)
    return reg_tree_predict(tree, x_test)


def fit_bagged_model(
    rng: np.random.Generator, x: np.ndarray, y: np.ndarray, x_test: np.ndarray
) -> np.ndarray:
    """Average of N_BAG unlimited-depth trees, each on a bootstrap resample."""
    preds = np.zeros(x_test.shape)
    for _ in range(N_BAG):
        idx = rng.integers(0, x.size, size=x.size)
        tree = train_reg_tree(x[idx], y[idx], max_depth=None, min_samples_leaf=1)
        preds += reg_tree_predict(tree, x_test)
    return preds / N_BAG


def prediction_matrix(fit_fn, rng: np.random.Generator, x_test: np.ndarray) -> np.ndarray:
    """Train on M fresh training sets; stack the M test predictions (M × N_TEST)."""
    rows = []
    for _ in range(M):
        x, y = make_training_set(rng)
        rows.append(fit_fn(rng, x, y, x_test))
    return np.stack(rows)


# ---------------------------------------------------------------------------
# Core function — YOU implement this one
# ---------------------------------------------------------------------------


def empirical_bias_variance(predictions: np.ndarray, y_true: np.ndarray) -> tuple[float, float]:
    """
    The bias–variance decomposition, computed from data.

    Args:
      predictions : (M, N_test) — row m holds model m's predictions on the
                    shared test grid (model m was trained on training set m).
      y_true      : (N_test,)   — the CLEAN targets f(x_test) (no noise).

    Returns: (bias_squared, variance) — two floats, each averaged over the
    test points:
      1. mean prediction per test point: average the M rows (axis=0) →
         a length-N_test vector ȳ̂.
      2. bias² = mean over test points of (ȳ̂ - y_true)².
      3. variance = mean over test points of the variance ACROSS the M models
         at that point, i.e. mean over m of (predictions[m] - ȳ̂)²
         (population variance — divide by M, not M-1).

    TODO: implement the three numbered steps above.
    """
    # TODO: implement the bias-variance decomposition
    raise NotImplementedError("TODO: implement empirical_bias_variance()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 4 — Empirical bias–variance decomposition of tree models\n")
    print(f"  Target f(x) = sin(2x), noise σ = {NOISE_STD} (σ² = {NOISE_STD**2:.3f})")
    print(f"  {M} resampled training sets of {N_TRAIN} points; {N_TEST} test points\n")

    x_test = np.linspace(-3.0, 3.0, N_TEST)
    y_true = f_true(x_test)  # CLEAN targets for the decomposition

    # One independent noisy test-label draw PER model, for the expected-MSE check.
    noise_rng = np.random.default_rng(SEED + 1)
    test_noise = noise_rng.normal(0.0, NOISE_STD, size=(M, N_TEST))

    models = [
        ("stump (depth 1)", fit_stump_model),
        ("deep tree", fit_deep_model),
        (f"bagged deep ×{N_BAG}", fit_bagged_model),
    ]

    results = {}
    print(f"  {'model':<18} {'bias²':>8} {'variance':>9} {'bias²+var':>10} {'expMSE−σ²':>10}")
    for name, fit_fn in models:
        rng = np.random.default_rng(SEED)  # same M training sets for every model
        preds = prediction_matrix(fit_fn, rng, x_test)
        bias_sq, variance = empirical_bias_variance(preds, y_true)
        # Expected MSE against noisy labels y = f(x) + ε (fresh ε per model draw).
        exp_mse = float(np.mean((preds - (y_true + test_noise)) ** 2))
        results[name] = (bias_sq, variance, exp_mse)
        print(
            f"  {name:<18} {bias_sq:>8.4f} {variance:>9.4f} "
            f"{bias_sq + variance:>10.4f} {exp_mse - NOISE_STD**2:>10.4f}"
        )

    (b_stump, v_stump, m_stump) = results["stump (depth 1)"]
    (b_deep, v_deep, m_deep) = results["deep tree"]
    (b_bag, v_bag, m_bag) = results[f"bagged deep ×{N_BAG}"]

    print(
        f"\n  bagging cut the deep tree's variance: {v_deep:.4f} → {v_bag:.4f} "
        f"({v_bag / v_deep:.0%} of it left)"
    )

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_bias = b_stump > b_deep and b_stump > b_bag
    ok_var = v_deep > v_stump and v_deep > v_bag
    ok_bag = v_bag < 0.6 * v_deep
    tol = 0.03
    ok_decomp = all(abs((b + v) - (m - NOISE_STD**2)) < tol for (b, v, m) in results.values())
    print(f"  [{'x' if ok_bias else ' '}] stump has the highest bias²  ({b_stump:.4f})")
    print(f"  [{'x' if ok_var else ' '}] deep tree has the highest variance  ({v_deep:.4f})")
    print(
        f"  [{'x' if ok_bag else ' '}] bagging cuts deep-tree variance by >40%  "
        f"({v_bag:.4f} < 0.6 × {v_deep:.4f})"
    )
    print(
        f"  [{'x' if ok_decomp else ' '}] bias² + variance ≈ expected MSE − σ²  "
        f"(within ±{tol}) for all three models"
    )

    if ok_bias and ok_var and ok_bag and ok_decomp:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
