/**
 * Task 4 🔴 — PCA (Principal Component Analysis) from scratch.
 *
 * What you'll learn:
 *   - PCA as finding the orthogonal directions of maximum variance — which
 *     are exactly the eigenvectors of the covariance matrix
 *   - Explained variance ratio: how many dimensions the data REALLY uses
 *   - Projection and reconstruction: lossy compression whose error is the
 *     variance you threw away
 *   - Why this matters later in the course: visualising embeddings (module 04)
 *     and shrinking vector-store footprints are PCA jobs
 *
 * The math (README derives each step):
 *
 *   Center:        X_c = X − mean(X)                    (column-wise mean)
 *   Covariance:    C   = (1/(N−1)) · X_cᵀ X_c           (D×D, symmetric)
 *   Eigen:         C v_j = λ_j v_j — eigenvectors v_j are the principal
 *                  components; eigenvalue λ_j is the variance along v_j.
 *   Sort λ descending; stack the v_j as COLUMNS of `components` (D×D).
 *   EVR:           evr_j = λ_j / Σ λ
 *   Project:       Z = X_c @ components[:, :k]           (N×k scores)
 *   Reconstruct:   X̂ = Z @ components[:, :k]ᵀ + mean     (back to N×D)
 *
 * 🔴 rule: no math libraries. A `symmetricEigen(A)` helper (cyclic Jacobi
 * rotations) is PROVIDED — do not edit it. It returns eigenpairs in NO
 * particular order; sorting them DESCENDING by eigenvalue is part of your job.
 *
 * You implement center, covarianceMatrix, pcaFit, project, reconstruct,
 * explainedVarianceRatio. The 10-D dataset (secretly ~2-D) and the harness
 * are provided.
 *
 * How to run:
 *   pnpm tsx modules/01f-stats-foundations/ts/04-pca.ts
 */

const SEED = 3;
const N = 300;
const D = 10;
const LATENT = 2; // the data secretly lives near a 2-D plane
const NOISE = 0.05;

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG + Box-Muller for reproducible Gaussians
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // Numerical Recipes LCG
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296; // uniform in [0, 1)
  };
}

function makeGaussian(seed: number): () => number {
  const u = makeRng(seed);
  return () => {
    // Box-Muller: two uniforms → one standard normal
    const u1 = u() + 1e-12;
    const u2 = u();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  };
}

// ---------------------------------------------------------------------------
// Matrix helpers (provided)
// ---------------------------------------------------------------------------

/** A (N×K) @ B (K×M) → (N×M). */
function matMul(A: number[][], B: number[][]): number[][] {
  const n = A.length,
    k = A[0].length,
    m = B[0].length;
  const C = Array.from({ length: n }, () => new Array(m).fill(0) as number[]);
  for (let i = 0; i < n; i++)
    for (let p = 0; p < k; p++)
      for (let j = 0; j < m; j++) C[i][j] += A[i][p] * B[p][j];
  return C;
}

/** Transpose A (N×M) → (M×N). */
function transpose(A: number[][]): number[][] {
  const n = A.length,
    m = A[0].length;
  const T = Array.from({ length: m }, () => new Array(n).fill(0) as number[]);
  for (let i = 0; i < n; i++) for (let j = 0; j < m; j++) T[j][i] = A[i][j];
  return T;
}

// ---------------------------------------------------------------------------
// symmetricEigen (provided — do not edit)
//
// Eigendecomposition of a real symmetric matrix via the cyclic Jacobi method:
// repeatedly apply plane rotations that zero the largest-magnitude off-diagonal
// entry until the matrix is (numerically) diagonal. The accumulated rotations
// are the eigenvectors. Returns { values, vectors } where vectors' COLUMNS are
// unit eigenvectors: vectors[i][j] = i-th component of the j-th eigenvector,
// matching values[j]. Order is NOT sorted — that's your job in pcaFit.
// ---------------------------------------------------------------------------

