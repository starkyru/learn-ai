# Module 01b — Classic ML Foundations

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

This course jumps almost straight to LLMs — but every AI interview, and a lot of
real debugging, still leans on the **classic-ML theory** underneath: linear and
logistic regression, the bias–variance tradeoff, regularisation, gradient-descent
mechanics, and ranking metrics like ROC (Receiver Operating Characteristic)/AUC (Area Under the Curve). This module fills that gap.

Everything here is **pure numpy (Python) / plain TypeScript (no math libraries)**,
fully **offline**, and **deterministic** (fixed seeds, synthetic data generated in
code). No provider, no network, no LLM (Large Language Model). You implement the pedagogically-core
functions; the data generation, training loops, splits, and printing are done for
you and are runnable the moment you fill the stubs.

This module does **not** duplicate Module 08 (softmax, cross-entropy for the
multi-class case, precision/recall/F1 (F1 score, the harmonic mean of precision and recall), confusion matrix). Here we focus on
**regression, bias–variance & cross-validation, regularisation, ROC/AUC, and
k-means**.

---

## Concepts

### 1. Linear regression, the normal equation, and gradient descent

We model a target `y` as a linear function of features `X` plus noise. If we fold
the intercept into the weights (prepend a column of `1`s to `X`, so `w[0]` is the
bias), the model is just:

```
ŷ = X w
```

We measure error with **mean squared error (MSE)**:

```
L(w) = (1/N) · ||X w - y||²  =  (1/N) · Σ_i (x_iᵀw - y_i)²
```

MSE is a convex, smooth bowl in `w`, so it has a single global minimum. Set the
gradient to zero to find it. The gradient is:

```
∇L(w) = (2/N) · Xᵀ (X w - y)
```

Setting `∇L = 0` and cancelling the constant gives the **normal equation**:

```
XᵀX w = Xᵀ y        →        w = (XᵀX)⁻¹ Xᵀ y
```

**Never form the inverse.** `(XᵀX)⁻¹` is slower to compute and numerically worse
than solving the linear system directly. Assemble `A = XᵀX` and `b = Xᵀy`, then
solve `A w = b` with an LU-based solver (`np.linalg.solve` in numpy; a small
Gaussian-elimination `solve()` is provided in the TS harness).

The closed form is exact but costs `O(D³)` and needs the whole dataset in memory.
**Gradient descent** finds the same minimum iteratively, one cheap step at a time:

```
w ← w - lr · ∇L(w) = w - lr · (2/N) · Xᵀ (X w - y)
```

With a sensible learning rate on standardised features, GD (Gradient Descent) marches monotonically
downhill to the same `w` the normal equation gives.

**R² (coefficient of determination)** is a scale-free goodness-of-fit score:

```
R² = 1 - SS_res / SS_tot
   SS_res = Σ (y_i - ŷ_i)²      (error the model still makes)
   SS_tot = Σ (y_i - ȳ)²        (error of just predicting the mean)
```

`R² = 1` is a perfect fit; `R² = 0` is no better than predicting the mean; negative
means worse than the mean.

### 2. Bias–variance, cross-validation, and ridge regularisation

Fit a polynomial of degree `d` by building features `φ(x) = [1, x, x², …, x^d]` and
running least squares on `Φ`. As `d` grows the model can represent more shapes —
but that flexibility cuts both ways. Expected test error decomposes into three
pieces:

```
E[(y - ŷ)²] = bias² + variance + irreducible_noise
```

- **High bias / underfitting** (low `d`): the model is too simple to capture the
  signal, so it does badly on _both_ train and test.
- **High variance / overfitting** (high `d`): the model has enough freedom to chase
  the _noise_ in the training set. Train error keeps dropping toward zero, but test
  error climbs because the fitted wiggles don't generalise.

Plot test error vs `d` and you get the classic **U-curve**: it falls (bias
shrinking), bottoms out at the sweet spot, then rises (variance growing).

We can't see test error during training, so we estimate it with **k-fold
cross-validation**. Split the data into `k` folds; for each fold, train on the
other `k-1` and score on the held-out fold; average the `k` scores:

```
CV_MSE(d) = (1/k) · Σ_{f=1..k}  MSE( model trained on all folds but f,  fold f )
```

