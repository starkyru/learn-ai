"""
Task 1 🔴 — Build a vector store FROM SCRATCH (no vector DB library).

What you'll learn:
  - What a vector is and how embeddings represent meaning as numbers
  - How cosine similarity works (dot product of unit vectors)
  - How to do brute-force top-k nearest-neighbour search
  - Why real ANN indexes (HNSW, IVF) exist — they solve the O(n·d) cost here

How to run:
  uv run python modules/04-embeddings-vectors/py/01_vector_store_scratch.py

The harness at the bottom embeds a small corpus and queries it.
Your job: fill in the three methods marked TODO.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    id: str
    score: float       # cosine similarity: 1 = identical, 0 = orthogonal
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# VectorStore — implement the three methods marked TODO
# ---------------------------------------------------------------------------


class VectorStore:
    """
    In-memory vector store with brute-force cosine top-k search.

    Intentionally simple — no compression, no index structures.
    The goal is to understand what a vector DB *does* before using one.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    # ── Public API ────────────────────────────────────────────────────────

    def add(
        self,
        id: str,
        vector: list[float],
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store a document with its pre-computed embedding.

        TODO: append a dict with keys "id", "vector", "text", "metadata"
              to self._entries.

        Think about: what should happen if the same id is added twice?
        (For now, just append — deduplication is a bonus stretch goal.)
        """
        raise NotImplementedError("TODO: implement add()")

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """
        Cosine similarity between two vectors.

        cosine(a, b) = dot(a, b) / (|a| * |b|)

        Key insight: embedding models typically L2-normalise their output,
        so |a| = |b| = 1 and cosine reduces to plain dot product. But
        implement the full formula so it works with un-normalised vectors.

        Returns a float in [-1, 1]. Higher = more similar.

        TODO: implement this.

        Steps:
          1. Compute dot product: sum of a[i] * b[i].
          2. Compute |a|: sqrt(sum of a[i]^2).
          3. Compute |b|: sqrt(sum of b[i]^2).
          4. Guard: if either magnitude is 0, return 0.0.
          5. Return dot / (mag_a * mag_b).

        Hint: a single loop can accumulate all three sums at once.
        """
        if len(a) != len(b):
            raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
        raise NotImplementedError("TODO: implement _cosine_similarity()")

    def query(self, query_vector: list[float], k: int = 3) -> list[SearchResult]:
        """
        Return the top-k documents most similar to query_vector.

        This is BRUTE FORCE: O(n·d) per query.
        Fine for hundreds of docs; see why ANN indexes matter at millions.

        TODO: implement this.

        Steps:
          1. For each entry, compute _cosine_similarity(query_vector, entry["vector"]).
          2. Build a list of SearchResult objects.
          3. Sort descending by score.
          4. Return the first k.
        """
        raise NotImplementedError("TODO: implement query()")

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Inline fallback corpus (runs standalone without data/corpus/)
# ---------------------------------------------------------------------------

CORPUS: list[dict[str, Any]] = [
    {
        "id": "doc-1",
        "text": "Embeddings are dense vector representations of text that capture semantic meaning.",
        "metadata": {"topic": "embeddings"},
    },
    {
        "id": "doc-2",
        "text": "Cosine similarity measures the angle between two vectors, ignoring magnitude.",
        "metadata": {"topic": "similarity"},
    },
    {
        "id": "doc-3",
        "text": "A neural network is composed of layers of interconnected nodes called neurons.",
        "metadata": {"topic": "neural networks"},
    },
    {
        "id": "doc-4",
        "text": "Retrieval-Augmented Generation (RAG) combines search with text generation.",
        "metadata": {"topic": "rag"},
    },
    {
        "id": "doc-5",
        "text": "Approximate nearest neighbour algorithms trade a little accuracy for huge speed gains.",
        "metadata": {"topic": "ann"},
    },
    {
        "id": "doc-6",
        "text": "Large language models are trained to predict the next token in a sequence.",
        "metadata": {"topic": "llm"},
    },
    {
        "id": "doc-7",
        "text": "Chunking splits long documents into smaller pieces before indexing.",
        "metadata": {"topic": "chunking"},
    },
    {
        "id": "doc-8",
        "text": "BM25 is a classic keyword-based ranking function used in search engines.",
        "metadata": {"topic": "bm25"},
    },
]


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nUsing provider: {provider.name} (embed model: {provider.embed_model})")

    # ── Step 1: embed corpus ──────────────────────────────────────────────
    print("\n[1/3] Embedding corpus documents...")
    texts = [d["text"] for d in CORPUS]
    result = provider.embed(texts)
    dim = len(result.vectors[0])
    print(f"  Embedded {len(texts)} documents → vectors of dimension {dim}")

    # ── Step 2: index ─────────────────────────────────────────────────────
    print("\n[2/3] Indexing into VectorStore...")
    store = VectorStore()
    for i, doc in enumerate(CORPUS):
        store.add(doc["id"], result.vectors[i], doc["text"], doc["metadata"])
    print(f"  Indexed {len(store)} documents.")

    # ── Step 3: query ─────────────────────────────────────────────────────
    queries = [
        "How do I measure text similarity?",
        "What is a neural network?",
        "How does retrieval-augmented generation work?",
    ]
    print("\n[3/3] Querying...\n")
    for q in queries:
        q_vec = provider.embed([q]).vectors[0]
        results = store.query(q_vec, k=3)
        print(f"Query: \"{q}\"")
        for r in results:
            print(f"  [score={r.score:.4f}] {r.id}: {r.text[:80]}...")
        print()


if __name__ == "__main__":
    main()
