"""
Task 6 — Langfuse: production tracing  🟡

What this teaches:
  - Task 2 hand-rolled a JSONL tracer. That's great for intuition, but in a real
    service you don't want to build (and babysit) your own dashboards, session
    grouping, cost roll-ups, and alerting. Langfuse (https://langfuse.com) is the
    industry-standard, open-source LLM-observability platform that gives you all
    of that for free — you just instrument your calls.
  - The core Langfuse vocabulary:
      * trace       — one end-to-end request/workflow (e.g. "answer the user").
      * generation  — one LLM call inside a trace, with input, output, the model,
                      token usage, and cost. A trace can hold many generations.
      * session     — a group of traces that belong together (a conversation, a
                      user's day of usage), so you can inspect them as one unit.
    You'll see these exact concepts in the hosted UI once you add keys.
  - The lesson is tracer-AGNOSTIC instrumentation: write your app once against a
    small `Tracer` interface, then pick the backend (hosted Langfuse or a local
    print-only tracer) at runtime. Nothing in `traced_chat` knows which one it is.

Offline-friendly by design:
  - With NO Langfuse keys set, this runs a `LocalTracer` that prints an indented
    trace tree to stdout — no account, no network. Set LANGFUSE_PUBLIC_KEY and
    LANGFUSE_SECRET_KEY to send the same data to the hosted UI instead.
  - It also survives having NO LLM running: if the provider is unavailable, it
    falls back to a deterministic fake ChatResult so the tracing path still runs.

How to run:
  # 1. Install the SDK (module 07 extra):
  uv sync --extra production
  # 2. Run offline (LocalTracer, prints a trace tree):
  uv run python modules/07-advanced-production/py/06_langfuse_tracing.py
  # 3. (Optional) See it in the hosted UI — get free keys at https://cloud.langfuse.com:
  export LANGFUSE_PUBLIC_KEY=pk-lf-...
  export LANGFUSE_SECRET_KEY=sk-lf-...
  uv run python modules/07-advanced-production/py/06_langfuse_tracing.py
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Protocol

from llm_core import ChatMessage, ChatResult, TokenUsage, get_provider

# ---------------------------------------------------------------------------
# Cost table  (approx USD per 1M tokens — same idea as Task 2)
# ---------------------------------------------------------------------------

COST_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
    # Ollama / local: 0 cost (omit from table)
}


def estimate_cost(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Return estimated USD cost for this call, or None if unknown.

    TODO 1 (same formula as Task 2):
      - Look up `model` in COST_PER_1M.
      - If found AND both token counts are not None:
            cost = (input_tokens  / 1_000_000) * costs["input"]
                 + (output_tokens / 1_000_000) * costs["output"]
        return that cost.
      - Otherwise return None (unknown/local model, or missing token counts).
    """
    raise NotImplementedError("TODO 1: implement estimate_cost (see Task 2)")


# ---------------------------------------------------------------------------
# The Tracer interface — application code depends ONLY on this.
# Two implementations below: LangfuseTracer (real) and LocalTracer (offline).
# ---------------------------------------------------------------------------


@dataclass
class GenerationRecord:
    """One LLM call inside a trace — the tracer-agnostic shape we record."""

    name: str
    model: str
    input: str
    output: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    cost_usd: float | None


class Tracer(Protocol):
    """A backend that can open a trace/session and record generations in it."""

    def start_trace(self, name: str, session_id: str) -> None: ...

    def generation(self, rec: GenerationRecord) -> None: ...

    def end_trace(self) -> None: ...

    def flush(self) -> None: ...


# ---------------------------------------------------------------------------
# LangfuseTracer — the REAL backend (used only when keys are present).
# This body is PROVIDED COMPLETE so you can see correct v3/v4 SDK usage.
# ---------------------------------------------------------------------------


