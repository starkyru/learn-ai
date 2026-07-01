/**
 * 02-use-mcp-server.ts — Connect to an existing MCP server.  🟢
 *
 * What this teaches:
 *   The Model Context Protocol (MCP) is an open standard for exposing tools,
 *   resources, and prompts to any LLM application. Instead of each app
 *   re-inventing how to call tools, every MCP server speaks the same protocol.
 *
 *   This file mirrors the Python task 2 using the TypeScript MCP SDK.
 *
 *   Transport layers:
 *     stdio  — server runs as a subprocess; communication over stdin/stdout.
 *     HTTP/SSE — server runs as a web service; needed for remote servers.
 *
 *   Lifecycle:
 *     1. Create StdioClientTransport pointing at the server command.
 *     2. Create a Client and connect().
 *     3. listTools() → discover what the server offers.
 *     4. listResources() → discover data sources.
 *     5. callTool(name, args) → invoke a tool.
 *
 * How to run (from repo root):
 *   pnpm tsx modules/17-mcp/ts/02-use-mcp-server.ts
 *
 *   # Or point at a custom server:
 *   MCP_SERVER_CMD="npx @modelcontextprotocol/server-filesystem /tmp" \
 *       pnpm tsx modules/17-mcp/ts/02-use-mcp-server.ts
 *
 * Env vars:
 *   MCP_SERVER_CMD — shell command to launch the server
 *
 * TS deps: @modelcontextprotocol/sdk (in package.json)
 */

import "dotenv/config";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const DEFAULT_SERVER_CMD =
  "npx -y @modelcontextprotocol/server-filesystem /tmp";

// ---------------------------------------------------------------------------
// MCP client helpers
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement listServerCapabilities.
 *
 * Connect to the server, discover its tools and resources, and print them.
 *
 * Steps:
 *   a) Split serverCmd on whitespace into [command, ...args].
 *   b) Create a StdioClientTransport pointing at that command and args.
 *   c) Create a Client (give it a name and version).
 *   d) await client.connect(transport).
 *   e) await client.listTools() and print each tool's name and description.
 *   f) await client.listResources() (the list may be empty) and print each
 *      resource's uri and name.
 *   g) await client.close() when done.
 */
async function listServerCapabilities(serverCmd: string): Promise<void> {
  throw new Error("TODO 1: implement listServerCapabilities");
}

/**
 * TODO 2: Implement callToolDemo.
 *
 * Connect to the server, call one tool, and return the text content.
 *
 * Steps (same connection pattern as TODO 1):
 *   Connect a client, then await client.callTool({ name: toolName, arguments:
 *   args }). result.content is an array of content blocks — keep the ones whose
 *   type is "text", pull their .text, join into one string and return it.
 */
async function callToolDemo(
  serverCmd: string,
  toolName: string,
  args: Record<string, unknown>
): Promise<string> {
  throw new Error("TODO 2: implement callToolDemo");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const serverCmd = process.env.MCP_SERVER_CMD ?? DEFAULT_SERVER_CMD;
  console.log(`MCP server command: ${serverCmd}\n`);

  console.log("=== Listing server capabilities ===");
  // TODO 3: Await listServerCapabilities(serverCmd).
  throw new Error("TODO 3: call listServerCapabilities and await it");

  // TODO 4: Call one tool the server exposes.
  //   For the filesystem server:
  //     const result = await callToolDemo(serverCmd, "list_directory", { path: "/tmp" });
  //     console.log("\n=== Tool result ===");
  //     console.log(result);
}

main().catch(console.error);
