"""
Shared helper: build a tool-calling LangChain ChatModel for the 06b exercises.

LangGraph runs on LangChain's ChatModel interface (it needs `.bind_tools()`),
so these framework exercises talk to `langchain_*` directly — the documented
exception to the `llm_core` rule (see the module README). Everywhere OUTSIDE
the framework tasks you should still use `get_provider()` from `llm_core`.

Defaults to local Ollama (zero cost). Switch with one env var:
    LANGGRAPH_MODEL_PROVIDER=ollama|openai|anthropic   (default: ollama)

Install the matching package:
    ollama     -> uv pip install langchain-ollama   (then `ollama pull llama3.2`)
    openai     -> uv pip install langchain-openai    (needs OPENAI_API_KEY)
    anthropic  -> uv pip install langchain-anthropic (needs ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import os


def get_chat_model(temperature: float = 0.0):
    """Return a LangChain BaseChatModel that supports `.bind_tools(...)`."""
    provider = os.getenv("LANGGRAPH_MODEL_PROVIDER", "ollama").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=os.getenv("OLLAMA_MODEL", "llama3.2"), temperature=temperature)
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=temperature)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            temperature=temperature,
        )

    raise ValueError(f"Unknown LANGGRAPH_MODEL_PROVIDER={provider!r} (use ollama|openai|anthropic)")
