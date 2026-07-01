"""
Task 5 🟡 — Reimplement LlamaIndex: Documents -> VectorStoreIndex -> query engine.

What you'll learn:
  - LlamaIndex's core RAG mental model in three moves: wrap raw text as
    `Document`s, build a `VectorStoreIndex.from_documents(docs)` (chunk each doc
    into Nodes and index them), then ask `index.as_query_engine().query(q)`.
  - "Indexing" is just: split docs into nodes and precompute a vector per node.
    We use the SAME deterministic bag-of-words vector as Task 2 — no embeddings,
    no network — so the whole pipeline is offline and reproducible.
  - A query engine is retrieve-then-synthesize: rank nodes against the query,
    take top-k, stuff their text into a prompt, and call the model once.

The math (retrieval, again — reused from Task 2):

  Each node's text becomes a sparse count vector (word -> count). Rank nodes
  against the query by cosine similarity:

      cosine(a, b) = (a . b) / (||a|| * ||b||)

  top-k retrieval = score every node, sort by cosine descending, take the first
  k. Then synthesis is one templated model call over the retrieved node texts.

The pieces we reimplement (and the real llama-index-core equivalent):

  ours                                real llama-index-core
  --------------------------------    ------------------------------------------
  Document(text)                      llama_index.core.Document(text=...)
  Node(text)                          a TextNode produced by the node parser
  VectorStoreIndex.from_documents     VectorStoreIndex.from_documents(docs)
  index.as_query_engine()             index.as_query_engine()
  query_engine.query(q)               query_engine.query(q) -> Response

OFFLINE: this task takes a `chat_fn: Callable[[list[dict]], str]`. With --stub it
uses a deterministic fake model that echoes the node texts it was handed, so we
can assert the retrieved context reached the synthesis prompt. Without --stub it
builds chat_fn from `get_provider().chat` so the *same engine* runs on a real LLM.

How to run:
  uv run python modules/06c-agent-frameworks/py/05_llamaindex.py --stub   # offline, deterministic
  uv run python modules/06c-agent-frameworks/py/05_llamaindex.py          # real model via get_provider()
"""

from __future__ import annotations

import argparse
import math
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

ChatFn = Callable[[list[dict[str, str]]], str]


# ---------------------------------------------------------------------------
# Documents and Nodes
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """A raw piece of text to index. Real: llama_index.core.Document(text=...)."""

    text: str


@dataclass
class Node:
    """A chunk of a Document plus its precomputed bag-of-words vector.

    Real LlamaIndex parses each Document into TextNodes and attaches an
    embedding. Here the "embedding" is a sparse word-count vector (offline).
    """

    text: str
    vector: Counter[str] = field(default_factory=Counter)


# ---------------------------------------------------------------------------
# Bag-of-words cosine (same idea as Task 2; deterministic, offline)
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens (letters/digits). Complete — no need to edit."""
    return re.findall(r"[a-z0-9]+", text.lower())


def bag_of_words(text: str) -> Counter[str]:
    """Word -> count. Complete — no need to edit."""
    return Counter(tokenize(text))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    """Cosine similarity between two sparse count vectors. Complete.

    Provided so this task can focus on retrieval + synthesis (you built cosine
    by hand in Task 2). dot over shared words / product of norms; 0 if a norm
    is 0.
    """
    dot = sum(a[w] * b[w] for w in a if w in b)
    norm_a = math.sqrt(sum(c * c for c in a.values()))
    norm_b = math.sqrt(sum(c * c for c in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def split_into_nodes(text: str) -> list[Node]:
    """Chunk a document into Nodes. Complete — no need to edit.

    A real node parser splits on tokens/sentences with overlap; to stay
    deterministic and simple we split on blank lines (one Node per paragraph,
    falling back to the whole text if there are no blank lines).
    """
    chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
    if not chunks:
        chunks = [text.strip()]
    return [Node(text=c, vector=bag_of_words(c)) for c in chunks]


# ---------------------------------------------------------------------------
# The index + query engine
# ---------------------------------------------------------------------------


class VectorStoreIndex:
    """An in-memory index of Nodes you can query. Built from Documents.

    Real LlamaIndex: `VectorStoreIndex.from_documents(docs)` parses docs into
    nodes, embeds them, and stores them in a vector store.
    """

    def __init__(self, nodes: list[Node]) -> None:
        self.nodes = nodes

    @classmethod
    def from_documents(cls, documents: list[Document]) -> VectorStoreIndex:
        """Chunk every Document into Nodes and build the index. Complete."""
        nodes: list[Node] = []
        for doc in documents:
            nodes.extend(split_into_nodes(doc.text))
        return cls(nodes)

    def retrieve(self, query: str, k: int = 2) -> list[Node]:
        """Return the top-k Nodes most similar to `query` (highest cosine first).

        This is the retriever half of the query engine — the same top-k-by-cosine
        ranking as Task 2's Retriever, but over Nodes instead of raw doc strings.

        TODO: implement.
          - Turn `query` into a bag-of-words vector (see bag_of_words above).
          - Score every node in self.nodes by cosine(query_vec, node.vector),
            keeping each node paired with its score.
          - Sort by score DESCENDING (ties keep original order — sort with a key
            of the negative score, which is stable).
          - Return the Node objects of the first k pairs (a list[Node]).
        """
        # TODO: implement top-k node retrieval by cosine
        raise NotImplementedError("TODO: implement VectorStoreIndex.retrieve()")

    def as_query_engine(self, k: int = 2) -> QueryEngine:
        """Expose this index as a query engine. Complete."""
        return QueryEngine(index=self, chat_fn=self._chat_fn, k=k)

    # The chat_fn is attached by the harness (see build_index) so as_query_engine
    # needs no extra plumbing — mirrors how LlamaIndex reads a global/Settings LLM.
    _chat_fn: ChatFn


SYNTHESIS_TEMPLATE = (
    "Context information is below.\n"
    "---------------------\n"
    "{context}\n"
    "---------------------\n"
    "Given the context information and not prior knowledge, answer the query.\n"
    "Query: {query}\n"
    "Answer:"
)


@dataclass
class QueryEngine:
    """Retrieve top-k nodes, then synthesize one answer from them via the model.

    Real LlamaIndex: `index.as_query_engine().query(q)` returns a Response whose
    `.source_nodes` are what was retrieved and `.response` is the synthesized text.
    """

    index: VectorStoreIndex
    chat_fn: ChatFn
    k: int = 2
    last_prompt: str = ""  # exposed so tests can inspect what we synthesized from

    def query(self, query_str: str) -> str:
        """Answer `query_str` over the index: retrieve top-k nodes, then synthesize.

        TODO: implement.
          1. Retrieve the top-k nodes for query_str via self.index.retrieve(...).
          2. Assemble the retrieved node TEXTS into a single context block
             (one node per line/paragraph — join their `.text` fields).
          3. Fill SYNTHESIS_TEMPLATE with that context and the query to make the
             synthesis prompt. Save it on self.last_prompt (tests inspect it).
          4. Call the model with a single user message carrying that prompt
             (build a `list[dict[str, str]]` with one {"role", "content"} entry)
             and return the reply text.
        """
        # TODO: implement retrieve-then-synthesize
        raise NotImplementedError("TODO: implement QueryEngine.query()")


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: echo back the context block it was given.

    It returns a fixed prefix plus the context section pulled from the prompt so
    tests can prove the *retrieved* node text reached the synthesis prompt — we
    are testing the engine, not a real model's wording.
    """

    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        # Pull the text between the "---------------------" fences (the context).
        parts = prompt.split("---------------------")
        context = parts[1].strip() if len(parts) >= 3 else ""
        return f"[stub-answer from {context}]"

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    """Build a ChatFn backed by the shared llm_core provider."""
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

