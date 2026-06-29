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

  // TODO 1: compile WITH the checkpointer so state is saved per thread.
  //   return graph.compile({ checkpointer });
  return graph.compile();
}

async function ask(app: any, text: string, threadId: string): Promise<string> {
  const config = { configurable: { thread_id: threadId } };
  const result = await app.invoke({ messages: [new HumanMessage(text)] }, config);
  return result.messages.at(-1).content;
}

async function main() {
  const app = await buildApp(new MemorySaver());

  // TODO 2: same thread remembers.
  //   console.log(await ask(app, "My name is Ada. Remember it.", "thread-A"));
  //   console.log(await ask(app, "What's my name?", "thread-A"));   // -> "Ada"

  // TODO 3: a different thread does NOT remember.
  //   console.log(await ask(app, "What's my name?", "thread-B"));   // -> doesn't know

  // TODO 4 (restart-survival): swap in a file-backed saver and re-run the script.
  //   import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";
  //   const saver = SqliteSaver.fromConnString("checkpoints.sqlite");
  //   const persistent = await buildApp(saver);
  //   console.log(await ask(persistent, "Codename is Borealis.", "persist-1"));
  //   console.log(await ask(persistent, "What's the codename?", "persist-1"));
  console.log("TODO: compile with the checkpointer, then run the thread demos.");
}

main().catch(console.error);