class LangfuseTracer:
    """Sends traces + generations to the hosted (or self-hosted) Langfuse UI.

    SDK reference (langfuse>=3): create one client, open a root span per trace,
    add a 'generation' observation per LLM call with input/output/usage/cost,
    group traces under a session_id, and flush() before exit.
    """

    def __init__(self) -> None:
        from langfuse import Langfuse  # imported lazily so the offline path needs no SDK

        self._client = Langfuse(
            public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
            secret_key=os.environ["LANGFUSE_SECRET_KEY"],
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        self._session_ctx = None  # propagate_attributes context (sets session_id)
        self._trace_ctx = None  # the root span context manager
        self._trace_span = None  # the root span (the "trace")

    def start_trace(self, name: str, session_id: str) -> None:
        from langfuse import propagate_attributes

        # propagate_attributes tags this + all child observations with session_id,
        # so the hosted UI groups every generation under one session.
        self._session_ctx = propagate_attributes(session_id=session_id)
        self._session_ctx.__enter__()

        self._trace_ctx = self._client.start_as_current_observation(
            name=name, as_type="span", input={"session_id": session_id}
        )
        self._trace_span = self._trace_ctx.__enter__()

    def generation(self, rec: GenerationRecord) -> None:
        # One 'generation' observation per LLM call. usage_details / cost_details
        # are what power Langfuse's token + cost dashboards.
        usage_details: dict[str, int] = {}
        if rec.input_tokens is not None:
            usage_details["input"] = rec.input_tokens
        if rec.output_tokens is not None:
            usage_details["output"] = rec.output_tokens

        cost_details = {"total": rec.cost_usd} if rec.cost_usd is not None else None

        gen = self._client.start_observation(
            name=rec.name,
            as_type="generation",
            model=rec.model,
            input=rec.input,
            usage_details=usage_details or None,
            cost_details=cost_details,
        )
        gen.update(output=rec.output, metadata={"latency_ms": rec.latency_ms})
        gen.end()

    def end_trace(self) -> None:
        if self._trace_ctx is not None:
            self._trace_ctx.__exit__(None, None, None)
            self._trace_ctx = self._trace_span = None
        if self._session_ctx is not None:
            self._session_ctx.__exit__(None, None, None)
            self._session_ctx = None

    def flush(self) -> None:
        # Langfuse batches network sends; flush() forces them before the process exits.
        self._client.flush()


# ---------------------------------------------------------------------------
# LocalTracer — offline fallback. Prints an indented trace tree. No network.
# ---------------------------------------------------------------------------


class LocalTracer:
    """Prints the same trace/generation structure Langfuse would show — to stdout."""

    def __init__(self) -> None:
        self._name = ""
        self._session_id = ""
        self.records: list[GenerationRecord] = []

    def start_trace(self, name: str, session_id: str) -> None:
        self._name = name
        self._session_id = session_id
        self.records = []
        print(f"\n[trace] {name}  (session={session_id})")

    def generation(self, rec: GenerationRecord) -> None:
        """Record a generation under the current trace and print it as a tree node.

        TODO 3: Append `rec` to self.records so end_trace() can total the costs,
        then print ONE indented tree-node line for this generation (the trace
        header above is already printed). Include on that line: the generation
        name, model, latency in ms (0 decimals), the in/out token counts, and the
        cost formatted via the provided `_fmt_cost()` helper. Then print two more
        indented lines showing the truncated (first ~60 chars) input and output,
        so the learner can eyeball the call.
        """
        raise NotImplementedError("TODO 3: record + print this generation (see docstring)")

    def end_trace(self) -> None:
        total = sum(r.cost_usd or 0.0 for r in self.records)
        print(
            f"[trace end] {self._name}  generations={len(self.records)}  "
            f"trace_cost={_fmt_cost(total)}"
        )

    def flush(self) -> None:
        # Nothing to flush — LocalTracer prints synchronously.
        pass


def _fmt_cost(cost: float | None) -> str:
    return f"${cost:.6f}" if cost is not None else "n/a"


# ---------------------------------------------------------------------------
# traced_chat — wraps provider.chat() and records a generation on ANY tracer.
# ---------------------------------------------------------------------------


def traced_chat(
    provider,
    messages: list[ChatMessage],
    tracer: Tracer,
    *,
    name: str = "chat",
) -> ChatResult:
    """Time provider.chat(), then record a generation on `tracer`.

    Works with the real provider OR, when no LLM is running, a deterministic fake
    result — so the tracing demo always completes. The call site never changes.
    """
    input_text = messages[-1].content if messages else ""
    t0 = time.perf_counter()

    try:
        result = provider.chat(messages)
    except Exception as e:
        # No live LLM? Fall back to a fake, deterministic result so the tracing
        # path is still exercised. (Real production code would let this raise.)
        result = _fake_chat_result(input_text, reason=str(e))

    latency_ms = (time.perf_counter() - t0) * 1000.0

    # TODO 2: Record this call on the tracer.
    #   a) Pull token counts from result.usage (result.usage.input_tokens /
    #      result.usage.output_tokens — either may be None).
    #   b) cost = estimate_cost(result.model, in_tok, out_tok)
    #   c) Build a GenerationRecord(name=name, model=result.model,
    #        input=input_text, output=result.text, input_tokens=in_tok,
    #        output_tokens=out_tok, latency_ms=latency_ms, cost_usd=cost)
    #   d) tracer.generation(rec)
    #   e) return result
    raise NotImplementedError(
        f"TODO 2: record this {latency_ms:.0f}ms call ({result.model}) "
        "on the tracer, then return result"
    )


def _fake_chat_result(question: str, *, reason: str = "") -> ChatResult:
    """Deterministic stand-in so the demo runs with no LLM and no network."""
    answer = f"[offline fake answer] I would answer: {question}"
    # Rough token estimates so cost math has something to chew on.
    return ChatResult(
        text=answer,
        model="gpt-4o-mini",  # a priced model so cost estimation is non-None
        usage=TokenUsage(
            input_tokens=max(1, len(question.split())),
            output_tokens=max(1, len(answer.split())),
        ),
    )


# ---------------------------------------------------------------------------
# Main — pick a tracer, run a few questions under ONE trace/session, summarise.
# ---------------------------------------------------------------------------


def _pick_tracer() -> tuple[Tracer, bool]:
    """LangfuseTracer if keys present, else LocalTracer. Returns (tracer, is_hosted)."""
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        return LangfuseTracer(), True
    return LocalTracer(), False


def main() -> None:
    tracer, is_hosted = _pick_tracer()

    if is_hosted:
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        print(f"[mode] Langfuse (hosted) — sending traces to {host}")
    else:
        print("[mode] LocalTracer (offline) — printing trace tree to stdout.")
        print("       Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (get free keys at")
        print("       https://cloud.langfuse.com) to send the same data to the hosted UI.")

    try:
        provider = get_provider()
    except Exception:
        provider = None  # no provider configured — the fake fallback covers it.

    class _NullProvider:
        def chat(self, messages):  # noqa: D401 - always fails -> fake result
            raise RuntimeError("no LLM configured")

    if provider is None:
        provider = _NullProvider()

    session_id = f"daily-qa-{uuid.uuid4().hex[:8]}"
    questions = [
        "What is 12 * 34?",
        "Name the capital of Japan.",
        "In one sentence, what is retrieval-augmented generation?",
    ]

    tracer.start_trace(name="daily-qa", session_id=session_id)

    try:
        for i, q in enumerate(questions, start=1):
            result = traced_chat(provider, [ChatMessage("user", q)], tracer, name=f"q{i}")
            print(f"Q{i}: {q}")
            print(f"A{i}: {result.text[:80]}")
    finally:
        tracer.end_trace()
        tracer.flush()

    # Session summary (works for LocalTracer; hosted UI shows the same numbers).
    if isinstance(tracer, LocalTracer):
        print("\n--- session cost summary ---")
        total = 0.0
        for rec in tracer.records:
            total += rec.cost_usd or 0.0
            print(f"  {rec.name:<4} {rec.model:<14} cost={_fmt_cost(rec.cost_usd)}")
        print(f"  {'TOTAL':<4} {'':<14} cost={_fmt_cost(total)}")
    else:
        print("\nDone — open the Langfuse UI and filter by session:", session_id)


if __name__ == "__main__":
    main()
