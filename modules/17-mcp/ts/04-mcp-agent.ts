/**
 * 04-mcp-agent.ts — Agent loop wired to MCP tools.  🟡
 *
 * What this teaches:
 *   Task 3 built a standalone MCP server. This task plugs those tools into an
 *   LLM agent loop, letting the agent answer questions by calling MCP tools
 *   autonomously — without hardcoded tool schemas.
 *
 *   Pattern:
 *     1. Connect an MCP client to the course server.
 *     2. Discover tools via listTools() — dynamic, no hardcoding.
 *     3. Convert MCP tool definitions to the provider's native format.
 *     4. Run a standard tool-calling loop (module 06 Task 2 pattern).
 *     5. When the model picks an MCP tool, call it through the MCP session.
 *
 *   This composability is MCP's main value: one server, many agents.
 *   The agent can answer:
 *     "What does module 06 cover?" (→ read_module)
 *     "Find me content about embeddings" (→ search_docs)
 *     "Quiz me on module 05" (→ run_exam_question)
 *
 * How to run (from repo root):
 *   # Default: launches the TS course server as a subprocess:
 *   pnpm tsx modules/17-mcp/ts/04-mcp-agent.ts
 *   LLM_PROVIDER=anthropic pnpm tsx modules/17-mcp/ts/04-mcp-agent.ts
 *
 * Env vars: OPENAI_API_KEY, ANTHROPIC_API_KEY, LLM_PROVIDER
 * TS deps: @modelcontextprotocol/sdk, openai, @anthropic-ai/sdk
 */

import "dotenv/config";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Launch the course MCP server as a subprocess
const SERVER_COMMAND = "pnpm";
const SERVER_ARGS = [
  "tsx",
  path.join(__dirname, "03-course-mcp-server.ts"),
];

const QUESTION =
  "What does module 06 cover? Also search the docs for 'RAG pipeline'.";

// ---------------------------------------------------------------------------
// Helpers — MCP tool schemas → provider format
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement mcpToolsToOpenAI.
 * Convert the MCP tool list to OpenAI function-calling format.
 *
 * MCP Tool shape (from listTools()):
 *   { name: string, description?: string, inputSchema: JSONSchema }
 *
 * OpenAI format:
 *   { type: "function", function: { name, description, parameters: inputSchema } }
 */
function mcpToolsToOpenAI(tools: any[]): OpenAI.Chat.Completions.ChatCompletionTool[] {
  throw new Error("TODO 1: implement mcpToolsToOpenAI");
}

/**
 * TODO 2: Implement mcpToolsToAnthropic.
 * Convert the MCP tool list to Anthropic tool format.
 *
 * Anthropic format:
 *   { name, description, input_schema: inputSchema }
 */
function mcpToolsToAnthropic(tools: any[]): Anthropic.Tool[] {
  throw new Error("TODO 2: implement mcpToolsToAnthropic");
}

// ---------------------------------------------------------------------------
// OpenAI agent loop with MCP
// ---------------------------------------------------------------------------

/**
 * TODO 3: Implement runOpenAIMcpAgent.
 *
 * Steps:
 *   a) Create a StdioClientTransport and Client (from the SERVER_COMMAND/ARGS),
 *      then connect.
 *   b) Discover the server's tools with mcpClient.listTools() and convert them
 *      with mcpToolsToOpenAI(...).
 *   c) Run the module-06 tool loop: start messages with the user question, then
 *      loop calling openai.chat.completions.create({ model, messages, tools }).
 *      While finish_reason === "tool_calls", for each tool call JSON.parse its
 *      arguments and — crucially — dispatch it by awaiting mcpClient.callTool({
 *      name, arguments }) rather than a local function. Join the "text" content
 *      blocks of the result, push the assistant message and a { role: "tool" }
 *      message (with tool_call_id and the text), then loop. Otherwise close the
 *      client and return choice.message.content. Log each tool call.
 */
async function runOpenAIMcpAgent(question: string): Promise<string> {
  throw new Error("TODO 3: implement runOpenAIMcpAgent");
}

// ---------------------------------------------------------------------------
// Anthropic agent loop with MCP
// ---------------------------------------------------------------------------

/**
 * TODO 4: Implement runAnthropicMcpAgent.
 *
 * Same structure as runOpenAIMcpAgent but with Anthropic's tool format.
 * Key differences (same as module 06 Task 2):
 *   - tools use input_schema instead of parameters
 *   - stop_reason "tool_use" instead of "tool_calls"
 *   - tool results: { role: "user", content: [{ type: "tool_result", tool_use_id, content }] }
 */
async function runAnthropicMcpAgent(question: string): Promise<string> {
  throw new Error("TODO 4: implement runAnthropicMcpAgent");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const provider = process.env.LLM_PROVIDER ?? "openai";
  console.log(`Provider : ${provider}`);
  console.log(`Question : ${QUESTION}\n`);

  let answer: string;
  if (provider === "anthropic") {
    answer = await runAnthropicMcpAgent(QUESTION);
  } else {
    answer = await runOpenAIMcpAgent(QUESTION);
  }

  console.log(`\nAnswer: ${answer}`);
}

main().catch(console.error);
