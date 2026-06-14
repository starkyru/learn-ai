/**
 * Task 6 🟡 — Distillation: teacher LLM labels a dataset, student learns from it.
 *
 * Knowledge distillation is a technique for making a small, cheap model behave
 * like a big, expensive one — at least on a narrow task. The key idea:
 *
 *   1. Teacher phase: use a powerful LLM (the "teacher") to label a dataset.
 *      Instead of human annotation, we call the big model for each example.
 *   2. Student phase: train a small, fast classifier on those labels.
 *      Here we use embeddings + kNN — no GPU needed.
 *   3. Evaluation: compare the student's accuracy and speed to calling the
 *      teacher on every query.
 *
 * This approach is used in production when:
 *   - LLM inference costs are too high at scale (student is 100–1000× cheaper).
 *   - Latency matters (embedding + kNN is < 1 ms; LLM is 500–2000 ms).
 *   - The task is narrow enough that a small model can learn it.
 *
 * What you'll learn:
 *   - Using an LLM to generate labels (synthetic annotation)
 *   - Embedding-based classification (reusing ideas from module 08)
 *   - Measuring accuracy, cost-per-query, and latency tradeoffs
 *   - When distillation fails (out-of-distribution inputs, ambiguous labels)
 *
 * How to run:
 *   pnpm tsx modules/13-fine-tuning/ts/06-distillation.ts
 */

import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Dataset: sentiment classification (positive / negative / neutral)
// ---------------------------------------------------------------------------

const UNLABELLED_TEXTS: string[] = [
  "This product exceeded all my expectations — absolutely love it!",
  "Terrible quality, broke after two days. Complete waste of money.",
  "It arrived on time and works as described. Nothing special.",
  "Best purchase I've made this year. Highly recommend!",
  "The instructions were confusing but the product itself is fine.",
  "Awful customer service. Never buying from here again.",
  "Decent value for the price. Does what it says on the tin.",
  "Mind-blowing performance. Changed how I work every day.",
  "Packaging was damaged but the item inside was okay.",
  "Total disappointment. Not at all what was advertised.",
  "Solid product, nothing groundbreaking. Gets the job done.",
  "Returned it immediately. The worst thing I've ever bought.",
  "Pretty good overall. Minor issues but I'm satisfied.",
  "Fantastic! Exceeded expectations in every way possible.",
  "Average product. You get what you pay for, I suppose.",
  "Incredibly frustrating to set up. Manual is incomprehensible.",
  "Works perfectly. Very happy with this purchase.",
  "Not worth the money at all. Save yourself the hassle.",
  "Good enough for what I needed. Would buy again.",
  "Outstanding quality. Five stars without hesitation.",
];

const TEST_SET: Array<[string, string]> = [
  ["Amazing product, life-changing!", "positive"],
  ["Complete rubbish, deeply disappointed.", "negative"],
  ["It does the job, nothing more.", "neutral"],
  ["Fantastic value and great quality!", "positive"],
  ["Broke on first use. Terrible.", "negative"],
  ["Acceptable, but not impressive.", "neutral"],
  ["Absolutely love this — worth every penny.", "positive"],
  ["Disappointing and overpriced.", "negative"],
  ["Fine for everyday use.", "neutral"],
  ["The best in its category, no contest.", "positive"],
];

const LABELS = ["positive", "negative", "neutral"] as const;
type Label = (typeof LABELS)[number];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LabelledExample {
  text: string;
  label: Label;
}

interface StudentClassifier {
  trainEmbeddings: number[][];
  trainLabels: string[];
  method: "knn";
  k: number;
}

interface EvalResults {
  studentAccuracy: number;
  teacherAccuracy: number;
  studentLatencyMs: number;
  teacherLatencyMs: number;
  studentPredictions: string[];
  teacherPredictions: string[];
}

// ---------------------------------------------------------------------------
// Phase 1 — Teacher labelling
// ---------------------------------------------------------------------------

/**
 * Use the provider (teacher LLM) to label each text as positive, negative,
 * or neutral.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. For each text, call provider.chat() with:
 *        messages: [
 *          { role: "system", content: "You are a sentiment classifier. Reply
 *            with exactly one word: positive, negative, or neutral. Nothing else." },
 *          { role: "user", content: text },
 *        ]
 *        options: { maxTokens: 5, temperature: 0 }
 *   2. Parse result.text: strip whitespace, lowercase.
 *   3. If the response is not in LABELS, default to "neutral".
 *   4. Return a string[] of labels, one per input text.
 *
 * Note: sequential calls are fine for this small dataset.
 */
async function llmLabel(
  texts: string[],
  provider: ReturnType<typeof getProvider>,
): Promise<string[]> {
  // TODO: implement llmLabel
  throw new Error("TODO: implement llmLabel()");
}

// ---------------------------------------------------------------------------
// Phase 2 — Student training
// ---------------------------------------------------------------------------

/**
 * Embed all labelled examples and build a kNN student classifier.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Extract texts and labels from `labelled`.
 *   2. Embed all texts: const result = await provider.embed(texts).
 *   3. Return {
 *        trainEmbeddings: result.vectors,
 *        trainLabels: labels,
 *        method: "knn",
 *        k: 3,
 *      } as StudentClassifier.
 */
async function trainStudent(
  labelled: LabelledExample[],
  provider: ReturnType<typeof getProvider>,
): Promise<StudentClassifier> {
  // TODO: implement trainStudent
  throw new Error("TODO: implement trainStudent()");
}

// ---------------------------------------------------------------------------
// Phase 2 continued — Student inference
// ---------------------------------------------------------------------------

