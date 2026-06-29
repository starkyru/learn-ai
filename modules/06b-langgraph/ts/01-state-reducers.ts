/**
 * Task 1 — State, channels & reducers  🟡
 *
 * What this teaches:
 *   - State is built with Annotation.Root; each field is a CHANNEL with a REDUCER.
 *   - A node returns ONLY the keys it changes; LangGraph merges each key through
 *     its channel's reducer:
 *       * no reducer            = last-write-wins (overwrite)
 *       * (a, b) => a.concat(b) = append (lists, like messages)
 *       * (a, b) => a + b       = accumulate (sum a counter)
 *   - "Designing the state" is mostly "pick the right reducer per channel."
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/01-state-reducers.ts
 *
 * No model/API key needed — pure graph mechanics.
 */

import { StateGraph, START, END, Annotation } from "@langchain/langgraph";
import { AIMessage, HumanMessage, BaseMessage } from "@langchain/core/messages";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// TODO 1: give each channel the right reducer.
const DemoState = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (a, b) => a.concat(b), // append
    default: () => [],
  }),
  stepCount: Annotation<number>({
    // TODO: make this SUM updates instead of overwriting.
    reducer: (_a, b) => b, // <-- overwrite for now; change to (a, b) => a + b
    default: () => 0,
  }),
  lastTool: Annotation<string>(), // no reducer => overwrite (last write wins)
});

type DemoStateT = typeof DemoState.State;

// ---------------------------------------------------------------------------
// Nodes — each returns a PARTIAL update to all three channels
// ---------------------------------------------------------------------------

const nodeA = (_state: DemoStateT) => ({
  messages: [new AIMessage("node A ran")],
  stepCount: 1,
  lastTool: "search",
});

const nodeB = (_state: DemoStateT) => ({
  messages: [new AIMessage("node B ran")],
  stepCount: 1,
  lastTool: "calculator",
});

// ---------------------------------------------------------------------------
// Build
// ---------------------------------------------------------------------------

// TODO 2: wire START -> a -> b -> END and compile.
const app = new StateGraph(DemoState)
  .addNode("a", nodeA)
  .addNode("b", nodeB)
  .addEdge(START, "a")
  // .addEdge("a", "b")
  // .addEdge("b", END)
  .compile();

async function main() {
  const initial = { messages: [new HumanMessage("go")], stepCount: 0, lastTool: "" };

  // TODO 3: stream with streamMode "values" and print state after each step.
  //   PREDICT first (with the SUM reducer): messages=3, stepCount=2, lastTool="calculator".
  for await (const snap of await app.stream(initial, { streamMode: "values" })) {
    console.log(
      `messages=${snap.messages.length}  stepCount=${snap.stepCount}  lastTool=${JSON.stringify(snap.lastTool)}`,
    );
  }

  // TODO 4: flip stepCount back to overwrite; predict (-> 1), then re-run.
}

main().catch(console.error);
