/**
 * Task 3 — Agent memory 🟡
 *
 * What this teaches:
 *   - "Memory" in an LLM agent is an architectural choice, not magic.
 *     There are three kinds:
 *       1. In-context (conversation history) — limited by the context window.
 *       2. External / persistent — a file or DB the agent reads and writes.
 *       3. Summarised — compress old turns so they fit the window.
 *   - A scratchpad lets the agent accumulate intermediate conclusions across
 *     turns without bloating the full message history.
 *   - Reading the scratchpad at the start of each turn is how the agent
 *     "remembers" what it decided in previous steps.
 *
 * How to run:
 *   pnpm tsx modules/06-agents/ts/03-memory.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";
import * as fs from "node:fs";
import * as path from "node:path";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

// ---------------------------------------------------------------------------
// Scratchpad — a file the agent reads/writes to persist notes across turns
// ---------------------------------------------------------------------------

const SCRATCHPAD_PATH = path.join(
  process.cwd(),
  "modules/06-agents/scratchpad.txt"
);

// TODO 1: Implement readScratchpad() and writeScratchpad().
//         If the file doesn't exist, readScratchpad() should return "".
//         writeScratchpad() appends a timestamped entry (don't overwrite the
//         whole file — the agent should accumulate notes over time).

function readScratchpad(): string {
  // TODO: return fs.existsSync(SCRATCHPAD_PATH) ? fs.readFileSync(SCRATCHPAD_PATH, "utf-8") : "";
  throw new Error("TODO: implement readScratchpad");
}

function writeScratchpad(note: string): void {
  // TODO: append `\n[${new Date().toISOString()}] ${note}` to the file.
  throw new Error("TODO: implement writeScratchpad");
}

// ---------------------------------------------------------------------------
// Conversation memory — sliding window to cap context size
// ---------------------------------------------------------------------------

const MAX_HISTORY_TURNS = 10; // keep at most N user+assistant pairs

// TODO 2: Implement trimHistory().
//         Always keep the system message (index 0).
//         If history has more than MAX_HISTORY_TURNS pairs after the system
//         message, drop the oldest pairs (not the system message).
//         A "pair" = one user message + one assistant message.

function trimHistory(history: ChatMessage[]): ChatMessage[] {
  // TODO: preserve history[0] (system), then keep only the last
  //       MAX_HISTORY_TURNS * 2 messages from the rest.
  throw new Error("TODO: implement trimHistory");
}

// ---------------------------------------------------------------------------
// System prompt — aware of the scratchpad
// ---------------------------------------------------------------------------

function buildSystemPrompt(scratchpadContent: string): string {
  // TODO 3: Write a system prompt that:
  //   - Tells the agent it has a persistent scratchpad it can use.
  //   - Shows the current scratchpad content (if any) inside a <scratchpad> block.
  //   - Instructs the agent to write notes in the format:
  //       SCRATCHPAD: <note to save>
  //     at the end of any response where it wants to remember something.
  //   - Tells it to say CLEAR_SCRATCHPAD to wipe and start fresh.
  return "TODO: write the system prompt. Show scratchpadContent inside <scratchpad> tags.";
}

// ---------------------------------------------------------------------------
// Response post-processing — extract and act on scratchpad commands
// ---------------------------------------------------------------------------

function processResponse(
  responseText: string
): { displayText: string; noteToSave?: string; clearScratchpad?: boolean } {
  // TODO 4: Scan responseText for:
  //   - "SCRATCHPAD: <note>" — extract <note> to save.
  //   - "CLEAR_SCRATCHPAD"   — signal to wipe the file.
  //   Then strip those lines from displayText so they aren't shown to the user.
  throw new Error("TODO: implement processResponse");
}

// ---------------------------------------------------------------------------
// Main — multi-turn chat with scratchpad memory
// ---------------------------------------------------------------------------

async function main() {
  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}`);
  console.log(`Scratchpad: ${SCRATCHPAD_PATH}\n`);

  // Build initial history with a system prompt that includes current scratchpad.
  let history: ChatMessage[] = [
    { role: "system", content: buildSystemPrompt(readScratchpad()) },
  ];

  const rl = readline.createInterface({ input, output });
  console.log('Memory-enabled agent. Type "exit" to quit, "scratchpad" to view it.\n');

  while (true) {
    const userInput = await rl.question("You: ");
    if (!userInput.trim()) continue;
    if (userInput.trim().toLowerCase() === "exit") break;

    if (userInput.trim().toLowerCase() === "scratchpad") {
      const content = readScratchpad();
      console.log("\n--- Scratchpad ---");
      console.log(content || "(empty)");
      console.log("--- End ---\n");
      continue;
    }

    // TODO 5: Append the user message, call llm.chat(), process the response:
    //   a) Process the raw text with processResponse().
    //   b) If noteToSave is present, call writeScratchpad(noteToSave).
    //   c) If clearScratchpad is true, clear the file (fs.writeFileSync with "").
    //   d) Append the assistant message (displayText) to history.
    //   e) Trim history with trimHistory() to prevent context overflow.
    //   f) Rebuild the system prompt with the updated scratchpad content so the
    //      agent sees its latest notes on the next turn.
    //   g) Print the displayText with "Assistant: " prefix.

    console.log("TODO: implement the memory-aware chat loop.\n");
    break; // remove once implemented
  }

  rl.close();
}

main().catch(console.error);
