"""
Task 2 🟢 — Use a real vector database (ChromaDB, with a Qdrant variant).

What you'll learn:
  - How a production vector DB manages storage, indexing, and querying
  - ChromaDB's Python client API (embedded mode — no server needed)
  - How Qdrant differs (server-based, HTTP REST, richer filtering)
  - The difference between ephemeral and persistent collections

How to run:
  uv run python modules/04-embeddings-vectors/py/02_real_vector_db.py

Extra deps: `uv sync --extra vectors` (installs chromadb, qdrant-client).

QDRANT VARIANT: at the bottom there is a QdrantVariant class stub.
To use it:
  docker run -p 6333:6333 qdrant/qdrant
  Then set QDRANT_URL=http://localhost:6333 in your .env.
"""

from __future__ import annotations

import os
from typing import Any

import chromadb

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

CORPUS: list[dict[str, Any]] = [
    {"id": "doc-1", "text": "Embeddings are dense vector representations of text that capture semantic meaning.", "metadata": {"topic": "embeddings"}},
    {"id": "doc-2", "text": "Cosine similarity measures the angle between two vectors, ignoring magnitude.", "metadata": {"topic": "similarity"}},
    {"id": "doc-3", "text": "A neural network is composed of layers of interconnected nodes called neurons.", "metadata": {"topic": "neural networks"}},
    {"id": "doc-4", "text": "Retrieval-Augmented Generation combines search with text generation.", "metadata": {"topic": "rag"}},
    {"id": "doc-5", "text": "Approximate nearest neighbour algorithms trade accuracy for huge speed gains.", "metadata": {"topic": "ann"}},
    {"id": "doc-6", "text": "Large language models are trained to predict the next token in a sequence.", "metadata": {"topic": "llm"}},
    {"id": "doc-7", "text": "Chunking splits long documents into smaller pieces before indexing.", "metadata": {"topic": "chunking"}},
    {"id": "doc-8", "text": "BM25 is a classic keyword-based ranking function used in search engines.", "metadata": {"topic": "bm25"}},
]

COLLECTION_NAME = "learn-ai-m04"


# ---------------------------------------------------------------------------
# ChromaDB helpers — implement the TODOs
# ---------------------------------------------------------------------------


def index_into_chroma(
    collection: chromadb.Collection,
    docs: list[dict[str, Any]],
    vectors: list[list[float]],
) -> None:
    """
    Upsert documents into a Chroma collection.

    TODO: call collection.upsert() with:
      ids        = [d["id"] for d in docs]
      embeddings = vectors
      documents  = [d["text"] for d in docs]
      metadatas  = [d.get("metadata", {}) for d in docs]

    "Upsert" (insert-or-update) is safe to call multiple times.
    """
    raise NotImplementedError("TODO: implement index_into_chroma()")


def query_chroma(
    collection: chromadb.Collection,
    query_vector: list[float],
    k: int = 3,
) -> list[dict[str, Any]]:
    """
    Query the collection and return top-k results.

    TODO: call collection.query() with:
      query_embeddings = [query_vector]
      n_results        = k

    The response shape is:
      { "ids": [[...]], "documents": [[...]], "distances": [[...]], "metadatas": [[...]] }
    (nested lists because you can pass multiple query vectors at once)

    Chroma uses L2 distance by default. Convert to a similarity score:
      score = 1 / (1 + distance)   — score 1 means distance 0 (identical)

    Return a list of dicts: [{"id": ..., "score": ..., "text": ...}, ...]
    """
    raise NotImplementedError("TODO: implement query_chroma()")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} | embed model: {provider.embed_model}")

    # ── Embed corpus ──────────────────────────────────────────────────────
    print("\n[1/4] Embedding corpus...")
    texts = [d["text"] for d in CORPUS]
    embed_result = provider.embed(texts)
    print(f"  {len(texts)} docs → dim {len(embed_result.vectors[0])} (model: {embed_result.model})")

    # ── Set up Chroma ─────────────────────────────────────────────────────
    print("\n[2/4] Setting up ChromaDB collection...")
    # EphemeralClient = in-memory. For persistence: chromadb.PersistentClient(path="./chroma-data")
    client = chromadb.EphemeralClient()

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # doesn't exist yet

    collection = client.create_collection(COLLECTION_NAME)
    print(f"  Collection '{COLLECTION_NAME}' created.")

    # ── Index ─────────────────────────────────────────────────────────────
    print("\n[3/4] Indexing documents...")
    index_into_chroma(collection, CORPUS, embed_result.vectors)
    print(f"  Collection now has {collection.count()} documents.")

    # ── Query ─────────────────────────────────────────────────────────────
    print("\n[4/4] Querying...\n")
    queries = [
        "How do I measure text similarity?",
        "What is a neural network?",
        "How does retrieval-augmented generation work?",
    ]
    for q in queries:
        q_vec = provider.embed([q]).vectors[0]
        results = query_chroma(collection, q_vec, k=3)
        print(f"Query: \"{q}\"")
        for r in results:
            print(f"  [score={r['score']:.4f}] {r['id']}: {r['text'][:80]}")
        print()

    client.delete_collection(COLLECTION_NAME)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# QDRANT VARIANT (optional — requires docker run -p 6333:6333 qdrant/qdrant)
# ---------------------------------------------------------------------------
#
# from qdrant_client import QdrantClient
# from qdrant_client.models import Distance, VectorParams, PointStruct
#
# class QdrantVariant:
#     def __init__(self, dim: int) -> None:
#         url = os.getenv("QDRANT_URL", "http://localhost:6333")
#         self.client = QdrantClient(url=url)
#         self.collection = "learn-ai-m04"
#         # TODO: self.client.recreate_collection(
#         #     collection_name=self.collection,
#         #     vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
#         # )
#
#     def upsert(self, docs: list[dict], vectors: list[list[float]]) -> None:
#         # TODO: self.client.upsert(
#         #     collection_name=self.collection,
#         #     points=[
#         #         PointStruct(id=i, vector=vectors[i], payload={"id": docs[i]["id"], "text": docs[i]["text"]})
#         #         for i in range(len(docs))
#         #     ],
#         # )
#         pass
#
#     def query(self, query_vec: list[float], k: int = 3) -> list[dict]:
#         # TODO: results = self.client.search(
#         #     collection_name=self.collection,
#         #     query_vector=query_vec,
#         #     limit=k,
#         #     with_payload=True,
#         # )
#         # return [{"id": r.payload["id"], "score": r.score, "text": r.payload["text"]} for r in results]
#         return []
