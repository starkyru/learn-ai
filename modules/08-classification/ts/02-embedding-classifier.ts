/**
 * Task 2 🟡 — Embeddings + hand-rolled kNN classifier.
 *
 * What you'll learn:
 *   - How to turn text into features via embeddings, then classify in vector space
 *   - Why k-Nearest Neighbours is a natural fit for embedding-based classification
 *   - How train/test split prevents you from measuring what you memorised
 *   - The trade-off: no sklearn in JS, so we implement kNN from scratch
 *
 * The pipeline:
 *   text → embed → float vector → kNN → label
 *
 * Key insight: once you have vectors, any distance-based algorithm works.
 * kNN is the simplest: "what label do most of my k nearest neighbours have?"
 *
 * Note: scikit-learn has no JavaScript equivalent. We implement kNN by hand,
 * which is good practice — and the Python file (02_embedding_classifier.py)
 * also provides a hand-rolled kNN so both are comparable.
 *
 * How to run:
 *   pnpm tsx modules/08-classification/ts/02-embedding-classifier.ts
 */

import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { getProvider } from "@learn-ai/llm-core";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ---------------------------------------------------------------------------
// Dataset helpers
// ---------------------------------------------------------------------------

const LABELS = ["technology", "science", "business", "sports", "health", "politics"] as const;
type Label = (typeof LABELS)[number];

interface DataItem {
  id: number;
  text: string;
  label: Label;
}

function loadDataset(): DataItem[] {
  const path = join(__dirname, "../data/texts.json");
  return JSON.parse(readFileSync(path, "utf-8")) as DataItem[];
}

// ---------------------------------------------------------------------------
// Linear algebra helpers (plain arrays — no external math library)
// ---------------------------------------------------------------------------

/**
 * Dot product of two equal-length vectors.
 *
 * TODO: return sum of a[i] * b[i] for all i.
 */
function dot(a: number[], b: number[]): number {
  // TODO: implement
  throw new Error("TODO: implement dot()");
}

/**
 * L2 norm (magnitude) of a vector.
 *
 * TODO: return sqrt(sum of x[i]^2 for all i).
 */
function norm(x: number[]): number {
  // TODO: implement
  throw new Error("TODO: implement norm()");
}

/**
 * Cosine similarity between two vectors.
 *
 * cosine(a, b) = dot(a, b) / (norm(a) * norm(b))
 *
 * TODO: use dot() and norm() above. Guard against zero-magnitude vectors.
 */
function cosineSimilarity(a: number[], b: number[]): number {
  // TODO: implement
  throw new Error("TODO: implement cosineSimilarity()");
}

// ---------------------------------------------------------------------------
// Train/test split
// ---------------------------------------------------------------------------

interface SplitResult {
  XTrain: number[][];
  XTest: number[][];
  yTrain: string[];
  yTest: string[];
}

/**
 * Stratified 80/20 train/test split.
 *
 * "Stratified" means each class gets proportional representation in both
 * train and test splits — important with only 50 samples.
 *
 * TODO:
 *   1. Group indices by label.
 *   2. For each label group, take the last 20% as test and the rest as train.
 *   3. Collect train and test indices, shuffle each (use the seed for reproducibility).
 *   4. Return the split matrices and label arrays.
 *
 * Tip: Math.floor(group.length * 0.2) items go to test.
 */
function trainTestSplit(
  X: number[][],
  y: string[],
  testFraction: number = 0.2,
  seed: number = 42,
): SplitResult {
  // TODO: implement stratified split
  throw new Error("TODO: implement trainTestSplit()");
}

// ---------------------------------------------------------------------------
// kNN classifier
// ---------------------------------------------------------------------------

/**
 * k-Nearest Neighbours classifier using cosine similarity.
 *
 * Implemented from scratch because scikit-learn has no JS equivalent.
 * The Python file (02_embedding_classifier.py) has the same class for parity.
 */
class KNNClassifier {
  private trainVectors: number[][] = [];
  private trainLabels: string[] = [];

  constructor(private k: number = 5) {}

  /**
   * Store the training set. kNN is a lazy learner — no computation at fit time.
   *
   * TODO: store X in this.trainVectors and y in this.trainLabels.
   */
  fit(X: number[][], y: string[]): this {
    // TODO: implement
    throw new Error("TODO: implement KNNClassifier.fit()");
  }

  /**
   * Predict the label for a single vector.
   *
   * TODO:
   *   1. Compute cosineSimilarity(x, trainVec) for every training vector.
   *   2. Find the k indices with the HIGHEST similarity scores.
   *   3. Collect their labels and return the most frequent (majority vote).
   *      Tie-break: return the alphabetically first label.
   *
   * Tip: sort similarities descending, take first k, count with a Map.
   */
  predictOne(x: number[]): string {
    // TODO: implement
    throw new Error("TODO: implement KNNClassifier.predictOne()");
  }

  /** Predict labels for an array of vectors. */
  predict(X: number[][]): string[] {
    return X.map((x) => this.predictOne(x));
  }
}

// ---------------------------------------------------------------------------
// Simple accuracy metric (full metrics suite is in Task 3)
// ---------------------------------------------------------------------------

function accuracy(yTrue: string[], yPred: string[]): number {
  // TODO: count the indices where yTrue and yPred match, then divide by the total length.
  throw new Error("TODO: implement accuracy()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nUsing provider: ${provider.name} (embed model: ${provider.embedModel})`);

  // ── Load dataset ─────────────────────────────────────────────────────────
  const dataset = loadDataset();
  const texts = dataset.map((d) => d.text);
  const labels = dataset.map((d) => d.label);
  console.log(`\nLoaded ${texts.length} samples across ${new Set(labels).size} classes.`);

  // ── Embed all texts ───────────────────────────────────────────────────────
  console.log("\n[1/3] Embedding all texts...");
  // Batch into 32 to be safe with provider limits
  const BATCH = 32;
  const allVectors: number[][] = [];
  for (let i = 0; i < texts.length; i += BATCH) {
    const batch = texts.slice(i, i + BATCH);
    const result = await provider.embed(batch);
    allVectors.push(...result.vectors);
  }
  console.log(
    `  Embedded ${allVectors.length} texts → dimension ${allVectors[0].length}`,
  );

  // ── Train/test split ──────────────────────────────────────────────────────
  console.log("\n[2/3] Splitting into train/test (80/20, stratified)...");
  const { XTrain, XTest, yTrain, yTest } = trainTestSplit(allVectors, labels);
  console.log(`  Train: ${yTrain.length} | Test: ${yTest.length}`);

  // ── kNN classifier ────────────────────────────────────────────────────────
  console.log("\n[3/3] Training kNN classifier (k=5, cosine)...");
  const knn = new KNNClassifier(5);
  knn.fit(XTrain, yTrain);
  const preds = knn.predict(XTest);
  const acc = accuracy(yTest, preds);
  console.log(`  kNN test accuracy: ${(acc * 100).toFixed(1)}%`);

  // Per-class breakdown
  console.log("\n  Per-class results:");
  const classLabels = [...new Set(labels)].sort();
  for (const cls of classLabels) {
    const idx = yTest.map((l, i) => (l === cls ? i : -1)).filter((i) => i >= 0);
    const clsTrue = idx.map((i) => yTest[i]);
    const clsPred = idx.map((i) => preds[i]);
    const clsAcc = accuracy(clsTrue, clsPred);
    console.log(`    ${cls.padEnd(12)} : ${(clsAcc * 100).toFixed(0)}% (n=${idx.length})`);
  }

  console.log(
    "\n  Task 3 (evaluation) will compute precision/recall/F1 and compare methods.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
