"""
Task 4 🔴 — DPO (Direct Preference Optimization) from scratch.

What you'll learn:
  - Why the RLHF objective has a CLOSED-FORM optimal policy, and how inverting
    it turns the policy itself into an implicit reward model
  - The DPO loss: Bradley–Terry on implicit rewards β·log(π_θ/π_ref) — no
    reward model, no RL loop, just a classification-style loss
  - The exact gradient of the DPO loss for a tabular softmax policy, verified
    against finite differences

The math (README derives each step):

  RLHF objective:   max_π  E_π[r(y)] − β·KL(π ‖ π_ref)
  Closed-form optimum:      π*(y) ∝ π_ref(y) · exp(r(y)/β)
  Invert for the reward:    r(y) = β·log(π*(y)/π_ref(y)) + const
  Substitute into Bradley–Terry for a pair (y_w chosen, y_l rejected) — the
  const cancels — and you get the DPO loss:

    m = β·[ (log π_θ(y_w) − log π_ref(y_w)) − (log π_θ(y_l) − log π_ref(y_l)) ]
    L = −log σ(m)

  Gradient w.r.t. the tabular logits z (π = softmax(z)):
    dL/dm = −(1 − σ(m))
    ∂log π(y)/∂z_j = 1[j = y] − π(j)          (softmax log-prob gradient)
    chain the two through m. (You may notice the −π(j) terms cancel between
    the y_w and y_l branches — that's real, and the provided finite-difference
    grad check will confirm your formula either way.)

You implement the two core functions (dpo_loss, dpo_grad). The toy world,
the preference sampling, the grad check, the training loop, and the report
are provided and runnable.

How to run:
  uv run python modules/13b-alignment/py/04_dpo.py
"""

from __future__ import annotations

import numpy as np

SEED = 44
P = 4  # prompts
K = 6  # candidate responses per prompt
N_PAIRS = 30  # preference pairs per prompt
BETA = 0.5  # DPO β (implicit-reward temperature)
LR = 0.5
EPOCHS = 500

# True reward of each candidate (what the annotators noisily follow).
TRUE_R = [
    [-1.8, -0.6, 0.2, 0.9, 1.6, -1.1],
    [0.4, -1.5, 1.2, -0.3, 2.0, -0.8],
    [-0.5, 1.8, -1.2, 0.7, -2.0, 1.1],
    [1.4, -0.9, 0.3, -1.6, 0.8, 2.1],
]

# Frozen reference policy logits (slightly non-uniform, as after SFT).
REF_LOGITS = [
    [0.2, -0.1, 0.0, 0.3, -0.2, 0.1],
    [-0.3, 0.1, 0.2, 0.0, -0.1, 0.2],
    [0.1, 0.0, -0.2, 0.2, 0.1, -0.3],
    [0.0, 0.2, -0.1, 0.1, -0.2, 0.3],
]


# ---------------------------------------------------------------------------
# Provided helpers and data generation  (do not edit)
# ---------------------------------------------------------------------------


def log_softmax(logits: np.ndarray) -> np.ndarray:
    """Stable row-wise log-softmax for a (K,) or (P, K) array."""
    z = logits - np.max(logits, axis=-1, keepdims=True)
    return z - np.log(np.sum(np.exp(z), axis=-1, keepdims=True))


def sigmoid(z: float) -> float:
    """σ(z) with the argument clamped to avoid overflow."""
    return 1.0 / (1.0 + np.exp(-np.clip(z, -500.0, 500.0)))


def make_pairs(rng: np.random.Generator) -> list[list[tuple[int, int]]]:
    """
    For each prompt, sample N_PAIRS preference pairs: pick two distinct
    candidates, then choose the winner with Bradley–Terry probability
    σ(r_true(i) − r_true(j)) — noisy labels, like real annotators.

    Returns pairs[p] = list of (y_w, y_l) index tuples.
    """
    pairs: list[list[tuple[int, int]]] = []
    for p in range(P):
        prompt_pairs: list[tuple[int, int]] = []
        for _ in range(N_PAIRS):
            i = int(rng.integers(K))
            j = int(rng.integers(K - 1))
            if j >= i:
                j += 1
            p_i_wins = sigmoid(TRUE_R[p][i] - TRUE_R[p][j])
            if rng.random() < p_i_wins:
                prompt_pairs.append((i, j))
            else:
                prompt_pairs.append((j, i))
        pairs.append(prompt_pairs)
    return pairs


