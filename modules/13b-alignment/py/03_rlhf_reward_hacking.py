"""
Task 3 🔴 — RLHF with REINFORCE, and its failure mode: reward hacking.

What you'll learn:
  - The RLHF objective:  maximize  E_π[r(x)] − β·KL(π ‖ π_ref)
  - The policy-gradient (REINFORCE) update for a tabular softmax policy,
    with a baseline to cut variance
  - Goodhart's law in action: optimizing an IMPERFECT reward model makes the
    true reward rise at first... then collapse (reward hacking /
    overoptimization)
  - Why the KL penalty is the leash that prevents the collapse

The math (README derives each step):

  Policy: per prompt, logits z ∈ ℝ^K over K candidate responses,
      π_θ(k) = softmax(z)_k = e^{z_k} / Σ_j e^{z_j}
  Expected reward:  J(θ) = Σ_k π(k)·R(k).  Its exact gradient w.r.t. z_j is
      ∂J/∂z_j = π(j)·(R(j) − b) ,   baseline b = Σ_k π(k)·R(k)
  (this is REINFORCE in expectation — we use the exact form over the small
  candidate set to stay deterministic). Gradient ASCENT: z ← z + lr·∂J/∂z.

  KL divergence:  KL(π ‖ π_ref) = Σ_k π(k) · log(π(k) / π_ref(k))

  The KL-regularized objective  J_KL = E_π[R] − β·KL(π‖π_ref)  has exactly the
  same gradient as plain REINFORCE with the SHAPED reward
      R'(k) = R(k) − β·log(π(k)/π_ref(k))
  (the harness applies this shaping and calls your reinforce_step).

  The reward model here is IMPERFECT (pre-baked from few noisy pairs, the
  Task 2 recipe): θ_RM = w* + error·û, with û ⊥ w*. It scores ordinary
  responses correctly — but each prompt has one "exploit" response pointing
  along û that the RM overrates even though its TRUE reward is terrible.
  Optimize the proxy hard enough and the policy finds it.

You implement the three core functions (softmax, reinforce_step,
kl_divergence). The toy world, the imperfect RM, both optimization runs,
and the side-by-side report are provided and runnable.

How to run:
  uv run python modules/13b-alignment/py/03_rlhf_reward_hacking.py
"""

from __future__ import annotations

import numpy as np

SEED = 33
D = 6  # response feature dimension
P = 4  # prompts
K = 6  # candidate responses per prompt (index K-1 is the exploit)
STEPS = 600
LR = 0.5
BETA = 3.5  # KL coefficient for run (b)

# Hidden TRUE reward direction (what humans actually want).
W_STAR = np.array([1.0, -0.6, 0.8, 0.4, -0.5, 0.3])

# The reward model's spurious direction (raw, orthogonalised in build_world).
U_RAW = np.array([0.5, 1.0, -0.3, 0.8, 0.9, -0.2])
RM_ERROR_SCALE = 1.0  # how much θ_RM leans on the spurious direction û
EXPLOIT_TRUE_COST = 1.5  # exploit's true reward is −this·‖w*‖
EXPLOIT_PROXY_MARGIN = 0.3  # proxy edge of the exploit over the best normal

# True reward of each prompt's K-1 NORMAL candidates (provided "dataset":
# every prompt has a couple of awful drafts, mediocre ones, and good ones).
TRUE_NORMALS = [
    [-4.0, -2.5, 0.5, 1.8, 2.3],
    [-3.5, -2.8, 0.0, 1.5, 2.6],
    [-4.2, -1.5, 0.8, 2.0, 2.4],
    [-3.8, -2.2, 0.3, 1.7, 2.2],
]


# ---------------------------------------------------------------------------
# Toy world: candidates, true reward, imperfect reward model
# (provided — do not edit)
# ---------------------------------------------------------------------------


