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
 *   a) Parse serverCmd into [command, ...args] by splitting on whitespace.
 *      (You can use: const parts = serverCmd.split(/\s+/); )
 *   b) Create a StdioClientTransport:
 *        const transport = new StdioClientTransport({ command: parts[0], args: parts.slice(1) });
 *   c) Create a Client:
 *        const client = new Client({ name: "learn-ai-client", version: "1.0" });
 *   d) Connect: await client.connect(transport);
 *   e) List tools:
 *        const { tools } = await client.listTools();
 *        tools.forEach(t => console.log(`  tool: ${t.name} — ${t.description}`));
 *   f) List resources (may be empty):
 *        const { resources } = await client.listResources();
 *        resources.forEach(r => console.log(`  resource: ${r.uri} — ${r.name}`));
 *   g) Close: await client.close();
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
 *   const result = await client.callTool({ name: toolName, arguments: args });
 *   // result.content is an array of content blocks
 *   // Extract text blocks: (result.content as any[]).filter(b => b.type === "text").map(b => b.text)
 *   // Join and return.
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
