"""
Task 3 🟡 — Chunking strategies.

What you'll learn:
  - Why chunk size dramatically affects retrieval quality
  - Fixed-size chunking: simple but can split sentences mid-thought
  - Sentence-based chunking: respects natural text boundaries
  - Overlapping chunks: ensures context at boundaries isn't lost
  - How to eyeball quality differences with the same query

How to run:
  uv run python modules/04-embeddings-vectors/py/03_chunking_strategies.py

No extra deps needed beyond llm_core.
"""

from __future__ import annotations

import re
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Sample long document (runs standalone without data/corpus/)
# ---------------------------------------------------------------------------

LONG_DOC = """
Embeddings and Vector Spaces

An embedding is a learned mapping from a discrete object — a word, a sentence,
an image, a user — into a continuous vector space. The key property is that
semantically similar objects land close together. When you embed the sentences
"The cat sat on the mat" and "A feline rested on the rug", their vectors will
be much closer than either is to "The stock market fell sharply today".

How are embeddings trained? Modern text embeddings come from transformer models
fine-tuned on contrastive objectives. In contrastive learning, the model is
shown pairs of similar and dissimilar sentences and trained to minimise the
distance between similar pairs while maximising it for dissimilar ones. This
process — sometimes called metric learning — shapes the geometry of the space.

Cosine similarity is the standard metric. Given two vectors a and b, cosine
similarity equals dot(a, b) divided by (|a| * |b|). Because embedding models
typically L2-normalise their outputs, |a| = |b| = 1 and cosine reduces to the
plain dot product. Values range from -1 (opposite) through 0 (orthogonal) to 1
(identical).

Approximate Nearest Neighbour search (ANN) solves the scaling problem. Brute-
force comparison is O(n*d) per query — for one million 1536-dimensional vectors
that is 1.5 billion multiplications. ANN algorithms like HNSW (Hierarchical
Navigable Small World) build a graph structure at index time so queries touch
only a small fraction of vectors. The trade-off: a small probability of missing
the true nearest neighbour. In practice the recall@k is above 99% at typical
settings, which is more than good enough for RAG workloads.

Chunking is the practice of splitting a long document into smaller passages
before embedding. This matters because embedding models have a fixed token
limit (usually 256–512 tokens) and the quality of the embedding degrades when
you stuff too much text in. Well-chosen chunk boundaries also mean the retrieved
chunk is coherent and self-contained. Common strategies include fixed-size
chunking (split every N tokens), sentence-based chunking (split on sentence
boundaries), and overlapping chunking (each chunk shares some tokens with the
next to avoid losing context at the boundary).

Hybrid search combines dense retrieval (vectors) with sparse retrieval (keyword
matching via BM25 or TF-IDF). The intuition is simple: dense retrieval excels
at semantic / paraphrase queries ("feline" matching "cat") while BM25 excels at
exact-match queries (model names, product codes, rare terms). Reciprocal Rank
Fusion (RRF) is a simple, effective way to merge the two ranked lists without
needing to calibrate scores across different scales.
""".strip()


# ---------------------------------------------------------------------------
# Chunking strategies — implement each one
# ---------------------------------------------------------------------------


def fixed_size_chunker(text: str, chunk_size: int = 300) -> list[str]:
    """
    Split text into chunks of roughly `chunk_size` characters.
    No overlap. Split at word boundaries (don't cut inside a word).

    TODO: implement this function.

    Algorithm:
      Walk through the text word by word. When adding the next word would
      exceed chunk_size characters, push the accumulated text as a chunk
      and start fresh.

    Edge cases:
      - The last chunk may be shorter than chunk_size.
      - Strip leading/trailing whitespace from each chunk.
      - A single word longer than chunk_size should still form its own chunk.
    """
    raise NotImplementedError("TODO: implement fixed_size_chunker()")


def sentence_chunker(text: str, sentences_per_chunk: int = 3) -> list[str]:
    """
    Split text into chunks where each chunk contains `sentences_per_chunk`
    consecutive sentences.

    TODO: implement this function.

    Algorithm:
      1. Split the text into sentences using the regex r'(?<=[.!?])\\s+'
         (positive lookbehind: split on whitespace *after* end-punctuation).
         This is imperfect for abbreviations but good enough for our corpus.
      2. Group consecutive sentences into windows of `sentences_per_chunk`.
      3. Join each group with " ".

    Hint: use re.split(r'(?<=[.!?])\\s+', text) for sentence splitting.
    """
    raise NotImplementedError("TODO: implement sentence_chunker()")


def overlapping_chunker(
    text: str, chunk_size: int = 300, overlap: int = 100
) -> list[str]:
    """
    Like fixed_size_chunker, but consecutive chunks overlap by `overlap`
    characters. This ensures context at a boundary isn't lost.

    TODO: implement this function.

    Algorithm (character-level):
      1. Start at position 0.
      2. Slice text[pos : pos + chunk_size].
      3. If not at the end, find the last space within the slice so you don't
         cut mid-word. Use that as the chunk boundary.
      4. Advance position by (actual_chunk_length - overlap).
      5. Repeat until pos >= len(text).

    Tip: if chunk_size <= overlap you'd loop forever — add a guard.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    raise NotImplementedError("TODO: implement overlapping_chunker()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def cosine(a: list[float], b: list[float]) -> float:
    """Inline cosine similarity — keeps file self-contained."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def retrieve_with_strategy(
    name: str,
    chunks: list[str],
    query_vec: list[float],
    provider: Any,
) -> None:
    embed_result = provider.embed(chunks)
    scored = [
        (cosine(query_vec, v), chunks[i])
        for i, v in enumerate(embed_result.vectors)
    ]
    scored.sort(key=lambda x: -x[0])
    score, top = scored[0]
    print(f"  [{name:12s}] {len(chunks)} chunks | best score={score:.4f}")
    print(f"    Top chunk ({len(top)} chars): \"{top[:120]}...\"")


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} | embed model: {provider.embed_model}\n")

    query = "How does cosine similarity work with normalised embeddings?"
    query_vec = provider.embed([query]).vectors[0]
    print(f"Query: \"{query}\"\n")

    fixed = fixed_size_chunker(LONG_DOC, chunk_size=300)
    sentence = sentence_chunker(LONG_DOC, sentences_per_chunk=3)
    overlapping = overlapping_chunker(LONG_DOC, chunk_size=300, overlap=100)

    retrieve_with_strategy("fixed-size", fixed, query_vec, provider)
    retrieve_with_strategy("sentence", sentence, query_vec, provider)
    retrieve_with_strategy("overlapping", overlapping, query_vec, provider)

    print(f"\n--- Chunk counts ---")
    print(f"  fixed-size:   {len(fixed)} chunks")
    print(f"  sentence:     {len(sentence)} chunks")
    print(f"  overlapping:  {len(overlapping)} chunks")
    print()
    print("Reflection questions:")
    print("  1. Which strategy retrieved the most relevant passage?")
    print("  2. Are there queries where fixed-size wins? Where does it fail?")
    print("  3. What's the storage cost of overlapping vs. the quality gain?")


if __name__ == "__main__":
    main()
