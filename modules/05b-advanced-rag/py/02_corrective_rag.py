"""
Task 2 🟡 — Corrective RAG (CRAG, Yan et al. 2024).

What you'll learn:
  - Why "retrieved" must not be trusted as "relevant"
  - How a retrieval evaluator grades chunks into Correct / Incorrect / Ambiguous
  - How to self-correct: rewrite the query and fall back instead of hallucinating

How to run:
  uv run python modules/05b-advanced-rag/py/02_corrective_rag.py
  (chat-only — works on ANY provider, including anthropic)

This task uses a simple lexical retriever (provided) so the lesson is the
correction loop, not embeddings. Your job: fill in the three TODO functions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Tiny corpus + a provided lexical retriever (the retriever is a black box here)
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    text: str


CORPUS: list[Chunk] = [
    Chunk(
        "photosynth",
        "Photosynthesis converts light energy into chemical energy stored in glucose. It happens in the chloroplasts of plant cells.",
    ),
    Chunk(
        "mitochondria",
        "Mitochondria are the powerhouse of the cell, producing ATP through cellular respiration.",
    ),
    Chunk(
        "water-cycle",
        "The water cycle moves water through evaporation, condensation, and precipitation across the Earth.",
    ),
    Chunk(
        "dna",
        "DNA stores genetic information in sequences of four nucleotide bases: adenine, thymine, guanine, and cytosine.",
    ),
]


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def lexical_retrieve(query: str, corpus: list[Chunk], k: int = 2) -> list[Chunk]:
    """Provided: rank chunks by query-token overlap. Deliberately crude — that's
    the point: it WILL return weakly-related chunks for off-topic queries, which
    is exactly what CRAG must catch."""
    q = set(_tokens(query))
    scored = [(c, len(q & set(_tokens(c.text)))) for c in corpus]
    return [c for c, _ in sorted(scored, key=lambda t: -t[1])[:k]]


def web_search_stub(query: str) -> str:
    """Provided fallback 'external source'. In a real system this is a web search
    / API call; here it returns a deterministic canned snippet so the demo runs
    offline."""
    return (
        f"[external source for '{query}']: The Eiffel Tower is a wrought-iron "
        "lattice tower in Paris, France, completed in 1889 and standing 330 metres tall."
    )


# ---------------------------------------------------------------------------
# TODO 1: grade retrieval
# ---------------------------------------------------------------------------


@dataclass
class Grade:
    scores: list[float]  # one relevance score in [0,1] per chunk, in order
    verdict: str  # "Correct" | "Incorrect" | "Ambiguous"


def grade_retrieval(query: str, chunks: list[Chunk], provider: Any) -> Grade:
    """
    Score each chunk's relevance to the query (0..1) with the LLM, then bucket
    the MAX score into a verdict.

    Buckets:  max >= 0.7 -> "Correct"
              max <  0.3 -> "Incorrect"
              else        -> "Ambiguous"

    TODO: implement this.

    Steps:
      1. For each chunk, ask the LLM for a single relevance number 0..1. Build a
         list[ChatMessage]: a system message telling the model to act as a retrieval
         evaluator and output ONLY a number between 0 and 1 for how well the passage
         helps answer the question, and a user message carrying the query and the
         chunk text. Use ChatOptions(temperature=0, max_tokens=...) with a tiny cap.
         Parse the reply with float(...); on ValueError use 0.0; clamp into [0,1].
         (You may loop sequentially, or parallelise with ThreadPoolExecutor.)
      2. Compute the verdict from max(scores) using the buckets above
         (empty list -> "Incorrect").
      3. Return Grade(scores, verdict).
    """
    raise NotImplementedError("TODO: implement grade_retrieval()")


# ---------------------------------------------------------------------------
# TODO 2: rewrite the query for the fallback search
# ---------------------------------------------------------------------------


def rewrite_query(query: str, provider: Any) -> str:
    """
    Turn the user's question into a cleaner standalone search query for the
    external source.

    TODO: implement this.

    Steps:
      1. Build a list[ChatMessage]: a system message asking the model to rewrite the
         user's question into a concise web search query and output only the query,
         plus a user message with the query.
      2. result = provider.chat(messages, ChatOptions(temperature=0, max_tokens=...))
         — a short cap is enough.
      3. Return the reply text, stripped.
    """
    raise NotImplementedError("TODO: implement rewrite_query()")


# ---------------------------------------------------------------------------
# TODO 3: the corrective loop
# ---------------------------------------------------------------------------


@dataclass
class CragResult:
    answer: str
    verdict: str
    branch: str  # "kept-chunks" | "fallback" | "both"
    context_used: str


def _generate(query: str, context: str, provider: Any) -> str:
    """Provided: answer the query grounded in context."""
    messages = [
        ChatMessage(
            "system",
            "Answer the question using ONLY the context. If the context is insufficient, say so.",
        ),
        ChatMessage("user", f"Context:\n{context}\n\nQuestion: {query}"),
    ]
    return provider.chat(messages, ChatOptions(temperature=0, max_tokens=200)).text.strip()


def corrective_rag(query: str, corpus: list[Chunk], provider: Any) -> CragResult:
    """
    Wire the CRAG loop:

        retrieve -> grade -> {
            Correct:   generate from the kept chunks
            Incorrect: rewrite query -> web_search_stub -> generate from that
            Ambiguous: do BOTH (chunks + fallback) and generate from the merge
        }

    TODO: implement this.

    Steps:
      1. Retrieve with lexical_retrieve(...), then grade_retrieval(...) for the verdict.
      2. Branch on grade.verdict to assemble `context` and the `branch` label:
         - "Correct":   the kept chunk texts joined;      branch = "kept-chunks"
         - "Incorrect": rewrite_query(...) then feed that to web_search_stub(...);
                        branch = "fallback"
         - "Ambiguous": merge the chunk texts with the fallback search result;
                        branch = "both"
      3. Generate the answer over that context with _generate(...) and return a
         CragResult carrying the answer, verdict, branch, and the context you used.
    """
    raise NotImplementedError("TODO: implement corrective_rag()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    queries = [
        "What do mitochondria do in a cell?",  # in corpus  -> Correct
        "How tall is the Eiffel Tower?",  # NOT in corpus -> Incorrect -> fallback
    ]

    for q in queries:
        print(f'\nQuery: "{q}"')
        result = corrective_rag(q, CORPUS, provider)
        print(f"  verdict={result.verdict}  branch={result.branch}")
        print(f"  answer: {result.answer[:200]}")

    print(
        "\nReflection: the biology query should grade Correct and stay in-corpus; "
        "the Eiffel Tower query should grade Incorrect and trigger the fallback "
        "instead of hallucinating over unrelated biology chunks."
    )


if __name__ == "__main__":
    main()
