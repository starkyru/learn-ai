/**
 * uncertainty.test.ts — seeded LCG, paired bootstrap CI, release verdict.
 * Mirrors test_uncertainty.py; exact bounds are hand-derived (see comments).
 */

import { Lcg, compareVariants, pairedBootstrapCi, winTieLoss } from "./uncertainty.js";

describe("LCG", () => {
  test("first value is hand-computed", () => {
    // (1664525*42 + 1013904223) mod 2**32 = 1083814273
    expect(new Lcg(42).nextU32()).toBe(1083814273);
  });
  test("randint uses the high bits", () => {
    // (1083814273 * 10) >> 32 = 2
    expect(new Lcg(42).randint(10)).toBe(2);
  });
});

describe("paired bootstrap CI", () => {
  test("constant input is exact (c, c) for any seed", () => {
    expect(pairedBootstrapCi([0.5, 0.5, 0.5], 200, 1)).toEqual([0.5, 0.5]);
  });
  test("single element is exact", () => {
    expect(pairedBootstrapCi([0.7], 50, 9)).toEqual([0.7, 0.7]);
  });
  test("two-point [0,1] tails are the extremes 0 and 1", () => {
    // means are 0/0.5/1; ~25% at each tail, so 2.5%/97.5% bounds are 0 and 1.
    expect(pairedBootstrapCi([0.0, 1.0], 2000, 7)).toEqual([0.0, 1.0]);
  });
  test("deterministic for a fixed seed", () => {
    const data = [0.2, 0.8, 0.5, 0.1, 0.9];
    expect(pairedBootstrapCi(data, 500, 123)).toEqual(
      pairedBootstrapCi(data, 500, 123),
    );
  });
  test("bounds bracket the data", () => {
    const data = [0.1, 0.4, 0.9, 0.3];
    const [lo, hi] = pairedBootstrapCi(data, 500, 5);
    expect(Math.min(...data)).toBeLessThanOrEqual(lo);
    expect(lo).toBeLessThanOrEqual(hi);
    expect(hi).toBeLessThanOrEqual(Math.max(...data));
  });
  test("rejects empty or zero iterations", () => {
    expect(() => pairedBootstrapCi([], 10, 1)).toThrow();
    expect(() => pairedBootstrapCi([0.1], 0, 1)).toThrow();
  });
});

describe("win/tie/loss and verdict", () => {
  test("win/tie/loss hand counts", () => {
    // diffs +1, 0, +0.5 -> 2 wins, 1 tie, 0 losses
    expect(winTieLoss([0, 0, 0], [1, 0, 0.5])).toEqual({ wins: 2, ties: 1, losses: 0 });
  });
  test("promote when CI clears the threshold", () => {
    const r = compareVariants([0, 0, 0, 0, 0], [1, 1, 1, 1, 1], 0.1, 500, 1);
    expect(r.verdict).toBe("promote");
    expect(r.mean_difference).toBe(1.0);
  });
  test("reject when CI at or below zero", () => {
    expect(compareVariants([1, 1, 1, 1, 1], [0, 0, 0, 0, 0], 0.1, 500, 1).verdict).toBe(
      "reject",
    );
  });
  test("inconclusive when CI crosses the threshold", () => {
    expect(compareVariants([0, 0, 1, 1], [1, 1, 0, 0], 0.1, 500, 1).verdict).toBe(
      "inconclusive",
    );
  });
  test("rejects mismatched lengths", () => {
    expect(() => compareVariants([0, 1], [1], 0.1, 100, 1)).toThrow();
  });
});
