/**
 * uncertainty.ts — paired comparison, bootstrap CI, release verdict (Task 3).
 *
 * A byte-for-byte port of uncertainty.py: the same seeded LCG (full-product
 * modulo, high-bit multiply-shift index) and the same nearest-index percentile,
 * so the confidence interval is identical across languages.
 */

const TIE_EPS = 1e-9;
const LCG_A = 1664525;
const LCG_C = 1013904223;
const LCG_M = 4294967296; // 2 ** 32

/** Seeded LCG. State advances explicitly; no global RNG is touched. */
export class Lcg {
  state: number;

  constructor(seed: number) {
    this.state = seed >>> 0;
  }

  nextU32(): number {
    // (a*state + c) mod 2**32. The product stays below 2**53, so plain Number
    // arithmetic is exact — do NOT use Math.imul (32-bit wrap gives a different
    // value than Python's arbitrary-precision multiply-then-mod).
    this.state = (LCG_A * this.state + LCG_C) % LCG_M;
    return this.state;
  }

  randint(n: number): number {
    // High bits via multiply-shift; floor-divide (not >> 32, which is 32-bit).
    return Math.floor((this.nextU32() * n) / LCG_M);
  }
}

function sortedIndex(sortedValues: readonly number[], fractionalRank: number): number {
  let idx = Math.trunc(fractionalRank);
  if (idx < 0) idx = 0;
  if (idx > sortedValues.length - 1) idx = sortedValues.length - 1;
  return sortedValues[idx];
}

export function pairedBootstrapCi(
  diffs: readonly number[],
  iterations: number,
  seed: number,
  alpha = 0.05,
): [number, number] {
  const n = diffs.length;
  if (n === 0) throw new Error("diffs must be non-empty");
  if (iterations <= 0) throw new Error("iterations must be positive");
  const rng = new Lcg(seed);
  const means: number[] = [];
  for (let b = 0; b < iterations; b += 1) {
    let total = 0.0;
    for (let i = 0; i < n; i += 1) total += diffs[rng.randint(n)];
    means.push(total / n);
  }
  means.sort((x, y) => x - y);
  const lower = sortedIndex(means, Math.floor((alpha / 2.0) * iterations));
  const upper = sortedIndex(means, Math.ceil((1.0 - alpha / 2.0) * iterations) - 1);
  return [lower, upper];
}

export interface WinTieLoss {
  wins: number;
  ties: number;
  losses: number;
}

export function winTieLoss(
  baseline: readonly number[],
  candidate: readonly number[],
): WinTieLoss {
  if (baseline.length !== candidate.length) {
    throw new Error("score sequences must be the same length");
  }
  let wins = 0;
  let ties = 0;
  let losses = 0;
  for (let i = 0; i < baseline.length; i += 1) {
    const diff = candidate[i] - baseline[i];
    if (diff > TIE_EPS) wins += 1;
    else if (diff < -TIE_EPS) losses += 1;
    else ties += 1;
  }
  return { wins, ties, losses };
}

export interface Comparison {
  num_cases: number;
  mean_difference: number;
  ci_lower: number;
  ci_upper: number;
  alpha: number;
  practical_threshold: number;
  bootstrap_iterations: number;
  bootstrap_seed: number;
  win_tie_loss: WinTieLoss;
  verdict: "promote" | "reject" | "inconclusive";
}

export function compareVariants(
  baseline: readonly number[],
  candidate: readonly number[],
  practicalThreshold: number,
  iterations: number,
  seed: number,
  alpha = 0.05,
): Comparison {
  if (baseline.length !== candidate.length) {
    throw new Error("score sequences must be the same length");
  }
  const diffs = baseline.map((b, i) => candidate[i] - b);
  const meanDiff = diffs.reduce((a, b) => a + b, 0) / diffs.length;
  const [lower, upper] = pairedBootstrapCi(diffs, iterations, seed, alpha);
  let verdict: "promote" | "reject" | "inconclusive";
  if (lower >= practicalThreshold) verdict = "promote";
  else if (upper <= 0.0) verdict = "reject";
  else verdict = "inconclusive";
  return {
    num_cases: diffs.length,
    mean_difference: meanDiff,
    ci_lower: lower,
    ci_upper: upper,
    alpha,
    practical_threshold: practicalThreshold,
    bootstrap_iterations: iterations,
    bootstrap_seed: seed,
    win_tie_loss: winTieLoss(baseline, candidate),
    verdict,
  };
}
