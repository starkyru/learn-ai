/**
 * Task 2 — Conditional edges & the prebuilt ToolNode  🟢
 *
 * What this teaches:
 *   - The ReAct loop from module 06 is a graph with a cycle and ONE decision:
 *     "did the model ask for a tool?" — that's a CONDITIONAL EDGE.
 *   - LangGraph ships the pieces you'd otherwise hand-roll:
 *       * ToolNode      — runs the tool_calls in the last AI message
 *       * toolsCondition — the router ("tools if tool_calls else END")
 *   - createReactAgent({ llm, tools }) builds the whole graph for you.
 *   - Build it THREE ways and confirm identical behaviour.
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/02-conditional-toolnode.ts
 *   (install a model package first, e.g. `pnpm add @langchain/ollama`)
 */

import { StateGraph, START, END, MessagesAnnotation } from "@langchain/langgraph";
import {
  ToolNode,
  toolsCondition,
  createReactAgent,
} from "@langchain/langgraph/prebuilt";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getChatModel } from "./_model.js";

const QUESTION =
  "What is the height of the Eiffel Tower in metres, and what is that in feet? (1 metre = 3.281 feet)";

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

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
    description: "Evaluate a simple arithmetic expression like '330 * 3.281'.",
    schema: z.object({ expression: z.string() }),
  },
);

const search = tool(
  async ({ query }) => {
    const db: Record<string, string> = {
      "eiffel tower height": "The Eiffel Tower is 330 metres tall.",
      "capital of france": "The capital of France is Paris.",
    };
    return db[query.toLowerCase().trim()] ?? `No result for: ${query}`;
  },
  {
    name: "search",
    description: "Look up a fact from a tiny knowledge base.",
    schema: z.object({ query: z.string() }),
  },
);

const TOOLS = [calculator, search];

// ---------------------------------------------------------------------------
// Variant A — hand-wired graph with YOUR OWN router
// ---------------------------------------------------------------------------

async function buildHandwired() {
  const model = (await getChatModel()).bindTools(TOOLS);

  const agentNode = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });

  // TODO 1: write the router `route(state)`. Grab the last message (cast to
  //         AIMessage) and decide: if it carries any tool_calls, return "tools";
  //         otherwise return END.

  return (
    new StateGraph(MessagesAnnotation)
      .addNode("agent", agentNode)
      .addNode("tools", new ToolNode(TOOLS))
      .addEdge(START, "agent")
      // TODO 2: register your router with `.addConditionalEdges("agent", route)`, and
      //         close the ReAct cycle with an edge from "tools" back to "agent".
      .compile()
  );
}

// ---------------------------------------------------------------------------
// Variant B — same graph, prebuilt toolsCondition instead of your router
// ---------------------------------------------------------------------------

async function buildPrebuiltRouter() {
  const model = (await getChatModel()).bindTools(TOOLS);
  const agentNode = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });

  return (
    new StateGraph(MessagesAnnotation)
      .addNode("agent", agentNode)
      .addNode("tools", new ToolNode(TOOLS))
      .addEdge(START, "agent")
      // TODO 3: same wiring as TODO 2, but pass the prebuilt `toolsCondition` to
      //         `.addConditionalEdges` on "agent" instead of your own router.
      .addEdge("tools", "agent")
      .compile()
  );
}

// ---------------------------------------------------------------------------
// Variant C — one line
// ---------------------------------------------------------------------------

async function buildFullyPrebuilt() {
  // TODO 4: collapse the whole graph into one call — `createReactAgent({ ... })`
  //         takes an options object with the chat model (`llm`) and `tools`; return it.
  throw new Error("TODO 4");
}

async function run(app: any, label: string) {
  console.log(`\n=== ${label} ===`);
  const result = await app.invoke({ messages: [new HumanMessage(QUESTION)] });
  console.log(result.messages.at(-1).content);
}

async function main() {
  await run(await buildHandwired(), "A: hand-wired router");
  await run(await buildPrebuiltRouter(), "B: toolsCondition");
  await run(await buildFullyPrebuilt(), "C: createReactAgent");
  // All three should reach ~1082 feet. Point at the lines B and C deleted.
}

main().catch(console.error);
