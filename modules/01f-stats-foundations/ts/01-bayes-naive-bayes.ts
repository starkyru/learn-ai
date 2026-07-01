/**
 * Task 1 🟡 — Bayes' theorem and a naive Bayes spam classifier.
 *
 * What you'll learn:
 *   - Bayes' theorem as a machine for inverting conditional probabilities
 *   - The base-rate fallacy: why a "95% accurate" test on a rare disease is
 *     usually wrong when it says "positive" (the classic interview trap)
 *   - Multinomial naive Bayes: turning Bayes' rule + a "words are independent
 *     given the class" assumption into a working text classifier
 *   - Laplace (add-one) smoothing and why you must work in log space
 *
 * The math (README derives each step):
 *
 *   Bayes:      P(H | E) = P(E | H) · P(H) / P(E)
 *
 *   Medical test (H = disease, E = positive test):
 *     P(D | +) = prior·sens / ( prior·sens + (1 − prior)·(1 − spec) )
 *     with prior = P(D), sens = P(+ | D), spec = P(− | ¬D).
 *
 *   Naive Bayes (class c, document w₁…wₙ):
 *     log P(c | doc) ∝ log P(c) + Σ_i log P(w_i | c)
 *     P(w | c) = (count(w, c) + 1) / (total_tokens(c) + V)   ← Laplace smoothing
 *
 * You implement bayesPosterior, fitNaiveBayes, and predictLogPosterior.
 * The synthetic spam/ham corpus, the train/test split, argmax prediction,
 * and the report are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/01f-stats-foundations/ts/01-bayes-naive-bayes.ts
 */

const SEED = 42;

// The famous interview numbers: 1% prevalence, 95% sensitivity, 95% specificity.
const PRIOR = 0.01;
const SENSITIVITY = 0.95;
const SPECIFICITY = 0.95;
// Analytic answer, worked by hand: 0.0095 / (0.0095 + 0.0495) = 0.16101...
const ANALYTIC_POSTERIOR = 0.16101694915254236;

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG for reproducible uniforms
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // Numerical Recipes LCG
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296; // uniform in [0, 1)
  };
}

// ---------------------------------------------------------------------------
// Synthetic spam/ham corpus (provided — do not edit)
// ---------------------------------------------------------------------------

const VOCAB = [
  "free",
  "win",
  "cash",
  "offer",
  "click",
  "prize", // spam-flavoured
  "meeting",
  "report",
  "project",
  "lunch",
  "schedule",
  "review", // ham-flavoured
];
const V = VOCAB.length;

// Class-conditional word distributions the corpus is secretly drawn from.
const P_WORD_SPAM = [
  0.2, 0.15, 0.15, 0.12, 0.12, 0.1, 0.04, 0.03, 0.03, 0.02, 0.02, 0.02,
];
const P_WORD_HAM = [
  0.02, 0.02, 0.02, 0.03, 0.03, 0.02, 0.18, 0.15, 0.15, 0.12, 0.14, 0.12,
];

const N_SPAM = 35;
const N_HAM = 45;
const DOC_LEN = 8;
const N_TRAIN = 60; // of the 80 docs; the remaining 20 are held out

/** Draw one index from a categorical distribution via its CDF. */
function sampleCategorical(u: () => number, probs: number[]): number {
  const r = u();
  let cum = 0;
  for (let i = 0; i < probs.length; i++) {
    cum += probs[i];
    if (r < cum) return i;
  }
  return probs.length - 1;
}

interface Corpus {
  trainDocs: number[][];
  trainLabels: number[];
  testDocs: number[][];
  testLabels: number[];
}

