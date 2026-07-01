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
      // TODO 1: add the compiled `research` subgraph DIRECTLY as a node (a compiled
      //         graph IS a valid node) — give it a name like "research".
      .addNode("summarise", summarise)
      .addEdge(START, "preprocess")
      // TODO 2: wire the linear path preprocess -> research -> summarise -> END with
      //         .addEdge calls before .compile().
      .compile()
  );
}

async function main() {
  const app = await buildParent();
  const inputs = { messages: [new HumanMessage("How tall is the tallest mountain?")] };

  // TODO 3: stream the parent with `{ subgraphs: true, streamMode: "updates" }`. Each
  //         event destructures to a [namespace, chunk] pair: the namespace is [] for
  //         the parent and ["research:<id>"] for steps inside the subgraph. Log the
  //         namespace and the chunk's node keys to watch the inner steps surface.

  // TODO 4: confirm isolation — inspect the final parent state and verify it has no
  //         `sourcesSeen` key (that PRIVATE channel never leaked out of the subgraph).
  console.log("TODO: add the subgraph as a node, stream with subgraphs:true.");
}

main().catch(console.error);
