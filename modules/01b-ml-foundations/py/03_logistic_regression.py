"""
Task 3 🟡 — Binary logistic regression with gradient descent + L2 regularisation.

What you'll learn:
  - The sigmoid: squashing a real-valued score into a probability in (0, 1)
  - Binary cross-entropy (log loss): the right loss for probabilistic classifiers
  - The logistic-regression gradient (structurally identical to linear regression)
  - L2 regularisation on the weights (but never on the bias)

The math (README derives each step):

  Score / logit:   z = X w      (X has a bias column, so w[0] is the intercept)
  Sigmoid:         σ(z) = 1 / (1 + e^{-z})       → probability of class 1
  Prediction:      ŷ = 1 if σ(z) ≥ 0.5 else 0

  Binary cross-entropy (per sample), averaged over the batch:
     L = -1/N · Σ [ y·log(p) + (1-y)·log(1-p) ]      where p = σ(Xw)
  (clip p to [ε, 1-ε] so log never sees 0)

  Gradient (the beautiful result — same shape as linear regression):
     ∇L = Xᵀ (σ(Xw) - y) / N        (+ L2 term below)

  L2 regularisation adds (λ/N)·Σ w_j² to the loss for j ≥ 1 (skip the bias),
  which adds  (λ/N)·w  to the gradient — but with the bias entry zeroed out.

You implement sigmoid, bce_loss, the gradient/step, and predict_proba/predict.
Everything else — two-Gaussian data, the split, the training loop, and the
||w|| comparison across λ — is provided and runnable.

How to run:
  uv run python modules/01b-ml-foundations/py/03_logistic_regression.py
"""

from __future__ import annotations

import numpy as np

SEED = 3
N_PER_CLASS = 150  # samples per class


# ---------------------------------------------------------------------------
# Synthetic data: two 2-D Gaussians  (provided)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray]:
    """
    Two well-separated 2-D Gaussian blobs → a (nearly) linearly separable
    binary problem. Class 0 centred at (-2, -2), class 1 at (+2, +2).

    Returns:
      X : (2·N_PER_CLASS, 2) features (NOT yet bias-augmented)
      y : (2·N_PER_CLASS,)   labels in {0, 1}
    """
    rng = np.random.default_rng(SEED)
    c0 = rng.normal(loc=[-2.0, -2.0], scale=1.0, size=(N_PER_CLASS, 2))
    c1 = rng.normal(loc=[2.0, 2.0], scale=1.0, size=(N_PER_CLASS, 2))
    X = np.vstack([c0, c1])
    y = np.concatenate([np.zeros(N_PER_CLASS), np.ones(N_PER_CLASS)]).astype(np.int64)
    return X, y


def add_bias_column(X: np.ndarray) -> np.ndarray:
    """Prepend a column of 1s so w[0] is the intercept."""
    return np.hstack([np.ones((X.shape[0], 1), dtype=X.dtype), X])


