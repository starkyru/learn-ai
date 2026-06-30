"""
Task 3 🟡 — Self-RAG (Asai et al. 2023), reflection tokens emulated.

What you'll learn:
  - Adaptive retrieval: let the model decide whether to retrieve at all
  - Relevance filtering (IsRel) and support-checking (IsSup) as gates
  - The difference between CRAG (grade retrieval) and Self-RAG (the model gates
    retrieval AND critiques its own generation)

How to run:
  uv run python modules/05b-advanced-rag/py/03_self_rag.py
  (chat-only — works on ANY provider, including anthropic)

The real Self-RAG trains a model to emit reflection tokens. We can't fine-tune
here, so we emulate each token with a prompted LLM-as-judge call — same control
flow, no training. Your job: fill in the four TODO functions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Tiny corpus + provided lexical retriever
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    text: str


CORPUS: list[Chunk] = [
    Chunk(
        "churn",
        "In Q3, customer churn rose to 5.2%, driven mainly by the small-business segment after a price increase.",
    ),
    Chunk("hiring", "The company hired 40 new engineers in Q3, expanding the platform team."),
    Chunk("revenue", "Q3 revenue was 12 million dollars, up 8% from Q2."),
    Chunk("office", "The new headquarters in Berlin opened in September with space for 300 staff."),
]


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def lexical_retrieve(query: str, corpus: list[Chunk], k: int = 3) -> list[Chunk]:
    """Provided: rank by token overlap. Crude on purpose — IsRel must drop the
    weakly-related chunks it lets through."""
    q = set(_tokens(query))
    scored = [(c, len(q & set(_tokens(c.text)))) for c in corpus]
    return [c for c, score in sorted(scored, key=lambda t: -t[1])[:k] if score > 0] or corpus[:k]


def _yes(text: str) -> bool:
    """Provided: read a yes/no answer from model text."""
    return text.strip().lower().startswith(("y", "true", "1"))


# ---------------------------------------------------------------------------
# TODO 1: the Retrieve token — do we need retrieval at all?
# ---------------------------------------------------------------------------


def should_retrieve(query: str, provider: Any) -> bool:
    """
    Decide whether the query needs external/document knowledge.

    Examples: "What is 17 * 23?" -> No (closed-book arithmetic).
              "What did the Q3 report say about churn?" -> Yes.

    TODO: implement this.

    Steps:
      1. messages:
           system: "Decide if answering the question needs retrieving external
                    documents. Closed-book facts, math, and general reasoning do
                    NOT. Answer only 'yes' or 'no'."
           user:   query
      2. result = provider.chat(messages, ChatOptions(temperature=0, max_tokens=3))
      3. return _yes(result.text)
    """
    raise NotImplementedError("TODO: implement should_retrieve()")


# ---------------------------------------------------------------------------
# TODO 2: the IsRel token — keep only relevant passages
# ---------------------------------------------------------------------------


def grade_relevance(query: str, chunks: list[Chunk], provider: Any) -> list[Chunk]:
    """
    Return only the chunks that are relevant to the query (IsRel = relevant).

    TODO: implement this.

    Steps:
      For each chunk, ask the LLM yes/no:
        system: "Is the passage relevant to answering the question? Answer only
                 'yes' or 'no'."
        user:   f"Question: {query}\\nPassage: {chunk.text}"
        options = ChatOptions(temperature=0, max_tokens=3)
      Keep the chunk if _yes(result.text). Return the kept list.
    """
    raise NotImplementedError("TODO: implement grade_relevance()")


# ---------------------------------------------------------------------------
# TODO 3: the IsSup token — is the answer supported by the passages?
# ---------------------------------------------------------------------------


def grade_support(answer: str, chunks: list[Chunk], provider: Any) -> str:
    """
    Judge whether `answer` is supported by the kept passages.
    Return one of: "fully" | "partially" | "no".

    TODO: implement this.

    Steps:
      1. context = "\\n".join(c.text for c in chunks)
      2. messages:
           system: "Judge how well the ANSWER is supported by the CONTEXT.
                    Reply with exactly one word: fully, partially, or no."
           user:   f"Context:\\n{context}\\n\\nAnswer:\\n{answer}"
         options = ChatOptions(temperature=0, max_tokens=5)
      3. Normalise result.text.strip().lower() to one of the three labels
         (default "no" if it's something unexpected).
    """
    raise NotImplementedError("TODO: implement grade_support()")


# ---------------------------------------------------------------------------
# TODO 4: wire the Self-RAG loop
# ---------------------------------------------------------------------------


@dataclass
class SelfRagResult:
    answer: str
    retrieved: bool
    kept_chunk_ids: list[str] = field(default_factory=list)
    support: str = "n/a"  # IsSup verdict, or "n/a" when retrieval was skipped


def _generate(query: str, context: str | None, provider: Any) -> str:
    """Provided: answer with context if given, else closed-book."""
    if context:
        messages = [
            ChatMessage("system", "Answer the question using the context."),
            ChatMessage("user", f"Context:\n{context}\n\nQuestion: {query}"),
        ]
    else:
        messages = [
            ChatMessage("system", "Answer the question directly and concisely."),
            ChatMessage("user", query),
        ]
    return provider.chat(messages, ChatOptions(temperature=0, max_tokens=200)).text.strip()


def self_rag(query: str, corpus: list[Chunk], provider: Any) -> SelfRagResult:
    """
    Self-RAG control flow:

        should_retrieve? --no--> generate closed-book (support = "n/a")
                         --yes-> retrieve -> grade_relevance (IsRel) ->
                                 generate over kept chunks ->
                                 grade_support (IsSup) -> surface the verdict

    TODO: implement this.

    Steps:
      1. If not should_retrieve(query, provider):
           answer = _generate(query, None, provider)
           return SelfRagResult(answer, retrieved=False)
      2. chunks = lexical_retrieve(query, corpus)
      3. kept = grade_relevance(query, chunks, provider)
      4. context = "\\n".join(c.text for c in kept)
      5. answer = _generate(query, context, provider)
      6. support = grade_support(answer, kept, provider)
      7. return SelfRagResult(answer, retrieved=True,
                              kept_chunk_ids=[c.id for c in kept], support=support)
    """
    raise NotImplementedError("TODO: implement self_rag()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    queries = [
        "What is 17 times 23?",  # closed-book -> Retrieve=No
        "What did the Q3 report say about customer churn?",  # corpus -> full loop
    ]

    for q in queries:
        print(f'\nQuery: "{q}"')
        result = self_rag(q, CORPUS, provider)
        print(f"  Retrieve={'Yes' if result.retrieved else 'No'}")
        if result.retrieved:
            print(f"  kept (IsRel) = {result.kept_chunk_ids}")
            print(f"  IsSup = {result.support}")
        print(f"  answer: {result.answer[:200]}")

    print(
        "\nReflection: the arithmetic query should skip retrieval entirely; the "
        "churn query should retrieve, drop the off-topic chunks (hiring/revenue), "
        "and report whether the answer is actually supported."
    )


if __name__ == "__main__":
    main()
