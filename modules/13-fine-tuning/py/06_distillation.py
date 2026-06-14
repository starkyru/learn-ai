"""
Task 6 🟡 — Distillation: teacher LLM labels a dataset, student learns from it.

Knowledge distillation is a technique for making a small, cheap model behave
like a big, expensive one — at least on a narrow task. The key idea:

  1. Teacher phase: use a powerful LLM (the "teacher") to label a dataset.
     Instead of human annotation, we call the big model for each example.
  2. Student phase: train a small, fast classifier on those labels.
     Here we use embeddings + logistic regression / kNN — no GPU needed.
  3. Evaluation: compare the student's accuracy and speed to calling the
     teacher on every query.

This approach is used in production when:
  - LLM inference costs are too high at scale (the student is 100-1000× cheaper).
  - Latency matters (embedding lookup + logistic regression is < 1 ms; LLM is 500-2000 ms).
  - The task is narrow enough that a small model can learn it.

What you'll learn:
  - Using an LLM to generate labels (a form of synthetic annotation)
  - Embedding-based classification (reusing ideas from module 08)
  - Measuring accuracy, cost-per-query, and latency tradeoffs
  - When distillation fails (out-of-distribution inputs, ambiguous labels)

How to run:
  uv run python modules/13-fine-tuning/py/06_distillation.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Dataset: sentiment classification (positive / negative / neutral)
# ---------------------------------------------------------------------------

# Unlabelled examples — the teacher will label these
UNLABELLED_TEXTS: list[str] = [
    "This product exceeded all my expectations — absolutely love it!",
    "Terrible quality, broke after two days. Complete waste of money.",
    "It arrived on time and works as described. Nothing special.",
    "Best purchase I've made this year. Highly recommend!",
    "The instructions were confusing but the product itself is fine.",
    "Awful customer service. Never buying from here again.",
    "Decent value for the price. Does what it says on the tin.",
    "Mind-blowing performance. Changed how I work every day.",
    "Packaging was damaged but the item inside was okay.",
    "Total disappointment. Not at all what was advertised.",
    "Solid product, nothing groundbreaking. Gets the job done.",
    "Returned it immediately. The worst thing I've ever bought.",
    "Pretty good overall. Minor issues but I'm satisfied.",
    "Fantastic! Exceeded expectations in every way possible.",
    "Average product. You get what you pay for, I suppose.",
    "Incredibly frustrating to set up. Manual is incomprehensible.",
    "Works perfectly. Very happy with this purchase.",
    "Not worth the money at all. Save yourself the hassle.",
    "Good enough for what I needed. Would buy again.",
    "Outstanding quality. Five stars without hesitation.",
]

# Hold-out test set with known labels (for evaluating the student)
TEST_SET: list[tuple[str, str]] = [
    ("Amazing product, life-changing!", "positive"),
    ("Complete rubbish, deeply disappointed.", "negative"),
    ("It does the job, nothing more.", "neutral"),
    ("Fantastic value and great quality!", "positive"),
    ("Broke on first use. Terrible.", "negative"),
    ("Acceptable, but not impressive.", "neutral"),
    ("Absolutely love this — worth every penny.", "positive"),
    ("Disappointing and overpriced.", "negative"),
    ("Fine for everyday use.", "neutral"),
    ("The best in its category, no contest.", "positive"),
]

LABELS = ["positive", "negative", "neutral"]


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class LabelledExample:
    text: str
    label: str    # "positive" | "negative" | "neutral"


@dataclass
class StudentClassifier:
    """Embedding-based student classifier."""
    # Stored per-class: list of (embedding, label) training points
    train_embeddings: list[list[float]]
    train_labels: list[str]
    # Method: "knn" (default) or "centroid"
    method: str = "knn"
    k: int = 3


# ---------------------------------------------------------------------------
# Phase 1 — Teacher labelling
# ---------------------------------------------------------------------------


def llm_label(texts: list[str], provider: Any) -> list[str]:
    """
    Use the provider (teacher LLM) to label each text as positive, negative,
    or neutral.

    TODO: implement this function.

    Steps:
      1. For each text, call provider.chat() with:
           system: "You are a sentiment classifier. Reply with exactly one word:
                    positive, negative, or neutral. Nothing else."
           user:   the text to classify
         Use ChatOptions(max_tokens=5, temperature=0) for determinism.
      2. Parse the response: strip whitespace, lowercase.
      3. If the response is not in LABELS, default to "neutral".
      4. Return a list of labels, one per input text.

    Note: in a real distillation pipeline you would batch requests and handle
    rate limits. Here, sequential calls are fine for the small dataset.
    """
    # TODO: implement llm_label
    raise NotImplementedError("TODO: implement llm_label()")


# ---------------------------------------------------------------------------
# Phase 2 — Student training
# ---------------------------------------------------------------------------


def train_student(
    labelled: list[LabelledExample],
    provider: Any,
) -> StudentClassifier:
    """
    Embed all labelled examples and build a kNN-based student classifier.

    TODO: implement this function.

    Steps:
      1. Extract texts and labels from `labelled`.
      2. Embed all texts in one call: result = provider.embed(texts).
      3. Return StudentClassifier(
             train_embeddings=result.vectors,
             train_labels=labels,
             method="knn",
             k=3,
         ).
    """
    # TODO: implement train_student
    raise NotImplementedError("TODO: implement train_student()")


# ---------------------------------------------------------------------------
# Phase 2 continued — Student inference
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity between two vectors."""
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = sum(ai * ai for ai in a) ** 0.5
    norm_b = sum(bi * bi for bi in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def student_predict(text_embedding: list[float], student: StudentClassifier) -> str:
    """
    Predict the label for an already-embedded text using the student classifier.

    TODO: implement this function.

    kNN algorithm:
      1. Compute cosine_similarity(text_embedding, e) for every training embedding e.
      2. Sort by similarity descending.
      3. Take the top-k labels.
      4. Return the most common label among the top-k (tie-break: first in LABELS order).
    """
    # TODO: implement student_predict
    raise NotImplementedError("TODO: implement student_predict()")


# ---------------------------------------------------------------------------
# Phase 3 — Evaluation
# ---------------------------------------------------------------------------


def evaluate(
    test_set: list[tuple[str, str]],
    student: StudentClassifier,
    provider: Any,
) -> dict[str, Any]:
    """
    Compare the student classifier against the teacher LLM on the test set.

    Measures:
      - Student accuracy (fraction correct out of len(test_set))
      - Teacher accuracy (same metric using llm_label)
      - Student latency per query (embed + kNN predict)
      - Teacher latency per query (one LLM chat call)

    TODO: implement this function.

    Steps:
      1. Split test_set into texts and gold_labels.

      2. [Student] Embed all test texts, then call student_predict for each.
         Time the entire embed + predict loop; compute per-query latency.
         Compute accuracy vs gold_labels.

      3. [Teacher] Call llm_label(texts, provider) and time it.
         Compute accuracy vs gold_labels.

      4. Return a dict with keys:
           "student_accuracy", "teacher_accuracy",
           "student_latency_ms", "teacher_latency_ms",
           "student_predictions", "teacher_predictions".
    """
    # TODO: implement evaluate
    raise NotImplementedError("TODO: implement evaluate()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider : {provider.name}  |  Chat: {provider.chat_model}"
          f"  |  Embed: {provider.embed_model}\n")

    # Phase 1: teacher labels the unlabelled training data
    print(f"Phase 1: Teacher labelling {len(UNLABELLED_TEXTS)} examples...")
    t0 = time.perf_counter()
    labels = llm_label(UNLABELLED_TEXTS, provider)
    label_time = time.perf_counter() - t0
    labelled = [LabelledExample(text=t, label=l) for t, l in zip(UNLABELLED_TEXTS, labels)]

    print(f"  Done in {label_time:.1f}s  ({label_time / len(labels) * 1000:.0f} ms/example)")
    label_counts = {lbl: labels.count(lbl) for lbl in LABELS}
    print(f"  Label distribution: {label_counts}")
    print()

    # Phase 2: train student on teacher-labelled data
    print(f"Phase 2: Training student classifier on {len(labelled)} labelled examples...")
    student = train_student(labelled, provider)
    print(f"  Student trained: {len(student.train_embeddings)} training points, "
          f"method={student.method}, k={student.k}")
    print()

    # Phase 3: evaluate both on the held-out test set
    print(f"Phase 3: Evaluating student vs teacher on {len(TEST_SET)} test examples...\n")
    results = evaluate(TEST_SET, student, provider)

    print(f"{'Metric':<30} {'Student':>12} {'Teacher':>12}")
    print("-" * 56)
    print(f"{'Accuracy':<30} {results['student_accuracy']:>11.1%} {results['teacher_accuracy']:>11.1%}")
    print(f"{'Latency per query (ms)':<30} {results['student_latency_ms']:>11.1f} {results['teacher_latency_ms']:>11.1f}")
    speedup = results["teacher_latency_ms"] / max(results["student_latency_ms"], 0.01)
    print(f"\nStudent is {speedup:.0f}× faster per query than the teacher.")
    print()

    # Show per-example breakdown
    print("Per-example breakdown (first 5):")
    texts = [t for t, _ in TEST_SET]
    gold = [g for _, g in TEST_SET]
    for i in range(min(5, len(TEST_SET))):
        s_pred = results["student_predictions"][i]
        t_pred = results["teacher_predictions"][i]
        s_ok = "✓" if s_pred == gold[i] else "✗"
        t_ok = "✓" if t_pred == gold[i] else "✗"
        print(f"  [{i+1}] text={texts[i][:40]!r}")
        print(f"       gold={gold[i]:<10}  student={s_pred} {s_ok}  teacher={t_pred} {t_ok}")

    print(
        "\nKey insights:"
        "\n  1. The teacher labels training data once — at annotation time, not inference time."
        "\n  2. The student (embed + kNN) is orders of magnitude faster per query."
        "\n  3. Accuracy gap reveals how much the student 'distills' from the teacher."
        "\n  4. For narrow tasks (sentiment), the student often matches teacher accuracy."
        "\n  5. Distillation fails when inputs are far from the training distribution."
    )


if __name__ == "__main__":
    main()
