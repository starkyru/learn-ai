/**
 * Task 6 🟢 — Routing, fallbacks & load testing.
 *
 * Running multiple LLM providers in production requires three pieces:
 *
 *   1. ROUTING — send easy queries to a cheap/fast model and hard queries to a
 *      stronger one. Correctly routing saves cost without sacrificing quality.
 *
 *   2. FALLBACKS — when a provider fails (timeout, rate limit, server error),
 *      automatically retry with the next provider in the list. This converts
 *      a single provider's reliability into a multi-provider SLA.
 *
 *   3. LOAD TESTING — measure what happens under concurrent load: requests per
 *      second, p50/p95 latency distribution, and error rate.
 *
 * What you'll learn:
 *   - Heuristic difficulty classification for query routing
 *   - Provider fallback chains with timeout handling
 *   - Concurrent request execution with Promise.all
 *   - Latency percentile (p50, p95) calculation
 *   - Reading throughput and error-rate metrics from a load test
 *
 * How to run:
 *   pnpm tsx modules/14-local-inference-optimization/ts/06-routing-fallbacks.ts
 */

import { getProvider, OpenAICompatibleProvider } from "@learn-ai/llm-core";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RoutingDecision {
  query: string;
  difficulty: "easy" | "hard";
  chosenModel: string;
  reason: string;
}

interface LoadTestResult {
  totalRequests: number;
  successCount: number;
  errorCount: number;
  elapsedMs: number;
  latenciesMs: number[];  // one per successful request
}

function throughputRps(r: LoadTestResult): number {
  return r.totalRequests / Math.max(r.elapsedMs / 1000, 1e-9);
}

function errorRate(r: LoadTestResult): number {
  return r.errorCount / Math.max(r.totalRequests, 1);
}

function percentile(latencies: number[], p: number): number {
  if (latencies.length === 0) return 0;
  const sorted = [...latencies].sort((a, b) => a - b);
  const idx = Math.min(Math.floor(sorted.length * p), sorted.length - 1);
  return sorted[idx];
}

// ---------------------------------------------------------------------------
// Step 1 — Difficulty classification
// ---------------------------------------------------------------------------

const HARD_KEYWORDS = [
  "explain", "compare", "analyse", "analyze", "design", "implement",
  "proof", "derive", "calculate", "optimise", "optimize", "refactor",
  "debug", "architecture", "tradeoff", "trade-off", "algorithm",
  "why does", "how does", "what would happen",
];

const EASY_KEYWORDS = [
  "what is", "define", "list", "name", "who is", "when was",
  "translate", "summarise", "summarize", "capital of",
];

// Model configuration
const EASY_MODEL = "llama3.2:1b";  // fast, cheap
const HARD_MODEL = "llama3.2";     // slower, stronger

/**
 * Classify a query as "easy" or "hard" using heuristics.
 *
 * TODO: implement this function.
 *
 * Heuristic rules (apply in order; first match wins):
 *   1. If the lowercased query contains any substring from HARD_KEYWORDS → "hard".
 *   2. If query.split(/\s+/).length > 20 → "hard".
 *   3. If (query.match(/\?/g) ?? []).length > 1 → "hard" (compound question).
 *   4. If the lowercased query contains any substring from EASY_KEYWORDS → "easy".
 *   5. Default → "easy".
 *
 * Returns "easy" | "hard".
 */
function classifyDifficulty(query: string): "easy" | "hard" {
  // TODO: implement classifyDifficulty
  throw new Error("TODO: implement classifyDifficulty()");
}

// ---------------------------------------------------------------------------
// Step 2 — Router
// ---------------------------------------------------------------------------

/**
 * Decide which model to use for `query`.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Call classifyDifficulty(query).
 *   2. If difficulty === "hard", chosenModel = HARD_MODEL.
 *      Else, chosenModel = EASY_MODEL.
 *   3. Build a human-readable reason string.
 *   4. Return a RoutingDecision.
 */
function route(query: string): RoutingDecision {
  // TODO: implement route
  throw new Error("TODO: implement route()");
}

// ---------------------------------------------------------------------------
// Step 3 — Provider fallback
// ---------------------------------------------------------------------------

/**
 * Try each provider in order. Return the first successful result.
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   For each provider in providers:
 *     1. Try:
 *          const result = await Promise.race([
 *            call(provider),
 *            new Promise((_, reject) =>
 *              setTimeout(() => reject(new Error("timeout")), timeoutMs)
 *            ),
 *          ]);
 *          Return [result, provider.name].
 *     2. On timeout or any error: console.warn(...) and continue to next provider.
 *
 *   If all providers fail, throw new Error("All providers failed.").
 *
 * `call` is an async function that takes a provider and returns a result.
 */
async function withFallback<T>(
  providers: ReturnType<typeof getProvider>[],
  call: (provider: ReturnType<typeof getProvider>) => Promise<T>,
  timeoutMs = 10_000,
): Promise<[T, string]> {
  // TODO: implement withFallback
  throw new Error("TODO: implement withFallback()");
}

// ---------------------------------------------------------------------------
// Step 4 — Load test
// ---------------------------------------------------------------------------

