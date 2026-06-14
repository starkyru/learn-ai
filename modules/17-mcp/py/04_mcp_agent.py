"""04_mcp_agent.py — Agent loop wired to MCP tools.  🟡

What this teaches:
    Task 3 built a standalone MCP server. Task 4 shows how to plug those
    tools into an LLM agent loop so the agent can use them autonomously.

    The pattern:
      1. Connect an MCP client to the course server (task 3).
      2. Discover tools via list_tools() — no hardcoded schemas needed.
      3. Convert MCP tool definitions to the provider's native tool format.
      4. Run a standard tool-calling loop (like module 06 Task 2).
      5. When the model picks an MCP tool, call it through the client session.

    This composability is MCP's main value: one server, many agents.
    The agent in this file will be able to answer questions like:
      "What is covered in module 06?" (→ read_module)
      "Search for RAG techniques" (→ search_docs)
      "Quiz me on module 05" (→ run_exam_question)

    Reuses: module 06 Task 2's tool-calling loop structure.

How to run (from repo root):
    # Terminal 1 — start the course server:
    uv run python modules/17-mcp/py/03_course_mcp_server.py

    # Terminal 2 — run the agent (it launches the server as a subprocess):
    LLM_PROVIDER=openai uv run python modules/17-mcp/py/04_mcp_agent.py
    LLM_PROVIDER=anthropic uv run python modules/17-mcp/py/04_mcp_agent.py

    # Default: launches the server automatically as a subprocess.

Environment variables:
    OPENAI_API_KEY / ANTHROPIC_API_KEY
    LLM_PROVIDER — "openai" (default) or "anthropic"

Python deps: mcp, openai or anthropic
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Command to launch the course MCP server as a subprocess
SERVER_CMD = [
    "uv", "run", "python",
    str(Path(__file__).parent / "03_course_mcp_server.py"),
]

QUESTION = "What does module 06 cover, and what is covered in the RAG module?"


# ---------------------------------------------------------------------------
# Helpers — MCP tool schemas → provider format
# ---------------------------------------------------------------------------

def mcp_tools_to_openai(tools) -> list[dict]:
    """Convert a list of MCP Tool objects to OpenAI function-calling format.

    MCP Tool: .name, .description, .inputSchema (JSON Schema dict)
    OpenAI:   { "type": "function", "function": { name, description, parameters } }
    """
    # TODO 1: Build the OpenAI tool list.
    #   return [
    #       {
    #           "type": "function",
    #           "function": {
    #               "name": tool.name,
    #               "description": tool.description or "",
    #               "parameters": tool.inputSchema,
    #           },
    #       }
    #       for tool in tools
    #   ]
    raise NotImplementedError("TODO 1: implement mcp_tools_to_openai")


def mcp_tools_to_anthropic(tools) -> list[dict]:
    """Convert a list of MCP Tool objects to Anthropic tool format.

    Anthropic: { name, description, input_schema: <JSON Schema> }
    """
    # TODO 2: Build the Anthropic tool list.
    #   return [
    #       {
    #           "name": tool.name,
    #           "description": tool.description or "",
    #           "input_schema": tool.inputSchema,
    #       }
    #       for tool in tools
    #   ]
    raise NotImplementedError("TODO 2: implement mcp_tools_to_anthropic")


# ---------------------------------------------------------------------------
# OpenAI agent loop with MCP
# ---------------------------------------------------------------------------

async def run_openai_mcp_agent(question: str) -> str:
    """Run an OpenAI tool-calling loop where tools are provided by MCP."""
    from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
    from mcp.client.stdio import stdio_client  # noqa: PLC0415
    from openai import OpenAI  # noqa: PLC0415

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    server_params = StdioServerParameters(
        command=SERVER_CMD[0], args=SERVER_CMD[1:]
    )

    # TODO 3: Implement the MCP + OpenAI agent loop.
    #   a) Open a stdio_client session and initialize it.
    #   b) Fetch tools: tool_list = (await session.list_tools()).tools
    #   c) Convert: openai_tools = mcp_tools_to_openai(tool_list)
    #   d) Standard OpenAI tool loop (module 06 Task 2 pattern):
    #      messages = [{"role": "user", "content": question}]
    #      while True:
    #          response = client.chat.completions.create(model=model, messages=messages, tools=openai_tools)
    #          choice = response.choices[0]
    #          if choice.finish_reason == "tool_calls":
    #              for tc in choice.message.tool_calls:
    #                  args = json.loads(tc.function.arguments)
    #                  # CALL MCP TOOL (not a local function!):
    #                  result = await session.call_tool(tc.function.name, arguments=args)
    #                  text = " ".join(b.text for b in result.content if b.type == "text")
    #                  print(f"  [tool] {tc.function.name}({args}) -> {text[:120]}...")
    #                  messages.append(choice.message)
    #                  messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})
    #          else:
    #              return choice.message.content or ""
    raise NotImplementedError("TODO 3: implement run_openai_mcp_agent")


# ---------------------------------------------------------------------------
# Anthropic agent loop with MCP
# ---------------------------------------------------------------------------

async def run_anthropic_mcp_agent(question: str) -> str:
    """Run an Anthropic tool-calling loop where tools are provided by MCP."""
    from mcp import ClientSession, StdioServerParameters  # noqa: PLC0415
    from mcp.client.stdio import stdio_client  # noqa: PLC0415
    import anthropic  # noqa: PLC0415

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

    client = anthropic.Anthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    server_params = StdioServerParameters(
        command=SERVER_CMD[0], args=SERVER_CMD[1:]
    )

    # TODO 4: Implement the MCP + Anthropic agent loop.
    #   Same structure as TODO 3 but with Anthropic's tool format.
    #   Key difference: tool results go back as:
    #     { "role": "user", "content": [{"type": "tool_result", "tool_use_id": ..., "content": ...}] }
    raise NotImplementedError("TODO 4: implement run_anthropic_mcp_agent")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    provider = os.getenv("LLM_PROVIDER", "openai")
    print(f"Provider : {provider}")
    print(f"Question : {QUESTION}\n")

    if provider == "anthropic":
        answer = await run_anthropic_mcp_agent(QUESTION)
    else:
        answer = await run_openai_mcp_agent(QUESTION)

    print(f"\nAnswer: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
