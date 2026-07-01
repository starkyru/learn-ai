/**
 * Task 3 🟡 — Reimplement CrewAI: role-grounded Agents, Tasks, a sequential Crew.
 *
 * What you'll learn:
 *   - CrewAI's core idea: an Agent is a *persona* (role + goal + backstory) bound
 *     to a model. Executing a Task = build a prompt that grounds the model in
 *     that persona, hand it the task description + any upstream context, call
 *     the model.
 *   - A Crew with process="sequential" is a *pipeline*: each task's output
 *     becomes the next task's context. That's the whole orchestration — a fold
 *     over tasks that accumulates context.
 *
 * The math (composition / a fold, not calculus):
 *
 *   Given tasks t_1..t_n whose agents are a_1..a_n, sequential kickoff computes:
 *
 *       context_0 = ""                       (no prior work yet)
 *       out_i = a_i.execute(t_i, out_{i-1})
 *       return out_n                         (the last task's output)
 *
 *   A role-grounded prompt is just:
 *
 *       System: You are {role}. Your goal is {goal}. Backstory: {backstory}.
 *       User:   {task.description}
 *               [Context from previous work: {context}]   (only if context != "")
 *               Expected output: {task.expectedOutput}
 *
 * The pieces we reimplement (and the real crewai equivalent):
 *
 *   ours                            real crewai
 *   ----------------------------    ------------------------------------------
 *   Agent(role, goal, backstory)    crewai.Agent(role=, goal=, backstory=, llm=)
 *   Agent.execute(task, context)    (crewai builds this prompt internally)
 *   Task(description, agent, ...)   crewai.Task(description=, agent=, expected_output=)
 *   Crew(agents, tasks, process)    crewai.Crew(agents=, tasks=, process=sequential)
 *   Crew.kickoff()                  crew.kickoff()
 *
 * OFFLINE: each Agent gets a `chatFn: (msgs) => string`. With --stub a
 * deterministic fake model echoes back which role/task it saw, so we can assert
 * the researcher's output really reached the writer.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/03-crew.ts --stub
 *   pnpm tsx modules/06c-agent-frameworks/ts/03-crew.ts
 */

import { getProvider } from "@learn-ai/llm-core";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

// ---------------------------------------------------------------------------
// Agent — a role-grounded persona bound to a model
// ---------------------------------------------------------------------------

class Agent {
  constructor(
    public role: string,
    public goal: string,
    public backstory: string,
    public chatFn: ChatFn,
  ) {}

  /**
   * Ground the model in this agent's persona and run the task.
   *
   * Build a two-message chat:
   *   - system: describes WHO the agent is (role/goal/backstory).
   *   - user:   the task description, upstream context (if any), and the
   *             expected-output hint.
   * Then call this.chatFn(messages) and return the reply.
   *
   * TODO: implement.
   *   1. const system =
   *        `You are ${this.role}. Your goal is ${this.goal}. ` +
   *        `Backstory: ${this.backstory}`;
   *   2. let user = task.description;
   *      if (context) user += `\n\nContext from previous work:\n${context}`;
   *      user += `\n\nExpected output: ${task.expectedOutput}`;
   *   3. const messages = [
   *        { role: "system", content: system },
   *        { role: "user", content: user },
   *      ];
   *   4. return this.chatFn(messages);
   */
  execute(_task: Task, _context = ""): string {
    // TODO: implement Agent.execute (assemble a role-grounded prompt)
    throw new Error("TODO: implement Agent.execute()");
  }
}

// ---------------------------------------------------------------------------
// Task
// ---------------------------------------------------------------------------

class Task {
  constructor(
    public description: string,
    public agent: Agent,
    public expectedOutput = "A concise, well-structured result.",
  ) {}
}

// ---------------------------------------------------------------------------
// Crew — sequential orchestration
// ---------------------------------------------------------------------------

interface TranscriptStep {
  agent: string;
  task: string;
  contextIn: string;
  output: string;
}

class Crew {
  transcript: TranscriptStep[] = [];

  constructor(
    public agents: Agent[],
    public tasks: Task[],
    public process: string = "sequential",
  ) {}

  /**
   * Run the tasks in order, threading each output into the next context.
   * Only process === "sequential" is supported here.
   *
   * TODO: implement.
   *   1. let context = "";  // no prior work before the first task
   *   2. for (const task of this.tasks):
   *        a. const output = task.agent.execute(task, context);
   *        b. this.transcript.push({
   *             agent: task.agent.role,
   *             task: task.description,
   *             contextIn: context,
   *             output,
   *           });
   *        c. context = output;  // thread into the NEXT task
   *   3. return the LAST task's output (or "" if there are no tasks).
   */
  kickoff(): string {
    // TODO: implement Crew.kickoff (sequential threading of outputs)
    throw new Error("TODO: implement Crew.kickoff()");
  }
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/**
 * Deterministic fake: echo the role it was told to be + whether it saw upstream
 * context, so we can prove the researcher's output reached the writer's prompt.
 */
function makeStubChatFn(): ChatFn {
  return (messages: Msg[]) => {
    const system = messages[0].content;
    const user = messages[messages.length - 1].content;
    const role = system.split(".")[0].replace("You are ", "").trim();
    const sawContext = user.includes("Context from previous work");
    const tag = sawContext ? "with-context" : "no-context";
    return `[${role} output | ${tag}]`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt Agent.execute to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 3: CrewAI crew — ${mode} ===\n`);

  const researcher = new Agent(
    "Senior Researcher",
    "find accurate, relevant facts on a topic",
    "You dig up primary sources and never invent details.",
    chatFn,
  );
  const writer = new Agent(
    "Content Writer",
    "turn research notes into a crisp paragraph",
    "You write clearly for a general audience.",
    chatFn,
  );

  const researchTask = new Task(
    "Research the benefits of retrieval-augmented generation (RAG).",
    researcher,
    "3-5 bullet points of key facts.",
  );
  const writeTask = new Task(
    "Write a short paragraph explaining RAG for beginners.",
    writer,
    "One tight paragraph, no jargon.",
  );

  const crew = new Crew([researcher, writer], [researchTask, writeTask]);
  const final = crew.kickoff();

  console.log("Kickoff trace:");
  crew.transcript.forEach((step, i) => {
    console.log(`  [${i + 1}] ${step.agent}`);
    console.log(`      task:      ${step.task}`);
    console.log(`      contextIn: ${JSON.stringify(step.contextIn)}`);
    console.log(`      output:    ${JSON.stringify(step.output)}`);
  });

  console.log(`\nFinal result: ${JSON.stringify(final)}`);

  if (useStub) {
    const last = crew.transcript[crew.transcript.length - 1];
    if (final !== last.output) throw new Error("final != last task output");
    if (final !== "[Content Writer output | with-context]")
      throw new Error(`unexpected final: ${JSON.stringify(final)}`);
    if (crew.transcript[0].agent !== "Senior Researcher")
      throw new Error("first task should be the researcher");
    if (crew.transcript[0].contextIn !== "")
      throw new Error("first task should have empty context");
    if (crew.transcript[1].agent !== "Content Writer")
      throw new Error("second task should be the writer");
    if (crew.transcript[1].contextIn !== crew.transcript[0].output)
      throw new Error("researcher output did not thread into writer's context");
    console.log(
      "\n[ok] researcher output threaded into writer context; task order enforced",
    );
  }

  console.log(
    "\nReal crewai: Crew(agents=[...], tasks=[...], process=Process.sequential)" +
      ".kickoff() runs the same pipeline.",
  );
}

main();
