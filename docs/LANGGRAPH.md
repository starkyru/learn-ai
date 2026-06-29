# LangGraph — reference & interview cheat-sheet

Companion to **`modules/06b-langgraph/`** (the hands-on lesson) and module 06
Task 4 (first contact). This file is the "I need the answer now" reference:
concepts, an API cheat-sheet for Python **and** TypeScript, the patterns
interviewers probe, and the gotchas that bite in production.

> Versions this targets: **Python `langgraph` 1.x** (`langchain-core` 1.x),
> **TypeScript `@langchain/langgraph` 0.2.x** (`@langchain/core` 0.3.x). The
> concepts are stable; a few import paths differ across versions — noted inline.

---

## 1. What LangGraph is (one sentence each)

- **LangGraph** = a typed, checkpointed, streamable **state machine runtime** for
  LLM workflows. You define nodes + edges over a shared state; it handles
  persistence, resumption, streaming, and human-in-the-loop.
- **LangChain** = the model/tool/prompt layer (`ChatModel`, `@tool`, retrievers).
  LangGraph _uses_ it for the model interface but is a separate engine.
- **LangSmith** = observability/eval SaaS (tracing). **LangGraph Studio** = visual
  debugger. **LangGraph Platform** = hosted deployment (graph → API + managed
  checkpointer + queue).

**When to reach for it:** you need memory across turns, resumption after a crash,
human approval gates, token+step streaming, branching/replay, or multi-agent
handoff. **When not to:** a single linear prompt → just call the model.

---

## 2. Core vocabulary

| Term                 | Meaning                                                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| **State**            | a typed dict that flows through the graph. The single source of truth.                                                  |
| **Channel**          | one field of the state. Each has a **reducer**.                                                                         |
| **Reducer**          | how a node's update merges into a channel. Default = overwrite; `add_messages` = append+dedupe; custom = sum/union/etc. |
| **Node**             | a function `(state) -> partial update`. Pure-ish; returns only changed keys.                                            |
| **Edge**             | fixed transition `A -> B`.                                                                                              |
| **Conditional edge** | a function `(state) -> next_node_name`; this is your control flow.                                                      |
| **`StateGraph`**     | the builder you add nodes/edges to.                                                                                     |
| **`compile()`**      | turns the builder into a runnable app (optionally with a checkpointer).                                                 |
| **Super-step**       | one "tick": all nodes scheduled this round run, then state is checkpointed.                                             |
| **Checkpointer**     | saves state per super-step; enables memory, resume, interrupts, time travel.                                            |
| **Thread**           | one conversation/run, keyed by `thread_id` in `config`.                                                                 |
| **`Command`**        | a node return that both updates state and routes (`goto`).                                                              |
| **`interrupt()`**    | pause inside a node, surface a payload, resume later.                                                                   |
| **Subgraph**         | a compiled graph used as a node in a parent graph.                                                                      |

---

## 3. API cheat-sheet (Python ‖ TypeScript)

### Define state

```python
# Python
from typing import Annotated, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
import operator

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]  # append + dedupe by id
    count: Annotated[int, operator.add]                  # SUM
    label: str                                           # overwrite (default)

# Prebuilt shortcut for the common case:
from langgraph.graph import MessagesState   # == {messages: add_messages}
```

```ts
// TypeScript
import { Annotation, MessagesAnnotation } from "@langchain/langgraph";
import { BaseMessage } from "@langchain/core/messages";

const State = Annotation.Root({
  messages: Annotation<BaseMessage[]>({
    reducer: (a, b) => a.concat(b),
    default: () => [],
  }),
  count: Annotation<number>({ reducer: (a, b) => a + b, default: () => 0 }),
  label: Annotation<string>(), // no reducer => overwrite
});
// Prebuilt shortcut: MessagesAnnotation  (just { messages })
```

### Build, compile, run

```python
from langgraph.graph import StateGraph, START, END
g = StateGraph(State)
g.add_node("agent", agent_node)
g.add_node("tools", tools_node)
g.add_edge(START, "agent")
g.add_conditional_edges("agent", route)   # route(state) -> "tools" | END
g.add_edge("tools", "agent")
app = g.compile()                          # add checkpointer=... for persistence
app.invoke({"messages": [...]}, {"configurable": {"thread_id": "t1"}})
```

