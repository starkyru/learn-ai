/**
 * Shared types for the provider-agnostic LLM layer.
 *
 * The whole point of this package: write your exercise code against ONE
 * interface (`LLMProvider`), then swap the underlying model — OpenAI, Claude,
 * a local Ollama model, or an NVIDIA-hosted model — by changing one env var.
 * That swap-ability is itself a core lesson (see modules/02-llm-integration).
 */

export type Role = "system" | "user" | "assistant";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ChatOptions {
  /** Sampling temperature. Ignored by providers/models that don't support it. */
  temperature?: number;
  /** Hard cap on output tokens. */
  maxTokens?: number;
  /** Stop sequences. */
  stop?: string[];
  /** Override the model id configured in env for this single call. */
  model?: string;
}

export interface TokenUsage {
  inputTokens?: number;
  outputTokens?: number;
}

export interface ChatResult {
  text: string;
  model: string;
  usage?: TokenUsage;
  /** The raw provider response, for when you want to inspect the real shape. */
  raw?: unknown;
}

export interface EmbeddingResult {
  /** One vector per input string, in order. */
  vectors: number[][];
  model: string;
  usage?: TokenUsage;
}

/**
 * The contract every provider implements. Keep this small on purpose —
 * advanced features (tools, JSON mode, etc.) are taught per-provider in the
 * modules rather than hidden behind a leaky abstraction.
 */
export interface LLMProvider {
  readonly name: string;
  readonly chatModel: string;
  readonly embedModel: string;

  chat(messages: ChatMessage[], options?: ChatOptions): Promise<ChatResult>;

  /** Token-by-token (or chunk-by-chunk) streaming. */
  chatStream(
    messages: ChatMessage[],
    options?: ChatOptions,
  ): AsyncIterable<string>;

  embed(input: string[]): Promise<EmbeddingResult>;
}
