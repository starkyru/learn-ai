/**
 * Task 2 — Native tool-calling agent 🟢
 *
 * What this teaches:
 *   - OpenAI and Anthropic expose "tool use" / "function calling" natively:
 *     the model returns a structured JSON object (not free text) describing
 *     which tool to call and with what arguments. No parsing fragility.
 *   - The llm_core chat() abstraction does NOT expose tools — this is intentional.
 *     Advanced features that vary across providers are taught at the SDK level
 *     so you see the real shape of each API (same philosophy as module 02).
 *   - You'll directly call the OpenAI or Anthropic SDK, then compare the
 *     reliability and ergonomics to the hand-parsed ReAct loop (Task 1).
 *
 * Requires: OPENAI_API_KEY or ANTHROPIC_API_KEY in .env
 *
 * How to run:
 *   # OpenAI path (default):
 *   LLM_PROVIDER=openai pnpm tsx modules/06-agents/ts/02-native-tools.ts
 *   # Anthropic path:
 *   LLM_PROVIDER=anthropic pnpm tsx modules/06-agents/ts/02-native-tools.ts
 */

import "dotenv/config";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

// ---------------------------------------------------------------------------
// Tool definitions — same logical tools as Task 1, different declaration format
// ---------------------------------------------------------------------------

// TODO 1: Define the tools in OpenAI's function-calling format.
//         Each tool needs: name, description, parameters (JSON Schema).
//         Use the same three tools from Task 1: calculator, search, retrieve.
//
// const openAITools: OpenAI.Chat.Completions.ChatCompletionTool[] = [
//   {
//     type: "function",
//     function: {
//       name: "calculator",
//       description: "...",
//       parameters: {
//         type: "object",
//         properties: { expression: { type: "string", description: "..." } },
//         required: ["expression"],
//       },
//     },
//   },
//   // ... search, retrieve
// ];

// TODO 2: Implement the same tools as in Task 1.
//         The execute() function signature is the same — only the calling
//         convention changes (structured args object instead of raw string).

function runTool(name: string, args: Record<string, string>): string {
  // TODO: dispatch on name, call the appropriate logic, return result string.
  throw new Error(`TODO: implement tool dispatch for "${name}"`);
}

// ---------------------------------------------------------------------------
// OpenAI native tool-calling loop
// ---------------------------------------------------------------------------

async function runOpenAIAgent(question: string): Promise<string> {
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const model = process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini";

  console.log(`\nOpenAI agent | model: ${model}`);
  console.log(`Question: ${question}\n`);

  // TODO 3: Implement the tool-calling loop for OpenAI.
  //   a) Build the initial messages array with a user message.
  //   b) Call client.chat.completions.create({ model, messages, tools: openAITools }).
  //   c) Check response.choices[0].message.finish_reason:
  //        - "tool_calls": the model wants to call tools. For each tool call:
  //            i)  Parse the JSON arguments.
  //            ii) Call runTool(name, args) to get the result.
  //            iii) Append a tool result message and continue the loop.
  //        - "stop": the model is done. Return the text content.
  //   d) Log each step so the learner sees: which tool, what args, what result.
  //
  // Hint: tool result messages look like:
  //   { role: "tool", tool_call_id: "...", content: "<result string>" }

  throw new Error("TODO: implement OpenAI agent loop");
}

// ---------------------------------------------------------------------------
// Anthropic native tool-calling loop
// ---------------------------------------------------------------------------

async function runAnthropicAgent(question: string): Promise<string> {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5";

  console.log(`\nAnthropic agent | model: ${model}`);
  console.log(`Question: ${question}\n`);

  // TODO 4: Implement the tool-calling loop for Anthropic.
  //   Anthropic's shape differs from OpenAI's:
  //     - Tools are declared as { name, description, input_schema: { type: "object", ... } }
  //     - stop_reason "tool_use" (not "tool_calls")
  //     - Content blocks: find blocks where block.type === "tool_use"
  //     - Tool results go back as: { role: "user", content: [{ type: "tool_result", tool_use_id, content }] }
  //   See: https://docs.anthropic.com/en/docs/tool-use

  throw new Error("TODO: implement Anthropic agent loop");
}

// ---------------------------------------------------------------------------
// Main — run whichever provider is configured
// ---------------------------------------------------------------------------

async function main() {
  const question =
    "What is the height of the Eiffel Tower in metres, and convert it to feet? (1 metre = 3.281 feet)";

  const provider = process.env.LLM_PROVIDER ?? "openai";

  if (provider === "anthropic") {
    const answer = await runAnthropicAgent(question);
    console.log("\nFinal Answer:", answer);
  } else {
    // Default to OpenAI
    const answer = await runOpenAIAgent(question);
    console.log("\nFinal Answer:", answer);
  }

  // TODO 5 (stretch): Run both providers on the same question and compare:
  //   - Number of tool calls
  //   - Format of the structured arguments
  //   - Whether the model calls tools in parallel (OpenAI supports parallel_tool_calls)
  //   - Token usage
}

main().catch(console.error);
