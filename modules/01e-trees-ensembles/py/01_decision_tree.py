"""
Task 1 🔴 — A decision tree (CART) from scratch.

What you'll learn:
  - Gini impurity: how "mixed" a set of labels is, and why a split that lowers
    the weighted impurity of its children is a good split.
  - Greedy recursive partitioning (CART): scan every feature and every midpoint
    threshold, take the best split, recurse — no gradient anywhere.
  - Why an unlimited-depth tree memorises the training set (train accuracy → 1)
    while its test accuracy lags — the overfitting gap made visible.
  - How max_depth / min_samples_leaf act as the tree's regularisers.

The math (README derives each step):

  Gini impurity of a label set y (classes c, class proportions p_c):
      G(y) = 1 - Σ_c p_c²
      pure node (one class)      → G = 0
      balanced binary (50/50)    → G = 0.5   (the binary maximum)

  Quality of a split of y into (y_left, y_right), sizes n_L and n_R:
      G_split = (n_L · G(y_left) + n_R · G(y_right)) / (n_L + n_R)
  Best split = the (feature, threshold) minimising G_split. Only accept it if
  G_split < G(y) (i.e. the "Gini gain" G(y) - G_split is positive).

  Candidate thresholds for a feature = midpoints between consecutive SORTED
  UNIQUE values of that feature — no other threshold changes the partition.

You implement the four core functions: gini, best_split, build_tree, and
predict_one. The dataset (a noisy XOR-quadrant pattern no linear model can
solve), train/test split, vectorised predict, and the depth-limited-vs-
unlimited comparison harness are provided and runnable.

How to run:
  uv run python modules/01e-trees-ensembles/py/01_decision_tree.py
"""

from __future__ import annotations

import numpy as np

