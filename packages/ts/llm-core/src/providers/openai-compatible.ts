/**
 * OpenAI-compatible provider.
 *
 * KEY LESSON: OpenAI's HTTP API became a de-facto standard. OpenAI itself,
 * NVIDIA NIM, Ollama, vLLM, LM Studio, Together, Groq, and many others all
 * expose the SAME `/v1/chat/completions` and `/v1/embeddings` shape. So one
 * class — just a different `baseURL` + `apiKey` + model id — covers five of
 * our six providers. Only Anthropic ships its own distinct API.
 */

import OpenAI from "openai";
import type {
  ChatMessage,
  ChatOptions,
  ChatResult,
  EmbeddingResult,
  LLMProvider,
} from "../types.js";

export interface OpenAICompatConfig {
  name: string;
  apiKey: string;
  baseURL?: string;
  chatModel: string;
  embedModel: string;
}

export class OpenAICompatibleProvider implements LLMProvider {
  readonly name: string;
  readonly chatModel: string;
  readonly embedModel: string;
  private client: OpenAI;

  constructor(cfg: OpenAICompatConfig) {
    this.name = cfg.name;
    this.chatModel = cfg.chatModel;
    this.embedModel = cfg.embedModel;
    this.client = new OpenAI({ apiKey: cfg.apiKey, baseURL: cfg.baseURL });
  }

  async chat(messages: ChatMessage[], options: ChatOptions = {}): Promise<ChatResult> {
    const model = options.model ?? this.chatModel;
    const resp = await this.client.chat.completions.create({
      model,
      messages,
      temperature: options.temperature,
      max_tokens: options.maxTokens,
      stop: options.stop,
    });
    return {
      text: resp.choices[0]?.message?.content ?? "",
      model,
      usage: {
        inputTokens: resp.usage?.prompt_tokens,
        outputTokens: resp.usage?.completion_tokens,
      },
      raw: resp,
    };
  }

  async *chatStream(
    messages: ChatMessage[],
    options: ChatOptions = {},
  ): AsyncIterable<string> {
    const model = options.model ?? this.chatModel;
    const stream = await this.client.chat.completions.create({
      model,
      messages,
      temperature: options.temperature,
      max_tokens: options.maxTokens,
      stop: options.stop,
      stream: true,
    });
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta?.content;
      if (delta) yield delta;
    }
  }

  async embed(input: string[]): Promise<EmbeddingResult> {
    const resp = await this.client.embeddings.create({
      model: this.embedModel,
      input,
      // Force plain-float output. With no encoding_format the OpenAI SDK
      // requests base64 and decodes it client-side; some OpenAI-compatible
      // servers (e.g. LM Studio) don't honour that, yielding all-zero vectors.
      encoding_format: "float",
    });
    return {
      vectors: resp.data.map((d) => d.embedding),
      model: this.embedModel,
      usage: { inputTokens: resp.usage?.prompt_tokens },
    };
  }
}
