"""
Task 1 🟡 — Bayes' theorem and a naive Bayes spam classifier.

What you'll learn:
  - Bayes' theorem as a machine for inverting conditional probabilities
  - The base-rate fallacy: why a "95% accurate" test on a rare disease is
    usually wrong when it says "positive" (the classic interview trap)
  - Multinomial naive Bayes: turning Bayes' rule + a "words are independent
    given the class" assumption into a working text classifier
  - Laplace (add-one) smoothing and why you must work in log space

The math (README derives each step):

  Bayes:      P(H | E) = P(E | H) · P(H) / P(E)

  Medical test (H = disease, E = positive test):
    P(D | +) = prior·sens / ( prior·sens + (1 − prior)·(1 − spec) )
    with prior = P(D), sens = P(+ | D), spec = P(− | ¬D).

  Naive Bayes (class c, document w₁…wₙ):
    log P(c | doc) ∝ log P(c) + Σ_i log P(w_i | c)
    P(w | c) = (count(w, c) + 1) / (total_tokens(c) + V)     ← Laplace smoothing

You implement bayes_posterior, fit_naive_bayes, and predict_log_posterior.
The synthetic spam/ham corpus, the train/test split, argmax prediction, and
the report are provided and runnable.

How to run:
  uv run python modules/01f-stats-foundations/py/01_bayes_naive_bayes.py
"""

from __future__ import annotations

import numpy as np

SEED = 42

# The famous interview numbers: 1% prevalence, 95% sensitivity, 95% specificity.
PRIOR = 0.01
SENSITIVITY = 0.95
SPECIFICITY = 0.95
# Analytic answer, worked by hand: 0.0095 / (0.0095 + 0.0495) = 0.16101...
ANALYTIC_POSTERIOR = 0.16101694915254236


# ---------------------------------------------------------------------------
# Synthetic spam/ham corpus  (provided — do not edit)
# ---------------------------------------------------------------------------

VOCAB = [
    "free",
    "win",
    "cash",
    "offer",
    "click",
    "prize",  # spam-flavoured
    "meeting",
    "report",
    "project",
    "lunch",
    "schedule",
    "review",  # ham-flavoured
]
V = len(VOCAB)

# Class-conditional word distributions the corpus is secretly drawn from.
P_WORD_SPAM = np.array([0.20, 0.15, 0.15, 0.12, 0.12, 0.10, 0.04, 0.03, 0.03, 0.02, 0.02, 0.02])
P_WORD_HAM = np.array([0.02, 0.02, 0.02, 0.03, 0.03, 0.02, 0.18, 0.15, 0.15, 0.12, 0.14, 0.12])

N_SPAM = 35
N_HAM = 45
DOC_LEN = 8
N_TRAIN = 60  # of the 80 docs; the remaining 20 are held out


def make_corpus() -> tuple[list[list[int]], list[int], list[list[int]], list[int]]:
    """
    Generate 80 synthetic docs (each a list of DOC_LEN word indices), shuffle,
    and split into train/test.

    Returns: (train_docs, train_labels, test_docs, test_labels); label 1 = spam.
    """
    rng = np.random.default_rng(SEED)
    docs: list[list[int]] = []
    labels: list[int] = []
    for _ in range(N_SPAM):
        docs.append(list(rng.choice(V, size=DOC_LEN, p=P_WORD_SPAM)))
        labels.append(1)
    for _ in range(N_HAM):
        docs.append(list(rng.choice(V, size=DOC_LEN, p=P_WORD_HAM)))
        labels.append(0)
    order = rng.permutation(len(docs))
    docs = [docs[i] for i in order]
    labels = [labels[i] for i in order]
    return docs[:N_TRAIN], labels[:N_TRAIN], docs[N_TRAIN:], labels[N_TRAIN:]


def doc_to_words(doc: list[int]) -> str:
    """Render a doc's word indices as readable text (for printing)."""
    return " ".join(VOCAB[w] for w in doc)


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def bayes_posterior(prior: float, sensitivity: float, specificity: float) -> float:
    """
    P(disease | positive test), by Bayes' theorem.

    P(D | +) = P(+ | D)·P(D) / P(+)
    where P(+) sums over both ways to test positive:
      a true positive  (has the disease AND the test fires):  prior · sensitivity
      a false positive (healthy AND the test misfires):       (1 − prior) · (1 − specificity)

    TODO: implement.
      - Compute the two paths to a positive test (true-positive mass and
        false-positive mass) as above.
      - Return the true-positive mass divided by their sum, as a float.
    """
    # TODO: implement Bayes' theorem for the medical test
    raise NotImplementedError("TODO: implement bayes_posterior()")