/** Generate 80 docs (each a list of DOC_LEN word indices), shuffle, split. Label 1 = spam. */
function makeCorpus(): Corpus {
  const u = makeRng(SEED);
  const docs: number[][] = [];
  const labels: number[] = [];
  for (let i = 0; i < N_SPAM; i++) {
    docs.push(Array.from({ length: DOC_LEN }, () => sampleCategorical(u, P_WORD_SPAM)));
    labels.push(1);
  }
  for (let i = 0; i < N_HAM; i++) {
    docs.push(Array.from({ length: DOC_LEN }, () => sampleCategorical(u, P_WORD_HAM)));
    labels.push(0);
  }
  // Fisher-Yates shuffle with the seeded RNG.
  for (let i = docs.length - 1; i > 0; i--) {
    const j = Math.floor(u() * (i + 1));
    [docs[i], docs[j]] = [docs[j], docs[i]];
    [labels[i], labels[j]] = [labels[j], labels[i]];
  }
  return {
    trainDocs: docs.slice(0, N_TRAIN),
    trainLabels: labels.slice(0, N_TRAIN),
    testDocs: docs.slice(N_TRAIN),
    testLabels: labels.slice(N_TRAIN),
  };
}

/** Render a doc's word indices as readable text (for printing). */
function docToWords(doc: number[]): string {
  return doc.map((w) => VOCAB[w]).join(" ");
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three
// ---------------------------------------------------------------------------

/**
 * P(disease | positive test), by Bayes' theorem.
 *
 * P(D | +) = P(+ | D)·P(D) / P(+)
 * where P(+) sums over both ways to test positive:
 *   a true positive  (has the disease AND the test fires):  prior · sensitivity
 *   a false positive (healthy AND the test misfires):       (1 − prior) · (1 − specificity)
 *
 * TODO: implement.
 *   - Compute the two paths to a positive test (true-positive mass and
 *     false-positive mass) as above.
 *   - Return the true-positive mass divided by their sum.
 */
function bayesPosterior(
  prior: number,
  sensitivity: number,
  specificity: number,
): number {
  // TODO: implement Bayes' theorem for the medical test
  throw new Error("TODO: implement bayesPosterior()");
}

interface NaiveBayesModel {
  /** logPrior[c] = log P(class c); index 0 = ham, 1 = spam. */
  logPrior: number[];
  /** logLik[c][w] = Laplace-smoothed log P(word w | class c); shape 2×V. */
  logLik: number[][];
}

/**
 * Fit a multinomial naive Bayes model. Label 1 = spam, 0 = ham.
 *
 *   logPrior[c] = log(#docs in c / #docs)
 *   logLik[c][w] = log( (count(w, c) + 1) / (total_tokens(c) + V) )   ← Laplace
 *
 * TODO: implement.
 *   1. Count docs per class → log priors (Math.log of the doc fraction).
 *   2. Count word occurrences per class: a 2×V count table over every token
 *      of every doc.
 *   3. Apply Laplace smoothing (add 1 to every count; add V to each class's
 *      token total), take Math.log, and return { logPrior, logLik }.
 */
function fitNaiveBayes(docs: number[][], labels: number[]): NaiveBayesModel {
  // TODO: count docs and words per class, smooth, log, return the model
  throw new Error("TODO: implement fitNaiveBayes()");
}

/**
 * Unnormalised log posterior for each class:
 *
 *   log P(c | doc) ∝ log P(c) + Σ_{w in doc} log P(w | c)
 *
 * Returns [logPosterior(ham), logPosterior(spam)].
 *
 * TODO: implement.
 *   - Start from the model's log priors and, for each class, add up the
 *     model's log-likelihood entries for every token in the doc.
 *   - Sums of logs — never multiply raw probabilities (they underflow).
 */
function predictLogPosterior(model: NaiveBayesModel, doc: number[]): number[] {
  // TODO: log priors + summed per-token log-likelihoods, length 2
  throw new Error("TODO: implement predictLogPosterior()");
}

// ---------------------------------------------------------------------------
// Prediction helpers (provided — use your predictLogPosterior)
// ---------------------------------------------------------------------------

/** Argmax class prediction. */
function predict(model: NaiveBayesModel, doc: number[]): number {
  const scores = predictLogPosterior(model, doc);
  return scores[1] > scores[0] ? 1 : 0;
}

/** Normalise the two log posteriors into probabilities (stable softmax). */
function posteriorProbs(model: NaiveBayesModel, doc: number[]): number[] {
  const logPost = predictLogPosterior(model, doc);
  const max = Math.max(...logPost);
  const p = logPost.map((lp) => Math.exp(lp - max));
  const sum = p[0] + p[1];
  return [p[0] / sum, p[1] / sum];
}

// ---------------------------------------------------------------------------
// Harness (provided — do not edit)
// ---------------------------------------------------------------------------

function main(): void {
  console.log("Task 1 — Bayes' theorem and naive Bayes\n");

  // ── Part A: the medical-test trap ──────────────────────────────────────────
  console.log("[1/2] Part A — Bayes' theorem (the medical-test question)...");
  console.log(`  Disease prevalence : ${(PRIOR * 100).toFixed(0)}%`);
  console.log(
    `  Test sensitivity   : ${(SENSITIVITY * 100).toFixed(0)}%   (P(+ | disease))`,
  );
  console.log(
    `  Test specificity   : ${(SPECIFICITY * 100).toFixed(0)}%   (P(− | healthy))`,
  );
  const posterior = bayesPosterior(PRIOR, SENSITIVITY, SPECIFICITY);
  console.log(`\n  P(disease | positive test) = ${posterior.toFixed(4)}`);
  console.log(`  Analytic value             = ${ANALYTIC_POSTERIOR.toFixed(4)}`);
  console.log("  → A positive result still means you're probably healthy: the 1%");
  console.log("    base rate is swamped by false positives from the healthy 99%.\n");

  // ── Part B: naive Bayes on the spam/ham corpus ─────────────────────────────
  console.log("[2/2] Part B — multinomial naive Bayes on synthetic spam/ham...");
  const { trainDocs, trainLabels, testDocs, testLabels } = makeCorpus();
  console.log(
    `  Corpus: ${trainDocs.length} train docs, ${testDocs.length} test docs, V=${V}`,
  );
  console.log(
    `  Example train doc (${trainLabels[0] ? "spam" : "ham"}): "${docToWords(trainDocs[0])}"`,
  );

  const model = fitNaiveBayes(trainDocs, trainLabels);
  console.log(
    `  log priors: ham=${model.logPrior[0].toFixed(4)}  spam=${model.logPrior[1].toFixed(4)}`,
  );

  let correct = 0;
  for (let i = 0; i < testDocs.length; i++) {
    if (predict(model, testDocs[i]) === testLabels[i]) correct++;
  }
  const accuracy = correct / testDocs.length;
  console.log(
    `  Held-out accuracy: ${accuracy.toFixed(2)}  (${correct}/${testDocs.length})`,
  );

  const obviousSpam = [0, 1, 2, 3, 0, 4, 5, 1]; // "free win cash offer free click prize win"
  const pSpam = posteriorProbs(model, obviousSpam)[1];
  console.log(`  Obvious spam doc "${docToWords(obviousSpam)}"`);
  console.log(`  → P(spam) = ${pSpam.toFixed(4)}`);

  // ── Acceptance checks ──────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okBayes = Math.abs(posterior - ANALYTIC_POSTERIOR) < 0.005;
  const okAcc = accuracy >= 0.9;
  const okSpam = pSpam > 0.9;
  console.log(
    `  [${okBayes ? "x" : " "}] medical-test posterior within ±0.005 of analytic (${posterior.toFixed(4)} vs ${ANALYTIC_POSTERIOR.toFixed(4)})`,
  );
  console.log(
    `  [${okAcc ? "x" : " "}] held-out spam/ham accuracy ≥ 0.9  (got ${accuracy.toFixed(2)})`,
  );
  console.log(
    `  [${okSpam ? "x" : " "}] obvious spam doc gets P(spam) > 0.9  (got ${pSpam.toFixed(4)})`,
  );

  if (okBayes && okAcc && okSpam) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
