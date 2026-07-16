/**
 * Deterministic, offline provider for the governance demo + tests.
 *
 * It satisfies the shared `@learn-ai/llm-core` `LLMProvider` interface, so
 * exercise code only ever calls `provider.chat(...)` — no vendor SDK, no
 * network, no key. Swapping in the real client is one line (`getProvider()`);
 * injecting this fake is how the demo stays deterministic and how a test can
 * inspect exactly what crossed the provider boundary.
 *
 * The reply is canned and never echoes the input, so the provider is not a leak
 * path — anything a test finds in `recordedMessages` was put there by the
 * caller, which is the point.
 */

import type {
  ChatMessage,
  ChatOptions,
  ChatResult,
  EmbeddingResult,
  LLMProvider,
} from "@learn-ai/llm-core";

export class RecordingProvider implements LLMProvider {
  readonly name = "fake-recording";
  readonly chatModel = "fake-chat-1";
  readonly embedModel = "fake-embed-1";

  /** Every `chat` call's messages, in order. */
  readonly calls: ChatMessage[][] = [];

  async chat(messages: ChatMessage[], _options?: ChatOptions): Promise<ChatResult> {
    this.calls.push([...messages]);
    // Canned reply — deterministic and independent of the input.
    return {
      text: "[fake] Support request acknowledged.",
      model: this.chatModel,
      usage: { inputTokens: 0, outputTokens: 0 },
    };
  }

  async *chatStream(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string> {
    const result = await this.chat(messages, options);
    yield result.text;
  }

  async embed(input: string[]): Promise<EmbeddingResult> {
    // Deterministic, content-free vectors — no external call.
    return {
      vectors: input.map((s) => [s.length, 0, 0]),
      model: this.embedModel,
    };
  }

  /** The messages from the most recent `chat` call. */
  get recordedMessages(): ChatMessage[] {
    return this.calls[this.calls.length - 1];
  }
}
