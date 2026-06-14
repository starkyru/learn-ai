"""
Task 2 — Native tool-calling agent  🟢

What this teaches:
  - OpenAI and Anthropic expose "tool use" / "function calling" natively:
    the model returns a structured JSON object describing which tool to call
    and with what arguments. No text parsing, no fragility.
  - The llm_core chat() abstraction does NOT expose tools — intentionally.
    Advanced features that differ across providers are taught at the SDK level
    so you see the real shape of each API (same philosophy as module 02).
  - Contrast: native tool calling is more reliable than Task 1's text parsing,
    but you're now locked into providers that support it.

Requires: OPENAI_API_KEY or ANTHROPIC_API_KEY in .env

How to run:
  # OpenAI (default):
  LLM_PROVIDER=openai uv run python modules/06-agents/py/02_native_tools.py
  # Anthropic:
  LLM_PROVIDER=anthropic uv run python modules/06-agents/py/02_native_tools.py
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Shared tool logic (same as Task 1)
# ---------------------------------------------------------------------------

def run_calculator(expression: str) -> str:
    """Evaluate a math expression string and return the result."""
    # TODO 1: Same implementation as Task 1's calculator.
    #         eval() is acceptable here for educational purposes.
    raise NotImplementedError("TODO: implement run_calculator")


def run_search(query: str) -> str:
    """Return a canned fact-lookup result."""
    # TODO 2: Same lookup table as Task 1's fake_search.
    raise NotImplementedError("TODO: implement run_search")


def dispatch_tool(name: str, args: dict) -> str:
    """Dispatch a tool call by name, using parsed args dict."""
    # TODO 3: Map tool name to function call.
    #         "calculator" -> run_calculator(args["expression"])
    #         "search"     -> run_search(args["query"])
    raise NotImplementedError("TODO: implement dispatch_tool")


# ---------------------------------------------------------------------------
# OpenAI native tool-calling loop
# ---------------------------------------------------------------------------

# TODO 4: Define tool schemas in OpenAI's format.
#         Each entry is a dict with: type="function", function={name, description, parameters}.
#         The parameters field is a JSON Schema object.
OPENAI_TOOLS: list[dict] = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "calculator",
    #         "description": "Evaluates a math expression and returns the result.",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "expression": {"type": "string", "description": "The math expression to evaluate."}
    #             },
    #             "required": ["expression"],
    #         },
    #     },
    # },
    # ... add search tool
]


def run_openai_agent(question: str) -> str:
    """Run a tool-calling agent loop using the OpenAI SDK directly."""
    from openai import OpenAI  # already installed as a dep of llm_core

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    print(f"\nOpenAI agent | model: {model}")
    print(f"Question: {question}\n")

    messages: list[dict] = [{"role": "user", "content": question}]

    # TODO 5: Implement the tool-calling loop:
    #   a) Call client.chat.completions.create(model=model, messages=messages, tools=OPENAI_TOOLS).
    #   b) Check response.choices[0].finish_reason:
    #        "tool_calls": iterate response.choices[0].message.tool_calls:
    #           i)   Parse tc.function.arguments as JSON.
    #           ii)  Call dispatch_tool(tc.function.name, args).
    #           iii) Append the assistant message, then a tool-result message:
    #                {"role": "tool", "tool_call_id": tc.id, "content": result}
    #           Continue the loop.
    #        "stop": return response.choices[0].message.content
    #   c) Log each step: tool name, args, result.
    #   d) Cap at 10 iterations to prevent infinite loops.

    raise NotImplementedError("TODO: implement run_openai_agent")


# ---------------------------------------------------------------------------
# Anthropic native tool-calling loop
# ---------------------------------------------------------------------------

# TODO 6: Define tool schemas in Anthropic's format.
#         Each entry: {name, description, input_schema: {type: "object", properties: {...}}}
ANTHROPIC_TOOLS: list[dict] = [
    # {
    #     "name": "calculator",
    #     "description": "...",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": { "expression": {"type": "string"} },
    #         "required": ["expression"],
    #     },
    # },
]


def run_anthropic_agent(question: str) -> str:
    """Run a tool-calling agent loop using the Anthropic SDK directly."""
    import anthropic  # already installed as a dep of llm_core

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    print(f"\nAnthropic agent | model: {model}")
    print(f"Question: {question}\n")

    messages: list[dict] = [{"role": "user", "content": question}]

    # TODO 7: Implement the Anthropic tool-calling loop.
    #   Anthropic differs from OpenAI:
    #     - stop_reason == "tool_use" (not "tool_calls")
    #     - response.content is a list of blocks; find blocks where block.type == "tool_use"
    #     - Tool results go back as:
    #         {"role": "user", "content": [
    #           {"type": "tool_result", "tool_use_id": block.id, "content": result}
    #         ]}
    #     - Use client.messages.create(model, max_tokens, tools, messages).

    raise NotImplementedError("TODO: implement run_anthropic_agent")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    question = (
        "What is the height of the Eiffel Tower in metres, and what is that in feet? "
        "(1 metre = 3.281 feet)"
    )

    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "anthropic":
        answer = run_anthropic_agent(question)
    else:
        answer = run_openai_agent(question)

    print("\nFinal Answer:", answer)

    # TODO 8 (stretch): Run both providers on the same question.
    #   Compare: number of tool calls, argument formats, parallel calls, token usage.


if __name__ == "__main__":
    main()
