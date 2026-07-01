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
    # TODO 1: Map each MCP tool to an OpenAI function-tool dict (a `list[dict]`).
    #   OpenAI nests the tool under a "function" key: {"type": "function",
    #   "function": {name, description, parameters}}. Pull name/description from
    #   each tool (default description to "" when missing) and pass the tool's
    #   .inputSchema straight through as "parameters".
    raise NotImplementedError("TODO 1: implement mcp_tools_to_openai")


def mcp_tools_to_anthropic(tools) -> list[dict]:
    """Convert a list of MCP Tool objects to Anthropic tool format.

    Anthropic: { name, description, input_schema: <JSON Schema> }
    """
    # TODO 2: Map each MCP tool to an Anthropic tool dict (a `list[dict]`).
    #   Anthropic keeps it flat: {name, description, input_schema}. Same fields
    #   as TODO 1 but the schema key is "input_schema" (fed from .inputSchema),
    #   and there's no "function" wrapper.
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
    #   a) Open a stdio_client(server_params) session (same connect/initialize
    #      pattern as task 2) and await session.initialize().
    #   b) Fetch the server's tools via session.list_tools() and convert them
    #      with mcp_tools_to_openai().
    #   c) Run the module-06 tool loop: start messages with the user question,
    #      then loop calling client.chat.completions.create(model, messages,
    #      tools). While finish_reason is "tool_calls", for each tool call parse
    #      its JSON arguments and — crucially — dispatch it by awaiting
    #      session.call_tool(name, arguments=...) rather than a local function.
    #      Join the text blocks of the result, append the assistant message and
    #      a role="tool" message (carrying tool_call_id and the result text),
    #      then loop. When finish_reason is not "tool_calls", return the message
    #      content. print() each tool call for tracing.
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
