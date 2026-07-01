# Module 01f — Probability, Statistics & PCA

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

ML-engineer and data-science interviews lean on **probability and statistics**
the course never covers: Bayes' theorem (and the base-rate trap), maximum
likelihood (MLE — and why cross-entropy _is_ maximum likelihood), hypothesis
testing and A/B (A vs B experiment) tests, and PCA (Principal Component Analysis)
for dimensionality reduction. This module fills that gap.

Everything here is **pure numpy (Python) / plain TypeScript (no math libraries)**,
fully **offline**, and **deterministic** (fixed seeds, synthetic data generated in
code). No provider, no network, no LLM (Large Language Model). You implement the
pedagogically-core functions; the data generation, simulations, grid searches,
and printing are done for you and are runnable the moment you fill the stubs.

This module does **not** duplicate Module 01b (ROC/AUC, k-means) or Module 08
(precision/recall/F1, confusion matrix). Here we focus on **Bayes & naive Bayes,
MLE & the loss-function connection, hypothesis testing & A/B tests, and PCA**.

---

## Concepts

### 1. Bayes' theorem, the base-rate fallacy, and naive Bayes

Bayes' theorem inverts a conditional probability — it turns "how likely is this
evidence, given the hypothesis" into "how likely is the hypothesis, given this
evidence":

```
P(H | E) = P(E | H) · P(H) / P(E)
```

The classic interview question: a disease has **1% prevalence**; a test has
**95% sensitivity** (P(+ | disease)) and **95% specificity** (P(− | healthy)).
You test positive. What's the chance you're sick? Intuition screams ~95%.
Bayes says otherwise. A positive test can arrive two ways:

```
true positive:   prior · sens              = 0.01 · 0.95 = 0.0095
false positive:  (1 − prior) · (1 − spec)  = 0.99 · 0.05 = 0.0495

P(disease | +) = 0.0095 / (0.0095 + 0.0495) ≈ 0.16
```

Only **16%**! The healthy 99% generate five times more false positives than the
sick 1% generate true positives. Ignoring the prior like this is the
**base-rate fallacy** — the single most common probability trap in interviews
(and in reading ML metrics on imbalanced data).

**Naive Bayes** turns this machinery into a text classifier. For a document
`w₁…wₙ` and class `c`, Bayes gives `P(c | doc) ∝ P(doc | c) · P(c)`. The
"naive" step assumes words are **independent given the class**, so
`P(doc | c) = Π_i P(w_i | c)`. Two practical fixes make it work:

- **Log space.** A product of 50 small probabilities underflows to 0. Sum logs
  instead: `log P(c | doc) ∝ log P(c) + Σ_i log P(w_i | c)`.
- **Laplace (add-one) smoothing.** A word never seen in class `c` would give
  `P(w | c) = 0` and veto the whole class. Pretend every word was seen once
  more than it was:

```
P(w | c) = (count(w, c) + 1) / (total_tokens(c) + V)        V = vocabulary size
```

Prediction is `argmax_c` of the log posterior; normalising the log posteriors
(a stable softmax) gives calibrated-looking class probabilities.

### 2. Maximum likelihood, and why your losses ARE likelihoods

Given i.i.d. data `x₁…x_N` and a model `p(x | θ)`, the **likelihood** is how
probable the data is under parameters θ:

```
L(θ) = Π_i p(x_i | θ)         ℓ(θ) = Σ_i log p(x_i | θ)      (log-likelihood)
```

**MLE** picks the θ that maximises `ℓ` — equivalently, minimises the **negative
log-likelihood (NLL)**. For the two workhorse distributions, take the
derivative, set it to zero:

```
Gaussian per-point NLL:   ½·log(2πσ²) + (x − μ)² / (2σ²)
  ∂/∂μ = 0   →  μ̂  = (1/N) Σ x_i               (the sample mean)
  ∂/∂σ² = 0  →  σ̂² = (1/N) Σ (x_i − μ̂)²        (the BIASED variance: ÷N, not N−1)

Bernoulli per-point NLL:  −[ x·log p + (1 − x)·log(1 − p) ]
  ∂/∂p = 0   →  p̂  = (1/N) Σ x_i               (the fraction of 1s)
```

