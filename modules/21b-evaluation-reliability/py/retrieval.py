"""retrieval.py — deterministic, offline retrieval methods for Module 21b.

Three methods are compared on identical cases:

- ``dense``    — cosine similarity over a seedless character-trigram hashing
                 "embedding". This is a deterministic stand-in for a real
                 embedding model so the benchmark can run as an offline release
                 gate; it captures fuzzy sub-word overlap, not true semantics.
- ``bm25``     — Okapi BM25 with a non-negative (Lucene-style) idf, implemented
                 from scratch. Exact-term lexical matching.
- ``hybrid``   — Reciprocal Rank Fusion (RRF) of the dense and BM25 rankings.
- ``reranked`` — a deterministic lexical-overlap reranker applied to the top of
                 the hybrid list (a stand-in for a cross-encoder reranker).

Every method returns the FULL corpus ranked by that method, with a stable
tie-break (score descending, then chunk id ascending), so the same query
produces byte-identical rankings on every run.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
_FNV_OFFSET = 2166136261
_FNV_PRIME = 16777619
_UINT32 = 0xFFFFFFFF


def tokenize(text: str) -> list[str]:
    """Lowercase and split on runs of non-alphanumeric characters."""
    return [tok for tok in _TOKEN_SPLIT.split(text.lower()) if tok]


def fnv1a_32(text: str) -> int:
    """Deterministic 32-bit FNV-1a hash over the UTF-8 bytes of ``text``.

    Implemented by hand (not Python's salted ``hash``) so the embedding is
    stable across processes and ports byte-for-byte to the TypeScript version.
    """
    h = _FNV_OFFSET
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * _FNV_PRIME) & _UINT32
    return h


def _char_ngrams(token: str, n: int) -> list[str]:
    padded = f"#{token}#"
    if len(padded) < n:
        return [padded]
    return [padded[i : i + n] for i in range(len(padded) - n + 1)]


def bigram_set(tokens: Sequence[str]) -> set[tuple[str, str]]:
    """Collision-free set of adjacent-token bigrams.

    Tuples keep the two tokens distinct, so ``("do", "g")`` and ``("d", "og")``
    never collide. The TypeScript port reproduces this with a separator the
    tokenizer can never emit.
    """
    return set(zip(tokens, tokens[1:], strict=False))


@dataclass(frozen=True)
class RetrievalConfig:
    """Versioned retrieval parameters (loaded from the fixtures manifest)."""

    embed_dim: int
    embed_ngram: int
    bm25_k1: float
    bm25_b: float
    rrf_k: int
    rerank_candidates: int
    rerank_phrase_weight: float

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, object]) -> RetrievalConfig:
        embedder = manifest["embedder"]  # type: ignore[index]
        bm25 = manifest["bm25"]  # type: ignore[index]
        hybrid = manifest["hybrid"]  # type: ignore[index]
        rerank = manifest["reranker"]  # type: ignore[index]
        return cls(
            embed_dim=int(embedder["dim"]),  # type: ignore[index]
            embed_ngram=int(embedder["ngram"]),  # type: ignore[index]
            bm25_k1=float(bm25["k1"]),  # type: ignore[index]
            bm25_b=float(bm25["b"]),  # type: ignore[index]
            rrf_k=int(hybrid["rrf_k"]),  # type: ignore[index]
            rerank_candidates=int(rerank["candidates"]),  # type: ignore[index]
            rerank_phrase_weight=float(rerank["phrase_weight"]),  # type: ignore[index]
        )


def embed(text: str, dim: int, ngram: int) -> np.ndarray:
    """Signed feature-hashing embedding over padded character n-grams, L2-normalised."""
    vec = np.zeros(dim, dtype=np.float64)
    for token in tokenize(text):
        for gram in _char_ngrams(token, ngram):
            index = fnv1a_32(gram) % dim
            sign = 1.0 if (fnv1a_32("s:" + gram) & 1) == 0 else -1.0
            vec[index] += sign
    norm = float(np.linalg.norm(vec))
    if norm == 0.0:
        return vec
    return vec / norm


def _rank(scores: Mapping[str, float]) -> list[str]:
    """Rank chunk ids by score descending, breaking ties by id ascending."""
    return sorted(scores.keys(), key=lambda cid: (-scores[cid], cid))


class RetrievalIndex:
    """In-memory flat index exposing dense / bm25 / hybrid / reranked ranking.

    All corpus statistics are precomputed once, so ranking a query is a pure,
    deterministic function of the query text.
    """

    def __init__(
        self,
        chunks: Sequence[Mapping[str, str]],
        config: RetrievalConfig,
    ) -> None:
        self.config = config
        self.ids: list[str] = [c["id"] for c in chunks]
        self.texts: dict[str, str] = {c["id"]: c["text"] for c in chunks}

        # Dense: one normalised embedding per chunk.
        self._embeddings: dict[str, np.ndarray] = {
            cid: embed(self.texts[cid], config.embed_dim, config.embed_ngram) for cid in self.ids
        }

        # Lexical structures for BM25 and the reranker.
        self._doc_tokens: dict[str, list[str]] = {
            cid: tokenize(self.texts[cid]) for cid in self.ids
        }
        self._doc_len: dict[str, int] = {cid: len(toks) for cid, toks in self._doc_tokens.items()}
        self._token_set: dict[str, set[str]] = {
            cid: set(toks) for cid, toks in self._doc_tokens.items()
        }
        self._bigrams: dict[str, set[tuple[str, str]]] = {
            cid: bigram_set(toks) for cid, toks in self._doc_tokens.items()
        }
        self._tf: dict[str, dict[str, int]] = {}
        df: dict[str, int] = {}
        for cid, toks in self._doc_tokens.items():
            counts: dict[str, int] = {}
            for tok in toks:
                counts[tok] = counts.get(tok, 0) + 1
            self._tf[cid] = counts
            for term in counts:
                df[term] = df.get(term, 0) + 1

        n_docs = len(self.ids)
        self._avgdl = sum(self._doc_len.values()) / n_docs if n_docs else 0.0
        # Non-negative (Lucene-style) idf: ln(1 + (N - df + 0.5) / (df + 0.5)).
        self._idf: dict[str, float] = {
            term: math.log(1.0 + (n_docs - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()
        }

    # -- individual methods -------------------------------------------------

    def dense_scores(self, query: str) -> dict[str, float]:
        q = embed(query, self.config.embed_dim, self.config.embed_ngram)
        return {cid: float(np.dot(q, self._embeddings[cid])) for cid in self.ids}

    def bm25_scores(self, query: str) -> dict[str, float]:
        q_terms = tokenize(query)
        k1, b = self.config.bm25_k1, self.config.bm25_b
        scores: dict[str, float] = {}
        for cid in self.ids:
            tf = self._tf[cid]
            dl = self._doc_len[cid]
            denom_len = k1 * (1.0 - b + b * dl / self._avgdl) if self._avgdl else k1
            score = 0.0
            for term in q_terms:
                freq = tf.get(term, 0)
                if freq == 0:
                    continue
                idf = self._idf.get(term, 0.0)
                score += idf * (freq * (k1 + 1.0)) / (freq + denom_len)
            scores[cid] = score
        return scores

    def dense(self, query: str) -> list[str]:
        return _rank(self.dense_scores(query))

    def bm25(self, query: str) -> list[str]:
        return _rank(self.bm25_scores(query))

    def hybrid(self, query: str) -> list[str]:
        dense_rank = {cid: i + 1 for i, cid in enumerate(self.dense(query))}
        bm25_rank = {cid: i + 1 for i, cid in enumerate(self.bm25(query))}
        rrf_k = self.config.rrf_k
        fused = {
            cid: 1.0 / (rrf_k + dense_rank[cid]) + 1.0 / (rrf_k + bm25_rank[cid])
            for cid in self.ids
        }
        return _rank(fused)

    def reranked(self, query: str) -> list[str]:
        hybrid = self.hybrid(query)
        m = self.config.rerank_candidates
        head = hybrid[:m]
        tail = hybrid[m:]
        q_terms = tokenize(query)
        q_set = set(q_terms)
        q_bigrams = bigram_set(q_terms)
        weight = self.config.rerank_phrase_weight

        def rerank_score(cid: str) -> float:
            if not q_set:
                return 0.0
            coverage = len(q_set & self._token_set[cid]) / len(q_set)
            phrase_hits = len(q_bigrams & self._bigrams[cid])
            return coverage + weight * phrase_hits

        hybrid_rank = {cid: i for i, cid in enumerate(head)}
        reordered = sorted(
            head,
            key=lambda cid: (-rerank_score(cid), hybrid_rank[cid], cid),
        )
        return reordered + tail

    def rank(self, method: str, query: str) -> list[str]:
        if method == "dense":
            return self.dense(query)
        if method == "bm25":
            return self.bm25(query)
        if method == "hybrid":
            return self.hybrid(query)
        if method == "reranked":
            return self.reranked(query)
        raise ValueError(f"unknown retrieval method: {method}")


METHODS: tuple[str, ...] = ("dense", "bm25", "hybrid", "reranked")