SEED = 11
N = 500  # total samples (first N_TRAIN train, rest test)
N_TRAIN = 350
NOISE_FLIP = 0.10  # fraction of labels flipped at random


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    2-D points uniform in [-3, 3]²; the true label is an offset XOR of the two
    coordinates:  y = (x0 > 0.8) XOR (x1 > -0.7)  — a nonlinear checkerboard
    quadrant pattern. Then NOISE_FLIP of the labels are flipped, so a perfect
    memoriser of the training set CANNOT be perfect on the test set.

    Returns: X_train (N_TRAIN, 2), y_train, X_test, y_test.
    """
    rng = np.random.default_rng(SEED)
    X = rng.uniform(-3.0, 3.0, size=(N, 2))
    y = ((X[:, 0] > 0.8) ^ (X[:, 1] > -0.7)).astype(int)
    flip = rng.random(N) < NOISE_FLIP
    y = np.where(flip, 1 - y, y)
    return X[:N_TRAIN], y[:N_TRAIN], X[N_TRAIN:], y[N_TRAIN:]


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def gini(y: np.ndarray) -> float:
    """
    Gini impurity:  G(y) = 1 - Σ_c p_c²  over the class proportions p_c.

    Args:
      y : (n,) int array of class labels (any label values; use np.unique).

    Returns: float in [0, 0.5] for binary labels (0 = pure, 0.5 = 50/50).
    An empty y should return 0.0.

    TODO: implement.
      - Handle the empty case first.
      - Get the per-class counts (np.unique with return_counts=True), turn them
        into proportions, and apply the formula above.
    """
    # TODO: implement Gini impurity
    raise NotImplementedError("TODO: implement gini()")


def best_split(X: np.ndarray, y: np.ndarray, min_samples_leaf: int = 1) -> tuple[int, float] | None:
    """
    Exhaustive CART split search: scan EVERY feature and EVERY midpoint between
    consecutive sorted unique values; return the (feature, threshold) whose
    weighted child Gini  (n_L·G_L + n_R·G_R) / n  is smallest.

    A point goes LEFT when  x[feature] <= threshold  (that convention must
    match predict_one). Skip splits that leave either side with fewer than
    min_samples_leaf points. Return None when no split strictly reduces the
    parent impurity (that node should become a leaf).

    Args:
      X : (n, d) features;  y : (n,) labels;  min_samples_leaf : int.

    Returns: (best_feature_index, best_threshold) or None.

    TODO: implement.
      1. Start with best score = gini(y) (a split must beat the parent).
      2. For each feature j: sort the unique values of X[:, j]; candidate
         thresholds are the midpoints of consecutive pairs.
      3. For each threshold: build the boolean left mask (<= threshold), skip
         if either side is smaller than min_samples_leaf, else compute the
         weighted child Gini per the formula and keep the argmin.
      4. Return the winning (feature, threshold), or None if nothing beat the
         parent impurity (use a small epsilon like 1e-12 for the comparison).
    """
    # TODO: implement the exhaustive split search
    raise NotImplementedError("TODO: implement best_split()")


def build_tree(
    X: np.ndarray,
    y: np.ndarray,
    depth: int = 0,
    max_depth: int | None = None,
    min_samples_leaf: int = 1,
) -> dict:
    """
    Recursively grow a CART tree. Nodes are plain dicts:

      leaf:      {"leaf": True,  "prediction": <majority class, int>}
      internal:  {"leaf": False, "feature": j, "threshold": t,
                  "left": <node>, "right": <node>}

    Stop and return a leaf when ANY of these hold:
      - the node is pure (gini == 0),
      - max_depth is set and depth has reached it,
      - best_split(...) returns None (no impurity-reducing split exists).

    The leaf prediction is the MAJORITY class of y at that node
    (np.bincount + argmax is one clean way).

    TODO: implement.
      1. Check the stopping conditions above; on any of them return the leaf
         dict with the majority class.
      2. Otherwise call best_split (pass min_samples_leaf through), partition
         the rows by  X[:, feature] <= threshold, and recurse on each side with
         depth + 1 to fill the internal node's "left" and "right".
    """
    # TODO: implement the recursive tree growth
    raise NotImplementedError("TODO: implement build_tree()")


def predict_one(node: dict, x: np.ndarray) -> int:
    """
    Route a single sample x down the tree to a leaf and return its prediction.

    At each internal node go LEFT when  x[node["feature"]] <= node["threshold"]
    (the same convention build_tree used), otherwise right.

    TODO: implement — walk (loop or recurse) until node["leaf"] is True, then
    return that leaf's prediction.
    """
    # TODO: implement the tree walk
    raise NotImplementedError("TODO: implement predict_one()")


# ---------------------------------------------------------------------------
# Helpers  (provided — use your predict_one)
# ---------------------------------------------------------------------------


def predict(tree: dict, X: np.ndarray) -> np.ndarray:
    """Vectorised wrapper: predict_one for every row."""
    return np.array([predict_one(tree, x) for x in X], dtype=int)


def accuracy(tree: dict, X: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(predict(tree, X) == y))


def tree_depth(node: dict) -> int:
    if node["leaf"]:
        return 0
    return 1 + max(tree_depth(node["left"]), tree_depth(node["right"]))


def count_leaves(node: dict) -> int:
    if node["leaf"]:
        return 1
    return count_leaves(node["left"]) + count_leaves(node["right"])


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 1 — Decision tree (CART) from scratch\n")

    # ── Gini sanity checks ───────────────────────────────────────────────────
    print("[1/3] Gini impurity sanity...")
    g_pure = gini(np.array([1, 1, 1, 1]))
    g_balanced = gini(np.array([0, 1, 0, 1]))
    print(f"  gini([1,1,1,1])  = {g_pure:.4f}   (pure     → expect 0.0)")
    print(f"  gini([0,1,0,1])  = {g_balanced:.4f}   (balanced → expect 0.5)\n")

    X_train, y_train, X_test, y_test = make_data()
    print(f"  Data: {len(y_train)} train / {len(y_test)} test, 2 features,")
    print(f"  XOR-quadrant boundary, {NOISE_FLIP:.0%} label noise\n")

    # ── Unlimited depth: the memoriser ───────────────────────────────────────
    print("[2/3] Unlimited-depth tree (memorises the training set)...")
    deep = build_tree(X_train, y_train, max_depth=None, min_samples_leaf=1)
    deep_train = accuracy(deep, X_train, y_train)
    deep_test = accuracy(deep, X_test, y_test)
    deep_gap = deep_train - deep_test
    print(f"  depth = {tree_depth(deep)}, leaves = {count_leaves(deep)}")
    print(f"  train acc = {deep_train:.4f}   test acc = {deep_test:.4f}")
    print(f"  overfit gap (train - test) = {deep_gap:+.4f}\n")

    # ── Depth-limited: the regularised tree ──────────────────────────────────
    print("[3/3] Depth-3 tree (regularised)...")
    shallow = build_tree(X_train, y_train, max_depth=3, min_samples_leaf=5)
    sh_train = accuracy(shallow, X_train, y_train)
    sh_test = accuracy(shallow, X_test, y_test)
    sh_gap = sh_train - sh_test
    print(f"  depth = {tree_depth(shallow)}, leaves = {count_leaves(shallow)}")
    print(f"  train acc = {sh_train:.4f}   test acc = {sh_test:.4f}")
    print(f"  overfit gap (train - test) = {sh_gap:+.4f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_gini = abs(g_pure) < 1e-12 and abs(g_balanced - 0.5) < 1e-12
    ok_memorise = deep_train >= 0.99
    ok_gap = deep_gap >= 0.10
    ok_shallow = sh_gap < deep_gap and sh_test >= 0.80
    print(f"  [{'x' if ok_gini else ' '}] gini: pure = 0.0, balanced binary = 0.5")
    print(
        f"  [{'x' if ok_memorise else ' '}] deep tree memorises: train acc ≥ 0.99  "
        f"(got {deep_train:.4f})"
    )
    print(
        f"  [{'x' if ok_gap else ' '}] deep tree overfits: train - test gap ≥ 0.10  "
        f"(got {deep_gap:+.4f})"
    )
    print(
        f"  [{'x' if ok_shallow else ' '}] depth-3 tree generalises: smaller gap "
        f"({sh_gap:+.4f} < {deep_gap:+.4f}) and test acc ≥ 0.80 (got {sh_test:.4f})"
    )

    if ok_gini and ok_memorise and ok_gap and ok_shallow:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
