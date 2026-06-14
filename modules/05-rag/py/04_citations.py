"""
Task 4 🟢 — Citations & attribution.

What you'll learn:
  - How to structure RAG prompts to enforce per-claim citations
  - How to parse and validate citations against the retrieved chunks
  - How to surface uncited or unsupported claims to the user
  - Why citations matter for trust and debugging

How to run:
  uv run python modules/05-rag/py/04_citations.py

Design:
  The LLM is asked to output a structured JSON response:
    {"claims": [{"text": "...", "citation": "chunk-id-or-null"}]}
  We then validate that every cited chunk-id actually exists in the
  retrieved set, and flag claims that have no citation.
"""

from __future__ import annotations

import json
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
class IndexEntry:
    chunk: Chunk
    vector: list[float]


@dataclass
class Claim:
    text: str
    citation: str | None   # chunk id, or None


@dataclass
class CitedAnswer:
    claims: list[Claim]
    answer: str                    # human-readable reconstructed answer
    valid_citations: list[str]     # cited ids that exist in retrieved set
    invalid_citations: list[str]   # cited ids that don't exist (hallucinated)
    uncited_claims: list[str]      # claim texts with no citation


# ---------------------------------------------------------------------------
# Shared corpus + index helpers (same as previous tasks)
# ---------------------------------------------------------------------------

CORPUS_DOCS: list[dict[str, str]] = [
    {"source": "embeddings-guide", "text": "Embeddings are dense vector representations that capture semantic meaning. Two texts that mean similar things will have vectors that are close together in the embedding space, even if they use different words. Embedding models are trained using contrastive learning — similar pairs are pulled together and dissimilar pairs are pushed apart. Common dimensions are 768 (BERT-style) and 1536 (OpenAI ada-002)."},
    {"source": "similarity-metrics", "text": "Cosine similarity is the standard metric for comparing text embeddings. It equals dot(a, b) / (|a| × |b|) and measures the angle between two vectors. Because most embedding models L2-normalise their output, cosine reduces to a plain dot product. Values range from -1 (opposite) to 1 (identical). Euclidean distance is another option but is sensitive to vector magnitude."},
    {"source": "ann-algorithms", "text": "Approximate Nearest Neighbour (ANN) algorithms speed up similarity search from O(n×d) brute force to nearly O(log n). HNSW (Hierarchical Navigable Small World) is the most popular: it builds a multi-layer graph where each node is connected to nearby nodes at multiple granularities. At query time, search starts at the top layer and greedily descends. Typical recall@10 is above 99%."},
    {"source": "chunking-strategies", "text": "Chunking splits a long document into shorter passages before embedding. Fixed-size chunking splits every N characters at word boundaries. Sentence-based chunking groups N consecutive sentences. Overlapping chunking adds a stride so consecutive chunks share some tokens."},
    {"source": "rag-overview", "text": "Retrieval-Augmented Generation (RAG) combines a retriever with a large language model. The pipeline: chunk documents, embed each chunk, embed the question, retrieve top-k chunks, stuff them into a prompt, ask the LLM to answer based only on the provided context. RAG reduces hallucination."},
    {"source": "reranking", "text": "Reranking is a second-stage retrieval step. First retrieve a broad set of candidates with a fast dense retriever. Then score each with a more powerful cross-encoder that jointly encodes query and passage. Reranking improves precision@k."},
    {"source": "hyde", "text": "HyDE (Hypothetical Document Embeddings) generates a hypothetical answer, then embeds that instead of the question. It works best when the question and answer have very different surface forms."},
    {"source": "rag-evaluation", "text": "RAG evaluation uses LLM-as-judge for three metrics: Faithfulness (claims grounded in context?), Context relevance (chunks relevant to question?), Answer relevance (answer addresses question?). The RAGAS framework automates these checks."},
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


def retrieve_top_k(query_vec: list[float], index: list[IndexEntry], k: int) -> list[RetrievedChunk]:
    scored = [
        RetrievedChunk(id=e.chunk.id, text=e.chunk.text, source=e.chunk.source, score=cosine(query_vec, e.vector))
        for e in index
    ]
    return sorted(scored, key=lambda r: -r.score)[:k]


# ---------------------------------------------------------------------------
# Citation-aware RAG prompt
# ---------------------------------------------------------------------------


def build_citation_prompt(question: str, chunks: list[RetrievedChunk]) -> list[ChatMessage]:
    """
    Build a prompt that instructs the LLM to output structured JSON claims
    with per-claim citations referencing chunk ids.

    TODO: implement this function.

    System message:
      "You are a helpful assistant. Answer using ONLY the provided context.
       Break your answer into individual factual claims. For each claim,
       provide the id of the context chunk it came from.
       If a claim cannot be grounded in any chunk, set citation to null.
       Output ONLY valid JSON in this format:
       {\"claims\": [{\"text\": \"...\", \"citation\": \"chunk-id-or-null\"}, ...]}"

    User message:
      Build a context block labelling each chunk:
        [chunk-id-1]
        {text}

        [chunk-id-2]
        {text}
        ...

        Question: {question}
    """
    raise NotImplementedError("TODO: implement build_citation_prompt()")


# ---------------------------------------------------------------------------
# Parse + validate citations
# ---------------------------------------------------------------------------


def cited_rag(
    question: str,
    chunks: list[RetrievedChunk],
    provider: Any,
) -> CitedAnswer:
    """
    Call the LLM with a citation prompt, parse the response, and validate.

    TODO: implement this function.

    Steps:
      1. messages = build_citation_prompt(question, chunks)
      2. result = provider.chat(messages)
      3. Parse result.text as JSON. Handle json.JSONDecodeError (return empty CitedAnswer).
      4. Extract claims: [{"text": ..., "citation": ...}, ...]
      5. valid_citations   = [c["citation"] for c in claims if c["citation"] is not None
                              and c["citation"] in {ch.id for ch in chunks}]
      6. invalid_citations = [c["citation"] for c in claims if c["citation"] is not None
                              and c["citation"] not in {ch.id for ch in chunks}]
      7. uncited_claims    = [c["text"] for c in claims if c["citation"] is None]
      8. Build readable answer:
           " ".join(
               c["text"] + (f" [{c['citation']}]" if c["citation"] else " [UNCITED]")
               for c in claims
           )
      9. Return CitedAnswer.
    """
    raise NotImplementedError("TODO: implement cited_rag()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    all_chunks = chunk_documents(CORPUS_DOCS, 80)
    index = build_index(all_chunks, provider)
    print(f"Index: {len(index)} chunks\n")

    questions = [
        "What is cosine similarity and how does it relate to dot product?",
        "Explain the RAG pipeline from chunk to answer.",
        "What is HyDE and how does it improve retrieval?",
    ]

    for q in questions:
        print(f"Q: {q}")
        q_vec = provider.embed([q]).vectors[0]
        retrieved = retrieve_top_k(q_vec, index, k=4)
        result = cited_rag(q, retrieved, provider)

        print(f"A: {result.answer}")
        print(f"   Valid citations:   {', '.join(result.valid_citations) or 'none'}")
        if result.invalid_citations:
            print(f"   !! Invalid citations (hallucinated): {', '.join(result.invalid_citations)}")
        if result.uncited_claims:
            print(f"   !! Uncited claims: {len(result.uncited_claims)}")
        print()


if __name__ == "__main__":
    main()
