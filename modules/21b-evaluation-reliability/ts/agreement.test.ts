/**
 * agreement.test.ts — Cohen's kappa + agreement (hand-derived expected values).
 * Mirrors test_agreement.py; kappa is derived on paper from the matrix.
 */

import { buildAgreementReport, cohensKappa, percentAgreement } from "./agreement.js";

describe("Cohen's kappa", () => {
  test("moderate: kappa = 0.4", () => {
    // p_o = 0.7, p_e = 0.5 -> (0.7-0.5)/0.5 = 0.4
    const a = [1, 1, 1, 1, 1, 1, 0, 0, 0, 0];
    const b = [1, 1, 1, 1, 0, 0, 1, 0, 0, 0];
    expect(cohensKappa(a, b)).toBeCloseTo(0.4, 9);
  });
  test("three-category kappa = 0.52 (hand-derived; byte-parity with Python)", () => {
    // a=[0,0,0,1,1,2], b=[0,1,2,1,1,2]. p_o=4/6; p_e=11/36; kappa=13/25=0.52.
    // The exact IEEE-754 value is pinned identically to test_agreement.py, so a
    // sorted category iteration keeps 3+ categories byte-identical across ports.
    expect(cohensKappa([0, 0, 0, 1, 1, 2], [0, 1, 2, 1, 1, 2])).toBe(
      0.5199999999999999,
    );
  });
  test("chance agreement -> 0", () => {
    expect(cohensKappa([1, 1, 0, 0], [1, 0, 1, 0])).toBe(0.0);
  });
  test("perfect non-degenerate -> 1", () => {
    expect(cohensKappa([1, 1, 0, 0], [1, 1, 0, 0])).toBe(1.0);
  });
  test("systematic disagreement -> -1", () => {
    expect(cohensKappa([1, 1, 0, 0], [0, 0, 1, 1])).toBe(-1.0);
  });
  test("degenerate single category -> 1", () => {
    expect(cohensKappa([1, 1, 1], [1, 1, 1])).toBe(1.0);
  });
  test("rejects mismatched lengths / empty", () => {
    expect(() => cohensKappa([1, 0], [1])).toThrow();
    expect(() => cohensKappa([], [])).toThrow();
  });
});

test("percent agreement hand value", () => {
  expect(percentAgreement([1, 0, 1, 1], [1, 1, 1, 0])).toBe(0.5);
});

test("agreement report queues disagreements", () => {
  const judge = { c1: 1, c2: 0, c3: 1, c4: 0 };
  const human = { c1: 1, c2: 0, c3: 0, c4: 1 };
  const report = buildAgreementReport(
    "variant_a",
    judge,
    human,
    "fake-judge-v1",
    "p-v1",
  );
  expect(report.num_labeled).toBe(4);
  expect(report.percent_agreement).toBe(0.5);
  expect(report.disagreement_queue.map((d) => d.case_id)).toEqual(["c3", "c4"]);
  expect(report.judge).toEqual({ model: "fake-judge-v1", prompt_version: "p-v1" });
});
