"""
Task 4 — Framework agent with LangGraph  🟢

What this teaches:
  - LangGraph models an agent as a typed state machine. Nodes transform state,
    edges (including conditional edges) decide what runs next.
  - The ReAct loop from Task 1 is just a graph with a cycle:
      agent_node -> tools_node -> agent_node -> END
  - Frameworks give you persistence, streaming, checkpointing, and tracing
    almost for free — at the cost of abstraction depth.
  - Building the from-scratch version first (Task 1) makes the framework
    transparent instead of magical.

Setup:
  uv sync --extra agents     # installs langgraph + langchain-core

How to run:
  uv run python modules/06-agents/py/04_framework.py
"""

from __future__ import annotations

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# LangGraph imports
# ---------------------------------------------------------------------------

# TODO 1: Import the LangGraph building blocks.
#         from langgraph.graph import StateGraph, END, START
#         from langgraph.checkpoint.memory import MemorySaver
#         from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
#         from langchain_core.tools import tool
#
# You'll also need a ChatModel that supports tool-calling.
# Option A (recommended): use langchain_openai or langchain_anthropic.
#   - pip install langchain-openai  (or langchain-anthropic)
#   - from langchain_openai import ChatOpenAI
# Option B: write a thin LangChain-compatible adapter around llm_core's provider.
#   LangChain's BaseChatModel interface is more involved — Option A is simpler.
#
# This file assumes you'll install langchain_openai separately, or switch to
# the adapter approach. Pick one and document your choice in a comment.

# from langgraph.graph import StateGraph, END, START
# from langgraph.checkpoint.memory import MemorySaver
# from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
# from langchain_core.tools import tool
# from langchain_openai import ChatOpenAI


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# TODO 2: Define the agent state TypedDict.
#         LangGraph accumulates messages using Annotated + operator.add (or
#         the built-in add_messages reducer from langchain_core.messages).
#
# from langchain_core.messages import add_messages
#
# class AgentState(TypedDict):
#     messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

# TODO 3: Define tools using the @tool decorator from langchain_core.
#         The decorator turns a typed Python function into a LangChain Tool.
#
# @tool
# def calculator(expression: str) -> str:
#     """Evaluates a simple math expression. Input: expression string."""
#     try:
#         return str(eval(expression))  # noqa: S307 — educational demo
#     except Exception as e:
#         return f"Error: {e}"
#
# @tool
# def search(query: str) -> str:
#     """Looks up a fact from a small knowledge base."""
#     db = {
#         "eiffel tower height": "The Eiffel Tower is 330 metres tall.",
#         "capital of france": "The capital of France is Paris.",
#     }
#     return db.get(query.lower().strip(), f"No result found for: {query}")

tools: list = []  # TODO: replace with [calculator, search]


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

# TODO 4: Create the model with tools bound.
#   model = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
#   model_with_tools = model.bind_tools(tools)

# TODO 5: Implement the agent node.
#   def agent_node(state: AgentState) -> dict:
#       response = model_with_tools.invoke(state["messages"])
#       return {"messages": [response]}

# TODO 6: Implement the tools node.
#   def tools_node(state: AgentState) -> dict:
#       last = state["messages"][-1]   # AIMessage with tool_calls
#       results = []
#       tools_by_name = {t.name: t for t in tools}
#       for call in last.tool_calls:
#           result = tools_by_name[call["name"]].invoke(call["args"])
#           results.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
#       return {"messages": results}

# TODO 7: Implement the routing function.
#   def should_continue(state: AgentState) -> str:
#       last = state["messages"][-1]
#       return "tools" if getattr(last, "tool_calls", None) else END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

# TODO 8: Wire up the graph.
#
# workflow = StateGraph(AgentState)
# workflow.add_node("agent", agent_node)
# workflow.add_node("tools", tools_node)
# workflow.add_edge(START, "agent")
# workflow.add_conditional_edges("agent", should_continue)
# workflow.add_edge("tools", "agent")
# app = workflow.compile()   # add checkpointer=MemorySaver() for persistence


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    question = (
        "What is the height of the Eiffel Tower in metres, "
        "and what is that in feet? (1 metre = 3.281 feet)"
    )
    print(f"Question: {question}\n")

    # TODO 9: Invoke the graph and stream the steps.
    #
    # from langchain_core.messages import HumanMessage
    # config = {"configurable": {"thread_id": "session-1"}}
    # for step in app.stream({"messages": [HumanMessage(content=question)]}, config):
    #     node_name, output = next(iter(step.items()))
    #     print(f"\n[{node_name}]")
    #     for msg in output["messages"]:
    #         print(f"  {msg.__class__.__name__}: {msg.content}")

    print("TODO: compile the graph (see TODOs above) and invoke it here.")

    # TODO 10 (stretch): Add a MemorySaver checkpointer.
    #   Ask two questions in sequence with the same thread_id.
    #   Confirm the agent remembers the first answer when answering the second.


if __name__ == "__main__":
    main()
