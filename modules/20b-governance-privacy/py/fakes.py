"""Deterministic, offline provider for the governance demo + tests.

It satisfies the shared ``llm_core`` :class:`LLMProvider` interface, so exercise
code only ever calls ``provider.chat(...)`` — no vendor SDK, no network, no key.
Swapping in the real client is one line (``get_provider()``); injecting this
fake is how the demo stays deterministic and how a test can inspect *exactly*
what crossed the provider boundary.

The reply is canned and never echoes the input, so the provider itself is not a
leak path — anything the test finds in ``recorded_messages`` was put there by
the caller, which is the point.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from llm_core import ChatMessage, ChatOptions, ChatResult, EmbeddingResult, TokenUsage


def _as_messages(messages: Iterable[ChatMessage | dict[str, str]]) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for m in messages:
        if isinstance(m, ChatMessage):
            out.append(m)
        else:
            out.append(ChatMessage(role=m["role"], content=m["content"]))  # type: ignore[index]
    return out


class RecordingProvider:
    """An ``LLMProvider`` that records every ``chat`` call for inspection."""

    name = "fake-recording"
    chat_model = "fake-chat-1"
    embed_model = "fake-embed-1"

    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult:
        self.calls.append(_as_messages(messages))
        # Canned reply — deterministic and independent of the input.
        return ChatResult(
            text="[fake] Support request acknowledged.",
            model=self.chat_model,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]:
        # Record and stream the canned reply in one chunk.
        text = self.chat(messages, options).text
        yield text

    def embed(self, input: list[str]) -> EmbeddingResult:
        # Deterministic, content-free vectors — no external call.
        vectors = [[float(len(s)), 0.0, 0.0] for s in input]
        return EmbeddingResult(vectors=vectors, model=self.embed_model)

    @property
    def recorded_messages(self) -> list[ChatMessage]:
        """The messages from the most recent ``chat`` call."""
        return self.calls[-1]