The CV (Cross-Validation) curve traces the same U as true test error, so its minimum tells you which
degree to pick — using only training data.

**Ridge (L2) regularisation** fights variance directly by penalising large weights:

```
L_ridge(w) = ||Φ w - y||² + λ · Σ_{j≥1} w_j²
```

Note the `j ≥ 1`: we **do not penalise the intercept** `w[0]` — shrinking the bias
would pull predictions toward zero for no good reason. The closed-form solution is
the normal equation with a `λ` added to the diagonal (except the bias entry):

```
w = (ΦᵀΦ + λ R)⁻¹ Φᵀ y ,      R = I  but  R[0,0] = 0
```

Larger `λ` → smaller `||w||` → smoother function → less variance (at the cost of a
little bias). At a fixed high degree, the right `λ` shrinks the weight norm _and_
lowers CV error. `λ = 0` recovers ordinary least squares.

### 3. Logistic regression (binary) and L2

For binary classification we want a **probability**, not a raw score. Feed the
linear score `z = X w` through the **sigmoid**:

```
σ(z) = 1 / (1 + e^{-z})        (squashes ℝ → (0, 1))
p = σ(X w) = P(class = 1 | x)
```

Predict class 1 when `p ≥ 0.5`. The right loss is **binary cross-entropy** (log
loss), the negative log-likelihood of the labels:

```
L = -1/N · Σ_i [ y_i · log(p_i) + (1 - y_i) · log(1 - p_i) ]
```

If the true label is 1 and `p → 1`, `log(p) → 0` (no loss); if `p → 0`, `log(p) →
-∞` (huge loss). Clip `p` to `[ε, 1-ε]` so `log` never sees exactly 0 or 1.

The gradient is beautifully simple — structurally identical to linear regression,
just with a sigmoid inside `p`:

```
∇L = (1/N) · Xᵀ (σ(X w) - y)
```

("prediction minus target", dotted with the features.) L2 regularisation adds
`(λ/N) · w` to the gradient, again **with the bias entry zeroed out**:

```
grad = (1/N) · Xᵀ (p - y) + (λ/N) · w      (but grad[0] gets no L2 term)
```

Larger `λ` shrinks `||w||`. On separable data the unregularised weights want to run
off to infinity (to push `p` to exactly 0/1); L2 reins them in.

### 4. Ranking metrics (ROC/AUC) and clustering (k-means)

**A classifier outputs scores, not just labels.** A _threshold_ turns a score into
a decision. Slide the threshold and the trade-off between catching positives and
raising false alarms changes. At threshold `t` (predict positive iff `score ≥ t`):

```
TPR(t) = TP / (TP + FN)   — true-positive rate  (a.k.a. recall / sensitivity)
FPR(t) = FP / (FP + TN)   — false-positive rate (1 − specificity)
```

Sweep `t` from high to low and plot `(FPR, TPR)`: that's the **ROC curve**. It
always runs from `(0, 0)` (threshold above every score — predict nothing positive)
to `(1, 1)` (threshold below every score — predict everything positive).

**AUC** is the area under that curve, computed with the trapezoidal rule:

```
AUC = Σ_i (fpr[i+1] - fpr[i]) · (tpr[i+1] + tpr[i]) / 2
```

AUC has a lovely interpretation: it equals the probability that a randomly chosen
positive is scored higher than a randomly chosen negative. It's **threshold-free**,
so it measures ranking quality independent of where you set the cutoff:

```
perfect ranker  → AUC = 1.0
random ranker   → AUC ≈ 0.5     (the diagonal)
reversed ranker → AUC = 0.0
```

