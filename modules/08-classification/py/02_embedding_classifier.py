"""
Task 2 🟡 — Embeddings + classic ML classifier.

What you'll learn:
  - How to turn text into features via embeddings, then train a traditional classifier
  - Why "embedding as feature vector" bridges NLP and classical ML
  - The difference between LogisticRegression and k-Nearest Neighbours (kNN)
  - How train/test split prevents you from measuring what you've memorised
  - Why this approach is much cheaper at inference than an LLM call

The pipeline:
  text → embed → float vector → classifier (LR or kNN) → label

Key insight: once you have vectors you can use ANY classifier you already know.
The embedding model did the hard "understanding" work; your classifier just finds
a decision boundary in that pre-built space.

Dependencies:
  uv sync --extra ml       (installs scikit-learn)

How to run:
  uv run python modules/08-classification/py/02_embedding_classifier.py
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
from llm_core import get_provider

# scikit-learn is in the `ml` extra — `uv sync --extra ml`
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder

# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "texts.json"
LABELS = ["technology", "science", "business", "sports", "health", "politics"]


def load_dataset() -> tuple[list[str], list[str]]:
    """Return (texts, labels) lists in the same order."""
    with open(DATA_PATH) as f:
        data = json.load(f)
    texts = [item["text"] for item in data]
    labels = [item["label"] for item in data]
    return texts, labels


# ---------------------------------------------------------------------------
# Task 2a — Embed all texts
# ---------------------------------------------------------------------------


def embed_texts(texts: list[str], provider) -> np.ndarray:
    """
    Embed all texts in one (or a few) batch calls and return an (N, D) array.

    Some embedding providers have a batch size limit. A safe default:
    chunk the list into batches of 32 and concatenate.

    TODO:
      1. Split `texts` into batches of at most 32.
      2. For each batch call provider.embed(batch) and collect .vectors.
      3. Concatenate and return as np.array with shape (len(texts), embedding_dim).

    Note: Anthropic's provider raises on embed() — use ollama/openai/nvidia.
    """
    # TODO: implement batched embedding
    raise NotImplementedError("TODO: implement embed_texts()")


# ---------------------------------------------------------------------------
# Task 2b — Hand-rolled kNN (no sklearn)
# ---------------------------------------------------------------------------


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D vectors."""
    # TODO: implement cosine similarity
    #   dot(a, b) / (||a|| * ||b||)
    raise NotImplementedError("TODO: implement cosine_similarity()")


class KNNClassifier:
    """
    k-Nearest Neighbours classifier using cosine similarity.

    Implemented from scratch — no sklearn — so the logic is transparent.
    This also means you can use it in Task 3's TS parity section.

    Sklearn's KNeighborsClassifier is shown below for comparison.
    """

    def __init__(self, k: int = 5) -> None:
        self.k = k
        self._train_vectors: np.ndarray | None = None
        self._train_labels: list[str] | None = None

    def fit(self, X: np.ndarray, y: list[str]) -> "KNNClassifier":
        """
        Store the training set. kNN is a lazy learner — no real training.

        TODO: store X as self._train_vectors and y as self._train_labels.
        """
        # TODO: implement fit()
        raise NotImplementedError("TODO: implement KNNClassifier.fit()")

    def predict_one(self, x: np.ndarray) -> str:
        """
        Predict the label for a single vector.

        TODO:
          1. Compute cosine_similarity(x, train_vector) for every training vector.
          2. Find the k indices with the highest similarity.
          3. Gather their labels and return the most frequent (majority vote).
             In case of tie, return the label that appears first alphabetically.

        Hint: np.argsort on the similarity array, then take the last k elements.
        """
        # TODO: implement predict_one()
        raise NotImplementedError("TODO: implement KNNClassifier.predict_one()")

    def predict(self, X: np.ndarray) -> list[str]:
        """Predict labels for each row of X."""
        return [self.predict_one(X[i]) for i in range(len(X))]


# ---------------------------------------------------------------------------
# Task 2c — Train/test split and evaluation
# ---------------------------------------------------------------------------


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """
    Fraction of correct predictions.

    TODO: count how many positions where y_true and y_pred agree (zip them),
    then divide by the total number of samples.
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement accuracy()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (embed model: {provider.embed_model})")

    # ── Load dataset ──────────────────────────────────────────────────────
    texts, labels = load_dataset()
    print(f"Loaded {len(texts)} samples across {len(set(labels))} classes.")

    # ── Embed ─────────────────────────────────────────────────────────────
    print("\n[1/4] Embedding all texts...")
    X = embed_texts(texts, provider)
    print(f"  Embedding matrix shape: {X.shape}")

    # ── Train/test split (80/20, stratified so each class is represented) ──
    print("\n[2/4] Splitting into train/test (80/20, stratified)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=0.2, random_state=42, stratify=labels
    )
    print(f"  Train: {len(y_train)} | Test: {len(y_test)}")

    # ── Logistic Regression (sklearn) ─────────────────────────────────────
    print("\n[3/4] Training Logistic Regression (sklearn)...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_preds = lr.predict(X_test)
    lr_acc = accuracy(list(lr_preds), y_test)
    print(f"  LR accuracy on test set: {lr_acc:.2%}")

    # ── sklearn kNN for reference ─────────────────────────────────────────
    print("\n[4/4] Training sklearn kNN (k=5, cosine metric)...")
    sk_knn = KNeighborsClassifier(n_neighbors=5, metric="cosine")
    sk_knn.fit(X_train, y_train)
    sk_knn_preds = sk_knn.predict(X_test)
    sk_knn_acc = accuracy(list(sk_knn_preds), y_test)
    print(f"  sklearn kNN accuracy: {sk_knn_acc:.2%}")

    # ── Hand-rolled kNN ───────────────────────────────────────────────────
    print("\n[BONUS] Hand-rolled kNN (k=5)...")
    my_knn = KNNClassifier(k=5)
    my_knn.fit(X_train, y_train)
    my_knn_preds = my_knn.predict(X_test)
    my_knn_acc = accuracy(my_knn_preds, y_test)
    print(f"  Hand-rolled kNN accuracy: {my_knn_acc:.2%}")

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Logistic Regression (sklearn) : {lr_acc:.2%}")
    print(f"  kNN k=5 (sklearn, cosine)     : {sk_knn_acc:.2%}")
    print(f"  kNN k=5 (hand-rolled)         : {my_knn_acc:.2%}")
    print()
    print("  Save the test predictions — Task 3 (evaluation) uses them.")

    # Return data for Task 3 to import
    return {
        "X_test": X_test,
        "y_test": y_test,
        "lr_preds": list(lr_preds),
        "knn_preds": my_knn_preds,
        "X_train": X_train,
        "y_train": y_train,
    }


if __name__ == "__main__":
    main()