def fit_naive_bayes(docs: list[list[int]], labels: list[int]) -> dict[str, np.ndarray]:
    """
    Fit a multinomial naive Bayes model. Label 1 = spam, 0 = ham.

    Returns a dict:
      "log_prior": shape (2,) — log P(class c) = log(#docs in c / #docs)
      "log_lik":   shape (2, V) — Laplace-smoothed per-word log-likelihoods:
                   log P(w | c) = log( (count(w, c) + 1) / (total_tokens(c) + V) )

    TODO: implement.
      1. Count docs per class → log priors (np.log of the doc fraction).
      2. Count word occurrences per class: a (2, V) count table over every
         token of every doc.
      3. Apply Laplace smoothing (add 1 to every count; add V to each class's
         token total), take np.log, and return the dict with both arrays.
    """
    # TODO: count docs and words per class, smooth, log, return the model dict
    raise NotImplementedError("TODO: implement fit_naive_bayes()")


def predict_log_posterior(model: dict[str, np.ndarray], doc: list[int]) -> np.ndarray:
    """
    Unnormalised log posterior for each class:

      log P(c | doc) ∝ log P(c) + Σ_{w in doc} log P(w | c)

    Returns shape (2,): [log-posterior(ham), log-posterior(spam)].

    TODO: implement.
      - Start from the model's log priors and, for each class, add up the
        model's log-likelihood entries for every token in the doc.
      - Sums of logs — never multiply raw probabilities (they underflow).
    """
    # TODO: log priors + summed per-token log-likelihoods, shape (2,)
    raise NotImplementedError("TODO: implement predict_log_posterior()")


# ---------------------------------------------------------------------------
# Prediction helpers  (provided — use your predict_log_posterior)
# ---------------------------------------------------------------------------


def predict(model: dict[str, np.ndarray], doc: list[int]) -> int:
    """Argmax class prediction."""
    return int(np.argmax(predict_log_posterior(model, doc)))


def posterior_probs(model: dict[str, np.ndarray], doc: list[int]) -> np.ndarray:
    """Normalise the two log posteriors into probabilities (stable softmax)."""
    log_post = predict_log_posterior(model, doc)
    shifted = log_post - log_post.max()
    p = np.exp(shifted)
    return p / p.sum()


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 1 — Bayes' theorem and naive Bayes\n")

    # ── Part A: the medical-test trap ────────────────────────────────────────
    print("[1/2] Part A — Bayes' theorem (the medical-test question)...")
    print(f"  Disease prevalence : {PRIOR:.0%}")
    print(f"  Test sensitivity   : {SENSITIVITY:.0%}   (P(+ | disease))")
    print(f"  Test specificity   : {SPECIFICITY:.0%}   (P(− | healthy))")
    posterior = bayes_posterior(PRIOR, SENSITIVITY, SPECIFICITY)
    print(f"\n  P(disease | positive test) = {posterior:.4f}")
    print(f"  Analytic value             = {ANALYTIC_POSTERIOR:.4f}")
    print("  → A positive result still means you're probably healthy: the 1%")
    print("    base rate is swamped by false positives from the healthy 99%.\n")

    # ── Part B: naive Bayes on the spam/ham corpus ───────────────────────────
    print("[2/2] Part B — multinomial naive Bayes on synthetic spam/ham...")
    train_docs, train_labels, test_docs, test_labels = make_corpus()
    print(f"  Corpus: {len(train_docs)} train docs, {len(test_docs)} test docs, V={V}")
    print(
        f"  Example train doc ({'spam' if train_labels[0] else 'ham'}): "
        f'"{doc_to_words(train_docs[0])}"'
    )

    model = fit_naive_bayes(train_docs, train_labels)
    print(f"  log priors: ham={model['log_prior'][0]:.4f}  spam={model['log_prior'][1]:.4f}")

    preds = [predict(model, doc) for doc in test_docs]
    accuracy = float(np.mean([p == t for p, t in zip(preds, test_labels, strict=True)]))
    n_correct = sum(p == t for p, t in zip(preds, test_labels, strict=True))
    print(f"  Held-out accuracy: {accuracy:.2f}  ({n_correct}/{len(test_docs)})")

    obvious_spam = [0, 1, 2, 3, 0, 4, 5, 1]  # "free win cash offer free click prize win"
    p_spam = float(posterior_probs(model, obvious_spam)[1])
    print(f'  Obvious spam doc "{doc_to_words(obvious_spam)}"')
    print(f"  → P(spam) = {p_spam:.4f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_bayes = abs(posterior - ANALYTIC_POSTERIOR) < 0.005
    ok_acc = accuracy >= 0.9
    ok_spam = p_spam > 0.9
    print(
        f"  [{'x' if ok_bayes else ' '}] medical-test posterior within ±0.005 of "
        f"analytic ({posterior:.4f} vs {ANALYTIC_POSTERIOR:.4f})"
    )
    print(f"  [{'x' if ok_acc else ' '}] held-out spam/ham accuracy ≥ 0.9  (got {accuracy:.2f})")
    print(f"  [{'x' if ok_spam else ' '}] obvious spam doc gets P(spam) > 0.9  (got {p_spam:.4f})")

    if ok_bayes and ok_acc and ok_spam:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
