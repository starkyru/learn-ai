/**
 * Task 5 — Tool / function calling 🟢
 *
 * What this teaches:
 *   - The llm_core abstraction only exposes chat/stream/embed. Tool calling
 *     requires richer request shapes (tool definitions, tool_choice, etc.)
 *     that live in the raw provider SDKs. This is WHERE YOU GO BEYOND the
 *     abstraction — and why it exists as a thin wrapper, not a thick one.
 *   - The manual tool loop:
 *       1. Send messages + tool definitions.
 *       2. Model replies with a tool_call (name + arguments JSON).
 *       3. You execute the tool locally.
 *       4. Append a "tool" result message and call the model again.
 *       5. Model uses the result to produce a final text answer.
 *   - OpenAI-style tools (shown here with openai SDK) work identically
 *     for ollama, lmstudio, and nvidia because they implement the same API surface.
 *   - Anthropic uses a different wire format but the same conceptual loop.
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/05-tool-calling.ts
 *
 * Required env (pick one):
 *   LLM_PROVIDER=openai    + OPENAI_API_KEY
 *   LLM_PROVIDER=ollama    (local; model must support tools, e.g. llama3.2)
 *   LLM_PROVIDER=lmstudio  (local; load a tool-capable model + Start Server on :1234)
 *   LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY  (see Part B)
 *
 * Local tool calling (Ollama / LM Studio):
 *   Part A talks raw OpenAI wire format, and both local servers are
 *   OpenAI-compatible — so no code change is needed, only env vars:
 *     LM Studio:  LLM_PROVIDER=lmstudio  [LMSTUDIO_BASE_URL=http://localhost:1234/v1]
 *                 [LMSTUDIO_CHAT_MODEL=qwen2.5-7b-instruct]
 *     Ollama:     LLM_PROVIDER=ollama    [OLLAMA_CHAT_MODEL=llama3.2]
 *   CAVEAT: tool calling depends on the *model*, not the server. Pick a
 *   tool-tuned instruct model (Qwen2.5-Instruct, Llama-3.1/3.2-Instruct,
 *   Mistral-Nemo). Small/quantized models often skip the tool call or emit
 *   malformed argument JSON — gate on `message.tool_calls?.length` rather
 *   than trusting finish_reason if a local model misbehaves.
 */

import "dotenv/config";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

// ---------------------------------------------------------------------------
// Fake tool: get_weather
// In a real app this would call a weather API. Here we return a hardcoded
// response so the exercise works without a real API key for weather.
// ---------------------------------------------------------------------------
function getWeather(location: string, unit: "celsius" | "fahrenheit" = "celsius"): string {
  // TODO: make this slightly more interesting — vary by city name so the model
  //       gets different data for different locations it asks about.
  const fakeData: Record<string, { temp: number; condition: string }> = {
    london:    { temp: 15, condition: "cloudy" },
    tokyo:     { temp: 22, condition: "sunny" },
    new_york:  { temp: 18, condition: "partly cloudy" },
  };
  const key = location.toLowerCase().replace(/\s+/g, "_");
  const weather = fakeData[key] ?? { temp: 20, condition: "unknown" };
  const temp = unit === "fahrenheit" ? weather.temp * 9 / 5 + 32 : weather.temp;
  return JSON.stringify({ location, temperature: temp, unit, condition: weather.condition });
}

// ---------------------------------------------------------------------------
// PART A: OpenAI-style tool calling
// This works for OpenAI, Ollama (if the model supports tools), and NVIDIA.
// ---------------------------------------------------------------------------

// TODO 1: Define the tool schema in OpenAI format.
//         It needs: type "function", function.name, function.description,
//         function.parameters (JSON Schema object with required fields).
const weatherToolDefinition: OpenAI.Chat.Completions.ChatCompletionTool = {
  type: "function",
  function: {
    name: "get_weather",
    description: "TODO: write a description that helps the model know WHEN to call this",
    parameters: {
      // TODO: fill in the JSON Schema for the parameters
      // Hint: properties { location: { type: "string" }, unit: { type: "string", enum: [...] } }
      type: "object",
      properties: {},
      required: [],
    },
  },
};

