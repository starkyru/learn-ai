"""llm_core — provider-agnostic LLM client for the learn-ai course.

Usage in any exercise::

    from llm_core import get_provider, ChatMessage

    llm = get_provider()                 # reads LLM_PROVIDER from .env
    result = llm.chat([ChatMessage("user", "hi")])
    print(result.text)

Force a specific provider::

    claude = get_provider("anthropic")
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

from .providers import AnthropicProvider, OpenAICompatibleProvider
from .types import (
    ChatMessage,
    ChatOptions,
    ChatResult,
    EmbeddingResult,
    LLMProvider,
    TokenUsage,
)

load_dotenv()

__all__ = [
    "get_provider",
    "ChatMessage",
    "ChatOptions",
    "ChatResult",
    "EmbeddingResult",
    "LLMProvider",
    "TokenUsage",
    "AnthropicProvider",
    "OpenAICompatibleProvider",
]


def _need(value: str | None, var_name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing env var {var_name}. Copy .env.example to .env and fill it in.")
    return value


def get_provider(name: str | None = None) -> LLMProvider:
    provider = name or os.getenv("LLM_PROVIDER", "ollama")

    if provider == "openai":
        return OpenAICompatibleProvider(
            name="openai",
            api_key=_need(os.getenv("OPENAI_API_KEY"), "OPENAI_API_KEY"),
            chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        )

    if provider == "anthropic":
        return AnthropicProvider(
            api_key=_need(os.getenv("ANTHROPIC_API_KEY"), "ANTHROPIC_API_KEY"),
            chat_model=os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8"),
        )

    if provider == "ollama":
        # Ollama needs no real key, but the OpenAI SDK requires a non-empty string.
        return OpenAICompatibleProvider(
            name="ollama",
            api_key="ollama",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            chat_model=os.getenv("OLLAMA_CHAT_MODEL", "llama3.2"),
            embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        )

    if provider == "nvidia":
        return OpenAICompatibleProvider(
            name="nvidia",
            api_key=_need(os.getenv("NVIDIA_API_KEY"), "NVIDIA_API_KEY"),
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            chat_model=os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.1-8b-instruct"),
            embed_model=os.getenv("NVIDIA_EMBED_MODEL", "nvidia/llama-3.2-nv-embedqa-1b-v2"),
        )

    if provider == "lmstudio":
        # LM Studio exposes an OpenAI-compatible server; no real key needed.
        return OpenAICompatibleProvider(
            name="lmstudio",
            api_key="lm-studio",
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            chat_model=os.getenv("LMSTUDIO_CHAT_MODEL", "google/gemma-4-12b-qat"),
            embed_model=os.getenv("LMSTUDIO_EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5"),
        )

    if provider == "gemini":
        # Google Gemini exposes an OpenAI-compatible endpoint, so it slots into
        # the same adapter — just a different base_url + key + model ids.
        return OpenAICompatibleProvider(
            name="gemini",
            api_key=_need(os.getenv("GEMINI_API_KEY"), "GEMINI_API_KEY"),
            base_url=os.getenv(
                "GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai/",
            ),
            chat_model=os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash"),
            embed_model=os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001"),
        )

    raise RuntimeError(
        f'Unknown provider "{provider}". Use one of: openai, anthropic, ollama, nvidia, lmstudio, gemini.'
    )