def stratified_split(
    X: np.ndarray, y: np.ndarray, test_fraction: float = 0.2, seed: int = SEED
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Stratified train/test split. Returns (X_train, X_test, y_train, y_test)."""
    rng = np.random.default_rng(seed)
    train_idx, test_idx = [], []
    for cls in np.unique(y):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        n_test = max(1, int(len(idx) * test_fraction))
        test_idx.extend(idx[:n_test].tolist())
        train_idx.extend(idx[n_test:].tolist())
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


# ---------------------------------------------------------------------------
# Core functions — YOU implement these
# ---------------------------------------------------------------------------


def sigmoid(z: np.ndarray) -> np.ndarray:
    """
    Logistic sigmoid: σ(z) = 1 / (1 + e^{-z}), applied element-wise.

    Use np.clip on z (e.g. to [-500, 500]) before exp to avoid overflow warnings
    for very large negative z. (For very negative z, e^{-z} overflows; clipping
    keeps it finite and the result is effectively 0 anyway.)

    TODO: implement.
      - First np.clip z to a safe range (e.g. [-500, 500]).
      - Then return the element-wise logistic 1 / (1 + e^{-z}) using np.exp.
    """
    # TODO: implement the sigmoid
    raise NotImplementedError("TODO: implement sigmoid()")


def bce_loss(p: np.ndarray, y: np.ndarray) -> float:
    """
    Mean binary cross-entropy (log loss).

    L = -1/N · Σ [ y·log(p) + (1-y)·log(1-p) ]

    Clip p to [1e-12, 1 - 1e-12] first so log never sees 0 or 1.

    TODO: implement.
      - np.clip p to [1e-12, 1 - 1e-12] so np.log never sees 0 or 1.
      - Compute the per-sample term y·log(p) + (1-y)·log(1-p) per the formula,
        and return the negative mean as a float.
    """
    # TODO: implement binary cross-entropy
    raise NotImplementedError("TODO: implement bce_loss()")


class LogisticRegression:
    """Binary logistic regression trained with full-batch gradient descent."""

    def __init__(self, n_features: int, lr: float = 0.1, lam: float = 0.0) -> None:
        # n_features already INCLUDES the bias column.
        self.lr = lr
        self.lam = lam  # L2 strength (0 = no regularisation)
        self.w = np.zeros(n_features, dtype=np.float64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Return P(class = 1 | x) = σ(X w) for each row of X.

        TODO: implement — apply sigmoid() to the linear score X @ self.w.
        """
        # TODO: implement predict_proba
        raise NotImplementedError("TODO: implement predict_proba()")

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Return 0/1 predictions by thresholding predict_proba at `threshold`."""
        return (self.predict_proba(X) >= threshold).astype(np.int64)

    def loss(self, X: np.ndarray, y: np.ndarray) -> float:
        """Cross-entropy loss (does not include the L2 penalty — for logging)."""
        return bce_loss(self.predict_proba(X), y)

    def gradient_step(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        One full-batch gradient-descent update. Returns the (pre-update) BCE loss.

        Forward:  p = σ(X w)
        Gradient: grad = Xᵀ (p - y) / N        (+ L2 term)
        L2:       add (lam / N) · w   to the gradient, but ZERO the bias entry
                  (grad[0]) so we never regularise the intercept.
        Update:   w -= lr · grad

        TODO: implement.
          - Forward pass: p = self.predict_proba(X); record the pre-update
            bce_loss(p, y) to return at the end.
          - Data gradient: Xᵀ·(p - y) / N per the formula above.
          - L2 term: (self.lam / N) · self.w, but with the bias entry (index 0)
            zeroed so the intercept is never regularised; add it to the gradient.
          - Update self.w in place by -lr · grad, then return the recorded loss.
        """
        # TODO: implement the gradient step
        raise NotImplementedError("TODO: implement gradient_step()")

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        """Fraction of correct 0/1 predictions."""
        return float(np.mean(self.predict(X) == y))


# ---------------------------------------------------------------------------
# Training loop  (provided — do not edit)
# ---------------------------------------------------------------------------


def train(
    model: LogisticRegression,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 200,
    print_every: int = 40,
) -> list[float]:
    """Full-batch gradient descent. Returns the loss history.

    Pass print_every=0 to train silently (used for the λ sweep below).
    """
    history: list[float] = []
    for epoch in range(epochs):
        loss = model.gradient_step(X, y)
        history.append(loss)
        if print_every and ((epoch + 1) % print_every == 0 or epoch == 0):
            print(f"  epoch {epoch + 1:>4}/{epochs}  loss={loss:.4f}")
    return history


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 3 — Binary logistic regression with gradient descent + L2\n")

    X_raw, y = make_data()
    X = add_bias_column(X_raw)
    X_train, X_test, y_train, y_test = stratified_split(X, y)
    print(f"  Data: {X.shape[0]} samples, 2 classes.  Train {len(y_train)}  Test {len(y_test)}\n")

    # ── Train a plain model (no regularisation) ──────────────────────────────
    print("[1/2] Training (λ=0)...")
    model = LogisticRegression(n_features=X.shape[1], lr=0.5, lam=0.0)
    print(f"  Initial train loss: {model.loss(X_train, y_train):.4f}")
    history = train(model, X_train, y_train, epochs=200, print_every=40)

    train_acc = model.accuracy(X_train, y_train)
    test_acc = model.accuracy(X_test, y_test)
    print(f"\n  Train accuracy: {train_acc:.2%}")
    print(f"  Test accuracy:  {test_acc:.2%}")

    # Monotone loss over first 30 epochs?
    first30 = history[:30]
    monotonic = all(first30[i + 1] <= first30[i] + 1e-9 for i in range(len(first30) - 1))
    print(f"  Loss monotone over first 30 epochs: {monotonic}\n")

    # ── L2 sweep: larger λ → smaller ||w|| ───────────────────────────────────
    print("[2/2] L2 regularisation sweep (larger λ should shrink ||w||):\n")
    print(f"  {'lambda':>8} | {'train acc':>9} | {'||w[1:]||':>10}")
    print(f"  {'-' * 8}-+-{'-' * 9}-+-{'-' * 10}")

    lambdas = [0.0, 1.0, 10.0, 50.0]
    weight_norms: list[float] = []
    for lam in lambdas:
        m = LogisticRegression(n_features=X.shape[1], lr=0.5, lam=lam)
        train(m, X_train, y_train, epochs=200, print_every=0)  # silent
        # weight norm excluding the bias (w[0]) — that's the part L2 controls
        wn = float(np.linalg.norm(m.w[1:]))
        weight_norms.append(wn)
        print(f"  {lam:>8.1f} | {m.accuracy(X_train, y_train):>9.2%} | {wn:>10.4f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_acc = train_acc >= 0.95
    ok_monotone = monotonic
    # Larger λ yields smaller ||w|| — check the norms are strictly decreasing.
    ok_l2 = all(weight_norms[i + 1] < weight_norms[i] for i in range(len(weight_norms) - 1))

    print(f"  [{'x' if ok_acc else ' '}] Train accuracy ≥ 0.95  (got {train_acc:.2%})")
    print(
        f"  [{'x' if ok_monotone else ' '}] BCE loss decreases monotonically over first 30 epochs"
    )
    print(
        f"  [{'x' if ok_l2 else ' '}] Larger λ yields smaller ||w||  "
        f"(norms: {[round(w, 3) for w in weight_norms]})"
    )

    if ok_acc and ok_monotone and ok_l2:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