def build_world() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build P prompts × K candidate "responses" (feature vectors) plus the
    imperfect reward model θ_RM, and score everything.

    Geometry (ŵ = w*/‖w*‖, û ⊥ ŵ unit):
      - θ_RM = w* + RM_ERROR_SCALE·û — right about the ŵ direction, but also
        rewards the spurious direction û that the true reward ignores.
      - Normal candidate with target true reward t:  x = (t/‖w*‖)·ŵ + noise,
        where the noise is orthogonal to BOTH ŵ and û — so true and proxy
        rewards agree exactly on normal responses (a *plausible-looking* RM).
      - Exploit candidate:  x = b·û − c·ŵ  with c = EXPLOIT_TRUE_COST and b
        solved so its proxy beats the prompt's best normal by
        EXPLOIT_PROXY_MARGIN, while its true reward is −c·‖w*‖ (the worst).

    Returns (X, true_r, proxy_r):
      X       : (P, K, D) candidate features
      true_r  : (P, K)    true rewards   w*·x
      proxy_r : (P, K)    RM rewards     θ_RM·x
    """
    rng = np.random.default_rng(SEED)
    w_norm = float(np.linalg.norm(W_STAR))
    w_hat = W_STAR / w_norm
    u = U_RAW - (U_RAW @ w_hat) * w_hat  # orthogonalise against w*
    u_hat = u / np.linalg.norm(u)
    theta_rm = W_STAR + RM_ERROR_SCALE * u_hat

    X = np.zeros((P, K, D))
    for p in range(P):
        for k in range(K - 1):
            noise = 0.5 * rng.normal(0.0, 1.0, size=D)
            noise -= (noise @ w_hat) * w_hat  # keep true reward exact
            noise -= (noise @ u_hat) * u_hat  # keep proxy reward exact
            X[p, k] = (TRUE_NORMALS[p][k] / w_norm) * w_hat + noise
        max_normal_proxy = float(np.max(X[p, : K - 1] @ theta_rm))
        # Solve θ_RM·(b·û − c·ŵ) = max_normal_proxy + margin for b, using
        # θ_RM·û = RM_ERROR_SCALE and θ_RM·ŵ = ‖w*‖ (since û ⊥ ŵ).
        c = EXPLOIT_TRUE_COST
        b = (max_normal_proxy + EXPLOIT_PROXY_MARGIN + c * w_norm) / RM_ERROR_SCALE
        X[p, K - 1] = b * u_hat - c * w_hat

    true_r = X @ W_STAR
    proxy_r = X @ theta_rm
    return X, true_r, proxy_r


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def softmax(logits: np.ndarray) -> np.ndarray:
    """
    Row-wise stable softmax. `logits` is (P, K); return (P, K) with each row
    summing to 1.

    Numerical stability: subtract each row's max before exponentiating
    (softmax is shift-invariant, so the result is unchanged).

    TODO: implement.
      - Shift each row by its max (keepdims=True helps broadcasting).
      - Exponentiate and divide each row by its sum.
    """
    # TODO: shift by row max, exponentiate, normalise per row
    raise NotImplementedError("TODO: implement softmax()")


def reinforce_step(logits: np.ndarray, rewards: np.ndarray, lr: float) -> np.ndarray:
    """
    One exact policy-gradient ASCENT step on E_π[R], per prompt.

      π = softmax(logits)                        row-wise, shape (P, K)
      baseline b_p = Σ_k π_p(k)·R_p(k)           expected reward per prompt
      gradient ∂J/∂z_{p,j} = π_p(j)·(R_p(j) − b_p)
      update:  z_new = z + lr·∂J/∂z              (ascent — we maximize J)

    The baseline is what makes this "REINFORCE with a baseline": it doesn't
    change the expected gradient but centres the reward signal.

    Return the UPDATED logits as a new (P, K) array (do not mutate the input —
    the loop reassigns logits = reinforce_step(...)).

    TODO: implement.
      - Get π via your softmax.
      - Compute each prompt's baseline as the π-weighted mean of its rewards
        (a (P, 1) column, so it broadcasts).
      - Assemble the gradient per the formula and return the stepped logits
        (note the PLUS sign — gradient ascent).
    """
    # TODO: policy gradient with a baseline, then one ASCENT step
    raise NotImplementedError("TODO: implement reinforce_step()")


def kl_divergence(pi: np.ndarray, pi_ref: np.ndarray) -> float:
    """
    Mean KL divergence over prompts:

        KL(π ‖ π_ref) = Σ_k π(k) · log(π(k) / π_ref(k))

    `pi` and `pi_ref` are (P, K); compute the KL of each row, then return the
    mean over the P prompts as a float. Clip both distributions to at least
    1e-12 before the log so 0·log(0) doesn't produce NaN.

    TODO: implement.
      - Clip, take the log-ratio, weight by π, sum over k, mean over prompts.
    """
    # TODO: Σ π·log(π/π_ref) per row, then mean over prompts
    raise NotImplementedError("TODO: implement kl_divergence()")


# ---------------------------------------------------------------------------
# Optimization runs  (provided — do not edit; uses your three functions)
# ---------------------------------------------------------------------------


def optimize(
    proxy_r: np.ndarray,
    true_r: np.ndarray,
    pi_ref: np.ndarray,
    beta: float,
    steps: int,
    lr: float,
) -> dict[str, list[float]]:
    """
    Run `steps` of policy-gradient ascent on the proxy reward, optionally
    KL-regularized (beta > 0), starting from the reference policy (logits 0).

    The KL penalty enters through reward shaping:
        R'(k) = proxy(k) − β·log(π(k)/π_ref(k))
    which gives exactly the gradient of  E_π[proxy] − β·KL(π‖π_ref).

    Tracks expected true reward, expected proxy reward, KL, and the mean
    probability of the exploit response over time (steps+1 entries each).
    """
    logits = np.zeros((P, K))
    traj: dict[str, list[float]] = {"true": [], "proxy": [], "kl": [], "p_exploit": []}

    def record() -> np.ndarray:
        pi = softmax(logits)
        traj["true"].append(float(np.mean(np.sum(pi * true_r, axis=-1))))
        traj["proxy"].append(float(np.mean(np.sum(pi * proxy_r, axis=-1))))
        traj["kl"].append(kl_divergence(pi, pi_ref))
        traj["p_exploit"].append(float(np.mean(pi[:, K - 1])))
        return pi

    for _ in range(steps):
        pi = record()
        shaped = proxy_r - beta * np.log(np.clip(pi, 1e-12, None) / pi_ref)
        logits = reinforce_step(logits, shaped, lr)
    record()
    return traj


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 3 — RLHF (REINFORCE) and reward hacking\n")

    X, true_r, proxy_r = build_world()
    pi_ref = np.full((P, K), 1.0 / K)  # uniform reference policy
    print(f"  World: {P} prompts x {K} candidates (feature dim {D})")
    print(f"  Exploit candidate (index {K - 1}) per prompt:")
    for p in range(P):
        print(
            f"    prompt {p}: proxy {proxy_r[p, K - 1]:+.2f} (best normal "
            f"{np.max(proxy_r[p, : K - 1]):+.2f})   true {true_r[p, K - 1]:+.2f} "
            f"(best normal {np.max(true_r[p, : K - 1]):+.2f})"
        )

    print("\n[1/2] Run (a): maximize proxy reward, NO KL penalty...")
    a = optimize(proxy_r, true_r, pi_ref, beta=0.0, steps=STEPS, lr=LR)
    print(f"[2/2] Run (b): maximize proxy − β·KL(π‖π_ref),  β = {BETA} ...")
    b = optimize(proxy_r, true_r, pi_ref, beta=BETA, steps=STEPS, lr=LR)

    print("\n  step | (a) proxy   true  P(exploit) | (b) proxy   true  P(exploit)   KL")
    for t in (0, 5, 10, 25, 50, 100, 300, STEPS):
        print(
            f"  {t:>4} |   {a['proxy'][t]:+.2f}  {a['true'][t]:+.2f}     {a['p_exploit'][t]:.3f}"
            f"   |   {b['proxy'][t]:+.2f}  {b['true'][t]:+.2f}     {b['p_exploit'][t]:.3f}"
            f"    {b['kl'][t]:.3f}"
        )

    a_peak_true = max(a["true"])
    a_peak_step = int(np.argmax(a["true"]))
    b_peak_true = max(b["true"])
    print(
        f"\n  (a) true reward: start {a['true'][0]:+.3f} → peak {a_peak_true:+.3f} "
        f"(step {a_peak_step}) → final {a['true'][-1]:+.3f}   ← Goodhart collapse"
    )
    print(f"  (a) final P(exploit) = {a['p_exploit'][-1]:.3f}")
    print(
        f"  (b) true reward: peak {b_peak_true:+.3f} → final {b['true'][-1]:+.3f}   "
        f"(KL = {b['kl'][-1]:.3f}, P(exploit) = {b['p_exploit'][-1]:.3f})"
    )

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_a_hack = a["true"][-1] < a_peak_true - 0.5 and a["proxy"][-1] >= max(a["proxy"]) - 1e-6
    ok_a_exploit = a["p_exploit"][-1] > 0.9
    ok_b_true = b["true"][-1] >= 0.9 * b_peak_true
    ok_b_kl = b["kl"][-1] < 1.0
    ok_b_exploit = b["p_exploit"][-1] < 0.3
    print(
        f"  [{'x' if ok_a_hack else ' '}] (a) proxy at max but true reward collapsed below its peak "
        f"({a['true'][-1]:+.2f} < {a_peak_true:+.2f} − 0.5)"
    )
    print(
        f"  [{'x' if ok_a_exploit else ' '}] (a) policy concentrated on the exploit: "
        f"P(exploit) = {a['p_exploit'][-1]:.3f} > 0.9"
    )
    print(
        f"  [{'x' if ok_b_true else ' '}] (b) KL leash keeps true reward ≥ 0.9× its peak "
        f"({b['true'][-1]:+.2f} vs peak {b_peak_true:+.2f})"
    )
    print(
        f"  [{'x' if ok_b_kl else ' '}] (b) KL(π‖π_ref) stays below 1.0  (KL = {b['kl'][-1]:.3f})"
    )
    print(
        f"  [{'x' if ok_b_exploit else ' '}] (b) exploit stays rare: "
        f"P(exploit) = {b['p_exploit'][-1]:.3f} < 0.3"
    )

    if ok_a_hack and ok_a_exploit and ok_b_true and ok_b_kl and ok_b_exploit:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
