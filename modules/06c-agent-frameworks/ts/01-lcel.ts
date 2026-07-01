/**
 * Task 1 🟢 — Reimplement LangChain LCEL (the `|` pipe).
 *
 * What you'll learn:
 *   - What a "Runnable" actually is: any object with an `invoke(input) -> output`.
 *   - How LangChain's `prompt | model | parser` chain is *just* function
 *     composition: each `|` threads one step's output into the next step's input.
 *   - Why LCEL feels magic but is ~30 lines: `pipe()` returns a RunnableSequence,
 *     and `invoke()` walks the steps left-to-right.
 *
 * The math (composition, not calculus):
 *
 *   A chain is a sequence of steps s_1, s_2, ..., s_n. Running it on input x is
 *   just repeated application:
 *
 *       out = s_n( ... s_2( s_1(x) ) ... )
 *
 *   or, folding left over the step list with the running value `acc`:
 *
 *       acc <- x
 *       for step of steps: acc <- step.invoke(acc)
 *       return acc
 *
 *   `pipe(other)` is the algebra: (a | b) means "an object whose invoke runs a
 *   then feeds the result to b". Chaining more just extends the step list.
 *
 * The pieces we reimplement (and the real LangChain equivalent):
 *
 *   ours                          real langchain-core
 *   ------------------------      ----------------------------------------
 *   Runnable.invoke               Runnable.invoke
 *   Runnable.pipe(other)          Runnable.pipe / the `|` operator
 *   RunnableSequence              RunnableSequence (what `a.pipe(b)` builds)
 *   PromptTemplate(t).format()    PromptTemplate.fromTemplate(t).invoke(vars)
 *   ModelRunnable(chatFn)         a ChatModel (already a Runnable)
 *   StrOutputParser               StrOutputParser
 *
 * OFFLINE: this task takes a `chatFn: (msgs) => string`. With --stub it uses a
 * deterministic fake model (no network). Without --stub it builds chatFn from
 * `getProvider().chat` so the *same chain* runs against a real LLM.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/01-lcel.ts --stub   # offline, deterministic
 *   pnpm tsx modules/06c-agent-frameworks/ts/01-lcel.ts          # real model via getProvider()
 */

import { getProvider } from "@learn-ai/llm-core";

// A ChatFn is the whole model dependency narrowed to one function:
//   given a list of chat messages ({role, content}), return the reply text.
export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

// ---------------------------------------------------------------------------
// The Runnable protocol — the heart of LCEL
// ---------------------------------------------------------------------------

/**
 * Base class: anything with an `invoke(input) -> output`.
 * `pipe(other)` composes two runnables into a RunnableSequence, so that
 * `a.pipe(b).pipe(c)` behaves like the LangChain expression `a | b | c`.
 */
abstract class Runnable<I = unknown, O = unknown> {
  abstract invoke(input: I): O;

  /**
   * Compose self with `other`, returning a RunnableSequence.
   *
   * `a.pipe(b)` must run `a` first, then feed its output into `b`.
   * If `self` is already a RunnableSequence, flatten so we keep a single flat
   * list of steps instead of nesting sequences.
   *
   * TODO: implement.
   *   1. leftSteps  = (this instanceof RunnableSequence) ? this.steps : [this]
   *   2. rightSteps = (other instanceof RunnableSequence) ? other.steps : [other]
   *   3. return new RunnableSequence([...leftSteps, ...rightSteps])
   */
  pipe(_other: Runnable<O, unknown>): RunnableSequence {
    // TODO: implement pipe (compose into a RunnableSequence)
    throw new Error("TODO: implement Runnable.pipe()");
  }
}

/** An ordered list of steps. invoke() threads the value through each. */
class RunnableSequence extends Runnable<unknown, unknown> {
  constructor(public steps: Runnable<unknown, unknown>[]) {
    super();
  }

  /**
   * Run each step in order, threading output -> next input.
   *
   * TODO: implement.
   *   1. let acc: unknown = input
   *   2. for (const step of this.steps) acc = step.invoke(acc)
   *   3. return acc
   */
  invoke(_input: unknown): unknown {
    // TODO: implement the fold-left over this.steps
    throw new Error("TODO: implement RunnableSequence.invoke()");
  }
}

// ---------------------------------------------------------------------------
// Concrete runnables
// ---------------------------------------------------------------------------

/**
 * A string template with {placeholders}. invoke(varsObject) -> filled string.
 * Real LangChain: `PromptTemplate.fromTemplate("...").invoke({...})`.
 */
class PromptTemplate extends Runnable<Record<string, unknown>, string> {
  constructor(private template: string) {
    super();
  }

  /**
   * Fill the template's {placeholders} from a variables object.
   * e.g. new PromptTemplate("Tell a joke about {topic}").format({topic: "cats"})
   *      -> "Tell a joke about cats"
   *
   * TODO: implement.
   *   Replace every {key} with String(variables[key]).
   *   Hint: this.template.replace(/\{(\w+)\}/g, (_, k) => String(variables[k]))
   */
  format(_variables: Record<string, unknown>): string {
    // TODO: implement template formatting
    throw new Error("TODO: implement PromptTemplate.format()");
  }

