/**
 * Entry point + provider registry.
 *
 * Usage in any exercise:
 *
 *   import { getProvider } from "@learn-ai/llm-core";
 *   const llm = getProvider();              // reads LLM_PROVIDER from .env
 *   const { text } = await llm.chat([{ role: "user", content: "hi" }]);
 *
 * Or force a specific one:
 *
 *   const claude = getProvider("anthropic");
 */

import "dotenv/config";
import { OpenAICompatibleProvider } from "./providers/openai-compatible.js";
import { AnthropicProvider } from "./providers/anthropic.js";
import type { LLMProvider } from "./types.js";

export * from "./types.js";
export { OpenAICompatibleProvider } from "./providers/openai-compatible.js";
export { AnthropicProvider } from "./providers/anthropic.js";

export type ProviderName = "openai" | "anthropic" | "ollama" | "nvidia" | "lmstudio";

function need(value: string | undefined, varName: string): string {
  if (!value) {
    throw new Error(
      `Missing env var ${varName}. Copy .env.example to .env and fill it in.`,
    );
  }
  return value;
}

export function getProvider(name?: ProviderName): LLMProvider {
  const provider = (name ?? process.env.LLM_PROVIDER ?? "ollama") as ProviderName;

  switch (provider) {
    case "openai":
      return new OpenAICompatibleProvider({
        name: "openai",
        apiKey: need(process.env.OPENAI_API_KEY, "OPENAI_API_KEY"),
        chatModel: process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini",
        embedModel: process.env.OPENAI_EMBED_MODEL ?? "text-embedding-3-small",
      });

    case "anthropic":
      return new AnthropicProvider({
        apiKey: need(process.env.ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY"),
        chatModel: process.env.ANTHROPIC_MODEL ?? "claude-opus-4-8",
      });

    case "ollama":
      // Ollama needs no real key, but the OpenAI SDK requires a non-empty string.
      return new OpenAICompatibleProvider({
        name: "ollama",
        apiKey: "ollama",
        baseURL: process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1",
        chatModel: process.env.OLLAMA_CHAT_MODEL ?? "llama3.2",
        embedModel: process.env.OLLAMA_EMBED_MODEL ?? "nomic-embed-text",
      });

    case "nvidia":
      return new OpenAICompatibleProvider({
        name: "nvidia",
        apiKey: need(process.env.NVIDIA_API_KEY, "NVIDIA_API_KEY"),
        baseURL: process.env.NVIDIA_BASE_URL ?? "https://integrate.api.nvidia.com/v1",
        chatModel: process.env.NVIDIA_CHAT_MODEL ?? "meta/llama-3.1-8b-instruct",
        embedModel:
          process.env.NVIDIA_EMBED_MODEL ?? "nvidia/llama-3.2-nv-embedqa-1b-v2",
      });

    case "lmstudio":
      // LM Studio exposes an OpenAI-compatible server; no real key needed.
      return new OpenAICompatibleProvider({
        name: "lmstudio",
        apiKey: "lm-studio",
        baseURL: process.env.LMSTUDIO_BASE_URL ?? "http://localhost:1234/v1",
        chatModel: process.env.LMSTUDIO_CHAT_MODEL ?? "google/gemma-4-12b-qat",
        embedModel:
          process.env.LMSTUDIO_EMBED_MODEL ?? "text-embedding-nomic-embed-text-v1.5",
      });

    default:
      throw new Error(
        `Unknown provider "${provider}". Use one of: openai, anthropic, ollama, nvidia, lmstudio.`,
      );
  }
}
