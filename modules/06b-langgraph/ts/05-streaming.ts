/**
 * Task 5 — Streaming modes  🟢
 *
 * What this teaches:
 *   - A graph emits a stream; streamMode picks the granularity:
 *       "updates"  -> just the delta each node returned  (progress UI)
 *       "values"   -> the full state after each step      ("state now")
 *       "messages" -> LLM TOKENS as they generate          (typing effect)
 *   - You can pass an ARRAY of modes; each event arrives tagged with its mode.
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/05-streaming.ts
 */

import { StateGraph, START, MessagesAnnotation } from "@langchain/langgraph";
import { ToolNode, toolsCondition } from "@langchain/langgraph/prebuilt";
import { HumanMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getChatModel } from "./_model.js";

const QUESTION =
  "What is 330 metres in feet? (1 metre = 3.281 feet). Use the calculator.";

const calculator = tool(
  async ({ expression }) => {
    try {
      // eslint-disable-next-line no-eval -- educational demo only
      return String(eval(expression));
    } catch (e) {
      return `Error: ${e}`;
    }
  },
  {
    name: "calculator",
    description: "Evaluate a simple arithmetic expression.",
    schema: z.object({ expression: z.string() }),
  },
);

const TOOLS = [calculator];

async function buildApp() {
  const model = (await getChatModel()).bindTools(TOOLS);
  const agentNode = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });

  return new StateGraph(MessagesAnnotation)
    .addNode("agent", agentNode)
    .addNode("tools", new ToolNode(TOOLS))
    .addEdge(START, "agent")
    .addConditionalEdges("agent", toolsCondition)
    .addEdge("tools", "agent")
    .compile();
}

async function main() {
  const app = await buildApp();
  const inputs = { messages: [new HumanMessage(QUESTION)] };

  // TODO 1: stream with `app.stream(inputs, { streamMode: "updates" })`. Each chunk
  //         is an object keyed by node name -> that node's delta. Iterate its entries
  //         and log which node ran and how many messages it added.

  // TODO 2: stream with { streamMode: "values" }. Now each event is the FULL state
  //         after a step — log the running message count so you can watch it grow.

  // TODO 3: stream with { streamMode: "messages" }. Each event destructures to a
  //         [token, metadata] pair; write the token's content to stdout as it arrives
  //         (no newline) for a typing effect, then log a trailing newline.

  // TODO 4 (stretch): pass an array of modes, e.g. ["updates", "messages"], and tag
  //         each event by its mode so you can see how they interleave.
  console.log("TODO: implement the three stream modes and compare them.");
}

main().catch(console.error);
