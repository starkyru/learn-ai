/**
 * Anthropic (Claude) provider.
 *
 * Claude does NOT use the OpenAI shape, so it gets its own class. Two things
 * to notice vs. the OpenAI-compatible providers:
 *   1. The `system` prompt is a top-level parameter, not a message with
 *      role:"system". We split it out here.
 *   2. `max_tokens` is REQUIRED by the Anthropic API (no default), so we
 *      always send one.
 *   3. Claude has no embeddings endpoint — `embed()` throws and points you at
 *      a provider that does. (Anthropic recommends Voyage AI in production.)
 */

import Anthropic from "@anthropic-ai/sdk";
import type {
  ChatMessage,
  ChatOptions,
  ChatResult,
  EmbeddingResult,
  LLMProvider,
} from "../types.js";

export interface AnthropicConfig {
  apiKey: string;
  chatModel: string;
}

function splitSystem(messages: ChatMessage[]): {
  system?: string;
  rest: { role: "user" | "assistant"; content: string }[];
} {
  const systemParts = messages.filter((m) => m.role === "system").map((m) => m.content);
  const rest = messages
    .filter((m) => m.role !== "system")
    .map((m) => ({ role: m.role as "user" | "assistant", content: m.content }));
  return {
    system: systemParts.length ? systemParts.join("\n\n") : undefined,
    rest,
  };
}

export class AnthropicProvider implements LLMProvider {
  readonly name = "anthropic";
  readonly chatModel: string;
  readonly embedModel = "(none — use openai/ollama/nvidia for embeddings)";
  private client: Anthropic;

  constructor(cfg: AnthropicConfig) {
    this.chatModel = cfg.chatModel;
    this.client = new Anthropic({ apiKey: cfg.apiKey });
  }

  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<ChatResult> {
    const model = options.model ?? this.chatModel;
    const { system, rest } = splitSystem(messages);
    const resp = await this.client.messages.create({
      model,
      max_tokens: options.maxTokens ?? 1024,
      temperature: options.temperature,
      stop_sequences: options.stop,
      system,
      messages: rest,
    });
    const text = resp.content
      .filter((b): b is Anthropic.TextBlock => b.type === "text")
      .map((b) => b.text)
      .join("");
    return {
      text,
      model,
      usage: {
        inputTokens: resp.usage.input_tokens,
        outputTokens: resp.usage.output_tokens,
      },
      raw: resp,
    };
  }

  async *chatStream(
    messages: ChatMessage[],
    options: ChatOptions = {},
  ): AsyncIterable<string> {
    const model = options.model ?? this.chatModel;
    const { system, rest } = splitSystem(messages);
    const stream = this.client.messages.stream({
      model,
      max_tokens: options.maxTokens ?? 1024,
      temperature: options.temperature,
      stop_sequences: options.stop,
      system,
      messages: rest,
    });
    for await (const event of stream) {
      if (
        event.type === "content_block_delta" &&
        event.delta.type === "text_delta"
      ) {
        yield event.delta.text;
      }
    }
  }

  async embed(_input: string[]): Promise<EmbeddingResult> {
    throw new Error(
      "Anthropic has no embeddings endpoint. Set LLM_PROVIDER=openai " +
        "(or ollama/nvidia) for embedding exercises, or use a dedicated " +
        "embeddings provider like Voyage AI in production.",
    );
  }
}
