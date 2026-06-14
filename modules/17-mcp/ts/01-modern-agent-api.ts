/**
 * 01-modern-agent-api.ts — Modern agent APIs vs. manual tool loops.  🟢
 *
 * What this teaches:
 *   Module 06 built a tool-calling agent from scratch: manually call the SDK,
 *   check finish_reason, dispatch tools, append messages, loop.
 *   That approach is universal but requires managing all protocol details.
 *
 *   OpenAI's Responses API (2025) moves conversation threading server-side:
 *   - `previous_response_id` chains turns (no re-sending the full history)
 *   - Hosted tools (web_search_preview) run server-side — no extra round-trips
 *   - Remote MCP connector: point at a URL and tools appear automatically
 *
 *   Anthropic's tool use pattern stays client-side but the SDK ergonomics
 *   are cleaner than the raw JSON manipulation of module 06.
 *
 *   Contrast:
 *     Manual loop (mod 06): universal, debuggable, works with Ollama
 *     Responses API:        less code, server-side history, built-in tools
 *     Anthropic:            client-side, clean SDK, extended thinking available
 *
 * How to run (from repo root):
 *   pnpm tsx modules/17-mcp/ts/01-modern-agent-api.ts
 *   LLM_PROVIDER=anthropic pnpm tsx modules/17-mcp/ts/01-modern-agent-api.ts
 *
 * Env vars: OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_PROVIDER
 */

import "dotenv/config";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

const QUESTION =
  "What is the capital of France, and what is 1337 * 42? Answer both questions.";

// ---------------------------------------------------------------------------
// Shared tool logic
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement runCalculator.
 * Evaluate a math expression string and return the numeric result as a string.
 * Use eval() — acceptable for a learning exercise.
 * Catch errors and return an error message instead of throwing.
 */
function runCalculator(expression: string): string {
  throw new Error("TODO 1: implement runCalculator");
}

/**
 * TODO 2: Implement runLookup.
 * Return a canned answer for common geography/fact queries.
 * Build a small map: { france: "Paris", germany: "Berlin", japan: "Tokyo" }
 * Return "Unknown" if no key matches (case-insensitive).
 */
function runLookup(query: string): string {
  throw new Error("TODO 2: implement runLookup");
}

/**
 * TODO 3: Implement dispatch.
 * Route a tool call by name to the right function.
 * Handles: "calculator" (args.expression) and "lookup" (args.query).
 * Throw for unknown tool names.
 */
function dispatch(name: string, args: Record<string, string>): string {
  throw new Error(`TODO 3: implement dispatch for tool "${name}"`);
}

// ---------------------------------------------------------------------------
// OpenAI Responses API
// ---------------------------------------------------------------------------

/**
 * runOpenAIResponses — use the Responses API to answer a question with tools.
 *
 * Key differences from Chat Completions (module 06 Task 2):
 *   - client.responses.create() instead of client.chat.completions.create()
 *   - `input` (string or array) instead of `messages`
 *   - `previous_response_id` chains turns without resending history
 *   - Output items (response.output) instead of choices[0].message
 */
async function runOpenAIResponses(question: string): Promise<string> {
  const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  const model = process.env.OPENAI_CHAT_MODEL ?? "gpt-4o-mini";

  console.log(`\nOpenAI Responses API | model: ${model}`);
  console.log(`Question: ${question}\n`);

  // TODO 4: Define tool schemas in Responses-API format.
  //   Same JSON Schema structure as Chat Completions:
  //   { type: "function", name: "...", description: "...", parameters: { ... } }
  //   Define "calculator" and "lookup".
  const tools: object[] = []; // TODO 4: replace with real tool defs

  // TODO 5: Implement the Responses API loop.
  //   a) Call client.responses.create({ model, input: question, tools }).
  //   b) Inspect response.output — list of output items:
  //      - { type: "message", content: [{ type: "output_text", text: "..." }] } → done
  //      - { type: "function_call", name, arguments, call_id } → call the tool
  //   c) For each function_call item:
  //        const result = dispatch(item.name, JSON.parse(item.arguments));
  //        console.log(`  [tool] ${item.name}(...) -> ${result}`);
  //        // Chain the next turn via previous_response_id:
  //        response = await client.responses.create({
  //            model,
  //            previous_response_id: response.id,
  //            input: [{ type: "function_call_output", call_id: item.call_id, output: result }],
  //            tools,
  //        });
  //   d) Continue until no more function_call items; return the message text.
  throw new Error("TODO 5: implement Responses API loop");
}

// ---------------------------------------------------------------------------
// Anthropic tool use
// ---------------------------------------------------------------------------

/**
 * runAnthropicTools — client-side tool loop with Anthropic.
 *
 * Same loop structure as module 06 Task 2, but here we annotate the contrast
 * with the Responses API explicitly so the learner can compare.
 *
 * Shape:
 *   tools = [{ name, description, input_schema: { type: "object", ... } }]
 *   stop_reason "tool_use" → content blocks with .type === "tool_use"
 *   inject results as: { role: "user", content: [{ type: "tool_result", tool_use_id, content }] }
 */
async function runAnthropicTools(question: string): Promise<string> {
  const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
  const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5";

  console.log(`\nAnthropic tool use | model: ${model}`);
  console.log(`Question: ${question}\n`);

  // TODO 6: Define Anthropic tool schemas.
  //   [{ name: "calculator", description: "...", input_schema: { type: "object", ... } }]
  const tools: Anthropic.Tool[] = []; // TODO 6: replace with real tool defs

  const messages: Anthropic.MessageParam[] = [
    { role: "user", content: question },
  ];

  // TODO 7: Implement the Anthropic tool-calling loop.
  //   a) Call client.messages.create({ model, max_tokens: 1024, tools, messages }).
  //   b) While response.stop_reason === "tool_use":
  //      - Find content blocks where block.type === "tool_use"
  //      - Call dispatch(block.name, block.input as Record<string, string>)
  //      - Log: console.log(`  [tool] ${block.name}(...) -> ${result}`)
  //      - Append the assistant turn, then inject results:
  //        messages.push({ role: "assistant", content: response.content });
  //        messages.push({
  //            role: "user",
  //            content: [{ type: "tool_result", tool_use_id: block.id, content: result }],
  //        });
  //      - Loop.
  //   c) When stop_reason === "end_turn", extract and return text content.
  throw new Error("TODO 7: implement Anthropic tool-calling loop");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const provider = process.env.LLM_PROVIDER ?? "openai";
  console.log(`Provider : ${provider}`);
  console.log(`Question : ${QUESTION}`);

  let answer: string;
  if (provider === "anthropic") {
    answer = await runAnthropicTools(QUESTION);
  } else {
    answer = await runOpenAIResponses(QUESTION);
  }

  console.log(`\nAnswer: ${answer}`);

  // TODO 8 (stretch): Run both providers on the same question.
  //   Compare: number of API calls, the tool call format,
  //   and whether the Responses API's ID chaining is more ergonomic.
}

main().catch(console.error);
