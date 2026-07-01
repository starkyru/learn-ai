"""
Task 4 🔴 — PCA (Principal Component Analysis) from scratch.

What you'll learn:
  - PCA as finding the orthogonal directions of maximum variance — which are
    exactly the eigenvectors of the covariance matrix
  - Explained variance ratio: how many dimensions the data REALLY uses
  - Projection and reconstruction: lossy compression whose error is the
    variance you threw away
  - Why this matters later in the course: visualising embeddings (module 04)
    and shrinking vector-store footprints are PCA jobs

The math (README derives each step):

  Center:        X_c = X − mean(X)                       (column-wise mean)
  Covariance:    C   = (1/(N−1)) · X_cᵀ X_c              (D×D, symmetric)
  Eigen:         C v_j = λ_j v_j — eigenvectors v_j are the principal
                 components; eigenvalue λ_j is the variance along v_j.
  Sort λ descending; stack the v_j as COLUMNS of `components` (D×D).
  EVR:           evr_j = λ_j / Σ λ
  Project:       Z = X_c @ components[:, :k]              (N×k scores)
  Reconstruct:   X̂ = Z @ components[:, :k]ᵀ + mean        (back to N×D)

🔴 rule: no sklearn / no library PCA. You may (must) call np.linalg.eigh for
the eigendecomposition of the symmetric covariance matrix — sorting its
eigenpairs DESCENDING is part of your job (eigh returns ascending order).

You implement center, covariance_matrix, pca_fit, project, reconstruct,
explained_variance_ratio. The 10-D dataset (secretly ~2-D) and the harness
are provided.

How to run:
  uv run python modules/01f-stats-foundations/py/04_pca.py
"""

from __future__ import annotations

import numpy as np

SEED = 3
N = 300
D = 10
LATENT = 2  # the data secretly lives near a 2-D plane
NOISE = 0.05


# ---------------------------------------------------------------------------
# Synthetic data  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_data() -> np.ndarray:
    """
    10-D data that secretly lives near a 2-D plane:
      Z_latent (N×2) standard normal  →  X = Z_latent @ Mᵀ + offset + small noise
    with M a fixed random 10×2 mixing matrix.
    """
    rng = np.random.default_rng(SEED)
    z_latent = rng.normal(0.0, 1.0, size=(N, LATENT))
    mixing = rng.normal(0.0, 1.0, size=(D, LATENT))
    offset = rng.normal(0.0, 2.0, size=D)
    noise = rng.normal(0.0, NOISE, size=(N, D))
    return z_latent @ mixing.T + offset + noise


# ---------------------------------------------------------------------------
# Core functions — YOU implement these six
# ---------------------------------------------------------------------------


