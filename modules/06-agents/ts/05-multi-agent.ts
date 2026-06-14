/**
 * Task 5 — Multi-agent system 🟡
 *
 * What this teaches:
 *   - A single agent context window and attention span has limits. Breaking work
 *     into a planner + specialised workers is a practical architectural pattern.
 *   - The planner decomposes the user request into subtasks and delegates each
 *     to a worker that has its own prompt, tools, and budget.
 *   - The planner collects worker results and synthesises a final answer.
 *   - This pattern scales: add more workers (researcher, coder, critic, etc.)
 *     without changing the planner's core loop.
 *
 * Architecture:
 *   User question
 *     └─> Planner  (LLM call: decompose into subtasks, emit JSON task list)
 *           ├─> Worker A  (LLM call: solve subtask A, return result)
 *           ├─> Worker B  (LLM call: solve subtask B, return result)
 *           └─> Synthesiser  (LLM call: combine results into a final answer)
 *
 * How to run:
 *   pnpm tsx modules/06-agents/ts/05-multi-agent.ts
 */

import { getProvider, ChatMessage } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Subtask schema — what the planner emits
// ---------------------------------------------------------------------------

interface Subtask {
  id: string;        // e.g. "task-1"
  worker: string;    // which worker to use: "researcher" | "calculator" | "writer"
  instruction: string; // the specific question or task for that worker
}

// ---------------------------------------------------------------------------
// Planner agent
// ---------------------------------------------------------------------------

// TODO 1: Implement the system prompt for the planner.
//         It should instruct the model to:
//           - Break the user question into 2-4 independent subtasks.
//           - Emit ONLY a JSON array of Subtask objects (no prose).
//           - Choose a worker type for each subtask:
//               "researcher" — fact retrieval or background info
//               "calculator" — numerical computation
//               "writer"     — synthesis, summarisation, final prose
//         Example output:
//           [
//             { "id": "task-1", "worker": "researcher", "instruction": "Find the height of the Eiffel Tower in metres." },
//             { "id": "task-2", "worker": "calculator",  "instruction": "Convert 330 metres to feet using 1m = 3.281ft." }
//           ]

const PLANNER_SYSTEM_PROMPT = "TODO: write the planner system prompt.";

async function runPlanner(question: string): Promise<Subtask[]> {
  const llm = getProvider();

  // TODO 2: Call llm.chat() with PLANNER_SYSTEM_PROMPT and the user question.
  //         Parse the JSON array from the response.
  //         Validate that each item has id, worker, and instruction fields.
  //         If parsing fails, throw a descriptive error.

  console.log(`\n[Planner] Decomposing: "${question}"`);
  throw new Error("TODO: implement runPlanner");
}

// ---------------------------------------------------------------------------
// Worker agents
// ---------------------------------------------------------------------------

// Worker system prompts — each worker has a different persona / skill set.

const WORKER_PROMPTS: Record<string, string> = {
  researcher:
    // TODO 3a: Write a researcher prompt. This worker answers factual questions
    //          concisely. It should say "I don't know" rather than hallucinate.
    "TODO: researcher prompt",

  calculator:
    // TODO 3b: Write a calculator prompt. This worker receives a computation
    //          task described in plain English, does the math step by step,
    //          and returns only the numeric result + brief explanation.
    "TODO: calculator prompt",

  writer:
    // TODO 3c: Write a writer/synthesiser prompt. This worker receives a
    //          collection of findings (other workers' results) and combines
    //          them into a clear, concise final answer for the user.
    "TODO: writer/synthesiser prompt",
};

async function runWorker(subtask: Subtask): Promise<string> {
  const llm = getProvider();
  const systemPrompt =
    WORKER_PROMPTS[subtask.worker] ?? WORKER_PROMPTS["researcher"];

  // TODO 4: Call llm.chat() with the appropriate system prompt and the
  //         subtask instruction as the user message. Return the text result.
  //         Log: "[Worker:<type>] <instruction> -> <result>"

  console.log(`\n[Worker:${subtask.worker}] ${subtask.instruction}`);
  throw new Error("TODO: implement runWorker");
}

// ---------------------------------------------------------------------------
// Synthesiser — combines all worker results into one answer
// ---------------------------------------------------------------------------

async function runSynthesiser(
  originalQuestion: string,
  results: { subtask: Subtask; result: string }[]
): Promise<string> {
  const llm = getProvider();

  // TODO 5: Build a message for the writer worker that includes:
  //         - The original question
  //         - Each subtask's instruction and its result, clearly labelled
  //         Call runWorker() with a synthetic Subtask of type "writer",
  //         or call llm.chat() directly with a custom synthesis prompt.
  //         Return the final synthesised answer.

  console.log("\n[Synthesiser] Combining results...");
  throw new Error("TODO: implement runSynthesiser");
}

// ---------------------------------------------------------------------------
// Orchestrator — runs the full planner -> workers -> synthesiser pipeline
// ---------------------------------------------------------------------------

async function runMultiAgent(question: string): Promise<string> {
  console.log("=".repeat(60));
  console.log(`Question: ${question}`);
  console.log("=".repeat(60));

  // TODO 6: Wire the pipeline:
  //   a) Call runPlanner(question) to get subtasks.
  //   b) Print the plan (subtask list).
  //   c) Run the non-writer workers. You can run them sequentially (simpler)
  //      or in parallel with Promise.all() (faster, but order is non-deterministic).
  //   d) Collect { subtask, result } pairs.
  //   e) Call runSynthesiser() to produce the final answer.
  //   f) Return the final answer.

  throw new Error("TODO: implement runMultiAgent orchestrator");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const question =
    "Explain what the Eiffel Tower is, how tall it is, and what its height " +
    "is in feet. Then write a one-sentence fun fact about it.";

  const answer = await runMultiAgent(question);
  console.log("\n" + "=".repeat(60));
  console.log("Final Answer:\n", answer);

  // TODO 7 (stretch): Add a "critic" worker that reviews the final answer and
  //         suggests improvements. Feed the critique back to the writer for a
  //         revised answer. This is the "reflection" pattern.
}

main().catch(console.error);