```ts
import { StateGraph, START, END } from "@langchain/langgraph";
const app = new StateGraph(State)
  .addNode("agent", agentNode)
  .addNode("tools", toolsNode)
  .addEdge(START, "agent")
  .addConditionalEdges("agent", route)
  .addEdge("tools", "agent")
  .compile();
await app.invoke({ messages: [...] }, { configurable: { thread_id: "t1" } });
```

### Prebuilt ReAct (skip the boilerplate)

```python
from langgraph.prebuilt import create_react_agent, ToolNode, tools_condition
app = create_react_agent(model, tools)          # whole agent in one line
# or hand-wire with:  ToolNode(tools)  +  add_conditional_edges("agent", tools_condition)
```

```ts
import {
  createReactAgent,
  ToolNode,
  toolsCondition,
} from "@langchain/langgraph/prebuilt";
const app = createReactAgent({ llm: model, tools });
```

### Persistence

```python
from langgraph.checkpoint.memory import InMemorySaver        # alias: MemorySaver
app = g.compile(checkpointer=InMemorySaver())
# persistent: from langgraph.checkpoint.sqlite import SqliteSaver
#   with SqliteSaver.from_conn_string("cp.sqlite") as cp: app = g.compile(checkpointer=cp)
```

```ts
import { MemorySaver } from "@langchain/langgraph";
const app = g.compile({ checkpointer: new MemorySaver() });
// persistent: import { SqliteSaver } from "@langchain/langgraph-checkpoint-sqlite";
```

### Human-in-the-loop

```python
from langgraph.types import interrupt, Command
def node(state):
    decision = interrupt({"approve?": pending})   # pauses here
    ...
app.invoke(Command(resume="approve"), config)     # resumes from the interrupt
# static form: g.compile(checkpointer=cp, interrupt_before=["tools"])
#   then app.invoke(None, config) to continue
```

```ts
import { interrupt, Command } from "@langchain/langgraph";
const decision = interrupt({ approve: pending });
await app.invoke(new Command({ resume: "approve" }), config);
// static: g.compile({ checkpointer, interruptBefore: ["tools"] });
```

### Streaming

```python
for chunk in app.stream(inputs, config, stream_mode="updates"):   # node deltas
for snap  in app.stream(inputs, config, stream_mode="values"):    # full state
for tok, meta in app.stream(inputs, config, stream_mode="messages"):  # LLM tokens
# multiple: stream_mode=["updates", "messages"] -> yields (mode, payload)
```

```ts
for await (const chunk of await app.stream(inputs, { streamMode: "updates" })) {
}
for await (const [tok] of await app.stream(inputs, { streamMode: "messages" })) {
}
```

### Subgraphs

```python
sub = sub_builder.compile()
parent.add_node("research", sub)                  # a compiled graph IS a node
for ns, chunk in app.stream(inputs, subgraphs=True, stream_mode="updates"): ...
```

```ts
const sub = subBuilder.compile();
parent.addNode("research", sub);
for await (const [ns, chunk] of await app.stream(inputs, {
  subgraphs: true,
  streamMode: "updates",
})) {
}
```

### Multi-agent handoff

```python
from langgraph.types import Command
def supervisor(state) -> Command:
    return Command(goto="researcher", update={"next": "researcher"})
# workers return Command(goto="supervisor", update={...}) to hand back
```

```ts
import { Command } from "@langchain/langgraph";
return new Command({ goto: "researcher", update: { next: "researcher" } });
// In TS, declare reachable targets: .addNode("supervisor", fn, { ends: ["researcher", END] })
```

### Time travel

```python
snap = app.get_state(config)                      # current StateSnapshot
for s in app.get_state_history(config): ...       # all checkpoints, newest first
app.invoke(None, old_snap.config)                 # fork/resume from an old checkpoint
app.update_state(config, {"messages": [...]})     # edit -> new checkpoint, then continue
```

```ts
const snap = await app.getState(config);
for await (const s of app.getStateHistory(config)) {}
await app.updateState(config, { messages: [...] });
```

---

## 4. Patterns interviewers ask you to draw

**ReAct agent** (the default; `create_react_agent` builds it):

```
START → agent → (tool_calls? ) → tools → agent → … → END
```

**Human approval gate:** `agent → [interrupt before tools] → human approves → tools`.
The interrupt + checkpointer pair is the whole answer.