Now the punchline interviewers fish for. Look at the Gaussian NLL as a function
of μ with σ fixed: it is `MSE/(2σ²) + constant`. So **minimising MSE is exactly
maximising a Gaussian likelihood** — least squares silently assumes Gaussian
noise. And the Bernoulli NLL is **literally the binary cross-entropy formula**,
term for term — BCE isn't "a loss that happens to work", it's the MLE objective
for a model that outputs `P(y = 1)`. (The same argument extends to softmax
cross-entropy and a categorical likelihood — that's module 08's loss.) The task
makes this concrete: grid-search each NLL, grid-search MSE/BCE on the same data,
and watch all the argmins coincide with the closed forms.

### 3. Hypothesis testing and the A/B test

An A/B test asks: arm A converted `conv_a / n_a`, arm B converted `conv_b / n_b`
— is the difference real, or noise? Frame it as a **hypothesis test**:

- **H₀ (null):** both arms share one true rate; the observed gap is luck.
- **H₁:** the rates differ.

A sample proportion `p̂` is a mean of 0/1s, so by the CLT (Central Limit Theorem)
it's approximately normal with variance `p(1−p)/n`. Under H₀ the best estimate
of the shared rate is the **pooled proportion**, which gives the standard error
of the difference, and the **z statistic** counts how many standard errors of
gap we observed:

```
p̂_pool = (conv_a + conv_b) / (n_a + n_b)
SE      = √( p̂_pool·(1 − p̂_pool)·(1/n_a + 1/n_b) )
z       = (p̂_b − p̂_a) / SE
p-value = 2 · (1 − Φ(|z|))          Φ(z) = ½·(1 + erf(z/√2))
```

The **p-value** is `P(a gap this extreme | H₀ is true)` — a statement about the
_data_, **not** `P(H₀ is true)`. If `p < α` (typically 0.05) we "reject H₀".
The **confidence interval** for the true difference uses the unpooled SE (each
arm keeps its own variance): `(p̂_b − p̂_a) ± z_crit·SE_unpooled`. A 95% CI that
excludes 0 agrees with `p < 0.05`.

Three failure modes to internalise (the harness simulates each):

- **Type I error (α):** run an A/A test (no true difference) many times, and
  the test still fires ≈ α of the time. That's not a bug — α is the false-alarm
  rate you chose.
- **Power:** with a true lift, the probability you detect it. Grows with sample
  size and effect size; an underpowered test mostly reports "no significant
  difference" even for real effects.
- **Multiple testing:** check 20 metrics on an A/A test and
  `P(≥1 spurious "win") = 1 − 0.95²⁰ ≈ 64%`. Pick the primary metric _before_
  the experiment, or correct for multiplicity (e.g. Bonferroni: use α/20).

### 4. PCA: variance-maximising directions = eigenvectors of the covariance

PCA asks: which **orthogonal directions** carry the most variance? Center the
data (`X_c = X − mean`), and the variance of the projection onto a unit vector
`v` is `vᵀ C v`, where `C` is the sample covariance:

```
C = (1/(N−1)) · X_cᵀ X_c          (D×D, symmetric)
```

Maximising `vᵀ C v` subject to `‖v‖ = 1` (a Lagrange multiplier away) gives
`C v = λ v` — the optimum is an **eigenvector** of `C`, and the variance it
captures is its **eigenvalue**. Because `C` is symmetric, the eigenvectors are
mutually orthogonal, so the principal components form an orthonormal basis,
sorted by eigenvalue descending. Each component's share of the total variance
is the **explained variance ratio** `λ_j / Σ λ`; project onto the top-k columns
and reconstruct to compress:

```
Z  = X_c @ components[:, :k]            (N×k scores — the compressed data)
X̂  = Z @ components[:, :k]ᵀ + mean      (back to N×D)
```

The reconstruction MSE equals the variance you threw away (the mean of the
discarded eigenvalues, `Σ_{j>k} λ_j / D`) — so it can only shrink as k grows,
and with k = D the reconstruction is exact (you just rotated and rotated back).
The task's dataset is 10-D but secretly generated from 2 latent factors: PCA
finds that plane, putting ≥ 90% of the variance in the top 2 components.

Why this matters later in the course: embedding vectors (module 04) are 384-,
768-, 1536-D — PCA is how you **visualise** them in 2-D and one way to shrink a
vector store's footprint. Eigendecomposition itself: Python calls
`np.linalg.eigh` (for symmetric matrices) inside your `pca_fit` — sorting its
ascending eigenpairs descending is part of the task; TypeScript gets a provided
`symmetricEigen()` (cyclic Jacobi rotations) so the two languages stay parallel.

