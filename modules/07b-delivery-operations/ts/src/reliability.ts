/**
 * Reliability envelope around the model call (Task 3, framework-agnostic).
 *
 * An LLM call is slow, remote, and fallible, so /ask does not call the provider
 * directly — it goes through `ReliabilityEnvelope`, which composes, in order:
 *
 *   1. per-identity RATE LIMIT   → 429 when a caller exceeds its request budget;
 *   2. CIRCUIT BREAKER           → 503 fast-fail while a provider outage is open;
 *   3. CONCURRENCY LIMIT         → 503 when too many calls are already in flight;
 *   4. per-request DEADLINE      → 504 when the total time budget is exhausted;
 *   5. bounded RETRY             → retries a transient failure, then 502.
 *
 * The Python port (`reliability.py`) is the structural twin; the only difference
 * is unit — this side works in milliseconds (JS convention) and awaits a Promise
 * rather than driving a worker thread. Everything time-based (the breaker
 * cool-off, the rate window) reads an injectable `clock`, so tests advance time
 * deterministically and never sleep. A deadline is enforced with `Promise.race`;
 * the losing provider promise cannot be cancelled, so it is abandoned while the
 * request returns a bounded 504 immediately.
 */

/** Monotonic clock in MILLISECONDS. */
export type Clock = () => number;

export const CLOSED = "closed";
export const OPEN = "open";
export const HALF_OPEN = "half_open";
export type CircuitState = typeof CLOSED | typeof OPEN | typeof HALF_OPEN;

const defaultClock: Clock = () => performance.now();

/** A bounded, mapped failure. `status` is the HTTP code; `reason` names the mode. */
export class ReliabilityError extends Error {
  readonly status: number = 503;
  constructor(
    readonly reason: string,
    message?: string,
  ) {
    super(message ?? reason);
    this.name = "ReliabilityError";
  }
}

export class RateLimited extends ReliabilityError {
  override readonly status = 429;
  constructor() {
    super("RateLimited", "rate limit exceeded");
  }
}

export class CircuitOpen extends ReliabilityError {
  override readonly status = 503;
  constructor() {
    super("CircuitOpen", "service temporarily unavailable");
  }
}

export class ConcurrencyLimited extends ReliabilityError {
  override readonly status = 503;
  constructor() {
    super("ConcurrencyLimited", "service busy");
  }
}

export class DeadlineExceeded extends ReliabilityError {
  override readonly status = 504;
  constructor() {
    super("DeadlineExceeded", "upstream timeout");
  }
}

export class ProviderUnavailable extends ReliabilityError {
  override readonly status = 502;
  constructor(cause?: unknown) {
    super("ProviderUnavailable", "upstream error");
    this.cause = cause;
  }
}

/**
 * A failure-counting circuit breaker with a timed cool-off. Opens after
 * `failureThreshold` consecutive failures; while OPEN, `allow()` returns false
 * until `cooldownMs` has elapsed, then a single HALF_OPEN probe is allowed. A
 * success closes; a failure in HALF_OPEN re-opens immediately.
 */
export class CircuitBreaker {
  private state: CircuitState = CLOSED;
  private failures = 0;
  private openedAt = 0;

  constructor(
    private readonly failureThreshold: number,
    private readonly cooldownMs: number,
    private readonly clock: Clock = defaultClock,
  ) {}

  allow(): boolean {
    if (this.state === OPEN && this.clock() - this.openedAt >= this.cooldownMs) {
      this.state = HALF_OPEN;
    }
    return this.state === CLOSED || this.state === HALF_OPEN;
  }

  recordSuccess(): void {
    this.state = CLOSED;
    this.failures = 0;
  }

  recordFailure(): void {
    // A failed HALF_OPEN probe re-opens straight away; otherwise trip once the
    // consecutive-failure count reaches the threshold.
    if (this.state === HALF_OPEN) {
      this.trip();
      return;
    }
    this.failures += 1;
    if (this.failures >= this.failureThreshold) this.trip();
  }

  private trip(): void {
    this.state = OPEN;
    this.openedAt = this.clock();
    this.failures = this.failureThreshold;
  }

  snapshot(): { state: CircuitState; failures: number } {
    return { state: this.state, failures: this.failures };
  }
}

/**
 * Per-key fixed-window request limiter. Allows at most `maxPerWindow` calls per
 * `windowMs` for each key, keyed on `floor(now / windowMs)` so it advances
 * without a timer. Stale keys are pruned once the table grows past a soft cap,
 * so a stream of distinct keys cannot leak memory unbounded.
 */
export class RateLimiter {
  private static readonly SOFT_CAP = 4096;
  private readonly buckets = new Map<string, { index: number; count: number }>();

  constructor(
    private readonly maxPerWindow: number,
    private readonly windowMs: number,
    private readonly clock: Clock = defaultClock,
  ) {}

  allow(key: string): boolean {
    const window = Math.floor(this.clock() / this.windowMs);
    if (this.buckets.size > RateLimiter.SOFT_CAP) this.prune(window);
    const bucket = this.buckets.get(key);
    let count = bucket && bucket.index === window ? bucket.count : 0;
    if (count >= this.maxPerWindow) {
      this.buckets.set(key, { index: window, count });
      return false;
    }
    count += 1;
    this.buckets.set(key, { index: window, count });
    return true;
  }

