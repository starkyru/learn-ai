"""
Task 3 🟡 — Reimplement CrewAI: role-grounded Agents, Tasks, a sequential Crew.

What you'll learn:
  - CrewAI's core idea: an Agent is a *persona* (role + goal + backstory) bound
    to a model. Executing a Task = build a prompt that grounds the model in that
    persona, hand it the task description + any upstream context, call the model.
  - A Crew with process="sequential" is a *pipeline*: each task's output becomes
    the next task's context. That's the whole orchestration — a fold over tasks
    that accumulates context.

The math (again: composition / a fold, not calculus):

  Given tasks t_1..t_n whose agents are a_1..a_n, sequential kickoff computes:

      context_0 = ""                      (no prior work yet)
      out_1 = a_1.execute(t_1, context_0)
      out_2 = a_2.execute(t_2, context_1)   where context_1 = out_1
      ...
      out_i = a_i.execute(t_i, out_{i-1})
      return out_n                         (the last task's output)

  Each agent grounds the model with its role. A role-grounded prompt is just:

      System: You are {role}. Your goal is {goal}. Backstory: {backstory}.
      User:   {task.description}
              [Context from previous work: {context}]   (only if context != "")
              Expected output: {task.expected_output}

The pieces we reimplement (and the real crewai equivalent):

  ours                            real crewai
  ----------------------------    ------------------------------------------
  Agent(role, goal, backstory)    crewai.Agent(role=, goal=, backstory=, llm=)
  Agent.execute(task, context)    (crewai builds this prompt internally)
  Task(description, agent, ...)   crewai.Task(description=, agent=, expected_output=)
  Crew(agents, tasks, process)    crewai.Crew(agents=, tasks=, process=Process.sequential)
  Crew.kickoff()                  crew.kickoff()

OFFLINE: each Agent gets a `chat_fn: Callable[[list[dict]], str]`. With --stub a
deterministic fake model echoes back which role/task it saw, so we can assert
the researcher's output really reached the writer.

How to run:
  uv run python modules/06c-agent-frameworks/py/03_crew.py --stub
  uv run python modules/06c-agent-frameworks/py/03_crew.py
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field

ChatFn = Callable[[list[dict[str, str]]], str]


# ---------------------------------------------------------------------------
# Agent — a role-grounded persona bound to a model
# ---------------------------------------------------------------------------


@dataclass
class Agent:
    role: str
    goal: str
    backstory: str
    chat_fn: ChatFn

    def execute(self, task: Task, context: str = "") -> str:
        """Ground the model in this agent's persona and run the task.

        Build a two-message chat:
          - system: describes WHO the agent is (role/goal/backstory).
          - user:   the task description, upstream context (if any), and the
                    expected-output hint.
        Then call self.chat_fn(messages) and return the reply.

        TODO: implement.
          - Build the system message from this agent's persona — its role, goal,
            and backstory — so the model knows WHO it is.
          - Build the user message: start from task.description; only when
            `context` is non-empty, append a labelled "Context from previous
            work" section carrying it; then append the expected-output hint.
            (The stub keys off the exact phrase "Context from previous work" to
            detect threading, so keep that label.)
          - Assemble a `list[dict[str, str]]`: a "system" message then a "user"
            message, each a {"role", "content"} dict.
          - Call self.chat_fn(messages) and return its reply.
        """
        # TODO: implement Agent.execute (assemble a role-grounded prompt)
        raise NotImplementedError("TODO: implement Agent.execute()")


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


@dataclass
class Task:
    description: str
    agent: Agent
    expected_output: str = "A concise, well-structured result."


# ---------------------------------------------------------------------------
# Crew — sequential orchestration
# ---------------------------------------------------------------------------


@dataclass
class Crew:
    agents: list[Agent]
    tasks: list[Task]
    process: str = "sequential"
    # Filled during kickoff so you can inspect what each task received/produced.
    transcript: list[dict[str, str]] = field(default_factory=list)

    def kickoff(self) -> str:
        """Run the tasks in order, threading each output into the next context.

        Only `process == "sequential"` is supported here (that's the common one).

        TODO: implement.
          - Start with an empty context (nothing done before the first task).
          - Walk self.tasks in order. For each task: run its agent with the
            current context (task.agent.execute(task, context)), then thread that
            output into the NEXT task by making it the new context.
          - Record one transcript entry per task with keys "agent"
            (task.agent.role), "task" (task.description), "context_in" (the
            context that went IN, before this task ran), and "output" — the tests
            read these to prove threading and ordering.
          - Return the last task's output (return "" if there are no tasks).
        """
        # TODO: implement Crew.kickoff (sequential threading of outputs)
        raise NotImplementedError("TODO: implement Crew.kickoff()")


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: echo the role it was told to be + whether it saw
    upstream context. This lets us prove the researcher's output reached the
    writer's prompt.
    """

    def chat_fn(messages: list[dict[str, str]]) -> str:
        system = messages[0]["content"]
        user = messages[-1]["content"]
        # Pull the role out of "You are <role>. Your goal ..." for a tidy echo.
        role = system.split(".")[0].replace("You are ", "").strip()
        saw_context = "Context from previous work" in user
        tag = "with-context" if saw_context else "no-context"
        return f"[{role} output | {tag}]"

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="CrewAI reimplementation (Task 3).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 3: CrewAI crew — {mode} ===\n")

    # A 2-agent crew: researcher -> writer.
    researcher = Agent(
        role="Senior Researcher",
        goal="find accurate, relevant facts on a topic",
        backstory="You dig up primary sources and never invent details.",
        chat_fn=chat_fn,
    )
    writer = Agent(
        role="Content Writer",
        goal="turn research notes into a crisp paragraph",
        backstory="You write clearly for a general audience.",
        chat_fn=chat_fn,
    )

    research_task = Task(
        description="Research the benefits of retrieval-augmented generation (RAG).",
        agent=researcher,
        expected_output="3-5 bullet points of key facts.",
    )
    write_task = Task(
        description="Write a short paragraph explaining RAG for beginners.",
        agent=writer,
        expected_output="One tight paragraph, no jargon.",
    )

    crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task])
    final = crew.kickoff()

    print("Kickoff trace:")
    for i, step in enumerate(crew.transcript, 1):
        print(f"  [{i}] {step['agent']}")
        print(f"      task:       {step['task']}")
        print(f"      context_in: {step['context_in']!r}")
        print(f"      output:     {step['output']!r}")

    print(f"\nFinal result: {final!r}")

    if args.stub:
        # 1) Final is the writer's output (last task).
        assert final == crew.transcript[-1]["output"], "final != last task output"
        assert final == "[Content Writer output | with-context]", f"unexpected final: {final!r}"
        # 2) Task order enforced: researcher ran first (no context), writer second.
        assert crew.transcript[0]["agent"] == "Senior Researcher"
        assert crew.transcript[0]["context_in"] == "", "first task should have empty context"
        assert crew.transcript[1]["agent"] == "Content Writer"
        # 3) The writer's context_in is EXACTLY the researcher's output — threading works.
        assert crew.transcript[1]["context_in"] == crew.transcript[0]["output"], (
            "researcher output did not thread into writer's context"
        )
        print("\n[ok] researcher output threaded into writer context; task order enforced")

    print(
        "\nReal crewai: Crew(agents=[...], tasks=[...], process=Process.sequential)"
        ".kickoff() runs the same pipeline."
    )


if __name__ == "__main__":
    main()
