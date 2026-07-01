/**
 * Task 3 🟡 — RAG evaluation with LLM-as-judge.
 *
 * What you'll learn:
 *   - The three core RAG metrics: faithfulness, context relevance, answer relevance
 *   - How to implement LLM-as-judge: prompt the model to score its own output
 *   - How to run a small evaluation harness over question/answer pairs
 *   - What the scores tell you (and where LLM-as-judge can be fooled)
 *
 * How to run:
 *   pnpm tsx modules/05-rag/ts/03-rag-evaluation.ts
 *
 * Metric definitions (RAGAS-inspired):
 *
 *   Faithfulness (0–1):
 *     Is every claim in the answer supported by the retrieved context?
 *     Score = (# claims supported by context) / (# claims in answer).
 *
 *   Context relevance (0–1):
 *     How much of the retrieved context is actually needed to answer the question?
 *     Score = (# relevant sentences in context) / (# sentences in context).
 *
 *   Answer relevance (0–1):
 *     Does the answer actually address the question asked?
 *     Score = average cosine similarity of answer to question across
 *     N synthetic questions generated from the answer.
 *     (Here we simplify: prompt the LLM for a direct 0–10 score.)
 */

import { getProvider, type ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EvalCase {
  question: string;
  answer: string;         // the RAG answer to evaluate
  context: string[];      // the retrieved chunks that were given to the LLM
}

interface EvalScores {
  faithfulness: number;      // 0–1
  contextRelevance: number;  // 0–1
  answerRelevance: number;   // 0–1
}

// ---------------------------------------------------------------------------
// Evaluation sample (answer these Q/A pairs manually or from task 1 output)
// ---------------------------------------------------------------------------

const EVAL_CASES: EvalCase[] = [
  {
    question: "What is cosine similarity and when should I use it?",
    answer:
      "Cosine similarity measures the angle between two vectors. It equals dot(a,b)/(|a|×|b|). " +
      "Most embedding models normalise their output so it reduces to a dot product. " +
      "Use it for comparing text embeddings; Euclidean distance is less common because it is sensitive to magnitude. " +
      "Cosine values range from -1 (opposite) to 1 (identical) [similarity-metrics-chunk-0].",
    context: [
      "Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude.",
      "Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space, even if they use different words.",
    ],
  },
  {
    question: "How does HNSW work?",
    answer:
      "HNSW builds a multi-layer graph. Search starts at the top coarse layer and descends greedily. " +
      "It achieves O(log n) query time. Recall@10 is typically above 99%. " +
      "It also supports GPU acceleration and requires no training data.",  // last claim is hallucinated
    context: [
      "HNSW (Hierarchical Navigable Small World) is the most popular ANN algorithm. It builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer (coarse) and greedily descends to the bottom layer (fine). Typical recall@10 is above 99% with index build time measured in seconds for millions of vectors.",
    ],
  },
  {
    question: "What is HyDE?",
    answer:
      "HyDE stands for Hypothetical Document Embeddings. It generates a hypothetical answer and embeds that instead of the question.",
    context: [
      "HyDE (Hypothetical Document Embeddings) is a query reformulation technique. Instead of embedding the raw question, generate a hypothetical answer using the LLM, then embed that. The hypothesis lives in the same semantic space as real answers, so retrieval tends to find better matches. HyDE works best when the question and the expected answer have very different surface forms.",
    ],
  },
];

// ---------------------------------------------------------------------------
// Metric 1: Faithfulness
// ---------------------------------------------------------------------------

/**
 * Score how well the answer is grounded in the context.
 *
 * TODO: implement this function.
 *
 * Build a ChatMessage[] asking the model to break the answer into its factual
 * claims and mark each as supported-by-context or not, emitting ONLY a JSON
 * array of {claim, supported} objects (interpolate the joined context and the
 * answer). Call provider.chat(messages, { temperature: 0 }).
 *
 * Parse result.text with JSON.parse inside a try/catch — on failure return 0.5
 * and log a warning so the harness continues. Score = (# supported) / (# total);
 * guard against an empty array.
 */
async function scoreFaithfulness(
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>
): Promise<number> {
  // TODO: implement faithfulness scoring.
  throw new Error("TODO: implement scoreFaithfulness()");
}

// ---------------------------------------------------------------------------
// Metric 2: Context relevance
// ---------------------------------------------------------------------------

/**
 * Score how much of the retrieved context is relevant to the question.
 *
 * TODO: implement this function.
 *
 * Build a ChatMessage[] asking the model to rate, on a 0–10 scale, how relevant
 * the context is for answering the question (10 = perfectly relevant, 0 =
 * irrelevant) and reply with ONLY the integer (interpolate the question and the
 * joined context). Parse the integer from result.text (guard against NaN →
 * return 0) and return it divided by 10.
 */
async function scoreContextRelevance(
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>
): Promise<number> {
  // TODO: implement context relevance scoring.
  throw new Error("TODO: implement scoreContextRelevance()");
}

// ---------------------------------------------------------------------------
// Metric 3: Answer relevance
// ---------------------------------------------------------------------------

/**
 * Score whether the answer addresses the question.
 *
 * TODO: implement this function.
 *
 * Build a ChatMessage[] asking the model to rate, on a 0–10 scale, how well the
 * answer addresses the question (10 = fully, 0 = off-topic) and reply with ONLY
 * the integer (interpolate the question and the answer). Parse the integer from
 * result.text (guard against NaN, like the other scorers) and return it / 10.
 */
async function scoreAnswerRelevance(
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>
): Promise<number> {
  // TODO: implement answer relevance scoring.
  throw new Error("TODO: implement scoreAnswerRelevance()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function evaluateCase(
  evalCase: EvalCase,
  provider: ReturnType<typeof getProvider>
): Promise<EvalScores> {
  const [faithfulness, contextRelevance, answerRelevance] = await Promise.all([
    scoreFaithfulness(evalCase, provider),
    scoreContextRelevance(evalCase, provider),
    scoreAnswerRelevance(evalCase, provider),
  ]);
  return { faithfulness, contextRelevance, answerRelevance };
}

function formatScores(scores: EvalScores): string {
  return (
    `faithfulness=${scores.faithfulness.toFixed(2)}  ` +
    `ctx_relevance=${scores.contextRelevance.toFixed(2)}  ` +
    `ans_relevance=${scores.answerRelevance.toFixed(2)}`
  );
}

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name} (chat model: ${provider.chatModel})\n`);
  console.log("Running RAG evaluation...\n");

  const allScores: EvalScores[] = [];

  for (const ec of EVAL_CASES) {
    console.log(`Q: ${ec.question}`);
    const scores = await evaluateCase(ec, provider);
    allScores.push(scores);
    console.log(`   ${formatScores(scores)}`);

    if (scores.faithfulness < 0.7) {
      console.log("   ⚠ Low faithfulness — the answer may contain hallucinations.");
    }
    if (scores.contextRelevance < 0.5) {
      console.log("   ⚠ Low context relevance — retrieval may have fetched off-topic chunks.");
    }
    console.log();
  }

  // Aggregate
  const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
  console.log("=== Aggregate (mean across test cases) ===");
  console.log(
    `  Faithfulness:       ${avg(allScores.map((s) => s.faithfulness)).toFixed(3)}`
  );
  console.log(
    `  Context relevance:  ${avg(allScores.map((s) => s.contextRelevance)).toFixed(3)}`
  );
  console.log(
    `  Answer relevance:   ${avg(allScores.map((s) => s.answerRelevance)).toFixed(3)}`
  );

  console.log("\nReflection:");
  console.log("  - Which eval case scored lowest on faithfulness? Why?");
  console.log("  - The HNSW answer contains a hallucinated claim about GPU acceleration.");
  console.log("    Did the faithfulness metric catch it?");
  console.log("  - How would you add more test cases? What would change the scores?");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
