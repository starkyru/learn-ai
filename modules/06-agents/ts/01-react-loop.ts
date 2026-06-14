/**
 * Task 1 — ReAct loop from scratch 🔴
 *
 * What this teaches:
 *   - An "agent" is just a loop: the model thinks, picks an action, we run it,
 *     feed the result back, and repeat until the model declares a Final Answer.
 *   - ReAct (Reason + Act) structures this as alternating Thought / Action /
 *     Observation steps, all inside a plain chat message. No special APIs needed.
 *   - Parsing the model's intent from free text is fragile — that fragility is
 *     the point. You'll feel why native tool-calling (Task 2) is an improvement.
 *   - This works with ANY provider, including local Ollama models.
 *
 * How to run:
 *   pnpm tsx modules/06-agents/ts/01-react-loop.ts
 *
 * Note on tool calling:
 *   This task intentionally uses plain llm.chat() and text parsing — NOT the
 *   OpenAI/Anthropic tool-calling APIs. That means it works on ollama and any
 *   other OpenAI-compatible provider. The fragility of text parsing is a lesson.
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Tool registry
// A tool has a name, description (for the prompt), and an execute function.
// ---------------------------------------------------------------------------

interface Tool {
  name: string;
  description: string;
  execute(args: string): string;
}

// TODO 1: Implement the three tools below.
//         Each execute() receives raw argument text (a string the model wrote)
//         and returns a string the agent will see as its Observation.

const calculatorTool: Tool = {
  name: "calculator",
  description:
    'Evaluates a simple math expression. Input: a math expression as a string, e.g. "12 * (3 + 4)".',
  execute(args: string): string {
    // TODO: Use Function() or a safe eval to compute the expression.
    //       Return the result as a string, or an error message on failure.
    //       HINT: new Function("return " + args)()
    //       WARNING: In production never eval untrusted input. This is a demo.
    throw new Error("TODO: implement calculator");
  },
};

const searchTool: Tool = {
  name: "search",
  description:
    "Looks up a fact. This is a fake search that returns canned answers for a small set of queries. Input: a search query string.",
  execute(args: string): string {
    // TODO: Implement a simple lookup table. Return a relevant fake result, or
    //       "No result found for: <query>" if nothing matches.
    //       Add at least 4 entries so the agent can answer multi-step questions.
    //       Example entries:
    //         "population of france" -> "France has a population of ~68 million (2024)."
    //         "capital of france"    -> "The capital of France is Paris."
    //         "eiffel tower height"  -> "The Eiffel Tower is 330 metres tall."
    //         "year eiffel tower built" -> "The Eiffel Tower was built in 1889."
    throw new Error("TODO: implement search");
  },
};

const retrieveTool: Tool = {
  name: "retrieve",
  description:
    "Retrieves a stored note by key. Input: the key name. Returns the stored value or 'Not found'.",
  execute(args: string): string {
    // TODO: Use the in-memory store below to look up a value by key.
    //       If missing, return "Not found: <key>".
    throw new Error("TODO: implement retrieve");
  },
};

// In-memory store that the agent can read (and you can pre-populate).
const memoryStore: Record<string, string> = {
  "user-goal": "Find the height of the Eiffel Tower and compute 330 * 3.281.",
  hint: "Use search to find the height, then calculator to convert metres to feet.",
};

// ---------------------------------------------------------------------------
// Tool registry — map name -> Tool for dispatch
// ---------------------------------------------------------------------------
const TOOLS: Record<string, Tool> = {
  [calculatorTool.name]: calculatorTool,
  [searchTool.name]: searchTool,
  [retrieveTool.name]: retrieveTool,
};

// ---------------------------------------------------------------------------
// System prompt — teaches the model the ReAct format
// ---------------------------------------------------------------------------

function buildSystemPrompt(): string {
  const toolDescriptions = Object.values(TOOLS)
    .map((t) => `  ${t.name}: ${t.description}`)
    .join("\n");

  return `You are a helpful AI assistant that solves problems step by step using tools.

You MUST respond in this EXACT format on every turn until you have the final answer:

Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <the input to pass to the tool>

When you have enough information to answer the original question, respond with:

Thought: <your final reasoning>
Final Answer: <your complete answer to the question>

Available tools:
${toolDescriptions}

Rules:
- Always start with "Thought:"
- Only use one action per response
- Never make up tool results — wait for the Observation
- Stop only with "Final Answer:"`;
}

// ---------------------------------------------------------------------------
// Parser — extract Action / Action Input / Final Answer from model output
// ---------------------------------------------------------------------------

interface ParsedStep {
  thought: string;
  finalAnswer?: string;
  action?: string;
  actionInput?: string;
}

function parseModelOutput(text: string): ParsedStep {
  // TODO 2: Parse the model's response.
  //         Extract:
  //           - thought: the content after "Thought:" (up to the next keyword)
  //           - finalAnswer: content after "Final Answer:" (if present)
  //           - action: content after "Action:" (tool name)
  //           - actionInput: content after "Action Input:"
  //         Tip: use regex or simple line-by-line parsing.
  //         The function should never throw — return empty strings for missing parts.
  throw new Error("TODO: implement parseModelOutput");
}

// ---------------------------------------------------------------------------
// ReAct loop — the agent's brain
// ---------------------------------------------------------------------------

async function runReActAgent(question: string, maxSteps = 10): Promise<string> {
  const llm = getProvider();
  console.log(`\nProvider: ${llm.name} / ${llm.chatModel}`);
  console.log(`Question: ${question}\n`);
  console.log("=".repeat(60));

  const messages: ChatMessage[] = [
    { role: "system", content: buildSystemPrompt() },
    { role: "user", content: question },
  ];

  for (let step = 0; step < maxSteps; step++) {
    console.log(`\n--- Step ${step + 1} ---`);

    // TODO 3: Call llm.chat(messages) to get the model's next step.
    //         Print the raw model output so the learner can see what's happening.
    //         Parse it with parseModelOutput().
    //         If parsed.finalAnswer is present, print it and return it.
    //         If parsed.action is present:
    //           a) Look it up in TOOLS. If missing, set observation to an error.
    //           b) Call tool.execute(parsed.actionInput ?? "").
    //           c) Build an observation string: "Observation: <result>"
    //           d) Append the assistant's response + the observation as a user
    //              message to `messages`, then continue the loop.
    //         If neither action nor finalAnswer is found, break (malformed output).

    throw new Error("TODO: implement the ReAct loop body");
  }

  return "Agent did not reach a final answer within the step limit.";
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  // Try a multi-step question that needs search + calculator.
  const question =
    "What is the height of the Eiffel Tower in metres, and what is that in feet? " +
    "(1 metre = 3.281 feet — use the calculator tool)";

  const answer = await runReActAgent(question);
  console.log("\n" + "=".repeat(60));
  console.log("Final Answer:", answer);

  // TODO 4 (stretch): Add a second question that needs the retrieve tool.
  //   Try: "What is my current goal? Then accomplish it."
  //   Pre-populate memoryStore with a goal and watch the agent use retrieve + search + calculator.
}

main().catch(console.error);
