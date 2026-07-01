"""
Task 4 🔴 — Multinomial logistic regression FROM SCRATCH.

What you'll learn:
  - The softmax function and why it turns raw scores into probabilities
  - Cross-entropy loss: the standard loss for classification
  - Gradient descent: how the weight matrix updates to minimise loss
  - Why the gradient of softmax + cross-entropy is elegantly simple

The math (README explains each step in plain English):

  Forward pass:
    z = X @ W + b           (linear layer: batch of scores, shape [N, C])
    p = softmax(z)          (probabilities, each row sums to 1)
    L = cross_entropy(p, y) (scalar loss)

  Backward pass (gradient of L with respect to W and b):
    dL/dz = p - one_hot(y)  (elegant: error is just predicted - true probs)
    dL/dW = X.T @ dL/dz / N
    dL/db = mean(dL/dz, axis=0)

  Update:
    W -= lr * dL/dW
    b -= lr * dL/db

No sklearn in this task. Only numpy.

How to run:
  uv run python modules/08-classification/py/04_logistic_scratch.py

The harness loads the dataset, embeds the texts, trains the model, and prints
training loss + final test accuracy. The gradient step is left as a TODO so you
implement the learning yourself.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
from llm_core import get_provider

DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "texts.json"
LABEL_NAMES = ["technology", "science", "business", "sports", "health", "politics"]
NUM_CLASSES = len(LABEL_NAMES)

# ---------------------------------------------------------------------------
# Data loading and embedding
# ---------------------------------------------------------------------------


def load_and_embed(provider) -> tuple[np.ndarray, np.ndarray]:
    """
    Load the dataset and embed all texts.

    Returns:
      X : float32 array of shape (N, D) — embedding matrix
      y : int array of shape (N,)     — label indices
    """
    with open(DATA_PATH) as f:
        data = json.load(f)

    texts = [item["text"] for item in data]
    label_to_idx = {l: i for i, l in enumerate(LABEL_NAMES)}
    y = np.array([label_to_idx[item["label"]] for item in data], dtype=np.int64)

    # Embed in one batch (50 texts is well within limits)
    result = provider.embed(texts)
    X = np.array(result.vectors, dtype=np.float32)
    return X, y


# ---------------------------------------------------------------------------
# Train/test split (same stratified 80/20 as other tasks)
# ---------------------------------------------------------------------------


def stratified_split(
    X: np.ndarray, y: np.ndarray, test_fraction: float = 0.2, seed: int = 42
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
# Softmax and cross-entropy — implement these
# ---------------------------------------------------------------------------


def softmax(z: np.ndarray) -> np.ndarray:
    """
    Softmax over the last axis.

    softmax(z)_i = exp(z_i) / sum_j(exp(z_j))

    Numerically stable version: subtract max(z) before exp() to prevent overflow.
    This doesn't change the result because exp(z - max) / sum(exp(z - max))
    = exp(z) / sum(exp(z)).

    Shape: z is (N, C) → returns (N, C), each row sums to 1.

    TODO: implement the numerically-stable softmax.
      - First shift each row so its max becomes 0: subtract the per-row max.
        Use `np.max(..., axis=1, keepdims=True)` so it broadcasts back over rows.
      - Exponentiate the shifted scores, then divide each row by its own sum
        (again reduce with `axis=1, keepdims=True` so the shapes broadcast).
    """
    # TODO: implement numerically-stable softmax
    raise NotImplementedError("TODO: implement softmax()")


def cross_entropy_loss(probs: np.ndarray, y: np.ndarray) -> float:
    """
    Mean cross-entropy loss over a batch.

    L = -1/N * sum_i( log( p[i, y[i]] ) )

    p[i, y[i]] is the predicted probability for the TRUE class of sample i.
    We want this to be 1.0 (log 1 = 0, no loss); if it's tiny, log is very negative.

    Clip probabilities at 1e-12 to avoid log(0).

    TODO: implement.
      - Clip `probs` into the range [1e-12, 1.0] with `np.clip` before taking any log.
      - Pull out the probability assigned to each sample's TRUE class. Advanced
        indexing does this in one shot: index rows with `np.arange(N)` and columns
        with `y`.
      - The loss is the negative mean of the logs of those correct-class probs.
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement cross_entropy_loss()")


# ---------------------------------------------------------------------------
# Logistic regression model
# ---------------------------------------------------------------------------


