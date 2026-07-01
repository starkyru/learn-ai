/**
 * Task 6 🟡 — Reimplement Semantic Kernel: a Kernel of functions you invoke by name.
 *
 * What you'll learn:
 *   - Semantic Kernel's core idea: a `Kernel` is a registry of callable functions
 *     you invoke *by name*. Two kinds live side by side:
 *       * a "semantic function" = a prompt template + the model (fill the template
 *         with args, call the model);
 *       * a "native function"   = plain code (a JS function, no model).
 *   - Both share one interface — `invoke(args) -> string` — so the kernel treats
 *     them uniformly. That uniform interface is what lets you *chain* them.
 *   - SK's sequential orchestration is a tiny pipeline: run function A, feed its
 *     output as the input to function B, and so on. Same fold-forward threading
 *     as the Crew in Task 3, but over named kernel functions.
 *
 * The math (a fold over named functions):
 *
 *   Given a pipeline of function names [f_1, ..., f_n] and a starting input x:
 *
 *       out_0 = x
 *       out_i = kernel.invoke(f_i, { input: out_{i-1} })   // feed output forward
 *       return out_n                                        (the last output)
 *
 *   A semantic function renders its prompt by substituting {placeholders}:
 *
 *       prompt = fill(template, args)   // e.g. "Summarize: {input}" + { input }
 *       reply  = model(prompt)
 *
 * The pieces we reimplement (and the real semantic-kernel equivalent):
 *
 *   ours                            real semantic-kernel
 *   ----------------------------    ------------------------------------------
 *   KernelFunction (semantic)       a prompt function (addFunction({ prompt }))
 *   KernelFunction (native)         a @kernelFunction-decorated method
 *   Kernel.addFunction(name, fn)    kernel.addFunction(...) / addPlugin(...)
 *   Kernel.invoke(name, args)       kernel.invoke({ functionName, ... })
 *   runPipeline([...], input)       sequential orchestration over functions
 *
 * OFFLINE: this task takes a `chatFn: (msgs) => string`. With --stub it uses a
 * deterministic fake model that echoes the rendered prompt, so we can assert each
 * semantic function saw the previous step's output. Without --stub it builds
 * chatFn from `getProvider().chat` so the *same kernel* runs on a real LLM.
 *
 * How to run:
 *   pnpm tsx modules/06c-agent-frameworks/ts/06-semantic-kernel.ts --stub   # offline, deterministic
 *   pnpm tsx modules/06c-agent-frameworks/ts/06-semantic-kernel.ts          # real model via getProvider()
 */

import { getProvider } from "@learn-ai/llm-core";

export interface Msg {
  role: string;
  content: string;
}
export type ChatFn = (messages: Msg[]) => string;

// A call carries named string args (e.g. { input: "..." }).
export type Args = Record<string, string>;
// A native function is plain code: named args in, string out.
export type NativeFn = (args: Args) => string;

// ---------------------------------------------------------------------------
// KernelFunction — a semantic (prompt+model) or native (plain code) function
// ---------------------------------------------------------------------------

/**
 * One invocable unit. Either a semantic function (promptTemplate + chatFn) or a
 * native function (nativeFn). Exactly one of the two is set.
 * Real SK: a "prompt function" (semantic) vs a `@kernelFunction` method (native);
 * both are `KernelFunction`s you invoke by name.
 */
class KernelFunction {
  constructor(
    public name: string,
    public opts: {
      promptTemplate?: string; // set for a semantic function
      chatFn?: ChatFn; // the model, for a semantic function
      nativeFn?: NativeFn; // set for a native function
    },
  ) {}

  /**
   * Run this function with named args, returning a string.
   *   - Native function: just call the plain code with the args.
   *   - Semantic function: render the prompt template with the args, wrap it in
   *     one user message, call the model, and return the reply.
   *
   * TODO: implement.
   *   Native branch (this.opts.nativeFn is set):
   *     - return this.opts.nativeFn(args).
   *   Semantic branch (this.opts.promptTemplate is set):
   *     - Render the prompt by replacing each {key} in the template with
   *       args[key] (a regex replace over {\w+} does it).
   *     - Build a Msg[] with a single { role: "user", content } carrying the
   *       rendered prompt.
   *     - Call this.opts.chatFn(messages) and return the reply.
   *   (You can assume exactly one of nativeFn / promptTemplate is set.)
   */
  invoke(_args: Args): string {
    // TODO: implement KernelFunction.invoke (native call vs render+model)
    throw new Error("TODO: implement KernelFunction.invoke()");
  }
}

// ---------------------------------------------------------------------------
// Kernel — a registry of functions you invoke by name
// ---------------------------------------------------------------------------

/** Holds functions by name and invokes them. Real SK: `Kernel`. */
class Kernel {
  private functions = new Map<string, KernelFunction>();

  /** Register a prompt-backed (semantic) function. Complete. */
  addSemanticFunction(name: string, promptTemplate: string, chatFn: ChatFn): void {
    this.functions.set(name, new KernelFunction(name, { promptTemplate, chatFn }));
  }

