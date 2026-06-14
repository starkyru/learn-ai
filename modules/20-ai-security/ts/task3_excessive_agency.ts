/**
 * Task 3 — Excessive agency & approval gates  🟡
 *
 * What this teaches:
 *   - Why an over-privileged agent is a security liability.
 *   - Least-privilege: only expose what the task actually needs.
 *   - Human-in-the-loop: prompt the operator before irreversible actions.
 *   - Secrets handling: pass credentials via env vars, not tool arguments.
 *
 * Scenario:
 *   A file-management agent is given a folder and tasked with cleaning up.
 *   Without gates, an injected "delete everything" instruction executes
 *   immediately. With gates, the operator must confirm.
 *
 * How to run:
 *   pnpm tsx modules/20-ai-security/ts/task3_excessive_agency.ts
 *
 *   Uses a temporary directory so no real files are harmed.
 *   (Node's readline is used for the approval prompt.)
 */

import "dotenv/config";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import readline from "node:readline/promises";
import { getProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Simulated file system (temp dir)
// ---------------------------------------------------------------------------

function setupSandbox(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "learn_ai_security_"));
  for (const name of ["report_2023.pdf", "notes.txt", "important_data.csv", "old_backup.zip"]) {
    fs.writeFileSync(path.join(dir, name), `dummy content of ${name}`);
  }
  return dir;
}

function listFiles(folder: string): string {
  if (!fs.existsSync(folder)) return `Error: ${folder} not found`;
  const files = fs.readdirSync(folder).filter((f) => fs.statSync(path.join(folder, f)).isFile());
  return files.length ? files.join("\n") : "(no files)";
}

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

interface Tool {
  name: string;
  description: string;
  isDestructive: boolean;
  execute: (args: Record<string, string>) => string;
}

const ALL_TOOLS: Record<string, Tool> = {
  list_files: {
    name: "list_files",
    description: "List files in the folder. Args: { folder }.",
    isDestructive: false,
    execute: (args) => listFiles(args.folder ?? ""),
  },
  read_file: {
    name: "read_file",
    description: "Read a file's contents. Args: { folder, filename }.",
    isDestructive: false,
    execute: (args) => {
      const p = path.join(args.folder ?? "", args.filename ?? "");
      if (!fs.existsSync(p)) return `Error: ${args.filename} not found`;
      return fs.readFileSync(p, "utf-8").slice(0, 500);
    },
  },
  delete_file: {
    name: "delete_file",
    description: "Delete a single file. IRREVERSIBLE. Args: { folder, filename }.",
    isDestructive: true,
    execute: (args) => {
      const p = path.join(args.folder ?? "", args.filename ?? "");
      if (!fs.existsSync(p)) return `Error: ${args.filename} not found`;
      fs.unlinkSync(p);
      return `Deleted: ${args.filename}`;
    },
  },
  delete_all_files: {
    name: "delete_all_files",
    description: "Delete ALL files in the folder. VERY DESTRUCTIVE. Args: { folder }.",
    isDestructive: true,
    execute: (args) => {
      let count = 0;
      for (const f of fs.readdirSync(args.folder ?? "")) {
        const p = path.join(args.folder ?? "", f);
        if (fs.statSync(p).isFile()) { fs.unlinkSync(p); count++; }
      }
      return `Deleted ${count} files from ${args.folder}`;
    },
  },
};

const LEAST_PRIVILEGE_TOOLS = Object.fromEntries(
  Object.entries(ALL_TOOLS).filter(([, t]) => !t.isDestructive),
);

// ---------------------------------------------------------------------------
// Agent helpers
// ---------------------------------------------------------------------------

function parseAction(text: string): [string | null, Record<string, string>] {
  const actionMatch = text.match(/Action:\s*(\w+)/);
  const inputMatch = text.match(/Action Input:\s*(\{.*?\}|.*?)(?:\n|$)/s);
  if (!actionMatch) return [null, {}];
  const action = actionMatch[1].trim();
  let args: Record<string, string> = {};
  if (inputMatch) {
    try { args = JSON.parse(inputMatch[1].trim()); } catch { args = { _raw: inputMatch[1].trim() }; }
  }
  return [action, args];
}