class LogisticRegressionScratch:
    """
    Multinomial logistic regression trained with mini-batch gradient descent.

    This is a LINEAR classifier on top of the embedding features.
    Exactly what sklearn's LogisticRegression does, minus the L2 regularisation.

    Attributes:
      W : weight matrix of shape (D, C)  — D = embed dim, C = num classes
      b : bias vector of shape (C,)
    """

    def __init__(self, n_features: int, n_classes: int, lr: float = 0.1) -> None:
        self.lr = lr
        # Xavier initialisation — keeps activations from exploding/vanishing
        scale = np.sqrt(2.0 / (n_features + n_classes))
        rng = np.random.default_rng(42)
        self.W = rng.normal(0, scale, (n_features, n_classes)).astype(np.float32)
        self.b = np.zeros(n_classes, dtype=np.float32)

    def forward(self, X: np.ndarray) -> np.ndarray:
        """
        Forward pass: return softmax probabilities.

        z = X @ W + b   (shape: N × C)
        p = softmax(z)  (shape: N × C)

        TODO: implement.
        """
        # TODO: implement forward pass
        raise NotImplementedError("TODO: implement forward()")

    def loss(self, X: np.ndarray, y: np.ndarray) -> float:
        """Compute cross-entropy loss on a batch."""
        probs = self.forward(X)
        return cross_entropy_loss(probs, y)

    def gradient_step(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        Compute gradients and update W and b.

        Forward:
          z     = X @ W + b                    shape: (N, C)
          probs = softmax(z)                   shape: (N, C)
          loss  = cross_entropy(probs, y)      scalar

        Backward (the beautiful result of differentiating softmax + cross-entropy):
          dL/dz = probs - one_hot(y)           shape: (N, C)
                  (predicted probs minus the true 1-hot target)

          dL/dW = X.T @ dL/dz  / N            shape: (D, C)
          dL/db = mean(dL/dz, axis=0)          shape: (C,)

        Update:
          W -= lr * dL/dW
          b -= lr * dL/db

        Return the scalar loss (for logging).

        TODO: implement this method — translate the math above into numpy.
          - Run the forward pass (self.forward) to get probs, and record the loss
            (self.loss or cross_entropy_loss) so you can return it at the end.
          - Build the one-hot target matrix for y (shape N×C): a zeros array with a
            single 1 per row in the true-class column.
          - Form dz = probs - one_hot, then turn it into the two gradients using the
            dL/dW and dL/db formulas above (note the 1/N and the `axis=0` mean).
          - Take one gradient-descent step on self.W and self.b (subtract lr * grad),
            and return the scalar loss.
        """
        # TODO: implement gradient step
        raise NotImplementedError("TODO: implement gradient_step()")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return the predicted class index for each row of X."""
        return np.argmax(self.forward(X), axis=1)

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        """Fraction of correct predictions."""
        return float(np.mean(self.predict(X) == y))


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------


def train(
    model: LogisticRegressionScratch,
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 200,
    batch_size: int = 16,
    print_every: int = 20,
) -> list[float]:
    """
    Mini-batch gradient descent training loop.

    Each epoch:
      1. Shuffle the training set.
      2. Split into mini-batches of `batch_size`.
      3. Call model.gradient_step() on each batch.
      4. Record the mean loss over all batches.

    This function is complete — you don't need to edit it.
    It calls model.gradient_step() which you implement above.
    """
    N = len(y_train)
    loss_history: list[float] = []
    rng = np.random.default_rng(42)

    for epoch in range(epochs):
        perm = rng.permutation(N)
        X_shuf, y_shuf = X_train[perm], y_train[perm]

        epoch_losses: list[float] = []
        for start in range(0, N, batch_size):
            Xb = X_shuf[start : start + batch_size]
            yb = y_shuf[start : start + batch_size]
            loss = model.gradient_step(Xb, yb)
            epoch_losses.append(loss)

        mean_loss = float(np.mean(epoch_losses))
        loss_history.append(mean_loss)

        if (epoch + 1) % print_every == 0 or epoch == 0:
            print(f"  Epoch {epoch + 1:>4}/{epochs}  loss={mean_loss:.4f}")

    return loss_history


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (embed model: {provider.embed_model})")

    # ── Load & embed ──────────────────────────────────────────────────────
    print("\n[1/4] Loading and embedding dataset...")
    X, y = load_and_embed(provider)
    print(f"  X shape: {X.shape}   (N={X.shape[0]}, D={X.shape[1]})")
    print(f"  y shape: {y.shape}   classes: {NUM_CLASSES}")

    # ── Split ─────────────────────────────────────────────────────────────
    print("\n[2/4] Stratified 80/20 train/test split...")
    X_train, X_test, y_train, y_test = stratified_split(X, y)
    print(f"  Train: {len(y_train)}  Test: {len(y_test)}")

    # ── Build model ───────────────────────────────────────────────────────
    D = X.shape[1]   # embedding dimension
    print(f"\n[3/4] Building LogisticRegressionScratch(D={D}, C={NUM_CLASSES})...")
    model = LogisticRegressionScratch(n_features=D, n_classes=NUM_CLASSES, lr=0.5)

    # ── Train ─────────────────────────────────────────────────────────────
    print("\n[4/4] Training with mini-batch gradient descent...")
    print(f"  Initial train loss: {model.loss(X_train, y_train):.4f}")
    print(f"  Initial train acc:  {model.accuracy(X_train, y_train):.2%}")
    print()

    loss_history = train(model, X_train, y_train, epochs=300, batch_size=16, print_every=50)

    # ── Evaluate ──────────────────────────────────────────────────────────
    train_acc = model.accuracy(X_train, y_train)
    test_acc = model.accuracy(X_test, y_test)

    print(f"\n  Final train loss: {loss_history[-1]:.4f}")
    print(f"  Train accuracy:   {train_acc:.2%}")
    print(f"  Test accuracy:    {test_acc:.2%}")

    # Per-class breakdown
    print("\n  Per-class test accuracy:")
    for cls_idx, cls_name in enumerate(LABEL_NAMES):
        mask = y_test == cls_idx
        if mask.sum() == 0:
            continue
        cls_acc = float(np.mean(model.predict(X_test[mask]) == y_test[mask]))
        print(f"    {cls_name:<12} : {cls_acc:.2%} (n={mask.sum()})")

    print("\n  Compare to Task 3 results — is from-scratch LR close to sklearn LR?")
    print("  Reflection: the gradient formula dL/dz = p - one_hot(y) is the")
    print("  'beautiful' result of differentiating softmax + cross-entropy jointly.")


if __name__ == "__main__":
    main()
