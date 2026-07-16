"""Reliability envelope around the model call (Task 3, framework-agnostic).

An LLM call is slow, remote, and fallible, so /ask does not call the provider
directly — it goes through :class:`ReliabilityEnvelope`, which composes, in order:

1. per-identity RATE LIMIT   → 429 when a caller exceeds its request budget;
2. CIRCUIT BREAKER           → 503 fast-fail while a provider outage is open;
3. CONCURRENCY LIMIT         → 503 when too many calls are already in flight;
4. per-request DEADLINE      → 504 when the total time budget is exhausted;
5. bounded RETRY             → retries a transient failure, then 502.

Everything that involves the passage of time (the breaker's cool-off, the rate
window) reads an injectable ``clock`` so tests are deterministic and never sleep.
The deadline itself is enforced with a real worker thread + ``Future.result``
timeout, because a provider ``chat`` is a blocking call that cannot be cancelled
cooperatively; a timed-out worker is abandoned (Python cannot kill a thread) but
the request returns a bounded 504 immediately regardless.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any, TypeVar

T = TypeVar("T")

Clock = Callable[[], float]

# States a circuit can be in. CLOSED = healthy, calls flow. OPEN = tripped, calls
# fast-fail without touching the provider. HALF_OPEN = probing, a single trial
# call is allowed; success closes the circuit, failure re-opens it.
CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class ReliabilityError(Exception):
    """Base for a bounded, mapped failure. ``status`` is the HTTP code to return;
    ``public`` is a short, safe reason (never a raw provider detail)."""

    status = 503
    public = "service unavailable"


class RateLimited(ReliabilityError):
    status = 429
    public = "rate limit exceeded"


class CircuitOpen(ReliabilityError):
    status = 503
    public = "service temporarily unavailable"


class ConcurrencyLimited(ReliabilityError):
    status = 503
    public = "service busy"


class DeadlineExceeded(ReliabilityError):
    status = 504
    public = "upstream timeout"


class ProviderUnavailable(ReliabilityError):
    status = 502
    public = "upstream error"


class CircuitBreaker:
    """A failure-counting circuit breaker with a timed cool-off.

    Opens after ``failure_threshold`` consecutive failures. While OPEN, ``allow``
    returns False until ``cooldown_s`` has elapsed, then transitions to HALF_OPEN
    and allows a single probe. A success in HALF_OPEN (or CLOSED) resets the
    failure count and closes; a failure in HALF_OPEN re-opens immediately.
    """

    def __init__(
        self, *, failure_threshold: int, cooldown_s: float, clock: Clock = time.monotonic
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_s
        self._clock = clock
        self._lock = threading.Lock()
        self._state = CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def allow(self) -> bool:
        """True if a call may proceed. May transition OPEN → HALF_OPEN on cool-off."""
        with self._lock:
            if self._state == OPEN and self._clock() - self._opened_at >= self._cooldown:
                self._state = HALF_OPEN
            return self._state in (CLOSED, HALF_OPEN)

    def record_success(self) -> None:
        with self._lock:
            self._state = CLOSED
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            # A failed probe in HALF_OPEN re-opens straight away; otherwise trip
            # once the consecutive-failure count reaches the threshold.
            if self._state == HALF_OPEN:
                self._trip_locked()
                return
            self._failures += 1
            if self._failures >= self._threshold:
                self._trip_locked()

    def _trip_locked(self) -> None:
        self._state = OPEN
        self._opened_at = self._clock()
        self._failures = self._threshold

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {"state": self._state, "failures": self._failures}


class RateLimiter:
    """Per-key fixed-window request limiter.

    Allows at most ``max_per_window`` calls per ``window_s`` for each key. The
    window is keyed on ``floor(now / window_s)`` so it advances without a timer.
    Stale keys are pruned opportunistically once the table grows past a soft cap,
    so a stream of distinct keys cannot leak memory unbounded.
    """

    _SOFT_CAP = 4096

    def __init__(
        self, *, max_per_window: int, window_s: float, clock: Clock = time.monotonic
    ) -> None:
        self._max = max_per_window
        self._window = window_s
        self._clock = clock
        self._lock = threading.Lock()
        # key -> (window_index, count)
        self._buckets: dict[str, tuple[int, int]] = {}

    def allow(self, key: str) -> bool:
        window = int(self._clock() // self._window)
        with self._lock:
            if len(self._buckets) > self._SOFT_CAP:
                self._prune_locked(window)
            index, count = self._buckets.get(key, (window, 0))
            if index != window:
                index, count = window, 0  # a new window resets the count
            if count >= self._max:
                self._buckets[key] = (index, count)
                return False
            self._buckets[key] = (index, count + 1)
            return True

    def _prune_locked(self, current_window: int) -> None:
        stale = [k for k, (index, _) in self._buckets.items() if index != current_window]
        for k in stale:
            del self._buckets[k]


class ReliabilityEnvelope:
    """Compose rate limit, circuit breaker, concurrency cap, deadline, and retry.

    ``call(fn, key=...)`` runs ``fn`` (the provider call) under the full envelope
    and returns its result, or raises a :class:`ReliabilityError` subclass mapped
    to an HTTP status. Only genuine provider failures (a timeout or a raised
    exception during the call) count toward the circuit; a rate-limit, open
    circuit, or concurrency rejection never trips the breaker further.
    """

    def __init__(
        self,
        *,
        timeout_s: float,
        max_concurrency: int,
        max_retries: int,
        breaker: CircuitBreaker,
        rate_limiter: RateLimiter,
        executor: ThreadPoolExecutor | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        retriable: Callable[[Exception], bool] | None = None,
        base_backoff_s: float = 0.05,
    ) -> None:
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._breaker = breaker
        self._rate = rate_limiter
        self._sleeper = sleeper
        self._retriable = retriable or (lambda _exc: True)
        self._base_backoff = base_backoff_s
        # One worker per allowed concurrent call, so a submitted call never queues
        # behind the concurrency cap; the semaphore is the actual admission gate.
        self._executor = executor or ThreadPoolExecutor(
            max_workers=max_concurrency, thread_name_prefix="m07b-provider"
        )
        self._slots = threading.BoundedSemaphore(max_concurrency)

    def call(self, fn: Callable[[], T], *, key: str) -> T:
        if not self._rate.allow(key):
            raise RateLimited
        if not self._breaker.allow():
            raise CircuitOpen
        if not self._slots.acquire(blocking=False):
            raise ConcurrencyLimited
        try:
            result = self._run_with_retry(fn)
        except (DeadlineExceeded, ProviderUnavailable):
            self._breaker.record_failure()
            raise
        else:
            self._breaker.record_success()
            return result
        finally:
            self._slots.release()

    def _run_with_retry(self, fn: Callable[[], T]) -> T:
        # A single deadline budget spans every retry, so total time is bounded by
        # timeout_s no matter how many attempts run.
        deadline_at = time.monotonic() + self._timeout
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            remaining = deadline_at - time.monotonic()
            if remaining <= 0:
                raise DeadlineExceeded from last_exc
            future: Future = self._executor.submit(fn)
            try:
                return future.result(timeout=remaining)
            except FutureTimeoutError as exc:
                # Budget exhausted mid-call: abandon the worker, fail bounded.
                future.cancel()
                raise DeadlineExceeded from exc
            except Exception as exc:  # noqa: BLE001 — the provider call's failure
                last_exc = exc
                if attempt >= self._max_retries or not self._retriable(exc):
                    raise ProviderUnavailable from exc
                # Back off, but never sleep past the deadline.
                backoff = min(
                    self._base_backoff * (2**attempt), max(deadline_at - time.monotonic(), 0)
                )
                if backoff > 0:
                    self._sleeper(backoff)
        # Unreachable: the loop always returns or raises. Guard for type-checkers.
        raise ProviderUnavailable from last_exc

    def snapshot(self) -> dict[str, Any]:
        """A metrics view: circuit state + how many concurrency slots are free."""
        snap = self._breaker.snapshot()
        snap["free_slots"] = self._slots._value  # type: ignore[attr-defined]
        return snap

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def build_envelope(settings: Any, *, clock: Clock = time.monotonic) -> ReliabilityEnvelope:
    """Construct the envelope from :class:`~m07b_service.config.Settings`."""
    breaker = CircuitBreaker(
        failure_threshold=settings.circuit_failure_threshold,
        cooldown_s=settings.circuit_cooldown_s,
        clock=clock,
    )
    rate_limiter = RateLimiter(
        max_per_window=settings.rate_limit_per_minute, window_s=60.0, clock=clock
    )
    return ReliabilityEnvelope(
        timeout_s=settings.request_timeout_s,
        max_concurrency=settings.provider_max_concurrency,
        max_retries=settings.provider_max_retries,
        breaker=breaker,
        rate_limiter=rate_limiter,
    )
