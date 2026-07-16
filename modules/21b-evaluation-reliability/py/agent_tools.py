"""agent_tools.py — deterministic fake tools + clock (Module 21b, Task 4).

Three fake tools plus an injectable deterministic clock, so an agent trajectory
can be replayed and evaluated offline with no LLM and no network:

- ``lookup_account`` — a READ-ONLY, idempotent lookup (safe).
- ``flaky_fetch``    — a transient-failure tool that raises ``ToolError`` for the
                       first ``flaky_failures`` calls, then succeeds (drives retry).
- ``slow_query``     — always raises ``ToolTimeout`` (drives timeout handling).
- ``send_email``     — a SIDE-EFFECTING action that records the effect and is
                       idempotent per ``idempotency_key`` (a duplicate key
                       produces exactly ONE effect).

Every call advances the injected clock (latency) and adds a fixed cost, so the
report's latency/cost are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ToolError(Exception):
    """A transient tool failure the agent is expected to retry."""


class ToolTimeout(Exception):
    """The tool exceeded its deadline; the agent must handle it safely."""


class Clock:
    """Injectable deterministic clock (integer ticks); no wall-clock time."""

    def __init__(self, start: int = 0) -> None:
        self.t = int(start)

    def now(self) -> int:
        return self.t

    def advance(self, dt: int) -> None:
        self.t += int(dt)


@dataclass
class AgentEnv:
    clock: Clock
    flaky_failures: int = 0
    effects: list[dict[str, Any]] = field(default_factory=list)
    idempotency: dict[str, dict[str, Any]] = field(default_factory=dict)
    call_counts: dict[str, int] = field(default_factory=dict)


# Tool metadata: whether it is a side-effecting action, its cost, and latency.
TOOLS: dict[str, dict[str, Any]] = {
    "lookup_account": {"side_effecting": False, "cost": 1, "latency": 1},
    "flaky_fetch": {"side_effecting": False, "cost": 1, "latency": 2},
    "slow_query": {"side_effecting": False, "cost": 1, "latency": 5},
    "send_email": {"side_effecting": True, "cost": 2, "latency": 3},
}

_ACCOUNTS: dict[str, dict[str, Any]] = {
    "acc-1": {"balance": 100, "owner": "owner@example.com"},
}


def is_known_tool(name: str) -> bool:
    return name in TOOLS


def is_side_effecting(name: str) -> bool:
    return bool(TOOLS.get(name, {}).get("side_effecting", False))


def run_tool(name: str, env: AgentEnv, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a fake tool against the env. Raises ToolError / ToolTimeout for the
    failure/timeout tools. Deterministic and offline."""
    meta = TOOLS[name]
    env.clock.advance(meta["latency"])
    env.call_counts[name] = env.call_counts.get(name, 0) + 1

    if name == "lookup_account":
        account = _ACCOUNTS.get(args.get("account_id"))
        if account is None:
            raise ToolError(f"unknown account {args.get('account_id')!r}")
        return {"account_id": args["account_id"], **account}

    if name == "flaky_fetch":
        if env.flaky_failures > 0:
            env.flaky_failures -= 1
            raise ToolError("transient failure")
        return {"report": args.get("report"), "status": "ok"}

    if name == "slow_query":
        raise ToolTimeout("tool exceeded its deadline")

    if name == "send_email":
        key = args.get("idempotency_key")
        # Only a TRUTHY key dedups. A missing/falsy key means NO dedup, so two
        # distinct keyless requests each produce their own effect (a falsy
        # sentinel must never collapse unrelated requests into one "replay").
        if key and key in env.idempotency:
            return {**env.idempotency[key], "replayed": True}
        env.effects.append(
            {
                "type": "email",
                "to": args.get("to"),
                "subject": args.get("subject"),
                "idempotency_key": key,
            }
        )
        stored = {"type": "email", "effect_id": len(env.effects)}
        if key:
            env.idempotency[key] = stored
        return {**stored, "replayed": False}

    raise ToolError(f"unknown tool {name!r}")
