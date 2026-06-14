/**
 * bpe.test.ts — unit tests for the WORKED fundamentals (jest).
 *
 * What it teaches:
 *   The from-scratch pieces have simple, checkable invariants: BPE must
 *   round-trip losslessly, and cosine has known values for identical and
 *   orthogonal vectors. These tests never touch the network — they exercise the
 *   pure logic only, which is what unit tests are for.
 *
 * How to run (from the repo root):
 *   pnpm jest modules/01-fundamentals/ts/bpe.test.ts
 */

import { BPETokenizer, CORPUS } from "./bpe.js";
import { cosine, dot, norm } from "./cosine.js";

function trainedTokenizer(): BPETokenizer {
  const tok = new BPETokenizer();
  tok.train(CORPUS, 50);
  return tok;
}

describe("BPE tokenizer", () => {
  test("round-trips a sample string losslessly", () => {
    const tok = trainedTokenizer();
    const sample = "the model reads tokens";
    expect(tok.decode(tok.encode(sample))).toBe(sample);
  });

  test("round-trips the full training corpus", () => {
    const tok = trainedTokenizer();
    expect(tok.decode(tok.encode(CORPUS))).toBe(CORPUS);
  });

  test("round-trips unseen and Unicode input (no 'unknown token')", () => {
    const tok = trainedTokenizer();
    for (const s of ["café — 日本語 😀", "zzz!!!", "", "  spaces  "]) {
      expect(tok.decode(tok.encode(s))).toBe(s);
    }
  });

  test("actually learns merges and compresses", () => {
    const tok = trainedTokenizer();
    expect(tok.merges.length).toBeGreaterThan(0);
    const text = "the model reads tokens";
    expect(tok.encode(text).length).toBeLessThan(new TextEncoder().encode(text).length);
  });

  test("vocab size = 256 base + merges", () => {
    const tok = trainedTokenizer();
    expect(tok.vocabSize).toBe(256 + tok.merges.length);
  });
});

describe("cosine similarity", () => {
  test("identical vectors -> 1", () => {
    const v = [1, 2, 3, 4];
    expect(cosine(v, v)).toBeCloseTo(1, 10);
  });

  test("orthogonal vectors -> 0", () => {
    expect(cosine([1, 0], [0, 1])).toBeCloseTo(0, 12);
  });

  test("opposite vectors -> -1", () => {
    expect(cosine([1, 2, 3], [-1, -2, -3])).toBeCloseTo(-1, 10);
  });

  test("zero vector is safe (returns 0, not NaN)", () => {
    expect(cosine([0, 0], [1, 1])).toBe(0);
  });

  test("dot and norm helpers", () => {
    expect(dot([1, 2, 3], [4, 5, 6])).toBe(32);
    expect(norm([3, 4])).toBeCloseTo(5, 12);
  });
});