function symmetricEigen(A: number[][]): { values: number[]; vectors: number[][] } {
  const n = A.length;
  const a = A.map((row) => [...row]); // working copy
  const V: number[][] = Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)),
  );
  for (let sweep = 0; sweep < 100; sweep++) {
    // Largest off-diagonal magnitude — stop when the matrix is diagonal.
    let off = 0;
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) off = Math.max(off, Math.abs(a[i][j]));
    if (off < 1e-13) break;
    for (let p = 0; p < n - 1; p++) {
      for (let q = p + 1; q < n; q++) {
        if (Math.abs(a[p][q]) < 1e-15) continue;
        // Jacobi rotation angle for the (p, q) plane.
        const theta = (a[q][q] - a[p][p]) / (2 * a[p][q]);
        const t =
          Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
        const c = 1 / Math.sqrt(t * t + 1);
        const s = t * c;
        // Rotate rows/columns p and q of the working matrix.
        for (let i = 0; i < n; i++) {
          const aip = a[i][p],
            aiq = a[i][q];
          a[i][p] = c * aip - s * aiq;
          a[i][q] = s * aip + c * aiq;
        }
        for (let i = 0; i < n; i++) {
          const api = a[p][i],
            aqi = a[q][i];
          a[p][i] = c * api - s * aqi;
          a[q][i] = s * api + c * aqi;
        }
        // Accumulate the rotation into the eigenvector matrix.
        for (let i = 0; i < n; i++) {
          const vip = V[i][p],
            viq = V[i][q];
          V[i][p] = c * vip - s * viq;
          V[i][q] = s * vip + c * viq;
        }
      }
    }
  }
  return { values: a.map((row, i) => row[i]), vectors: V };
}

// ---------------------------------------------------------------------------
// Synthetic data (provided — do not edit)
// ---------------------------------------------------------------------------

/**
 * 10-D data that secretly lives near a 2-D plane:
 *   Z_latent (N×2) standard normal → X = Z_latent @ Mᵀ + offset + small noise
 * with M a fixed random 10×2 mixing matrix.
 */
function makeData(): number[][] {
  const g = makeGaussian(SEED);
  const zLatent = Array.from({ length: N }, () =>
    Array.from({ length: LATENT }, () => g()),
  );
  const gm = makeGaussian(SEED + 1);
  const mixing = Array.from({ length: D }, () =>
    Array.from({ length: LATENT }, () => gm()),
  );
  const go = makeGaussian(SEED + 2);
  const offset = Array.from({ length: D }, () => 2 * go());
  const gn = makeGaussian(SEED + 3);
  return zLatent.map((z) =>
    mixing.map(
      (mRow, j) => mRow.reduce((acc, m, l) => acc + m * z[l], offset[j]) + NOISE * gn(),
    ),
  );
}

