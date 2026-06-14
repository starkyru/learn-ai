/**
 * 03-course-mcp-server.ts — Build an MCP server for this course.  🟢 (flagship)
 *
 * What this teaches:
 *   Building an MCP server is the mirror image of consuming one (task 2).
 *   You register tools and resources; the MCP SDK handles the protocol.
 *   Any MCP client can then discover and call your tools.
 *
 *   This server exposes three tools:
 *
 *   search_docs(query, top_k?)
 *     Full-text search across all module README files.
 *     Same idea as the RAG retrieve step (module 05) but simpler.
 *
 *   read_module(module)
 *     Return the full README.md for a given module like "06-agents".
 *
 *   run_exam_question(module, answer?)
 *     Return a quiz question, or grade a submitted answer.
 *
 *   Transport: stdio. This is also the server task 4's agent will use.
 *
 * How to run (from repo root):
 *   pnpm tsx modules/17-mcp/ts/03-course-mcp-server.ts
 *
 *   # Test with the task-2 client:
 *   MCP_SERVER_CMD="pnpm tsx modules/17-mcp/ts/03-course-mcp-server.ts" \
 *       pnpm tsx modules/17-mcp/ts/02-use-mcp-server.ts
 *
 *   # Use as a Claude Code project MCP server — add to .claude/settings.json:
 *   # { "mcpServers": { "learn-ai": {
 *   #     "command": "pnpm",
 *   #     "args": ["tsx", "modules/17-mcp/ts/03-course-mcp-server.ts"]
 *   # }}}
 *
 * TS deps: @modelcontextprotocol/sdk
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../../");
const MODULES_DIR = path.join(REPO_ROOT, "modules");

// ---------------------------------------------------------------------------
// Corpus helpers
// ---------------------------------------------------------------------------

interface ReadmeEntry {
  module: string;
  text: string;
}

/** Scan all modules and return their README text. */
function allReadmes(): ReadmeEntry[] {
  // TODO 1: Read all README.md files under MODULES_DIR.
  //   a) fs.readdirSync(MODULES_DIR, { withFileTypes: true }) — filter directories
  //   b) For each dir, check if README.md exists (fs.existsSync)
  //   c) If yes, read the text (fs.readFileSync(readmePath, "utf-8"))
  //   d) Return sorted array of { module: dir.name, text }
  throw new Error("TODO 1: implement allReadmes");
}

interface SearchResult {
  module: string;
  excerpt: string;
  score: number;
}

/**
 * TODO 2: Implement simpleSearch.
 * Keyword-frequency search across all README files.
 *   a) Tokenise query: query.toLowerCase().split(/\W+/).filter(Boolean)
 *   b) For each readme, score = count of query tokens found in text.toLowerCase()
 *   c) Sort by score descending, take top topK
 *   d) Return { module, excerpt: text.slice(0, 400), score }[]
 */
function simpleSearch(query: string, topK = 3): SearchResult[] {
  throw new Error("TODO 2: implement simpleSearch");
}

/**
 * TODO 3: Implement readModuleReadme.
 * Return the README.md content for a module name like "06-agents".
 *   a) Try MODULES_DIR/module/README.md directly.
 *   b) If not found, glob for *<number>*/README.md to handle bare numbers.
 *   c) Return the text, or a helpful error message if not found.
 */
function readModuleReadme(module: string): string {
  throw new Error("TODO 3: implement readModuleReadme");
}

// ---------------------------------------------------------------------------
// Exam questions
// ---------------------------------------------------------------------------

const EXAM_QUESTIONS: Record<string, { question: string; answer: string }> = {
  "00-setup": {
    question: "What env var controls which LLM provider is used across all modules?",
    answer: "LLM_PROVIDER",
  },
  "05-rag": {
    question: "What are the five stages of a RAG pipeline?",
    answer: "load, chunk, embed, retrieve, generate",
  },
  "06-agents": {
    question: "In the ReAct pattern, what are the three components of each agent step?",
    answer: "thought, action, observation",
  },
  "17-mcp": {
    question: "What are the two standard MCP transport types?",
    answer: "stdio and HTTP/SSE",
  },
};

/**
 * TODO 4: Implement getExamQuestion.
 * Look up the module in EXAM_QUESTIONS (try exact key and with leading-zero normalisation).
 * Return a formatted string: "Module: ...\nQuestion: ...\n(Submit your answer with answer=<text>)"
 * If not found, list available modules.
 */
function getExamQuestion(module: string): string {
  throw new Error("TODO 4: implement getExamQuestion");
}

/**
 * TODO 5: Implement gradeAnswer.
 * Simple case-insensitive substring check:
 *   Does userAnswer contain the key words from the expected answer?
 * Return "Correct! ..." or "Not quite. Hint: ..."
 */
function gradeAnswer(module: string, userAnswer: string): string {
  throw new Error("TODO 5: implement gradeAnswer");
}

// ---------------------------------------------------------------------------
// MCP server
// ---------------------------------------------------------------------------

/**
 * TODO 6: Create the MCP server and register handlers.
 *
 * a) new Server({ name: "learn-ai-course", version: "0.1.0" }, { capabilities: { tools: {} } })
 *
 * b) Register ListToolsRequestSchema handler:
 *    server.setRequestHandler(ListToolsRequestSchema, async () => ({
 *        tools: [
 *            { name: "search_docs", description: "...", inputSchema: { type: "object",
 *              properties: { query: { type: "string" }, top_k: { type: "number" } },
 *              required: ["query"] } },
 *            { name: "read_module", description: "...", inputSchema: { ... } },
 *            { name: "run_exam_question", description: "...", inputSchema: {
 *              properties: { module: { type: "string" }, answer: { type: "string" } },
 *              required: ["module"] } },
 *        ],
 *    }));
 *
 * c) Register CallToolRequestSchema handler:
 *    server.setRequestHandler(CallToolRequestSchema, async (request) => {
 *        const { name, arguments: args } = request.params;
 *        let text: string;
 *        if (name === "search_docs") { ... }
 *        else if (name === "read_module") { ... }
 *        else if (name === "run_exam_question") { ... }
 *        else throw new Error(`Unknown tool: ${name}`);
 *        return { content: [{ type: "text", text }] };
 *    });
 *
 * d) return server;
 */
function buildServer(): Server {
  throw new Error("TODO 6: implement buildServer");
}

// ---------------------------------------------------------------------------
// Main — start stdio transport
// ---------------------------------------------------------------------------

/**
 * TODO 7: Start the server with stdio transport.
 *   const server = buildServer();
 *   const transport = new StdioServerTransport();
 *   await server.connect(transport);
 *   // The process will now block, handling MCP requests on stdin/stdout.
 */
async function main() {
  throw new Error("TODO 7: start StdioServerTransport and connect");
}

main().catch(console.error);
