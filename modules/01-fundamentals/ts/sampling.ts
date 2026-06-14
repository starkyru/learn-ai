/**
 * sampling.ts — greedy / temperature / top-k / top-p sampling (Task 4, 🔴 STUB).
 *
 * What it teaches:
 *   How a model's raw output (logits) becomes the next token. The four
 *   strategies here are exactly the temperature / top_k / top_p knobs you set on
 *   every API call. See README Concept 4 for the math. Fill in the TODOs.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/01-fundamentals/ts/sampling.ts
 */

// A toy logit vector over a 6-token vocabulary. Index 2 is the clear favourite.
const LOGITS = [2.0, 1.0, 4.0, 0.5, 3.0, -1.0];

/** A tiny seeded PRNG (mulberry32) so sampling runs are reproducible. */
function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Turn logits into a probability distribution, optionally temperatured.
 * p_i = exp(logit_i / T) / Σ_j exp(logit_j / T). Stable (subtracts the max).
 * (Provided for you — use it below.)
 */
export function softmax(logits: number[], temperature = 1.0): number[] {
  const scaled = logits.map((x) => x / temperature);
  const m = Math.max(...scaled);
  const exps = scaled.map((x) => Math.exp(x - m));
  const total = exps.reduce((a, b) => a + b, 0);
  return exps.map((e) => e / total);
}

/**
 * Sample an index from a probability distribution `probs`. Provided helper —
 * walk a cumulative sum until it exceeds a uniform random draw.
 */
export function sampleFromProbs(probs: number[], rng: () => number): number {
  const r = rng();
  let acc = 0;
  for (let i = 0; i < probs.length; i++) {
    acc += probs[i];
    if (r < acc) return i;
  }
  return probs.length - 1; // numerical safety net
}

/**
 * Return the index of the highest-logit token. Deterministic, no randomness.
 * TODO: return the argmax of `logits`.
 */
export function greedy(_logits: number[]): number {
  throw new Error("Implement greedy (argmax) — see the docstring TODO.");
}

/**
 * Sample from softmax(logits / temperature).
 * TODO: probs = softmax(logits, temperature); return sampleFromProbs(probs, rng).
 * Lower T -> sharper distribution -> picks the top token more often.
 */
export function sampleTemperature(_logits: number[], _temperature: number, _rng: () => number): number {
  throw new Error("Implement temperature sampling — see the TODO.");
}

/**
 * Top-k: keep the k highest-logit tokens, renormalise over them, sample.
 * TODO:
 *   1. Find the indices of the top-k logits.
 *   2. Build a distribution over ONLY those k (softmax of their logits, or
 *      zero the rest and renormalise).
 *   3. Sample an index — it must always be one of the top-k.
 */
export function sampleTopK(_logits: number[], _k: number, _rng: () => number): number {
  throw new Error("Implement top-k sampling — see the TODOs.");
}

/**
 * Top-p (nucleus): keep the smallest set whose cumulative probability ≥ p,
 * renormalise, sample.
 * TODO:
 *   1. probs = softmax(logits).
 *   2. Sort tokens by probability descending (track original indices).
 *   3. Accumulate until the running sum ≥ p (always keep at least the top-1).
 *   4. Renormalise over the kept set and sample — the result must be a kept token.
 */
export function sampleTopP(_logits: number[], _p: number, _rng: () => number): number {
  throw new Error("Implement top-p (nucleus) sampling — see the TODOs.");
}

function main(): void {
  const rng = makeRng(42);
  console.log("Logits     :", LOGITS);
  console.log(
    "Probabilities (T=1):",
    softmax(LOGITS).map((p) => Number(p.toFixed(3))),
  );
  console.log();
  console.log("greedy             ->", greedy(LOGITS));
  console.log("temperature(T=0.5) ->", sampleTemperature(LOGITS, 0.5, rng));
  console.log("temperature(T=2.0) ->", sampleTemperature(LOGITS, 2.0, rng));
  console.log("top_k(k=2)         ->", sampleTopK(LOGITS, 2, rng));
  console.log("top_p(p=0.9)       ->", sampleTopP(LOGITS, 0.9, rng));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
