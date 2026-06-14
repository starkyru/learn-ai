/**
 * Task 3 🟡 — Evaluation: precision, recall, F1, confusion matrix.
 *
 * What you'll learn:
 *   - Why accuracy alone is misleading on multi-class problems
 *   - Precision vs. recall: the "don't cry wolf" vs. "miss nothing" trade-off
 *   - F1: the harmonic mean that balances precision and recall
 *   - Confusion matrix: WHERE your classifier goes wrong
 *   - How to compare the LLM classifier vs. the kNN embedding classifier
 *
 * Key intuition:
 *   Precision = of everything I called "sports", how many actually were?
 *   Recall    = of all the "sports" items, how many did I find?
 *   F1        = 2 * P * R / (P + R)   — the harmonic mean, punishes extremes
 *
 * Note: unlike Python, we implement ALL metrics by hand (no sklearn in JS).
 *
 * How to run:
 *   pnpm tsx modules/08-classification/ts/03-evaluation.ts
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { getProvider } from "@learn-ai/llm-core";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const LABELS = ["technology", "science", "business", "sports", "health", "politics"];

interface DataItem {
  id: number;
  text: string;
  label: string;
}

function loadDataset(): DataItem[] {
  const path = join(__dirname, "../data/texts.json");
  return JSON.parse(readFileSync(path, "utf-8")) as DataItem[];
}

// ---------------------------------------------------------------------------
// Metrics — implement from scratch
// ---------------------------------------------------------------------------

/**
 * Overall accuracy = correct / total.
 *
 * TODO: implement.
 */
export function accuracy(yTrue: string[], yPred: string[]): number {
  // TODO: implement
  throw new Error("TODO: implement accuracy()");
}

/**
 * Per-class precision, recall, and F1 for a single label.
 *
 * Definitions:
 *   TP = predicted `label` AND actually `label`
 *   FP = predicted `label` BUT actually something else
 *   FN = actually `label`  BUT predicted something else
 *
 *   Precision = TP / (TP + FP)
 *   Recall    = TP / (TP + FN)
 *   F1        = 2 * P * R / (P + R)
 *
 * Edge cases: if any denominator is 0, return 0.0 for that metric.
 *
 * TODO: implement.
 */
export function precisionRecallF1(
  yTrue: string[],
  yPred: string[],
  label: string,
): { precision: number; recall: number; f1: number } {
  // TODO: count TP, FP, FN then compute the metrics
  throw new Error("TODO: implement precisionRecallF1()");
}

/**
 * Macro-averaged F1: average the per-class F1 scores.
 *
 * "Macro" means every class counts equally regardless of size.
 *
 * TODO: call precisionRecallF1() for each label, collect f1 values, return mean.
 */
export function macroF1(yTrue: string[], yPred: string[], labels: string[]): number {
  // TODO: implement
  throw new Error("TODO: implement macroF1()");
}

/**
 * Build a confusion matrix as a 2-D array.
 *
 * matrix[i][j] = count of samples where true label is labels[i]
 *                and predicted label is labels[j].
 *
 * Diagonal = correct predictions.
 * Off-diagonal = misclassifications.
 *
 * TODO:
 *   1. Create an n×n array of zeros.
 *   2. Build a label → index map.
 *   3. For each (true, pred) pair, increment matrix[trueIdx][predIdx].
 */
export function confusionMatrix(
  yTrue: string[],
  yPred: string[],
  labels: string[],
): number[][] {
  // TODO: implement
  throw new Error("TODO: implement confusionMatrix()");
}

function printConfusionMatrix(matrix: number[][], labels: string[]): void {
  const short = labels.map((l) => l.slice(0, 4).padStart(4));
  console.log("        " + short.join("  "));
  for (let i = 0; i < labels.length; i++) {
    const row = matrix[i].map((v) => String(v).padStart(4)).join("  ");
    console.log(`  ${labels[i].slice(0, 4).padStart(4)}  ${row}`);
  }
}

