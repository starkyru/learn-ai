"""
Task 6 🟡 — Reimplement Semantic Kernel: a Kernel of functions you invoke by name.

What you'll learn:
  - Semantic Kernel's core idea: a `Kernel` is a registry of callable functions
    you invoke *by name*. Two kinds live side by side:
      * a "semantic function" = a prompt template + the model (fill the template
        with args, call the model);
      * a "native function"   = plain code (a Python callable, no model).
  - Both share one interface — `invoke(**args) -> str` — so the kernel treats
    them uniformly. That uniform interface is what lets you *chain* them.
  - SK's sequential orchestration is a tiny pipeline: run function A, feed its
    output as the input to function B, and so on. Same fold-forward threading as
    the Crew in Task 3, but over named kernel functions.

The math (a fold over named functions):

  Given a pipeline of function names [f_1, ..., f_n] and a starting input x:

      out_0 = x
      out_i = kernel.invoke(f_i, input=out_{i-1})   # feed prior output forward
      return out_n                                   (the last function's output)

  A semantic function renders its prompt by substituting {placeholders}:

      prompt = template.format(**args)   # e.g. "Summarize: {input}" + {input=...}
      reply  = model(prompt)

The pieces we reimplement (and the real semantic-kernel equivalent):

  ours                            real semantic-kernel
  ----------------------------    ------------------------------------------
  KernelFunction (semantic)       a prompt function (add_function(prompt=...))
  KernelFunction (native)         a @kernel_function-decorated method
  Kernel.add_function(name, fn)   kernel.add_function(...) / add_plugin(...)
  Kernel.invoke(name, **args)     await kernel.invoke(function_name=..., ...)
  run_pipeline([...], input)      sequential orchestration over functions

OFFLINE: this task takes a `chat_fn: Callable[[list[dict]], str]`. With --stub it
uses a deterministic fake model that echoes the rendered prompt, so we can assert
each semantic function saw the previous step's output. Without --stub it builds
chat_fn from `get_provider().chat` so the *same kernel* runs on a real LLM.

How to run:
  uv run python modules/06c-agent-frameworks/py/06_semantic_kernel.py --stub   # offline, deterministic
  uv run python modules/06c-agent-frameworks/py/06_semantic_kernel.py          # real model via get_provider()
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ChatFn = Callable[[list[dict[str, str]]], str]

# A native function is plain code: it takes keyword args and returns a string.
NativeFn = Callable[..., str]


# ---------------------------------------------------------------------------
# KernelFunction — a semantic (prompt+model) or native (plain code) function
# ---------------------------------------------------------------------------


@dataclass
class KernelFunction:
    """One invocable unit. Either a semantic function (prompt_template + chat_fn)
    or a native function (native_fn). Exactly one of the two is set.

    Real SK: a "prompt function" (semantic) vs a `@kernel_function` method
    (native); both are `KernelFunction`s you invoke by name.
    """

    name: str
    prompt_template: str | None = None  # set for a semantic function
    chat_fn: ChatFn | None = None  # the model, for a semantic function
    native_fn: NativeFn | None = None  # set for a native function

    def invoke(self, **args: Any) -> str:
        """Run this function with keyword arguments, returning a string.

        - Native function: just call the plain code with the args.
        - Semantic function: render the prompt template with the args, wrap it in
          one user message, call the model, and return the reply.

        TODO: implement.
          Native branch (self.native_fn is not None):
            - return self.native_fn(**args).
          Semantic branch (self.prompt_template is not None):
            - Render the prompt by substituting the args into the template's
              {placeholders} (standard str formatting fills them by name).
            - Build a `list[dict[str, str]]` with a single {"role", "content"}
              user message carrying that rendered prompt.
            - Call self.chat_fn(messages) and return the reply.
          (You can assume exactly one of native_fn / prompt_template is set.)
        """
        # TODO: implement KernelFunction.invoke (native call vs render+model)
        raise NotImplementedError("TODO: implement KernelFunction.invoke()")


# ---------------------------------------------------------------------------
# Kernel — a registry of functions you invoke by name
# ---------------------------------------------------------------------------


class Kernel:
    """Holds functions by name and invokes them. Real SK: `Kernel`."""

    def __init__(self) -> None:
        self.functions: dict[str, KernelFunction] = {}

    def add_semantic_function(self, name: str, prompt_template: str, chat_fn: ChatFn) -> None:
        """Register a prompt-backed (semantic) function. Complete."""
        self.functions[name] = KernelFunction(
            name=name, prompt_template=prompt_template, chat_fn=chat_fn
        )

    def add_native_function(self, name: str, native_fn: NativeFn) -> None:
        """Register a plain-code (native) function. Complete."""
        self.functions[name] = KernelFunction(name=name, native_fn=native_fn)

    def invoke(self, name: str, **args: Any) -> str:
        """Look up the function named `name` and invoke it with `args`.

        TODO: implement.
          - Look up self.functions[name] (raise a clear KeyError/ValueError if
            it is missing — invoking an unregistered name is a bug).
          - Delegate to that KernelFunction's invoke(**args) and return the result.
        """
        # TODO: implement Kernel.invoke (look up by name, delegate)
        raise NotImplementedError("TODO: implement Kernel.invoke()")

    def run_pipeline(self, function_names: list[str], initial_input: str) -> str:
        """Chain functions sequentially: each output feeds the next as `input`.

        This is SK's sequential orchestration: the functions here each take an
        `input` argument, so we thread the running value forward under that key.

        TODO: implement.
          1. Start with current = initial_input.
          2. For each name in function_names, in order:
               - invoke that function passing the running value as input=current
                 (i.e. self.invoke(name, input=current)).
               - set current to the returned string (thread it into the NEXT step).
          3. Return the final value (the last function's output).
        """
        # TODO: implement run_pipeline (sequential fold over named functions)
        raise NotImplementedError("TODO: implement Kernel.run_pipeline()")


# ---------------------------------------------------------------------------
# Stub + real model
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """Deterministic fake: tag the reply with the rendered prompt it received.

    It echoes the incoming prompt so tests can prove each semantic function saw
    the previous step's output threaded in — we test the kernel, not the model.
    """

    def chat_fn(messages: list[dict[str, str]]) -> str:
        prompt = messages[-1]["content"]
        return f"<{prompt}>"

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    """Build a ChatFn backed by the shared llm_core provider."""
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        return provider.chat(messages).text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic Kernel reimplementation (Task 6).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 6: Semantic Kernel — {mode} ===\n")

    kernel = Kernel()

    # A native function (plain code): normalize whitespace on the input. No model.
    def clean(input: str) -> str:  # noqa: A002 — SK uses `input` as the arg name
        return " ".join(input.split())

    kernel.add_native_function("clean", clean)

    # Two semantic functions (prompt template + model): summarize, then translate.
    kernel.add_semantic_function(
        "summarize",
        "Summarize the following text in one sentence:\n{input}",
        chat_fn,
    )
    kernel.add_semantic_function(
        "translate",
        "Translate the following text to French:\n{input}",
        chat_fn,
    )

    raw = "  RAG   grounds a model    in retrieved documents.  "

    # ── Invoke one function by name (native) ─────────────────────────────────
    cleaned = kernel.invoke("clean", input=raw)
    print(f"native  clean({raw!r})\n     -> {cleaned!r}")

    # ── Sequential pipeline: clean -> summarize -> translate ─────────────────
    final = kernel.run_pipeline(["clean", "summarize", "translate"], raw)
    print("\npipeline: clean -> summarize -> translate")
    print(f"final -> {final!r}")

    if args.stub:
        # 1) The native function ran real code (collapsed the extra whitespace).
        assert cleaned == "RAG grounds a model in retrieved documents.", (
            f"native clean produced {cleaned!r}"
        )
        # 2) A single semantic invoke renders its template with the arg.
        one = kernel.invoke("summarize", input="hello world")
        assert one == "<Summarize the following text in one sentence:\nhello world>", (
            f"semantic render wrong: {one!r}"
        )
        # 3) The pipeline threaded outputs forward: the final (translate) step's
        #    prompt wrapped the summarize step's output, which wrapped the
        #    cleaned text — so the cleaned text survives to the end.
        assert final.startswith("<Translate the following text to French:")
        assert "Summarize the following text in one sentence:" in final, (
            "summarize output did not thread into translate"
        )
        assert "RAG grounds a model in retrieved documents." in final, (
            "cleaned input did not survive the pipeline"
        )
        print("\n[ok] native code ran; semantic funcs rendered; pipeline threaded outputs")

    print(
        "\nReal semantic-kernel: register prompt/native functions on a Kernel and "
        "kernel.invoke(function_name=...) / sequential orchestration runs the chain."
    )


if __name__ == "__main__":
    main()
