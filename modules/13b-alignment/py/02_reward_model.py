"""
Task 2 🟡 — Reward model from preferences (Bradley–Terry).

What you'll learn:
  - The Bradley–Terry model: turning "chosen ≻ rejected" pairs into a
    probabilistic training signal
  - The reward-modeling loss used by InstructGPT: −log σ(r_chosen − r_rejected)
  - Why maximum likelihood on noisy preferences recovers the hidden reward
    (direction) — the exact recipe behind every RLHF reward model

The math (README derives each step):

  Responses are feature vectors x ∈ ℝ^D. A hidden true reward scores them:
      r*(x) = w* · x
  Preference data: for a pair (x_a, x_b), the label "a chosen" is sampled with
      P(a ≻ b) = σ(r*(x_a) − r*(x_b))          (Bradley–Terry)
  We fit a linear reward model  r_θ(x) = θ · x  by minimising, over pairs,
      L(θ) = −mean log σ(Δ) ,   Δ = r_θ(x_chosen) − r_θ(x_rejected)
  Gradient (derive it: d/dΔ [−log σ(Δ)] = −(1 − σ(Δ)), then chain to θ):
      ∂L/∂θ = −mean (1 − σ(Δ)) · (x_chosen − x_rejected)

You implement the three core functions (bt_prob, bt_loss, bt_grad_step).
Data generation, the train/held-out split, the training loop, and the
evaluation report are provided and runnable.

How to run:
  uv run python modules/13b-alignment/py/02_reward_model.py
"""

from __future__ import annotations

import numpy as np

SEED = 21
D = 6  # response feature dimension
N_TRAIN = 400  # preference pairs for training
N_TEST = 200  # held-out preference pairs
LR = 0.2
EPOCHS = 200

# The hidden "true" reward direction the annotators (noisily) follow.
W_TRUE = np.array([3.0, -4.0, 2.0, 1.2, -2.4, 1.6])