---

## Tasks

### Task 1 🟡 — Bayes' theorem + a naive Bayes classifier

**Goal:** Answer the classic medical-test question with Bayes' theorem, then
scale the same rule up into a working spam classifier.

**Files:**

- `py/01_bayes_naive_bayes.py`
- `ts/01-bayes-naive-bayes.ts`

**Steps:**

_Part A — Bayes' theorem:_

1. Implement `bayes_posterior(prior, sensitivity, specificity)` /
   `bayesPosterior(...)`: P(disease | positive test) — the true-positive mass
   divided by the total positive mass (true + false positives).

_Part B — multinomial naive Bayes:_

2. Implement `fit_naive_bayes(docs, labels)` / `fitNaiveBayes(...)`: log class
   priors from doc counts, plus Laplace-smoothed per-word log-likelihoods
   `log((count + 1) / (total + V))` as a 2×V table.
3. Implement `predict_log_posterior(model, doc)` / `predictLogPosterior(...)`:
   `log P(c) + Σ log P(w | c)` over the doc's tokens — sums of logs, never
   products of probabilities. (Argmax `predict` and the softmax
   `posterior_probs` are provided on top of it.)

**Acceptance:**

- The 1%-prevalence / 95%-sensitivity / 95%-specificity posterior is within
  **±0.005** of the analytic value (≈ 0.161 — the interview trap).
- Held-out spam/ham accuracy **≥ 0.9**.
- An obvious all-spam-words doc gets **P(spam) > 0.9**.

---

### Task 2 🟡 — MLE and the loss-function connection

**Goal:** Derive-by-doing: compute closed-form MLEs, verify them with a grid
search over the NLL, then show minimising MSE/BCE finds the same optima.

**Files:**

- `py/02_mle_loss.py`
- `ts/02-mle-loss.ts`

**Steps:**

1. Implement `gaussian_mle(x)` / `gaussianMle(x)`: μ̂ = sample mean,
   σ̂² = **biased** MLE variance (divide by N).
2. Implement `bernoulli_mle(x)` / `bernoulliMle(x)`: p̂ = fraction of 1s.
3. Implement `nll_gaussian(x, mu, sigma)` / `nllGaussian(...)`: average of
   `½·log(2πσ²) + (x − μ)²/(2σ²)`.
4. Implement `nll_bernoulli(x, p)` / `nllBernoulli(...)`: average of
   `−[x·log p + (1 − x)·log(1 − p)]` — recognise it as BCE.

**Acceptance:**

- Each NLL's grid argmin lands within **one grid step** of the closed-form MLE
  (both distributions).
- The MSE argmin **equals** the Gaussian-NLL argmin (same grid index).
- The BCE argmin **equals** the Bernoulli-NLL argmin (same grid index).

---

### Task 3 🟢 — Hypothesis testing & the A/B test

**Goal:** Build the two-proportion z-test, then use simulation to see α, power,
and the multiple-testing trap with your own eyes.

**Files:**

- `py/03_ab_testing.py`
- `ts/03-ab-testing.ts`

**Steps:**

1. Implement `normal_cdf(z)` / `normalCdf(z)`: `½·(1 + erf(z/√2))` — Python
   uses `math.erf`; TS uses the provided `erf()` helper.
2. Implement `two_proportion_ztest(conv_a, n_a, conv_b, n_b)` /
   `twoProportionZtest(...)`: pooled proportion → pooled SE → z → two-sided
   p-value.
3. Implement `confidence_interval_diff(conv_a, n_a, conv_b, n_b, z_crit)` /
   `confidenceIntervalDiff(...)`: `(p̂_b − p̂_a) ± z_crit · SE_unpooled`.

The provided harness then runs: a worked A/B experiment with a real lift, an
A/A simulation (false-positive rate ≈ α), an A/B simulation (empirical power),
and a 20-metric A/A run (the multiple-testing warning).

**Acceptance:**

- Worked example: **p < 0.05** and the 95% CI **excludes 0**.
- A/A false-positive rate within **0.05 ± 0.02**.
- Empirical power is reported (and exceeds the A/A rate).
- The 20-metric A/A run finds **≥ 1** spurious "significant" result (with the
  fixed seed).