/** Cosine similarity between two equal-length vectors. */
function cosineSimilarity(a: number[], b: number[]): number {
  const dot = a.reduce((s, v, i) => s + v * b[i], 0);
  const normA = Math.sqrt(a.reduce((s, v) => s + v * v, 0));
  const normB = Math.sqrt(b.reduce((s, v) => s + v * v, 0));
  if (normA === 0 || normB === 0) return 0;
  return dot / (normA * normB);
}

/**
 * Predict the label for an already-embedded text using the student classifier.
 *
 * TODO: implement this function.
 *
 * kNN algorithm:
 *   1. Compute cosineSimilarity(textEmbedding, e) for every training embedding.
 *   2. Sort by similarity descending.
 *   3. Take the top-k labels.
 *   4. Return the most common label among top-k.
 *      Tie-break: first in LABELS order (positive > negative > neutral).
 */
function studentPredict(textEmbedding: number[], student: StudentClassifier): string {
  // TODO: implement studentPredict
  throw new Error("TODO: implement studentPredict()");
}

// ---------------------------------------------------------------------------
// Phase 3 — Evaluation
// ---------------------------------------------------------------------------

/**
 * Compare the student classifier against the teacher LLM on the test set.
 *
 * Measures:
 *   - Student accuracy (fraction correct)
 *   - Teacher accuracy (same metric using llmLabel)
 *   - Student latency per query (embed + kNN predict)
 *   - Teacher latency per query (one LLM chat call)
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Split testSet into texts and goldLabels.
 *
 *   2. [Student] Embed all test texts at once, then call studentPredict for each.
 *      Time the entire embed + predict loop; compute per-query latency.
 *      Compute accuracy vs goldLabels.
 *
 *   3. [Teacher] Call llmLabel(texts, provider) and time it.
 *      Compute accuracy vs goldLabels.
 *
 *   4. Return an EvalResults object.
 */
async function evaluate(
  testSet: Array<[string, string]>,
  student: StudentClassifier,
  provider: ReturnType<typeof getProvider>,
): Promise<EvalResults> {
  // TODO: implement evaluate
  throw new Error("TODO: implement evaluate()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(
    `\nProvider : ${provider.name}  |  Chat: ${provider.chatModel}  |  Embed: ${provider.embedModel}\n`,
  );

  // Phase 1: teacher labels the unlabelled training data
  console.log(`Phase 1: Teacher labelling ${UNLABELLED_TEXTS.length} examples...`);
  const t0 = performance.now();
  const labels = await llmLabel(UNLABELLED_TEXTS, provider);
  const labelTimeMs = performance.now() - t0;
  const labelled: LabelledExample[] = UNLABELLED_TEXTS.map((text, i) => ({
    text,
    label: labels[i] as Label,
  }));

  console.log(
    `  Done in ${(labelTimeMs / 1000).toFixed(1)}s  (${(labelTimeMs / labels.length).toFixed(0)} ms/example)`,
  );
  const labelCounts: Record<string, number> = {};
  for (const l of labels) labelCounts[l] = (labelCounts[l] ?? 0) + 1;
  console.log(`  Label distribution: ${JSON.stringify(labelCounts)}`);
  console.log();

  // Phase 2: train student on teacher-labelled data
  console.log(`Phase 2: Training student classifier on ${labelled.length} labelled examples...`);
  const student = await trainStudent(labelled, provider);
  console.log(
    `  Student trained: ${student.trainEmbeddings.length} training points, ` +
      `method=${student.method}, k=${student.k}`,
  );
  console.log();

  // Phase 3: evaluate both on the held-out test set
  console.log(`Phase 3: Evaluating student vs teacher on ${TEST_SET.length} test examples...\n`);
  const results = await evaluate(TEST_SET, student, provider);

  const col1 = (s: string) => s.padEnd(30);
  const col2 = (s: string) => s.padStart(12);
  console.log(`${col1("Metric")} ${col2("Student")} ${col2("Teacher")}`);
  console.log("-".repeat(56));
  console.log(
    `${col1("Accuracy")} ${col2((results.studentAccuracy * 100).toFixed(1) + "%")} ${col2((results.teacherAccuracy * 100).toFixed(1) + "%")}`,
  );
  console.log(
    `${col1("Latency per query (ms)")} ${col2(results.studentLatencyMs.toFixed(1))} ${col2(results.teacherLatencyMs.toFixed(1))}`,
  );
  const speedup = results.teacherLatencyMs / Math.max(results.studentLatencyMs, 0.01);
  console.log(`\nStudent is ${speedup.toFixed(0)}× faster per query than the teacher.`);
  console.log();

  // Per-example breakdown
  console.log("Per-example breakdown (first 5):");
  const texts = TEST_SET.map(([t]) => t);
  const gold = TEST_SET.map(([, g]) => g);
  for (let i = 0; i < Math.min(5, TEST_SET.length); i++) {
    const sPred = results.studentPredictions[i];
    const tPred = results.teacherPredictions[i];
    const sOk = sPred === gold[i] ? "✓" : "✗";
    const tOk = tPred === gold[i] ? "✓" : "✗";
    console.log(`  [${i + 1}] text=${JSON.stringify(texts[i].slice(0, 40))}`);
    console.log(
      `       gold=${gold[i].padEnd(10)}  student=${sPred} ${sOk}  teacher=${tPred} ${tOk}`,
    );
  }

  console.log(
    "\nKey insights:",
    "\n  1. The teacher labels training data once — at annotation time, not inference time.",
    "\n  2. The student (embed + kNN) is orders of magnitude faster per query.",
    "\n  3. Accuracy gap reveals how much the student 'distills' from the teacher.",
    "\n  4. For narrow tasks (sentiment), the student often matches teacher accuracy.",
    "\n  5. Distillation fails when inputs are far from the training distribution.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
