/**
 * Task 4 — Human-in-the-loop with interrupt()  🔴
 *
 * What this teaches:
 *   - The most-asked LangGraph production feature: pause for approval before a
 *     dangerous tool fires, then resume EXACTLY where you left off.
 *   - interrupt(payload) inside a node stops the graph and surfaces `payload`.
 *     Resume by invoking `new Command({ resume })` on the SAME thread.
 *   - Works only because the checkpointer snapshotted state at the pause.
 *   - (Stretch) static form: compile({ interruptBefore: ["tools"] }).
 *
 * How to run:
 *   pnpm tsx modules/06b-langgraph/ts/04-human-in-the-loop.ts
 */

import {
  StateGraph,
  START,
  END,
  MessagesAnnotation,
  MemorySaver,
  Command,
  interrupt,
} from "@langchain/langgraph";
import { HumanMessage, AIMessage, ToolMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { getChatModel } from "./_model.js";

const sendEmail = tool(async ({ to, body }) => `EMAIL SENT to ${to}: ${body}`, {
  name: "send_email",
  description: "Send an email. MUST be approved by a human before it sends.",
  schema: z.object({ to: z.string(), body: z.string() }),
});

const TOOLS = [sendEmail];
const TOOLS_BY_NAME: Record<string, typeof sendEmail> = { send_email: sendEmail };

async function buildApp() {
  const model = (await getChatModel()).bindTools(TOOLS);

  const agentNode = async (state: typeof MessagesAnnotation.State) => ({
    messages: [await model.invoke(state.messages)],
  });

  const toolsNode = async (state: typeof MessagesAnnotation.State) => {
    const last = state.messages.at(-1) as AIMessage;
    const out: ToolMessage[] = [];
    for (const call of last.tool_calls ?? []) {
      // TODO 1: gate send_email behind a human decision.
      //   if (call.name === "send_email") {
      //     const decision = interrupt({ action: "send_email", args: call.args });
      //     if (decision !== "approve") {
      //       out.push(new ToolMessage({
      //         content: "Human DENIED this email. Do not retry; explain instead.",
      //         tool_call_id: call.id!,
      //       }));
      //       continue;
      //     }
      //   }
      const result = await TOOLS_BY_NAME[call.name].invoke(call.args as any);
      out.push(new ToolMessage({ content: String(result), tool_call_id: call.id! }));
    }
    return { messages: out };
  };

  const route = (state: typeof MessagesAnnotation.State) => {
    const last = state.messages.at(-1) as AIMessage;
    return last.tool_calls?.length ? "tools" : END;
  };

  const graph = new StateGraph(MessagesAnnotation)
    .addNode("agent", agentNode)
    .addNode("tools", toolsNode)
    .addEdge(START, "agent")
    .addConditionalEdges("agent", route)
    .addEdge("tools", "agent");

  // TODO 2: compile WITH a checkpointer — interrupts require it.
  //   return graph.compile({ checkpointer: new MemorySaver() });
  return graph.compile();
}

async function main() {
  const app = await buildApp();
  const config = { configurable: { thread_id: "hitl-1" } };
  const prompt = "Email ada@example.com to say the build passed.";

  // TODO 3: first invoke runs until interrupt(), then pauses.
  //   const result = await app.invoke({ messages: [new HumanMessage(prompt)] }, config);
  //   console.log("PAUSED, awaiting approval:", result.__interrupt__);

  // TODO 4: resume with a human decision on the SAME thread.
  //   const approved = await app.invoke(new Command({ resume: "approve" }), config); // "deny" rejects
  //   console.log(approved.messages.at(-1).content);
  console.log("TODO: invoke, observe the pause, resume with new Command({ resume }).");
}

main().catch(console.error);
