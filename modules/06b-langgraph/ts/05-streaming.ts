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

  // TODO 1: streamMode "updates" — print which node ran and its delta.
  //   for await (const chunk of await app.stream(inputs, { streamMode: "updates" })) {
  //     for (const [node, update] of Object.entries(chunk)) {
  //       console.log(`[${node}] +${(update as any).messages.length} message(s)`);
  //     }
  //   }

  // TODO 2: streamMode "values" — print the running message count.
  //   for await (const snap of await app.stream(inputs, { streamMode: "values" })) {
  //     console.log("state messages:", snap.messages.length);
  //   }

  // TODO 3: streamMode "messages" — print LLM TOKENS as they arrive.
  //   for await (const [token] of await app.stream(inputs, { streamMode: "messages" })) {
  //     if (token.content) process.stdout.write(String(token.content));
  //   }
  //   console.log();

  // TODO 4 (stretch): pass ["updates", "messages"] and tag each event by mode.
  console.log("TODO: implement the three stream modes and compare them.");
}

main().catch(console.error);