# ---------------------------------------------------------------------------
# Core functions — YOU implement these two
# ---------------------------------------------------------------------------


def dpo_loss(
    logp_w: float, logp_l: float, ref_logp_w: float, ref_logp_l: float, beta: float
) -> float:
    """
    The DPO loss for ONE preference pair, from log-probabilities.

      m = β·[ (logp_w − ref_logp_w) − (logp_l − ref_logp_l) ]   (the margin)
      L = −log σ(m)

    Clip σ(m) to at least 1e-12 before the log. Return L as a float.

    TODO: implement.
      - Assemble the margin m from the four log-probs per the formula.
      - Push it through the provided sigmoid, clip, and return the negative
        log.
    """
    # TODO: margin m from the four log-probs, then −log σ(m)
    raise NotImplementedError("TODO: implement dpo_loss()")


def dpo_grad(
    logits_row: np.ndarray, ref_logp_row: np.ndarray, y_w: int, y_l: int, beta: float
) -> np.ndarray:
    """
    Analytic gradient of the DPO loss w.r.t. ONE prompt's logits (shape (K,)).

    Steps of the derivation you should reproduce:
      π        = softmax(logits_row)      (log_softmax is provided)
      m        = β·[(log π(y_w) − ref_logp(y_w)) − (log π(y_l) − ref_logp(y_l))]
      dL/dm    = −(1 − σ(m))
      ∂log π(y)/∂z_j = 1[j = y] − π(j)
      ∂L/∂z_j  = dL/dm · β · (∂log π(y_w)/∂z_j − ∂log π(y_l)/∂z_j)

    Return the (K,) gradient array. The harness's finite-difference grad
    check will verify it numerically — if the check fails, re-derive.

    TODO: implement.
      - Get the log-probs of the row via log_softmax, compute m and dL/dm.
      - Build the two one-hot-minus-π vectors from the softmax log-prob
        gradient formula, take their difference, and scale by dL/dm·β.
    """
    # TODO: chain dL/dm through the softmax log-prob gradient for both branches
    raise NotImplementedError("TODO: implement dpo_grad()")


# ---------------------------------------------------------------------------
# Grad check  (provided — do not edit)
# ---------------------------------------------------------------------------


def grad_check(
    logits_row: np.ndarray, ref_logp_row: np.ndarray, y_w: int, y_l: int, beta: float
) -> float:
    """
    Compare your analytic dpo_grad against a central finite difference of
    dpo_loss. Returns the max absolute deviation over the K logits.
    """
    analytic = dpo_grad(logits_row, ref_logp_row, y_w, y_l, beta)
    eps = 1e-5
    numeric = np.zeros(K)
    for j in range(K):
        for sign, store in ((+1.0, "hi"), (-1.0, "lo")):
            z = logits_row.copy()
            z[j] += sign * eps
            logp = log_softmax(z)
            val = dpo_loss(
                float(logp[y_w]),
                float(logp[y_l]),
                float(ref_logp_row[y_w]),
                float(ref_logp_row[y_l]),
                beta,
            )
            if store == "hi":
                hi = val
            else:
                lo = val
        numeric[j] = (hi - lo) / (2.0 * eps)
    return float(np.max(np.abs(analytic - numeric)))


# ---------------------------------------------------------------------------
# Training + metrics  (provided — do not edit; uses your two functions)
# ---------------------------------------------------------------------------


