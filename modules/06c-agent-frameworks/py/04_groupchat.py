"""
Task 4 🟡 — Reimplement AutoGen: ConversableAgents in a round-robin GroupChat.

What you'll learn:
  - AutoGen's core idea: several ConversableAgents share ONE transcript. A
    manager picks the next speaker, asks it to generate a reply *given the whole
    history so far*, appends that reply, and repeats.
  - The loop is bounded two ways: a hard cap (max_round) AND an early stop when
    any reply contains a termination phrase ("TERMINATE"). Real multi-agent
    systems need both — a budget and a done-signal — or they never stop.
  - "Round-robin" speaker selection is just rotating an index modulo the number
    of agents.

The math (a bounded loop + modular rotation):

  Let agents = [g_0, ..., g_{m-1}] and history H (a list of messages). Start H
  with the initial user message. For round r = 0, 1, 2, ...:

      speaker = agents[r mod m]           # round-robin rotation
      reply   = speaker.generate_reply(H) # depends on the whole transcript
      append {speaker.name, reply} to H
      if "TERMINATE" in reply: stop       # done-signal
      if (r + 1) >= max_round: stop        # budget

  So the transcript length after the loop is:
      1 (initial) + min(rounds_until_terminate, max_round) replies.

The pieces we reimplement (and the real autogen equivalent):

  ours                              real autogen
  ------------------------------    ----------------------------------------
  ConversableAgent(name, sys, fn)   autogen.ConversableAgent(name=, system_message=)
    .generate_reply(history)          (agent replies given the message list)
  GroupChat(agents, max_round)      autogen.GroupChat(agents=, max_round=)
  GroupChatManager.run(msg)         autogen.GroupChatManager(...).initiate_chat / run

OFFLINE: each agent gets a `chat_fn: Callable[[list[dict]], str]`. With --stub,
agents are scripted so one of them emits TERMINATE, proving early stop and
correct speaker labelling — no network.

How to run:
  uv run python modules/06c-agent-frameworks/py/04_groupchat.py --stub
  uv run python modules/06c-agent-frameworks/py/04_groupchat.py
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field

ChatFn = Callable[[list[dict[str, str]]], str]
TERMINATION_PHRASE = "TERMINATE"


# ---------------------------------------------------------------------------
# ConversableAgent
# ---------------------------------------------------------------------------


@dataclass
class ConversableAgent:
    name: str
    system_message: str
    chat_fn: ChatFn

    def generate_reply(self, history: list[dict[str, str]]) -> str:
        """Produce this agent's next reply given the shared transcript.

        Prepend this agent's system message, then pass the whole transcript as
        the running conversation, then ask the model for the next turn.

        The transcript entries look like {"name": <speaker>, "content": <text>}.
        We convert them to chat messages the model understands: label each with
        its speaker so the agent can see who said what.

        TODO: implement.
          - Build a `list[dict[str, str]]` starting with a "system" message
            carrying this agent's self.system_message.
          - Replay the shared transcript: for each history entry, append a "user"
            message whose content prefixes the speaker name onto the text (e.g.
            "<name>: <content>") so the model sees who said what.
          - Call self.chat_fn(messages) and return the reply with surrounding
            whitespace stripped.
        """
        # TODO: implement generate_reply (build messages from shared history)
        raise NotImplementedError("TODO: implement ConversableAgent.generate_reply()")


# ---------------------------------------------------------------------------
# GroupChat + Manager
# ---------------------------------------------------------------------------


@dataclass
class GroupChat:
    agents: list[ConversableAgent]
    max_round: int = 6
    # The shared transcript: list of {"name", "content"}.
    messages: list[dict[str, str]] = field(default_factory=list)


class GroupChatManager:
    """Drives the group chat: round-robin speakers, shared transcript, stop rules."""

    def __init__(self, groupchat: GroupChat) -> None:
        self.groupchat = groupchat

    def run(self, initial_message: str, initiator: str = "user") -> list[dict[str, str]]:
        """Run the round-robin loop and return the full transcript.

        The transcript starts with the initial message from `initiator`. Then we
        rotate through agents, each replying to the whole history, until either
        an agent emits TERMINATION_PHRASE or we hit max_round replies.

        TODO: implement the manager loop.
          - Seed the shared transcript (gc.messages) with the initial message as
            a {"name", "content"} entry spoken by `initiator`.
          - Loop at most max_round times. Each round, pick the speaker by
            round-robin: rotate an index modulo the number of agents (r % m).
          - Ask that speaker to generate_reply over the whole transcript, then
            append its reply as a {"name", "content"} entry.
          - Stop early (break) the moment a reply contains TERMINATION_PHRASE.
          - Return the full transcript (gc.messages).
        """
        # TODO: implement GroupChatManager.run (round-robin loop + stop rules)
        raise NotImplementedError("TODO: implement GroupChatManager.run()")


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn_for(name: str, script: list[str]) -> ChatFn:
    """Deterministic per-agent stub: return the next scripted line each call.

    Each agent gets its OWN scripted list so we can force a specific speaker to
    emit TERMINATE at a known round. The `name` is only for readability.
    """
    state = {"i": 0}

    def chat_fn(messages: list[dict[str, str]]) -> str:
        line = script[min(state["i"], len(script) - 1)]
        state["i"] += 1
        return line

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
    ap = argparse.ArgumentParser(description="AutoGen group chat reimplementation (Task 4).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    print(
        f"\n=== Task 4: AutoGen group chat — "
        f"{'STUB (offline)' if args.stub else 'REAL (get_provider)'} ===\n"
    )

    if args.stub:
        # Scripted so the SECOND agent (critic) emits TERMINATE on its first
        # turn — that is round r=1, i.e. after exactly 2 agent replies.
        planner_fn = make_stub_chat_fn_for("planner", ["Here is a plan: step 1, step 2."])
        critic_fn = make_stub_chat_fn_for("critic", ["Looks good. TERMINATE"])
        agents = [
            ConversableAgent("planner", "You plan tasks.", planner_fn),
            ConversableAgent("critic", "You review plans and end when satisfied.", critic_fn),
        ]
    else:
        chat_fn = make_real_chat_fn()
        agents = [
            ConversableAgent(
                "planner",
                "You are a planner. Propose a short plan. Keep replies to 1-2 sentences.",
                chat_fn,
            ),
            ConversableAgent(
                "critic",
                "You are a critic. If the plan is good, reply with 'TERMINATE'. "
                "Otherwise suggest one improvement in 1-2 sentences.",
                chat_fn,
            ),
        ]

    groupchat = GroupChat(agents=agents, max_round=6)
    manager = GroupChatManager(groupchat)

    transcript = manager.run("Plan a 3-step launch for a new podcast.")

    print("Transcript:")
    for i, msg in enumerate(transcript):
        print(f"  [{i}] {msg['name']}: {msg['content']}")

    if args.stub:
        # 1) Ordered with correct speaker labels: user, planner, critic.
        names = [m["name"] for m in transcript]
        assert names == ["user", "planner", "critic"], f"bad order/labels: {names}"
        # 2) Early termination: critic said TERMINATE on round 1, so the loop
        #    stopped after 2 replies (transcript = 1 initial + 2 replies = 3).
        assert TERMINATION_PHRASE in transcript[-1]["content"], "did not terminate on phrase"
        assert len(transcript) == 3, f"expected 3 messages (early stop), got {len(transcript)}"
        # 3) At most max_round replies (never exceeded the budget).
        assert (len(transcript) - 1) <= groupchat.max_round, "exceeded max_round budget"
        print(
            "\n[ok] round-robin order + labels correct; terminated early on TERMINATE; "
            "within max_round budget"
        )

    print(
        "\nReal autogen: ConversableAgent + GroupChat + GroupChatManager drive "
        "the same speaker-rotation loop with is_termination_msg / max_round."
    )


if __name__ == "__main__":
    main()
