"""
Task 1 — ReAct loop from scratch  🔴

What this teaches:
  - An "agent" is a loop: LLM decides → tool runs → observation feeds back → repeat.
  - ReAct (Reason + Act) structures each step as Thought / Action / Observation
    text, all within a plain chat conversation. No special API needed.
  - Parsing the model's intent from free text is *fragile*. You'll feel why
    native tool-calling (Task 2) is an improvement.
  - Works with ANY provider including local Ollama.

How to run:
  uv run python modules/06-agents/py/01_react_loop.py

Note on tool calling:
  This file uses plain provider.chat() and text parsing — intentionally NOT the
  OpenAI/Anthropic tool-calling APIs. That means it works on ollama and any
  OpenAI-compatible provider. The parsing fragility is part of the lesson.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from llm_core import get_provider, ChatMessage, ChatOptions


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

@dataclass
class Tool:
    name: str
    description: str
    execute: Callable[[str], str]


def calculator(args: str) -> str:
    """Evaluate a simple math expression given as a plain string."""
    # TODO 1: Evaluate the (stripped) expression with Python's `eval()`.
    #         Wrap it in try/except and return an error message string on failure.
    #         WARNING: eval() is unsafe in production — this is a demo only.
    raise NotImplementedError("TODO: implement calculator")


def fake_search(args: str) -> str:
    """Return a canned answer for a small set of queries."""
    # TODO 2: Build a lookup dict with at least 4 entries.
    #         Normalise args (lower, strip) before lookup.
    #         Return a result string, or "No result found for: <query>".
    #         Suggested entries:
    #           "population of france"    -> "France has a population of ~68 million (2024)."
    #           "capital of france"       -> "The capital of France is Paris."
    #           "eiffel tower height"     -> "The Eiffel Tower is 330 metres tall."
    #           "year eiffel tower built" -> "The Eiffel Tower was built in 1889."
    raise NotImplementedError("TODO: implement fake_search")


# In-memory key-value store the agent can read.
_MEMORY_STORE: dict[str, str] = {
    "user-goal": "Find the height of the Eiffel Tower and compute 330 * 3.281.",
    "hint": "Use search to find the height, then calculator to convert metres to feet.",
}


def retrieve(args: str) -> str:
    """Look up a key in the in-memory store."""
    # TODO 3: Look up the (stripped) key in `_MEMORY_STORE`. If it's missing,
    #         return a "Not found: <key>" message instead of raising.
    raise NotImplementedError("TODO: implement retrieve")


TOOLS: dict[str, Tool] = {
    "calculator": Tool(
        name="calculator",
        description='Evaluates a simple math expression. Input: expression string, e.g. "12 * (3 + 4)".',
        execute=calculator,
    ),
    "search": Tool(
        name="search",
        description="Looks up a fact. Returns a canned answer for a small set of queries. Input: query string.",
        execute=fake_search,
    ),
    "retrieve": Tool(
        name="retrieve",
        description="Retrieves a stored note by key. Input: the key name.",
        execute=retrieve,
    ),
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    tool_descriptions = "\n".join(
        f"  {t.name}: {t.description}" for t in TOOLS.values()
    )
    return f"""You are a helpful AI assistant that solves problems step by step using tools.

You MUST respond in this EXACT format on every turn until you have the final answer:

Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <the input to pass to the tool>

When you have enough information to answer the original question, respond with:

Thought: <your final reasoning>
Final Answer: <your complete answer to the question>

Available tools:
{tool_descriptions}

Rules:
- Always start with "Thought:"
- Only use one action per response
- Never make up tool results — wait for the Observation
- Stop only with "Final Answer:\""""


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

@dataclass
class ParsedStep:
    thought: str = ""
    final_answer: str | None = None
    action: str | None = None
    action_input: str | None = None


def parse_model_output(text: str) -> ParsedStep:
    """Extract Thought / Action / Action Input / Final Answer from model text.

    TODO 4: Implement this parser.
    Strategy — scan the text line by line (or use regex) for these patterns:
      - "Thought:"     -> everything after the colon on that line (strip)
      - "Action:"      -> the tool name (strip)
      - "Action Input:" -> the raw argument string (strip)
      - "Final Answer:" -> everything after the colon (may span multiple lines)

    The function should NEVER raise — return empty strings for missing parts.
    """
    raise NotImplementedError("TODO: implement parse_model_output")


# ---------------------------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------------------------

def run_react_agent(question: str, max_steps: int = 10) -> str:
    """Run the ReAct loop for `question`, returning the agent's Final Answer."""
    provider = get_provider()
    print(f"\nProvider: {provider.name} / {provider.chat_model}")
    print(f"Question: {question}\n")
    print("=" * 60)

    messages: list[ChatMessage] = [
        ChatMessage("system", build_system_prompt()),
        ChatMessage("user", question),
    ]

    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")

        # TODO 5: Implement the loop body:
        #   a) Call provider.chat(messages) to get the model's response.
        #      Use ChatOptions(max_tokens=512, temperature=0) for more determinism.
        #   b) Print the raw model output.
        #   c) Call parse_model_output() on the result text.
        #   d) If parsed.final_answer is not None, print and return it.
        #   e) If parsed.action is set:
        #        i)  Look it up in TOOLS. If missing, set observation to an error msg.
        #        ii) Call tool.execute(parsed.action_input or "").
        #        iii) Build observation = f"Observation: {result}"
        #        iv) Print the observation.
        #        v)  Append the assistant message + a user message with the
        #            observation to `messages`, then continue.
        #   f) If neither action nor final_answer, break (malformed output).

        raise NotImplementedError("TODO: implement the ReAct loop body")

    return "Agent did not reach a final answer within the step limit."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    question = (
        "What is the height of the Eiffel Tower in metres, and what is that in feet? "
        "(1 metre = 3.281 feet — use the calculator tool)"
    )
    answer = run_react_agent(question)
    print("\n" + "=" * 60)
    print("Final Answer:", answer)

    # TODO 6 (stretch): Ask a second question that uses the retrieve tool:
    #   "What is my current goal? Then accomplish it."
    # Watch the agent use retrieve -> search -> calculator across multiple steps.


if __name__ == "__main__":
    main()