def batch_metrics(
    logits: np.ndarray, ref_logp: np.ndarray, pairs: list[list[tuple[int, int]]]
) -> dict[str, float]:
    """Mean DPO loss, P(chosen), P(rejected), implicit margin, and KL."""
    logp = log_softmax(logits)
    pi = np.exp(logp)
    losses, p_w, p_l, margins = [], [], [], []
    for p in range(P):
        for y_w, y_l in pairs[p]:
            losses.append(
                dpo_loss(
                    float(logp[p, y_w]),
                    float(logp[p, y_l]),
                    float(ref_logp[p, y_w]),
                    float(ref_logp[p, y_l]),
                    BETA,
                )
            )
            p_w.append(float(pi[p, y_w]))
            p_l.append(float(pi[p, y_l]))
            margins.append(
                BETA
                * (
                    (float(logp[p, y_w]) - float(ref_logp[p, y_w]))
                    - (float(logp[p, y_l]) - float(ref_logp[p, y_l]))
                )
            )
    kl = float(np.mean(np.sum(pi * (logp - ref_logp), axis=-1)))
    return {
        "loss": float(np.mean(losses)),
        "p_chosen": float(np.mean(p_w)),
        "p_rejected": float(np.mean(p_l)),
        "margin": float(np.mean(margins)),
        "kl": kl,
    }


def main() -> None:
    print("Task 4 — DPO from scratch\n")

    rng = np.random.default_rng(SEED)
    pairs = make_pairs(rng)
    ref_logp = log_softmax(np.array(REF_LOGITS, dtype=float))
    logits = np.array(REF_LOGITS, dtype=float)  # start the policy at π_ref
    print(f"  World: {P} prompts x {K} candidates, {N_PAIRS} preference pairs each")
    print(f"  β = {BETA}, lr = {LR}, epochs = {EPOCHS}\n")

    # ── Grad check ───────────────────────────────────────────────────────────
    print("[1/2] Finite-difference grad check on your dpo_grad...")
    dev = grad_check(np.array([0.5, -0.3, 0.1, 0.8, -0.6, 0.2]), ref_logp[0], 3, 1, BETA)
    print(f"  max |analytic − numeric| = {dev:.2e}")

    # ── Training ─────────────────────────────────────────────────────────────
    print("\n[2/2] Training the policy with DPO (full-batch gradient descent)...")
    print("  epoch |   loss  P(chosen)  P(rejected)  margin     KL")
    history: list[dict[str, float]] = []
    for epoch in range(EPOCHS + 1):
        metrics = batch_metrics(logits, ref_logp, pairs)
        history.append(metrics)
        if epoch in (0, 5, 10, 25, 50, 100, 300, EPOCHS):
            print(
                f"  {epoch:>5} | {metrics['loss']:.4f}    {metrics['p_chosen']:.3f}"
                f"       {metrics['p_rejected']:.3f}     {metrics['margin']:+.3f}  {metrics['kl']:.3f}"
            )
        if epoch == EPOCHS:
            break
        for p in range(P):
            grad = np.zeros(K)
            for y_w, y_l in pairs[p]:
                grad += dpo_grad(logits[p], ref_logp[p], y_w, y_l, BETA)
            logits[p] = logits[p] - LR * grad / len(pairs[p])

    final = history[-1]
    losses = [h["loss"] for h in history]
    first20 = losses[:20]
    monotone = all(first20[i + 1] <= first20[i] + 1e-9 for i in range(len(first20) - 1))
    gap = final["p_chosen"] - final["p_rejected"]
    margin_grew = final["margin"] > history[0]["margin"]

    print(
        f"\n  final: P(chosen) = {final['p_chosen']:.3f}, P(rejected) = {final['p_rejected']:.3f}"
    )
    print(
        f"  implicit reward margin β·Δlog(π/π_ref): {history[0]['margin']:+.3f} → {final['margin']:+.3f}"
    )
    print(f"  KL(π‖π_ref) = {final['kl']:.3f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_grad = dev < 1e-5
    ok_gap = gap > 0.2
    ok_monotone = monotone and margin_grew
    ok_kl = final["kl"] < 1.5
    print(f"  [{'x' if ok_grad else ' '}] grad check passes  (max dev = {dev:.2e} < 1e-5)")
    print(
        f"  [{'x' if ok_gap else ' '}] mean P(chosen) beats P(rejected) by a clear margin "
        f"(gap = {gap:.3f} > 0.2)"
    )
    print(
        f"  [{'x' if ok_monotone else ' '}] DPO loss monotone decreasing (first 20 epochs) "
        f"and implicit margin grew"
    )
    print(f"  [{'x' if ok_kl else ' '}] KL(π‖π_ref) stays below 1.5  (KL = {final['kl']:.3f})")

    if ok_grad and ok_gap and ok_monotone and ok_kl:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
