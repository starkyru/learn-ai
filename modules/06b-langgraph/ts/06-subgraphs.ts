/**
 * Task 6 — Subgraphs  🟡
 *
 * What this teaches:
 *   - A COMPILED graph can be used as a NODE inside a bigger graph (a subgraph) —
 *     the unit of composition for large agent systems.
 *   - Shared state flows by matching CHANNEL NAMES: parent and subgraph share
 *     `messages`, but the subgraph keeps PRIVATE channels the parent never sees.
 *   - Stream the parent with `{ subgraphs: true }` to watch inner steps.
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/06-subgraphs.ts
 */

import {
  StateGraph,
  START,
  END,
  MessagesAnnotation,
  Annotation,
} from "@langchain/langgraph";
import { ToolNode, toolsCondition } from "@langchain/langgraph/prebuilt";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getChatModel } from "./_model.js";

const search = tool(
  async ({ query }) => {
    const db: Record<string, string> = {
      "tallest mountain": "Mount Everest is 8849 metres tall.",
    };
    return db[query.toLowerCase().trim()] ?? `No result for: ${query}`;
  },
  {
    name: "search",
    description: "Look up a fact.",
    schema: z.object({ query: z.string() }),
  },
);

// ---------------------------------------------------------------------------
// Inner subgraph — a self-contained ReAct researcher with a PRIVATE channel
// ---------------------------------------------------------------------------

const ResearchState = Annotation.Root({
  ...MessagesAnnotation.spec, // shares `messages` with the parent
  sourcesSeen: Annotation<number>({ reducer: (a, b) => a + b, default: () => 0 }), // PRIVATE
});

async function buildResearchSubgraph() {
  const model = (await getChatModel()).bindTools([search]);
  const agent = async (state: typeof ResearchState.State) => ({
    messages: [await model.invoke(state.messages)],
    sourcesSeen: 1,
  });

  return new StateGraph(ResearchState)
    .addNode("agent", agent)
    .addNode("tools", new ToolNode([search]))
    .addEdge(START, "agent")
    .addConditionalEdges("agent", toolsCondition)
    .addEdge("tools", "agent")
    .compile();
}

// ---------------------------------------------------------------------------
// Parent graph — preprocess -> research(subgraph) -> summarise
// Parent state has NO `sourcesSeen` key, so it stays inside the subgraph.
// ---------------------------------------------------------------------------

async function buildParent() {
  const research = await buildResearchSubgraph();

  const preprocess = (_s: typeof MessagesAnnotation.State) => ({
    messages: [new HumanMessage("(framing the research question)")],
  });
  const summarise = (_s: typeof MessagesAnnotation.State) => ({
    messages: [new AIMessage("(summary of the research)")],
  });

  return (
    new StateGraph(MessagesAnnotation)
      .addNode("preprocess", preprocess)
      // TODO 1: add the compiled subgraph DIRECTLY as a node.
      //   .addNode("research", research)
      .addNode("summarise", summarise)
      .addEdge(START, "preprocess")
      // TODO 2: preprocess -> research -> summarise -> END
      .compile()
  );
}

async function main() {
  const app = await buildParent();
  const inputs = { messages: [new HumanMessage("How tall is the tallest mountain?")] };

  // TODO 3: stream with subgraphs:true so inner steps are visible.
  //   for await (const [ns, chunk] of await app.stream(inputs, { subgraphs: true, streamMode: "updates" })) {
  //     console.log(ns, Object.keys(chunk)); // ns is [] for parent, ["research:<id>"] for subgraph
  //   }

  // TODO 4: confirm isolation — the final parent state has no `sourcesSeen`.
  console.log("TODO: add the subgraph as a node, stream with subgraphs:true.");
}

main().catch(console.error);
