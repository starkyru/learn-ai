"""test_agent_tools.py — deterministic fake tools + clock (exact assertions)."""

from __future__ import annotations

import agent_tools as at
import pytest


def _env(flaky: int = 0) -> at.AgentEnv:
    return at.AgentEnv(clock=at.Clock(), flaky_failures=flaky)


def test_clock_advances_deterministically() -> None:
    clock = at.Clock()
    assert clock.now() == 0
    clock.advance(3)
    clock.advance(2)
    assert clock.now() == 5


def test_lookup_is_readonly_and_idempotent() -> None:
    env = _env()
    r1 = at.run_tool("lookup_account", env, {"account_id": "acc-1"})
    r2 = at.run_tool("lookup_account", env, {"account_id": "acc-1"})
    assert r1 == {"account_id": "acc-1", "balance": 100, "owner": "owner@example.com"}
    assert r2 == r1
    assert env.effects == []  # read-only: no side effects
    assert env.clock.now() == 2  # two calls, latency 1 each


def test_lookup_unknown_account_raises() -> None:
    with pytest.raises(at.ToolError):
        at.run_tool("lookup_account", _env(), {"account_id": "acc-999"})


def test_flaky_fetch_fails_then_succeeds() -> None:
    env = _env(flaky=1)
    with pytest.raises(at.ToolError):
        at.run_tool("flaky_fetch", env, {"report": "daily"})  # 1st fails
    result = at.run_tool("flaky_fetch", env, {"report": "daily"})  # retry succeeds
    assert result == {"report": "daily", "status": "ok"}


def test_slow_query_times_out() -> None:
    with pytest.raises(at.ToolTimeout):
        at.run_tool("slow_query", _env(), {"query": "big"})


def test_send_email_records_one_effect() -> None:
    env = _env()
    result = at.run_tool("send_email", env, {"to": "a@b", "subject": "hi", "idempotency_key": "k1"})
    assert result["replayed"] is False
    assert env.effects == [{"type": "email", "to": "a@b", "subject": "hi", "idempotency_key": "k1"}]


def test_send_email_is_idempotent_per_key() -> None:
    env = _env()
    args = {"to": "a@b", "subject": "hi", "idempotency_key": "k1"}
    at.run_tool("send_email", env, args)
    replay = at.run_tool("send_email", env, args)  # duplicate SAME key
    assert replay["replayed"] is True
    assert len(env.effects) == 1  # exactly ONE effect from the duplicate


def test_send_email_different_keys_produce_two_effects() -> None:
    env = _env()
    at.run_tool("send_email", env, {"to": "a@b", "subject": "hi", "idempotency_key": "k1"})
    at.run_tool("send_email", env, {"to": "a@b", "subject": "hi", "idempotency_key": "k2"})
    assert len(env.effects) == 2


def test_send_email_without_key_never_dedups() -> None:
    # A missing/falsy idempotency key must NOT dedup: two keyless requests are
    # distinct effects, never collapsed into one "replay" by a falsy sentinel
    # (regression guard — a `None` key must not match a stored `None`).
    env = _env()
    first = at.run_tool("send_email", env, {"to": "a@b", "subject": "one"})
    second = at.run_tool("send_email", env, {"to": "a@b", "subject": "two"})
    assert first["replayed"] is False
    assert second["replayed"] is False
    assert len(env.effects) == 2


def test_tool_metadata_marks_side_effects() -> None:
    assert at.is_side_effecting("send_email") is True
    assert at.is_side_effecting("lookup_account") is False