**Supervisor multi-agent:** one `supervisor` node `Command(goto=worker)`; each
worker `Command(goto=supervisor)`; loop until `goto=END`. Variants: **swarm**
(workers hand off directly to each other), **hierarchical** (supervisors of
supervisors via subgraphs).

**Map-reduce / fan-out:** the `Send` API dispatches a node over a dynamic list:
`return [Send("worker", {"item": x}) for x in items]`, results gathered by the
channel reducer. Use for "summarise each of N docs then combine."

**Reflection loop:** `generate → critique → (good? END : generate)` — a
conditional edge back to `generate` until a judge node approves.

---

## 5. Gotchas (the stuff that actually breaks)

- **No checkpointer → no memory / interrupts / time travel.** Compile with one or
  none of those features work. Multi-turn memory needs the _same_ `thread_id`.
- **Reducer mismatch.** If a list channel keeps overwriting, you forgot its
  append reducer. If messages duplicate, you concatenated _and_ used `add_messages`
  (it already appends — return only the _new_ messages from a node).
- **`interrupt()` re-runs the node from the top on resume.** Code before the
  `interrupt` call runs again. Keep pre-interrupt work idempotent (or put it after).
- **`Command(goto=...)` needs the target to be reachable.** In Python it usually
  just works; in TS declare `{ ends: [...] }` on the node, or the compiler can't
  see the dynamic edge.
- **Tool-calling requires a model that supports it.** `create_react_agent` /
  `bind_tools` need an OpenAI/Anthropic/compatible model (or Ollama with a
  tool-capable model like `llama3.2`). A plain text model silently won't call tools.
- **`MemorySaver` is in-process only.** It vanishes on restart — use
  `SqliteSaver`/`PostgresSaver` for durability.
- **Import drift across versions.** `MemorySaver`↔`InMemorySaver`,
  `langgraph.prebuilt` location, and `Command`/`interrupt` living in
  `langgraph.types` (Python) vs the package root (TS). Check the installed version
  if an import 404s.

---

## 6. 60-second interview answers

- **"LangGraph vs LangChain?"** LangChain is the model/tool/prompt layer; LangGraph
  is the stateful graph _runtime_ on top — it owns persistence, streaming,
  human-in-the-loop, and multi-agent control flow.
- **"Why not just a while loop?"** A loop works until you need durable memory,
  resume-after-crash, approval gates, token streaming from inside the loop, or
  branching/replay. LangGraph gives all of those for the cost of one abstraction.
- **"What's a reducer?"** The per-channel merge function. It's why the messages
  list grows (append reducer) while a scalar field overwrites.
- **"How do you add a human approval step?"** `interrupt()` inside the node (or
  `interrupt_before` at compile) + a checkpointer; resume with `Command(resume=…)`.
- **"How does memory persist across sessions?"** A checkpointer keyed by
  `thread_id`; swap `InMemorySaver` for `SqliteSaver`/`PostgresSaver` for durability.
- **"How do agents hand off?"** `Command(goto=other_node, update=shared_state)` —
  a handoff is just "write shared state + jump."
- **"How would you debug a bad production run?"** Replay it: `get_state_history`
  to find where it went wrong, fork from an earlier checkpoint or `update_state`
  to correct, and read the full trace in LangSmith.
- **"How do you scale a big agent system?"** Compose **subgraphs** (each a focused
  agent) instead of one giant graph; isolate private channels; deploy on LangGraph
  Platform with a durable checkpointer.

---

## 7. Map to the hands-on lesson

| Concept                                             | Exercise               |
| --------------------------------------------------- | ---------------------- |
| State / channels / reducers                         | `06b-langgraph` Task 1 |
| Conditional edges, `ToolNode`, `create_react_agent` | Task 2                 |
| Checkpointer + threads + persistence                | Task 3                 |
| `interrupt()` / human-in-the-loop                   | Task 4                 |
| Streaming modes (updates/values/messages)           | Task 5                 |
| Subgraphs                                           | Task 6                 |
| Supervisor / `Command` handoff                      | Task 7                 |
| Time travel (history/fork/update_state)             | Task 8                 |

Official docs: <https://langchain-ai.github.io/langgraph/> (Python) and
<https://langchain-ai.github.io/langgraphjs/> (TypeScript).
