"""
Task 2 — Conditional edges & the prebuilt ToolNode  🟢

What this teaches:
  - The ReAct loop from module 06 is a graph with a cycle and ONE decision:
    "did the model ask for a tool?" That decision is a CONDITIONAL EDGE.
  - LangGraph ships the two pieces you'd otherwise hand-roll:
      * ToolNode        — runs the tool_calls in the last AI message
      * tools_condition — the router ("tools if tool_calls else END")
  - create_react_agent(model, tools) builds this entire graph for you.
  - You'll build it THREE ways and confirm identical behaviour, so you can see
    exactly what each abstraction collapsed.

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama        # or langchain-openai / langchain-anthropic

How to run:
  uv run python modules/06b-langgraph/py/02_conditional_toolnode.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode

QUESTION = (
    "What is the height of the Eiffel Tower in metres, and what is that in feet? "
    "(1 metre = 3.281 feet)"
)


# ---------------------------------------------------------------------------
# Tools — the @tool decorator turns a typed function into a LangChain tool.
# ---------------------------------------------------------------------------


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple arithmetic expression like '330 * 3.281'."""
    try:
        return str(eval(expression))  # noqa: S307 — educational demo only
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


@tool
def search(query: str) -> str:
    """Look up a fact from a tiny knowledge base."""
    db = {
        "eiffel tower height": "The Eiffel Tower is 330 metres tall.",
        "capital of france": "The capital of France is Paris.",
    }
    return db.get(query.lower().strip(), f"No result for: {query}")


TOOLS = [calculator, search]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


# ---------------------------------------------------------------------------
# Variant A — hand-wired graph with YOUR OWN router
# ---------------------------------------------------------------------------


def build_handwired():
    model = get_chat_model().bind_tools(TOOLS)

    def agent_node(state: AgentState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    # TODO 1: write the router. Return "tools" if the last message has tool_calls,
    #         else END.
    #   def route(state: AgentState) -> str:
    #       last = state["messages"][-1]
    #       return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))  # prebuilt node executes the tool_calls
    graph.add_edge(START, "agent")
    # TODO 2: add_conditional_edges("agent", route) and add_edge("tools", "agent")
    return graph.compile()


# ---------------------------------------------------------------------------
# Variant B — same graph, but swap YOUR router for the prebuilt tools_condition
# ---------------------------------------------------------------------------


def build_prebuilt_router():
    model = get_chat_model().bind_tools(TOOLS)

    def agent_node(state: AgentState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    # TODO 3: graph.add_conditional_edges("agent", tools_condition)
    #         (tools_condition routes to "tools" or END for you)
    graph.add_edge("tools", "agent")
    return graph.compile()


# ---------------------------------------------------------------------------
# Variant C — the whole thing in one line
# ---------------------------------------------------------------------------


def build_fully_prebuilt():
    # TODO 4: return create_react_agent(get_chat_model(), TOOLS)
    raise NotImplementedError("TODO 4")


def run(app, label: str) -> None:
    print(f"\n=== {label} ===")
    result = app.invoke({"messages": [HumanMessage(content=QUESTION)]})
    print(result["messages"][-1].content)


def main() -> None:
    run(build_handwired(), "A: hand-wired router")
    run(build_prebuilt_router(), "B: tools_condition")
    run(build_fully_prebuilt(), "C: create_react_agent")
    # All three should reach ~1082 feet. Point at the lines B and C deleted.


if __name__ == "__main__":
    main()
