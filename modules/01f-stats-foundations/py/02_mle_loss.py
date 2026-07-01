"""
Task 2 🟡 — Maximum likelihood, and why your loss functions ARE likelihoods.

What you'll learn:
  - Maximum likelihood estimation (MLE): pick the parameters that make the
    observed data most probable
  - The closed-form MLEs for a Gaussian (μ̂ = sample mean, σ̂² = biased sample
    variance) and a Bernoulli (p̂ = sample mean)
  - The punchline every interviewer loves: minimising MSE ≡ maximising a
    Gaussian likelihood in μ, and minimising binary cross-entropy ≡ maximising
    a Bernoulli likelihood. Your loss functions were MLE all along.

The math (README derives each step):

  Likelihood:      L(θ) = Π_i p(x_i | θ)          (i.i.d. data)
  Log-likelihood:  ℓ(θ) = Σ_i log p(x_i | θ)      (same argmax, no underflow)
  NLL:             minimise −ℓ(θ)  ⇔  maximise ℓ(θ)

  Gaussian per-point NLL:   ½·log(2πσ²) + (x − μ)² / (2σ²)
    ∂/∂μ = 0  →  μ̂ = (1/N) Σ x_i          (the mean!)
    ∂/∂σ² = 0 →  σ̂² = (1/N) Σ (x_i − μ̂)²  (biased MLE variance: divide by N)

  Bernoulli per-point NLL:  −[ x·log p + (1 − x)·log(1 − p) ]   ← literally BCE
    ∂/∂p = 0  →  p̂ = (1/N) Σ x_i           (the fraction of 1s)

You implement gaussian_mle, bernoulli_mle, nll_gaussian, nll_bernoulli.
The data, the grid searches, the MSE/BCE curves, and the report are provided.

How to run:
  uv run python modules/01f-stats-foundations/py/02_mle_loss.py
"""

from __future__ import annotations

import numpy as np

SEED = 11
N = 400
MU_TRUE = 2.5
SIGMA_TRUE = 1.2
P_TRUE = 0.3

MU_GRID_STEP = 0.01
P_GRID_STEP = 0.005


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> tuple[np.ndarray, np.ndarray]:
    """
    Returns:
      x_gauss : (N,) draws from N(MU_TRUE, SIGMA_TRUE²)
      x_bern  : (N,) draws (0/1) from Bernoulli(P_TRUE)
    """
    rng = np.random.default_rng(SEED)
    x_gauss = rng.normal(MU_TRUE, SIGMA_TRUE, size=N)
    x_bern = (rng.random(N) < P_TRUE).astype(np.float64)
    return x_gauss, x_bern


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def gaussian_mle(x: np.ndarray) -> tuple[float, float]:
    """
    Closed-form Gaussian MLE.

    Returns (mu_hat, sigma2_hat) as floats:
      mu_hat     = sample mean
      sigma2_hat = BIASED MLE variance — mean of squared deviations from
                   mu_hat, dividing by N (not N−1; np.var's default ddof=0
                   is exactly this).

    TODO: implement — two one-liner statistics of x.
    """
    # TODO: return (mu_hat, sigma2_hat) — biased variance, divide by N
    raise NotImplementedError("TODO: implement gaussian_mle()")


def bernoulli_mle(x: np.ndarray) -> float:
    """
    Closed-form Bernoulli MLE: p̂ = the fraction of 1s in x.

    TODO: implement — one statistic of x, returned as a float.
    """
    # TODO: return the Bernoulli MLE
    raise NotImplementedError("TODO: implement bernoulli_mle()")


def nll_gaussian(x: np.ndarray, mu: float, sigma: float) -> float:
    """
    Average Gaussian negative log-likelihood of x under N(mu, sigma²):

      NLL(μ, σ) = (1/N) Σ_i [ ½·log(2πσ²) + (x_i − μ)² / (2σ²) ]

    TODO: implement.
      - Compute the per-point NLL per the formula (np.log, np.pi) and return
        its mean as a float.
    """
    # TODO: implement the average Gaussian NLL
    raise NotImplementedError("TODO: implement nll_gaussian()")


