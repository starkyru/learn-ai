/**
 * agreement.ts — judge <-> human reliability (Task 3). Port of agreement.py.
 *
 * Cohen's kappa: kappa = (p_o - p_e) / (1 - p_e), where p_e is the chance
 * agreement = sum over categories k of P(A = k) * P(B = k).
 */

export function percentAgreement(
  labelsA: readonly number[],
  labelsB: readonly number[],
): number {
  if (labelsA.length !== labelsB.length) {
    throw new Error("label sequences must be the same length");
  }
  if (labelsA.length === 0) throw new Error("no labels to compare");
  let matches = 0;
  for (let i = 0; i < labelsA.length; i += 1)
    if (labelsA[i] === labelsB[i]) matches += 1;
  return matches / labelsA.length;
}

function counts(labels: readonly number[]): Map<number, number> {
  const out = new Map<number, number>();
  for (const label of labels) out.set(label, (out.get(label) ?? 0) + 1);
  return out;
}

export function cohensKappa(
  labelsA: readonly number[],
  labelsB: readonly number[],
): number {
  if (labelsA.length !== labelsB.length) {
    throw new Error("label sequences must be the same length");
  }
  const n = labelsA.length;
  if (n === 0) throw new Error("no labels to compare");
  let observed = 0;
  for (let i = 0; i < n; i += 1) if (labelsA[i] === labelsB[i]) observed += 1;
  const pObserved = observed / n;
  const countA = counts(labelsA);
  const countB = counts(labelsB);
  // Iterate categories in a CANONICAL SORTED order to match the Python port:
  // float addition is not associative, so an unordered traversal could make
  // pExpected differ in the last ULP for 3+ categories.
  const categories = [...new Set<number>([...countA.keys(), ...countB.keys()])].sort(
    (a, b) => a - b,
  );
  let pExpected = 0;
  for (const k of categories) {
    pExpected += ((countA.get(k) ?? 0) / n) * ((countB.get(k) ?? 0) / n);
  }
  if (pExpected === 1.0) {
    // No variance in the labels; kappa is undefined — report perfect agreement
    // as 1.0, otherwise 0.0.
    return pObserved === 1.0 ? 1.0 : 0.0;
  }
  return (pObserved - pExpected) / (1.0 - pExpected);
}

export interface AgreementReport {
  variant: string;
  judge: { model: string; prompt_version: string };
  num_labeled: number;
  percent_agreement: number;
  cohens_kappa: number;
  disagreement_queue: Array<{ case_id: string; judge: number; human: number }>;
}

export function buildAgreementReport(
  variant: string,
  judgeLabels: Record<string, number>,
  humanLabels: Record<string, number>,
  judgeModel: string,
  promptVersion: string,
): AgreementReport {
  const common = Object.keys(judgeLabels)
    .filter((c) => c in humanLabels)
    .sort();
  if (common.length === 0) throw new Error("judge and human share no labeled cases");
  const judgeSeq = common.map((c) => judgeLabels[c]);
  const humanSeq = common.map((c) => humanLabels[c]);
  const queue = common
    .filter((c) => judgeLabels[c] !== humanLabels[c])
    .map((c) => ({ case_id: c, judge: judgeLabels[c], human: humanLabels[c] }));
  return {
    variant,
    judge: { model: judgeModel, prompt_version: promptVersion },
    num_labeled: common.length,
    percent_agreement: percentAgreement(judgeSeq, humanSeq),
    cohens_kappa: cohensKappa(judgeSeq, humanSeq),
    disagreement_queue: queue,
  };
}
