/**
 * Task 3 🟡 — Throughput vs latency: batching and concurrency.
 *
 * What you'll learn:
 *   - The difference between latency (single request) and throughput (many)
 *   - Time-to-first-token (TTFT): the most user-perceived metric in chat apps
 *   - How concurrent requests improve aggregate throughput
 *   - Why batching is fundamental for high-throughput serving
 *
 * Key insight: a single request gets the lowest latency by monopolising resources.
 * But aggregate throughput across all users is maximised by batching requests —
 * the weight-loading overhead is amortised.
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/03-throughput-latency.ts
 */

import { getProvider } from "@learn-ai/llm-core";

const PROMPT =
  "List 5 practical tips for writing clean, maintainable TypeScript code. " +
  "Be concise — one sentence per tip.";

const SHORT_PROMPT = "What is 2 + 2? Answer with just the number.";

// ---------------------------------------------------------------------------
// Time-to-first-token (TTFT)
// ---------------------------------------------------------------------------

/**
 * Measure the time from sending a request to receiving the FIRST token.
 *
 * Uses chatStream() to capture the exact moment the first chunk arrives.
 * TTFT is the dominant latency for interactive chat UIs.
 *
 * Returns elapsed milliseconds until the first token.
 *
 * TODO:
 *   1. Snapshot start = performance.now().
 *   2. Iterate provider.chatStream() over a single "user" message with
 *      `for await (const chunk of ...)`.
 *   3. The moment you see the FIRST non-empty chunk, snapshot the clock and
 *      break — don't drain the rest of the stream.
 *   4. Return the elapsed ms from start to that first chunk (the caller converts
 *      to seconds).
 */
async function measureTtft(
  prompt: string,
  provider: ReturnType<typeof getProvider>,
): Promise<number> {
  // TODO: implement measureTtft
  throw new Error("TODO: implement measureTtft()");
}

// ---------------------------------------------------------------------------
// Single-request latency
// ---------------------------------------------------------------------------

interface SingleResult {
  ttftS: number;
  totalS: number;
  tokensOut: number;
  tokensPerS: number;
}

/**
 * Measure total latency, TTFT, and tokens/sec for one request.
 *
 * TODO:
 *   1. Measure TTFT with measureTtft().
 *   2. Measure full request: performance.now() + provider.chat().
 *   3. Return { ttftS, totalS, tokensOut, tokensPerS }.
 */
async function measureSingleRequest(
  prompt: string,
  provider: ReturnType<typeof getProvider>,
): Promise<SingleResult> {
  // TODO: implement measureSingleRequest
  throw new Error("TODO: implement measureSingleRequest()");
}

// ---------------------------------------------------------------------------
// Concurrent requests
// ---------------------------------------------------------------------------

interface ConcurrentResult {
  n: number;
  wallClockS: number;
  totalTokens: number;
  aggregateTokensPerS: number;
}

/**
 * Fire `n` requests concurrently and measure aggregate throughput.
 *
 * Returns { n, wallClockS, totalTokens, aggregateTokensPerS }.
 *
 * TODO:
 *   1. Snapshot start = performance.now().
 *   2. Kick off n provider.chat() calls at once and await them together with
 *      Promise.all — keep each run short with a small maxTokens.
 *   3. Snapshot end; wallClockS is the difference in seconds.
 *   4. Sum the output tokens across all results.
 *   5. Return the ConcurrentResult (n / wallClockS / totalTokens /
 *      aggregateTokensPerS).
 */
async function measureConcurrent(
  prompt: string,
  provider: ReturnType<typeof getProvider>,
  n: number,
): Promise<ConcurrentResult> {
  // TODO: implement measureConcurrent
  throw new Error("TODO: implement measureConcurrent()");
}

// ---------------------------------------------------------------------------
// Latency table
// ---------------------------------------------------------------------------

/**
 * Print a table comparing single-request latency vs concurrent throughput.
 *
 * Columns: Concurrency | Wall-clock(s) | Total tokens | Agg. Tokens/sec
 *
 * TODO: print a header row and one row per result.
 */
function printLatencyTable(results: ConcurrentResult[]): void {
  // TODO: implement printLatencyTable
  throw new Error("TODO: implement printLatencyTable()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`Provider: ${provider.name} | Model: ${provider.chatModel}`);

  // Single-request baseline
  console.log("\n" + "=".repeat(60));
  console.log("SINGLE REQUEST BASELINE");
  console.log("=".repeat(60));
  try {
    const single = await measureSingleRequest(PROMPT, provider);
    console.log(`  TTFT           : ${single.ttftS.toFixed(3)}s`);
    console.log(`  Total latency  : ${single.totalS.toFixed(3)}s`);
    console.log(`  Output tokens  : ${single.tokensOut}`);
    console.log(`  Tokens/sec     : ${single.tokensPerS.toFixed(1)}`);
  } catch (e) {
    console.log(`  Skipped: ${e}`);
    return;
  }

  // Concurrent benchmark
  console.log("\n" + "=".repeat(60));
  console.log("CONCURRENT THROUGHPUT (N parallel requests)");
  console.log("=".repeat(60));

  const tableResults: ConcurrentResult[] = [];
  for (const n of [1, 2, 4, 8]) {
    try {
      process.stdout.write(`  n=${n}... `);
      const res = await measureConcurrent(SHORT_PROMPT, provider, n);
      console.log(
        `wall=${res.wallClockS.toFixed(2)}s  agg=${res.aggregateTokensPerS.toFixed(1)} tok/s`,
      );
      tableResults.push(res);
    } catch (e) {
      console.log(`skipped (${e})`);
    }
  }

  console.log();
  printLatencyTable(tableResults);

  console.log(
    "\nKey takeaway: concurrent requests increase aggregate throughput because",
    "\nthe model server can batch work. Wall-clock time grows sub-linearly with N.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