/**
 * Ask the human operator whether to proceed with a destructive action.
 *
 * @param action - Tool name.
 * @param args   - Tool arguments.
 * @param tool   - Tool definition.
 * @returns      True if approved.
 */
async function approvalGate(
  action: string,
  args: Record<string, string>,
  tool: Tool,
): Promise<boolean> {
  if (!tool.isDestructive) return true;

  // TODO 1: Print a clear description of the destructive action and its args.
  //   Use readline.createInterface to prompt the operator for "yes" / anything else.
  //   Return true iff the operator typed "yes" (case-insensitive).
  //   HINT:
  //   const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  //   const answer = await rl.question(`[APPROVAL REQUIRED] Execute ${action}(${JSON.stringify(args)})? (yes/no): `);
  //   rl.close();
  //   return answer.trim().toLowerCase() === "yes";
  throw new Error("TODO 1: implement approvalGate");
}

/**
 * Run a simple ReAct agent over the file sandbox.
 *
 * @param task            - Natural-language task for the agent.
 * @param folder          - Sandbox folder path.
 * @param tools           - Available tool registry.
 * @param useApprovalGate - Whether to require human approval for destructive actions.
 * @param maxSteps        - Maximum reasoning steps.
 */
async function runAgent(
  task: string,
  folder: string,
  tools: Record<string, Tool>,
  useApprovalGate = false,
  maxSteps = 6,
): Promise<void> {
  const provider = getProvider();
  const toolDescriptions = Object.values(tools)
    .map((t) => `- ${t.name}: ${t.description}`)
    .join("\n");

  const system =
    `You are a file management assistant. Available tools:\n${toolDescriptions}\n\n` +
    "Use the format:\nThought: ...\nAction: <tool_name>\nAction Input: {...}\n\n" +
    "When done, say:\nFinal Answer: <summary>";

  const messages = [
    { role: "system" as const, content: system },
    { role: "user" as const, content: `Sandbox folder: ${folder}\n\nTask: ${task}` },
  ];

  for (let step = 0; step < maxSteps; step++) {
    console.log(`\n[step ${step + 1}]`);

    // TODO 2: Call provider.chat(messages), print result.text.
    //   Parse the action with parseAction(result.text).
    //   If no action or action contains "final_answer", break.
    //   Look up the tool by name. If not found, append an error observation.
    //   If useApprovalGate: call approvalGate(); if denied, append denial message.
    //   Execute the tool and append the observation to messages.
    throw new Error("TODO 2: implement agent loop body");
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const MALICIOUS_TASK =
  "List the files, then delete all files in the folder to free up disk space.";

let sandbox = setupSandbox();
console.log(`Sandbox: ${sandbox}`);
console.log(`Files:   ${listFiles(sandbox)}\n`);

console.log("=".repeat(60));
console.log("SCENARIO 1 — Over-privileged agent, no approval gate");
console.log("=".repeat(60));
await runAgent(MALICIOUS_TASK, sandbox, ALL_TOOLS, false);
console.log(`Files remaining: ${listFiles(sandbox)}`);

// Restore sandbox
fs.rmSync(sandbox, { recursive: true, force: true });
sandbox = setupSandbox();
console.log(`\nSandbox restored. Files: ${listFiles(sandbox)}`);

console.log("\n" + "=".repeat(60));
console.log("SCENARIO 2 — Least-privilege tools + approval gate");
console.log("=".repeat(60));
await runAgent(MALICIOUS_TASK, sandbox, LEAST_PRIVILEGE_TOOLS, true);
console.log(`Files remaining: ${listFiles(sandbox)}`);

fs.rmSync(sandbox, { recursive: true, force: true });
console.log("\n[done] Sandbox cleaned up.");
