"""
Task 3 🟡 — Evaluation: accuracy, precision, recall, F1, confusion matrix.

What you'll learn:
  - Why accuracy alone is misleading (class imbalance, minority classes)
  - Precision vs. recall: the trade-off between "don't cry wolf" and "miss nothing"
  - F1 score: the harmonic mean that balances precision and recall
  - Confusion matrix: where a classifier actually goes wrong
  - How to compare the LLM classifier vs. the trained embedding classifier

Key intuition:
  Precision = of everything I called "sports", how many actually were?
  Recall    = of all the "sports" items, how many did I find?
  F1        = 2 * P * R / (P + R)   — the harmonic mean, punishes extremes

This file re-runs the embedding classifier and the LLM classifier on the SAME
test split, then prints a side-by-side comparison.

How to run:
  uv run python modules/08-classification/py/03_evaluation.py

Note: this file calls the LLM for every test sample, so it will make ~10 API
calls (the test set is 10 items). Set LLM_PROVIDER=ollama for free inference.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
from llm_core import ChatMessage, get_provider

# We reuse helpers from the other tasks.
# In a real project these would be a shared module; here we inline what we need.

DATA_PATH = pathlib.Path(__file__).parent.parent / "data" / "texts.json"
LABELS_LIST = ["technology", "science", "business", "sports", "health", "politics"]


# ---------------------------------------------------------------------------
# Metrics — implement from scratch (sklearn.metrics available for comparison)
# ---------------------------------------------------------------------------


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    """
    Overall accuracy = correct / total.

    TODO: implement.
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement accuracy()")


def precision_recall_f1(
    y_true: list[str], y_pred: list[str], label: str
) -> tuple[float, float, float]:
    """
    Per-class precision, recall, and F1 for a single `label`.

    Definitions:
      TP = true positives : predicted `label` AND actually `label`
      FP = false positives: predicted `label` BUT actually something else
      FN = false negatives: actually `label`  BUT predicted something else

      Precision = TP / (TP + FP)   — avoid false alarms
      Recall    = TP / (TP + FN)   — avoid missing true cases
      F1        = 2 * P * R / (P + R)

    Edge cases:
      - If TP + FP == 0 (never predicted this label): precision = 0.0
      - If TP + FN == 0 (label never appears in truth): recall = 0.0
      - If P + R == 0: F1 = 0.0

    TODO: implement.
    """
    # TODO: count TP, FP, FN then compute the three metrics
    raise NotImplementedError("TODO: implement precision_recall_f1()")


def macro_f1(y_true: list[str], y_pred: list[str], labels: list[str]) -> float:
    """
    Macro-averaged F1: average the per-class F1 scores.

    "Macro" means every class counts equally regardless of how many samples it has.
    That's the right choice here since our dataset is balanced.

    TODO:
      1. For each label call precision_recall_f1() and collect the F1.
      2. Return the mean of those F1 values.
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement macro_f1()")


def confusion_matrix(
    y_true: list[str], y_pred: list[str], labels: list[str]
) -> np.ndarray:
    """
    Build a confusion matrix of shape (len(labels), len(labels)).

    matrix[i][j] = number of samples where true label is labels[i]
                   and predicted label is labels[j].

    Diagonal entries are correct predictions.
    Off-diagonal entries are misclassifications.

    TODO:
      1. Create a zero matrix of shape (n, n) where n = len(labels).
      2. Build a label → index mapping.
      3. For each (true, pred) pair increment matrix[true_idx][pred_idx].
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement confusion_matrix()")


def print_confusion_matrix(matrix: np.ndarray, labels: list[str]) -> None:
    """Pretty-print a confusion matrix with row/column headers."""
    short = [l[:4] for l in labels]
    header = "      " + "  ".join(f"{s:>4}" for s in short)
    print(header)
    for i, label in enumerate(labels):
        row = "  ".join(f"{int(matrix[i][j]):>4}" for j in range(len(labels)))
        print(f"  {label[:4]:>4}  {row}")


def print_metrics_table(
    y_true: list[str], y_pred: list[str], labels: list[str], title: str
) -> float:
    """Print a per-class metrics table and return macro F1."""
    print(f"\n{title}")
    print(f"  {'Label':<12} {'Prec':>6} {'Rec':>6} {'F1':>6}  {'Support':>7}")
    print("  " + "-" * 50)
    for label in labels:
        p, r, f = precision_recall_f1(y_true, y_pred, label)
        support = sum(1 for t in y_true if t == label)
        print(f"  {label:<12} {p:>6.2%} {r:>6.2%} {f:>6.2%}  {support:>7}")

    acc = accuracy(y_true, y_pred)
    mf1 = macro_f1(y_true, y_pred, labels)
    print("  " + "-" * 50)
    print(f"  {'accuracy':<12} {acc:>6.2%}")
    print(f"  {'macro F1':<12} {mf1:>6.2%}")
    return mf1


