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

    # TODO 1: stream with `app.stream(inputs, stream_mode="updates")`. Each chunk is a
    #         dict keyed by node name -> the delta that node returned. Loop the items
    #         and print which node ran and how many messages it added.

    # TODO 2: stream with stream_mode="values". Now each event is the FULL state after
    #         a step — print the running message count so you can watch it grow.

    # TODO 3: stream with stream_mode="messages". Each event is a (token, metadata)
    #         pair; print the token's content as it arrives (end="", flush=True) for a
    #         typing effect, then a trailing newline.

    # TODO 4 (stretch): pass a LIST of modes, e.g. ["updates", "messages"]. Each event
    #         now arrives as a (mode, payload) tuple — print both so you can see how the
    #         modes interleave.
    print("TODO: implement the three stream modes above and compare them.")


if __name__ == "__main__":
    main()
