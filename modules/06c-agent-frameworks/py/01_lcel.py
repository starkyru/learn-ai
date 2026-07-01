"""
Task 1 🟢 — Reimplement LangChain LCEL (the `|` pipe).

What you'll learn:
  - What a "Runnable" actually is: any object with an `invoke(input) -> output`.
  - How LangChain's `prompt | model | parser` chain is *just* function composition:
    each `|` threads one step's output into the next step's input.
  - Why LCEL feels magic but is ~30 lines: `pipe()` returns a RunnableSequence,
    and `invoke()` walks the steps left-to-right.

The math (composition, not calculus):

  A chain is a sequence of steps s_1, s_2, ..., s_n. Running it on input x is
  just repeated application:

      out = s_n( ... s_2( s_1(x) ) ... )

  or, folding left over the step list with the running value `acc`:

      acc <- x
      for step in steps:
          acc <- step.invoke(acc)
      return acc

  `pipe(other)` is the algebra: (a | b) means "an object whose invoke runs a
  then feeds the result to b". Chaining more just extends the step list.

The pieces we reimplement (and the real LangChain equivalent):

  ours                         real langchain-core
  ------------------------     ----------------------------------------
  Runnable.invoke              Runnable.invoke
  Runnable.pipe(other)         Runnable.__or__  (the `|` operator)
  RunnableSequence             RunnableSequence (what `a | b` builds)
  PromptTemplate(t).format()   PromptTemplate.from_template(t).invoke(vars)
  ModelRunnable(chat_fn)       a ChatModel (wrapped as a Runnable)
  StrOutputParser              StrOutputParser

OFFLINE: this task takes a `chat_fn: Callable[[list[dict]], str]`. With --stub it
uses a deterministic fake model (no network). Without --stub it builds chat_fn
from `get_provider().chat` so the *same chain* runs against a real LLM.

How to run:
  uv run python modules/06c-agent-frameworks/py/01_lcel.py --stub   # offline, deterministic
  uv run python modules/06c-agent-frameworks/py/01_lcel.py          # real model via get_provider()
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

# A ChatFn is the whole model dependency, narrowed to one function:
#   given a list of chat messages ({"role", "content"}), return the reply text.
ChatFn = Callable[[list[dict[str, str]]], str]


# ---------------------------------------------------------------------------
# The Runnable protocol — the heart of LCEL
# ---------------------------------------------------------------------------


class Runnable:
    """Base class: anything with an `invoke(input) -> output`.

    `pipe(other)` composes two runnables into a RunnableSequence, so that
    `a.pipe(b).pipe(c)` behaves like the LangChain expression `a | b | c`.
    """

    def invoke(self, input: Any) -> Any:  # noqa: A002 - mirror LangChain's name
        raise NotImplementedError("subclasses implement invoke()")

    def pipe(self, other: Runnable) -> RunnableSequence:
        """Compose self with `other`, returning a RunnableSequence.

        `a.pipe(b)` must run `a` first, then feed its output into `b`.
        If `self` is already a RunnableSequence, flatten so we keep a single
        flat list of steps instead of nesting sequences.

        TODO: implement.
          1. Collect self's steps: if isinstance(self, RunnableSequence) use
             self.steps, else [self].
          2. Collect other's steps the same way.
          3. return RunnableSequence(left_steps + right_steps).
        """
        # TODO: implement pipe (compose into a RunnableSequence)
        raise NotImplementedError("TODO: implement Runnable.pipe()")


class RunnableSequence(Runnable):
    """An ordered list of steps. invoke() threads the value through each."""

    def __init__(self, steps: list[Runnable]) -> None:
        self.steps = steps

    def invoke(self, input: Any) -> Any:  # noqa: A002
        """Run each step in order, threading output -> next input.

        TODO: implement.
          1. acc = input
          2. for step in self.steps: acc = step.invoke(acc)
          3. return acc
        """
        # TODO: implement the fold-left over self.steps
        raise NotImplementedError("TODO: implement RunnableSequence.invoke()")


# ---------------------------------------------------------------------------
# Concrete runnables
# ---------------------------------------------------------------------------


class PromptTemplate(Runnable):
    """A string template with {placeholders}. invoke(vars_dict) -> filled string.

    Real LangChain: `PromptTemplate.from_template("...").invoke({...})`.
    """

    def __init__(self, template: str) -> None:
        self.template = template

    def format(self, **variables: Any) -> str:
        """Fill the template's {placeholders} from keyword variables.

        e.g. PromptTemplate("Tell a joke about {topic}").format(topic="cats")
             -> "Tell a joke about cats"

        TODO: implement.
          Use Python str formatting: return self.template.format(**variables)
        """
        # TODO: implement template formatting
        raise NotImplementedError("TODO: implement PromptTemplate.format()")

    def invoke(self, input: dict[str, Any]) -> str:  # noqa: A002
        # As a Runnable, invoking a prompt = formatting it from an input dict.
        return self.format(**input)


class ModelRunnable(Runnable):
    """Wraps a ChatFn as a Runnable. invoke(prompt_str) -> model reply str.

    Real LangChain: a ChatModel is already a Runnable; you just drop it in the
    pipe. Here we adapt our plain `chat_fn` into the same shape by turning the
    incoming prompt string into a single user message.
    """

    def __init__(self, chat_fn: ChatFn) -> None:
        self.chat_fn = chat_fn

    def invoke(self, input: str) -> str:  # noqa: A002
        messages = [{"role": "user", "content": input}]
        return self.chat_fn(messages)


class StrOutputParser(Runnable):
    """Trivial output parser: strip whitespace off the model's raw text.

    Real LangChain: StrOutputParser pulls `.content` off a chat message and
    returns the plain string. Ours strips, which is enough for text pipelines.
    """

    def invoke(self, input: str) -> str:  # noqa: A002
        return input.strip()


# ---------------------------------------------------------------------------
# Deterministic stub model (offline) and the real model adapter
# ---------------------------------------------------------------------------


def make_stub_chat_fn() -> ChatFn:
    """A fake model: echoes the prompt in a fixed, deterministic template.

    It surrounds its reply with leading/trailing whitespace on purpose so the
    StrOutputParser has something to strip — proving the parser step ran.
    """

    def chat_fn(messages: list[dict[str, str]]) -> str:
        last = messages[-1]["content"]
        return f"  [stub-reply] {last}  "

    return chat_fn


def make_real_chat_fn() -> ChatFn:
    """Build a ChatFn backed by the shared llm_core provider."""
    from llm_core import get_provider

    provider = get_provider()

    def chat_fn(messages: list[dict[str, str]]) -> str:
        result = provider.chat(messages)
        return result.text

    return chat_fn


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def build_chain(chat_fn: ChatFn) -> Runnable:
    """The canonical LCEL chain: prompt | model | parser."""
    prompt = PromptTemplate("Write a one-line tagline about {topic}.")
    model = ModelRunnable(chat_fn)
    parser = StrOutputParser()
    return prompt.pipe(model).pipe(parser)


def main() -> None:
    ap = argparse.ArgumentParser(description="LCEL reimplementation (Task 1).")
    ap.add_argument("--stub", action="store_true", help="use the offline deterministic model")
    args = ap.parse_args()

    chat_fn = make_stub_chat_fn() if args.stub else make_real_chat_fn()
    mode = "STUB (offline)" if args.stub else "REAL (get_provider)"
    print(f"\n=== Task 1: LCEL runnable — {mode} ===\n")

    # ── The canonical chain: prompt | model | parser ──────────────────────
    chain = build_chain(chat_fn)
    out = chain.invoke({"topic": "vector databases"})
    print("chain = prompt.pipe(model).pipe(parser)")
    print('chain.invoke({"topic": "vector databases"}) ->')
    print(f"  {out!r}")

    if args.stub:
        # The stub reply is deterministic, so we can assert the exact string.
        expected = "[stub-reply] Write a one-line tagline about vector databases."
        assert out == expected, f"expected {expected!r}, got {out!r}"
        # And prove the parser stripped the stub's surrounding whitespace:
        assert not out.startswith(" ") and not out.endswith(" "), "parser did not strip"
        print("\n[ok] parsed output matches the formatted prompt through the fake model")

    # ── A 3-step sequence applies steps in strict left-to-right order ──────
    # Build three tiny runnables from plain lambdas to show ordering matters.
    class Lambda(Runnable):
        def __init__(self, fn: Callable[[Any], Any]) -> None:
            self.fn = fn

        def invoke(self, input: Any) -> Any:  # noqa: A002
            return self.fn(input)

    add1 = Lambda(lambda x: x + 1)
    times3 = Lambda(lambda x: x * 3)
    to_str = Lambda(lambda x: f"result={x}")
    seq = add1.pipe(times3).pipe(to_str)
    seq_out = seq.invoke(4)  # ((4 + 1) * 3) -> "result=15"
    print(f"\n3-step sequence: (4 + 1) * 3 -> {seq_out!r}")
    if args.stub:
        assert seq_out == "result=15", f"ordering wrong: {seq_out!r}"
        # Swapping the order changes the result, proving order is enforced:
        swapped = times3.pipe(add1).pipe(to_str).invoke(4)  # (4 * 3) + 1 -> 13
        assert swapped == "result=13", f"expected result=13, got {swapped!r}"
        print("[ok] steps applied in order; swapping order changes the result")

    print(
        "\nReal LangChain: `prompt | model | parser` builds the same "
        "RunnableSequence via the __or__ operator."
    )


if __name__ == "__main__":
    main()