# ---------------------------------------------------------------------------
# Rebuild the embedding classifier on the standard split
# ---------------------------------------------------------------------------


def run_embedding_classifier(provider) -> tuple[list[str], list[str]]:
    """
    Re-run the embedding pipeline from Task 2 on the full dataset,
    using the same 80/20 stratified split (seed=42).

    Returns (y_test, y_pred) for the test set.

    TODO:
      1. Load data from DATA_PATH.
      2. Embed all texts in batches (reuse the pattern from Task 2).
      3. Do a stratified 80/20 split (seed=42).
      4. Train a LogisticRegression on the train split.
      5. Predict on the test split.
      6. Return (y_test, predictions).

    You may import from sklearn here.
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement run_embedding_classifier()")


# ---------------------------------------------------------------------------
# Run the LLM classifier on the same test set
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = [
    ("NASA launched a new space telescope to study distant galaxies.", "science"),
    ("The central bank cut interest rates amid recession fears.", "business"),
    ("The striker scored a hat-trick in the cup final.", "sports"),
    ("Eating more fibre reduces cholesterol and improves gut health.", "health"),
    ("The new legislation restricts campaign finance donations.", "politics"),
    ("Engineers demonstrated a chip that runs on ambient light alone.", "technology"),
]


def parse_label(raw: str, labels: list[str]) -> str | None:
    text = raw.lower().strip()
    for label in labels:
        if label in text:
            return label
    return None


def llm_classify(text: str, provider, labels: list[str]) -> str | None:
    """
    Few-shot classify a single text.

    TODO: build a few-shot prompt (same approach as Task 1) and call provider.chat().
    """
    # TODO: implement
    raise NotImplementedError("TODO: implement llm_classify()")


def run_llm_classifier(
    texts: list[str], provider, labels: list[str]
) -> list[str | None]:
    """Classify all texts using the LLM. Returns predictions (may contain None)."""
    preds: list[str | None] = []
    for i, text in enumerate(texts):
        pred = llm_classify(text, provider, labels)
        preds.append(pred)
        print(f"  LLM classified {i + 1}/{len(texts)}: {pred}")
    return preds


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name}")

    # ── Step 1: embedding classifier ─────────────────────────────────────
    print("\n[1/3] Running embedding + LogisticRegression classifier...")
    y_test, emb_preds = run_embedding_classifier(provider)
    emb_f1 = print_metrics_table(y_test, emb_preds, LABELS_LIST, "Embedding + LR:")

    print("\n  Confusion matrix (Embedding + LR):")
    cm = confusion_matrix(y_test, emb_preds, LABELS_LIST)
    print_confusion_matrix(cm, LABELS_LIST)

    # ── Step 2: LLM classifier on the same test set ───────────────────────
    print(f"\n[2/3] Running LLM few-shot classifier on {len(y_test)} test samples...")
    print("  (This makes one API call per sample — may be slow/costly)\n")
    # Load the test texts (we need them to call the LLM)
    with open(DATA_PATH) as f:
        data = json.load(f)

    # We need the SAME test split — reproduce it deterministically
    from sklearn.model_selection import train_test_split

    all_texts = [d["text"] for d in data]
    all_labels = [d["label"] for d in data]
    _, test_texts, _, _ = train_test_split(
        all_texts, all_labels, test_size=0.2, random_state=42, stratify=all_labels
    )

    llm_raw_preds = run_llm_classifier(test_texts, provider, LABELS_LIST)

    # Replace None with a fallback label so metrics still work
    llm_preds = [p if p is not None else "__unknown__" for p in llm_raw_preds]
    none_count = sum(1 for p in llm_raw_preds if p is None)
    if none_count:
        print(f"\n  Warning: {none_count} LLM response(s) could not be parsed.")

    llm_f1 = print_metrics_table(y_test, llm_preds, LABELS_LIST, "LLM few-shot:")

    print("\n  Confusion matrix (LLM few-shot):")
    cm_llm = confusion_matrix(y_test, llm_preds, LABELS_LIST)
    print_confusion_matrix(cm_llm, LABELS_LIST)

    # ── Step 3: comparison ────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("COMPARISON — macro F1 on the same test set")
    print("=" * 55)
    print(f"  Embedding + LogisticRegression : {emb_f1:.2%}")
    print(f"  LLM few-shot                   : {llm_f1:.2%}")
    print()
    print("  Which wins? What's the cost trade-off?")
    print("  LLM: no training data needed, but slow and costly per call.")
    print("  Embedding + LR: needs labelled data, but sub-millisecond inference.")


if __name__ == "__main__":
    main()
