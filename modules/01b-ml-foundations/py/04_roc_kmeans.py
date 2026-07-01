"""
Task 4 🟢 — Ranking metrics (ROC/AUC) and clustering (k-means) from scratch.

What you'll learn:
  Part A — ROC curves and AUC:
    - A classifier outputs SCORES, not just labels; a threshold turns scores into
      decisions. Sweeping the threshold traces the ROC curve.
    - TPR (recall) vs FPR at every threshold; AUC summarises the whole curve.
    - AUC = P(a random positive scores higher than a random negative). It is
      threshold-free, which is why interviewers love it.

  Part B — k-means (Lloyd's algorithm):
    - Unsupervised clustering: no labels, just group points by proximity.
    - Alternate two steps until convergence: (1) assign each point to its nearest
      centroid, (2) move each centroid to the mean of its assigned points.
    - Inertia (within-cluster sum of squared distances) never increases — that's
      why the algorithm is guaranteed to converge.

The math (README derives each step):

  ROC:  at threshold t, predict positive iff score ≥ t.
        TPR(t) = TP / (TP + FN)     (fraction of real positives caught)
        FPR(t) = FP / (FP + TN)     (fraction of real negatives wrongly flagged)
        Sweep t from high→low; each unique score is a candidate threshold.
  AUC:  area under the (FPR, TPR) curve, computed with the trapezoidal rule:
        AUC = Σ (fpr[i+1] - fpr[i]) · (tpr[i+1] + tpr[i]) / 2

  k-means:
        assign:  cluster(x) = argmin_k ||x - c_k||²
        update:  c_k = mean of all x assigned to k
        inertia: Σ_i ||x_i - c_{assign(i)}||²

You implement: roc_curve, auc, assign_clusters, update_centroids, and inertia.
Everything else — data, the three sanity rankers, the k-means loop, and the
cluster-recovery check — is provided and runnable.

How to run:
  uv run python modules/01b-ml-foundations/py/04_roc_kmeans.py
"""

from __future__ import annotations

import numpy as np

SEED = 5


# ===========================================================================
# PART A — ROC / AUC
# ===========================================================================


