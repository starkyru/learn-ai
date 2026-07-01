"""
Task 4 🟡 — Hybrid search: BM25 + dense embeddings via Reciprocal Rank Fusion.

What you'll learn:
  - Why dense retrieval alone fails on rare/exact terms (e.g. "HNSW", "BM25")
  - Why BM25 alone fails on semantic paraphrase queries
  - How Reciprocal Rank Fusion (RRF) merges two ranked lists robustly
  - Why "hybrid" consistently outperforms either approach alone

How to run:
  uv run python modules/04-embeddings-vectors/py/04_hybrid_search.py

Extra deps: `uv sync --extra vectors` (installs rank-bm25).

BM25 library: rank-bm25  — https://pypi.org/project/rank-bm25/
RRF formula: score(d) = Σ_r  1 / (k + rank_r(d))
  where k=60 is a smoothing constant and the sum is over each ranker r.
"""

from __future__ import annotations

from typing import Any

from rank_bm25 import BM25Okapi

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

CORPUS: list[dict[str, str]] = [
    {"id": "doc-1", "text": "Embeddings are dense vector representations of text that capture semantic meaning."},
    {"id": "doc-2", "text": "Cosine similarity measures the angle between two vectors, ignoring their magnitude."},
    {"id": "doc-3", "text": "HNSW is a graph-based approximate nearest neighbour index with excellent recall and speed."},
    {"id": "doc-4", "text": "BM25 is a classic keyword-based ranking function used in search engines like Elasticsearch."},
    {"id": "doc-5", "text": "Retrieval-Augmented Generation (RAG) combines a retriever with a language model generator."},
    {"id": "doc-6", "text": "Chunking splits long documents into smaller passages before embedding for better recall."},
    {"id": "doc-7", "text": "Reciprocal Rank Fusion merges multiple ranked lists by summing 1/(k+rank) per document."},
    {"id": "doc-8", "text": "Sparse retrieval uses term frequency and inverted document frequency (TF-IDF) signals."},
    {"id": "doc-9", "text": "Large language models predict the next token using attention over a context window."},
    {"id": "doc-10", "text": "Hybrid search combines dense and sparse retrieval for consistently better results."},
]


# ---------------------------------------------------------------------------
# BM25 retrieval (using rank-bm25 library)
# ---------------------------------------------------------------------------


def build_bm25(docs: list[dict[str, str]]) -> BM25Okapi:
    """
    Build a BM25Okapi index from the corpus.

    TODO: tokenise each document, then construct and return a `BM25Okapi(...)`
    over the tokenised corpus.

    Tokenisation: for each doc lowercase its text and split on whitespace, so you
    end up with a `list[list[str]]` (one token list per document).

    BM25Okapi uses Okapi BM25 (the most common variant, k1=1.5, b=0.75).
    """
    raise NotImplementedError("TODO: implement build_bm25()")


def bm25_rank(
    bm25: BM25Okapi,
    query: str,
    docs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """
    Return docs ranked by BM25 score, descending.

    TODO: implement this.

    Steps:
      1. Tokenise the query: query.lower().split()
      2. scores = bm25.get_scores(query_tokens)   — returns a numpy array
      3. Build list of {"id": ..., "score": float} sorted descending.
    """
    raise NotImplementedError("TODO: implement bm25_rank()")


# ---------------------------------------------------------------------------
# Dense retrieval
# ---------------------------------------------------------------------------


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def dense_rank(
    query_vec: list[float],
    doc_vecs: list[list[float]],
    docs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    scored = [
        {"id": docs[i]["id"], "score": cosine(query_vec, doc_vecs[i])}
        for i in range(len(docs))
    ]
    return sorted(scored, key=lambda x: -x["score"])


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score for doc d = Σ_ranker  1 / (k + rank(d, ranker))
    where rank is 1-indexed.

    TODO: implement this.

    Steps:
      1. Build a dict: id → fused_score (default 0).
      2. For each ranked list, enumerate items with 1-based rank.
         fused[id] += 1 / (k + rank)
      3. Sort the dict items by fused score descending.
      4. Return list of {"id": ..., "fused_score": ...}.
    """
    raise NotImplementedError("TODO: implement reciprocal_rank_fusion()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def print_results(
    label: str,
    results: list[dict[str, Any]],
    docs: list[dict[str, str]],
    top_k: int = 3,
    score_key: str = "score",
) -> None:
    print(f"\n  {label}")
    for r in results[:top_k]:
        doc = next(d for d in docs if d["id"] == r["id"])
        print(f"    [{r[score_key]:.4f}] {r['id']}: {doc['text'][:70]}...")


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} | embed model: {provider.embed_model}\n")

    # Index
    doc_vecs = provider.embed([d["text"] for d in CORPUS]).vectors
    bm25 = build_bm25(CORPUS)

    queries = [
        # Semantic — dense should excel; BM25 may miss paraphrase
        "How do I find similar vectors quickly?",
        # Exact-term — BM25 should excel
        "BM25 keyword ranking function",
        # Hybrid test
        "What algorithm merges ranked lists from different retrieval methods?",
    ]

    for q in queries:
        print(f"\nQuery: \"{q}\"")
        q_vec = provider.embed([q]).vectors[0]

        dense_results = dense_rank(q_vec, doc_vecs, CORPUS)
        bm25_results = bm25_rank(bm25, q, CORPUS)
        hybrid_results = reciprocal_rank_fusion([dense_results, bm25_results])

        print_results("Dense only ", dense_results, CORPUS)
        print_results("BM25 only  ", bm25_results, CORPUS)
        print_results("Hybrid (RRF)", hybrid_results, CORPUS, score_key="fused_score")

    print("\n--- Reflection ---")
    print("  Does BM25 find 'BM25' docs that dense retrieval ranks lower?")
    print("  Does dense retrieval handle paraphrase queries that BM25 misses?")
    print("  Is hybrid always better, or are there edge cases?")


if __name__ == "__main__":
    main()
