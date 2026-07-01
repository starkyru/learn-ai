"""
Task 2 🟡 — OPTIMIZERS (SGD / momentum / Adam) and weight INITIALISATION.

What you'll learn:
  - How the same gradient produces very different steps under SGD / momentum / Adam.
  - Why Adam usually reaches a target loss in fewer epochs (adaptive per-param steps).
  - He vs Xavier initialisation and why the fan-in scale keeps activations sane.
  - The vanishing-gradient problem: sigmoid squashes gradients, ReLU doesn't.

The math (README §2 explains each step in plain English):

  SGD:       θ ← θ - lr·g
  Momentum:  v ← β·v + (1-β)·g ;              θ ← θ - lr·v            (β=0.9)
  Adam:      m ← β1·m + (1-β1)·g
             v ← β2·v + (1-β2)·g²
             m̂ = m/(1-β1^t) ;  v̂ = v/(1-β2^t)                        (t = step, 1-indexed)
             θ ← θ - lr·m̂/(sqrt(v̂)+ε)          (β1=0.9, β2=0.999, ε=1e-8)

  He init (ReLU):        scale = sqrt(2 / fan_in)
  Xavier init (tanh):    scale = sqrt(2 / (fan_in + fan_out))

  Vanishing gradients: sigmoid'(x)=σ(1-σ) ≤ 0.25, so a deep sigmoid net multiplies
  many small factors → tiny first-layer gradients. ReLU'(x)=1 for x>0 → gradients survive.

Everything (dataset, forward, MANUAL backprop, training loop) is provided.
You implement the three optimizer update rules and the two init scale factors.

How to run:
  uv run python modules/01c-deep-learning/py/02_optimizers.py

Only numpy is used.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Init scale factors — implement these
# ---------------------------------------------------------------------------


def he_init(fan_in: int, fan_out: int) -> float:
    """
    He initialisation scale (std of the Normal), tuned for ReLU.

    TODO: return the He scale factor (see the He-init formula in the file header) —
    it depends only on `fan_in`.
    """
    raise NotImplementedError("TODO: implement he_init()")


def xavier_init(fan_in: int, fan_out: int) -> float:
    """
    Xavier/Glorot initialisation scale (std of the Normal), tuned for tanh/sigmoid.

    TODO: return the Xavier scale factor (see the Xavier-init formula in the file
    header) — it uses both `fan_in` and `fan_out`.
    """
    raise NotImplementedError("TODO: implement xavier_init()")


# ---------------------------------------------------------------------------
# Optimizer update rules — implement these
# ---------------------------------------------------------------------------


def sgd_update(param: np.ndarray, grad: np.ndarray, state: dict, lr: float) -> None:
    """
    Plain SGD, IN PLACE:   param -= lr * grad

    `state` is unused for SGD (kept for a uniform signature).

    TODO: update `param` in place — step it down the gradient by `lr` (use `-=` so
    the numpy array is mutated in place, not rebound).
    """
    raise NotImplementedError("TODO: implement sgd_update()")


def momentum_update(
    param: np.ndarray, grad: np.ndarray, state: dict, lr: float, beta: float = 0.9
) -> None:
    """
    SGD with momentum, IN PLACE. `state["v"]` holds the running velocity (init 0).

      v ← β·v + (1-β)·g
      param ← param - lr·v

    TODO: implement using the two-line rule in the docstring above.
      - Read the running velocity from `state["v"]` (same shape as param, starts 0).
      - Update it to the exponential moving average of the gradient — write it back
        in place (`v[:] = ...`) so the stored state persists across steps.
      - Step `param` down that velocity by `lr` (in place, `-=`).
    """
    raise NotImplementedError("TODO: implement momentum_update()")


def adam_update(
    param: np.ndarray,
    grad: np.ndarray,
    state: dict,
    lr: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    eps: float = 1e-8,
) -> None:
    """
    Adam, IN PLACE. `state` holds "m", "v" (both init 0) and "t" (step count, init 0).

      t ← t + 1
      m ← β1·m + (1-β1)·g
      v ← β2·v + (1-β2)·g²
      m̂ = m / (1 - β1^t)
      v̂ = v / (1 - β2^t)
      param ← param - lr·m̂ / (sqrt(v̂) + ε)

    TODO: implement the six-line rule in the docstring above.
      - Increment the step counter `state["t"]` and read it as `t` (needed for bias
        correction — this is why t must persist in state, not reset each call).
      - Update the two running moments `state["m"]` (mean of g) and `state["v"]`
        (mean of g²) in place, mixing in the new gradient with beta1 / beta2.
      - Bias-correct each moment by dividing by (1 - beta^t).
      - Step `param` in place: the corrected mean over the sqrt of the corrected
        second moment (plus `eps` for numerical safety), scaled by `lr`.
    """
    raise NotImplementedError("TODO: implement adam_update()")


# ---------------------------------------------------------------------------
# Synthetic dataset (complete) — a 2-D two-spiral-ish nonlinear binary problem
# ---------------------------------------------------------------------------


def make_dataset(n: int = 400, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Two interleaving clusters that are NOT linearly separable (needs a hidden layer).
    Returns X (n, 2) and y (n,) with labels in {0, 1}.
    """
    rng = np.random.default_rng(seed)
    half = n // 2
    # Class 0: ring near radius 1 ; Class 1: ring near radius 2.5
    theta0 = rng.uniform(0, 2 * np.pi, half)
    r0 = 1.0 + rng.normal(0, 0.15, half)
    x0 = np.stack([r0 * np.cos(theta0), r0 * np.sin(theta0)], axis=1)
    theta1 = rng.uniform(0, 2 * np.pi, half)
    r1 = 2.5 + rng.normal(0, 0.15, half)
    x1 = np.stack([r1 * np.cos(theta1), r1 * np.sin(theta1)], axis=1)
    X = np.concatenate([x0, x1], axis=0).astype(np.float64)
    y = np.concatenate([np.zeros(half), np.ones(half)]).astype(np.int64)
    perm = rng.permutation(n)
    return X[perm], y[perm]


