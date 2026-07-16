"""Unit tests for the reliability envelope (Task 3), fully offline + deterministic.

The circuit breaker and rate limiter read an injectable clock, so cool-off and
window transitions are tested by advancing a fake clock — never by sleeping. The
deadline and concurrency behaviours use real worker threads (a blocking call
cannot be cancelled cooperatively), but with tiny bounds so they finish fast.

Imports only ``m07b_service.reliability`` (stdlib-backed), so this file runs on
base deps without the FastAPI ``production`` extra.
"""

from __future__ import annotations

import threading
import time

import pytest
from m07b_service import reliability as rel


class FakeClock:
    """A hand-advanced monotonic clock (seconds)."""

    def __init__(self, t: float = 0.0) -> None:
        self.t = float(t)

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


# ── CircuitBreaker ──────────────────────────────────────────────────────────


def test_circuit_opens_after_threshold_consecutive_failures():
    clk = FakeClock()
    cb = rel.CircuitBreaker(failure_threshold=3, cooldown_s=10, clock=clk)
    assert cb.allow() is True
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is True  # 2 < 3, still closed
    cb.record_failure()  # 3rd consecutive -> trips
    assert cb.allow() is False
    assert cb.snapshot()["state"] == rel.OPEN


def test_open_circuit_blocks_until_cooldown_then_half_opens():
    clk = FakeClock()
    cb = rel.CircuitBreaker(failure_threshold=1, cooldown_s=10, clock=clk)
    cb.record_failure()  # opens at t=0
    assert cb.allow() is False
    clk.advance(9.99)
    assert cb.allow() is False  # cool-off not elapsed
    clk.advance(0.02)  # now >= 10
    assert cb.allow() is True  # a single half-open probe is allowed
    assert cb.snapshot()["state"] == rel.HALF_OPEN


def test_half_open_success_closes_the_circuit():
    clk = FakeClock()
    cb = rel.CircuitBreaker(failure_threshold=1, cooldown_s=5, clock=clk)
    cb.record_failure()
    clk.advance(5)
    assert cb.allow() is True  # half-open
    cb.record_success()
    assert cb.snapshot()["state"] == rel.CLOSED
    assert cb.allow() is True


def test_half_open_failure_reopens_and_restarts_cooldown():
    clk = FakeClock()
    cb = rel.CircuitBreaker(failure_threshold=2, cooldown_s=5, clock=clk)
    cb.record_failure()
    cb.record_failure()  # opens at t=0
    clk.advance(5)
    assert cb.allow() is True  # half-open probe
    cb.record_failure()  # probe fails -> reopen immediately at t=5
    assert cb.allow() is False
    clk.advance(4.99)
    assert cb.allow() is False  # cool-off restarted from the reopen
    clk.advance(0.02)
    assert cb.allow() is True


def test_success_resets_the_consecutive_failure_count():
    cb = rel.CircuitBreaker(failure_threshold=3, cooldown_s=5)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()  # a good call clears the streak
    cb.record_failure()
    cb.record_failure()
    assert cb.allow() is True  # 2 < 3 because the count reset
    assert cb.snapshot()["failures"] == 2


# ── RateLimiter ─────────────────────────────────────────────────────────────


def test_rate_limiter_allows_up_to_max_then_blocks_in_window():
    clk = FakeClock()
    limiter = rel.RateLimiter(max_per_window=2, window_s=60, clock=clk)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False  # 3rd in the same 60s window


def test_rate_limiter_resets_on_a_new_window():
    clk = FakeClock()
    limiter = rel.RateLimiter(max_per_window=1, window_s=60, clock=clk)
    assert limiter.allow("u1") is True
    assert limiter.allow("u1") is False
    clk.advance(60)  # next window index
    assert limiter.allow("u1") is True


def test_rate_limiter_isolates_keys():
    clk = FakeClock()
    limiter = rel.RateLimiter(max_per_window=1, window_s=60, clock=clk)
    assert limiter.allow("u1") is True
    assert limiter.allow("u2") is True  # different identity, own budget
    assert limiter.allow("u1") is False


# ── ReliabilityEnvelope ─────────────────────────────────────────────────────


