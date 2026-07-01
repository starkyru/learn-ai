"""
Task 7 — Multi-agent supervisor with Command  🔴

What this teaches:
  - The LangGraph-native multi-agent primitive is Command: a node returns
    Command(goto=<next_node>, update={...}) to set state AND jump in one move.
  - Supervisor pattern: a router node picks the next worker; each worker hands
    control back to the supervisor. Repeat until the supervisor goes to END.
  - This is the "handoff" interviewers ask about — it's just
    "update shared state + goto another node."

Module 06 Task 5 did planner->workers->synthesiser by hand. Here it's the same
idea expressed in the framework's routing primitive.

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama

How to run:
  uv run python modules/06b-langgraph/py/07_supervisor.py
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph, add_messages
from langgraph.types import Command


@tool
def search(query: str) -> str:
    """Look up a fact."""
    db = {"eiffel tower height": "The Eiffel Tower is 330 metres tall."}
    return db.get(query.lower().strip(), f"No result for: {query}")


@tool
def calculator(expression: str) -> str:
    """Evaluate arithmetic, e.g. '330 * 3.281'."""
    try:
        return str(eval(expression))  # noqa: S307 — educational demo only
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    next: str  # which worker the supervisor chose (for tracing)


WORKERS = ["researcher", "mathematician"]


def supervisor(state: State) -> Command[Literal["researcher", "mathematician", "__end__"]]:
    """Decide who works next, or finish. Returns a Command(goto=...)."""
    # TODO 1: make ONE routing call. Build a SystemMessage telling the model it routes
    #         between the two workers (researcher = facts, mathematician = arithmetic)
    #         and must reply with EXACTLY one word: a worker name or FINISH. Invoke
    #         get_chat_model() on [that system message, *state["messages"]] and normalise
    #         the reply (strip + lowercase). Map it to a `goto`: END on "finish", else the
    #         matching worker name. Return `Command(goto=goto, update={"next": goto})` so
    #         the same move both records the choice and jumps. (import END from
    #         langgraph.graph)
    raise NotImplementedError("TODO 1")


def researcher(state: State) -> Command[Literal["supervisor"]]:
    model = get_chat_model().bind_tools([search])
    sys = SystemMessage(content="You are a researcher. Use search, then report the fact.")
    reply = model.invoke([sys, *state["messages"]])
    # TODO 2: (optional) execute any tool_calls, then hand back to the supervisor.
    return Command(goto="supervisor", update={"messages": [reply]})


def mathematician(state: State) -> Command[Literal["supervisor"]]:
    model = get_chat_model().bind_tools([calculator])
    sys = SystemMessage(content="You are a mathematician. Use the calculator for any arithmetic.")
    reply = model.invoke([sys, *state["messages"]])
    return Command(goto="supervisor", update={"messages": [reply]})


def build_app():
    g = StateGraph(State)
    g.add_node("supervisor", supervisor)
    g.add_node("researcher", researcher)
    g.add_node("mathematician", mathematician)
    g.add_edge(START, "supervisor")
    # NOTE: no explicit edges FROM the workers — Command(goto=...) IS the edge.
    return g.compile()


def main() -> None:
    app = build_app()  # noqa: F841
    question = "How tall is the Eiffel Tower in feet? (1 m = 3.281 ft)"  # noqa: F841

    # TODO 3: stream the app with stream_mode="updates" on a HumanMessage carrying the
    #         `question`, and print each chunk's node keys. Watch the handoffs cycle:
    #         supervisor -> worker -> supervisor -> ... -> END.
    print("TODO: implement supervisor routing, then trace the handoffs.")
    # Bonus: note that create_react_agent / the `langgraph-supervisor` package
    # generate this supervisor graph for you.


if __name__ == "__main__":
    main()
