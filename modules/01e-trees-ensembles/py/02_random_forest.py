"""
Task 2 🟡 — Bagging → random forest.

What you'll learn:
  - Bootstrap sampling: draw n indices WITH replacement — each resample leaves
    out ≈ 36.8% of the rows (the fraction of unique rows → 1 - 1/e ≈ 63.2%).
  - Bagging: train one tree per bootstrap, average (majority-vote) their
    predictions — averaging B noisy estimators divides the uncorrelated part
    of their variance by B.
  - The random-forest trick: at EVERY split, consider only a random subset of
    max_features features, so the trees stop all making the same greedy first
    split and become decorrelated — which is what makes the averaging work.

The math (README derives each step):

  Unique-fraction of a bootstrap:  P(row i never drawn in n tries)
      = (1 - 1/n)^n → e⁻¹ ≈ 0.368,  so  unique ≈ 63.2% of rows.

  Variance of an average of B estimators with variance σ² and pairwise
  correlation ρ:
      Var( (1/B) Σ f_b ) = ρσ² + (1-ρ)σ²/B
  Bagging shrinks the second term; feature subsampling shrinks ρ — the first.

You implement: bootstrap_sample, train_forest, forest_predict. A full
single-tree trainer that accepts max_features (the per-split feature
sampler), the dataset (2 signal + 3 pure-noise features), and the harness
comparing individual trees vs the ensemble vs a single deep-tree baseline
are provided and runnable.

How to run:
  uv run python modules/01e-trees-ensembles/py/02_random_forest.py
"""

from __future__ import annotations

import numpy as np

