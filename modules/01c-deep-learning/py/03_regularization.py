"""
Task 3 🟡 — REGULARISATION: inverted dropout, batchnorm, and L2 weight decay.

What you'll learn:
  - Why a high-capacity net overfits (train acc ≫ test acc) on small noisy data.
  - Inverted dropout: randomly drop neurons at train time, scale to keep the mean,
    do nothing at test time.
  - Batch normalisation: normalise each feature to mean 0 / var 1, then rescale.
  - L2 weight decay: add (λ/2)·ΣW² to the loss → an extra λ·W term in each gradient.

The math (README §3 explains each step in plain English):

  Inverted dropout (train):  mask ~ Bernoulli(1-p);  out = (x * mask) / (1 - p)
  Inverted dropout (test):   out = x                       (identity)

  Batchnorm forward:
    μ  = mean(x over batch)          σ² = var(x over batch)     (per feature)
    x̂  = (x - μ) / sqrt(σ² + ε)
    out = γ · x̂ + β                  (with γ=1, β=0 → mean 0, var 1)

  L2:  L_total = L_data + (λ/2)·ΣW²  →  ∂/∂W = λ·W  (added to the data gradient)

The dataset, the 2-layer MLP, backprop, and the training loop are provided. You
implement dropout_forward, batchnorm_forward, and l2_grad.

How to run:
  uv run python modules/01c-deep-learning/py/03_regularization.py

Only numpy is used.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# The three regularisers — implement these
# ---------------------------------------------------------------------------


def dropout_forward(
    x: np.ndarray, p: float, training: bool, rng: np.random.Generator
) -> np.ndarray:
    """
    Inverted dropout.

    Training: draw a Bernoulli(keep_prob=1-p) mask the same shape as x, zero the
    dropped units, and divide the survivors by (1-p) so E[out] == x. This scaling
    is why test time can be a plain identity — the expectation already matches.

    Test: return x unchanged (identity).

    TODO: implement.
      - If not training, return `x` untouched.
      - Otherwise let keep = 1 - p. Draw a keep/drop mask the shape of `x` using
        `rng.random(x.shape)` compared against `keep` (True = keep).
      - Return `x` with dropped units zeroed and survivors divided by `keep`, so
        E[out] == x. Keep it vectorised (no Python loop).
    """
    raise NotImplementedError("TODO: implement dropout_forward()")


def batchnorm_forward(
    x: np.ndarray, gamma: np.ndarray, beta: np.ndarray, eps: float = 1e-5
) -> np.ndarray:
    """
    Batch normalisation forward pass (per-feature, over the batch axis=0).

      μ   = x.mean(axis=0)             # (D,)  one mean per feature
      var = x.var(axis=0)              # (D,)  one variance per feature
      x̂   = (x - μ) / sqrt(var + eps)  # normalised: each feature ~ mean 0 / var 1
      out = gamma * x̂ + beta           # learnable rescale/shift

    With gamma=1, beta=0 the OUTPUT has per-feature mean ≈ 0 and var ≈ 1.

    TODO: implement the four steps in the formula above and return the (N, D) output.
      - Compute the per-feature mean and variance over the batch — reduce over the
        rows, i.e. `axis=0`, so each is shape (D,).
      - Normalise: subtract the mean, divide by sqrt(var + eps).
      - Apply the learnable rescale/shift with `gamma` and `beta` (broadcasts over rows).
    """
    raise NotImplementedError("TODO: implement batchnorm_forward()")


def l2_grad(W: np.ndarray, lam: float) -> np.ndarray:
    """
    Gradient contribution of the L2 penalty (λ/2)·ΣW²  →  λ·W.
    This is ADDED onto the data gradient of the same weight matrix.

    TODO: return the elementwise derivative of the (λ/2)·ΣW² penalty w.r.t. W.
    """
    raise NotImplementedError("TODO: implement l2_grad()")


# ---------------------------------------------------------------------------
# Small NOISY dataset that a big net will overfit (complete)
# ---------------------------------------------------------------------------


def make_noisy_dataset(
    n: int = 90, dim: int = 60, n_informative: int = 3, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """
    A binary problem where the label depends on only `n_informative` dims but the
    input has MANY pure-noise dims. With a small training set a high-capacity net
    latches onto spurious noise-dim correlations (memorises the train set) and
    generalises poorly — the classic overfitting setup. There is NO label noise,
    so the signal is fully learnable; the gap comes purely from the noise features.
    """
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, (n, dim))
    w_true = np.zeros(dim)
    # Only the first `n_informative` dims carry signal; the rest are noise.
    w_true[:n_informative] = rng.normal(0, 1.5, n_informative)
    y = (X @ w_true > 0).astype(np.int64)
    return X.astype(np.float64), y


def split(X: np.ndarray, y: np.ndarray, test_n: int = 30) -> tuple:
    """Fixed split: last `test_n` rows are the test set (deterministic)."""
    return X[:-test_n], X[-test_n:], y[:-test_n], y[-test_n:]


# ---------------------------------------------------------------------------
# 2-layer MLP with dropout + batchnorm + L2 (complete — uses your functions)
# ---------------------------------------------------------------------------


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


class RegularizedMLP:
    """
    X → W1,b1 → batchnorm(optional) → relu → dropout(optional) → W2,b2 → sigmoid.
    """

    def __init__(self, n_in: int, n_hidden: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0, np.sqrt(2.0 / n_in), (n_in, n_hidden))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0, np.sqrt(2.0 / n_hidden), (n_hidden, 1))
        self.b2 = np.zeros(1)
        self.gamma = np.ones(n_hidden)
        self.beta = np.zeros(n_hidden)

    def forward(self, X: np.ndarray, training: bool, dropout_p: float, use_bn: bool, rng) -> dict:
        z1 = X @ self.W1 + self.b1
        bn = batchnorm_forward(z1, self.gamma, self.beta) if use_bn else z1
        a1 = np.maximum(0, bn)
        a1_drop = dropout_forward(a1, dropout_p, training, rng) if dropout_p > 0 else a1
        z2 = a1_drop @ self.W2 + self.b2
        p = sigmoid(z2)
        return {"X": X, "z1": z1, "bn": bn, "a1": a1, "a1_drop": a1_drop, "p": p}

    def train_step(self, X, y, lr, dropout_p, use_bn, lam, rng) -> float:
        cache = self.forward(X, True, dropout_p, use_bn, rng)
        p, a1_drop = cache["p"], cache["a1_drop"]
        N = X.shape[0]
        yc = y.reshape(-1, 1).astype(p.dtype)
        dz2 = (p - yc) / N
        dW2 = a1_drop.T @ dz2 + l2_grad(self.W2, lam)  # L2 on W2
        db2 = dz2.sum(axis=0)
        da1 = dz2 @ self.W2.T
        da1 = da1 * (cache["bn"] > 0)  # relu grad (bn feeds relu)
        dW1 = X.T @ da1 + l2_grad(self.W1, lam)  # L2 on W1
        db1 = da1.sum(axis=0)
        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        p_clip = np.clip(p.ravel(), 1e-12, 1 - 1e-12)
        return float(-np.mean(yc.ravel() * np.log(p_clip) + (1 - yc.ravel()) * np.log(1 - p_clip)))

    def accuracy(self, X, y) -> float:
        # Eval mode: no dropout, batchnorm still normalises this batch.
        p = self.forward(X, False, 0.0, self._use_bn_eval, np.random.default_rng(0))["p"].ravel()
        return float(np.mean((p > 0.5).astype(np.int64) == y))

    _use_bn_eval = False


def train(model, X_tr, y_tr, epochs, lr, dropout_p, use_bn, lam, seed=0):
    rng = np.random.default_rng(seed)
    model._use_bn_eval = use_bn
    for _ in range(epochs):
        model.train_step(X_tr, y_tr, lr, dropout_p, use_bn, lam, rng)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n=== Task 3: regularisation (dropout / batchnorm / L2) ===\n")

    # ── Batchnorm sanity check ────────────────────────────────────────────────
    print("[1/2] Batchnorm output statistics (want mean≈0, var≈1):")
    rng = np.random.default_rng(1)
    x = rng.normal(5.0, 3.0, (64, 8))  # deliberately off-center, wide
    gamma, beta = np.ones(8), np.zeros(8)
    out = batchnorm_forward(x, gamma, beta)
    mean_abs = float(np.abs(out.mean(axis=0)).max())
    var_err = float(np.abs(out.var(axis=0) - 1.0).max())
    print(f"    max |per-feature mean| = {mean_abs:.2e}   (want < 1e-6)")
    print(f"    max |per-feature var-1| = {var_err:.2e}   (want < 1e-3)")
    bn_ok = mean_abs < 1e-6 and var_err < 1e-3
    print(f"    batchnorm normalises correctly: {bn_ok}")

    # ── Overfitting vs regularisation ─────────────────────────────────────────
    print("\n[2/2] Generalisation gap: no-reg vs dropout+L2 (same split & seed):")
    X, y = make_noisy_dataset(n=90, dim=60, n_informative=3, seed=0)
    X_tr, X_te, y_tr, y_te = split(X, y, test_n=30)

    # Baseline: high-capacity net, NO regularisation → memorises train set.
    m0 = RegularizedMLP(n_in=60, n_hidden=64, seed=42)
    train(m0, X_tr, y_tr, epochs=1500, lr=0.3, dropout_p=0.0, use_bn=False, lam=0.0)
    tr0, te0 = m0.accuracy(X_tr, y_tr), m0.accuracy(X_te, y_te)
    gap0 = tr0 - te0

    # Regularised: same architecture/seed, WITH dropout + L2.
    m1 = RegularizedMLP(n_in=60, n_hidden=64, seed=42)
    train(m1, X_tr, y_tr, epochs=1500, lr=0.3, dropout_p=0.2, use_bn=False, lam=1e-2)
    tr1, te1 = m1.accuracy(X_tr, y_tr), m1.accuracy(X_te, y_te)
    gap1 = tr1 - te1

    print(f"    no reg      : train {tr0:.2%}  test {te0:.2%}  gap {gap0:.2%}")
    print(f"    dropout+L2  : train {tr1:.2%}  test {te1:.2%}  gap {gap1:.2%}")
    print(f"\n  Regularisation shrank the generalisation gap: {gap1 < gap0}")
    print(f"  ({gap0:.2%} → {gap1:.2%})")


if __name__ == "__main__":
    main()