# ---------------------------------------------------------------------------
# A matrix-form 2-layer MLP with MANUAL backprop (complete — you don't edit this)
# ---------------------------------------------------------------------------


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


class TwoLayerMLP:
    """
    Architecture:  X (N,2) → W1,b1 → hidden (relu or sigmoid) → W2,b2 → sigmoid → p (N,1)
    Loss: binary cross-entropy. Backprop is written out by hand below.
    """

    def __init__(self, n_in: int, n_hidden: int, activation: str, init: str, seed: int = 0):
        self.activation = activation
        rng = np.random.default_rng(seed)
        s1 = he_init(n_in, n_hidden) if init == "he" else xavier_init(n_in, n_hidden)
        s2 = he_init(n_hidden, 1) if init == "he" else xavier_init(n_hidden, 1)
        self.W1 = rng.normal(0, s1, (n_in, n_hidden))
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.normal(0, s2, (n_hidden, 1))
        self.b2 = np.zeros(1)

    def _act(self, z: np.ndarray) -> np.ndarray:
        return np.maximum(0, z) if self.activation == "relu" else sigmoid(z)

    def _act_grad(self, z: np.ndarray, a: np.ndarray) -> np.ndarray:
        if self.activation == "relu":
            return (z > 0).astype(z.dtype)
        return a * (1 - a)  # sigmoid'(z) = a(1-a)

    def forward(self, X: np.ndarray) -> dict:
        z1 = X @ self.W1 + self.b1
        a1 = self._act(z1)
        z2 = a1 @ self.W2 + self.b2
        p = sigmoid(z2)
        return {"X": X, "z1": z1, "a1": a1, "z2": z2, "p": p}

    def loss(self, X: np.ndarray, y: np.ndarray) -> float:
        p = self.forward(X)["p"].ravel()
        p = np.clip(p, 1e-12, 1 - 1e-12)
        return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))

    def backward(self, cache: dict, y: np.ndarray) -> dict:
        """Manual backprop. Returns grads for W1,b1,W2,b2. (Complete.)"""
        X, a1, p = cache["X"], cache["a1"], cache["p"]
        N = X.shape[0]
        yc = y.reshape(-1, 1).astype(p.dtype)
        # dL/dz2 for BCE + sigmoid is (p - y) — same elegant form as softmax+CE
        dz2 = (p - yc) / N  # (N, 1)
        dW2 = a1.T @ dz2  # (H, 1)
        db2 = dz2.sum(axis=0)  # (1,)
        da1 = dz2 @ self.W2.T  # (N, H)
        dz1 = da1 * self._act_grad(cache["z1"], a1)  # (N, H)
        dW1 = X.T @ dz1  # (2, H)
        db1 = dz1.sum(axis=0)  # (H,)
        return {"W1": dW1, "b1": db1, "W2": dW2, "b2": db2}

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.forward(X)["p"].ravel() > 0.5).astype(np.int64)


# ---------------------------------------------------------------------------
# Generic training loop that plugs in any optimizer (complete)
# ---------------------------------------------------------------------------

OPTIMIZERS = {
    "sgd": sgd_update,
    "momentum": momentum_update,
    "adam": adam_update,
}


