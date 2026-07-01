"""
Task 4 🔴 — GraphRAG: multi-hop retrieval over a hand-built knowledge graph.

What you'll learn:
  - Why vector top-k fails on multi-hop questions (the answer is a PATH)
  - How an LLM extracts (subject, relation, object) triples from text
  - How to build a graph BY HAND (adjacency dict) and traverse it with BFS

How to run:
  uv run python modules/05b-advanced-rag/py/04_graph_rag.py
  (extraction + final answer are chat() calls — works on ANY provider)

🔴 Constraint: NO networkx, NO graphrag / nano-graphrag package. A graph is a
dict of adjacency lists; building and walking it is the whole point.

Your job: fill in the four TODO sections.
"""

from __future__ import annotations

import json  # noqa: F401 — used in your extract_triples TODO (json.loads)
import re
from collections import deque  # noqa: F401 — used in your multi_hop_subgraph TODO (BFS queue)
from dataclasses import dataclass, field
from typing import Any

from llm_core import (  # noqa: F401 — ChatMessage/ChatOptions used in your TODOs
    ChatMessage,
    ChatOptions,
    get_provider,
)

# ---------------------------------------------------------------------------
# Corpus — the answer to the demo question spans TWO documents (two hops).
# ---------------------------------------------------------------------------

CORPUS: list[str] = [
    "Marie Curie collaborated with Pierre Curie on research into radioactivity.",
    "Pierre Curie won the Nobel Prize in Physics in 1903.",
    "Ernest Rutherford mentored Niels Bohr at the University of Manchester.",
    "Niels Bohr won the Nobel Prize in Physics for his model of the atom.",
]

Triple = tuple[str, str, str]  # (subject, relation, object)


