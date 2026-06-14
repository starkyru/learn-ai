"""Shared types for the provider-agnostic LLM layer.

The whole point of this package: write your exercise code against ONE
interface (``LLMProvider``), then swap the underlying model — OpenAI, Claude,
a local Ollama model, or an NVIDIA-hosted model — by changing one env var.
That swap-ability is itself a core lesson (see modules/02-llm-integration).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]


@dataclass
class ChatMessage:
    role: Role
    content: str


@dataclass
class ChatOptions:
    temperature: float | None = None
    max_tokens: int | None = None
    stop: list[str] | None = None
    # Override the model id configured in env for this single call.
    model: str | None = None


@dataclass
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass
class ChatResult:
    text: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    raw: object | None = None  # the raw provider response, to inspect real shapes


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]  # one vector per input string, in order
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)


# Helper so callers can write messages as plain dicts OR ChatMessage objects.
def to_messages(
    messages: Iterable[ChatMessage | dict[str, str]],
) -> list[ChatMessage]:
    out: list[ChatMessage] = []
    for m in messages:
        if isinstance(m, ChatMessage):
            out.append(m)
        else:
            out.append(ChatMessage(role=m["role"], content=m["content"]))  # type: ignore[arg-type]
    return out


@runtime_checkable
class LLMProvider(Protocol):
    """The contract every provider implements. Kept small on purpose —
    advanced features (tools, JSON mode, etc.) are taught per-provider in the
    modules rather than hidden behind a leaky abstraction.
    """

    name: str
    chat_model: str
    embed_model: str

    def chat(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> ChatResult: ...

    def chat_stream(
        self,
        messages: Iterable[ChatMessage | dict[str, str]],
        options: ChatOptions | None = None,
    ) -> Iterator[str]: ...

    def embed(self, input: list[str]) -> EmbeddingResult: ...
