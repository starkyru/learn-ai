"""
Task 3 — Persistence: checkpointer + threads  🟡

What this teaches:
  - Compile with a CHECKPOINTER and every super-step is saved.
  - A thread_id names one conversation. Same thread -> the next invoke continues
    from the saved state (memory across turns). Different thread -> blank slate.
  - Swap InMemorySaver for SqliteSaver and memory survives a PROCESS RESTART.
  - This is also the foundation for interrupts (Task 4) and time travel (Task 8).

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama
  # optional, for the persistent saver:
  uv pip install langgraph-checkpoint-sqlite

How to run:
  uv run python modules/06b-langgraph/py/03_persistence.py
  # run it TWICE to see the SqliteSaver thread remember across restarts.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver  # alias: MemorySaver
from langgraph.graph import START, StateGraph, add_messages


class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_app(checkpointer):
    model = get_chat_model()

    def chat_node(state: ChatState) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(ChatState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    # TODO 1: compile WITH the checkpointer so state is saved per thread.
    #   return graph.compile(checkpointer=checkpointer)
    raise NotImplementedError("TODO 1")


def ask(app, text: str, thread_id: str) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke({"messages": [HumanMessage(content=text)]}, config)
    return result["messages"][-1].content


def demo_in_memory() -> None:
    app = build_app(InMemorySaver())  # noqa: F841

    # TODO 2: same thread remembers.
    #   print(ask(app, "My name is Ada. Remember it.", "thread-A"))
    #   print(ask(app, "What's my name?", "thread-A"))        # -> "Ada"
    #
    # TODO 3: a different thread does NOT remember.
    #   print(ask(app, "What's my name?", "thread-B"))        # -> doesn't know
    print("TODO 2/3: ask on thread-A twice, then thread-B once.")


def demo_sqlite() -> None:
    # TODO 4: use a file-backed checkpointer so memory survives a restart.
    #   from langgraph.checkpoint.sqlite import SqliteSaver
    #   with SqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
    #       app = build_app(saver)
    #       print(ask(app, "Remember: the project codename is Borealis.", "persist-1"))
    #       print(ask(app, "What's the project codename?", "persist-1"))
    #   # Re-run this script: the SAME thread still knows "Borealis".
    print("TODO 4: wire SqliteSaver and re-run to prove restart-survival.")


def main() -> None:
    demo_in_memory()
    demo_sqlite()


if __name__ == "__main__":
    main()