async function runOpenAIToolLoop(question: string): Promise<void> {
  console.log("=== Part A: OpenAI-style tool calling ===\n");

  // LLM_PROVIDER is the single source of truth: it selects the baseURL, key,
  // and model together (mirrors @learn-ai/llm-core's config). Part A uses the
  // raw OpenAI SDK on purpose, so we resolve that config here by hand.
  const provider = process.env.LLM_PROVIDER ?? "ollama";
  const PROVIDER_CONFIG: Record<string, { apiKey: string; baseURL?: string; model: string }> = {
    openai: {
      apiKey: process.env.OPENAI_API_KEY ?? "",
      model: process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini",
    },
    ollama: {
      apiKey: "ollama", // any non-empty string; local server ignores it
      baseURL: process.env.OLLAMA_BASE_URL ?? "http://localhost:11434/v1",
      model: process.env.OLLAMA_CHAT_MODEL ?? "llama3.2",
    },
    lmstudio: {
      apiKey: "lm-studio",
      baseURL: process.env.LMSTUDIO_BASE_URL ?? "http://localhost:1234/v1",
      model: process.env.LMSTUDIO_CHAT_MODEL ?? "qwen2.5-7b-instruct",
    },
    nvidia: {
      apiKey: process.env.NVIDIA_API_KEY ?? "",
      baseURL: process.env.NVIDIA_BASE_URL ?? "https://integrate.api.nvidia.com/v1",
      model: process.env.NVIDIA_CHAT_MODEL ?? "meta/llama-3.1-8b-instruct",
    },
  };
  const config = PROVIDER_CONFIG[provider];
  if (!config) {
    throw new Error(
      `Part A (OpenAI-style) supports: ${Object.keys(PROVIDER_CONFIG).join(", ")}. ` +
        `Got LLM_PROVIDER="${provider}". For anthropic, see Part B.`,
    );
  }
  const client = new OpenAI({ apiKey: config.apiKey, baseURL: config.baseURL });
  const model = config.model;
  console.log(`Provider: ${provider} / ${model}`);

  console.log(`Question: ${question}\n`);

  // -------------------------------------------------------------------------
  // TODO 2: Send the initial request with the tool definition.
  //         Use client.chat.completions.create({ model, messages, tools, tool_choice: "auto" })
  // -------------------------------------------------------------------------
  // const messages: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
  //   { role: "user", content: question },
  // ];
  // let response = await client.chat.completions.create({
  //   model,
  //   messages,
  //   tools: [weatherToolDefinition],
  //   tool_choice: "auto",
  // });
  // let message = response.choices[0].message;
  // console.log("First response finish_reason:", response.choices[0].finish_reason);

  // -------------------------------------------------------------------------
  // TODO 3: Check if finish_reason === "tool_calls". If so:
  //         a) Append the assistant message to `messages`.
  //         b) For each tool_call in message.tool_calls:
  //            - Parse the arguments JSON.
  //            - Call getWeather() with those args.
  //            - Append a { role: "tool", tool_call_id, content: result } message.
  //         c) Call the API again with the updated messages.
  //         d) Print the final text response.
  // -------------------------------------------------------------------------
  // if (message.tool_calls && response.choices[0].finish_reason === "tool_calls") {
  //   messages.push(message);
  //   for (const toolCall of message.tool_calls) {
  //     const args = JSON.parse(toolCall.function.arguments);
  //     const result = getWeather(args.location, args.unit);
  //     console.log(`Tool called: ${toolCall.function.name}(${toolCall.function.arguments})`);
  //     console.log(`Tool result: ${result}\n`);
  //     messages.push({ role: "tool", tool_call_id: toolCall.id, content: result });
  //   }
  //   response = await client.chat.completions.create({ model, messages, tools: [weatherToolDefinition] });
  //   message = response.choices[0].message;
  // }
  // console.log("Final answer:", message.content);

  console.log("TODO: implement the tool loop above.");
}

// ---------------------------------------------------------------------------
// PART B: Anthropic-style tool calling
// Different wire format, same conceptual loop.
// ---------------------------------------------------------------------------

async function runAnthropicToolLoop(question: string): Promise<void> {
  console.log("\n=== Part B: Anthropic-style tool calling ===\n");

  const client = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
  });
  const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5";

  console.log(`Question: ${question}\n`);

  // -------------------------------------------------------------------------
  // TODO 4: Define the Anthropic tool. Format differs from OpenAI:
  //         { name, description, input_schema: { type: "object", properties, required } }
  // -------------------------------------------------------------------------
  // const tool: Anthropic.Tool = {
  //   name: "get_weather",
  //   description: "...",
  //   input_schema: { type: "object", properties: { ... }, required: [...] },
  // };

  // -------------------------------------------------------------------------
  // TODO 5: Send the initial request.
  //         client.messages.create({ model, max_tokens, tools: [tool], messages })
  //         Check response.stop_reason === "tool_use".
  // -------------------------------------------------------------------------

  // -------------------------------------------------------------------------
  // TODO 6: For each content block with type "tool_use":
  //         - Execute the tool.
  //         - Append the assistant message (as-is) to the messages array.
  //         - Append a user message with content = [{ type: "tool_result", tool_use_id, content }].
  //         - Call the API again and print the final text.
  //         Anthropic's loop uses alternating user/assistant messages;
  //         tool results go INSIDE a user message, not as a top-level role.
  // -------------------------------------------------------------------------

  console.log("TODO: implement the Anthropic tool loop above.");
  console.log("(Skip this part if you don't have an ANTHROPIC_API_KEY)");
}

async function main() {
  const question = "What's the weather like in London and Tokyo right now?";

  // Run OpenAI-compatible path (also works with ollama)
  await runOpenAIToolLoop(question);

  // Run Anthropic path (requires ANTHROPIC_API_KEY)
  if (process.env.ANTHROPIC_API_KEY) {
    await runAnthropicToolLoop(question);
  } else {
    console.log("\nSkipping Part B (no ANTHROPIC_API_KEY set).");
  }
}

main().catch(console.error);
