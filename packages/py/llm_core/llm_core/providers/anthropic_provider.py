"""Anthropic (Claude) provider.

Claude does NOT use the OpenAI shape, so it gets its own class. Things to
notice vs. the OpenAI-compatible providers:
  1. The ``system`` prompt is a top-level parameter, not a message with
     role="system". We split it out here.
  2. ``max_tokens`` is REQUIRED by the Anthropic API (no default), so we
     always send one.
  3. Claude has no embeddings endpoint — ``embed()`` raises and points you at
     a provider that does. (Anthropic recommends Voyage AI in production.)
"""

from __future__ import annotations

from typing import Iterable, Iterator

import anthropic

from ..types import (
    ChatMessage,
    ChatOptions,
    ChatResult,
    EmbeddingResult,
    TokenUsage,
    to_messages,
)


def _split_system(messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
    system_parts = [m.content for m in messages if m.role == "system"]
    rest = [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.role != "system"
    ]
    system = "\n\n".join(system_parts) if system_parts else None
    return system, rest


class AnthropicProvider:
    name = "anthropic"
    embed_model = "(none — use openai/ollama/nvidia for embeddings)"

    def __init__(self, api_key: str, chat_model: str) -> None:
        self.chat_model = chat_model
        self._client = anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        opts = options or ChatOptions()
        system, rest = _split_system(to_messages(messages))
        model = opts.model or self.chat_model
        kwargs: dict = {
            "model": model,
            "max_tokens": opts.max_tokens or 1024,
            "messages": rest,
        }
        if system is not None:
            kwargs["system"] = system
        if opts.temperature is not None:
            kwargs["temperature"] = opts.temperature
        if opts.stop:
            kwargs["stop_sequences"] = opts.stop

        resp = self._client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if b.type == "text")
        return ChatResult(
            text=text,
            model=model,
            usage=TokenUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            raw=resp,
        )

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]:
        opts = options or ChatOptions()
        system, rest = _split_system(to_messages(messages))
        kwargs: dict = {
            "model": opts.model or self.chat_model,
            "max_tokens": opts.max_tokens or 1024,
            "messages": rest,
        }
        if system is not None:
            kwargs["system"] = system
        if opts.temperature is not None:
            kwargs["temperature"] = opts.temperature
        if opts.stop:
            kwargs["stop_sequences"] = opts.stop

        with self._client.messages.stream(**kwargs) as stream:
            yield from stream.text_stream

    def embed(self, input: list[str]) -> EmbeddingResult:
        raise NotImplementedError(
            "Anthropic has no embeddings endpoint. Set LLM_PROVIDER=openai "
            "(or ollama/nvidia) for embedding exercises, or use a dedicated "
            "embeddings provider like Voyage AI in production."
        )