def _strip_code_fences(text: str) -> str:
    """Provided: remove ```json ... ``` fences some models add around JSON."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    return t


def _norm(entity: str) -> str:
    """Provided: canonical key for an entity (case/space-insensitive)."""
    return " ".join(entity.lower().split())


# ---------------------------------------------------------------------------
# TODO 1: extract triples from a chunk with the LLM
# ---------------------------------------------------------------------------


def extract_triples(text: str, provider: Any) -> list[Triple]:
    """
    Ask the LLM to extract (subject, relation, object) triples from `text` and
    return them as a list of 3-tuples.

    TODO: implement this.

    Steps:
      1. Build a list[ChatMessage]: a system message telling the model to extract
         knowledge-graph triples and respond with ONLY a JSON array of
         [subject, relation, object] arrays using short snake_case relations (giving
         one tiny example helps), and a user message with the text. Use
         ChatOptions(temperature=0, max_tokens=...).
      2. Run the reply through the provided _strip_code_fences(), then json.loads().
      3. Keep only rows that are lists of length 3 (skip malformed ones) and turn
         them into 3-tuples. Wrap the whole parse in try/except and return [] on any
         failure, so a bad reply doesn't crash graph building.
    """
    raise NotImplementedError("TODO: implement extract_triples()")


# ---------------------------------------------------------------------------
# TODO 2: the knowledge graph (adjacency dict, both directions)
# ---------------------------------------------------------------------------


@dataclass
class Edge:
    relation: str
    other: str  # the neighbour entity (canonical key)
    direction: str  # "out" (self -> other) or "in" (other -> self)


@dataclass
class KnowledgeGraph:
    # adjacency: entity-key -> list of edges
    adj: dict[str, list[Edge]] = field(default_factory=dict)
    # display label per entity-key (first spelling we saw)
    label: dict[str, str] = field(default_factory=dict)

    def add_triple(self, subj: str, rel: str, obj: str) -> None:
        """
        Store the triple in BOTH directions so traversal can move either way.

        TODO: implement this.

        Steps:
          1. Canonicalise both entities with _norm() to get their keys.
          2. Remember a display label for each key the first time you see it (the
             first spelling wins — setdefault does exactly this; don't overwrite).
          3. Append an Edge to the subject key's adjacency list pointing "out" at the
             object key, AND an Edge to the object key's list pointing "in" back at
             the subject key (both carry rel). Use setdefault(key, []) to create each
             list lazily.
        """
        raise NotImplementedError("TODO: implement add_triple()")

    def neighbors(self, entity: str) -> list[Edge]:
        """Return all edges touching `entity` (both directions), or []."""
        # TODO: look up the adjacency list for the _norm()-ed entity key, defaulting to [].
        raise NotImplementedError("TODO: implement neighbors()")

    def entities(self) -> list[str]:
        return list(self.adj.keys())


# ---------------------------------------------------------------------------
# TODO 3: multi-hop BFS subgraph
# ---------------------------------------------------------------------------


def multi_hop_subgraph(graph: KnowledgeGraph, seeds: list[str], depth: int = 2) -> list[Triple]:
    """
    BFS out from `seeds` up to `depth` hops, collecting the triples encountered.

    TODO: implement this.

    Steps:
      1. Standard BFS. Seed a `visited` set with the _norm()-ed seed keys and a deque
         of (key, hop) starting at hop 0. Keep a collected list[Triple] plus a set to
         dedupe triples you've already emitted.
      2. Pop (key, hop); stop expanding a node once hop == depth. For each Edge in
         graph.neighbors(key), reconstruct the triple in canonical subject->object
         order using the edge's direction ("out" means key is the subject; "in" means
         key is the object) and graph.label for display names (fall back to the key).
         Add it to collected if unseen.
      3. Enqueue any unvisited neighbour at hop + 1. Return collected.
    """
    raise NotImplementedError("TODO: implement multi_hop_subgraph()")


# ---------------------------------------------------------------------------
# TODO 4: answer over the assembled subgraph
# ---------------------------------------------------------------------------


def find_seed_entities(query: str, graph: KnowledgeGraph) -> list[str]:
    """Provided: graph entities whose label appears in the query (case-insensitive)."""
    ql = query.lower()
    return [key for key, lbl in graph.label.items() if lbl.lower() in ql]


def graph_rag_answer(query: str, graph: KnowledgeGraph, provider: Any) -> tuple[str, list[Triple]]:
    """
    Find seed entities in the query, gather their multi-hop subgraph, serialise
    the triples as context, and ask the LLM to answer over THAT.

    TODO: implement this.

    Steps:
      1. Locate seed entities with the provided find_seed_entities(), then gather
         their 2-hop neighbourhood with multi_hop_subgraph().
      2. Serialise each triple into a readable one-line fact (e.g. "s --relation--> o")
         and join them into a context string.
      3. Build a list[ChatMessage]: a system message telling the model to answer using
         ONLY these knowledge-graph facts, and a user message carrying the facts and
         the question. Use ChatOptions(temperature=0, max_tokens=...).
      4. Return the stripped reply text together with the triples you used.
    """
    raise NotImplementedError("TODO: implement graph_rag_answer()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def build_graph(corpus: list[str], provider: Any) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for chunk in corpus:
        for subj, rel, obj in extract_triples(chunk, provider):
            graph.add_triple(subj, rel, obj)
    return graph


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name}\n")

    print("Extracting triples + building graph...")
    graph = build_graph(CORPUS, provider)
    print(f"Graph: {len(graph.entities())} entities\n")

    # A 2-hop question: no single sentence contains the answer.
    query = "Which collaborator of Marie Curie won a Nobel Prize?"
    print(f'Query: "{query}"\n')

    answer, subgraph = graph_rag_answer(query, graph, provider)
    print("Subgraph used (the connecting path):")
    for s, r, o in subgraph:
        print(f"  {s} --{r}--> {o}")
    print(f"\nAnswer: {answer}")

    print(
        "\nReflection: vector top-k would retrieve the 'Marie Curie' sentence and "
        "miss the 'Pierre Curie won...' sentence — they share no query words. The "
        "graph connects them via the shared entity Pierre Curie."
    )


if __name__ == "__main__":
    main()
