"""
Task 6 — Harden the loop: stop conditions, failure detection, idempotency  🟡

What this teaches:
  - A naive agent loop exits only when the model stops emitting tool calls.
    A production harness needs *engineered* exits: an iteration cap, a
    wall-clock timeout, and a goal-completion predicate that is DISTINCT from
    "the model produced a terminal message" (a terminal message may be a
    clarifying question, not success).
  - Failure detection: an agent that calls the SAME tool with IDENTICAL
    arguments over and over (or oscillates A/B/A/B between two calls) is
    stuck. Detect it and exit early with a diagnostic instead of burning the
    remaining budget.
  - Idempotency for side-effecting tools: a retried `send_email` must not
    send twice. Assign a stable idempotency key per logical call and dedupe
    at execution time. This is HARNESS-level engineering — the model never
    sees the key.
  - Determinism: the timeout branch is tested with an injected FAKE clock (a
    counter the harness advances), not real sleeps.

How to run:
  uv run python modules/06-agents/py/06_harden_loop.py --stub   # offline, deterministic
  uv run python modules/06-agents/py/06_harden_loop.py          # real model via get_provider()

The `--stub` path replays scripted tool-call decisions through YOUR guarded
loop — no network, no key, exact assertions. The real path drives the same
loop with a live model through llm_core (never a hardcoded vendor).
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from llm_core import ChatMessage, ChatOptions, get_provider

# ---------------------------------------------------------------------------
# Core types  (provided — do not edit)
# ---------------------------------------------------------------------------


@dataclass
class Decision:
    """One model turn: EITHER a tool call (tool + args) OR a terminal message."""

    tool: str | None = None
    args: dict[str, Any] | None = None
    message: str | None = None


@dataclass
class HardenedTool:
    name: str
    execute: Callable[[dict[str, Any]], str]


class TransientToolError(Exception):
    """A tool failure that is safe to retry (network blip, 429, timeout)."""


@dataclass
class LoopResult:
    """What the guarded loop reports back to the caller.

    status is one of:
      "success"        — terminal message AND goal_check(message) is True
      "incomplete"     — terminal message but goal_check is False
                         (e.g. the model asked a clarifying question)
      "stuck"          — detect_stuck fired; diagnostic explains why
      "timeout"        — wall-clock budget exceeded (per the injected clock)
      "max_iterations" — iteration cap reached without a terminal message
    """

    status: str
    final_message: str | None
    iterations: int
    diagnostic: str | None = None


# ---------------------------------------------------------------------------
# Clocks  (provided — do not edit)
# ---------------------------------------------------------------------------


class FakeClock:
    """Deterministic clock: every now() call returns the current time, then
    advances it by `step` seconds. No real time passes — the timeout branch
    becomes exactly testable. The loop contract: call now() ONCE to record
    the start time, then ONCE at the top of each iteration."""

    def __init__(self, step: float = 0.0) -> None:
        self.t = 0.0
        self.step = step

    def now(self) -> float:
        current = self.t
        self.t += self.step
        return current


class SystemClock:
    """Real wall-clock time, for the live (non---stub) path."""

    def now(self) -> float:
        return time.monotonic()


# ---------------------------------------------------------------------------
# Tools  (provided — do not edit)
# ---------------------------------------------------------------------------


def make_tools(
    fail_first_send: bool = False,
) -> tuple[dict[str, HardenedTool], list[dict[str, str]], dict[str, int]]:
    """Build a fresh tool set per scenario.

    Returns (tools, outbox, stats):
      - `search` returns canned text (read-only, safe to repeat).
      - `send_email` appends to `outbox` — a SIDE EFFECT. With
        fail_first_send=True the FIRST attempt raises TransientToolError
        before anything is sent (the flaky wrapper).
      - `stats` counts send_email attempts/failures so the harness can prove
        how many times the side effect was really tried.
    """
    outbox: list[dict[str, str]] = []
    stats = {"send_attempts": 0, "send_failures": 0}
    failures_left = 1 if fail_first_send else 0

    def search(args: dict[str, Any]) -> str:
        query = str(args.get("query", "")).lower().strip()
        if "eiffel" in query:
            return "The Eiffel Tower is 330 metres tall."
        if "population of france" in query:
            return "France has a population of ~68 million (2024)."
        if "capital of france" in query:
            return "The capital of France is Paris."
        return f"No result found for: {query}"

    def send_email(args: dict[str, Any]) -> str:
        nonlocal failures_left
        stats["send_attempts"] += 1
        if failures_left > 0:
            failures_left -= 1
            stats["send_failures"] += 1
            raise TransientToolError("SMTP connection dropped before send (safe to retry)")
        to = str(args.get("to", ""))
        outbox.append({"to": to, "subject": str(args.get("subject", ""))})
        return f"email sent to {to}"

    tools = {
        "search": HardenedTool("search", search),
        "send_email": HardenedTool("send_email", send_email),
    }
    return tools, outbox, stats


# ---------------------------------------------------------------------------
# Models  (provided — do not edit)
# ---------------------------------------------------------------------------


class StubModel:
    """Replays a fixed script of Decisions, ignoring the history. This is the
    deterministic fake model: each scenario scripts exactly what a (mis)behaving
    model would do, so YOUR guards are the only thing under test."""

    def __init__(self, script: list[Decision]) -> None:
        self.script = list(script)

    def decide(self, history: list[str]) -> Decision:
        if not self.script:
            return Decision(message="(stub script exhausted)")
        return self.script.pop(0)


class LiveModel:
    """The real path: asks the provider (via llm_core) to emit ONE JSON object
    per turn — {"tool": ..., "args": {...}} or {"message": ...} — and parses it
    into a Decision. Never a hardcoded vendor."""

    def __init__(self, goal: str) -> None:
        self.provider = get_provider()
        self.goal = goal

    def decide(self, history: list[str]) -> Decision:
        system = (
            "You control tools by replying with EXACTLY ONE JSON object and nothing else.\n"
            'To call a tool: {"tool": "<name>", "args": {...}}\n'
            "Tools:\n"
            '  search — looks up a fact. args: {"query": "<text>"}\n'
            '  send_email — sends an email. args: {"to": "<addr>", "subject": "<text>"}\n'
            'Only when the goal is fully accomplished, reply: {"message": "<short summary>"}'
        )
        transcript = "\n".join(history) if history else "(nothing yet)"
        user = f"Goal: {self.goal}\n\nWhat happened so far:\n{transcript}\n\nNext JSON:"
        result = self.provider.chat(
            [ChatMessage("system", system), ChatMessage("user", user)],
            ChatOptions(temperature=0, max_tokens=300),
        )
        text = result.text
        try:
            payload = json.loads(text[text.index("{") : text.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            return Decision(message=text.strip())
        if isinstance(payload, dict) and payload.get("tool"):
            return Decision(tool=str(payload["tool"]), args=dict(payload.get("args") or {}))
        if isinstance(payload, dict) and "message" in payload:
            return Decision(message=str(payload["message"]))
        return Decision(message=text.strip())


# ---------------------------------------------------------------------------
# Core functions — YOU implement these four
# ---------------------------------------------------------------------------


def idempotency_key(tool_name: str, args: dict[str, Any]) -> str:
    """A STABLE key identifying one logical tool call.

    Two calls with the same tool and the same arguments must produce the same
    key even if the args dict was built in a different insertion order —
    and different arguments must produce different keys. This key is used
    both as the "signature" for stuck detection and as the dedupe key for
    side-effecting tools.

    TODO: implement.
      - Combine the tool name and a canonical JSON rendering of `args` into
        one string. `json.dumps` has a flag that sorts object keys — that is
        what makes the key insertion-order-stable.
    """
    # TODO: implement the stable key
    raise NotImplementedError("TODO: implement idempotency_key()")


def detect_stuck(recent_calls: list[str], window: int = 3) -> str | None:
    """Detect a stuck agent from its recent call signatures.

    Two classic signals:
      1. Repetition — the last `window` signatures are all IDENTICAL.
      2. Oscillation — the last 4 signatures alternate A, B, A, B between
         two DISTINCT calls.

    Return a human-readable diagnostic string when stuck, else None.

    TODO: implement.
      - Repetition: with at least `window` calls, look at the last `window`
        signatures; if they are all the same value, return a diagnostic that
        names the repeated signature.
      - Oscillation: with at least 4 calls, take the last 4; if positions
        1 & 3 match, positions 2 & 4 match, and the two values differ,
        return a diagnostic naming both signatures.
      - Otherwise (including too few calls) return None.
    """
    # TODO: implement repetition + oscillation detection
    raise NotImplementedError("TODO: implement detect_stuck()")


def execute_with_retry(tool: HardenedTool, args: dict[str, Any], executed: dict[str, str]) -> str:
    """Execute a tool with (a) at-most-once side effects and (b) one retry.

    - If this call's idempotency key is already in `executed`, do NOT run the
      tool again — return the recorded result.
    - Otherwise run it; on TransientToolError retry ONCE (a second failure
      propagates to the caller).
    - Record the successful result under the key before returning it.

    TODO: implement.
      - Compute this call's key with idempotency_key().
      - Dedupe: if the key is already in `executed`, return the recorded
        result WITHOUT running the tool again.
      - Run tool.execute(args) inside try/except catching ONLY
        TransientToolError; on that error call it once more (a second
        failure propagates to the caller).
      - Store the successful result in `executed` under the key, return it.
    """
    # TODO: implement dedupe + single retry
    raise NotImplementedError("TODO: implement execute_with_retry()")


def run_agent_loop(
    model: StubModel | LiveModel,
    tools: dict[str, HardenedTool],
    goal_check: Callable[[str], bool],
    *,
    max_iterations: int,
    max_seconds: float,
    clock: FakeClock | SystemClock,
) -> LoopResult:
    """The guarded agent loop.

    Contract per iteration i = 1..max_iterations:
      1. Timeout guard: if clock.now() - start > max_seconds, return
         LoopResult("timeout", ...). Record `start` with ONE clock.now() call
         before the loop; call now() exactly ONCE per iteration.
      2. decision = model.decide(history).
      3. Terminal message? Then goal_check(message) decides between
         "success" and "incomplete" (terminal message != goal complete).
      4. Tool call: append its idempotency_key signature to recent_calls,
         run detect_stuck — if it fires, return "stuck" with the diagnostic
         BEFORE executing (don't waste the call).
      5. Otherwise execute via execute_with_retry and append the action +
         observation to `history`.
    Falls out of the loop -> "max_iterations".

    Tips:
      - State to initialise before the loop: a `history: list[str]`
        transcript, a `recent_calls: list[str]` of signatures, an
        `executed: dict[str, str]` dedupe map, and the recorded start time.
      - An unknown tool name should append an error observation to `history`
        and continue — not crash.
      - The "stuck" LoopResult carries detect_stuck's diagnostic; every
        LoopResult carries the iteration number it exited on.
    """
    # TODO: implement the guarded loop per the contract in the docstring
    raise NotImplementedError("TODO: implement run_agent_loop()")


# ---------------------------------------------------------------------------
# Scenario harness  (provided — do not edit)
# ---------------------------------------------------------------------------

SEND_ARGS = {"to": "learner@example.com", "subject": "Eiffel Tower height"}


def run_scenario(
    name: str,
    script: list[Decision],
    tools: dict[str, HardenedTool],
    goal_check: Callable[[str], bool],
    *,
    max_iterations: int = 10,
    max_seconds: float = 1000.0,
    clock: FakeClock | None = None,
) -> LoopResult:
    result = run_agent_loop(
        StubModel(script),
        tools,
        goal_check,
        max_iterations=max_iterations,
        max_seconds=max_seconds,
        clock=clock or FakeClock(step=1.0),
    )
    print(f"  [{name}]")
    print(
        f"    status={result.status!r} iterations={result.iterations}"
        + (f" diagnostic={result.diagnostic!r}" if result.diagnostic else "")
    )
    return result


def run_stub_scenarios() -> None:
    print("=== Task 6: harden the loop — STUB (offline) ===\n")
    print("Scenarios:")

    # ── A. Clean success: search -> send_email -> terminal, goal met ────────
    tools_a, outbox_a, _ = make_tools()
    r_success = run_scenario(
        "success",
        [
            Decision(tool="search", args={"query": "eiffel tower height"}),
            Decision(tool="send_email", args=dict(SEND_ARGS)),
            Decision(message="Done — I looked up the height and emailed it."),
        ],
        tools_a,
        lambda _msg: len(outbox_a) == 1,  # goal = the email really went out
    )

    # ── B. Terminal message that is NOT success (clarifying question) ───────
    tools_b, outbox_b, _ = make_tools()
    r_clarify = run_scenario(
        "clarifying question",
        [
            Decision(tool="search", args={"query": "eiffel tower height"}),
            Decision(message="Which email address should I send the answer to?"),
        ],
        tools_b,
        lambda _msg: len(outbox_b) == 1,
    )

    # ── C. Stuck: the identical search repeated 3x (cap is 10) ──────────────
    tools_c, _, _ = make_tools()
    r_stuck = run_scenario(
        "stuck (repetition)",
        [
            Decision(tool="search", args={"query": "eiffel tower height"}),
            Decision(tool="search", args={"query": "how tall is the eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            # padding — never reached if detect_stuck fires at iteration 5:
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
            Decision(tool="search", args={"query": "eiffel tower"}),
        ],
        tools_c,
        lambda _msg: False,
    )

    # ── D. Stuck: A/B/A/B oscillation between two distinct calls ────────────
    tools_d, _, _ = make_tools()
    osc_a = Decision(tool="search", args={"query": "capital of france"})
    osc_b = Decision(tool="search", args={"query": "population of france"})
    r_osc = run_scenario(
        "stuck (oscillation)",
        [osc_a, osc_b, osc_a, osc_b, osc_a, osc_b, osc_a, osc_b],
        tools_d,
        lambda _msg: False,
    )

    # ── E. Timeout via the fake clock (10s per tick, 35s budget) ────────────
    tools_e, _, _ = make_tools()
    r_timeout = run_scenario(
        "timeout (fake clock)",
        [Decision(tool="search", args={"query": f"fact {i}"}) for i in range(12)],
        tools_e,
        lambda _msg: False,
        max_iterations=50,
        max_seconds=35.0,
        clock=FakeClock(step=10.0),
    )

    # ── F. Idempotency: transient failure + retry + duplicate call ──────────
    # First send_email attempt raises TransientToolError (nothing sent), the
    # retry succeeds. The model then re-issues the SAME logical call with the
    # args in a different key order — the harness must dedupe it.
    tools_f, outbox_f, stats_f = make_tools(fail_first_send=True)
    r_idem = run_scenario(
        "idempotency (flaky send_email)",
        [
            Decision(tool="search", args={"query": "eiffel tower height"}),
            Decision(tool="send_email", args=dict(SEND_ARGS)),
            Decision(
                tool="send_email",
                args={"subject": SEND_ARGS["subject"], "to": SEND_ARGS["to"]},
            ),
            Decision(message="The report email has been sent."),
        ],
        tools_f,
        lambda _msg: len(outbox_f) == 1,
    )
    print(f"    outbox={outbox_f} send_attempts={stats_f['send_attempts']}")

    # ── Key stability (unit check) ───────────────────────────────────────────
    k1 = idempotency_key("send_email", {"a": 1, "b": [2, 3]})
    k2 = idempotency_key("send_email", {"b": [2, 3], "a": 1})
    k3 = idempotency_key("send_email", {"a": 1, "b": [2, 4]})

    # ── Acceptance ───────────────────────────────────────────────────────────
    checks: list[tuple[bool, str]] = [
        (
            r_success.status == "success" and r_success.iterations == 3 and len(outbox_a) == 1,
            "success run: goal_check saw the sent email -> status 'success' in 3 iterations",
        ),
        (
            r_clarify.status == "incomplete" and len(outbox_b) == 0,
            "clarifying terminal message -> status 'incomplete' (terminal message != success)",
        ),
        (
            r_stuck.status == "stuck" and r_stuck.iterations == 5 and bool(r_stuck.diagnostic),
            f"stuck (repetition) exits at iteration {r_stuck.iterations} of cap 10 "
            "with a diagnostic",
        ),
        (
            r_osc.status == "stuck" and r_osc.iterations == 4,
            "stuck (A/B/A/B oscillation) exits at iteration 4 with a diagnostic",
        ),
        (
            r_timeout.status == "timeout" and r_timeout.iterations < 50,
            "timeout run exits via the fake clock, well before the iteration cap",
        ),
        (
            r_idem.status == "success" and len(outbox_f) == 1 and stats_f["send_attempts"] == 2,
            "idempotency: EXACTLY 1 email in the outbox (1 transient failure + 1 retry; "
            "duplicate call deduped)",
        ),
        (
            k1 == k2 and k1 != k3,
            "idempotency_key is arg-order-stable and argument-sensitive",
        ),
    ]

    print("\nAcceptance:")
    for ok, label in checks:
        print(f"  [{'x' if ok else ' '}] {label}")
    if all(ok for ok, _ in checks):
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


def run_live() -> None:
    print("=== Task 6: harden the loop — REAL (get_provider) ===\n")
    tools, outbox, stats = make_tools(fail_first_send=True)
    goal = (
        "Find the height of the Eiffel Tower with the search tool, email it to "
        "learner@example.com with the send_email tool, then reply with a short summary."
    )
    model = LiveModel(goal)
    print(f"Provider: {model.provider.name} / {model.provider.chat_model}")
    result = run_agent_loop(
        model,
        tools,
        lambda _msg: len(outbox) >= 1,
        max_iterations=10,
        max_seconds=120.0,
        clock=SystemClock(),
    )
    print(f"\nstatus={result.status!r} iterations={result.iterations}")
    if result.final_message:
        print(f"final message: {result.final_message}")
    if result.diagnostic:
        print(f"diagnostic: {result.diagnostic}")
    print(f"outbox: {outbox} (send attempts: {stats['send_attempts']})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Harden the agent loop (Task 6).")
    ap.add_argument("--stub", action="store_true", help="offline deterministic scripted model")
    args = ap.parse_args()
    if args.stub:
        run_stub_scenarios()
    else:
        run_live()


if __name__ == "__main__":
    main()
