/**
 * Task 3 — Conversation memory / compaction 🟡
 *
 * What this teaches:
 *   - In a long chat, the context window fills up with old turns. The model sees the
 *     full history on every request — you are responsible for keeping it within budget.
 *   - Sliding window (keep the last K turns) is simple but loses early context.
 *   - Running summary (summarise old turns when the budget is exceeded) is more powerful:
 *     the model retains the gist without the full verbatim transcript.
 *   - A hybrid (summary + recent turns) is the most robust production approach.
 *
 * How to run:
 *   pnpm tsx modules/16-context-engineering/ts/03-memory-compaction.ts
 */

import "dotenv/config";
import { getProvider, ChatMessage, ChatOptions } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Rough token counter (replace with tiktoken from Task 1 for precision).
// ---------------------------------------------------------------------------
function countTokens(text: string): number {
  return Math.ceil(text.split(/\s+/).length * 1.3);
}

function countHistoryTokens(messages: ChatMessage[]): number {
  return messages.reduce((sum, m) => sum + countTokens(m.content), 0);
}

// Budget is intentionally small to trigger compaction during the demo.
const TOKEN_BUDGET = 800;

// ---------------------------------------------------------------------------
// Simulated conversation — 15 turns covering distinct topics.
// The early turns (movie recommendation) will eventually be compacted.
// ---------------------------------------------------------------------------
const CONVERSATION_SCRIPT: Array<[string, string]> = [
  ["user",      "What's a good sci-fi movie to watch tonight?"],
  ["assistant", "I'd recommend 'Arrival' (2016). It's a cerebral sci-fi film about a linguist who helps decode an alien language. Thoughtful, slow-paced, and emotionally resonant."],
  ["user",      "Sounds great! Is it suitable for kids?"],
  ["assistant", "It's rated PG-13. The themes are abstract rather than violent, but younger children might find the pacing slow. Fine for teenagers and adults."],
  ["user",      "OK. Now let's talk about TypeScript. How do I read a file?"],
  ["assistant", "Use `fs.readFileSync('file.txt', 'utf-8')` for synchronous reads, or `fs.promises.readFile('file.txt', 'utf-8')` for async. The async approach is preferred in modern Node.js."],
  ["user",      "What about writing to a file?"],
  ["assistant", "Use `fs.writeFileSync('output.txt', content)` or `await fs.promises.writeFile('output.txt', content)`. For appending, pass `{ flag: 'a' }` as the third argument."],
  ["user",      "How does the Node.js event loop work?"],
  ["assistant", "The event loop processes tasks in phases: timers (setTimeout/setInterval), I/O callbacks, idle/prepare, poll (new I/O), check (setImmediate), and close callbacks. Each phase has a FIFO queue; the loop continues until all queues are empty."],
  ["user",      "Got it. Can you explain Promise.all vs Promise.allSettled?"],
  ["assistant", "Promise.all resolves when ALL promises resolve, or rejects as soon as ONE rejects. Promise.allSettled always resolves with an array of results (fulfilled or rejected) — it never rejects."],
  ["user",      "Thanks! Switching topics — what is the capital of Japan?"],
  ["assistant", "Tokyo."],
  ["user",      "And Australia?"],
  ["assistant", "Canberra."],
  ["user",      "One more — what was the movie you recommended earlier? Do you remember?"],
  ["user",      "It was at the very start of our chat."],
];

// ---------------------------------------------------------------------------
// TODO 1: Implement summariseTurns.
//         Given an array of ChatMessage objects, ask the LLM to produce a 2–3 sentence
//         summary of that exchange. Return a ChatMessage with role="system" and content
//         starting with "Summary of earlier conversation: ...".
//
//         Suggested prompt:
//           "Summarise the following conversation exchange in 2-3 sentences.
//            Focus on key facts, decisions, and topics discussed.
//            Do not include conversational filler.\n\n<transcript>"
// ---------------------------------------------------------------------------
async function summariseTurns(
  turns: ChatMessage[],
  llm: ReturnType<typeof getProvider>,
): Promise<ChatMessage> {
  // const transcript = turns.map((m) => `${m.role}: ${m.content}`).join("\n");
  // const prompt =
  //   "Summarise the following conversation exchange in 2-3 sentences. " +
  //   "Focus on key facts, decisions, and topics discussed. " +
  //   "Do not include conversational filler.\n\n" + transcript;
  // const result = await llm.chat([{ role: "user", content: prompt }], { temperature: 0 });
  // return { role: "system", content: "Summary of earlier conversation: " + result.text };
  throw new Error("TODO: implement summariseTurns");
}

