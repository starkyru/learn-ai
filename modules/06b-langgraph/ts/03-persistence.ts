/**
 * Task 3 — Persistence: checkpointer + threads  🟡
 *
 * What this teaches:
 *   - Compile with a CHECKPOINTER and every super-step is saved.
 *   - thread_id names one conversation: same thread continues from saved state
 *     (memory across turns); a different thread starts blank.
 *   - Swap MemorySaver for SqliteSaver and memory survives a process restart.
 *   - Foundation for interrupts (Task 4) and time travel (Task 8).
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/03-persistence.ts
 *   # for the restart demo: pnpm add @langchain/langgraph-checkpoint-sqlite
 */

import {
  StateGraph,
  START,
  MessagesAnnotation,
  MemorySaver,
} from "@langchain/langgraph";
import { HumanMessage } from "@langchain/core/messages";
import { getChatModel } from "./_model.js";

async function buildApp(checkpointer: any) {
  const model = await getChatModel();
  const chatNode = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });

  const graph = new StateGraph(MessagesAnnotation)
    .addNode("chat", chatNode)
    .addEdge(START, "chat");

  // TODO 1: compile the graph, but pass the `checkpointer` in the compile options
  //         so every super-step is saved per thread.
  return graph.compile();
}

async function ask(app: any, text: string, threadId: string): Promise<string> {
  const config = { configurable: { thread_id: threadId } };
  const result = await app.invoke({ messages: [new HumanMessage(text)] }, config);
  return result.messages.at(-1).content;
}

async function main() {
  const app = await buildApp(new MemorySaver());

  // TODO 2: same thread remembers. Call `ask(app, ..., threadId)` twice on ONE
  //         thread id — first tell it a fact to remember, then ask it back — and log
  //         each reply. The second reply should recall the fact.

  // TODO 3: a different thread does NOT remember. Ask the same recall question on a
  //         DIFFERENT thread id and log it — the model should not know.

  // TODO 4 (restart-survival): swap in a file-backed saver and re-run the script.
  //         Import `SqliteSaver` (from @langchain/langgraph-checkpoint-sqlite),
  //         create one via its `fromConnString(...)` pointing at a `.sqlite` file,
  //         buildApp(saver), then run a fact-then-recall pair on one thread id.
  //         Re-run the script: the same thread still knows the fact.
  console.log("TODO: compile with the checkpointer, then run the thread demos.");
}

main().catch(console.error);
