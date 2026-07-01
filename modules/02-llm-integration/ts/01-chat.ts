/**
 * Task 1 — Chat & system prompts 🟢
 *
 * What this teaches:
 *   - How multi-turn chat works: the model never has memory — you send the
 *     full conversation history on every request.
 *   - How the "system" role shapes behaviour without being shown to users.
 *   - Why message ordering matters (system → user → assistant → user …).
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/01-chat.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";

// ---------------------------------------------------------------------------
// TODO 1: Define a system prompt that gives the assistant a persona or scope.
//         Keep it short (1-3 sentences). Example: "You are a concise, helpful
//         coding tutor. Explain things simply. When in doubt, show a code snippet."
// ---------------------------------------------------------------------------
const SYSTEM_PROMPT = "TODO: write your system prompt here.";

async function main() {
  const llm = getProvider();
  console.log(`Using provider: ${llm.name} / model: ${llm.chatModel}\n`);

  // ---------------------------------------------------------------------------
  // TODO 2: Initialise the conversation history.
  //         The history starts with the system message and grows as the user
  //         and assistant take turns. Build an array of ChatMessage objects.
  //         Hint: the system message uses role "system".
  // ---------------------------------------------------------------------------
  //         Seed it with a single system-role entry carrying SYSTEM_PROMPT.
  const history: ChatMessage[] = [];

  const rl = readline.createInterface({ input, output });
  console.log('Multi-turn chat started. Type "exit" to quit.\n');

  while (true) {
    const userInput = await rl.question("You: ");
    if (userInput.trim().toLowerCase() === "exit") break;
    if (!userInput.trim()) continue;

    // -------------------------------------------------------------------------
    // TODO 3: Drive one turn of the conversation:
    //         - Push the user's line onto `history` as a user-role ChatMessage.
    //         - Call `llm.chat(history)` with the WHOLE history (the model has no
    //           memory of its own — history IS the memory).
    //         - Push the reply back onto `history` as an assistant-role message
    //           so the next turn sees it.
    //         - Print the reply with an "Assistant: " prefix.
    // -------------------------------------------------------------------------

    console.log("TODO: implement the chat loop above.\n");
    break; // remove this once you've implemented the loop
  }

  rl.close();

  // ---------------------------------------------------------------------------
  // TODO 4 (stretch): Print the full conversation history at the end so you
  //         can see exactly what was sent to the model on the last request.
  //         Notice how it grows with each turn — this is the "context window"
  //         filling up. What happens when a long conversation exceeds the limit?
  // ---------------------------------------------------------------------------
}

main().catch(console.error);