---

### Task 4 🔴 — PCA from scratch

**Goal:** Implement the full PCA pipeline — center, covariance,
eigendecomposition, sort, project, reconstruct — and watch it discover that a
10-D dataset is secretly a 2-D plane.

**Files:**

- `py/04_pca.py`
- `ts/04-pca.ts`

**Steps:**

1. Implement `center(X)`: subtract the column-wise mean; return both the
   centered data and the mean.
2. Implement `covariance_matrix(Xc)` / `covarianceMatrix(Xc)`:
   `(1/(N−1)) · XcᵀXc` (do **not** use `np.cov` — building it is the exercise).
3. Implement `pca_fit(X)` / `pcaFit(X)`: center → covariance →
   eigendecomposition → sort eigenpairs **descending**. Python calls
   `np.linalg.eigh` (returns ascending — reordering is your job); TS calls the
   **provided** `symmetricEigen()` (Jacobi rotations, unsorted — do not edit it).
4. Implement `project(Xc, components, k)`: `Xc @ components[:, :k]`.
5. Implement `reconstruct(Z, components, mean)`: `Z @ components[:, :k]ᵀ + mean`.
6. Implement `explained_variance_ratio(eigenvalues)` /
   `explainedVarianceRatio(...)`: `λ_j / Σ λ`.

**Acceptance:**

- Components are **orthonormal**: `componentsᵀ·components ≈ I` (max deviation
  < 1e-6).
- Top-2 explained variance ratio **≥ 0.9** (the hidden plane).
- Reconstruction MSE **strictly decreases** for k = 1 → 2 → 5.
- k = 10 projection + reconstruction recovers X within tolerance (max error
  < 1e-6).

---

## Done when

- [ ] `01_bayes_naive_bayes` / `01-bayes-naive-bayes` prints the ≈ 0.16
      medical-test posterior (within ±0.005), ≥ 0.9 held-out spam/ham accuracy,
      and P(spam) > 0.9 on the obvious spam doc.
- [ ] `02_mle_loss` / `02-mle-loss` prints grid argmins within one step of the
      closed-form MLEs, with the MSE argmin matching Gaussian-NLL and the BCE
      argmin matching Bernoulli-NLL.
- [ ] `03_ab_testing` / `03-ab-testing` prints a significant worked example
      (p < 0.05, CI excluding 0), an A/A false-positive rate ≈ 0.05, an
      empirical power figure, and ≥ 1 spurious hit in the 20-metric demo.
- [ ] `04_pca` / `04-pca` prints orthonormal components, top-2 EVR ≥ 0.9,
      strictly decreasing reconstruction MSE for k = 1 → 2 → 5, and an exact
      k = 10 reconstruction.

Each file prints its own **Acceptance** checklist at the end — every box should read
`[x]` and the file should say "All acceptance checks passed."

---

## Going deeper

- **Introduction to Probability** (Blitzstein & Hwang, Harvard Stat 110) — the
  best grounding for Bayes, distributions, and MLE; free book + lectures:
  <https://projects.iq.harvard.edu/stat110>
- **Statistical Inference** (Casella & Berger) — the rigorous reference for
  likelihood theory and hypothesis testing.
- **StatQuest (Josh Starmer)** — intuitive video explainers for Bayes, MLE,
  p-values, and PCA: <https://www.youtube.com/c/joshstarmer>
- **A One-Stop Shop for Principal Component Analysis** — a visual walk through
  PCA, eigenvectors, and explained variance:
  <https://towardsdatascience.com/a-one-stop-shop-for-principal-component-analysis-5582fb7e0a9c>
- **Evan Miller — How Not To Run an A/B Test** — the classic warning about
  peeking and multiple testing: <https://www.evanmiller.org/how-not-to-run-an-ab-test.html>

---

## Environment

No provider, network, or LLM — these exercises are fully offline and deterministic
(fixed seeds, synthetic data generated in code). No new environment variables.

**Python:** numpy only (a base dependency — no extra needed; `math.erf` is
standard library).

```bash
uv run python modules/01f-stats-foundations/py/01_bayes_naive_bayes.py
```

**TypeScript:** plain arrays only (no npm math libraries). Build nothing; just run.

```bash
pnpm tsx modules/01f-stats-foundations/ts/01-bayes-naive-bayes.ts
```
