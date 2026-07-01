# Module 01e — Trees & Ensembles

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

The course covers linear models (01b) and deep nets (01c) — but nothing
**tree-based**. Decision trees, random forests, and gradient boosting are the
#1 classic-ML interview family and still the default baseline (and frequent
winner) on tabular data. This module fills that gap: you build CART, bagging,
a random forest, and least-squares gradient boosting from the ground up, then
measure — not just recite — the bias–variance decomposition that explains why
ensembles work.

Everything here is **pure numpy (Python) / plain TypeScript (no math
libraries)** — **no sklearn, no xgboost**; that constraint is the point.
Fully **offline** and **deterministic** (fixed seeds, synthetic data generated
in code). No provider, no network, no LLM (Large Language Model). You
implement the pedagogically-core functions; the data generation, harnesses,
splits, and printing are done for you and are runnable the moment you fill the
stubs.

**Prerequisites:** Module 01b (bias–variance, train/test discipline, MSE).

---

## Concepts

### 1. Decision trees (CART) and Gini impurity

A decision tree classifies by asking a sequence of threshold questions
("is `x[0] ≤ 0.8`?") that carve feature space into axis-aligned boxes, each
box predicting one class. Training is **greedy recursive partitioning**
(CART, Classification And Regression Trees): at every node, try every
possible split, keep the best, recurse on the two halves.

"Best" needs a number for how _mixed_ a set of labels is. **Gini impurity**
is the probability that two draws (with replacement) from the node disagree:

```
G(y) = 1 - Σ_c p_c²          (p_c = fraction of class c at the node)

pure node (one class):   G = 1 - 1² = 0
balanced binary (50/50): G = 1 - (0.25 + 0.25) = 0.5   (the binary max)
```

A split sends each point left (`x[j] ≤ t`) or right, producing children of
sizes `n_L`, `n_R`. Its quality is the **weighted child impurity**:

```
G_split = (n_L · G(y_left) + n_R · G(y_right)) / (n_L + n_R)
```

and the **gain** is `G(parent) - G_split` — the same "information gain" idea
as entropy-based trees, just with Gini in place of entropy (they pick nearly
identical splits; Gini skips the `log`). A split is only worth taking if its
gain is positive; when no split has positive gain, the node becomes a leaf
predicting its majority class.

Only **midpoints between consecutive sorted unique feature values** need to be
tried as thresholds — any other threshold produces one of the same partitions.

Left to grow without limits, a tree keeps splitting until every leaf is pure —
it **memorises the training set** (train accuracy → 1.0), noise and all. On
noisy data that memorisation does not transfer: the test accuracy lags far
behind, and the train−test gap is the visible signature of **overfitting**.
`max_depth` and `min_samples_leaf` are the tree's regularisers: a depth-3 tree
can't chase individual noisy points, so its gap shrinks.

### 2. Bagging and random forests

One deep tree is a **low-bias, high-variance** model: re-draw the training set
and you get a very different tree. Averaging is the classic variance killer —
so manufacture many training sets from the one you have.

A **bootstrap sample** draws `n` indices _with replacement_ from `{0…n-1}`.
The chance a given row is never drawn is

```
(1 - 1/n)^n  →  e⁻¹ ≈ 0.368        so ≈ 63.2% of unique rows appear
```

