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
// TODO 1: Import the LangGraph building blocks you'll wire together below.
//         From @langchain/langgraph you'll need the graph builder, the START /
//         END sentinels, the checkpointer (stretch TODO 9), and the `Annotation`
//         helper used to declare state (TODO 2).
//         From @langchain/core/messages you'll need the message classes you
//         construct/inspect (Human / AI / Tool).
//         From @langchain/core/tools you'll need the `tool` declaration helper.
//         You'll also need a ChatOpenAI or ChatAnthropic model from
//         @langchain/openai or @langchain/anthropic — but those require
//         separate installs. Alternatively, build a thin adapter that wraps
//         the llm-core provider (see TODO 2).

// ---------------------------------------------------------------------------
// State definition
// LangGraph agents carry a state object that gets updated at each node.
// ---------------------------------------------------------------------------

// TODO 2: Define the agent state with `Annotation.Root({...})`. It needs a single
//         `messages` channel typed as BaseMessage[], declared with an
//         `Annotation<...>` whose reducer CONCATENATES the previous and new
//         messages (so each node's output is appended, not replaced).

// ---------------------------------------------------------------------------
// Tool definitions
// ---------------------------------------------------------------------------

// TODO 3: Define the same tools as Task 1 (calculator, search) with the `tool()`
//         helper. Each call takes an async implementation whose argument is the
//         validated input object, plus a config object with `name`, `description`,
//         and a zod `schema` describing each argument. Name the schema fields to
//         match what your implementations destructure. Reuse Task 1's calculator
//         (eval-in-try/catch) and search (canned lookup) logic.

const tools: unknown[] = [
  // TODO: add your tool objects here
];

// ---------------------------------------------------------------------------
// Graph nodes
// ---------------------------------------------------------------------------

// TODO 4: Implement the agent node — an async function taking the state, that
//         invokes the tools-bound model on `state.messages` and returns
//         `{ messages: [response] }` (the reducer appends it).

// TODO 5: Implement the tools node. Take the last message (the AI message with
//         tool_calls). Build a name->tool lookup, then for each tool_call invoke
//         the matching tool on its args and wrap the result in a `ToolMessage`
//         tagged with that call's id. Return them under `messages`.

// TODO 6: Implement the routing function used by the conditional edge: inspect
//         the last message — if it carries tool_calls, return "tools", otherwise
//         return END. Type its return as "tools" | typeof END.

// ---------------------------------------------------------------------------
// Build the graph
// ---------------------------------------------------------------------------

// TODO 7: Wire up the graph. Construct a `new StateGraph(AgentState)`, add the
//         "agent" and "tools" nodes, then add the edges forming the cycle:
//           START -> "agent", a CONDITIONAL edge from "agent" (using
//           shouldContinue) to "tools" or END, and "tools" -> "agent".
//         Compile it into an `app`.

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const question =
    "What is the height of the Eiffel Tower in metres, and convert it to feet? (1 metre = 3.281 feet)";

  console.log(`Question: ${question}\n`);

  // TODO 8: Invoke the compiled graph with an initial state whose `messages` is a
  //         single HumanMessage(question). Prefer `app.stream(...)` and iterate the
  //         async stream with `for await`, printing each yielded step so you can
  //         watch the agent -> tools -> agent cycle happen.

  console.log("TODO: compile the graph and invoke it.");

  // TODO 9 (stretch): Add a MemorySaver checkpointer to persist state across
  //         runs. Pass { configurable: { thread_id: "session-1" } } to invoke().
  //         Then ask a follow-up question and see that the agent remembers context.
}

main().catch(console.error);
