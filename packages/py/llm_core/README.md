# llm_core (Python)

The provider-agnostic LLM client used across every Python exercise in the
course. Write your code against one small interface, then swap the underlying
model — **OpenAI, Anthropic (Claude), Ollama, or NVIDIA NIM** — by changing a
single environment variable.

> Why this exists is itself a lesson (modules 00–02): OpenAI's HTTP API became a
> de-facto standard, so one class covers OpenAI, Ollama, and NVIDIA; only
> Anthropic ships a distinct API and gets its own adapter.

## Install

It's installed editable into the repo's uv environment automatically:

```bash
uv sync                       # from the repo root
```

## Usage

```python
from llm_core import get_provider, ChatMessage, ChatOptions

llm = get_provider()                       # reads LLM_PROVIDER from .env (default: ollama)
result = llm.chat([
    ChatMessage("system", "You are concise."),
    ChatMessage("user", "What is a vector embedding?"),
])
print(result.model, result.usage, result.text)

# messages can also be plain dicts:
llm.chat([{"role": "user", "content": "hi"}], ChatOptions(temperature=0.2))

# Streaming
for delta in llm.chat_stream([ChatMessage("user", "Tell a joke")]):
    print(delta, end="", flush=True)

# Embeddings (not available on Anthropic — raises NotImplementedError)
vecs = get_provider("ollama").embed(["hello", "world"]).vectors
```

Force a specific provider: `get_provider("anthropic")`.

## The interface

```python
class LLMProvider(Protocol):
    name: str
    chat_model: str
    embed_model: str
    def chat(self, messages, options: ChatOptions | None = None) -> ChatResult: ...
    def chat_stream(self, messages, options=None) -> Iterator[str]: ...
    def embed(self, input: list[str]) -> EmbeddingResult: ...
```

`messages` accepts `ChatMessage(role, content)` objects or `{"role", "content"}`
dicts. `ChatOptions(temperature=None, max_tokens=None, stop=None, model=None)`.
`ChatResult` has `.text`, `.model`, `.usage` (`.input_tokens` / `.output_tokens`),
and `.raw` (the untouched provider response, to inspect real shapes).

## Providers & env vars

| Provider | `LLM_PROVIDER` | Key | Notes |
| --- | --- | --- | --- |
| Ollama | `ollama` | none | local, free; default. `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL` |
| OpenAI | `openai` | `OPENAI_API_KEY` | `OPENAI_CHAT_MODEL`, `OPENAI_EMBED_MODEL` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL`; **no embeddings** |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | OpenAI-compatible; `NVIDIA_*` model vars |

See [`.env.example`](../../../.env.example) for the full list.

## Design notes / limits

- The interface is **deliberately small**. Advanced features (tool calling,
  structured output, multimodal, prompt caching) are taught per-provider in the
  modules using the underlying SDKs directly — not hidden behind a leaky
  abstraction. When an exercise says "go beyond the abstraction", that's why.
- `embed()` on the Anthropic provider raises on purpose (Claude has no
  embeddings endpoint) — use `openai`/`ollama`/`nvidia` for embedding work.

The TypeScript twin lives at [`packages/ts/llm-core`](../../ts/llm-core/).
