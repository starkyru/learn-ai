"""OpenAI-compatible provider.

KEY LESSON: OpenAI's HTTP API became a de-facto standard. OpenAI itself,
NVIDIA NIM, Ollama, vLLM, LM Studio, Together, Groq, and many others all expose
the SAME ``/v1/chat/completions`` and ``/v1/embeddings`` shape. So one class —
just a different ``base_url`` + ``api_key`` + model id — covers three of our
four providers. Only Anthropic ships its own distinct API.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from openai import OpenAI

from ..types import (
    ChatMessage,
    ChatOptions,
    ChatResult,
    EmbeddingResult,
    TokenUsage,
    to_messages,
)


class OpenAICompatibleProvider:
    def __init__(
        self,
        name: str,
        api_key: str,
        chat_model: str,
        embed_model: str,
        base_url: str | None = None,
    ) -> None:
        self.name = name
        self.chat_model = chat_model
        self.embed_model = embed_model
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def _payload(self, messages: Iterable[ChatMessage | dict], options: ChatOptions | None):
        opts = options or ChatOptions()
        msgs = [{"role": m.role, "content": m.content} for m in to_messages(messages)]
        kwargs: dict = {"model": opts.model or self.chat_model, "messages": msgs}
        if opts.temperature is not None:
            kwargs["temperature"] = opts.temperature
        if opts.max_tokens is not None:
            kwargs["max_tokens"] = opts.max_tokens
        if opts.stop:
            kwargs["stop"] = opts.stop
        return kwargs

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        kwargs = self._payload(messages, options)
        resp = self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        return ChatResult(
            text=resp.choices[0].message.content or "",
            model=kwargs["model"],
            usage=TokenUsage(
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
            ),
            raw=resp,
        )

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]:
        kwargs = self._payload(messages, options)
        kwargs["stream"] = True
        for chunk in self._client.chat.completions.create(**kwargs):
            # Some OpenAI-compatible servers (LM Studio, vLLM, …) emit chunks with
            # an empty `choices` list — e.g. a final usage-only chunk. Skip them.
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def embed(self, input: list[str]) -> EmbeddingResult:
        resp = self._client.embeddings.create(model=self.embed_model, input=input)
        return EmbeddingResult(
            vectors=[d.embedding for d in resp.data],
            model=self.embed_model,
            usage=TokenUsage(input_tokens=getattr(resp.usage, "prompt_tokens", None)),
        )