def roc_curve(scores: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute the ROC curve by sweeping every threshold.

    Args:
      scores : (N,) float — the classifier's confidence that each item is positive
      labels : (N,) int in {0, 1} — the ground truth

    Returns:
      fpr : (M,) false-positive rates, ascending, starting at 0 and ending at 1
      tpr : (M,) true-positive  rates, matched to fpr

    Method (a clean, standard way):
      1. P = number of positives (labels == 1); Nn = number of negatives.
      2. Sort the items by score DESCENDING. As you lower the threshold you admit
         items one at a time in that order.
      3. Start at the point (FPR=0, TPR=0) — threshold above every score.
      4. Walk down the sorted list; each time you admit a positive, TP += 1; each
         time you admit a negative, FP += 1. After each step record
         (FPR = FP / Nn, TPR = TP / P).
      5. The curve therefore starts at (0, 0) and ends at (1, 1).

    TODO: implement.
      1. order = np.argsort(-scores)               # indices, highest score first
      2. y = labels[order]
      3. P = (labels == 1).sum(); Nn = (labels == 0).sum()
      4. tp = fp = 0
         tpr_list = [0.0]; fpr_list = [0.0]
         for lbl in y:
             if lbl == 1: tp += 1
             else:        fp += 1
             tpr_list.append(tp / P)
             fpr_list.append(fp / Nn)
      5. return np.array(fpr_list), np.array(tpr_list)
    """
    # TODO: implement the ROC sweep
    raise NotImplementedError("TODO: implement roc_curve()")


def auc(fpr: np.ndarray, tpr: np.ndarray) -> float:
    """
    Area under the ROC curve via the trapezoidal rule.

    AUC = Σ_i (fpr[i+1] - fpr[i]) · (tpr[i+1] + tpr[i]) / 2

    (fpr must be non-decreasing — roc_curve returns it that way.)

    TODO: implement.
      area = 0.0
      for i in range(len(fpr) - 1):
          area += (fpr[i+1] - fpr[i]) * (tpr[i+1] + tpr[i]) / 2
      return area
    (or, equivalently, return float(np.trapezoid(tpr, fpr)))
    """
    # TODO: implement the trapezoidal AUC
    raise NotImplementedError("TODO: implement auc()")


# ===========================================================================
# PART B — k-means (Lloyd's algorithm)
# ===========================================================================


def assign_clusters(X: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """
    Assign each point to its nearest centroid (by squared Euclidean distance).

    Args:
      X         : (N, D) points
      centroids : (k, D) current centroids

    Returns:
      (N,) int array — the cluster index of each point.

    TODO: implement.
      For each point x_i, compute ||x_i - c_j||² for every centroid j and take the
      argmin. A vectorised way:
        # dists[i, j] = squared distance from point i to centroid j
        diff = X[:, None, :] - centroids[None, :, :]   # (N, k, D)
        dists = (diff ** 2).sum(axis=2)                # (N, k)
        return np.argmin(dists, axis=1)                # (N,)
      (A plain double loop is fine too — clarity over cleverness.)
    """
    # TODO: implement nearest-centroid assignment
    raise NotImplementedError("TODO: implement assign_clusters()")


def update_centroids(X: np.ndarray, assignments: np.ndarray, k: int) -> np.ndarray:
    """
    Recompute each centroid as the mean of the points assigned to it.

    Args:
      X           : (N, D) points
      assignments : (N,) cluster index of each point
      k           : number of clusters

    Returns:
      (k, D) new centroids.

    Handle empty clusters: if no point is assigned to cluster j, keep a sensible
    fallback (e.g. a random point, or leave it as zeros). For this seeded data no
    cluster goes empty, so the simple mean is enough.

    TODO: implement.
      D = X.shape[1]
      new_centroids = np.zeros((k, D))
      for j in range(k):
          members = X[assignments == j]
          if len(members) > 0:
              new_centroids[j] = members.mean(axis=0)
      return new_centroids
    """
    # TODO: implement the centroid update
    raise NotImplementedError("TODO: implement update_centroids()")


def inertia(X: np.ndarray, centroids: np.ndarray, assignments: np.ndarray) -> float:
    """
    Within-cluster sum of squared distances (the k-means objective).

    inertia = Σ_i ||x_i - c_{assignments[i]}||²

    TODO: implement.
      total = 0.0
      for i in range(len(X)):
          diff = X[i] - centroids[assignments[i]]
          total += float(np.dot(diff, diff))
      return total
    (or vectorised: ((X - centroids[assignments]) ** 2).sum())
    """
    # TODO: implement the inertia
    raise NotImplementedError("TODO: implement inertia()")


# ---------------------------------------------------------------------------
# Data + harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_scores() -> tuple[np.ndarray, np.ndarray]:
    """Ground-truth labels + a realistic 'good but imperfect' score for each item."""
    rng = np.random.default_rng(SEED)
    labels = np.concatenate([np.ones(50), np.zeros(50)]).astype(np.int64)
    # positives score higher on average, but the distributions overlap
    pos_scores = rng.normal(1.0, 1.0, 50)
    neg_scores = rng.normal(-1.0, 1.0, 50)
    scores = np.concatenate([pos_scores, neg_scores])
    return scores, labels


def make_blobs() -> tuple[np.ndarray, np.ndarray]:
    """Three well-separated 2-D Gaussian blobs. Returns (X, true_label)."""
    rng = np.random.default_rng(SEED)
    centers = np.array([[0.0, 0.0], [6.0, 6.0], [0.0, 6.0]])
    pts, true = [], []
    for cls, ctr in enumerate(centers):
        pts.append(rng.normal(ctr, 0.7, size=(60, 2)))
        true.append(np.full(60, cls))
    X = np.vstack(pts)
    true_label = np.concatenate(true)
    return X, true_label


def _init_centroids(X: np.ndarray, k: int, seed: int) -> np.ndarray:
    """
    Deterministic k-means++-style init (farthest-first traversal): a seeded first
    centre, then each next centre is the point farthest (by squared distance)
    from the centres chosen so far. This spreads the initial centroids across the
    blobs and avoids the "two centres land in one blob" local optimum that plain
    random init can fall into. Returns k point indices.
    """
    rng = np.random.default_rng(seed)
    chosen = [int(rng.integers(len(X)))]
    while len(chosen) < k:
        # distance of each point to its NEAREST already-chosen centre
        d = np.min(np.stack([((X - X[c]) ** 2).sum(axis=1) for c in chosen], axis=1), axis=1)
        d[chosen] = -1.0  # never re-pick an existing centre
        chosen.append(int(np.argmax(d)))
    return X[chosen].copy()


def kmeans(
    X: np.ndarray, k: int, max_iter: int = 50, seed: int = SEED
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    """
    Full Lloyd's algorithm using your assign/update/inertia functions.

    Initialise centroids with a farthest-first traversal (see _init_centroids),
    then alternate assign/update until assignments stop changing or max_iter.
    Returns (centroids, assignments, inertia_history). Provided — don't edit.
    """
    centroids = _init_centroids(X, k, seed)

    assignments = assign_clusters(X, centroids)
    history = [inertia(X, centroids, assignments)]

    for _ in range(max_iter):
        centroids = update_centroids(X, assignments, k)
        new_assign = assign_clusters(X, centroids)
        history.append(inertia(X, centroids, new_assign))
        if np.array_equal(new_assign, assignments):
            assignments = new_assign
            break
        assignments = new_assign

    return centroids, assignments, history


def main() -> None:
    print("Task 4 — ROC/AUC and k-means from scratch\n")

    # ── PART A: ROC / AUC ────────────────────────────────────────────────────
    print("=" * 60)
    print("PART A — ROC / AUC")
    print("=" * 60)

    scores, labels = make_scores()

    # A perfect ranker: use the labels themselves as the score.
    perfect = labels.astype(float)
    # A reversed ranker: exactly wrong.
    reversed_ranker = 1.0 - labels.astype(float)
    # A random ranker: scores unrelated to labels.
    rng = np.random.default_rng(SEED + 5)
    random_ranker = rng.normal(0, 1, len(labels))

    def auc_of(s: np.ndarray) -> float:
        f, t = roc_curve(s, labels)
        return auc(f, t)

    auc_perfect = auc_of(perfect)
    auc_reversed = auc_of(reversed_ranker)
    auc_random = auc_of(random_ranker)
    auc_real = auc_of(scores)

    print(f"\n  AUC (perfect ranker)  = {auc_perfect:.3f}   (expect 1.0)")
    print(f"  AUC (reversed ranker) = {auc_reversed:.3f}   (expect 0.0)")
    print(f"  AUC (random ranker)   = {auc_random:.3f}   (expect ≈ 0.5)")
    print(f"  AUC (realistic model) = {auc_real:.3f}   (good separation → high)")

    fpr, tpr = roc_curve(scores, labels)
    print(
        f"\n  ROC curve has {len(fpr)} points; starts at "
        f"({fpr[0]:.1f}, {tpr[0]:.1f}) ends at ({fpr[-1]:.1f}, {tpr[-1]:.1f})."
    )

    # ── PART B: k-means ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PART B — k-means (Lloyd's algorithm)")
    print("=" * 60)

    X, true_label = make_blobs()
    k = 3
    centroids, assignments, history = kmeans(X, k)

    print(f"\n  Ran k-means (k={k}) on {len(X)} points in 3 true blobs.")
    print(f"  Iterations recorded: {len(history)}")
    print("  Inertia over iterations:")
    for i, val in enumerate(history):
        print(f"    iter {i:>2}: inertia = {val:>10.2f}")

    # Non-increasing inertia?
    non_increasing = all(history[i + 1] <= history[i] + 1e-6 for i in range(len(history) - 1))

    # Cluster recovery: each TRUE blob should be dominated by a single cluster id.
    recovered = 0
    for cls in range(k):
        mask = true_label == cls
        cluster_ids = assignments[mask]
        # most common cluster id among this blob's points
        counts = np.bincount(cluster_ids, minlength=k)
        dominant_frac = counts.max() / counts.sum()
        if dominant_frac >= 0.9:
            recovered += 1

    # Also confirm the 3 dominant cluster ids are distinct (no two blobs collapse).
    dominant_ids = []
    for cls in range(k):
        mask = true_label == cls
        dominant_ids.append(int(np.bincount(assignments[mask], minlength=k).argmax()))
    distinct = len(set(dominant_ids)) == k

    print(f"\n  Inertia non-increasing every iteration: {non_increasing}")
    print(f"  True blobs cleanly recovered (≥90% one cluster): {recovered}/{k}")
    print(f"  Dominant cluster ids per blob: {dominant_ids}  (distinct: {distinct})")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_perfect = abs(auc_perfect - 1.0) < 1e-9
    ok_reversed = abs(auc_reversed - 0.0) < 1e-9
    ok_random = abs(auc_random - 0.5) < 0.15
    ok_noninc = non_increasing
    ok_recover = recovered == k and distinct

    print(f"  [{'x' if ok_perfect else ' '}] AUC of perfect ranker == 1.0  ({auc_perfect:.3f})")
    print(f"  [{'x' if ok_reversed else ' '}] AUC of reversed ranker == 0.0  ({auc_reversed:.3f})")
    print(f"  [{'x' if ok_random else ' '}] AUC of random ranker ≈ 0.5 (±0.15)  ({auc_random:.3f})")
    print(f"  [{'x' if ok_noninc else ' '}] k-means inertia non-increasing each iteration")
    print(f"  [{'x' if ok_recover else ' '}] k-means recovers all {k} blobs (distinct clusters)")

    if ok_perfect and ok_reversed and ok_random and ok_noninc and ok_recover:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
