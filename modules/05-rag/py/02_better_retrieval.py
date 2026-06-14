"""
Task 2 🟡 — Better retrieval: reranking + HyDE.

What you'll learn:
  - Why two-stage retrieval (retrieve-then-rerank) improves precision
  - How LLM-based reranking works (prompt the model to judge relevance)
  - HyDE: generate a hypothetical answer and embed THAT to retrieve
  - When each technique helps and when it adds latency without benefit

How to run:
  uv run python modules/05-rag/py/02_better_retrieval.py

This file builds on the index from task 1. The corpus and helpers are
copied here so the file runs standalone.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Shared types + corpus + index helpers (copied from task 1)
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    text: str
    source: str


@dataclass
class RetrievedChunk(Chunk):
    score: float = 0.0


@dataclass
class IndexEntry:
    chunk: Chunk
    vector: list[float]


CORPUS_DOCS: list[dict[str, str]] = [
    {"source": "embeddings-guide", "text": "Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space, even if they use different words. Embedding models are trained using contrastive learning — similar pairs are pulled together and dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and 1536 (OpenAI ada-002)."},
    {"source": "similarity-metrics", "text": "Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude."},
    {"source": "ann-algorithms", "text": "Approximate Nearest Neighbour (ANN) algorithms speed up similarity search from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable Small World) is the most popular: it builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer (coarse) and greedily descends. Typical recall@10 is above 99%."},
    {"source": "chunking-strategies", "text": "Chunking splits a long document into shorter passages before embedding. Fixed-size chunking splits every N characters at word boundaries. Sentence-based chunking groups N consecutive sentences. Overlapping chunking adds a stride so consecutive chunks share some tokens — preventing context loss at boundaries."},
    {"source": "rag-overview", "text": "Retrieval-Augmented Generation (RAG) combines a retriever with a large language model. The pipeline: chunk documents, embed each chunk, embed the question, retrieve top-k chunks, stuff them into a prompt, ask the LLM to answer based only on the provided context. RAG reduces hallucination."},
    {"source": "reranking", "text": "Reranking is a second-stage retrieval step. First retrieve a broad set of candidates (top-50) with a fast dense retriever. Then score each candidate with a more powerful but slower cross-encoder model that jointly encodes the query and passage. Reranking consistently improves precision@k."},
    {"source": "hyde", "text": "HyDE (Hypothetical Document Embeddings) is a query reformulation technique. Instead of embedding the raw question, generate a hypothetical answer using the LLM, then embed that. The hypothesis lives in the same semantic space as real answers, so retrieval tends to find better matches. HyDE works best when the question and the expected answer have very different surface forms."},
    {"source": "rag-evaluation", "text": "RAG evaluation uses LLM-as-judge to score three dimensions: Faithfulness (claims grounded in context?), Context relevance (chunks relevant to question?), Answer relevance (answer addresses question?). The RAGAS framework automates these checks."},
]


def chunk_documents(docs: list[dict[str, str]], words_per_chunk: int = 80) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in docs:
        words = doc["text"].split()
        for idx, i in enumerate(range(0, len(words), words_per_chunk)):
            chunks.append(Chunk(
                id=f"{doc['source']}-chunk-{idx}",
                text=" ".join(words[i : i + words_per_chunk]),
                source=doc["source"],
            ))
    return chunks


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def build_index(chunks: list[Chunk], provider: Any) -> list[IndexEntry]:
    result = provider.embed([c.text for c in chunks])
    return [IndexEntry(chunk=chunks[i], vector=result.vectors[i]) for i in range(len(chunks))]


def retrieve_top_k(
    query_vec: list[float], index: list[IndexEntry], k: int
) -> list[RetrievedChunk]:
    scored = [
        RetrievedChunk(
            id=e.chunk.id,
            text=e.chunk.text,
            source=e.chunk.source,
            score=cosine(query_vec, e.vector),
        )
        for e in index
    ]
    return sorted(scored, key=lambda r: -r.score)[:k]


# ---------------------------------------------------------------------------
# Technique 1: LLM reranker
# ---------------------------------------------------------------------------


def llm_rerank(
    question: str,
    candidates: list[RetrievedChunk],
    provider: Any,
    k: int = 3,
) -> list[RetrievedChunk]:
    """
    Rerank candidates using the LLM as a relevance judge.

    What: Ask the LLM to score each chunk for relevance to the question (0–10).
    Why: The bi-encoder retriever encodes query and passage separately. The LLM
         sees both together, giving it much better understanding of relevance.
    Trade-off: one LLM call per candidate — add latency, but improve precision.

    TODO: implement this function.

    Algorithm:
      For each candidate, call provider.chat() with:
        messages = [
          ChatMessage("system", "You are a relevance judge."),
          ChatMessage("user",
              f"Rate the relevance of the following passage to the question "
              f"on a scale of 0–10. Reply with ONLY the integer.\\n"
              f"Question: {question}\\n"
              f"Passage: {chunk.text}"),
        ]
        options = ChatOptions(temperature=0, max_tokens=5)
      Parse the integer from result.text. Guard against ValueError (use 0).

      Use a ThreadPoolExecutor to score all candidates in parallel:
        with ThreadPoolExecutor() as ex:
            futures = {ex.submit(score_one, c): c for c in candidates}
            ...

      Sort descending by score. Return top k.
    """
    raise NotImplementedError("TODO: implement llm_rerank()")


# ---------------------------------------------------------------------------
# Technique 2: HyDE
# ---------------------------------------------------------------------------


def hyde_query_vector(question: str, provider: Any) -> list[float]:
    """
    Generate a hypothetical answer, then return its embedding vector.

    What: Instead of embedding the question, embed a hypothetical answer.
    Why: The question lives in question-space; corpus chunks live in
         answer-space. The gap causes retrieval to sometimes miss. A
         hypothetical answer is already in answer-space.

    TODO: implement this function.

    Steps:
      1. Call provider.chat() with:
           system: "You are a knowledgeable assistant."
           user:   "Write a short, factual 2–3 sentence paragraph that would
                    be a good answer to this question. Be concise.
                    Question: {question}"
      2. Embed the generated hypothesis text.
      3. Return vectors[0].
    """
    raise NotImplementedError("TODO: implement hyde_query_vector()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    chunks = chunk_documents(CORPUS_DOCS, 80)
    index = build_index(chunks, provider)
    print(f"Index: {len(index)} chunks\n")

    questions = [
        "How does HNSW achieve fast approximate nearest neighbour search?",
        "What is HyDE and why does it improve retrieval quality?",
    ]

    for q in questions:
        print(f"\nQuestion: \"{q}\"")
        raw_vec = provider.embed([q]).vectors[0]

        # Standard: top-8 → rerank to top-3
        print("\n  [Standard] retrieve top-8 → rerank to top-3")
        candidates = retrieve_top_k(raw_vec, index, k=8)
        reranked = llm_rerank(q, candidates, provider, k=3)
        for r in reranked:
            print(f"    [score={r.score:.2f}] {r.id}: {r.text[:70]}...")

        # HyDE: generate hypothesis → embed → top-3
        print("\n  [HyDE] generate hypothesis → embed → retrieve top-3")
        hyde_vec = hyde_query_vector(q, provider)
        hyde_results = retrieve_top_k(hyde_vec, index, k=3)
        for r in hyde_results:
            print(f"    [score={r.score:.4f}] {r.id}: {r.text[:70]}...")

        print("\n  Reflection: Do HyDE and reranking surface different chunks?")


if __name__ == "__main__":
    main()
