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
    # TODO 1: add the compiled subgraph DIRECTLY as a node.
    #   parent.add_node("research", research)
    parent.add_node("summarise", summarise)
    parent.add_edge(START, "preprocess")
    # TODO 2: preprocess -> research -> summarise -> END
    raise NotImplementedError("TODO 1/2")


def main() -> None:
    app = build_parent()  # noqa: F841
    inputs = {"messages": [HumanMessage(content="How tall is the tallest mountain?")]}  # noqa: F841

    # TODO 3: stream with subgraphs=True so the inner steps are visible.
    #   for namespace, chunk in app.stream(inputs, subgraphs=True, stream_mode="updates"):
    #       # namespace == () for the parent, ("research:<id>",) for the subgraph
    #       print(namespace, list(chunk.keys()))
    #
    # TODO 4: confirm isolation — the FINAL parent state has no `sources_seen` key.
    print("TODO: add the subgraph as a node, stream with subgraphs=True.")


if __name__ == "__main__":
    main()
