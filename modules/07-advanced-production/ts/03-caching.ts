/**
 * Task 3 — Caching & cost control 🟡
 *
 * What this teaches:
 *   - Many LLM requests are identical or near-identical. A prompt/response cache
 *     returns the stored answer instantly at zero model cost.
 *   - Cache keys are deterministic hashes of (model + messages + options) — if
 *     any field changes, you get a fresh response.
 *   - A running cost tracker lets you see exactly how much the cache is saving.
 *   - In production: semantic caching (embed the prompt, find the nearest cached
 *     response above a similarity threshold) handles paraphrased repeats too.
 *
 * How to run:
 *   pnpm tsx modules/07-advanced-production/ts/03-caching.ts
 */

import { getProvider, ChatMessage, ChatOptions, ChatResult } from "@learn-ai/llm-core";
import * as fs from "node:fs";
import * as path from "node:path";
import * as crypto from "node:crypto";

// ---------------------------------------------------------------------------
// Cache storage — JSONL file keyed by request hash
// ---------------------------------------------------------------------------

const CACHE_PATH = path.join(
  process.cwd(),
  "modules/07-advanced-production/prompt-cache.jsonl"
);

interface CacheEntry {
  key: string;
  model: string;
  messages: ChatMessage[];
  result: ChatResult;
  cachedAt: string;
}

// TODO 1: Implement loadCache().
//         Read CACHE_PATH line by line, parse each JSON entry, and return a
//         Map<string, CacheEntry> keyed by entry.key.
//         Return an empty Map if the file doesn't exist.

function loadCache(): Map<string, CacheEntry> {
  throw new Error("TODO: implement loadCache");
}

// TODO 2: Implement saveToCache(entry).
//         Append the entry as a JSON line to CACHE_PATH.

function saveToCache(entry: CacheEntry): void {
  throw new Error("TODO: implement saveToCache");
}

// ---------------------------------------------------------------------------
// Cache key
// ---------------------------------------------------------------------------

// TODO 3: Implement cacheKey(model, messages, options).
//         Hash the JSON-serialised (model + messages + options) with SHA-256.
//         Return the hex digest. This is the cache lookup key.

function cacheKey(
  model: string,
  messages: ChatMessage[],
  options?: ChatOptions
): string {
  throw new Error("TODO: implement cacheKey");
}

// ---------------------------------------------------------------------------
// Cost tracker
// ---------------------------------------------------------------------------

const COST_PER_1M: Record<string, { input: number; output: number }> = {
  "gpt-4o-mini":      { input: 0.15,  output: 0.60 },
  "claude-haiku-4-5": { input: 0.25,  output: 1.25 },
};

interface CostTracker {
  calls: number;
  cacheHits: number;
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
  savedCostUsd: number;
}

// TODO 4: Implement addCost(tracker, model, result, wasCacheHit).
//         Update tracker.calls and tracker.cacheHits.
//         If not a cache hit, add to inputTokens, outputTokens, and estimatedCostUsd.
//         If it WAS a cache hit, add the amount saved to tracker.savedCostUsd
//         (i.e., what the call would have cost if we hadn't cached it).

function addCost(
  tracker: CostTracker,
  model: string,
  result: ChatResult,
  wasCacheHit: boolean
): void {
  throw new Error("TODO: implement addCost");
}

// ---------------------------------------------------------------------------
// Cached chat
// ---------------------------------------------------------------------------

async function cachedChat(
  messages: ChatMessage[],
  options?: ChatOptions,
  tracker?: CostTracker
): Promise<{ result: ChatResult; cacheHit: boolean }> {
  const provider = getProvider();
  const cache = loadCache();
  const key = cacheKey(provider.chatModel, messages, options);

  // TODO 5: Check if key is in cache.
  //         If yes, log "[CACHE HIT]", update tracker if provided, return the
  //         cached result with cacheHit: true.
  //         If no, call provider.chat(), save the result to cache, update tracker,
  //         return with cacheHit: false.

  throw new Error("TODO: implement cachedChat");
}

// ---------------------------------------------------------------------------
// Main — demonstrate cache hits and savings
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`Provider: ${provider.name} / ${provider.chatModel}\n`);
  console.log(`Cache: ${CACHE_PATH}\n`);

  const tracker: CostTracker = {
    calls: 0,
    cacheHits: 0,
    inputTokens: 0,
    outputTokens: 0,
    estimatedCostUsd: 0,
    savedCostUsd: 0,
  };

  const questions = [
    "What is the capital of France?",
    "What is 12 * 34?",
    "What is the capital of France?", // should hit cache
    "What is 12 * 34?",               // should hit cache
    "What year was the Eiffel Tower built?",
  ];

  for (const q of questions) {
    const t0 = performance.now();
    const { result, cacheHit } = await cachedChat(
      [{ role: "user", content: q }],
      undefined,
      tracker
    );
    const ms = performance.now() - t0;
    const tag = cacheHit ? "[HIT] " : "[MISS]";
    console.log(`${tag} ${ms.toFixed(0).padStart(5)} ms | ${q}`);
    console.log(`       ${result.text.slice(0, 80)}\n`);
  }

  // TODO 6: Print a cost summary:
  //   - Total calls, cache hits, hit rate %
  //   - Input/output tokens used (excluding cache hits)
  //   - Estimated cost (USD) for the actual LLM calls
  //   - Estimated savings (USD) from cache hits
  console.log("--- Cost summary ---");
  console.log("TODO: print tracker stats.");
}

main().catch(console.error);
