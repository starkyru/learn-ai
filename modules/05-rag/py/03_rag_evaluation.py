"""
Task 3 🟡 — RAG evaluation with LLM-as-judge.

What you'll learn:
  - The three core RAG metrics: faithfulness, context relevance, answer relevance
  - How to implement LLM-as-judge: prompt the model to score its own output
  - How to run a small evaluation harness over question/answer pairs
  - What the scores tell you (and where LLM-as-judge can be fooled)

How to run:
  uv run python modules/05-rag/py/03_rag_evaluation.py

Metric definitions (RAGAS-inspired):

  Faithfulness (0–1):
    Is every claim in the answer grounded in the retrieved context?
    Score = (# claims supported by context) / (# claims in answer).

  Context relevance (0–1):
    How much of the retrieved context is actually needed to answer the question?
    Score = (# relevant sentences in context) / (# sentences in context).

  Answer relevance (0–1):
    Does the answer actually address the question?
    (We simplify: prompt the LLM for a direct 0–10 score.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    question: str
    answer: str          # the RAG answer to evaluate
    context: list[str]   # the retrieved chunks that were given to the LLM


@dataclass
class EvalScores:
    faithfulness: float       # 0–1
    context_relevance: float  # 0–1
    answer_relevance: float   # 0–1


# ---------------------------------------------------------------------------
# Evaluation sample (one answer is intentionally hallucinated)
# ---------------------------------------------------------------------------

EVAL_CASES: list[EvalCase] = [
    EvalCase(
        question="What is cosine similarity and when should I use it?",
        answer=(
            "Cosine similarity measures the angle between two vectors. It equals dot(a,b)/(|a|×|b|). "
            "Most embedding models normalise their output so it reduces to a dot product. "
            "Use it for comparing text embeddings; Euclidean distance is less common because it is "
            "sensitive to magnitude. Cosine values range from -1 (opposite) to 1 (identical) "
            "[similarity-metrics-chunk-0]."
        ),
        context=[
            "Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude.",
            "Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space.",
        ],
    ),
    EvalCase(
        question="How does HNSW work?",
        # Last claim about GPU is hallucinated — not in any context chunk
        answer=(
            "HNSW builds a multi-layer graph. Search starts at the top coarse layer and descends greedily. "
            "It achieves O(log n) query time. Recall@10 is typically above 99%. "
            "It also supports GPU acceleration and requires no training data."
        ),
        context=[
            "HNSW (Hierarchical Navigable Small World) is the most popular ANN algorithm. It builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer (coarse) and greedily descends. Typical recall@10 is above 99%.",
        ],
    ),
    EvalCase(
        question="What is HyDE?",
        answer=(
            "HyDE stands for Hypothetical Document Embeddings. It generates a hypothetical answer "
            "and embeds that instead of the question. It works best when the question and answer "
            "have very different surface forms."
        ),
        context=[
            "HyDE (Hypothetical Document Embeddings) is a query reformulation technique. Instead of embedding the raw question, generate a hypothetical answer using the LLM, then embed that. The hypothesis lives in the same semantic space as real answers, so retrieval tends to find better matches. HyDE works best when the question and the expected answer have very different surface forms.",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Metric 1: Faithfulness
# ---------------------------------------------------------------------------


def score_faithfulness(case: EvalCase, provider: Any) -> float:
    """
    Score how well the answer is grounded in the context.

    TODO: implement this function.

    Prompt the LLM:
      System: "You are a faithful AI evaluator."
      User:
        "Given the context and answer below, identify each factual claim in
         the answer. For each claim, determine whether it is directly supported
         by the context (true) or not (false).
         Output ONLY valid JSON in this format:
         [{\"claim\": \"...\", \"supported\": true/false}, ...]
         Context:
         {context}
         Answer:
         {answer}"

    Parse the JSON (handle errors with try/except — return 0.5 on failure).
    Return: (# supported) / (# total claims).
    """
    context_str = "\n\n".join(case.context)
    raise NotImplementedError("TODO: implement score_faithfulness()")


# ---------------------------------------------------------------------------
# Metric 2: Context relevance
# ---------------------------------------------------------------------------


def score_context_relevance(case: EvalCase, provider: Any) -> float:
    """
    Score how relevant the retrieved context is to the question.

    TODO: implement this function.

    Prompt the LLM:
      "Rate how relevant the following context is for answering the question
       on a scale of 0–10. 10 = perfectly relevant. 0 = completely irrelevant.
       Reply with ONLY the integer score.
       Question: {question}
       Context: {context}"

    Return: parsed_score / 10. Guard against ValueError (return 0.0).
    """
    context_str = "\n\n".join(case.context)
    raise NotImplementedError("TODO: implement score_context_relevance()")


# ---------------------------------------------------------------------------
# Metric 3: Answer relevance
# ---------------------------------------------------------------------------


def score_answer_relevance(case: EvalCase, provider: Any) -> float:
    """
    Score whether the answer addresses the question.

    TODO: implement this function.

    Prompt the LLM:
      "On a scale of 0–10, how well does the following answer address the
       question? 10 = fully. 0 = completely off-topic.
       Reply with ONLY the integer score.
       Question: {question}
       Answer: {answer}"

    Return: parsed_score / 10.
    """
    raise NotImplementedError("TODO: implement score_answer_relevance()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def evaluate_case(case: EvalCase, provider: Any) -> EvalScores:
    return EvalScores(
        faithfulness=score_faithfulness(case, provider),
        context_relevance=score_context_relevance(case, provider),
        answer_relevance=score_answer_relevance(case, provider),
    )


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} (chat model: {provider.chat_model})\n")
    print("Running RAG evaluation...\n")

    all_scores: list[EvalScores] = []
    for case in EVAL_CASES:
        print(f"Q: {case.question}")
        scores = evaluate_case(case, provider)
        all_scores.append(scores)
        print(
            f"   faithfulness={scores.faithfulness:.2f}  "
            f"ctx_relevance={scores.context_relevance:.2f}  "
            f"ans_relevance={scores.answer_relevance:.2f}"
        )
        if scores.faithfulness < 0.7:
            print("   ** Low faithfulness — the answer may contain hallucinations.")
        if scores.context_relevance < 0.5:
            print("   ** Low context relevance — retrieval may have fetched off-topic chunks.")
        print()

    # Aggregate
    def avg(vals: list[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    print("=== Aggregate (mean across test cases) ===")
    print(f"  Faithfulness:       {avg([s.faithfulness for s in all_scores]):.3f}")
    print(f"  Context relevance:  {avg([s.context_relevance for s in all_scores]):.3f}")
    print(f"  Answer relevance:   {avg([s.answer_relevance for s in all_scores]):.3f}")
    print()
    print("Reflection:")
    print("  - Which eval case scored lowest on faithfulness? Why?")
    print("  - The HNSW answer has a hallucinated GPU claim. Did faithfulness catch it?")
    print("  - How would you add more test cases? What would change the scores?")


if __name__ == "__main__":
    main()