  private prune(currentWindow: number): void {
    for (const [key, bucket] of this.buckets) {
      if (bucket.index !== currentWindow) this.buckets.delete(key);
    }
  }
}

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

export interface EnvelopeOptions {
  timeoutMs: number;
  maxConcurrency: number;
  maxRetries: number;
  breaker: CircuitBreaker;
  rateLimiter: RateLimiter;
  /** Injected in tests so retry backoff does not really wait. */
  sleeper?: (ms: number) => Promise<void>;
  retriable?: (err: unknown) => boolean;
  baseBackoffMs?: number;
}

/**
 * Compose rate limit, circuit breaker, concurrency cap, deadline, and retry.
 * `call(fn, key)` runs `fn` (the provider call) under the full envelope and
 * resolves its result, or rejects with a `ReliabilityError` subclass mapped to
 * an HTTP status. Only genuine provider failures (a timeout or a rejection
 * during the call) count toward the circuit.
 */
export class ReliabilityEnvelope {
  private readonly timeoutMs: number;
  private readonly maxConcurrency: number;
  private readonly maxRetries: number;
  private readonly breaker: CircuitBreaker;
  private readonly rate: RateLimiter;
  private readonly sleeper: (ms: number) => Promise<void>;
  private readonly retriable: (err: unknown) => boolean;
  private readonly baseBackoffMs: number;
  private inFlight = 0;

  constructor(options: EnvelopeOptions) {
    this.timeoutMs = options.timeoutMs;
    this.maxConcurrency = options.maxConcurrency;
    this.maxRetries = options.maxRetries;
    this.breaker = options.breaker;
    this.rate = options.rateLimiter;
    this.sleeper = options.sleeper ?? sleep;
    this.retriable = options.retriable ?? (() => true);
    this.baseBackoffMs = options.baseBackoffMs ?? 50;
  }

  async call<T>(fn: () => Promise<T>, key: string): Promise<T> {
    if (!this.rate.allow(key)) throw new RateLimited();
    if (!this.breaker.allow()) throw new CircuitOpen();
    if (this.inFlight >= this.maxConcurrency) throw new ConcurrencyLimited();
    this.inFlight += 1;
    try {
      const result = await this.runWithRetry(fn);
      this.breaker.recordSuccess();
      return result;
    } catch (err) {
      if (err instanceof DeadlineExceeded || err instanceof ProviderUnavailable) {
        this.breaker.recordFailure();
      }
      throw err;
    } finally {
      this.inFlight -= 1;
    }
  }

  private async runWithRetry<T>(fn: () => Promise<T>): Promise<T> {
    // A single deadline budget spans every retry, so total time is bounded by
    // timeoutMs no matter how many attempts run. `performance.now()` (real time)
    // drives the deadline; the injectable clock only governs breaker/rate state.
    const deadlineAt = performance.now() + this.timeoutMs;
    let lastErr: unknown;
    for (let attempt = 0; attempt <= this.maxRetries; attempt += 1) {
      const remaining = deadlineAt - performance.now();
      if (remaining <= 0) throw new DeadlineExceeded();
      try {
        return await this.withDeadline(fn, remaining);
      } catch (err) {
        if (err instanceof DeadlineExceeded) throw err;
        lastErr = err;
        if (attempt >= this.maxRetries || !this.retriable(err)) {
          throw new ProviderUnavailable(err);
        }
        const backoff = Math.min(
          this.baseBackoffMs * 2 ** attempt,
          Math.max(deadlineAt - performance.now(), 0),
        );
        if (backoff > 0) await this.sleeper(backoff);
      }
    }
    // Unreachable: the loop always returns or throws.
    throw new ProviderUnavailable(lastErr);
  }

  private withDeadline<T>(fn: () => Promise<T>, ms: number): Promise<T> {
    let timer: ReturnType<typeof setTimeout>;
    const timeout = new Promise<never>((_resolve, reject) => {
      timer = setTimeout(() => reject(new DeadlineExceeded()), ms);
    });
    const call = fn();
    // If the deadline wins the race, `call` is abandoned but still pending; a
    // later rejection would surface as an unhandledRejection. Swallow it — the
    // deadline result is already what the caller gets.
    call.catch(() => {});
    // Clear the timer whichever side wins, so a resolved call leaves no pending
    // handle (which would keep the event loop — and tests — alive).
    return Promise.race([call, timeout]).finally(() => clearTimeout(timer));
  }

  snapshot(): { state: CircuitState; failures: number; inFlight: number } {
    return { ...this.breaker.snapshot(), inFlight: this.inFlight };
  }
}

/** Construct the envelope from a Config. */
export function buildEnvelope(
  config: {
    requestTimeoutMs: number;
    providerMaxConcurrency: number;
    rateLimitPerMinute: number;
    providerMaxRetries: number;
    circuitFailureThreshold: number;
    circuitCooldownMs: number;
  },
  clock: Clock = defaultClock,
): ReliabilityEnvelope {
  const breaker = new CircuitBreaker(
    config.circuitFailureThreshold,
    config.circuitCooldownMs,
    clock,
  );
  const rateLimiter = new RateLimiter(config.rateLimitPerMinute, 60_000, clock);
  return new ReliabilityEnvelope({
    timeoutMs: config.requestTimeoutMs,
    maxConcurrency: config.providerMaxConcurrency,
    maxRetries: config.providerMaxRetries,
    breaker,
    rateLimiter,
  });
}
