"""03_course_mcp_server.py — Build an MCP server for this course.  🟢 (flagship)

What this teaches:
    Building an MCP server is the mirror image of consuming one (task 2).
    You define tools and resources; the MCP SDK handles the protocol, transport
    and schema serialisation. Any MCP client — Claude Code, the OpenAI connector,
    task 4's agent — can then discover and call your tools.

    This server exposes three tools designed for this course:

    search_docs(query: str) -> str
        Full-text search across all module README files in this repo.
        Returns the top matching excerpts with source paths.
        Pattern: same retrieve-from-corpus idea as module 05 RAG.

    read_module(module: str) -> str
        Return the full README.md for a given module (e.g. "06-agents").
        Useful for "what does module X cover?" queries.

    run_exam_question(module: str) -> str
        Return a quiz question for a module.
        Bonus: accept an `answer` argument and grade it (string-match or LLM judge).

    Transport: stdio (default). Run this server directly; point an MCP client at it.

    This is also the server task 4 will connect to.

How to run (from repo root):
    # Install mcp extra first:
    uv sync --extra mcp

    # Start the server (it stays alive waiting for client connections on stdin):
    uv run python modules/17-mcp/py/03_course_mcp_server.py

    # To test manually, pipe an MCP initialize request, or use task 2's client:
    MCP_SERVER_CMD="uv run python modules/17-mcp/py/03_course_mcp_server.py" \\
        uv run python modules/17-mcp/py/02_use_mcp_server.py

    # Claude Code / Cursor can also use it as a project MCP server:
    # Add to .claude/settings.json → "mcpServers":
    #   { "learn-ai": { "command": "uv", "args": ["run", "python", "modules/17-mcp/py/03_course_mcp_server.py"] } }

Python deps: mcp  (uv sync --extra mcp)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Corpus helpers — scan module READMEs
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent.parent  # learn-ai/
MODULES_DIR = REPO_ROOT / "modules"


def _all_readmes() -> list[tuple[str, str]]:
    """Return [(module_name, readme_text), ...] for all modules that have a README."""
    results = []
    for p in sorted(MODULES_DIR.glob("*/README.md")):
        module_name = p.parent.name
        try:
            text = p.read_text(encoding="utf-8")
            results.append((module_name, text))
        except OSError:
            pass
    return results


def _simple_search(query: str, top_k: int = 3) -> list[dict]:
    """Very simple TF-style search: score each README by keyword overlap.

    Returns a list of dicts: {module, excerpt, score}.
    (Task 5 of module 05 shows how to do this properly with embeddings.)
    """
    # TODO 1: Implement simple keyword search.
    #   a) Tokenise query (lower-case, split on whitespace/punctuation).
    #   b) For each (module_name, text) from _all_readmes():
    #      - Score = count of query tokens that appear in text.lower()
    #   c) Sort by score descending, return top_k as list of dicts:
    #      {"module": module_name, "excerpt": first 400 chars of text, "score": score}
    #   d) Return empty list if no tokens match.
    raise NotImplementedError("TODO 1: implement _simple_search")


def _read_module_readme(module: str) -> str:
    """Return the full README.md text for a module like '06-agents'.

    Accepts both exact folder names ('06-agents') and bare numbers ('6' or '06').
    """
    # TODO 2: Locate the README.
    #   a) Try MODULES_DIR / module / "README.md" directly.
    #   b) If not found, search MODULES_DIR.glob(f"*{module.lstrip('0')}*/README.md")
    #      to handle bare numbers like "6" or "06".
    #   c) Return the file contents, or a helpful error string if not found.
    raise NotImplementedError("TODO 2: implement _read_module_readme")


# ---------------------------------------------------------------------------
# Exam questions — one per module
# ---------------------------------------------------------------------------

EXAM_QUESTIONS: dict[str, dict] = {
    "00-setup": {
        "question": "What env var controls which LLM provider is used across all modules?",
        "answer": "LLM_PROVIDER",
    },
    "01-fundamentals": {
        "question": "What algorithm does BPE (Byte-Pair Encoding) use to build a vocabulary?",
        "answer": "merge the most frequent pair of tokens repeatedly",
    },
    "02-llm-integration": {
        "question": "What HTTP response technique does streaming use to deliver tokens incrementally?",
        "answer": "server-sent events",
    },
    "05-rag": {
        "question": "What are the five stages of a RAG pipeline?",
        "answer": "load, chunk, embed, retrieve, generate",
    },
    "06-agents": {
        "question": "In the ReAct pattern, what are the three components of each agent step?",
        "answer": "thought, action, observation",
    },
    "17-mcp": {
        "question": "What are the two standard MCP transport types?",
        "answer": "stdio and HTTP/SSE",
    },
}


def _get_exam_question(module: str) -> str:
    """Return the exam question for a module. Grade an answer if provided."""
    # TODO 3: Look up module in EXAM_QUESTIONS (try both exact and normalised key).
    #   Return a formatted string like:
    #   "Module: 06-agents\nQuestion: ...\n(Submit your answer with answer=<text>)"
    #   If module not found, return a list of available modules.
    raise NotImplementedError("TODO 3: implement _get_exam_question")


def _grade_answer(module: str, user_answer: str) -> str:
    """Simple string-match grader. Returns 'Correct!' or 'Incorrect. Hint: ...'."""
    # TODO 4 (stretch): Use the LLM as a judge:
    #   from llm_core import get_provider, ChatMessage
    #   llm = get_provider()
    #   Check if user_answer captures the key concepts from EXAM_QUESTIONS[module]["answer"].
    #   For now, implement a simple substring check (case-insensitive).
    raise NotImplementedError("TODO 4: implement _grade_answer")


# ---------------------------------------------------------------------------
# MCP server definition
# ---------------------------------------------------------------------------

def build_server():
    """Create and return the MCP server instance with all tools registered."""
    # TODO 5: Import and instantiate the MCP server.
    #   from mcp.server import Server
    #   from mcp.server.models import InitializationOptions
    #   import mcp.types as types
    #
    #   server = Server("learn-ai-course")
    raise NotImplementedError("TODO 5: import mcp and create server = Server('learn-ai-course')")

    # TODO 6: Register the list_tools handler.
    #   @server.list_tools()
    #   async def handle_list_tools() -> list[types.Tool]:
    #       return [
    #           types.Tool(
    #               name="search_docs",
    #               description="Search across all module READMEs by keyword.",
    #               inputSchema={
    #                   "type": "object",
    #                   "properties": {
    #                       "query": {"type": "string", "description": "Search query"},
    #                       "top_k": {"type": "integer", "description": "Max results", "default": 3},
    #                   },
    #                   "required": ["query"],
    #               },
    #           ),
    #           types.Tool(name="read_module", description="Return a module's README.",
    #               inputSchema={"type":"object","properties":{"module":{"type":"string"}},"required":["module"]}),
    #           types.Tool(name="run_exam_question", description="Get an exam question for a module.",
    #               inputSchema={"type":"object","properties":{
    #                   "module":{"type":"string"},
    #                   "answer":{"type":"string","description":"Optional: your answer to grade"}
    #               },"required":["module"]}),
    #       ]

    # TODO 7: Register the call_tool handler.
    #   @server.call_tool()
    #   async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    #       args = arguments or {}
    #       if name == "search_docs":
    #           results = _simple_search(args["query"], args.get("top_k", 3))
    #           text = json.dumps(results, indent=2) if results else "No results found."
    #       elif name == "read_module":
    #           text = _read_module_readme(args["module"])
    #       elif name == "run_exam_question":
    #           text = _get_exam_question(args["module"])
    #           if "answer" in args:
    #               text += "\n\n" + _grade_answer(args["module"], args["answer"])
    #       else:
    #           raise ValueError(f"Unknown tool: {name}")
    #       return [types.TextContent(type="text", text=text)]

    # return server  # TODO: un-comment when TODOs above are done


def main() -> None:
    """Run the MCP server over stdio."""
    # TODO 8: Run the server using the stdio transport.
    #   import asyncio
    #   from mcp.server.stdio import stdio_server
    #
    #   server = build_server()
    #
    #   async def run():
    #       async with stdio_server() as (read_stream, write_stream):
    #           await server.run(
    #               read_stream,
    #               write_stream,
    #               InitializationOptions(
    #                   server_name="learn-ai-course",
    #                   server_version="0.1.0",
    #                   capabilities=server.get_capabilities(
    #                       notification_options=NotificationOptions(),
    #                       experimental_capabilities={},
    #                   ),
    #               ),
    #           )
    #   asyncio.run(run())
    raise NotImplementedError("TODO 8: start the stdio MCP server")


if __name__ == "__main__":
    main()