@pytest.fixture
def envelopes():
    """Factory for envelopes; every one is closed (worker pool) at teardown."""
    created: list[rel.ReliabilityEnvelope] = []

    def _make(
        *,
        timeout_s: float = 5.0,
        max_concurrency: int = 4,
        max_retries: int = 0,
        failure_threshold: int = 3,
        cooldown_s: float = 10.0,
        rate_per_window: int = 1000,
        clock=time.monotonic,
        retriable=None,
    ) -> rel.ReliabilityEnvelope:
        breaker = rel.CircuitBreaker(
            failure_threshold=failure_threshold, cooldown_s=cooldown_s, clock=clock
        )
        limiter = rel.RateLimiter(max_per_window=rate_per_window, window_s=60, clock=clock)
        env = rel.ReliabilityEnvelope(
            timeout_s=timeout_s,
            max_concurrency=max_concurrency,
            max_retries=max_retries,
            breaker=breaker,
            rate_limiter=limiter,
            sleeper=lambda _s: None,  # no real backoff sleep in tests
            retriable=retriable,
        )
        created.append(env)
        return env

    yield _make
    for env in created:
        env.close()


def test_envelope_returns_result_on_success(envelopes):
    env = envelopes()
    assert env.call(lambda: "ok", key="u1") == "ok"
    assert env.snapshot()["state"] == rel.CLOSED


def test_envelope_rate_limits_per_identity(envelopes):
    env = envelopes(rate_per_window=1)
    assert env.call(lambda: "ok", key="u1") == "ok"
    with pytest.raises(rel.RateLimited):
        env.call(lambda: "ok", key="u1")


def test_envelope_deadline_exceeded_on_slow_call(envelopes):
    env = envelopes(timeout_s=0.05)
    with pytest.raises(rel.DeadlineExceeded):
        env.call(lambda: time.sleep(0.5) or "late", key="u1")


def test_envelope_retries_a_transient_failure_then_succeeds(envelopes):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "recovered"

    env = envelopes(max_retries=3)
    assert env.call(flaky, key="u1") == "recovered"
    assert calls["n"] == 3  # failed twice, third attempt succeeded


def test_envelope_exhausts_retries_then_provider_unavailable(envelopes):
    calls = {"n": 0}

    def always_fail():
        calls["n"] += 1
        raise RuntimeError("down")

    env = envelopes(max_retries=2)
    with pytest.raises(rel.ProviderUnavailable):
        env.call(always_fail, key="u1")
    assert calls["n"] == 3  # 1 initial + 2 retries


def test_envelope_does_not_retry_a_non_retriable_error(envelopes):
    calls = {"n": 0}

    def fail():
        calls["n"] += 1
        raise ValueError("permanent")

    env = envelopes(max_retries=5, retriable=lambda exc: not isinstance(exc, ValueError))
    with pytest.raises(rel.ProviderUnavailable):
        env.call(fail, key="u1")
    assert calls["n"] == 1  # classified non-retriable -> tried once


def test_envelope_circuit_opens_on_outage_then_recovers_after_cooldown(envelopes):
    clk = FakeClock()

    def down():
        raise RuntimeError("outage")

    env = envelopes(max_retries=0, failure_threshold=1, cooldown_s=10, clock=clk)
    with pytest.raises(rel.ProviderUnavailable):
        env.call(down, key="u1")  # provider fails -> circuit trips
    # Circuit is open: the next call fast-fails WITHOUT invoking the provider
    # (a CircuitOpen, not a ProviderUnavailable, proves down() was not called).
    with pytest.raises(rel.CircuitOpen):
        env.call(down, key="u1")
    clk.advance(10)  # cool-off elapses
    assert env.call(lambda: "ok", key="u1") == "ok"  # half-open probe succeeds
    assert env.snapshot()["state"] == rel.CLOSED


def test_envelope_rejects_over_the_concurrency_cap(envelopes):
    entered = threading.Event()
    release = threading.Event()

    def blocking():
        entered.set()
        release.wait(timeout=5)
        return "done"

    env = envelopes(max_concurrency=1, timeout_s=5)
    holder = threading.Thread(target=lambda: env.call(blocking, key="u1"))
    holder.start()
    try:
        assert entered.wait(timeout=5)  # the single slot is now held in-flight
        with pytest.raises(rel.ConcurrencyLimited):
            env.call(lambda: "quick", key="u2")
    finally:
        release.set()
        holder.join(timeout=5)
