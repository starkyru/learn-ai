/**
 * Task 4 — Framework agent with LangGraph.js 🟢
 *
 * What this teaches:
 *   - LangGraph models an agent as a state machine: nodes transform state,
 *     edges (including conditional edges) decide what runs next.
 *   - The "loop" you built from scratch in Task 1 is just a graph with a
 *     cycle: agent_node -> tools_node -> agent_node -> END.
 *   - Frameworks give you persistence, streaming, checkpointing, and
 *     observability almost for free — at the cost of abstraction.
 *   - Understanding the from-scratch version (Task 1) makes the framework
 *     transparent instead of magical.
 *
 * How to run:
 *   pnpm tsx modules/06-agents/ts/04-framework.ts
 *
 * Note: @langchain/langgraph is declared in this module's package.json.
 *       Run `pnpm install` first if you haven't.
 */

import "dotenv/config";
// TODO 1: Import the LangGraph building blocks you'll use.
//         Key imports from @langchain/langgraph:
//           StateGraph, END, START, MemorySaver, Annotation
//         Key imports from @langchain/core/messages:
//           HumanMessage, AIMessage, ToolMessage, SystemMessage
//         Key imports from @langchain/core/tools:
//           tool (the function to declare tools)
//         You'll also need the ChatOpenAI or ChatAnthropic model from
//         @langchain/openai or @langchain/anthropic — but those require
//         separate installs. Alternatively, build a thin adapter that wraps
//         the llm-core provider (see TODO 2).

// import { StateGraph, END, START, Annotation } from "@langchain/langgraph";
// import { HumanMessage, AIMessage, ToolMessage } from "@langchain/core/messages";

// ---------------------------------------------------------------------------
// State definition
// LangGraph agents carry a state object that gets updated at each node.
// ---------------------------------------------------------------------------

// TODO 2: Define the agent state using Annotation.Root.
//         The standard ReAct agent state is just a list of messages.
//         LangGraph knows how to reduce/append them automatically.
//
// const AgentState = Annotation.Root({
//   messages: Annotation<BaseMessage[]>({
//     reducer: (x, y) => x.concat(y),
//   }),
// });

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

// TODO 3: Define the same tools as Task 1 using LangGraph's `tool()` helper.
//         Each tool takes a zod schema for its inputs and returns a string.
//
// import { z } from "zod";
// const calculatorTool = tool(
//   async ({ expression }) => { /* ... */ },
//   { name: "calculator", description: "...", schema: z.object({ expression: z.string() }) }
// );

const tools: unknown[] = [
  // TODO: add your tool objects here
];

// ---------------------------------------------------------------------------
// Graph nodes
// ---------------------------------------------------------------------------

// TODO 4: Implement the agent node.
//         It receives the current state, calls the LLM (with tools bound),
//         and returns the new message(s) to add to state.
//
// async function agentNode(state: typeof AgentState.State) {
//   const response = await modelWithTools.invoke(state.messages);
//   return { messages: [response] };
// }

// TODO 5: Implement the tools node.
//         It finds all ToolCall objects in the last AI message, executes each
//         tool, and returns ToolMessage objects with the results.
//
// async function toolsNode(state: typeof AgentState.State) {
//   const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
//   const toolMessages: ToolMessage[] = [];
//   for (const toolCall of lastMessage.tool_calls ?? []) {
//     const tool = toolsByName[toolCall.name];
//     const result = await tool.invoke(toolCall.args);
//     toolMessages.push(new ToolMessage({ content: result, tool_call_id: toolCall.id! }));
//   }
//   return { messages: toolMessages };
// }

// TODO 6: Implement the routing function (conditional edge).
//         If the last message has tool_calls, go to "tools".
//         Otherwise, go to END.
//
// function shouldContinue(state: typeof AgentState.State): "tools" | typeof END {
//   const last = state.messages[state.messages.length - 1] as AIMessage;
//   return last.tool_calls?.length ? "tools" : END;
// }

// ---------------------------------------------------------------------------
// Build the graph
// ---------------------------------------------------------------------------

// TODO 7: Wire up the graph.
//
// const workflow = new StateGraph(AgentState)
//   .addNode("agent", agentNode)
//   .addNode("tools", toolsNode)
//   .addEdge(START, "agent")
//   .addConditionalEdges("agent", shouldContinue)
//   .addEdge("tools", "agent");
//
// const app = workflow.compile();

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const question =
    "What is the height of the Eiffel Tower in metres, and convert it to feet? (1 metre = 3.281 feet)";

  console.log(`Question: ${question}\n`);

  // TODO 8: Invoke the compiled graph with an initial HumanMessage and stream
  //         or await the result. Print each step as it happens.
  //
  // const stream = await app.stream({
  //   messages: [new HumanMessage(question)],
  // });
  // for await (const step of stream) {
  //   console.log(JSON.stringify(step, null, 2));
  // }

  console.log("TODO: compile the graph and invoke it.");

  // TODO 9 (stretch): Add a MemorySaver checkpointer to persist state across
  //         runs. Pass { configurable: { thread_id: "session-1" } } to invoke().
  //         Then ask a follow-up question and see that the agent remembers context.
}

main().catch(console.error);
