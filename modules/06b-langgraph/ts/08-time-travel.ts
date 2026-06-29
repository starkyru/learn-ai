/**
 * Task 8 — Time travel  🟡
 *
 * What this teaches:
 *   - With a checkpointer you get the FULL history of a thread:
 *       getState(config)        -> the current StateSnapshot
 *       getStateHistory(config) -> every past checkpoint, newest first
 *   - Resume from an OLD checkpoint (pass its config) -> the run FORKS a branch.
 *   - updateState(config, values) edits state (through channel reducers) to make
 *     a corrected checkpoint, then you continue from the edit.
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/08-time-travel.ts
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
  const chat = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });
  return new StateGraph(MessagesAnnotation)
    .addNode("chat", chat)
    .addEdge(START, "chat")
    .compile({ checkpointer });
}

async function main() {
  const app = await buildApp(new MemorySaver());
  const config = { configurable: { thread_id: "tt-1" } };

  // 1) Run a couple of turns so the thread has several checkpoints.
  await app.invoke(
    { messages: [new HumanMessage("Pick a number 1-10 and remember it.")] },
    config,
  );
  await app.invoke({ messages: [new HumanMessage("Now double it.")] }, config);

  // TODO 1: list checkpoints (newest first) with id and `next` nodes.
  //   const history: any[] = [];
  //   for await (const snap of app.getStateHistory(config)) {
  //     history.push(snap);
  //     console.log(snap.config.configurable?.checkpoint_id, "next=", snap.next, "msgs=", snap.values.messages.length);
  //   }

  // TODO 2: fork from an EARLIER checkpoint by passing its config back in.
  //   const earlier = history[history.length - 2];
  //   const forked = await app.invoke(
  //     { messages: [new HumanMessage("Actually, triple it instead.")] },
  //     earlier.config,            // <-- resume from this checkpoint
  //   );
  //   console.log("forked branch:", forked.messages.at(-1).content);

  // TODO 3: edit state with updateState, then continue from the correction.
  //   const newConfig = await app.updateState(config, { messages: [new HumanMessage("Correction: the number was 7.")] });
  //   const cont = await app.invoke(null, newConfig);
  //   console.log("after edit:", cont.messages.at(-1).content);
  console.log("TODO: list history, fork from an old checkpoint, edit-then-continue.");
}

main().catch(console.error);
