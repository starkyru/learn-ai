/**
 * Task 4 🟡 — Reimplement AutoGen: ConversableAgents in a round-robin GroupChat.
 *
 * What you'll learn:
 *   - AutoGen's core idea: several ConversableAgents share ONE transcript. A
 *     manager picks the next speaker, asks it to generate a reply *given the
 *     whole history so far*, appends that reply, and repeats.
 *   - The loop is bounded two ways: a hard cap (maxRound) AND an early stop when
 *     any reply contains a termination phrase ("TERMINATE"). Real multi-agent
 *     systems need both — a budget and a done-signal — or they never stop.
 *   - "Round-robin" speaker selection is just rotating an index modulo the
 *     number of agents.
 *
 * The math (a bounded loop + modular rotation):
 *
 *   Let agents = [g_0, ..., g_{m-1}] and history H (a list of messages). Start H
 *   with the initial user message. For round r = 0, 1, 2, ...:
 *
 *       speaker = agents[r mod m]           // round-robin rotation
 *       reply   = speaker.generateReply(H)  // depends on the whole transcript
 *       append {speaker.name, reply} to H
 *       if reply includes "TERMINATE": stop // done-signal
 *       if (r + 1) >= maxRound: stop         // budget
 *
 *   Transcript length after the loop:
 *       1 (initial) + min(roundsUntilTerminate, maxRound) replies.
 *
 * The pieces we reimplement (and the real autogen equivalent):
 *
 *   ours                              real autogen
 *   ------------------------------    ----------------------------------------
 *   ConversableAgent(name, sys, fn)   autogen ConversableAgent(name, system_message)
 *     .generateReply(history)           (agent replies given the message list)
 *   GroupChat(agents, maxRound)       autogen GroupChat(agents, max_round)
 *   GroupChatManager.run(msg)         autogen GroupChatManager(...).run
 *
 * OFFLINE: each agent gets a `chatFn: (msgs) => string`. With --stub, agents are
 * scripted so one emits TERMINATE, proving early stop + correct labelling.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/04-groupchat.ts --stub
 *   pnpm tsx modules/06c-agent-frameworks/ts/04-groupchat.ts
 */

import { getProvider } from "@learn-ai/llm-core";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

const TERMINATION_PHRASE = "TERMINATE";

// A transcript entry names its speaker.
interface TranscriptMsg {
  name: string;
  content: string;
}

// ---------------------------------------------------------------------------
// ConversableAgent
// ---------------------------------------------------------------------------

class ConversableAgent {
  constructor(
    public name: string,
    public systemMessage: string,
    public chatFn: ChatFn,
  ) {}

  /**
   * Produce this agent's next reply given the shared transcript.
   *
   * Prepend this agent's system message, then pass the whole transcript as the
   * running conversation, labelling each entry with its speaker so the agent
   * can see who said what.
   *
   * TODO: implement.
   *   1. const messages: Msg[] = [{ role: "system", content: this.systemMessage }];
   *   2. for (const entry of history) messages.push({
   *          role: "user",
   *          content: `${entry.name}: ${entry.content}`,
   *      });
   *   3. return this.chatFn(messages).trim();
   */
  generateReply(_history: TranscriptMsg[]): string {
    // TODO: implement generateReply (build messages from shared history)
    throw new Error("TODO: implement ConversableAgent.generateReply()");
  }
}

// ---------------------------------------------------------------------------
// GroupChat + Manager
// ---------------------------------------------------------------------------

class GroupChat {
  messages: TranscriptMsg[] = []; // the shared transcript

  constructor(
    public agents: ConversableAgent[],
    public maxRound = 6,
  ) {}
}

class GroupChatManager {
  constructor(private groupchat: GroupChat) {}

