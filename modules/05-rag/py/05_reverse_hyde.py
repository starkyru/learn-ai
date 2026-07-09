"""
Task 5 🟡 — Reverse HyDE (index-time question generation).

What you'll learn:
  - Forward HyDE (Task 2) fixed the query side: turn the QUESTION into a
    hypothetical ANSWER so it lands in answer-space before retrieving.
  - Reverse HyDE fixes the INDEX side instead: at index time, ask the LLM for
    the questions each chunk would answer, embed THOSE questions, and store them
    pointing back at the chunk. Now a real user question is compared
    question-to-question — the same surface form — which closes the query/answer
    embedding gap without any per-query LLM call.
  - The trade-off vs forward HyDE: reverse pays once at index time (LLM calls ×
    chunks) and adds nothing to query latency; forward pays one LLM call on
    every query. Reverse also stores several vectors per chunk.

How to run:
  uv run python modules/05-rag/py/05_reverse_hyde.py

Needs an embedding provider (LLM_PROVIDER=openai|ollama|nvidia|lmstudio|gemini;
NOT anthropic — it has no embed()). Also uses chat() to generate questions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Corpus + helpers (same shape as Task 2)
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    text: str
    source: str


@dataclass
class RetrievedChunk(Chunk):
    score: float = 0.0


CORPUS_DOCS: list[dict[str, str]] = [
    {
        "source": "hnsw",
        "text": "HNSW builds a multi-layer proximity graph. Each node links to nearby nodes at several granularities; search starts coarse at the top layer and greedily descends to finer layers. This makes approximate nearest-neighbour search run in nearly logarithmic time with recall@10 above 99%.",
    },
    {
        "source": "cosine",
        "text": "The angle between two vectors, computed as dot(a,b) divided by the product of their magnitudes, ranges from -1 to 1. Because most embedding models L2-normalise their output, this reduces to a plain dot product. It is the default way to compare two pieces of text once embedded.",
    },
    {
        "source": "chunking",
        "text": "Splitting a long document into shorter passages before embedding keeps each vector focused. Fixed-size cuts every N characters; sentence-based groups N sentences; overlapping adds a stride so neighbours share tokens and no context is lost at a boundary.",
    },
    {
        "source": "reranking",
        "text": "A second-stage step: first retrieve a broad candidate set with a fast dense retriever, then rescore each candidate with a slower cross-encoder that reads the query and passage together. It consistently lifts precision at the top ranks.",
    },
    {
        "source": "faithfulness",
        "text": "To check whether a generated answer is grounded, decompose it into individual claims and verify each against the retrieved context. The fraction of claims supported by the context is the faithfulness score; unsupported claims signal hallucination.",
    },
]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def chunks_from_docs(docs: list[dict[str, str]]) -> list[Chunk]:
    return [Chunk(id=d["source"], text=d["text"], source=d["source"]) for d in docs]


# ---------------------------------------------------------------------------
# Reverse HyDE index — one entry per generated question, all pointing at a chunk
# ---------------------------------------------------------------------------


@dataclass
class QuestionEntry:
    chunk: Chunk
    question: str
    vector: list[float] = field(default_factory=list)


def generate_questions(chunk: Chunk, provider: Any, n: int = 3) -> list[str]:
    """Ask the LLM for `n` distinct questions that `chunk` answers.

    TODO: implement this function.

    Steps:
      1. Build a `list[ChatMessage]`: a system message casting the model as a
         question generator, and a user message that asks for exactly `n` short,
         distinct questions this passage would answer — one per line, no
         numbering (interpolate `chunk.text` and `n`).
      2. Call `provider.chat(messages, ChatOptions(temperature=..., max_tokens=...))`.
         A little temperature helps produce varied questions.
      3. Split `result.text` into lines, strip whitespace and any leading
         bullets/numbers, drop blanks, and return up to `n` questions.
    """
    raise NotImplementedError("TODO: implement generate_questions()")


def build_reverse_hyde_index(chunks: list[Chunk], provider: Any, n: int = 3) -> list[QuestionEntry]:
    """For each chunk, generate questions and embed each one.

    TODO: implement this function.

    Steps:
      1. For every chunk, call `generate_questions(chunk, provider, n)`.
      2. Collect ALL questions across all chunks and embed them in ONE
         `provider.embed([...])` call (batching keeps it fast/cheap).
      3. Build one `QuestionEntry(chunk, question, vector)` per question, keeping
         each question aligned with its chunk and its vector (mind the ordering).

    Return: a flat list of QuestionEntry — several per chunk.
    """
    raise NotImplementedError("TODO: implement build_reverse_hyde_index()")


def retrieve_reverse_hyde(
    question: str, index: list[QuestionEntry], provider: Any, k: int = 3
) -> list[RetrievedChunk]:
    """Retrieve chunks by matching the query against generated questions.

    TODO: implement this function.

    Steps:
      1. Embed the incoming `question` with `provider.embed([question])`.
      2. Score every QuestionEntry by `cosine(query_vec, entry.vector)`.
      3. Collapse to chunks: a chunk's score is its BEST-matching question's
         score (a chunk can own several question entries — keep the max, don't
         double-count).
      4. Return the top-k chunks as `RetrievedChunk` sorted by score descending.
    """
    raise NotImplementedError("TODO: implement retrieve_reverse_hyde()")


# ---------------------------------------------------------------------------
# Baseline: embed the chunk text directly (naive retrieval from Task 1)
# ---------------------------------------------------------------------------


def retrieve_baseline(
    question: str, chunks: list[Chunk], chunk_vectors: list[list[float]], provider: Any, k: int = 3
) -> list[RetrievedChunk]:
    qv = provider.embed([question]).vectors[0]
    scored = [
        RetrievedChunk(id=c.id, text=c.text, source=c.source, score=cosine(qv, chunk_vectors[i]))
        for i, c in enumerate(chunks)
    ]
    return sorted(scored, key=lambda r: -r.score)[:k]


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    chunks = chunks_from_docs(CORPUS_DOCS)
    chunk_vectors = provider.embed([c.text for c in chunks]).vectors

    print("Building reverse-HyDE index (generating questions per chunk)…")
    index = build_reverse_hyde_index(chunks, provider, n=3)
    print(f"  {len(chunks)} chunks → {len(index)} question vectors\n")

    # Deliberately phrased far from the chunk wording, to stress the query/answer gap.
    questions = [
        "Why can I search a huge vector set so quickly?",
        "How do I tell if the model made something up?",
    ]

    for q in questions:
        print(f'\nQuestion: "{q}"')

        print("  [Baseline] embed question vs chunk text:")
        for r in retrieve_baseline(q, chunks, chunk_vectors, provider, k=3):
            print(f"    [{r.score:.4f}] {r.id}: {r.text[:60]}…")

        print("  [Reverse HyDE] embed question vs generated questions:")
        for r in retrieve_reverse_hyde(q, index, provider, k=3):
            print(f"    [{r.score:.4f}] {r.id}: {r.text[:60]}…")

    print("\nReflection:")
    print("  1. Did reverse HyDE rank the intended chunk higher than the baseline?")
    print("  2. Forward HyDE (Task 2) vs reverse: which adds per-query latency?")
    print("  3. What's the storage cost of N question vectors per chunk?")


if __name__ == "__main__":
    main()
