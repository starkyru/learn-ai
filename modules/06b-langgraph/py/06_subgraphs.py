"""
Task 6 — Subgraphs  🟡

What this teaches:
  - A COMPILED graph can be used as a NODE inside a bigger graph. That's a
    subgraph — the unit of composition for large agent systems.
  - Shared state flows by matching CHANNEL NAMES: the parent and subgraph share
    `messages` (same name) but the subgraph can keep PRIVATE channels the parent
    never sees.
  - Stream the parent with subgraphs=True to watch the inner steps.

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama

How to run:
  uv run python modules/06b-langgraph/py/06_subgraphs.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition


@tool
def search(query: str) -> str:
    """Look up a fact from a tiny knowledge base."""
    db = {"tallest mountain": "Mount Everest is 8849 metres tall."}
    return db.get(query.lower().strip(), f"No result for: {query}")


# ---------------------------------------------------------------------------
# Inner subgraph — a self-contained ReAct researcher
# ---------------------------------------------------------------------------


class ResearchState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # SHARED (same name as parent)
    sources_seen: int  # PRIVATE channel — the parent has no such key


def build_research_subgraph():
    model = get_chat_model().bind_tools([search])

    def agent(state: ResearchState) -> dict:
        return {"messages": [model.invoke(state["messages"])], "sources_seen": 1}

    g = StateGraph(ResearchState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode([search]))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile()


# ---------------------------------------------------------------------------
# Parent graph — preprocess -> research(subgraph) -> summarise
# ---------------------------------------------------------------------------


class ParentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    # NOTE: no `sources_seen` here — it stays inside the subgraph.


def build_parent():
    research = build_research_subgraph()  # noqa: F841

    def preprocess(state: ParentState) -> dict:
        return {"messages": [HumanMessage(content="(framing the research question)")]}

    def summarise(state: ParentState) -> dict:
        return {"messages": [AIMessage(content="(summary of the research)")]}

    parent = StateGraph(ParentState)
    parent.add_node("preprocess", preprocess)
    # TODO 1: add the compiled `research` subgraph DIRECTLY as a node (a compiled graph
    #         IS a valid node) — give it a name like "research".
    parent.add_node("summarise", summarise)
    parent.add_edge(START, "preprocess")
    # TODO 2: wire the linear path preprocess -> research -> summarise -> END with
    #         add_edge calls, then compile and return the parent app.
    raise NotImplementedError("TODO 1/2")


def main() -> None:
    app = build_parent()  # noqa: F841
    inputs = {"messages": [HumanMessage(content="How tall is the tallest mountain?")]}  # noqa: F841

    # TODO 3: stream the parent with `subgraphs=True` (and stream_mode="updates"). Each
    #         event is a (namespace, chunk) pair: the namespace is () for the parent and
    #         a ("research:<id>",) tuple for steps inside the subgraph. Print the
    #         namespace and the chunk's node keys to watch the inner steps surface.
    #
    # TODO 4: confirm isolation — inspect the FINAL parent state and verify it has no
    #         `sources_seen` key (that PRIVATE channel never leaked out of the subgraph).
    print("TODO: add the subgraph as a node, stream with subgraphs=True.")


if __name__ == "__main__":
    main()