  /**
   * Run the round-robin loop and return the full transcript.
   *
   * The transcript starts with the initial message from `initiator`. Then we
   * rotate through agents, each replying to the whole history, until either an
   * agent emits TERMINATION_PHRASE or we hit maxRound replies.
   *
   * TODO: implement the manager loop.
   *   1. const gc = this.groupchat;
   *      gc.messages.push({ name: initiator, content: initialMessage });
   *   2. const m = gc.agents.length;
   *   3. for (let r = 0; r < gc.maxRound; r++) {
   *        const speaker = gc.agents[r % m];              // round-robin rotation
   *        const reply = speaker.generateReply(gc.messages);
   *        gc.messages.push({ name: speaker.name, content: reply });
   *        if (reply.includes(TERMINATION_PHRASE)) break; // early stop
   *      }
   *   4. return gc.messages;
   */
  run(_initialMessage: string, _initiator = "user"): TranscriptMsg[] {
    // TODO: implement GroupChatManager.run (round-robin loop + stop rules)
    throw new Error("TODO: implement GroupChatManager.run()");
  }
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/**
 * Deterministic per-agent stub: return the next scripted line each call. Each
 * agent gets its OWN script so we can force a specific speaker to emit TERMINATE
 * at a known round.
 */
function makeStubChatFnFor(_name: string, script: string[]): ChatFn {
  let i = 0;
  return () => {
    const line = script[Math.min(i, script.length - 1)];
    i += 1;
    return line;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt generateReply to `await provider.chat(...)`.",
    );
  };
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

function main(): void {
  const useStub = process.argv.includes("--stub");
  console.log(
    `\n=== Task 4: AutoGen group chat — ${useStub ? "STUB (offline)" : "REAL (getProvider)"} ===\n`,
  );

  let agents: ConversableAgent[];
  if (useStub) {
    // Scripted so the SECOND agent (critic) emits TERMINATE on its first turn
    // — round r=1, i.e. after exactly 2 agent replies.
    const plannerFn = makeStubChatFnFor("planner", ["Here is a plan: step 1, step 2."]);
    const criticFn = makeStubChatFnFor("critic", ["Looks good. TERMINATE"]);
    agents = [
      new ConversableAgent("planner", "You plan tasks.", plannerFn),
      new ConversableAgent(
        "critic",
        "You review plans and end when satisfied.",
        criticFn,
      ),
    ];
  } else {
    const chatFn = makeRealChatFn();
    agents = [
      new ConversableAgent(
        "planner",
        "You are a planner. Propose a short plan. Keep replies to 1-2 sentences.",
        chatFn,
      ),
      new ConversableAgent(
        "critic",
        "You are a critic. If the plan is good, reply with 'TERMINATE'. " +
          "Otherwise suggest one improvement in 1-2 sentences.",
        chatFn,
      ),
    ];
  }

  const groupchat = new GroupChat(agents, 6);
  const manager = new GroupChatManager(groupchat);

  const transcript = manager.run("Plan a 3-step launch for a new podcast.");

  console.log("Transcript:");
  transcript.forEach((msg, i) => {
    console.log(`  [${i}] ${msg.name}: ${msg.content}`);
  });

  if (useStub) {
    const names = transcript.map((m) => m.name);
    if (JSON.stringify(names) !== JSON.stringify(["user", "planner", "critic"]))
      throw new Error(`bad order/labels: ${JSON.stringify(names)}`);
    if (!transcript[transcript.length - 1].content.includes(TERMINATION_PHRASE))
      throw new Error("did not terminate on phrase");
    if (transcript.length !== 3)
      throw new Error(`expected 3 messages (early stop), got ${transcript.length}`);
    if (transcript.length - 1 > groupchat.maxRound)
      throw new Error("exceeded maxRound budget");
    console.log(
      "\n[ok] round-robin order + labels correct; terminated early on TERMINATE; " +
        "within maxRound budget",
    );
  }

  console.log(
    "\nReal autogen: ConversableAgent + GroupChat + GroupChatManager drive " +
      "the same speaker-rotation loop with is_termination_msg / max_round.",
  );
}

main();