SEED = 21
N = 520  # total samples (first N_TRAIN train, rest test)
N_TRAIN = 370
NOISE_FLIP = 0.10
N_TREES = 25
MAX_FEATURES = 2  # features considered per split (out of 5)


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    5 features: x0, x1 carry the signal (the offset-XOR pattern from Task 1);
    x2..x4 are pure Gaussian noise — bait for an overfitting deep tree.
    NOISE_FLIP of the labels are flipped.

    Returns: X_train (N_TRAIN, 5), y_train, X_test, y_test.
    """
    rng = np.random.default_rng(SEED)
    X_signal = rng.uniform(-3.0, 3.0, size=(N, 2))
    X_noise = rng.normal(0.0, 1.0, size=(N, 3))
    X = np.hstack([X_signal, X_noise])
    y = ((X[:, 0] > 0.8) ^ (X[:, 1] > -0.7)).astype(int)
    flip = rng.random(N) < NOISE_FLIP
    y = np.where(flip, 1 - y, y)
    return X[:N_TRAIN], y[:N_TRAIN], X[N_TRAIN:], y[N_TRAIN:]


# ---------------------------------------------------------------------------
# Single-tree trainer  (provided — do not edit)
#
# The same CART you built in Task 1, with ONE addition: if max_features is
# set, each split only scans a random subset of that many features (drawn
# with the rng) — the random-forest decorrelation trick.
# ---------------------------------------------------------------------------


def _gini(y: np.ndarray) -> float:
    if y.size == 0:
        return 0.0
    _, counts = np.unique(y, return_counts=True)
    p = counts / y.size
    return float(1.0 - np.sum(p**2))


def _best_split(
    X: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    max_features: int | None,
) -> tuple[int, float] | None:
    n, d = X.shape
    if max_features is None:
        features = np.arange(d)
    else:
        features = rng.choice(d, size=min(max_features, d), replace=False)
    best: tuple[int, float] | None = None
    best_score = _gini(y) - 1e-12
    for j in features:
        vals = np.unique(X[:, j])
        for k in range(len(vals) - 1):
            t = (vals[k] + vals[k + 1]) / 2.0
            left = X[:, j] <= t
            n_l = int(left.sum())
            if n_l == 0 or n_l == n:
                continue
            score = (n_l * _gini(y[left]) + (n - n_l) * _gini(y[~left])) / n
            if score < best_score:
                best_score = score
                best = (int(j), float(t))
    return best


def train_tree(
    X: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    max_features: int | None = None,
) -> dict:
    """Grow an unlimited-depth CART tree; same node dicts as Task 1."""
    if _gini(y) == 0.0:
        return {"leaf": True, "prediction": int(np.bincount(y).argmax())}
    split = _best_split(X, y, rng, max_features)
    if split is None:
        return {"leaf": True, "prediction": int(np.bincount(y).argmax())}
    j, t = split
    left = X[:, j] <= t
    return {
        "leaf": False,
        "feature": j,
        "threshold": t,
        "left": train_tree(X[left], y[left], rng, max_features),
        "right": train_tree(X[~left], y[~left], rng, max_features),
    }


def tree_predict(tree: dict, X: np.ndarray) -> np.ndarray:
    """Predict every row of X with one tree."""
    out = np.empty(len(X), dtype=int)
    for i, x in enumerate(X):
        node = tree
        while not node["leaf"]:
            node = node["left"] if x[node["feature"]] <= node["threshold"] else node["right"]
        out[i] = node["prediction"]
    return out


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def bootstrap_sample(rng: np.random.Generator, n: int) -> np.ndarray:
    """
    Draw a bootstrap sample: n indices from {0, …, n-1} WITH replacement.

    Returns: (n,) int array of row indices (duplicates expected — that's the
    point; ≈ 63.2% of the rows appear at least once).

    TODO: implement — one call to rng.integers with the right bounds and size.
    """
    # TODO: implement the bootstrap draw
    raise NotImplementedError("TODO: implement bootstrap_sample()")


def train_forest(
    X: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    n_trees: int,
    max_features: int | None,
) -> list[dict]:
    """
    Train a random forest: n_trees CART trees, EACH on its own bootstrap
    sample of the rows, EACH restricted to max_features random features per
    split (the provided train_tree handles that part — just pass it through).

    Returns: list of n_trees tree dicts.

    TODO: implement.
      1. For each of the n_trees rounds, draw indices with your
         bootstrap_sample and slice X and y by them.
      2. Train a tree on that resample with the provided train_tree
         (forward rng and max_features), and collect it.
      3. Return the list of trees.
    """
    # TODO: implement the bootstrap-then-train loop
    raise NotImplementedError("TODO: implement train_forest()")


def forest_predict(trees: list[dict], X: np.ndarray) -> np.ndarray:
    """
    Majority vote of the forest: predict X with every tree (tree_predict),
    then, per sample, output the class most trees chose.

    With binary {0,1} labels the vote reduces to: mean over trees ≥ 0.5 → 1.
    (N_TREES is odd, so there are no exact ties.)

    Returns: (len(X),) int array of {0, 1} predictions.

    TODO: implement.
      1. Stack every tree's tree_predict(tree, X) into an (n_trees, N) matrix.
      2. Take the per-column vote per the rule above and return it as ints.
    """
    # TODO: implement the majority vote
    raise NotImplementedError("TODO: implement forest_predict()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 2 — Bagging → random forest\n")

    X_train, y_train, X_test, y_test = make_data()
    print(f"  Data: {len(y_train)} train / {len(y_test)} test, 5 features")
    print(f"  (2 signal + 3 pure noise), {NOISE_FLIP:.0%} label noise\n")

    # ── Bootstrap statistics ─────────────────────────────────────────────────
    print("[1/3] Bootstrap sampling (63.2% unique)...")
    rng = np.random.default_rng(SEED)
    n = len(y_train)
    unique_fracs = []
    all_have_dups = True
    for _ in range(20):
        idx = bootstrap_sample(rng, n)
        uniq = len(np.unique(idx))
        unique_fracs.append(uniq / n)
        if uniq == n:
            all_have_dups = False
    mean_unique = float(np.mean(unique_fracs))
    print(f"  20 bootstraps of n={n}: mean unique fraction = {mean_unique:.4f}")
    print(f"  (theory: 1 - 1/e ≈ 0.6321) — every sample has duplicates: {all_have_dups}\n")

    # ── Baseline: one deep tree on everything ────────────────────────────────
    print("[2/3] Baseline: single deep tree (all rows, all features)...")
    rng = np.random.default_rng(SEED)
    baseline = train_tree(X_train, y_train, rng, max_features=None)
    base_train = float(np.mean(tree_predict(baseline, X_train) == y_train))
    base_test = float(np.mean(tree_predict(baseline, X_test) == y_test))
    print(f"  train acc = {base_train:.4f}   test acc = {base_test:.4f}\n")

    # ── The forest ───────────────────────────────────────────────────────────
    print(f"[3/3] Random forest ({N_TREES} trees, max_features={MAX_FEATURES})...")
    rng = np.random.default_rng(SEED)
    forest = train_forest(X_train, y_train, rng, N_TREES, MAX_FEATURES)
    tree_accs = np.array([float(np.mean(tree_predict(t, X_test) == y_test)) for t in forest])
    ens_test = float(np.mean(forest_predict(forest, X_test) == y_test))
    print(f"  individual tree test accs (first 8): {np.round(tree_accs[:8], 3)}")
    print(
        f"  individual: mean = {tree_accs.mean():.4f}  "
        f"min = {tree_accs.min():.4f}  max = {tree_accs.max():.4f}"
    )
    print(f"  ensemble (majority vote) test acc = {ens_test:.4f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_boot = all_have_dups and 0.55 <= mean_unique <= 0.72
    ok_vs_mean = ens_test >= float(tree_accs.mean())
    ok_vs_base = ens_test >= base_test
    print(
        f"  [{'x' if ok_boot else ' '}] bootstraps have duplicates; unique fraction "
        f"≈ 0.632 (got {mean_unique:.4f})"
    )
    print(
        f"  [{'x' if ok_vs_mean else ' '}] ensemble ≥ mean individual tree  "
        f"({ens_test:.4f} ≥ {tree_accs.mean():.4f})"
    )
    print(
        f"  [{'x' if ok_vs_base else ' '}] ensemble ≥ single deep-tree baseline  "
        f"({ens_test:.4f} ≥ {base_test:.4f})"
    )

    if ok_boot and ok_vs_mean and ok_vs_base:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