interface PcaModel {
  /** (D×D) eigenvectors of the covariance as COLUMNS, eigenvalue-descending. */
  components: number[][];
  /** (D) the matching variances, descending. */
  eigenvalues: number[];
  /** (D) the column means (needed to reconstruct). */
  mean: number[];
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these six
// ---------------------------------------------------------------------------

/**
 * Subtract the column-wise mean.
 *
 * Returns { Xc, mean }: Xc is (N×D) centered data, mean is length D.
 *
 * TODO: implement — compute the per-column mean, subtract it from every row,
 * return both.
 */
function center(X: number[][]): { Xc: number[][]; mean: number[] } {
  // TODO: implement column-wise centering
  throw new Error("TODO: implement center()");
}

/**
 * Sample covariance of the CENTERED data:  C = (1/(N−1)) · Xcᵀ Xc.
 *
 * Returns (D×D) — symmetric.
 *
 * TODO: implement — one product of transpose(Xc) against Xc (matMul helper),
 * with every entry scaled by 1/(N−1).
 */
function covarianceMatrix(Xc: number[][]): number[][] {
  // TODO: implement the sample covariance of the centered data
  throw new Error("TODO: implement covarianceMatrix()");
}

/**
 * Full PCA fit.
 *
 * TODO: implement.
 *   1. center(X), then covarianceMatrix of the centered data.
 *   2. symmetricEigen(C) → { values, vectors } (vectors' columns are unit
 *      eigenvectors, UNSORTED).
 *   3. Reorder BOTH to descending eigenvalue order: sort the column indices
 *      by eigenvalue, then rebuild the components matrix with its columns in
 *      that order.
 *   4. Return { components, eigenvalues, mean }.
 */
function pcaFit(X: number[][]): PcaModel {
  // TODO: center → covariance → symmetricEigen → sort descending → return
  throw new Error("TODO: implement pcaFit()");
}

/**
 * Project CENTERED data onto the top-k principal components:
 *   Z = Xc @ components[:, :k]        → (N×k) scores
 *
 * TODO: implement — for each row of Xc, its dot product with each of the
 * first k component COLUMNS.
 */
function project(Xc: number[][], components: number[][], k: number): number[][] {
  // TODO: implement the projection onto the top-k components
  throw new Error("TODO: implement project()");
}

/**
 * Map k-D scores back to the original D-D space and un-center:
 *   X̂ = Z @ components[:, :k]ᵀ + mean        → (N×D)
 * (k is Z[0].length — use the same columns you projected with.)
 *
 * TODO: implement — for each score row, a weighted sum of the first k
 * component columns, plus the mean.
 */
function reconstruct(
  Z: number[][],
  components: number[][],
  mean: number[],
): number[][] {
  // TODO: implement the reconstruction back to D dimensions
  throw new Error("TODO: implement reconstruct()");
}

/**
 * Each eigenvalue's share of the total variance: λ_j / Σ λ. Length D.
 *
 * TODO: implement — one map over the eigenvalues.
 */
function explainedVarianceRatio(eigenvalues: number[]): number[] {
  // TODO: implement the explained variance ratio
  throw new Error("TODO: implement explainedVarianceRatio()");
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

/** Mean squared reconstruction error using the top-k components. */
function reconstructionMse(X: number[][], model: PcaModel, k: number): number {
  const Xc = X.map((row) => row.map((v, j) => v - model.mean[j]));
  const Z = project(Xc, model.components, k);
  const Xhat = reconstruct(Z, model.components, model.mean);
  let total = 0;
  for (let i = 0; i < X.length; i++)
    for (let j = 0; j < X[0].length; j++) total += (X[i][j] - Xhat[i][j]) ** 2;
  return total / (X.length * X[0].length);
}

function round(v: number[], places = 4): number[] {
  const f = 10 ** places;
  return v.map((x) => Math.round(x * f) / f);
}

function main(): void {
  console.log("Task 4 — PCA from scratch\n");

  const X = makeData();
  console.log(
    `  Data: ${N} points in ${D}-D (secretly ≈${LATENT}-D + noise ${NOISE})\n`,
  );

  console.log("[1/3] Fitting PCA (covariance eigendecomposition)...");
  const model = pcaFit(X);
  const { components, eigenvalues } = model;
  console.log(`  eigenvalues (desc): [${round(eigenvalues)}]`);

  // Orthonormality: componentsᵀ components should be the identity.
  const gram = matMul(transpose(components), components);
  let orthoErr = 0;
  for (let i = 0; i < D; i++)
    for (let j = 0; j < D; j++)
      orthoErr = Math.max(orthoErr, Math.abs(gram[i][j] - (i === j ? 1 : 0)));
  console.log(`  max |componentsᵀ·components − I| = ${orthoErr.toExponential(2)}\n`);

  console.log("[2/3] Explained variance...");
  const evr = explainedVarianceRatio(eigenvalues);
  console.log(`  EVR: [${round(evr)}]`);
  const top2 = evr[0] + evr[1];
  console.log(
    `  top-2 cumulative EVR = ${top2.toFixed(4)}  → the 10-D cloud is really a plane\n`,
  );

  console.log("[3/3] Reconstruction error vs k...");
  const ks = [1, 2, 5, 10];
  const mses = new Map<number, number>();
  for (const k of ks) {
    mses.set(k, reconstructionMse(X, model, k));
    console.log(
      `  k=${String(k).padStart(2)}: reconstruction MSE = ${mses.get(k)!.toFixed(6)}`,
    );
  }
  const Xc = X.map((row) => row.map((v, j) => v - model.mean[j]));
  const XhatFull = reconstruct(project(Xc, components, D), components, model.mean);
  let maxReconErr = 0;
  for (let i = 0; i < N; i++)
    for (let j = 0; j < D; j++)
      maxReconErr = Math.max(maxReconErr, Math.abs(X[i][j] - XhatFull[i][j]));
  console.log(`  k=${D} max |X̂ − X| = ${maxReconErr.toExponential(2)}`);

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okOrtho = orthoErr < 1e-6;
  const okEvr = top2 >= 0.9;
  const okMono = mses.get(1)! > mses.get(2)! && mses.get(2)! > mses.get(5)!;
  const okFull = maxReconErr < 1e-6;
  console.log(
    `  [${okOrtho ? "x" : " "}] components orthonormal  (max deviation ${orthoErr.toExponential(2)} < 1e-6)`,
  );
  console.log(
    `  [${okEvr ? "x" : " "}] top-2 explained variance ratio ≥ 0.9  (got ${top2.toFixed(4)})`,
  );
  console.log(
    `  [${okMono ? "x" : " "}] reconstruction MSE strictly decreases for k = 1 → 2 → 5`,
  );
  console.log(
    `  [${okFull ? "x" : " "}] k=${D} reconstruction recovers X  (max err ${maxReconErr.toExponential(2)} < 1e-6)`,
  );

  if (okOrtho && okEvr && okMono && okFull) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