function printMetricsTable(
  yTrue: string[],
  yPred: string[],
  labels: string[],
  title: string,
): number {
  console.log(`\n${title}`);
  console.log(`  ${"Label".padEnd(12)} ${"Prec".padStart(6)} ${"Rec".padStart(6)} ${"F1".padStart(6)}  ${"Support".padStart(7)}`);
  console.log("  " + "-".repeat(50));
  for (const label of labels) {
    const { precision, recall, f1 } = precisionRecallF1(yTrue, yPred, label);
    const support = yTrue.filter((t) => t === label).length;
    console.log(
      `  ${label.padEnd(12)} ${(precision * 100).toFixed(1).padStart(5)}% ${(recall * 100).toFixed(1).padStart(5)}% ${(f1 * 100).toFixed(1).padStart(5)}%  ${String(support).padStart(7)}`,
    );
  }
  const acc = accuracy(yTrue, yPred);
  const mf1 = macroF1(yTrue, yPred, labels);
  console.log("  " + "-".repeat(50));
  console.log(`  ${"accuracy".padEnd(12)} ${(acc * 100).toFixed(1).padStart(5)}%`);
  console.log(`  ${"macro F1".padEnd(12)} ${(mf1 * 100).toFixed(1).padStart(5)}%`);
  return mf1;
}

// ---------------------------------------------------------------------------
// Linear algebra helpers (needed for kNN below)
// ---------------------------------------------------------------------------

function dot(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += a[i] * b[i];
  return sum;
}

function norm(x: number[]): number {
  return Math.sqrt(x.reduce((s, v) => s + v * v, 0));
}

function cosineSimilarity(a: number[], b: number[]): number {
  const n = norm(a) * norm(b);
  return n === 0 ? 0 : dot(a, b) / n;
}

// ---------------------------------------------------------------------------
// Stratified train/test split (deterministic)
// ---------------------------------------------------------------------------

function trainTestSplit(
  X: number[][],
  y: string[],
  testFraction = 0.2,
): { XTrain: number[][]; XTest: number[][]; yTrain: string[]; yTest: string[] } {
  // Group indices by label
  const groups: Record<string, number[]> = {};
  for (let i = 0; i < y.length; i++) {
    (groups[y[i]] ??= []).push(i);
  }

  const trainIdx: number[] = [];
  const testIdx: number[] = [];
  for (const indices of Object.values(groups)) {
    const nTest = Math.round(indices.length * testFraction);
    testIdx.push(...indices.slice(0, nTest));
    trainIdx.push(...indices.slice(nTest));
  }

  return {
    XTrain: trainIdx.map((i) => X[i]),
    XTest: testIdx.map((i) => X[i]),
    yTrain: trainIdx.map((i) => y[i]),
    yTest: testIdx.map((i) => y[i]),
  };
}

// ---------------------------------------------------------------------------
// kNN classifier (from Task 2 — inline here to keep this file self-contained)
// ---------------------------------------------------------------------------

class KNNClassifier {
  private trainVectors: number[][] = [];
  private trainLabels: string[] = [];

  constructor(private k: number = 5) {}

  fit(X: number[][], y: string[]): this {
    this.trainVectors = X;
    this.trainLabels = y;
    return this;
  }

  predictOne(x: number[]): string {
    const sims = this.trainVectors.map((v, i) => ({
      sim: cosineSimilarity(x, v),
      label: this.trainLabels[i],
    }));
    sims.sort((a, b) => b.sim - a.sim);
    const top = sims.slice(0, this.k);
    const counts: Record<string, number> = {};
    for (const { label } of top) counts[label] = (counts[label] ?? 0) + 1;
    return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0];
  }

  predict(X: number[][]): string[] {
    return X.map((x) => this.predictOne(x));
  }
}

// ---------------------------------------------------------------------------
// LLM few-shot classifier (from Task 1 — inline here)
// ---------------------------------------------------------------------------

const FEW_SHOT_EXAMPLES: [string, string][] = [
  ["NASA launched a new space telescope to study distant galaxies.", "science"],
  ["The central bank cut interest rates amid recession fears.", "business"],
  ["The striker scored a hat-trick in the cup final.", "sports"],
  ["Eating more fibre reduces cholesterol and improves gut health.", "health"],
  ["The new legislation restricts campaign finance donations.", "politics"],
  ["Engineers demonstrated a chip that runs on ambient light alone.", "technology"],
];

