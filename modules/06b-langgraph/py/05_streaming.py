"""
Task 5 — Streaming modes  🟢

What this teaches:
  - A graph emits a stream; stream_mode picks the granularity:
      "updates"  -> just the delta each node returned  (progress UI)
      "values"   -> the full state after each step      ("state now")
      "messages" -> LLM TOKENS as they generate          (typing effect)
  - You can pass a LIST of modes; each event arrives tagged with its mode.

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama

How to run:
  uv run python modules/06b-langgraph/py/05_streaming.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition

QUESTION = "What is 330 metres in feet? (1 metre = 3.281 feet). Use the calculator."


@tool
def calculator(expression: str) -> str:
    """Evaluate a simple arithmetic expression."""
    try:
        return str(eval(expression))  # noqa: S307 — educational demo only
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


TOOLS = [calculator]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_app():
    model = get_chat_model().bind_tools(TOOLS)

    def agent_node(state: State) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def main() -> None:
    app = build_app()  # noqa: F841
    inputs = {"messages": [HumanMessage(content=QUESTION)]}  # noqa: F841

    # TODO 1: stream "updates" — print which node ran and what it returned.
    #   for chunk in app.stream(inputs, stream_mode="updates"):
    #       for node, update in chunk.items():
    #           print(f"[{node}] +{len(update['messages'])} message(s)")

    # TODO 2: stream "values" — print the running message count (full state).
    #   for snapshot in app.stream(inputs, stream_mode="values"):
    #       print("state messages:", len(snapshot["messages"]))

    # TODO 3: stream "messages" — print LLM TOKENS as they arrive (typing effect).
    #   for token, metadata in app.stream(inputs, stream_mode="messages"):
    #       if token.content:
    #           print(token.content, end="", flush=True)
    #   print()

    # TODO 4 (stretch): pass both modes and tag each event.
    #   for mode, payload in app.stream(inputs, stream_mode=["updates", "messages"]):
    #       print(mode, "->", payload)
    print("TODO: implement the three stream modes above and compare them.")


if __name__ == "__main__":
    main()