def nll_bernoulli(x: np.ndarray, p: float) -> float:
    """
    Average Bernoulli negative log-likelihood of the 0/1 array x under
    Bernoulli(p):

      NLL(p) = −(1/N) Σ_i [ x_i·log(p) + (1 − x_i)·log(1 − p) ]

    (Look closely: this is binary cross-entropy with x as the targets.)

    TODO: implement.
      - Compute the per-point term per the formula and return the negated
        mean as a float. Assume 0 < p < 1 (the grid never touches 0 or 1).
    """
    # TODO: implement the average Bernoulli NLL (a.k.a. BCE)
    raise NotImplementedError("TODO: implement nll_bernoulli()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 2 — Maximum likelihood and the loss-function connection\n")

    x_gauss, x_bern = make_data()
    print(f"  Data: {N} Gaussian draws (true μ={MU_TRUE}, σ={SIGMA_TRUE}),")
    print(f"        {N} Bernoulli draws (true p={P_TRUE})\n")

    # ── Closed-form MLEs ─────────────────────────────────────────────────────
    print("[1/3] Closed-form MLEs...")
    mu_hat, sigma2_hat = gaussian_mle(x_gauss)
    sigma_hat = float(np.sqrt(sigma2_hat))
    p_hat = bernoulli_mle(x_bern)
    print(f"  Gaussian : μ̂ = {mu_hat:.4f}   σ̂² = {sigma2_hat:.4f}  (σ̂ = {sigma_hat:.4f})")
    print(f"  Bernoulli: p̂ = {p_hat:.4f}\n")

    # ── Grid search: does the NLL argmin land on the closed form? ────────────
    print("[2/3] Grid-searching each NLL...")
    mu_grid = np.arange(1.5, 3.5 + 1e-9, MU_GRID_STEP)
    nll_mu = np.array([nll_gaussian(x_gauss, float(m), sigma_hat) for m in mu_grid])
    i_nll_mu = int(np.argmin(nll_mu))
    print(f"  Gaussian NLL over μ-grid [1.5, 3.5] (step {MU_GRID_STEP}):")
    print(f"    argmin μ = {mu_grid[i_nll_mu]:.4f}   (closed-form μ̂ = {mu_hat:.4f})")

    p_grid = np.arange(0.01, 0.99 + 1e-9, P_GRID_STEP)
    nll_p = np.array([nll_bernoulli(x_bern, float(p)) for p in p_grid])
    i_nll_p = int(np.argmin(nll_p))
    print(f"  Bernoulli NLL over p-grid [0.01, 0.99] (step {P_GRID_STEP}):")
    print(f"    argmin p = {p_grid[i_nll_p]:.4f}   (closed-form p̂ = {p_hat:.4f})\n")

    # ── The punchline: MSE and BCE are the same curves ───────────────────────
    print("[3/3] The loss-function connection...")
    # MSE as a function of μ, on the SAME data:
    mse_mu = np.array([float(np.mean((x_gauss - m) ** 2)) for m in mu_grid])
    i_mse = int(np.argmin(mse_mu))
    # BCE as a function of p (targets = the Bernoulli data), on the SAME data:
    bce_p = np.array(
        [float(-np.mean(x_bern * np.log(p) + (1 - x_bern) * np.log(1 - p))) for p in p_grid]
    )
    i_bce = int(np.argmin(bce_p))

    print(
        f"  MSE(μ) argmin      = {mu_grid[i_mse]:.4f}   vs Gaussian-NLL argmin  = {mu_grid[i_nll_mu]:.4f}"
    )
    print(
        f"  BCE(p) argmin      = {p_grid[i_bce]:.4f}   vs Bernoulli-NLL argmin = {p_grid[i_nll_p]:.4f}"
    )
    print("  → Minimising MSE in μ IS maximising a Gaussian likelihood;")
    print("    minimising binary cross-entropy IS maximising a Bernoulli likelihood.")
    print("    (Gaussian NLL = MSE/(2σ²) + const; Bernoulli NLL = BCE, identically.)")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_grid_mu = abs(float(mu_grid[i_nll_mu]) - mu_hat) <= MU_GRID_STEP + 1e-9
    ok_grid_p = abs(float(p_grid[i_nll_p]) - p_hat) <= P_GRID_STEP + 1e-9
    ok_mse = i_mse == i_nll_mu
    ok_bce = i_bce == i_nll_p
    print(
        f"  [{'x' if ok_grid_mu else ' '}] Gaussian NLL grid-argmin within one grid step of closed-form μ̂"
    )
    print(
        f"  [{'x' if ok_grid_p else ' '}] Bernoulli NLL grid-argmin within one grid step of closed-form p̂"
    )
    print(f"  [{'x' if ok_mse else ' '}] MSE argmin == Gaussian-NLL argmin (same grid index)")
    print(f"  [{'x' if ok_bce else ' '}] BCE argmin == Bernoulli-NLL argmin (same grid index)")

    if ok_grid_mu and ok_grid_p and ok_mse and ok_bce:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
