/**
 * Shared helper: build a tool-calling LangChain chat model for the 06b exercises.
 *
 * LangGraph runs on LangChain's chat-model interface (it needs `.bindTools()`),
 * so these framework exercises talk to `@langchain/*` directly — the documented
 * exception to the llm-core rule (see the module README). Outside the framework
 * tasks, keep using `getProvider()` from `@learn-ai/llm-core`.
 *
 * Defaults to local Ollama (zero cost). Switch with one env var:
 *   LANGGRAPH_MODEL_PROVIDER=ollama|openai|anthropic   (default: ollama)
 *
 * Install the package for the provider you pick:
 *   ollama     -> pnpm add @langchain/ollama      (then `ollama pull llama3.2`)
 *   openai     -> pnpm add @langchain/openai       (needs OPENAI_API_KEY)
 *   anthropic  -> pnpm add @langchain/anthropic    (needs ANTHROPIC_API_KEY)
 *
 * `pnpm tsx` transpiles without type-checking, so an un-installed provider only
 * fails at runtime if you actually select it.
 */

export async function getChatModel(temperature = 0) {
  const provider = (process.env.LANGGRAPH_MODEL_PROVIDER ?? "ollama").toLowerCase();

  if (provider === "ollama") {
    const { ChatOllama } = await import("@langchain/ollama");
    return new ChatOllama({
      model: process.env.OLLAMA_MODEL ?? "llama3.2",
      temperature,
    });
  }
  if (provider === "openai") {
    const { ChatOpenAI } = await import("@langchain/openai");
    return new ChatOpenAI({
      model: process.env.OPENAI_MODEL ?? "gpt-4o-mini",
      temperature,
    });
  }
  if (provider === "anthropic") {
    const { ChatAnthropic } = await import("@langchain/anthropic");
    return new ChatAnthropic({
      model: process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5-20251001",
      temperature,
    });
  }

  throw new Error(
    `Unknown LANGGRAPH_MODEL_PROVIDER=${provider} (use ollama|openai|anthropic)`,
  );
}
