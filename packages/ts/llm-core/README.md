# @learn-ai/llm-core

The provider-agnostic LLM client used across every TypeScript exercise in the
course. Write your code against one small interface, then swap the underlying
model — **OpenAI, Anthropic (Claude), Ollama, or NVIDIA NIM** — by changing a
single environment variable.

> Why this exists is itself a lesson (modules 00–02): OpenAI's HTTP API became a
> de-facto standard, so one class covers OpenAI, Ollama, and NVIDIA; only
> Anthropic ships a distinct API and gets its own adapter.

## Install / build

It's a workspace package — already linked. From the repo root:

```bash
pnpm install
pnpm build:core      # compiles src → dist (run once, or `pnpm --filter @learn-ai/llm-core dev` to watch)
```

## Usage

```ts
import { getProvider } from "@learn-ai/llm-core";

const llm = getProvider();                 // reads LLM_PROVIDER from .env (default: ollama)
const { text, model, usage } = await llm.chat([
  { role: "system", content: "You are concise." },
  { role: "user", content: "What is a vector embedding?" },
]);
console.log(model, usage, text);

// Streaming
for await (const delta of llm.chatStream([{ role: "user", content: "Tell a joke" }])) {
  process.stdout.write(delta);
}

// Embeddings (not available on Anthropic — throws with a helpful message)
const { vectors } = await getProvider("ollama").embed(["hello", "world"]);
```

Force a specific provider: `getProvider("anthropic")`.

## The interface

```ts
interface LLMProvider {
  name: string;
  chatModel: string;
  embedModel: string;
  chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatResult>;
  chatStream(messages: ChatMessage[], options?: ChatOptions): AsyncIterable<string>;
  embed(input: string[]): Promise<EmbeddingResult>;
}
```

`ChatMessage` = `{ role: "system" | "user" | "assistant"; content: string }`.
`ChatOptions` = `{ temperature?, maxTokens?, stop?, model? }`.
`ChatResult` = `{ text, model, usage?, raw? }` (`raw` is the untouched provider
response, for when you want to inspect the real shape).

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
- `embed()` on the Anthropic provider throws on purpose (Claude has no
  embeddings endpoint) — use `openai`/`ollama`/`nvidia` for embedding work.

The Python twin lives at [`packages/py/llm_core`](../../py/llm_core/).