**k-means (Lloyd's algorithm)** is unsupervised: no labels, just group `N` points
into `k` clusters by proximity. It alternates two steps until nothing changes:

```
assign:  for each point x_i, pick the nearest centroid   cluster(i) = argmin_k ||x_i - c_k||²
update:  move each centroid to the mean of its points     c_k = mean{ x_i : cluster(i) = k }
```

The objective it minimises is **inertia**, the within-cluster sum of squared
distances:

```
inertia = Σ_i ||x_i - c_{cluster(i)}||²
```

Both steps can only lower (or hold) inertia, so it's **monotonically
non-increasing** and the algorithm always converges — though possibly to a _local_
minimum, which is why initialisation matters. (The harness uses a farthest-first /
k-means++-style init to spread the starting centroids across the blobs.)

---

## Tasks

### Task 1 🟡 — Linear regression (normal equation + gradient descent)

**Goal:** Fit a linear model two ways — the closed-form normal equation and
gradient descent — and confirm they land on the same weights.

**Files:**

- `py/01_linear_regression.py`
- `ts/01-linear-regression.ts`

**Steps:**

1. Implement `normal_equation(X, y)` / `normalEquation(X, y)`: assemble `A = XᵀX`
   and `b = Xᵀy`, then solve `A w = b`. Python: `np.linalg.solve(A, b)` — do **not**
   use `np.linalg.inv`. TS: assemble the system and call the provided `solve()`.
2. Implement `predict(X, w)` / `predict(X, w)`: `ŷ = X w` (X already has the bias
   column).
3. Implement `mse_loss(X, y, w)` / `mseLoss(X, y, w)`: mean of the squared
   residuals.
4. Implement `gradient_step(X, y, w, lr)` / `gradientStep(...)`: compute
   `grad = (2/N) · Xᵀ(Xw - y)` and return `w - lr · grad` (return a new vector; do
   not mutate the input).

**Acceptance:**

- Gradient descent converges to the normal-equation weights:
  `||w_gd - w_normal|| < 0.1` after training.
- MSE decreases **monotonically** over the first 30 epochs.
- `R² > 0.9` for the fitted model.

---

### Task 2 🔴 — Bias–variance, cross-validation, and ridge

**Goal:** Reproduce the classic overfitting U-curve, then use ridge regularisation
to tame a deliberately over-flexible model.

**Files:**

- `py/02_bias_variance.py`
- `ts/02-bias-variance.ts`

**Steps:**

1. Implement `kfold_indices(n, k)` / `kfoldIndices(n, k)`: shuffle `0..n-1` with the
   provided seeded RNG, split into `k` near-equal folds, return the list of index
   arrays.
2. Implement `ridge_fit(Phi, y, lam)` / `ridgeFit(Phi, y, lam)`: solve
   `(ΦᵀΦ + λR) w = Φᵀy` where `R = I` but `R[0,0] = 0` (**do not regularise the
   intercept**). `lam = 0` must give ordinary least squares. Use the solver — never
   invert.
3. Implement `cv_score(x, y, degree, lam)` / `cvScore(...)`: k-fold CV mean MSE —
   for each fold, train on the other folds (build poly features on the train `x`,
   `ridge_fit`), score MSE on the held-out fold, average.

**Acceptance:**

- The CV-optimal degree is **between 2 and 6** (not the max degree) — CV bottoms out
  mid-range, proving it detects overfitting.
- At degree 12, plain (`λ=0`) **train MSE ≪ CV MSE** (the overfitting gap).
- At degree 12, **ridge (`λ>0`) reduces both `||w||` and CV MSE** versus `λ=0`.

---

### Task 3 🟡 — Logistic regression with gradient descent + L2

**Goal:** Train a binary classifier on two Gaussian blobs; add L2 and watch the
weight norm shrink.

**Files:**

- `py/03_logistic_regression.py`
- `ts/03-logistic-regression.ts`

**Steps:**

1. Implement `sigmoid(z)` / `sigmoid(z)`: `1 / (1 + e^{-z})`, element-wise, with `z`
   clamped to `[-500, 500]` to avoid overflow.
2. Implement `bce_loss(p, y)` / `bceLoss(p, y)`: mean binary cross-entropy, with `p`
   clipped to `[1e-12, 1 - 1e-12]`.
3. Implement `predict_proba(X)` / `predictProba(X)`: `σ(X w)`.
4. Implement `gradient_step(X, y)` / `gradientStep(X, y)`: `grad = Xᵀ(p - y)/N`,
   plus the L2 term `(λ/N)·w` with the **bias entry zeroed**, then `w -= lr·grad`.
   Return the (pre-update) BCE loss.

**Acceptance:**

- Train accuracy **≥ 0.95** on the (separable) data.
- BCE loss decreases **monotonically** over the first 30 epochs.
- Larger `λ` yields a **smaller** `||w||` (the L2 sweep prints strictly decreasing
  weight norms).

---

### Task 4 🟢 — ROC/AUC and k-means from scratch

**Goal:** Build ranking metrics (ROC/AUC) and a clustering algorithm (k-means) with
no libraries, then sanity-check them.

**Files:**

- `py/04_roc_kmeans.py`
- `ts/04-roc-kmeans.ts`

**Steps:**

_Part A — ROC / AUC:_

1. Implement `roc_curve(scores, labels)` / `rocCurve(scores, labels)`: sort by score
   descending; walking the order, increment TP on each positive and FP on each
   negative; after each step record `(FPR = FP/N⁻, TPR = TP/P)`. The curve starts at
   `(0, 0)` and ends at `(1, 1)`.
2. Implement `auc(fpr, tpr)`: trapezoidal area under the curve.

_Part B — k-means (Lloyd):_

3. Implement `assign_clusters(X, centroids)` / `assignClusters(...)`: each point →
   index of its nearest centroid by squared L2 distance.
4. Implement `update_centroids(X, assignments, k)` / `updateCentroids(...)`: each
   centroid → mean of its assigned points.
5. Implement `inertia(X, centroids, assignments)`: within-cluster sum of squared
   distances.

**Acceptance:**

- AUC of a **perfect** ranker `== 1.0`, a **reversed** ranker `== 0.0`, a **random**
  ranker `≈ 0.5` (±0.15).
- k-means **inertia is non-increasing** on every iteration.
- k-means **recovers the 3 blobs**: each true blob is dominated (≥90%) by one
  cluster id, and the three dominant ids are distinct.

---

## Done when

- [ ] `01_linear_regression` / `01-linear-regression` prints normal-equation and GD
      weights that match, monotone MSE, and `R² > 0.9`.
- [ ] `02_bias_variance` / `02-bias-variance` prints the train-vs-CV U-curve, a
      CV-optimal degree in [2, 6], the degree-12 overfitting gap, and ridge lowering
      both `||w||` and CV MSE.
- [ ] `03_logistic_regression` / `03-logistic-regression` reaches ≥ 95% train
      accuracy with monotone BCE loss, and shows `||w||` shrinking as `λ` grows.
- [ ] `04_roc_kmeans` / `04-roc-kmeans` prints AUC = 1.0 / 0.0 / ≈0.5 for the three
      rankers and recovers 3 distinct k-means clusters with non-increasing inertia.

Each file prints its own **Acceptance** checklist at the end — every box should read
`[x]` and the file should say "All acceptance checks passed."

---

## Going deeper

- **The Elements of Statistical Learning** (Hastie, Tibshirani, Friedman) — the
  reference for regression, bias–variance, and regularisation:
  <https://hastie.su.domains/ElemStatLearn/>
- **Andrew Ng's ML course notes** — clean derivations of linear/logistic regression
  and gradient descent: <https://cs229.stanford.edu/notes2022fall/main_notes.pdf>
- **scikit-learn user guide** — how the production versions of everything here work
  (Ridge, LogisticRegression, `roc_auc_score`, KMeans):
  <https://scikit-learn.org/stable/user_guide.html>
- **StatQuest (Josh Starmer)** — intuitive video explainers for ROC/AUC, bias–
  variance, and cross-validation: <https://www.youtube.com/c/joshstarmer>
- **k-means++** — the smarter initialisation the harness uses, from Arthur &
  Vassilvitskii: <https://theory.stanford.edu/~sergei/papers/kMeansPP-soda.pdf>

---

## Environment

No provider, network, or LLM — these exercises are fully offline and deterministic
(fixed seeds, synthetic data generated in code). No new environment variables.

**Python:** numpy only (a base dependency — no extra needed).

```bash
uv run python modules/01b-ml-foundations/py/01_linear_regression.py
```

**TypeScript:** plain arrays only (no npm math libraries). Build nothing; just run.

```bash
pnpm tsx modules/01b-ml-foundations/ts/01-linear-regression.ts
```
