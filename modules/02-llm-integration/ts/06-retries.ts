/**
 * Task 6 — Retries & errors 🟡
 *
 * What this teaches:
 *   - LLM APIs are remote HTTP calls; they fail with rate limits (429),
 *     server errors (500), and timeouts. Resilient code handles these.
 *   - Exponential backoff with jitter is the standard retry pattern:
 *     wait 2^attempt * base_ms + random jitter, doubling each retry.
 *   - The openai and anthropic SDKs already retry automatically (by default
 *     2 retries). This exercise teaches you the pattern explicitly so you
 *     can tune it, wrap non-SDK calls, or build higher-level retry policies.
 *   - Typed error handling: distinguish retriable errors (429, 503) from
 *     permanent ones (401 invalid key, 400 bad request) — don't retry the latter.
 *
 * How to run:
 *   pnpm tsx modules/02-llm-integration/ts/06-retries.ts
 */

import { getProvider, ChatMessage, ChatResult } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Error classification
// ---------------------------------------------------------------------------

export class LLMError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
    public readonly retriable: boolean = true,
  ) {
    super(message);
    this.name = "LLMError";
  }
}

// ---------------------------------------------------------------------------
// TODO 1: Implement isRetriable(error: unknown): boolean
//         Return true for:
//           - HTTP 429 (rate limit) — always retry
//           - HTTP 500, 502, 503, 504 (server errors) — usually transient
//         Return false for:
//           - HTTP 401 (bad API key) — retrying won't help
//           - HTTP 400 (bad request / invalid payload) — your bug, not theirs
//         Hint: openai and anthropic SDKs both attach `.status` to their errors.
//         Check `(error as any).status` or use instanceof checks.
// ---------------------------------------------------------------------------
function isRetriable(error: unknown): boolean {
  // TODO: implement
  if (error instanceof LLMError) return error.retriable;
  const status = (error as { status?: number }).status;
  if (status === undefined) return true; // network error — probably retriable
  return [429, 500, 502, 503, 504].includes(status);
}

// ---------------------------------------------------------------------------
// TODO 2: Implement withRetry<T>.
//         Parameters:
//           fn         — async function that may throw
//           maxRetries — max attempts after the first (default 3)
//           baseMs     — base delay in ms (default 500)
//         Algorithm:
//           1. Try fn().
//           2. On error: if !isRetriable(err) OR attempt >= maxRetries → rethrow.
//           3. Else: wait baseMs * 2^attempt + random(0..baseMs) ms.
//           4. Log the attempt number, wait time, and error message.
//           5. Retry.
// ---------------------------------------------------------------------------
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseMs = 500,
): Promise<T> {
  // TODO: implement
  // for (let attempt = 0; attempt <= maxRetries; attempt++) {
  //   try {
  //     return await fn();
  //   } catch (err) {
  //     if (attempt === maxRetries || !isRetriable(err)) throw err;
  //     const delay = baseMs * 2 ** attempt + Math.random() * baseMs;
  //     console.warn(`Attempt ${attempt + 1} failed (${(err as Error).message}). Retrying in ${delay.toFixed(0)}ms...`);
  //     await new Promise(r => setTimeout(r, delay));
  //   }
  // }
  // throw new Error("unreachable");
  throw new Error("withRetry not implemented yet — uncomment the block above");
}

// ---------------------------------------------------------------------------
// TODO 3: Implement chatWithRetry — a thin wrapper that calls withRetry
//         around a single llm.chat() call. Return the ChatResult.
// ---------------------------------------------------------------------------
async function chatWithRetry(
  messages: ChatMessage[],
  maxRetries = 3,
): Promise<ChatResult> {
  const llm = getProvider();
  // TODO: return withRetry(() => llm.chat(messages), maxRetries);
  return llm.chat(messages); // placeholder — replace with the line above
}

// ---------------------------------------------------------------------------
// Simulation helpers — let you test the retry logic without a real API error.
// ---------------------------------------------------------------------------

let callCount = 0;

/** Returns a function that fails the first `failTimes` calls with the given
 *  status code, then succeeds. Use it to test your retry logic offline. */
function makeFlaky(failTimes: number, statusCode: number) {
  return async (): Promise<string> => {
    callCount++;
    if (callCount <= failTimes) {
      const err = Object.assign(new Error(`Simulated ${statusCode}`), { status: statusCode });
      throw err;
    }
    return "success after retries";
  };
}

async function main() {
  console.log("=== Retry & error handling demo ===\n");

  // -------------------------------------------------------------------------
  // Test 1: flaky function that fails twice then succeeds (429 → retriable)
  // -------------------------------------------------------------------------
  console.log("Test 1: 2 rate-limit errors then success");
  callCount = 0;
  try {
    const result = await withRetry(makeFlaky(2, 429));
    console.log("Result:", result, "\n");
  } catch (err) {
    console.error("Failed:", err, "\n");
  }

  // -------------------------------------------------------------------------
  // Test 2: permanent error (401) — should NOT retry
  // -------------------------------------------------------------------------
  console.log("Test 2: permanent auth error (401) — should fail immediately");
  callCount = 0;
  try {
    await withRetry(makeFlaky(5, 401));
  } catch (err) {
    console.log(`Correctly failed without retrying: ${(err as Error).message}\n`);
  }

  // -------------------------------------------------------------------------
  // Test 3: real API call with retry wrapper
  // -------------------------------------------------------------------------
  console.log("Test 3: real API call (should succeed on first attempt)");
  try {
    const result = await chatWithRetry([
      { role: "user", content: "Say 'retry test passed' and nothing else." },
    ]);
    console.log("Response:", result.text);
    console.log("Model:", result.model, "\n");
  } catch (err) {
    console.error("Real call failed:", err);
  }

  // -------------------------------------------------------------------------
  // TODO 4 (stretch): Implement a circuit breaker that opens after N
  //         consecutive failures and refuses calls for a cooldown period.
  //         This prevents hammering an API that's completely down.
  // -------------------------------------------------------------------------
}

main().catch(console.error);
