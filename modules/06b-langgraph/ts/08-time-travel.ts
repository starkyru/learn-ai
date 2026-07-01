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

  // TODO 1: iterate the `app.getStateHistory(config)` async generator (it yields
  //         snapshots newest-first), collecting them into an array. For each, log its
  //         checkpoint id (under snap.config.configurable), its `.next` nodes, and its
  //         message count (snap.values.messages.length).

  // TODO 2: fork from an EARLIER checkpoint. Pick an older snapshot from the collected
  //         history (e.g. second-to-last) and invoke the app with a new HumanMessage
  //         BUT pass that snapshot's `.config` instead of the live config — resuming
  //         from an old checkpoint FORKS a new branch. Log the forked reply.

  // TODO 3: edit-then-continue. Call `app.updateState(config, { ... })` with a message
  //         that corrects the state; it applies through the channel reducers and
  //         returns a new config pointing at the edited checkpoint. Then invoke the app
  //         with `null` as input and that new config to continue from the edit, and log
  //         the result.
  console.log("TODO: list history, fork from an old checkpoint, edit-then-continue.");
}

main().catch(console.error);
