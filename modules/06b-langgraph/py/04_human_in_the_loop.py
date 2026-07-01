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
            # TODO 1: gate send_email behind a human decision. When the call is for
            #         "send_email", pause the graph by calling `interrupt(payload)` —
            #         pass a payload dict describing the action and its args so the
            #         human can review it. The value the human resumes with comes back
            #         as interrupt()'s return. If it isn't an approval, append a
            #         ToolMessage (tool_call_id=call["id"]) telling the model the human
            #         denied it and to explain rather than retry, then `continue` past
            #         the real invoke below.
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
    # TODO 2: compile WITH a checkpointer (an `InMemorySaver()` is enough) — interrupts
    #         cannot pause/resume without one. Return the compiled app.
    raise NotImplementedError("TODO 2")


def main() -> None:
    app = build_app()  # noqa: F841
    config = {"configurable": {"thread_id": "hitl-1"}}  # noqa: F841
    prompt = "Email ada@example.com to say the build passed."  # noqa: F841

    # TODO 3: first invoke the app normally (a HumanMessage with `prompt`, plus the
    #         `config` carrying the thread_id). It runs until interrupt() and pauses;
    #         the payload you passed to interrupt() surfaces under the result's
    #         "__interrupt__" key. Print it to see what's awaiting approval.
    #
    # TODO 4: resume on the SAME thread by invoking the app with `Command(resume=...)`
    #         (from langgraph.types) carrying the human's decision — the value flows
    #         back as interrupt()'s return in the tools node. Print the final message.
    #
    # Acceptance: with a "deny" decision, the email never sends and the agent
    # replans/explains instead.
    print("TODO: invoke, observe the pause, resume with Command(resume=...).")


if __name__ == "__main__":
    main()
