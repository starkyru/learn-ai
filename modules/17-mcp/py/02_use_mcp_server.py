"""02_use_mcp_server.py — Connect to an existing MCP server.  🟢

What this teaches:
    The Model Context Protocol (MCP) is an open standard (Anthropic, 2024) for
    exposing tools, resources, and prompts to any LLM application. Instead of
    each app re-inventing how to call tools, every MCP server speaks the same
    protocol — and every MCP client (Claude Code, OpenAI, LangGraph, your own
    code) can talk to it.

    Transport layers:
      stdio  — server runs as a subprocess; communication over stdin/stdout.
               Simple, secure: the server process is local and sandboxed.
      HTTP/SSE — server runs as a web service; client connects via HTTP.
               Required for remote/hosted servers.

    The MCP SDK (`mcp` package) handles the wire protocol for you. You create a
    ClientSession, handshake (initialize), then:
      - list_tools()      → see what the server offers
      - list_resources()  → see what data sources are available
      - call_tool(name, args) → invoke a tool, get a result

    This file connects to Python's built-in `mcp` example server (or any server
    you point it at) and demonstrates the discovery + call lifecycle.

How to run (from repo root):
    # First make sure you have the mcp extra:
    uv sync --extra mcp

    # Run against the bundled example server:
    uv run python modules/17-mcp/py/02_use_mcp_server.py

    # Or point at any MCP server binary:
    MCP_SERVER_CMD="npx @modelcontextprotocol/server-filesystem /tmp" \\
        uv run python modules/17-mcp/py/02_use_mcp_server.py

Environment variables:
    MCP_SERVER_CMD  — shell command to launch the server (default: see below)

Python deps: mcp  (uv sync --extra mcp)
"""

from __future__ import annotations

import asyncio
import os
import shlex

from dotenv import load_dotenv

load_dotenv()

# Default: the MCP filesystem server (requires npx / Node to be installed).
# You can point this at any stdio MCP server binary.
DEFAULT_SERVER_CMD = "npx -y @modelcontextprotocol/server-filesystem /tmp"


# ---------------------------------------------------------------------------
# MCP client helpers
# ---------------------------------------------------------------------------

async def list_server_capabilities(server_cmd: str) -> None:
    """Connect to an MCP server via stdio and list its tools and resources."""
    # TODO 1: Import the MCP client classes.
    #   from mcp import ClientSession, StdioServerParameters
    #   from mcp.client.stdio import stdio_client
    #
    # TODO 2: Parse server_cmd into a list with shlex.split().
    #         StdioServerParameters expects command (str) and args (list[str]).
    #
    # TODO 3: Open a stdio_client context and create a ClientSession:
    #   async with stdio_client(server_params) as (read, write):
    #       async with ClientSession(read, write) as session:
    #           await session.initialize()   # MCP handshake
    #           ...
    #
    # TODO 4: Call session.list_tools() and print each tool's name + description.
    #         Tool shape: result.tools[i].name, result.tools[i].description
    #
    # TODO 5: Call session.list_resources() and print each resource's URI + name.
    #         (Some servers expose no resources — that's fine.)
    raise NotImplementedError("TODO 1-5: implement list_server_capabilities")


async def call_tool_demo(server_cmd: str, tool_name: str, args: dict) -> str:
    """Connect to an MCP server, call one tool, and return the text result."""
    # TODO 6: Reuse the connection pattern from list_server_capabilities.
    #   After initialize(), call:
    #     result = await session.call_tool(tool_name, arguments=args)
    #   MCP tool results contain a list of content blocks.
    #   Extract and join the text from blocks where block.type == "text":
    #     return " ".join(b.text for b in result.content if b.type == "text")
    raise NotImplementedError("TODO 6: implement call_tool_demo")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    server_cmd = os.getenv("MCP_SERVER_CMD", DEFAULT_SERVER_CMD)
    print(f"MCP server command: {server_cmd}\n")

    print("=== Listing server capabilities ===")
    # TODO 7: Call list_server_capabilities(server_cmd).
    # list_server_capabilities is async so await it.
    raise NotImplementedError("TODO 7: call list_server_capabilities and print results")

    # TODO 8: Call one tool that the server offers.
    #   For the filesystem server, try:
    #     tool_name = "list_directory"
    #     args = {"path": "/tmp"}
    #   For a different server, adjust to match what list_tools() returned.
    #
    # print("\n=== Calling a tool ===")
    # result = await call_tool_demo(server_cmd, tool_name, args)
    # print(f"Tool result:\n{result}")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