// ---------------------------------------------------------------------------
// TODO 2: Implement maybeCompact.
//         1. Count the total tokens in `messages`.
//         2. If count > budget:
//            a. Separate system messages from non-system messages.
//            b. Find the oldest non-system turns to summarise (enough to go below budget).
//            c. Call summariseTurns on those oldest turns.
//            d. Return: [systemMessages, summaryMessage, ...remainingTurns].
//         3. If within budget, return messages unchanged.
//         4. Log when compaction fires.
// ---------------------------------------------------------------------------
async function maybeCompact(
  messages: ChatMessage[],
  budget: number,
  llm: ReturnType<typeof getProvider>,
): Promise<ChatMessage[]> {
  // const current = countHistoryTokens(messages);
  // if (current <= budget) return messages;
  //
  // console.log(`\n  [COMPACTION] tokens=${current} > budget=${budget}; compacting...`);
  // const systemMsgs = messages.filter((m) => m.role === "system");
  // const convoMsgs  = messages.filter((m) => m.role !== "system");
  //
  // const split = Math.max(1, Math.floor(convoMsgs.length / 2));
  // const toSummarise = convoMsgs.slice(0, split);
  // const toKeep      = convoMsgs.slice(split);
  //
  // const summary = await summariseTurns(toSummarise, llm);
  // const newMessages = [...systemMsgs, summary, ...toKeep];
  // console.log(`  [COMPACTION] done — new token count=${countHistoryTokens(newMessages)}`);
  // return newMessages;
  throw new Error("TODO: implement maybeCompact");
}

async function main() {
  console.log("=== Task 3: Conversation Memory / Compaction ===\n");
  console.log(`Token budget: ${TOKEN_BUDGET} tokens\n`);

  const llm = getProvider();
  console.log(`Provider: ${llm.name} / ${llm.chatModel}\n`);

  // -------------------------------------------------------------------------
  // TODO 3: Simulate the conversation.
  //         For each turn in CONVERSATION_SCRIPT:
  //           1. Append the scripted message to history.
  //           2. If the turn is a "user" message, call maybeCompact, then
  //              call llm.chat(history) to get the assistant's reply.
  //           3. Append the assistant's reply to history.
  //           4. Print the current token count after each turn.
  // -------------------------------------------------------------------------

  let history: ChatMessage[] = [
    { role: "system", content: "You are a helpful, knowledgeable assistant." },
  ];

  for (const [role, content] of CONVERSATION_SCRIPT) {
    history.push({ role: role as "user" | "assistant", content });
    const tokens = countHistoryTokens(history);
    console.log(`[${role.padStart(9)}] tokens=${String(tokens).padStart(4)} | ${content.slice(0, 60)}...`);

    if (role === "user") {
      try {
        history = await maybeCompact(history, TOKEN_BUDGET, llm);
        const result = await llm.chat(history);
        history.push({ role: "assistant", content: result.text });
        console.log(`[assistant] ${result.text.slice(0, 80)}...`);
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.startsWith("TODO")) {
          console.log("  [TODO: implement maybeCompact and summariseTurns]");
        } else {
          console.log(`  ERROR: ${msg}`);
        }
        history.push({ role: "assistant", content: "(not implemented)" });
      }
    }
  }

  console.log();
  console.log("Observation:");
  console.log("  When compaction fires, observe whether the model still answers questions");
  console.log("  about early turns (e.g. the movie recommendation) via the summary.");
}

main().catch(console.error);