  /** Register a plain-code (native) function. Complete. */
  addNativeFunction(name: string, nativeFn: NativeFn): void {
    this.functions.set(name, new KernelFunction(name, { nativeFn }));
  }

  /**
   * Look up the function named `name` and invoke it with `args`.
   *
   * TODO: implement.
   *   - Look up the function in this.functions (throw a clear error if it is
   *     missing — invoking an unregistered name is a bug).
   *   - Delegate to that KernelFunction's invoke(args) and return the result.
   */
  invoke(_name: string, _args: Args): string {
    // TODO: implement Kernel.invoke (look up by name, delegate)
    throw new Error("TODO: implement Kernel.invoke()");
  }

  /**
   * Chain functions sequentially: each output feeds the next as `input`.
   * This is SK's sequential orchestration: the functions here each take an
   * `input` argument, so we thread the running value forward under that key.
   *
   * TODO: implement.
   *   1. Start with current = initialInput.
   *   2. For each name in functionNames, in order:
   *        - invoke that function passing the running value as { input: current }
   *          (i.e. this.invoke(name, { input: current })).
   *        - set current to the returned string (thread it into the NEXT step).
   *   3. Return the final value (the last function's output).
   */
  runPipeline(_functionNames: string[], _initialInput: string): string {
    // TODO: implement runPipeline (sequential fold over named functions)
    throw new Error("TODO: implement Kernel.runPipeline()");
  }
}

// ---------------------------------------------------------------------------
// Stub + real model
// ---------------------------------------------------------------------------

/**
 * Deterministic fake: tag the reply with the rendered prompt it received.
 * It echoes the incoming prompt so tests can prove each semantic function saw
 * the previous step's output threaded in — we test the kernel, not the model.
 */
function makeStubChatFn(): ChatFn {
  return (messages: Msg[]) => {
    const prompt = messages[messages.length - 1].content;
    return `<${prompt}>`;
  };
}

/** Wrap the shared provider. Sync signature; real chat is async — see README. */
function makeRealChatFn(): ChatFn {
  const provider = getProvider();
  void provider;
  return () => {
    throw new Error(
      "Real provider chat is async. Run with --stub for the offline check, " +
        "or adapt KernelFunction.invoke to `await provider.chat(...)`.",
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
  console.log(`\n=== Task 6: Semantic Kernel — ${mode} ===\n`);

  const kernel = new Kernel();

  // A native function (plain code): normalize whitespace on the input. No model.
  kernel.addNativeFunction("clean", (args) =>
    args.input.split(/\s+/).filter(Boolean).join(" "),
  );

  // Two semantic functions (prompt template + model): summarize, then translate.
  kernel.addSemanticFunction(
    "summarize",
    "Summarize the following text in one sentence:\n{input}",
    chatFn,
  );
  kernel.addSemanticFunction(
    "translate",
    "Translate the following text to French:\n{input}",
    chatFn,
  );

  const raw = "  RAG   grounds a model    in retrieved documents.  ";

  // ── Invoke one function by name (native) ─────────────────────────────────
  const cleaned = kernel.invoke("clean", { input: raw });
  console.log(
    `native  clean(${JSON.stringify(raw)})\n     -> ${JSON.stringify(cleaned)}`,
  );

  // ── Sequential pipeline: clean -> summarize -> translate ─────────────────
  const final = kernel.runPipeline(["clean", "summarize", "translate"], raw);
  console.log("\npipeline: clean -> summarize -> translate");
  console.log(`final -> ${JSON.stringify(final)}`);

  if (useStub) {
    // 1) The native function ran real code (collapsed the extra whitespace).
    if (cleaned !== "RAG grounds a model in retrieved documents.")
      throw new Error(`native clean produced ${JSON.stringify(cleaned)}`);
    // 2) A single semantic invoke renders its template with the arg.
    const one = kernel.invoke("summarize", { input: "hello world" });
    if (one !== "<Summarize the following text in one sentence:\nhello world>")
      throw new Error(`semantic render wrong: ${JSON.stringify(one)}`);
    // 3) The pipeline threaded outputs forward: the final (translate) step's
    //    prompt wrapped the summarize step's output, which wrapped the cleaned
    //    text — so the cleaned text survives to the end.
    if (!final.startsWith("<Translate the following text to French:"))
      throw new Error("pipeline did not end with the translate step");
    if (!final.includes("Summarize the following text in one sentence:"))
      throw new Error("summarize output did not thread into translate");
    if (!final.includes("RAG grounds a model in retrieved documents."))
      throw new Error("cleaned input did not survive the pipeline");
    console.log(
      "\n[ok] native code ran; semantic funcs rendered; pipeline threaded outputs",
    );
  }

  console.log(
    "\nReal semantic-kernel: register prompt/native functions on a Kernel and " +
      "kernel.invoke({ functionName }) / sequential orchestration runs the chain.",
  );
}

main();
