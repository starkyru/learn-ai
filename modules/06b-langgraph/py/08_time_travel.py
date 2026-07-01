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

    # TODO 1: materialise `app.get_state_history(config)` into a list (it yields
    #         snapshots newest-first). For each snapshot, print its checkpoint id (under
    #         snap.config["configurable"]), its `.next` nodes, and its message count
    #         (len of snap.values["messages"]).

    # TODO 2: fork from an EARLIER checkpoint. Pick an older snapshot from the history
    #         list (e.g. the second-to-last) and invoke the app with a new HumanMessage
    #         BUT pass that snapshot's `.config` instead of the live config — resuming
    #         from an old checkpoint FORKS a new branch. Print the forked reply.

    # TODO 3: edit-then-continue. Call `app.update_state(config, {...})` with a message
    #         that corrects the state; it applies through the channel reducers and
    #         returns a new config pointing at the edited checkpoint. Then invoke the app
    #         with `None` as input and that new config to continue from the edit, and
    #         print the result.
    print("TODO: list history, fork from an old checkpoint, edit-then-continue.")


if __name__ == "__main__":
    main()
