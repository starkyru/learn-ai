"""
Task 4 🟢 — Hybrid routing.

Not every question should go to SQL. Questions about *what happened* in structured
data belong to SQL. Questions about *why* or *how* — or questions about unstructured
knowledge — belong to vector retrieval (RAG from module 05).

A router classifies intent and dispatches to the right backend.

What you'll learn:
  - The key distinction between structured (SQL) and unstructured (RAG) queries
  - How to prompt an LLM to classify query intent with a small set of categories
  - How a router composes two retrieval backends
  - When each backend wins and when they complement each other

How to run:
  uv run python modules/12-text-to-sql/py/04_hybrid_routing.py
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from llm_core import ChatMessage, ChatOptions, get_provider

DB_PATH = Path(__file__).parent.parent / "sales.db"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Route = Literal["sql", "vector", "both", "unknown"]


@dataclass
class RouterDecision:
    route: Route
    reasoning: str      # a short sentence from the LLM explaining why


@dataclass
class HybridAnswer:
    question: str
    route: Route
    reasoning: str
    sql_result: dict[str, Any] | None = None    # populated if route in ("sql","both")
    rag_result: str | None = None               # populated if route in ("vector","both")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def classify_intent(question: str, provider: Any) -> RouterDecision:
    """
    Ask the LLM to classify the question's retrieval intent.

    TODO: implement this function.

    Steps:
      1. Build a system prompt that explains the two backends:
         - "sql"    : questions about numbers, counts, aggregations, filters,
                      rankings, trends from the sales/orders/customers/products
                      tables in the database.
         - "vector" : questions about concepts, explanations, how-to, background
                      knowledge not in the database (e.g. RAG, embeddings, AI).
         - "both"   : the question has a structured sub-question AND a knowledge
                      sub-question.
         - "unknown": intent is unclear; ask the user to rephrase.
      2. Instruct the model to reply as a JSON object with two fields — a
         "route" (one of sql/vector/both/unknown) and a one-sentence
         "reasoning" — and nothing else.
      3. Call `provider.chat(..., ChatOptions(temperature=...))` with the
         deterministic setting.
      4. Parse the JSON out of `result.text`; be ready to strip a
         ```json ... ``` fence before `json.loads`.
      5. Return a `RouterDecision` built from the parsed "route" and "reasoning".
    """
    raise NotImplementedError("TODO: implement classify_intent()")


# ---------------------------------------------------------------------------
# SQL backend (simplified — no safety guards for brevity; use task 3 in prod)
# ---------------------------------------------------------------------------


SCHEMA = """
customers(id, name, email, region, signup_date)
products(id, name, category, price_usd)
orders(id, customer_id→customers, product_id→products, quantity, order_date, status)
""".strip()


def sql_answer(question: str, provider: Any) -> dict[str, Any]:
    """Generate SQL, execute it, return result dict."""
    messages = [
        ChatMessage("system",
            f"You are a SQL expert. Schema:\n{SCHEMA}\n"
            "Return ONLY a SQL SELECT statement, no explanation, no fences."),
        ChatMessage("user", question),
    ]
    import re
    result = provider.chat(messages, ChatOptions(temperature=0))
    sql = result.text.strip()
    sql = re.sub(r"```(?:sql)?\n?", "", sql, flags=re.IGNORECASE).strip("` \n")
    if ";" in sql:
        sql = sql[: sql.index(";") + 1]

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.execute(sql)
        columns = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
    finally:
        conn.close()
    return {"sql": sql, "columns": columns, "rows": rows}


# ---------------------------------------------------------------------------
# Vector backend (stub — in a real system this calls your RAG pipeline)
# ---------------------------------------------------------------------------


# Tiny inline knowledge base — mirrors the sample_docs content from module 11
_KNOWLEDGE_BASE = """
RAG (Retrieval-Augmented Generation) combines a retrieval system with an LLM.
It solves the problem of LLMs hallucinating by injecting relevant passages as
context. The key stages are: parse, chunk, embed, retrieve, generate.

Vector databases store high-dimensional embeddings and support approximate
nearest-neighbour (ANN) search. Popular options include Chroma, Qdrant, and
Pinecone. HNSW is the most common index structure.

Chunking splits documents into shorter passages before embedding because
embedding models have token limits (usually 256-512 tokens). Section-aware
chunking follows document structure; naive chunking uses fixed character counts.

Incremental indexing re-embeds only changed documents by comparing content
hashes, saving API costs. A manifest file tracks which documents have been
ingested and at what version.
"""


def rag_answer(question: str, provider: Any) -> str:
    """
    Answer from the inline knowledge base using the LLM (simulated RAG).

    TODO: implement this function.

    In a real system this would embed the question, retrieve chunks from a
    vector store, and call the LLM with context. For this exercise:

    Steps:
      1. Build a `list[ChatMessage]`:
         - a system message that constrains the model to answer ONLY from the
           supplied context and to admit when the context lacks the answer;
         - a user message that stitches together `_KNOWLEDGE_BASE` (as the
           context) and the `question`.
      2. Call `provider.chat(messages)`.
      3. Return the model's text.

    Reflection: what would change if you replaced _KNOWLEDGE_BASE with
    the live vector retrieval from module 05?
    """
    raise NotImplementedError("TODO: implement rag_answer()")


# ---------------------------------------------------------------------------
# Router dispatcher
# ---------------------------------------------------------------------------


def route_and_answer(question: str, provider: Any) -> HybridAnswer:
    """
    Classify intent, dispatch to the right backend(s), return a HybridAnswer.

    TODO: implement this function.

    Steps:
      1. Get a `RouterDecision` from `classify_intent()`.
      2. Seed a `HybridAnswer` carrying the question plus the decision's route
         and reasoning.
      3. Dispatch based on the route: call `sql_answer()` when the route covers
         SQL ("sql"/"both") and `rag_answer()` when it covers knowledge
         ("vector"/"both"), storing each into the matching field.
      4. For "unknown", leave both result fields unset. Return the answer.
    """
    raise NotImplementedError("TODO: implement route_and_answer()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

TEST_QUESTIONS = [
    # Should route to SQL
    "How many orders were placed in Q1 2024?",
    "What is the average order value per region?",
    # Should route to vector / RAG
    "What is retrieval-augmented generation and how does it reduce hallucination?",
    "What is HNSW and why do vector databases use it?",
    # Ambiguous — might route to "both" or either
    "What products does the top-spending customer buy, and how does RAG help personalise recommendations?",
]


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run `uv run python modules/12-text-to-sql/py/seed_db.py` first.")
        return

    provider = get_provider()
    print(f"\nProvider: {provider.name}  |  Model: {provider.chat_model}\n")

    for q in TEST_QUESTIONS:
        print(f"Q: {q}")
        result = route_and_answer(q, provider)
        print(f"   Route    : {result.route}")
        print(f"   Reasoning: {result.reasoning}")
        if result.sql_result:
            print(f"   SQL      : {result.sql_result['sql']}")
            for row in result.sql_result["rows"][:3]:
                print(f"   Row      : {tuple(row)}")
        if result.rag_result:
            preview = result.rag_result[:200].replace("\n", " ")
            print(f"   RAG      : {preview}...")
        print()

    print("Key insight: SQL excels at exact aggregations and filters over")
    print("structured tables; RAG excels at open-ended knowledge questions.")
    print("A router lets you serve both from one interface.")


if __name__ == "__main__":
    main()
