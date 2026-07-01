"""
Task 1 🟡 — Contextual Retrieval (Anthropic, 2024).

What you'll learn:
  - Why a chunk that's clear to a human can be invisible to a retriever
  - How prepending LLM-generated context to a chunk BEFORE embedding fixes it
  - That the text you EMBED and the text you SHOW the generator can differ

How to run:
  LLM_PROVIDER=openai uv run python modules/05b-advanced-rag/py/01_contextual_retrieval.py
  (any provider with embeddings: openai / ollama / nvidia / lmstudio — NOT anthropic)

The harness builds two indexes over the same corpus — a naive one (raw chunks)
and a contextual one (chunk + generated context) — and compares retrieval.
Your job: fill in the two TODO functions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from llm_core import (  # noqa: F401 — ChatMessage/ChatOptions used in your TODO
    ChatMessage,
    ChatOptions,
    get_provider,
)

# ---------------------------------------------------------------------------
# Corpus — each chunk is deliberately "context-poor" on its own.
# A human reading the whole doc knows what "the model" / "it" refers to;
# the embedding of the bare chunk does not.
# ---------------------------------------------------------------------------


@dataclass
class Document:
    id: str
    title: str
    text: str


@dataclass
class Chunk:
    id: str
    doc_id: str
    text: str  # the ORIGINAL chunk text


@dataclass
class IndexEntry:
    chunk: Chunk
    embed_text: str  # what we actually embedded (may be augmented)
    vector: list[float]


DOCUMENTS: list[Document] = [
    Document(
        id="claude-card",
        title="Claude 3.5 Sonnet model card (2024)",
        text=(
            "Claude 3.5 Sonnet is Anthropic's mid-tier model released in 2024. "
            "It was evaluated on a suite of academic benchmarks. "
            "It scored 88.7% on the MMLU knowledge benchmark. "
            "On graduate-level reasoning (GPQA) it reached 59.4%. "
            "The model runs at roughly twice the speed of the previous Opus model."
        ),
    ),
    Document(
        id="acme-q3",
        title="Acme Corp Q3 2024 earnings report",
        text=(
            "Acme Corp reported its third-quarter 2024 results in October. "
            "Revenue rose to 4.2 billion dollars for the quarter. "
            "It grew 3% year over year, slower than the prior quarter. "
            "The cloud division was the main driver of the increase. "
            "Management guided to flat growth in the fourth quarter."
        ),
    ),
    Document(
        id="hnsw-note",
        title="Note on approximate nearest neighbour search",
        text=(
            "HNSW is a graph-based index for vector similarity search. "
            "It builds a multi-layer navigable small-world graph. "
            "Queries start at a coarse top layer and descend greedily. "
            "Recall above 99% is typical at production settings."
        ),
    ),
]


def chunk_document(doc: Document) -> list[Chunk]:
    """One sentence per chunk — small enough to be genuinely context-poor."""
    sentences = [s.strip() for s in doc.text.split(". ") if s.strip()]
    chunks: list[Chunk] = []
    for i, s in enumerate(sentences):
        text = s if s.endswith(".") else s + "."
        chunks.append(Chunk(id=f"{doc.id}-{i}", doc_id=doc.id, text=text))
    return chunks


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def retrieve(
    query_vec: list[float], index: list[IndexEntry], k: int
) -> list[tuple[IndexEntry, float]]:
    scored = [(e, cosine(query_vec, e.vector)) for e in index]
    return sorted(scored, key=lambda t: -t[1])[:k]


def build_naive_index(chunks: list[Chunk], provider: Any) -> list[IndexEntry]:
    """Baseline: embed the raw chunk text. Provided for comparison."""
    vectors = provider.embed([c.text for c in chunks]).vectors
    return [IndexEntry(chunk=c, embed_text=c.text, vector=vectors[i]) for i, c in enumerate(chunks)]


# ---------------------------------------------------------------------------
# TODO 1: situate a chunk inside its document
# ---------------------------------------------------------------------------


def situate_chunk(document_text: str, chunk_text: str, provider: Any) -> str:
    """
    Return a short (1–2 sentence) context that locates `chunk_text` inside
    `document_text` — naming the document's subject, time, and entities the
    chunk only refers to by pronoun.

    What: e.g. for the chunk "It grew 3% year over year." inside the Acme Q3
          report, return something like "This is from Acme Corp's Q3 2024
          earnings report, describing quarterly revenue growth."
    Why:  the bare chunk never says "Acme" or "revenue"; the embedding of the
          augmented chunk will, so a query for "Acme revenue growth" can match.

    TODO: implement this.

    Steps:
      1. Build a list[ChatMessage]: a system message instructing the model to write
         a 1-2 sentence context that situates a chunk in its document (name the
         document's subject and any entity the chunk only refers to indirectly; do
         NOT repeat the chunk; output only the context), and a user message that
         presents the full document_text and the chunk_text (e.g. wrapped in
         <document>/<chunk> tags).
      2. result = provider.chat(messages, ChatOptions(temperature=0, max_tokens=...))
         — a short cap is enough for 1-2 sentences.
      3. Return the reply text, stripped.
    """
    raise NotImplementedError("TODO: implement situate_chunk()")


# ---------------------------------------------------------------------------
# TODO 2: build the contextual index
# ---------------------------------------------------------------------------


def build_contextual_index(
    chunks: list[Chunk], documents: list[Document], provider: Any
) -> list[IndexEntry]:
    """
    For each chunk: generate its context, prepend it to the chunk, embed the
    AUGMENTED text — but keep the ORIGINAL chunk text in the entry.

    TODO: implement this.

    Steps:
      1. Build a lookup: doc_id -> document_text.
      2. For each chunk, call situate_chunk(doc_text, chunk.text, provider) and
         prepend that generated context to the original chunk text to form the
         augmented text.
      3. Embed ALL augmented texts in one provider.embed([...]) call (batch).
      4. Return one IndexEntry per chunk where embed_text is the augmented text but
         chunk.text stays the original.
    """
    raise NotImplementedError("TODO: implement build_contextual_index()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


QUERIES = [
    "How much did Acme's revenue grow?",  # answer chunk says only "It grew 3%..."
    "What did Claude 3.5 Sonnet score on MMLU?",  # answer chunk says only "It scored 88.7%..."
    "How does HNSW search vectors quickly?",  # naming-rich already; both should do fine
]


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} (embed: {provider.embed_model})\n")

    chunks: list[Chunk] = []
    for doc in DOCUMENTS:
        chunks.extend(chunk_document(doc))
    print(f"Corpus: {len(DOCUMENTS)} documents → {len(chunks)} chunks\n")

    print("Building naive index (raw chunks)...")
    naive = build_naive_index(chunks, provider)

    print("Building contextual index (chunk + generated context)...")
    contextual = build_contextual_index(chunks, DOCUMENTS, provider)

    for q in QUERIES:
        qvec = provider.embed([q]).vectors[0]
        print(f'\nQuery: "{q}"')
        for label, idx in (("naive     ", naive), ("contextual", contextual)):
            top = retrieve(qvec, idx, k=1)[0]
            entry, score = top
            print(f"  [{label}] top1 score={score:.4f}  {entry.chunk.id}: {entry.chunk.text[:60]}")

    print(
        "\nReflection: on the context-poor queries (Acme, Claude), the contextual "
        "index should rank the right chunk higher — its embedding carries the "
        "nouns the bare chunk omitted."
    )


if __name__ == "__main__":
    main()
