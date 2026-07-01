/**
 * Task 7 — Multi-agent supervisor with Command  🔴
 *
 * What this teaches:
 *   - The LangGraph-native multi-agent primitive is Command: a node returns
 *     `new Command({ goto, update })` to set state AND jump in one move.
 *   - Supervisor pattern: a router node picks the next worker; each worker hands
 *     control back to the supervisor; repeat until the supervisor goes to END.
 *   - A "handoff" is just "update shared state + goto another node."
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/07-supervisor.ts
 */

import {
  StateGraph,
  START,
  END,
  Annotation,
  Command,
  MessagesAnnotation,
} from "@langchain/langgraph";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getChatModel } from "./_model.js";

const search = tool(
  async ({ query }) => {
    const db: Record<string, string> = {
      "eiffel tower height": "The Eiffel Tower is 330 metres tall.",
    };
    return db[query.toLowerCase().trim()] ?? `No result for: ${query}`;
  },
  {
    name: "search",
    description: "Look up a fact.",
    schema: z.object({ query: z.string() }),
  },
);

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
    description: "Evaluate arithmetic.",
    schema: z.object({ expression: z.string() }),
  },
);

const State = Annotation.Root({
  ...MessagesAnnotation.spec,
  next: Annotation<string>(), // which worker the supervisor chose (for tracing)
});
type StateT = typeof State.State;

// supervisor returns a Command(goto=...) — the routing primitive.
async function supervisor(state: StateT) {
  // TODO 1: make ONE routing call. Build a SystemMessage telling the model it routes
  //         between the two workers (researcher = facts, mathematician = arithmetic)
  //         and must reply with EXACTLY one word: a worker name or FINISH. Invoke the
  //         chat model on [that system message, ...state.messages], coerce the reply's
  //         content to a normalised string (trim + lowercase), and map it to a `goto`:
  //         END on "finish", else the matching worker name. Return
  //         `new Command({ goto, update: { next: goto } })` so one move both records
  //         the choice and jumps.
  throw new Error("TODO 1");
}

async function researcher(state: StateT) {
  const model = (await getChatModel()).bindTools([search]);
  const sys = new SystemMessage(
    "You are a researcher. Use search, then report the fact.",
  );
  const reply = await model.invoke([sys, ...state.messages]);
  return new Command({ goto: "supervisor", update: { messages: [reply] } });
}

async function mathematician(state: StateT) {
  const model = (await getChatModel()).bindTools([calculator]);
  const sys = new SystemMessage(
    "You are a mathematician. Use the calculator for any arithmetic.",
  );
  const reply = await model.invoke([sys, ...state.messages]);
  return new Command({ goto: "supervisor", update: { messages: [reply] } });
}

async function buildApp() {
  // ends: tells the graph which nodes a Command may jump to.
  return new StateGraph(State)
    .addNode("supervisor", supervisor, { ends: ["researcher", "mathematician", END] })
    .addNode("researcher", researcher, { ends: ["supervisor"] })
    .addNode("mathematician", mathematician, { ends: ["supervisor"] })
    .addEdge(START, "supervisor")
    .compile();
}

async function main() {
  const app = await buildApp();
  const question = "How tall is the Eiffel Tower in feet? (1 m = 3.281 ft)";

  // TODO 2: stream the app with { streamMode: "updates" } on a HumanMessage carrying
  //         the `question`, and log each chunk's node keys. Watch the handoffs cycle:
  //         supervisor -> worker -> supervisor -> ... -> END.
  console.log("TODO: implement supervisor routing, then trace the handoffs.");
}

main().catch(console.error);