  invoke(input: Record<string, unknown>): string {
    // As a Runnable, invoking a prompt = formatting it from an input object.
    return this.format(input);
  }
}

/**
 * Wraps a ChatFn as a Runnable. invoke(promptStr) -> model reply str.
 * Real LangChain: a ChatModel is already a Runnable; you just drop it in the
 * pipe. Here we adapt our plain `chatFn` by turning the prompt string into a
 * single user message.
 */
class ModelRunnable extends Runnable<string, string> {
  constructor(private chatFn: ChatFn) {
    super();
  }

  invoke(input: string): string {
    return this.chatFn([{ role: "user", content: input }]);
  }
}

/**
 * Trivial output parser: strip whitespace off the model's raw text.
 * Real LangChain: StrOutputParser pulls `.content` off a chat message.
 */
class StrOutputParser extends Runnable<string, string> {
  invoke(input: string): string {
    return input.trim();
  }
}

/** Wrap a plain function as a Runnable (used to demo step ordering). */
class RunnableLambda<I, O> extends Runnable<I, O> {
  constructor(private fn: (x: I) => O) {
    super();
  }
  invoke(input: I): O {
    return this.fn(input);
  }
}

// ---------------------------------------------------------------------------
// Deterministic stub model (offline) and the real model adapter
// ---------------------------------------------------------------------------

/**
 * A fake model: echoes the prompt in a fixed, deterministic template.
 * It pads its reply with whitespace on purpose so StrOutputParser has
 * something to strip — proving the parser step ran.
 */
function makeStubChatFn(): ChatFn {
  return (messages: Msg[]) => {
    const last = messages[messages.length - 1].content;
    return `  [stub-reply] ${last}  `;
  };
}

/** Build a ChatFn backed by the shared llm_core provider. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  // The real provider is async; we keep ChatFn sync for the reimplementation,
  // so we surface a clear error if someone runs the real path without a model.
  // (For a real async pipeline, LangChain's Runnable.invoke is itself async.)
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt ModelRunnable to `await provider.chat(...)`.",
    );
  };
  // NOTE: `provider` is captured so learners can switch ModelRunnable to async
  // and call `await provider.chat(messages)`. See README for the async note.
  void provider;
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

/** The canonical LCEL chain: prompt | model | parser. */
function buildChain(chatFn: ChatFn): Runnable<Record<string, unknown>, unknown> {
  const prompt = new PromptTemplate("Write a one-line tagline about {topic}.");
  const model = new ModelRunnable(chatFn);
  const parser = new StrOutputParser();
  return prompt.pipe(model).pipe(parser) as unknown as Runnable<
    Record<string, unknown>,
    unknown
  >;
}

function main(): void {
  const useStub = process.argv.includes("--stub");
  const chatFn = useStub ? makeStubChatFn() : makeRealChatFn();
  const mode = useStub ? "STUB (offline)" : "REAL (getProvider)";
  console.log(`\n=== Task 1: LCEL runnable — ${mode} ===\n`);

  // ── The canonical chain: prompt | model | parser ────────────────────────
  const chain = buildChain(chatFn);
  const out = chain.invoke({ topic: "vector databases" }) as string;
  console.log("chain = prompt.pipe(model).pipe(parser)");
  console.log('chain.invoke({ topic: "vector databases" }) ->');
  console.log(`  ${JSON.stringify(out)}`);

  if (useStub) {
    const expected = "[stub-reply] Write a one-line tagline about vector databases.";
    if (out !== expected)
      throw new Error(
        `expected ${JSON.stringify(expected)}, got ${JSON.stringify(out)}`,
      );
    if (out.startsWith(" ") || out.endsWith(" "))
      throw new Error("parser did not strip");
    console.log(
      "\n[ok] parsed output matches the formatted prompt through the fake model",
    );
  }

  // ── A 3-step sequence applies steps in strict left-to-right order ────────
  const add1 = new RunnableLambda<number, number>((x) => x + 1);
  const times3 = new RunnableLambda<number, number>((x) => x * 3);
  const toStr = new RunnableLambda<number, string>((x) => `result=${x}`);
  const seq = add1.pipe(times3).pipe(toStr);
  const seqOut = seq.invoke(4) as string; // ((4 + 1) * 3) -> "result=15"
  console.log(`\n3-step sequence: (4 + 1) * 3 -> ${JSON.stringify(seqOut)}`);

  if (useStub) {
    if (seqOut !== "result=15")
      throw new Error(`ordering wrong: ${JSON.stringify(seqOut)}`);
    const swapped = times3.pipe(add1).pipe(toStr).invoke(4) as string; // (4 * 3) + 1 -> 13
    if (swapped !== "result=13")
      throw new Error(`expected result=13, got ${JSON.stringify(swapped)}`);
    console.log("[ok] steps applied in order; swapping order changes the result");
  }

  console.log(
    "\nReal LangChain: `prompt | model | parser` builds the same " +
      "RunnableSequence via the pipe operator.",
  );
}

main();