def center(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Subtract the column-wise mean.

    Returns (X_centered, mean): X_centered shape (N, D), mean shape (D,).

    TODO: implement — compute the per-column mean (axis=0), subtract it,
    return both.
    """
    # TODO: implement column-wise centering
    raise NotImplementedError("TODO: implement center()")


def covariance_matrix(Xc: np.ndarray) -> np.ndarray:
    """
    Sample covariance of the CENTERED data:  C = (1/(N−1)) · Xcᵀ Xc.

    Returns shape (D, D) — symmetric.

    TODO: implement — one matrix product of Xc against itself, scaled by
    1/(N−1). (Do not use np.cov; building C is the exercise.)
    """
    # TODO: implement the sample covariance of the centered data
    raise NotImplementedError("TODO: implement covariance_matrix()")


def pca_fit(X: np.ndarray) -> dict[str, np.ndarray]:
    """
    Full PCA fit. Returns a dict:
      "components":  (D, D) — eigenvectors of the covariance as COLUMNS,
                     sorted by eigenvalue DESCENDING (components[:, 0] is PC1)
      "eigenvalues": (D,)   — the matching variances, descending
      "mean":        (D,)   — the column means (needed to reconstruct)

    TODO: implement.
      1. center(X), then covariance_matrix of the centered data.
      2. np.linalg.eigh(C) → (eigenvalues ascending, eigenvectors as columns).
      3. Reorder BOTH to descending eigenvalue order (np.argsort gives
         ascending — reverse it; reindex the eigenvector COLUMNS with it).
      4. Return the dict.
    """
    # TODO: center → covariance → eigh → sort descending → return the dict
    raise NotImplementedError("TODO: implement pca_fit()")


def project(Xc: np.ndarray, components: np.ndarray, k: int) -> np.ndarray:
    """
    Project CENTERED data onto the top-k principal components:
      Z = Xc @ components[:, :k]        → shape (N, k)

    TODO: implement — slice the first k component columns and one matrix
    product.
    """
    # TODO: implement the projection onto the top-k components
    raise NotImplementedError("TODO: implement project()")


def reconstruct(Z: np.ndarray, components: np.ndarray, mean: np.ndarray) -> np.ndarray:
    """
    Map k-D scores back to the original D-D space and un-center:
      X̂ = Z @ components[:, :k]ᵀ + mean        → shape (N, D)
    (k is Z.shape[1] — slice the same columns you projected with.)

    TODO: implement — one matrix product against the transposed component
    slice, then add the mean back.
    """
    # TODO: implement the reconstruction back to D dimensions
    raise NotImplementedError("TODO: implement reconstruct()")


def explained_variance_ratio(eigenvalues: np.ndarray) -> np.ndarray:
    """
    Each eigenvalue's share of the total variance: λ_j / Σ λ. Shape (D,).

    TODO: implement — one line.
    """
    # TODO: implement the explained variance ratio
    raise NotImplementedError("TODO: implement explained_variance_ratio()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def reconstruction_mse(X: np.ndarray, model: dict[str, np.ndarray], k: int) -> float:
    """Mean squared reconstruction error using the top-k components."""
    Xc = X - model["mean"]
    Z = project(Xc, model["components"], k)
    X_hat = reconstruct(Z, model["components"], model["mean"])
    return float(np.mean((X - X_hat) ** 2))


def main() -> None:
    print("Task 4 — PCA from scratch\n")

    X = make_data()
    print(f"  Data: {N} points in {D}-D (secretly ≈{LATENT}-D + noise {NOISE})\n")

    print("[1/3] Fitting PCA (covariance eigendecomposition)...")
    model = pca_fit(X)
    components, eigenvalues = model["components"], model["eigenvalues"]
    print(f"  eigenvalues (desc): {np.round(eigenvalues, 4)}")

    # Orthonormality: componentsᵀ components should be the identity.
    gram = components.T @ components
    ortho_err = float(np.max(np.abs(gram - np.eye(D))))
    print(f"  max |componentsᵀ·components − I| = {ortho_err:.2e}\n")

    print("[2/3] Explained variance...")
    evr = explained_variance_ratio(eigenvalues)
    print(f"  EVR: {np.round(evr, 4)}")
    top2 = float(evr[:2].sum())
    print(f"  top-2 cumulative EVR = {top2:.4f}  → the 10-D cloud is really a plane\n")

    print("[3/3] Reconstruction error vs k...")
    ks = [1, 2, 5, 10]
    mses = {k: reconstruction_mse(X, model, k) for k in ks}
    for k in ks:
        print(f"  k={k:>2}: reconstruction MSE = {mses[k]:.6f}")
    max_recon_err = float(
        np.max(
            np.abs(
                X
                - reconstruct(project(X - model["mean"], components, D), components, model["mean"])
            )
        )
    )
    print(f"  k={D} max |X̂ − X| = {max_recon_err:.2e}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_ortho = ortho_err < 1e-6
    ok_evr = top2 >= 0.9
    ok_mono = mses[1] > mses[2] > mses[5]
    ok_full = max_recon_err < 1e-6
    print(
        f"  [{'x' if ok_ortho else ' '}] components orthonormal  (max deviation {ortho_err:.2e} < 1e-6)"
    )
    print(f"  [{'x' if ok_evr else ' '}] top-2 explained variance ratio ≥ 0.9  (got {top2:.4f})")
    print(f"  [{'x' if ok_mono else ' '}] reconstruction MSE strictly decreases for k = 1 → 2 → 5")
    print(
        f"  [{'x' if ok_full else ' '}] k={D} reconstruction recovers X  (max err {max_recon_err:.2e} < 1e-6)"
    )

    if ok_ortho and ok_evr and ok_mono and ok_full:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
