"""01_modern_agent_api.py — Modern agent APIs vs. manual tool loops.  🟢

What this teaches:
    Module 06 built a tool-calling agent from scratch: manually call the SDK,
    check finish_reason / stop_reason, dispatch tools, append messages, loop.
    That approach works everywhere but requires you to manage the entire protocol.

    OpenAI's Responses API (2025) and Anthropic's agent patterns move some of that
    bookkeeping server-side. The Responses API supports hosted tools (web search,
    code interpreter, file search) and remote MCP servers — you describe what you
    want and the platform handles the loop on its end. Anthropic's approach keeps
    the loop client-side but adds extended thinking and richer tool use patterns.

    Key contrasts:
      Manual loop (module 06):
        - Works with any provider including Ollama
        - You control every step; great for debugging
        - You manage the message history yourself

      OpenAI Responses API:
        - Hosted tools run server-side (no extra round-trips for web_search)
        - `previous_response_id` chains turns without re-sending full history
        - Built-in MCP connector: point at a URL, get tools automatically

      Anthropic:
        - Tool use stays client-side but extended thinking adds a reasoning step
        - Tool schemas in a slightly different shape than OpenAI's

    When to use which:
        - Prototyping / Ollama: manual loop (module 06)
        - Production with web search / code: Responses API
        - Anthropic with reasoning: Claude + extended thinking
        - Cross-provider tools: MCP (tasks 2-4)

How to run (from repo root):
    # OpenAI Responses API:
    LLM_PROVIDER=openai uv run python modules/17-mcp/py/01_modern_agent_api.py

    # Anthropic tool use:
    LLM_PROVIDER=anthropic uv run python modules/17-mcp/py/01_modern_agent_api.py

Environment variables:
    OPENAI_API_KEY      — required for OpenAI path
    ANTHROPIC_API_KEY   — required for Anthropic path
    LLM_PROVIDER        — "openai" (default) or "anthropic"

Python deps: openai, anthropic (both installed as llm_core deps)
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

QUESTION = (
    "What is the capital of France, and what is 1337 * 42? "
    "Answer both questions."
)


# ---------------------------------------------------------------------------
# Shared tool logic (same as module 06 — reimported for clarity)
# ---------------------------------------------------------------------------

def run_calculator(expression: str) -> str:
    """Evaluate a simple math expression and return the result as a string."""
    # TODO 1: Use eval() to evaluate the expression (acceptable for learning).
    #         Catch exceptions and return an error string instead of raising.
    #         Example: eval("1337 * 42") -> "56154"
    raise NotImplementedError("TODO 1: implement run_calculator")


def run_lookup(query: str) -> str:
    """Return a canned answer for common geography/fact queries."""
    # TODO 2: Build a small lookup dict mapping lowercased query keywords to answers.
    #         e.g. {"france": "Paris", "germany": "Berlin"}
    #         If no key matches, return "Unknown".
    raise NotImplementedError("TODO 2: implement run_lookup")


def dispatch(name: str, args: dict) -> str:
    """Route a tool call by name to the right function."""
    # TODO 3: Map "calculator" -> run_calculator, "lookup" -> run_lookup.
    #         Raise ValueError for unknown tool names.
    raise NotImplementedError("TODO 3: implement dispatch")


# ---------------------------------------------------------------------------
# Task A — OpenAI Responses API
# ---------------------------------------------------------------------------

def run_openai_responses(question: str) -> str:
    """Use the OpenAI Responses API to answer a question with tools.

    The Responses API differs from Chat Completions:
      - client.responses.create() instead of client.chat.completions.create()
      - `input` instead of `messages`
      - `previous_response_id` chains turns (server keeps the conversation)
      - Built-in tool type "web_search_preview" runs server-side
      - Custom function tools work the same as Chat Completions

    Contrast with module 06 Task 2:
      - Same tool schemas (JSON Schema parameters)
      - Same loop structure (check finish reason, dispatch, append result)
      - Difference: message threading via response IDs instead of a list
    """
    from openai import OpenAI  # noqa: PLC0415

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # TODO 4: Define tools in Responses-API format (a `list[dict]`).
    #   Each tool is a flat dict with keys "type": "function", "name",
    #   "description", and "parameters" (a JSON Schema object). Note the shape
    #   is flatter than Chat Completions — name/parameters sit at the top level,
    #   not nested under a "function" key. Define both "calculator" (takes an
    #   "expression" string) and "lookup" (takes a "query" string).
    tools: list[dict] = []  # TODO 4: replace with real tool defs

    # TODO 5: Run the Responses API loop.
    #   a) Call client.responses.create(...) passing model, input=question, tools.
    #   b) response.output is a list of output items. Items whose type is
    #      "message" hold the text answer; items whose type is "function_call"
    #      need to be dispatched and their results injected.
    #   c) For each function_call item: parse item.arguments (JSON string) with
    #      json.loads and pass to dispatch(item.name, ...). Send the result back
    #      by calling client.responses.create AGAIN with previous_response_id set
    #      to the prior response.id, and input=[<a "function_call_output" dict
    #      carrying item.call_id and the result>], plus tools.
    #   d) Repeat until the output has no more function_call items; then extract
    #      and return the text from the message item.
    #   e) print() each tool call and its result so you can trace the loop.
    raise NotImplementedError("TODO 5: implement Responses API loop")


# ---------------------------------------------------------------------------
# Task B — Anthropic tool use (client-side loop, same as module 06 but annotated)
# ---------------------------------------------------------------------------

def run_anthropic_tools(question: str) -> str:
    """Use the Anthropic SDK with tool use to answer a question.

    Anthropic's tool loop is client-side (unlike OpenAI's Responses API
    which chains via response IDs). The structure mirrors module 06 Task 2
    but here we annotate the contrast explicitly.

    Shape reminder:
      - Tools: [{ name, description, input_schema: { type: "object", ... } }]
      - Stop when stop_reason == "end_turn" (no tool_use blocks in content)
      - Tool results: role="user", content=[{ type: "tool_result", ... }]
    """
    import anthropic  # noqa: PLC0415

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # TODO 6: Define Anthropic tool schemas (a `list[dict]`).
    #   Anthropic uses a different key than OpenAI: each tool has "name",
    #   "description", and "input_schema" (the JSON Schema object — note the key
    #   is input_schema, not parameters). Define "calculator" and "lookup".
    tools: list[dict] = []  # TODO 6: replace with real tool defs

    messages: list[dict] = [{"role": "user", "content": question}]

    # TODO 7: Implement the Anthropic tool-calling loop.
    #   a) Call client.messages.create(...) with model, tools, messages, and a
    #      max_tokens budget.
    #   b) Loop while response.stop_reason == "tool_use":
    #        - Select the content blocks whose type == "tool_use".
    #        - For each, call dispatch(block.name, block.input).
    #        - Append the assistant's message (its full content list) to
    #          `messages`, then append a role="user" message whose content is a
    #          list of "tool_result" blocks — each carrying the block.id (as
    #          tool_use_id) and the dispatch result. Then create again.
    #   c) When stop_reason == "end_turn", pull the text out of the text content
    #      block and return it.
    #   d) print() each step so you can trace the loop.
    raise NotImplementedError("TODO 7: implement Anthropic tool loop")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    provider = os.getenv("LLM_PROVIDER", "openai")
    print(f"Provider : {provider}")
    print(f"Question : {QUESTION}\n")

    if provider == "anthropic":
        answer = run_anthropic_tools(QUESTION)
    else:
        answer = run_openai_responses(QUESTION)

    print(f"\nAnswer: {answer}")

    # TODO 8 (stretch): Run both providers on the same question.
    #   Compare: how many round-trips each needs, the tool call format,
    #   and whether the Responses API's response-ID chaining is more ergonomic
    #   than managing the messages list yourself.


if __name__ == "__main__":
    main()
