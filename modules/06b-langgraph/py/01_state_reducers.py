"""
Task 1 — State, channels & reducers  🟡

What this teaches:
  - State is a typed dict; each field is a CHANNEL with a REDUCER.
  - A node returns ONLY the keys it changes. LangGraph merges each key through
    its channel's reducer:
      * default reducer (no annotation) = last-write-wins (overwrite)
      * operator.add on an int          = accumulate (sum)
      * add_messages                    = append + dedupe-by-id, coerce -> Messages
  - "Designing the state" is mostly "pick the right reducer per channel."

This file RUNS as-is (no model/API key needed). Your job is to PREDICT the output
first, then change a reducer and predict again — the exercises are in main().

How to run:
  uv run python modules/06b-langgraph/py/01_state_reducers.py
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph, add_messages

# ---------------------------------------------------------------------------
# State — three channels, three DIFFERENT reducers
# ---------------------------------------------------------------------------


class DemoState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # append + dedupe
    step_count: Annotated[int, operator.add]  # SUM each update
    last_tool: str  # no reducer = overwrite


# ---------------------------------------------------------------------------
# Nodes — each returns a PARTIAL update to all three channels
# ---------------------------------------------------------------------------


def node_a(state: DemoState) -> dict:
    return {
        "messages": [AIMessage(content="node A ran")],
        "step_count": 1,
        "last_tool": "search",
    }


def node_b(state: DemoState) -> dict:
    return {
        "messages": [AIMessage(content="node B ran")],
        "step_count": 1,
        "last_tool": "calculator",
    }


# ---------------------------------------------------------------------------
# Build — START -> a -> b -> END
# ---------------------------------------------------------------------------

graph = StateGraph(DemoState)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")
graph.add_edge("a", "b")
graph.add_edge("b", END)
app = graph.compile()


def main() -> None:
    initial: DemoState = {
        "messages": [HumanMessage(content="go")],
        "step_count": 0,
        "last_tool": "",
    }

    # TODO 1: PREDICT each line before you read the output.
    #   After both nodes run, what are messages / step_count / last_tool?
    #   (Answer: 3 messages, step_count 2, last_tool "calculator" — verify below.)
    for snapshot in app.stream(initial, stream_mode="values"):
        print(
            f"messages={len(snapshot['messages'])}  "
            f"step_count={snapshot['step_count']}  "
            f"last_tool={snapshot['last_tool']!r}"
        )

    # TODO 2: Change step_count's reducer (line ~36) from `operator.add` to a bare
    #         `int` (overwrite). PREDICT the new step_count, then re-run.
    #         (It becomes 1, not 2 — the last write wins instead of summing.)
    #
    # TODO 3: Do the same thought experiment for `messages`: drop `add_messages`
    #         and predict what `len(messages)` becomes. (Overwrite -> 1.)


if __name__ == "__main__":
    main()
