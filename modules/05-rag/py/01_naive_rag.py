"""
Task 1 🟢 — Naive RAG end-to-end.

The full RAG pipeline in one file:
  corpus → chunk → embed → store → retrieve → prompt → answer with citations

What you'll learn:
  - The five stages of RAG: load, chunk, embed, retrieve, generate
  - How to inject retrieved context into a prompt (context stuffing)
  - How to ask the LLM to cite which chunk each claim came from
  - Where naive RAG fails (task 2 improves it)

How to run:
  uv run python modules/05-rag/py/01_naive_rag.py

This file is intentionally self-contained with an inline corpus so it
runs even if data/corpus/ is absent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from llm_core import ChatMessage, get_provider

# ---------------------------------------------------------------------------
# Types
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
class RAGAnswer:
    answer: str
    chunks: list[RetrievedChunk]


# ---------------------------------------------------------------------------
# Inline corpus
# ---------------------------------------------------------------------------

CORPUS_DOCS: list[dict[str, str]] = [
    {
        "source": "embeddings-guide",
        "text": (
            "Embeddings are dense vector representations that capture semantic meaning. "
            "Two texts that mean similar things will have vectors that are close together "
            "in the embedding space, even if they use different words. Embedding models are "
            "trained using contrastive learning — similar pairs are pulled together and "
            "dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and "
            "1536 (OpenAI ada-002)."
        ),
    },
    {
        "source": "similarity-metrics",
        "text": (
            "Cosine similarity is the standard metric for comparing text embeddings. "
            "It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. "
            "Because most embedding models L2-normalise their output, cosine reduces to a "
            "plain dot product. Values range from -1 (opposite) to 1 (identical). "
            "Euclidean distance is another option but is sensitive to vector magnitude."
        ),
    },
    {
        "source": "ann-algorithms",
        "text": (
            "Approximate Nearest Neighbour (ANN) algorithms speed up similarity search "
            "from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable "
            "Small World) is the most popular: it builds a multi-layer graph where each "
            "node is connected to nearby nodes at multiple granularities. At query time, "
            "search starts at the top layer (coarse) and greedily descends to the bottom "
            "layer (fine). Typical recall@10 is above 99%."
        ),
    },
    {
        "source": "chunking-strategies",
        "text": (
            "Chunking splits a long document into shorter passages before embedding. "
            "Embedding models have a token limit (usually 256–512 tokens) and quality "
            "degrades when you exceed it. Fixed-size chunking splits every N characters "
            "at word boundaries. Sentence-based chunking groups N consecutive sentences. "
            "Overlapping chunking adds a stride so consecutive chunks share some tokens — "
            "this prevents losing context that falls at a boundary."
        ),
    },
    {
        "source": "rag-overview",
        "text": (
            "Retrieval-Augmented Generation (RAG) combines a retriever with a large "
            "language model. The pipeline: (1) at index time, chunk documents and embed "
            "each chunk; (2) at query time, embed the question, retrieve the top-k most "
            "similar chunks, stuff them into a prompt, and ask the LLM to answer based "
            "only on the provided context. RAG reduces hallucination because the model "
            "is constrained to what was retrieved."
        ),
    },
    {
        "source": "reranking",
        "text": (
            "Reranking is a second-stage retrieval step. First retrieve a broad set of "
            "candidates (top-50) with a fast dense retriever. Then score each candidate "
            "with a more powerful but slower cross-encoder model that jointly encodes the "
            "query and passage. Reranking consistently improves precision@k."
        ),
    },
    {
        "source": "hyde",
        "text": (
            "HyDE (Hypothetical Document Embeddings) is a query reformulation technique. "
            "Instead of embedding the raw question, generate a hypothetical answer using "
            "the LLM, then embed that. The hypothesis lives in the same semantic space as "
            "real answers, so retrieval tends to find better matches. HyDE works best when "
            "the question and the expected answer have very different surface forms."
        ),
    },
    {
        "source": "rag-evaluation",
        "text": (
            "RAG evaluation uses LLM-as-judge to score three dimensions: (1) Faithfulness "
            "— is every claim in the answer grounded in the retrieved context? (2) Context "
            "relevance — are the retrieved chunks actually relevant to the question? (3) "
            "Answer relevance — does the answer address the question? The RAGAS framework "
            "automates these checks."
        ),
    },
]


# ---------------------------------------------------------------------------
# Stage 1: Chunk
# ---------------------------------------------------------------------------


def chunk_documents(
    docs: list[dict[str, str]], words_per_chunk: int = 80
) -> list[Chunk]:
    """
    Simple word-based fixed-size chunker.

    TODO: implement this function.

    For each doc, split doc["text"] on whitespace into words. Walk through
    the words in steps of `words_per_chunk`, join each slice into a string,
    and create a Chunk:
      id     = f"{doc['source']}-chunk-{index}"   (0-based index per doc)
      text   = joined words
      source = doc["source"]

    Return the full list of Chunk objects across all docs.
    """
    raise NotImplementedError("TODO: implement chunk_documents()")


# ---------------------------------------------------------------------------
# Stage 2 & 3: Embed + Store
# ---------------------------------------------------------------------------


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


@dataclass
class IndexEntry:
    chunk: Chunk
    vector: list[float]


def build_index(chunks: list[Chunk], provider: Any) -> list[IndexEntry]:
    """
    Embed all chunks and return an in-memory index.

    TODO: implement this function.

    Steps:
      1. texts = [c.text for c in chunks]
      2. result = provider.embed(texts)
      3. return [IndexEntry(chunk=chunks[i], vector=result.vectors[i]) for i in ...]
    """
    raise NotImplementedError("TODO: implement build_index()")


# ---------------------------------------------------------------------------
# Stage 4: Retrieve
# ---------------------------------------------------------------------------


def retrieve(
    query_vec: list[float], index: list[IndexEntry], k: int = 4
) -> list[RetrievedChunk]:
    """
    Return top-k chunks by cosine similarity.

    TODO: implement this function.

    Steps:
      1. Score each entry: cosine(query_vec, entry.vector).
      2. Build RetrievedChunk objects (copy fields from entry.chunk, add score).
      3. Sort descending by score.
      4. Return first k.
    """
    raise NotImplementedError("TODO: implement retrieve()")


# ---------------------------------------------------------------------------
# Stage 5: Generate with citations
# ---------------------------------------------------------------------------


def build_rag_prompt(
    question: str, chunks: list[RetrievedChunk]
) -> list[ChatMessage]:
    """
    Build a RAG prompt that asks the LLM to answer using ONLY the context
    and to cite which chunk each claim comes from.

    TODO: implement this function.

    Return [system_message, user_message] where:

    System: "You are a helpful assistant. Answer using ONLY the provided
             context. After each claim, add a citation like [chunk-id].
             If the context does not contain the answer, say so."

    User: Build a context block like:
            [chunk-id-1]
            {text}

            [chunk-id-2]
            {text}

            Question: {question}
    """
    raise NotImplementedError("TODO: implement build_rag_prompt()")


def rag(
    question: str,
    index: list[IndexEntry],
    provider: Any,
    k: int = 4,
) -> RAGAnswer:
    """Full RAG pipeline for a single question."""
    q_vec = provider.embed([question]).vectors[0]
    chunks = retrieve(q_vec, index, k)
    messages = build_rag_prompt(question, chunks)
    result = provider.chat(messages)
    return RAGAnswer(answer=result.text, chunks=chunks)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}")
    print(f"  Chat model:  {provider.chat_model}")
    print(f"  Embed model: {provider.embed_model}\n")

    # Build index
    print("[1/2] Building RAG index...")
    chunks = chunk_documents(CORPUS_DOCS, words_per_chunk=80)
    print(f"  {len(CORPUS_DOCS)} docs → {len(chunks)} chunks")
    index = build_index(chunks, provider)
    print(f"  Index built with {len(index)} vectors.\n")

    # Answer questions
    questions = [
        "What is cosine similarity and when should I use it instead of Euclidean distance?",
        "How does HNSW work and what recall can I expect?",
        "What is HyDE and why does it improve retrieval?",
        "How do I evaluate whether my RAG system is faithfully grounding its answers?",
    ]

    print("[2/2] Answering questions...\n")
    for q in questions:
        print(f"Q: {q}")
        result = rag(q, index, provider)
        print(f"A: {result.answer}")
        print(f"   (Retrieved: {', '.join(c.id for c in result.chunks)})")
        print()


if __name__ == "__main__":
    main()