/**
 * Fire `n` total requests with `concurrency` concurrent workers.
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   1. Create a pool of `concurrency` worker slots using a semaphore pattern:
 *        const inFlight = { count: 0 };
 *        Use a simple task queue: build n Promise-returning tasks, then run
 *        them with a concurrency limiter.
 *
 *      Simpler approach (acceptable here):
 *        Divide n requests into batches of `concurrency`.
 *        For each batch, run Promise.all(batch.map(fn)) and collect results.
 *        This is not a true semaphore but demonstrates the concurrency concept.
 *
 *   2. Each task:
 *        a. Records start = performance.now().
 *        b. Calls: await fn()
 *        c. Records latency = performance.now() - start.
 *        d. Returns { ok: true, latencyMs: latency } on success.
 *        e. Returns { ok: false, latencyMs: 0 } on exception.
 *
 *   3. Record total elapsed time from before the first batch to after the last.
 *   4. Return LoadTestResult.
 *
 * `fn` is a zero-argument async function that makes one request.
 */
async function loadTest(
  fn: () => Promise<unknown>,
  concurrency: number,
  n: number,
): Promise<LoadTestResult> {
  // TODO: implement loadTest
  throw new Error("TODO: implement loadTest()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const SAMPLE_QUERIES = [
  "What is the capital of France?",
  "Define machine learning in one sentence.",
  "Who invented the telephone?",
  "Explain the tradeoffs between RAG and fine-tuning for a production chatbot.",
  "Design an architecture for a high-throughput LLM serving system that handles 10,000 RPS.",
  "Why does the KV cache reduce memory bandwidth in transformer inference?",
  "List three programming languages.",
  "Summarise what a neural network does.",
  "Compare and analyse the differences between quantization and distillation as model compression techniques.",
  "What year was Python first released?",
];

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Chat model: ${provider.chatModel}\n`);

  // ---------------------------------------------------------------------------
  // Part A: Routing demo
  // ---------------------------------------------------------------------------
  console.log("=".repeat(60));
  console.log("PART A — ROUTING");
  console.log("=".repeat(60));
  console.log(`\n${"Query".padEnd(55)} ${"Diff".padEnd(6)} Model`);
  console.log("-".repeat(78));
  for (const q of SAMPLE_QUERIES) {
    const decision = route(q);
    console.log(`  ${q.slice(0, 53).padEnd(53)}  ${decision.difficulty.padEnd(6)}  ${decision.chosenModel}`);
  }
  const easyCount = SAMPLE_QUERIES.filter((q) => route(q).difficulty === "easy").length;
  const hardCount = SAMPLE_QUERIES.length - easyCount;
  console.log(`\n  Easy: ${easyCount} → ${EASY_MODEL}  |  Hard: ${hardCount} → ${HARD_MODEL}`);

  // ---------------------------------------------------------------------------
  // Part B: Fallback demo
  // ---------------------------------------------------------------------------
  console.log("\n" + "=".repeat(60));
  console.log("PART B — FALLBACK");
  console.log("=".repeat(60));

  const primary = getProvider();
  const fallbackProvider = getProvider();
  const prompt = "Say 'fallback works' and nothing else.";

  const makeCall = async (p: ReturnType<typeof getProvider>): Promise<string> => {
    const result = await p.chat([{ role: "user", content: prompt }], { maxTokens: 10 });
    return result.text;
  };

  console.log("\nAttempting request with fallback chain [primary → fallback]...");
  try {
    const [result, usedProvider] = await withFallback(
      [primary, fallbackProvider],
      makeCall,
      30_000,
    );
    console.log(`  Success via '${usedProvider}': ${JSON.stringify(result.trim())}`);
  } catch (err) {
    console.log(`  All providers failed: ${err}`);
  }

  // ---------------------------------------------------------------------------
  // Part C: Load test
  // ---------------------------------------------------------------------------
  console.log("\n" + "=".repeat(60));
  console.log("PART C — LOAD TEST");
  console.log("=".repeat(60));

  const testPrompt = "Reply with exactly one word: OK.";
  const singleRequest = async () =>
    provider.chat([{ role: "user", content: testPrompt }], { maxTokens: 5 });

  for (const [concurrency, n] of [[1, 5], [3, 9]] as [number, number][]) {
    console.log(`\n  concurrency=${concurrency}, n=${n} requests...`);
    const ltResult = await loadTest(singleRequest, concurrency, n);
    console.log(`  Throughput  : ${throughputRps(ltResult).toFixed(2)} req/s`);
    console.log(`  p50 latency : ${percentile(ltResult.latenciesMs, 0.5).toFixed(0)} ms`);
    console.log(`  p95 latency : ${percentile(ltResult.latenciesMs, 0.95).toFixed(0)} ms`);
    console.log(
      `  Error rate  : ${(errorRate(ltResult) * 100).toFixed(1)}%  ` +
        `(${ltResult.errorCount}/${ltResult.totalRequests} failed)`,
    );
  }

  console.log(
    "\nKey insights:",
    "\n  1. Routing lets you serve cheap queries cheaply without sacrificing quality.",
    "\n  2. Fallbacks turn single-provider reliability into multi-provider SLAs.",
    "\n  3. Load tests reveal p95 latency spikes that p50 hides.",
    "\n  4. Concurrency > 1 improves throughput but may increase p95 latency.",
    "\n  5. Error rate under load tells you where your provider's limits are.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
