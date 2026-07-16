/**
 * Unit tests for the reliability envelope (Task 3), deterministic + offline.
 *
 * Mirrors test_07b_reliability.py. The breaker and rate limiter read an
 * injectable clock (milliseconds), so cool-off and window transitions are tested
 * by advancing a fake clock, never by sleeping. The deadline and concurrency
 * behaviours use real timers/promises but with tiny bounds so they finish fast.
 */

import {
  CircuitBreaker,
  CircuitOpen,
  CLOSED,
  ConcurrencyLimited,
  DeadlineExceeded,
  HALF_OPEN,
  OPEN,
  ProviderUnavailable,
  RateLimited,
  RateLimiter,
  ReliabilityEnvelope,
} from "../src/reliability.js";

/** A hand-advanced monotonic clock (milliseconds). */
class FakeClock {
  t = 0;
  now = (): number => this.t;
  advance(dt: number): void {
    this.t += dt;
  }
}

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (err?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function makeEnvelope(
  overrides: {
    timeoutMs?: number;
    maxConcurrency?: number;
    maxRetries?: number;
    failureThreshold?: number;
    cooldownMs?: number;
    ratePerWindow?: number;
    clock?: () => number;
    retriable?: (err: unknown) => boolean;
  } = {},
): ReliabilityEnvelope {
  const clock = overrides.clock ?? (() => performance.now());
  const breaker = new CircuitBreaker(
    overrides.failureThreshold ?? 3,
    overrides.cooldownMs ?? 10_000,
    clock,
  );
  const rateLimiter = new RateLimiter(overrides.ratePerWindow ?? 1000, 60_000, clock);
  return new ReliabilityEnvelope({
    timeoutMs: overrides.timeoutMs ?? 5000,
    maxConcurrency: overrides.maxConcurrency ?? 4,
    maxRetries: overrides.maxRetries ?? 0,
    breaker,
    rateLimiter,
    sleeper: async () => {}, // no real backoff sleep in tests
    retriable: overrides.retriable,
  });
}

// ── CircuitBreaker ──────────────────────────────────────────────────────────

test("circuit opens after threshold consecutive failures", () => {
  const clk = new FakeClock();
  const cb = new CircuitBreaker(3, 10_000, clk.now);
  expect(cb.allow()).toBe(true);
  cb.recordFailure();
  cb.recordFailure();
  expect(cb.allow()).toBe(true); // 2 < 3, still closed
  cb.recordFailure(); // 3rd consecutive -> trips
  expect(cb.allow()).toBe(false);
  expect(cb.snapshot().state).toBe(OPEN);
});

test("open circuit blocks until cooldown then half-opens", () => {
  const clk = new FakeClock();
  const cb = new CircuitBreaker(1, 10_000, clk.now);
  cb.recordFailure(); // opens at t=0
  expect(cb.allow()).toBe(false);
  clk.advance(9_990);
  expect(cb.allow()).toBe(false); // cool-off not elapsed
  clk.advance(20); // now >= 10_000
  expect(cb.allow()).toBe(true); // a single half-open probe is allowed
  expect(cb.snapshot().state).toBe(HALF_OPEN);
});

test("half-open success closes the circuit", () => {
  const clk = new FakeClock();
  const cb = new CircuitBreaker(1, 5_000, clk.now);
  cb.recordFailure();
  clk.advance(5_000);
  expect(cb.allow()).toBe(true); // half-open
  cb.recordSuccess();
  expect(cb.snapshot().state).toBe(CLOSED);
  expect(cb.allow()).toBe(true);
});

test("half-open failure reopens and restarts the cooldown", () => {
  const clk = new FakeClock();
  const cb = new CircuitBreaker(2, 5_000, clk.now);
  cb.recordFailure();
  cb.recordFailure(); // opens at t=0
  clk.advance(5_000);
  expect(cb.allow()).toBe(true); // half-open probe
  cb.recordFailure(); // probe fails -> reopen at t=5_000
  expect(cb.allow()).toBe(false);
  clk.advance(4_990);
  expect(cb.allow()).toBe(false); // cool-off restarted from the reopen
  clk.advance(20);
  expect(cb.allow()).toBe(true);
});

test("a success resets the consecutive-failure count", () => {
  const cb = new CircuitBreaker(3, 5_000);
  cb.recordFailure();
  cb.recordFailure();
  cb.recordSuccess(); // clears the streak
  cb.recordFailure();
  cb.recordFailure();
  expect(cb.allow()).toBe(true); // 2 < 3 because the count reset
  expect(cb.snapshot().failures).toBe(2);
});

// ── RateLimiter ───────────────────────────────────────────────────────────

test("rate limiter allows up to max then blocks in a window", () => {
  const clk = new FakeClock();
  const limiter = new RateLimiter(2, 60_000, clk.now);
  expect(limiter.allow("u1")).toBe(true);
  expect(limiter.allow("u1")).toBe(true);
  expect(limiter.allow("u1")).toBe(false); // 3rd in the same window
});

test("rate limiter resets on a new window", () => {
  const clk = new FakeClock();
  const limiter = new RateLimiter(1, 60_000, clk.now);
  expect(limiter.allow("u1")).toBe(true);
  expect(limiter.allow("u1")).toBe(false);
  clk.advance(60_000); // next window index
  expect(limiter.allow("u1")).toBe(true);
});

test("rate limiter isolates keys", () => {
  const clk = new FakeClock();
  const limiter = new RateLimiter(1, 60_000, clk.now);
  expect(limiter.allow("u1")).toBe(true);
  expect(limiter.allow("u2")).toBe(true); // different identity, own budget
  expect(limiter.allow("u1")).toBe(false);
});

// ── ReliabilityEnvelope ─────────────────────────────────────────────────────

test("envelope returns the result on success", async () => {
  const env = makeEnvelope();
  await expect(env.call(async () => "ok", "u1")).resolves.toBe("ok");
  expect(env.snapshot().state).toBe(CLOSED);
});

test("envelope rate limits per identity", async () => {
  const env = makeEnvelope({ ratePerWindow: 1 });
  await expect(env.call(async () => "ok", "u1")).resolves.toBe("ok");
  await expect(env.call(async () => "ok", "u1")).rejects.toBeInstanceOf(RateLimited);
});

test("envelope raises DeadlineExceeded on a slow call", async () => {
  const env = makeEnvelope({ timeoutMs: 50 });
  await expect(
    env.call(async () => {
      await sleep(500);
      return "late";
    }, "u1"),
  ).rejects.toBeInstanceOf(DeadlineExceeded);
});

test("deadline wins even if the abandoned call later rejects (no unhandled rejection)", async () => {
  const env = makeEnvelope({ timeoutMs: 20, maxRetries: 0 });
  await expect(
    env.call(async () => {
      await sleep(100);
      throw new Error("late rejection");
    }, "u1"),
  ).rejects.toBeInstanceOf(DeadlineExceeded);
  // Let the abandoned promise reject; the guard must swallow it, not crash.
  await sleep(150);
});

test("envelope retries a transient failure then succeeds", async () => {
  let n = 0;
  const flaky = async (): Promise<string> => {
    n += 1;
    if (n < 3) throw new Error("transient");
    return "recovered";
  };
  const env = makeEnvelope({ maxRetries: 3 });
  await expect(env.call(flaky, "u1")).resolves.toBe("recovered");
  expect(n).toBe(3);
});

test("envelope exhausts retries then rejects ProviderUnavailable", async () => {
  let n = 0;
  const alwaysFail = async (): Promise<never> => {
    n += 1;
    throw new Error("down");
  };
  const env = makeEnvelope({ maxRetries: 2 });
  await expect(env.call(alwaysFail, "u1")).rejects.toBeInstanceOf(ProviderUnavailable);
  expect(n).toBe(3); // 1 initial + 2 retries
});

test("envelope does not retry a non-retriable error", async () => {
  let n = 0;
  const fail = async (): Promise<never> => {
    n += 1;
    throw new TypeError("permanent");
  };
  const env = makeEnvelope({
    maxRetries: 5,
    retriable: (err) => !(err instanceof TypeError),
  });
  await expect(env.call(fail, "u1")).rejects.toBeInstanceOf(ProviderUnavailable);
  expect(n).toBe(1); // classified non-retriable -> tried once
});

test("envelope opens the circuit on an outage then recovers after cool-off", async () => {
  const clk = new FakeClock();
  const down = async (): Promise<never> => {
    throw new Error("outage");
  };
  const env = makeEnvelope({
    maxRetries: 0,
    failureThreshold: 1,
    cooldownMs: 10_000,
    clock: clk.now,
  });
  await expect(env.call(down, "u1")).rejects.toBeInstanceOf(ProviderUnavailable);
  // Circuit open: the next call fast-fails WITHOUT invoking the provider (a
  // CircuitOpen, not a ProviderUnavailable, proves down() was not called).
  await expect(env.call(down, "u1")).rejects.toBeInstanceOf(CircuitOpen);
  clk.advance(10_000); // cool-off elapses
  await expect(env.call(async () => "ok", "u1")).resolves.toBe("ok"); // half-open probe
  expect(env.snapshot().state).toBe(CLOSED);
});

test("envelope rejects over the concurrency cap", async () => {
  const gate = deferred<string>();
  const env = makeEnvelope({ maxConcurrency: 1, timeoutMs: 5000 });
  const holder = env.call(() => gate.promise, "u1"); // holds the single slot in-flight
  try {
    await expect(env.call(async () => "quick", "u2")).rejects.toBeInstanceOf(
      ConcurrencyLimited,
    );
  } finally {
    gate.resolve("done");
    await holder;
  }
});