# ---------------------------------------------------------------------------
# Preference-pair generation  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_pairs(n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate n preference pairs. Each pair draws two random "responses"
    x_a, x_b ~ N(0, I_D); the winner is sampled from the Bradley–Terry
    probability under the TRUE reward — so labels contain realistic noise
    (the better response usually wins, not always).

    Returns (X_chosen, X_rejected), each of shape (n, D).
    """
    X_a = rng.normal(0.0, 1.0, size=(n, D))
    X_b = rng.normal(0.0, 1.0, size=(n, D))
    p_a = 1.0 / (1.0 + np.exp(-(X_a @ W_TRUE - X_b @ W_TRUE)))
    a_wins = rng.random(n) < p_a
    X_chosen = np.where(a_wins[:, None], X_a, X_b)
    X_rejected = np.where(a_wins[:, None], X_b, X_a)
    return X_chosen, X_rejected


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def bt_prob(r_chosen: np.ndarray, r_rejected: np.ndarray) -> np.ndarray:
    """
    Bradley–Terry probability that "chosen" beats "rejected", element-wise:

        P(chosen ≻ rejected) = σ(r_chosen − r_rejected)

    Both inputs are (n,) arrays of scalar rewards; return an (n,) array.
    Clamp the exponent argument to [-500, 500] to avoid overflow.

    TODO: implement.
      - Form the reward gap, clamp it with np.clip, and push it through the
        sigmoid  σ(z) = 1 / (1 + e^{-z}).
    """
    # TODO: sigmoid of the clipped reward gap
    raise NotImplementedError("TODO: implement bt_prob()")


def bt_loss(r_chosen: np.ndarray, r_rejected: np.ndarray) -> float:
    """
    The reward-modeling loss (negative log-likelihood of the preferences):

        L = −mean log σ(r_chosen − r_rejected)

    Clip the probability to [1e-12, 1 − 1e-12] before the log.

    TODO: implement.
      - Get the pairwise probabilities from bt_prob, clip them with np.clip,
        and return the mean negative log as a float.
    """
    # TODO: mean negative log of the clipped bt_prob values
    raise NotImplementedError("TODO: implement bt_loss()")


def bt_grad_step(
    theta: np.ndarray, X_chosen: np.ndarray, X_rejected: np.ndarray, lr: float
) -> np.ndarray:
    """
    One full-batch gradient-descent step on the Bradley–Terry loss for the
    linear reward model r_θ(x) = θ·x.

      Δ_i    = θ·x_chosen_i − θ·x_rejected_i                (shape (n,))
      ∂L/∂θ  = −(1/n) Σ_i (1 − σ(Δ_i)) · (x_chosen_i − x_rejected_i)
      update:  θ_new = θ − lr · ∂L/∂θ

    Return the UPDATED θ as a new (D,) array (do not mutate the input — the
    training loop reassigns theta = bt_grad_step(...)).

    TODO: implement.
      - Compute both reward arrays with matrix-vector products, then σ(Δ) via
        bt_prob.
      - Weight each pair's feature difference (x_chosen − x_rejected) by its
        (1 − σ(Δ_i)) factor — broadcasting a (n, 1) column over (n, D) works —
        and average over pairs with the leading minus sign.
      - Return the stepped weights.
    """
    # TODO: build the Bradley–Terry gradient and take one descent step
    raise NotImplementedError("TODO: implement bt_grad_step()")


# ---------------------------------------------------------------------------
# Evaluation helpers  (provided — use your bt_* functions)
# ---------------------------------------------------------------------------


def ranking_accuracy(theta: np.ndarray, Xc: np.ndarray, Xr: np.ndarray) -> float:
    """Fraction of held-out pairs where the model ranks chosen above rejected."""
    return float(np.mean(Xc @ theta > Xr @ theta))


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 2 — Reward model from preferences (Bradley–Terry)\n")

    rng = np.random.default_rng(SEED)
    Xc_train, Xr_train = make_pairs(N_TRAIN, rng)
    Xc_test, Xr_test = make_pairs(N_TEST, rng)
    print(f"  Pairs: {N_TRAIN} train / {N_TEST} held-out, D={D}")
    print(f"  Hidden true reward w* = {W_TRUE}\n")

    print("[1/2] Training the linear reward model on preference pairs...")
    theta = np.zeros(D)
    loss_history: list[float] = []
    for _epoch in range(EPOCHS):
        loss_history.append(bt_loss(Xc_train @ theta, Xr_train @ theta))
        theta = bt_grad_step(theta, Xc_train, Xr_train, LR)

    for e in (1, 5, 20, 60, EPOCHS):
        print(f"  epoch {e:>4}: BT loss = {loss_history[e - 1]:.4f}")

    first30 = loss_history[:30]
    monotonic = all(first30[i + 1] <= first30[i] + 1e-9 for i in range(len(first30) - 1))

    print("\n[2/2] Evaluating the learned reward model...")
    acc = ranking_accuracy(theta, Xc_test, Xr_test)
    cos = cosine(theta, W_TRUE)
    print(f"  learned θ = {np.round(theta, 3)}")
    print(f"  held-out ranking accuracy = {acc:.3f}")
    print(f"  cosine(θ, w*)             = {cos:.4f}")
    print(f"  loss monotone (first 30)  = {monotonic}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_acc = acc >= 0.9
    ok_cos = cos >= 0.9
    ok_monotone = monotonic
    print(f"  [{'x' if ok_acc else ' '}] held-out ranking accuracy >= 0.9  (acc = {acc:.3f})")
    print(f"  [{'x' if ok_cos else ' '}] cosine(θ, w*) >= 0.9  (cos = {cos:.4f})")
    print(f"  [{'x' if ok_monotone else ' '}] BT loss decreases monotonically over first 30 epochs")

    if ok_acc and ok_cos and ok_monotone:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
