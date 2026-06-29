"""
Task 4 — Human-in-the-loop with interrupt()  🔴

What this teaches:
  - The most-asked LangGraph production feature: pause for human approval before
    a dangerous tool fires, then resume EXACTLY where you left off.
  - interrupt(payload) inside a node stops the graph and surfaces `payload`.
    The app resumes by invoking Command(resume=<answer>) on the SAME thread.
  - This only works because the checkpointer snapshotted state at the pause.
  - (Stretch) the static form: compile(..., interrupt_before=["tools"]).

Setup:
  uv sync --extra agents
  uv pip install langchain-ollama

How to run:
  uv run python modules/06b-langgraph/py/04_human_in_the_loop.py
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from _model import get_chat_model
from langchain_core.messages import AnyMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph, add_messages


@tool
def send_email(to: str, body: str) -> str:
    """Send an email. MUST be approved by a human before it actually sends."""
    return f"EMAIL SENT to {to}: {body}"


TOOLS = [send_email]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_app():
    model = get_chat_model().bind_tools(TOOLS)

    def agent_node(state: State) -> dict:
        return {"messages": [model.invoke(state["messages"])]}

    def tools_node(state: State) -> dict:
        last = state["messages"][-1]
        out: list[ToolMessage] = []
        for call in last.tool_calls:
            # TODO 1: gate send_email behind a human decision.
            #   if call["name"] == "send_email":
            #       decision = interrupt({"action": "send_email", "args": call["args"]})
            #       if decision != "approve":
            #           out.append(ToolMessage(
            #               content="Human DENIED this email. Do not retry; explain instead.",
            #               tool_call_id=call["id"]))
            #           continue
            result = TOOLS_BY_NAME[call["name"]].invoke(call["args"])
            out.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        return {"messages": out}

    def route(state: State) -> str:
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route)
    graph.add_edge("tools", "agent")
    # TODO 2: compile WITH a checkpointer — interrupts require it.
    #   return graph.compile(checkpointer=InMemorySaver())
    raise NotImplementedError("TODO 2")


def main() -> None:
    app = build_app()  # noqa: F841
    config = {"configurable": {"thread_id": "hitl-1"}}  # noqa: F841
    prompt = "Email ada@example.com to say the build passed."  # noqa: F841

    # TODO 3: first invoke runs until interrupt(), then pauses.
    #   result = app.invoke({"messages": [HumanMessage(content=prompt)]}, config)
    #   pending = result.get("__interrupt__")          # the payload you passed to interrupt()
    #   print("PAUSED, awaiting approval:", pending)
    #
    # TODO 4: resume with a human decision on the SAME thread.
    #   approved = app.invoke(Command(resume="approve"), config)   # "deny" to reject
    #   print(approved["messages"][-1].content)
    #
    # Acceptance: with "deny", the email never sends and the agent replans/explains.
    print("TODO: invoke, observe the pause, resume with Command(resume=...).")


if __name__ == "__main__":
    main()