function parseLabel(raw: string, validLabels: string[]): string | null {
  const lower = raw.toLowerCase().trim();
  for (const label of validLabels) {
    if (lower.includes(label)) return label;
  }
  return null;
}

async function llmClassify(
  text: string,
  provider: ReturnType<typeof getProvider>,
  labels: string[],
): Promise<string | null> {
  /**
   * TODO: build a few-shot prompt and call provider.chat().
   *
   * Example format:
   *   Classify the text into one of: technology, science, business, sports, health, politics
   *   Reply with ONLY the label.
   *
   *   Text: <example>
   *   Label: <label>
   *   ... (repeat for all examples)
   *
   *   Text: <query>
   *   Label:
   */
  throw new Error("TODO: implement llmClassify()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name}`);

  const dataset = loadDataset();
  const texts = dataset.map((d) => d.text);
  const allLabels = dataset.map((d) => d.label);

  // ── Embed all texts ───────────────────────────────────────────────────────
  console.log("\n[1/3] Embedding all texts...");
  const BATCH = 32;
  const allVectors: number[][] = [];
  for (let i = 0; i < texts.length; i += BATCH) {
    const result = await provider.embed(texts.slice(i, i + BATCH));
    allVectors.push(...result.vectors);
  }

  // ── Train/test split ──────────────────────────────────────────────────────
  const { XTrain, XTest, yTrain, yTest } = trainTestSplit(allVectors, allLabels);
  const testTexts = yTest.map((_, i) => {
    // Recover test texts from the same split
    const testIndices: number[] = [];
    const groups: Record<string, number[]> = {};
    for (let j = 0; j < allLabels.length; j++) {
      (groups[allLabels[j]] ??= []).push(j);
    }
    for (const indices of Object.values(groups)) {
      const nTest = Math.round(indices.length * 0.2);
      testIndices.push(...indices.slice(0, nTest));
    }
    return texts[testIndices[i]];
  });

  // ── kNN classifier ────────────────────────────────────────────────────────
  console.log("\n[2/3] Training kNN + evaluating on test set...");
  const knn = new KNNClassifier(5);
  knn.fit(XTrain, yTrain);
  const knnPreds = knn.predict(XTest);
  const knnF1 = printMetricsTable(yTest, knnPreds, LABELS, "kNN (cosine, k=5):");

  console.log("\n  Confusion matrix (kNN):");
  printConfusionMatrix(confusionMatrix(yTest, knnPreds, LABELS), LABELS);

  // ── LLM classifier on same test set ──────────────────────────────────────
  console.log(`\n[3/3] Running LLM few-shot on ${testTexts.length} test samples...`);
  console.log("  (One API call per sample — may be slow)\n");
  const llmRaw: (string | null)[] = [];
  for (let i = 0; i < testTexts.length; i++) {
    const pred = await llmClassify(testTexts[i], provider, LABELS);
    llmRaw.push(pred);
    process.stdout.write(`  ${i + 1}/${testTexts.length}: ${pred ?? "???"}\n`);
  }
  const llmPreds = llmRaw.map((p) => p ?? "__unknown__");
  const nullCount = llmRaw.filter((p) => p === null).length;
  if (nullCount > 0) console.log(`\n  Warning: ${nullCount} LLM response(s) could not be parsed.`);

  const llmF1 = printMetricsTable(yTest, llmPreds, LABELS, "LLM few-shot:");

  console.log("\n  Confusion matrix (LLM few-shot):");
  printConfusionMatrix(confusionMatrix(yTest, llmPreds, LABELS), LABELS);

  // ── Comparison ────────────────────────────────────────────────────────────
  console.log("\n" + "=".repeat(55));
  console.log("COMPARISON — macro F1 on the same test set");
  console.log("=".repeat(55));
  console.log(`  kNN (embeddings, cosine)  : ${(knnF1 * 100).toFixed(1)}%`);
  console.log(`  LLM few-shot              : ${(llmF1 * 100).toFixed(1)}%`);
  console.log();
  console.log("  Which wins? What's the cost trade-off?");
  console.log("  LLM: no training data needed, but slow and costly per call.");
  console.log("  kNN: needs labelled data, but sub-millisecond at inference time.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