(every bootstrap therefore contains duplicates — you'll print this).
**Bagging** (bootstrap aggregating) trains one deep tree per bootstrap and
majority-votes their predictions. Why it helps: for B estimators each with
variance σ² and pairwise correlation ρ,

```
Var( (1/B) Σ_b f_b )  =  ρσ²  +  (1-ρ)·σ²/B
```

The second term dies as B grows — but the first does **not**. If all your
trees are basically the same tree (ρ high), averaging them barely helps.
Bagged trees _are_ highly correlated: they all greedily grab the same strong
feature for the first split.

The **random forest** trick attacks ρ directly: at _every split_, only a
random subset of `max_features` features may be considered. Trees are forced
to build differently, decorrelating their errors, and the vote gets the full
benefit of averaging. Individually the feature-starved trees are _worse_
(you'll print their scattered accuracies); collectively they beat the single
deep tree.

### 3. Gradient boosting = gradient descent in function space

Bagging builds strong learners **in parallel** and averages away variance.
**Boosting** builds weak learners **in sequence**, each one correcting what
the running model still gets wrong — it drives down bias.

The model after `m` rounds is a sum, with learning rate (shrinkage) `ν`:

```
F_m(x) = F_0 + ν · Σ_{k=1..m} h_k(x),        F_0 = ȳ  (the best constant)
```

Where does "fit the residuals" come from? Treat the model's predictions
`F(x_i)` as free parameters and take the gradient of the squared-error loss:

```
L = ½ Σ_i (y_i - F(x_i))²
-∂L/∂F(x_i) = y_i - F(x_i)      ← the residual IS the negative gradient
```

So each round of "fit a small model `h_m` to the residuals and add a bit of
it" is literally one **gradient-descent step in function space** — that's the
"gradient" in gradient boosting. (Swap the loss and its negative gradient —
log-loss, absolute error — and the same loop gives you the whole GBM
(Gradient Boosting Machine) family; least squares is the case where the
negative gradient happens to equal the plain residual.)

The weak learner here is a **regression stump** — a depth-1 tree: one
threshold, two leaf values, each leaf value the _mean_ of its side's residuals
(the SSE-optimal constant):

```
SSE(t) = Σ_{x≤t} (r - mean_left)² + Σ_{x>t} (r - mean_right)²
```

Because each stump is the best least-squares step, **train MSE never
increases**. Validation MSE traces the familiar U-curve: falling while the
ensemble absorbs signal, rising once it starts absorbing noise. **Early
stopping** — keep the round where validation MSE bottomed out — is boosting's
main regulariser, alongside a small `ν` (smaller steps, more rounds,
better generalisation).

### 4. The bias–variance decomposition, measured empirically

Module 01b stated the decomposition; here you _measure_ it. Train the same
model class on `M` independently resampled training sets and evaluate all `M`
models on one fixed test grid, giving an `(M × N_test)` prediction matrix.
At each test point `x` with clean target `f(x)`:

```
mean prediction:  ȳ̂(x)  = (1/M) Σ_m ŷ_m(x)
bias²(x)        = ( ȳ̂(x) - f(x) )²          (systematically wrong)
variance(x)     = (1/M) Σ_m ( ŷ_m(x) - ȳ̂(x) )²   (scattered across retrains)
```

Average both over the test grid. Against _noisy_ test labels
`y = f(x) + ε`, `ε ~ N(0, σ²)`, the decomposition says:

```
E[(y - ŷ)²] = bias² + variance + σ²     →    bias² + variance ≈ expMSE - σ²
```

and the harness verifies that numerically. The punchline table:

| model             | bias²                                      | variance                                 |
| ----------------- | ------------------------------------------ | ---------------------------------------- |
| stump             | **high** (too rigid to bend with the data) | low                                      |
| deep tree         | ≈ 0                                        | **high** (bends with every noise wiggle) |
| bagged deep trees | ≈ 0                                        | **cut roughly in half**                  |

Bagging leaves bias almost untouched and slashes variance — down to the
correlated floor `ρσ²` from Concept 2, which is exactly why random forests
add feature subsampling on top.

---

## Tasks

### Task 1 🔴 — Decision tree (CART) from scratch

**Goal:** Build a working CART classifier — impurity, exhaustive split
search, recursive growth, prediction — and watch depth control the
overfitting gap on a noisy XOR-quadrant dataset no linear model can solve.

**Files:**

- `py/01_decision_tree.py`
- `ts/01-decision-tree.ts`

**Steps:**

1. Implement `gini(y)` / `gini(y)`: `1 - Σ p_c²` over the class proportions
   (empty input → 0).
2. Implement `best_split(X, y, min_samples_leaf)` / `bestSplit(...)`: scan
   every feature and every midpoint between consecutive sorted unique values;
   return the (feature, threshold) minimising the weighted child Gini, or
   None/null when no split beats the parent impurity.
3. Implement `build_tree(X, y, depth, max_depth, min_samples_leaf)` /
   `buildTree(...)`: recursive growth returning leaf nodes
   (majority-class prediction) and internal nodes (feature, threshold,
   left, right); stop on purity, the depth cap, or a failed split search.
4. Implement `predict_one(node, x)` / `predictOne(node, x)`: walk left on
   `x[feature] <= threshold`, right otherwise, until a leaf.

**Acceptance:**

- `gini` of a pure array = **0.0**; of a balanced binary array = **0.5**.
- The unlimited-depth tree **memorises**: train accuracy ≥ 0.99, and its
  train − test gap is ≥ **0.10** (the overfit gap, printed).
- The depth-3 tree has a **smaller** train − test gap and test accuracy
  ≥ 0.80 — regularisation by depth.

---

### Task 2 🟡 — Bagging → random forest

**Goal:** Turn Task 1's tree into a forest: bootstrap resampling + per-split
feature subsampling + majority vote, and show the ensemble beating both its
average member and a single deep tree.

**Files:**

- `py/02_random_forest.py`
- `ts/02-random-forest.ts`

**Steps:**

1. Implement `bootstrap_sample(rng, n)` / `bootstrapSample(rng, n)`: `n`
   indices drawn from `{0…n-1}` **with replacement**.
2. Implement `train_forest(X, y, rng, n_trees, max_features)` /
   `trainForest(...)`: each tree trains on its own bootstrap resample via the
   **provided** `train_tree` / `trainTree` (which handles the per-split
   random feature subset — pass `max_features` through).
3. Implement `forest_predict(trees, X)` / `forestPredict(trees, X)`: majority
   vote over every tree's predictions (odd tree count → no ties).

**Acceptance:**

- Every bootstrap sample (20 draws, fixed seed) contains **duplicate
  indices**, and the mean unique fraction ≈ **0.632** (printed; accepted in
  [0.55, 0.72]).
- Ensemble test accuracy ≥ the **mean individual** tree accuracy (the
  individual accuracies are printed — they scatter widely).
- Ensemble test accuracy ≥ the **single deep-tree baseline**.

---

### Task 3 🔴 — Gradient boosting (least squares) with stumps

**Goal:** Boost regression stumps on a noisy 1-D sinusoid, watch train MSE
fall monotonically while validation MSE traces the U-curve, and pick the
early-stopping round.

**Files:**

- `py/03_gradient_boosting.py`
- `ts/03-gradient-boosting.ts`

**Steps:**

1. Implement `fit_stump(x, residuals)` / `fitStump(x, residuals)`: the best
   single-threshold regression stump — candidate thresholds are midpoints of
   consecutive sorted unique `x` values; each side predicts its residual
   mean; minimise the two-sided SSE.
2. Implement `boost(x, y, x_val, y_val, n_rounds, lr)` / `boost(...)`:
   `F0 = mean(y)`; each round fit a stump to the residuals `y − F` (the
   negative gradient), add `lr ·` its predictions to the running train/val
   predictions, and record train/val MSE; finish with the early-stopping pick
   `best_round` = the 1-based argmin of the validation-MSE history.

**Acceptance:**

- Train MSE is **non-increasing** over all rounds (each stump is the best
  least-squares step).
- Validation MSE reaches its minimum **before the last round** and is higher
  at the end — the U-curve / overfitting is visible.
- The boosted model at `best_round` has validation MSE **< 0.5 ×** the
  single-stump baseline.

---

### Task 4 🟢 — Empirical bias–variance decomposition

**Goal:** Measure bias² and variance for a stump, a deep tree, and bagged
deep trees by retraining each on M resampled training sets — and confirm
`bias² + variance ≈ expected MSE − σ²` numerically.

**Files:**

- `py/04_bias_variance.py`
- `ts/04-bias-variance.ts`

**Steps:**

1. Implement `empirical_bias_variance(predictions, y_true)` /
   `empiricalBiasVariance(predictions, yTrue)` — the only stub in this task:
   given the `(M × N_test)` prediction matrix and the **clean** targets,
   compute the per-point mean prediction, then
   bias² = mean over test points of (mean_pred − y_true)², and
   variance = mean over test points of the population variance across the M
   models. Everything else (the regression-tree trainer, resampling
   machinery, the three model classes, the table) is provided.

**Acceptance:**

- The **stump** has the highest bias²; the **deep tree** has the highest
  variance (3-row table printed).
- Bagging cuts the deep tree's variance by **> 40%** (the correlated
  remainder is the `ρσ²` floor).
- For all three models, `bias² + variance` matches `expected MSE − σ²`
  within **± 0.03**.

---

## Done when

- [ ] `01_decision_tree` / `01-decision-tree` prints gini 0.0 / 0.5, a deep
      tree with train acc ≥ 0.99 and an overfit gap ≥ 0.10, and a depth-3
      tree with a smaller gap and test acc ≥ 0.80.
- [ ] `02_random_forest` / `02-random-forest` prints bootstrap unique
      fraction ≈ 0.632 with duplicates in every draw, and an ensemble that
      beats both the mean individual tree and the single deep-tree baseline.
- [ ] `03_gradient_boosting` / `03-gradient-boosting` prints monotone train
      MSE, a validation-MSE minimum strictly before the last round, and a
      boosted model at under half the single-stump validation MSE.
- [ ] `04_bias_variance` / `04-bias-variance` prints the 3-row table with the
      stump highest in bias², the deep tree highest in variance, bagging
      cutting variance by > 40%, and the decomposition matching
      expected MSE − σ² within ± 0.03.

Each file prints its own **Acceptance** checklist at the end — every box
should read `[x]` and the file should say "All acceptance checks passed."

---

## Going deeper

- **The Elements of Statistical Learning** (Hastie, Tibshirani, Friedman) —
  chapters 9 (trees), 10 (boosting), 15 (random forests):
  <https://hastie.su.domains/ElemStatLearn/>
- **Greedy Function Approximation: A Gradient Boosting Machine** (Friedman, 2001) — the paper that framed boosting as gradient descent in function
  space: <https://jerryfriedman.su.domains/ftp/trebst.pdf>
- **Random Forests** (Breiman, 2001) — bagging + feature subsampling and the
  correlation argument:
  <https://www.stat.berkeley.edu/~breiman/randomforest2001.pdf>
- **XGBoost: A Scalable Tree Boosting System** (Chen & Guestrin, 2016) — the
  production descendant of Task 3 (second-order boosting, regularised
  objective, clever systems work): <https://arxiv.org/abs/1603.02754>
- **StatQuest (Josh Starmer)** — intuitive video series on decision trees,
  random forests, AdaBoost, and gradient boost:
  <https://www.youtube.com/c/joshstarmer>

---

## Environment

No provider, network, or LLM — these exercises are fully offline and
deterministic (fixed seeds, synthetic data generated in code). No new
environment variables.

**Python:** numpy only (a base dependency — no extra needed).

```bash
uv run python modules/01e-trees-ensembles/py/01_decision_tree.py
```

**TypeScript:** plain arrays only (no npm math libraries). Build nothing; just run.

```bash
pnpm tsx modules/01e-trees-ensembles/ts/01-decision-tree.ts
```