DOCS = [
    Document(
        "Python is a dynamically typed programming language popular for data "
        "science and scripting.\n\n"
        "It has a large ecosystem of libraries such as NumPy and pandas."
    ),
    Document(
        "The Eiffel Tower is an iron lattice tower on the Champ de Mars in "
        "Paris, France.\n\n"
        "It was completed in 1889 and is one of the most visited monuments in "
        "the world."
    ),
    Document(
        "Retrieval-augmented generation (RAG) grounds a language model in "
        "retrieved documents.\n\n"
        "It reduces hallucination by giving the model relevant context at query "
        "time."
    ),
]


def build_index(chat_fn: ChatFn) -> VectorStoreIndex:
    """Build the index from DOCS and attach the model. Complete."""
    index = VectorStoreIndex.from_documents(DOCS)
    index._chat_fn = chat_fn
    return index


def main() -> None:
    ap = argparse.ArgumentParser(description="LlamaIndex reimplementation (Task 5).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 5: LlamaIndex query engine — {mode} ===\n")

    index = build_index(chat_fn)
    print(f"Indexed {len(index.nodes)} nodes from {len(DOCS)} documents.")

    query_engine = index.as_query_engine(k=2)
    question = "Where is the Eiffel Tower located?"
    print(f"\nQuery: {question!r}")

    # Retrieval sanity: show which nodes the engine pulls before synthesis.
    retrieved = index.retrieve(question, k=2)
    print("Top-k retrieved nodes:")
    for i, node in enumerate(retrieved, 1):
        print(f"  [{i}] {node.text!r}")

    answer = query_engine.query(question)
    print(f"\nAnswer: {answer!r}")

    if args.stub:
        # 1) Retrieval returns the Eiffel-Tower node first (highest overlap).
        top = index.retrieve(question, k=1)
        assert top and "Eiffel Tower" in top[0].text, (
            f"top node should mention the Eiffel Tower, got {top!r}"
        )
        # 2) The synthesis prompt carried the retrieved node text as context.
        assert "Eiffel Tower" in query_engine.last_prompt, (
            "retrieved context not in synthesis prompt"
        )
        assert f"Query: {question}" in query_engine.last_prompt, "query not in synthesis prompt"
        # 3) The (stub) answer was synthesized FROM the retrieved context.
        assert "Eiffel Tower" in answer, "answer did not include retrieved context"
        print(
            "\n[ok] index chunked docs into nodes; query engine retrieved the "
            "right node and synthesized from it"
        )

    print(
        "\nReal LlamaIndex: VectorStoreIndex.from_documents(docs)"
        ".as_query_engine().query(q) runs the same retrieve-then-synthesize flow."
    )


if __name__ == "__main__":
    main()
