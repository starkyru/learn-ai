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

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# LangGraph imports
# ---------------------------------------------------------------------------

# TODO 1: Import the LangGraph building blocks you'll wire together below:
#   - from `langgraph.graph`: the graph builder, plus the START / END sentinels
#     (and the `add_messages` reducer used by the state in TODO 2).
#   - from `langgraph.checkpoint.memory`: the in-memory checkpointer (stretch TODO 10).
#   - from `langchain_core.messages`: the message classes you'll construct/inspect
#     (Human / AI / Tool / Base).
#   - from `langchain_core.tools`: the `tool` decorator.
#
# You'll also need a ChatModel that supports tool-calling.
# Option A (recommended): use langchain_openai or langchain_anthropic
#   (e.g. `pip install langchain-openai`, then import its ChatOpenAI class).
# Option B: write a thin LangChain-compatible adapter around llm_core's provider.
#   LangChain's BaseChatModel interface is more involved — Option A is simpler.
#
# This file assumes you'll install langchain_openai separately, or switch to
# the adapter approach. Pick one and document your choice in a comment.


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# TODO 2: Define the agent state as a TypedDict with a single `messages` field:
#         a list of BaseMessage. Annotate that field with the `add_messages`
#         reducer so each node's returned messages are APPENDED to state rather
#         than replacing it (use typing.Annotated).


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

# TODO 3: Define a `calculator` and a `search` tool by decorating typed Python
#         functions with `@tool` (the decorator turns a typed function into a
#         LangChain Tool, and its docstring becomes the tool description the model
#         reads — so write a clear one-line docstring for each).
#         - calculator(expression: str) -> str : same eval-in-try/except behaviour
#           as Task 1's calculator.
#         - search(query: str) -> str : same small canned lookup table as Task 1.

tools: list = []  # TODO: replace with your two decorated tool functions


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

# TODO 4: Instantiate your chat model (reading the API key from the environment)
#         and bind the `tools` list to it with `.bind_tools(...)`, keeping the
#         tool-aware model in its own variable.

# TODO 5: Implement `agent_node(state) -> dict`: invoke the tool-aware model on
#         the current `state["messages"]` and return a dict whose `messages` value
#         is a list containing just that response (the reducer appends it).

# TODO 6: Implement `tools_node(state) -> dict`: look at the last message (the AI
#         message carrying tool_calls). Build a name->tool lookup, and for each
#         tool_call invoke the matching tool on its args, wrapping each result in a
#         ToolMessage tagged with that call's id. Return them under `messages`.

# TODO 7: Implement `should_continue(state) -> str`: inspect the last message — if
#         it has tool_calls, route to the "tools" node; otherwise return END.


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

# TODO 8: Build a StateGraph over your AgentState. Add the "agent" and "tools"
#         nodes, then wire the edges so the cycle is:
#           START -> agent, a CONDITIONAL edge from "agent" (using should_continue)
#           to either "tools" or END, and a plain edge back from "tools" -> "agent".
#         Compile it to an app (pass checkpointer=MemorySaver() for persistence,
#         see stretch TODO 10).


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    question = (
        "What is the height of the Eiffel Tower in metres, "
        "and what is that in feet? (1 metre = 3.281 feet)"
    )
    print(f"Question: {question}\n")

    # TODO 9: Stream the graph over an initial state whose `messages` is a single
    #         HumanMessage(question). Iterate the stream; each yielded step is a
    #         {node_name: node_output} dict — pull out the node name and its output
    #         messages and print each message's class name and content so you can
    #         watch the agent -> tools -> agent cycle unfold.
    #         (If you add a checkpointer, also pass a config with a thread_id.)

    print("TODO: compile the graph (see TODOs above) and invoke it here.")

    # TODO 10 (stretch): Add a MemorySaver checkpointer.
    #   Ask two questions in sequence with the same thread_id.
    #   Confirm the agent remembers the first answer when answering the second.


if __name__ == "__main__":
    main()
