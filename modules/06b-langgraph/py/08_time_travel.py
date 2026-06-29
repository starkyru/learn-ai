"""
Task 8 — Time travel  🟡

What this teaches:
  - With a checkpointer you get the FULL history of a thread:
      get_state(config)          -> the current StateSnapshot
      get_state_history(config)  -> every past checkpoint, newest first
  - Resume from an OLD checkpoint (pass its checkpoint_id) -> the run FORKS a new
    branch from that point.
  - update_state(config, values) edits state (through channel reducers) to make a
    corrected checkpoint, then you continue from the edit.
  - This powers debugging ("replay from step 3"), what-if branching, and
    human-edit-then-continue.

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama

How to run:
  uv run python modules/06b-langgraph/py/08_time_travel.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, StateGraph, add_messages


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_app(checkpointer):
    model = get_chat_model()

    def chat(state: State) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    g = StateGraph(State)
    g.add_node("chat", chat)
    g.add_edge(START, "chat")
    return g.compile(checkpointer=checkpointer)


def main() -> None:
    app = build_app(InMemorySaver())
    config = {"configurable": {"thread_id": "tt-1"}}

    # 1) Run a few turns on one thread so there are several checkpoints.
    app.invoke({"messages": [HumanMessage(content="Pick a number 1-10 and remember it.")]}, config)
    app.invoke({"messages": [HumanMessage(content="Now double it.")]}, config)

    # TODO 1: list the checkpoints (newest first) with their id and `next` nodes.
    #   history = list(app.get_state_history(config))
    #   for snap in history:
    #       print(snap.config["configurable"]["checkpoint_id"], "next=", snap.next,
    #             "msgs=", len(snap.values["messages"]))

    # TODO 2: fork from an EARLIER checkpoint by passing its config back in.
    #   earlier = history[-2]                       # an older snapshot
    #   forked = app.invoke(
    #       {"messages": [HumanMessage(content="Actually, triple it instead.")]},
    #       earlier.config,                         # <-- resume from this checkpoint
    #   )
    #   print("forked branch:", forked["messages"][-1].content)

    # TODO 3: edit state with update_state, then continue from the correction.
    #   new_config = app.update_state(config, {"messages": [HumanMessage(content="Correction: the number was 7.")]})
    #   cont = app.invoke(None, new_config)         # continue from the edited checkpoint
    #   print("after edit:", cont["messages"][-1].content)
    print("TODO: list history, fork from an old checkpoint, edit-then-continue.")


if __name__ == "__main__":
    main()