def train_until(
    model: TwoLayerMLP,
    X: np.ndarray,
    y: np.ndarray,
    optimizer: str,
    lr: float,
    target_loss: float,
    max_epochs: int = 2000,
) -> tuple[int, float]:
    """
    Full-batch training. Runs until loss <= target_loss or max_epochs.
    Returns (epochs_used, final_loss). Calls the chosen optimizer update per param.
    """
    update = OPTIMIZERS[optimizer]
    params = {"W1": model.W1, "b1": model.b1, "W2": model.W2, "b2": model.b2}
    # Per-parameter optimizer state (velocity / moments)
    state = {
        name: {"v": np.zeros_like(p), "m": np.zeros_like(p), "t": 0} for name, p in params.items()
    }

    for epoch in range(1, max_epochs + 1):
        cache = model.forward(X)
        grads = model.backward(cache, y)
        for name, p in params.items():
            update(p, grads[name], state[name], lr)
        loss = model.loss(X, y)
        if loss <= target_loss:
            return epoch, loss
    return max_epochs, model.loss(X, y)


# ---------------------------------------------------------------------------
# Vanishing-gradient demo (complete) — deep net, sigmoid vs relu first-layer grad
# ---------------------------------------------------------------------------


def first_layer_grad_norm(activation: str, depth: int = 8, width: int = 16, seed: int = 3) -> float:
    """
    Build a `depth`-layer net (all hidden), do one forward+backward pass on random
    data, and return the L2 norm of the gradient at the FIRST layer's weights.

    With sigmoid, each layer multiplies gradient by ≤0.25 → the first-layer grad is
    tiny. With relu, the derivative is 1 for active units → the grad stays large.
    (Complete — reuses the same activation gradients as the MLP above.)
    """
    rng = np.random.default_rng(seed)
    N = 64
    X = rng.normal(0, 1, (N, width))
    y = rng.integers(0, 2, N).astype(np.float64).reshape(-1, 1)

    # Xavier init so both nets start on equal footing (the point is the activation).
    scale = xavier_init(width, width)
    Ws = [rng.normal(0, scale, (width, width)) for _ in range(depth)]
    Wout = rng.normal(0, scale, (width, 1))

    def act(z):
        return np.maximum(0, z) if activation == "relu" else sigmoid(z)

    def act_grad(z, a):
        return (z > 0).astype(z.dtype) if activation == "relu" else a * (1 - a)

    # Forward, storing per-layer pre/post activations
    zs, as_ = [], [X]
    h = X
    for W in Ws:
        z = h @ W
        h = act(z)
        zs.append(z)
        as_.append(h)
    p = sigmoid(h @ Wout)

    # Backward
    dz = (p - y) / N  # BCE+sigmoid gradient at output
    dh = dz @ Wout.T
    grads = [None] * depth
    for i in reversed(range(depth)):
        dz_i = dh * act_grad(zs[i], as_[i + 1])
        grads[i] = as_[i].T @ dz_i
        dh = dz_i @ Ws[i].T
    return float(np.linalg.norm(grads[0]))


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    print("\n=== Task 2: optimizers + initialisation ===\n")

    X, y = make_dataset(n=400, seed=0)
    print(f"Dataset: {X.shape[0]} points, 2 nonlinear classes (rings).")

    # ── Optimizer race: same seed/data/model, count epochs to target loss ─────
    print("\n[1/2] Epochs to reach target loss (lower = faster convergence):")
    target = 0.20
    results: dict[str, tuple[int, float]] = {}
    lrs = {"sgd": 0.5, "momentum": 0.5, "adam": 0.05}
    for opt in ("sgd", "momentum", "adam"):
        model = TwoLayerMLP(n_in=2, n_hidden=16, activation="relu", init="he", seed=7)
        epochs, loss = train_until(
            model, X, y, opt, lr=lrs[opt], target_loss=target, max_epochs=5000
        )
        results[opt] = (epochs, loss)
        print(f"    {opt:<9}: {epochs:>5} epochs  (final loss {loss:.4f}, lr={lrs[opt]})")

    adam_faster = results["adam"][0] < results["sgd"][0]
    print(f"\n  Adam reached target in fewer epochs than SGD: {adam_faster}")

    # ── Vanishing-gradient demo ───────────────────────────────────────────────
    print("\n[2/2] Vanishing gradients — first-layer grad norm in an 8-layer net:")
    g_sigmoid = first_layer_grad_norm("sigmoid")
    g_relu = first_layer_grad_norm("relu")
    ratio = g_relu / g_sigmoid if g_sigmoid > 0 else float("inf")
    print(f"    sigmoid first-layer |grad| = {g_sigmoid:.3e}")
    print(f"    relu    first-layer |grad| = {g_relu:.3e}")
    print(f"    ratio (relu / sigmoid)     = {ratio:.1f}x   (want > 5x)")
    print(f"\n  ReLU grad clearly larger than sigmoid: {ratio > 5}")


if __name__ == "__main__":
    main()
