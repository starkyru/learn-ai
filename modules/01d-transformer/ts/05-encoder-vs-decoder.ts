/**
 * Task 5 🟡 — Encoder vs decoder: same attention, different mask (BERT vs GPT).
 *
 * What you'll learn:
 *   - The classic interview question "what's the difference between BERT and GPT?"
 *     made concrete: BOTH use exactly the scaled dot-product attention you built in
 *     Task 1. What differs is the MASK (none vs causal) and the training OBJECTIVE
 *     (masked-token prediction vs next-token prediction).
 *   - Bidirectional (encoder / BERT-style) attention: no mask — every position sees
 *     the whole sequence, left AND right. Great contextual representations; useless
 *     for left-to-right generation (it would see the answer).
 *   - Causal (decoder / GPT-style) attention: the Task-1 mask — position i sees only
 *     j <= i. Enables generation; but a position can never use its RIGHT context.
 *   - The masked-token readout experiment: replace one token with [MASK], run one
 *     round of attention, and ask "which vocabulary token is this position's
 *     contextual representation now closest to?" When the disambiguating word sits
 *     to the RIGHT of the mask, bidirectional attention recovers the true token and
 *     causal attention provably cannot (its view of every sequence is identical).
 *
 * The math (all pieces from Task 1, minus/plus the mask):
 *
 *   Full (bidirectional) attention — NO mask:
 *     scores  = Q @ Kᵀ / sqrt(dK)          shape (n, n)
 *     weights = softmax(scores)            row-wise, each row sums to 1
 *     output  = weights @ V                every position mixes ALL positions
 *
 *   Causal attention — Task 1's additive mask:
 *     mask[i][j] = 0        if j <= i
 *     mask[i][j] = NEG_INF  if j >  i      future weights become exactly 0
 *
 *   Future mass: per row i, sum weights[i][j] over j > i; report the mean over
 *   rows. Causal must give exactly 0; bidirectional gives a healthy chunk.
 *
 *   Nearest-token readout (cosine argmax):
 *     cos(r, e) = (r . e) / (|r| * |e|)   → pick the vocab index maximising it.
 *
 * No external math library. Plain number[][] arrays.
 *
 * How to run:
 *   pnpm tsx modules/01d-transformer/ts/05-encoder-vs-decoder.ts
 */

type Matrix = number[][];

const NEG_INF = -1e9; // a large negative number; "-inf" for masking purposes

const D_MODEL = 16; // embedding dimension
const MASK_POS = 2; // the position we hide in every toy sentence

// ---------------------------------------------------------------------------
// Matrix helpers (provided for you)
// ---------------------------------------------------------------------------

/** Matrix multiply: A (m×k) @ B (k×n) -> (m×n). */
function matMul(A: Matrix, B: Matrix): Matrix {
  const m = A.length,
    k = B.length,
    n = B[0].length;
  const out: Matrix = Array.from({ length: m }, () => new Array(n).fill(0) as number[]);
  for (let i = 0; i < m; i++)
    for (let p = 0; p < k; p++) {
      const aip = A[i][p];
      for (let j = 0; j < n; j++) out[i][j] += aip * B[p][j];
    }
  return out;
}

/** Transpose a matrix (n×m) -> (m×n). */
function transpose(A: Matrix): Matrix {
  return A[0].map((_, j) => A.map((row) => row[j]));
}

/** Numerically-stable softmax of ONE row (subtract the max before exp). */
function softmaxRow(row: number[]): number[] {
  const mx = Math.max(...row);
  const exps = row.map((v) => Math.exp(v - mx));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map((e) => e / sum);
}

/** Dot product of two equal-length vectors. */
function dot(a: number[], b: number[]): number {
  return a.reduce((s, v, i) => s + v * b[i], 0);
}

/** Euclidean norm of a vector. */
function norm(a: number[]): number {
  return Math.sqrt(dot(a, a));
}

// ---------------------------------------------------------------------------
// Toy vocabulary + sentences  (provided — do not edit)
// ---------------------------------------------------------------------------
//
// A miniature "distributional" embedding table. Function words and sounds get
// one-hot embeddings; each ANIMAL's embedding is built from the contexts it
// appears in (the company it keeps — word2vec's idea in miniature):
//
//   emb(animal_i) = ( emb(the) + emb(big) + emb(today) + emb(sound_i) ) / 2
//
// So "cat" points along {the, big, today, meow}; "dog" along {the, big, today,
// woof}; only the SOUND distinguishes the animals. Every toy sentence is
//
//   the  big  <animal_i>  <sound_i>  today
//    0    1       2           3        4
//
// and we hide position 2 with [MASK]. The LEFT context ("the big") is identical
// across all five sentences — only the RIGHT neighbour (the sound) says which
// animal is hidden. That is exactly what a causal model can never see.

const VOCAB_NAMES = [
  "the",
  "big",
  "today",
  "[MASK]", // 0..3  one-hot e0..e3
  "meow",
  "woof",
  "moo",
  "quack",
  "baa", // 4..8  one-hot e4..e8
  "cat",
  "dog",
  "cow",
  "duck",
  "sheep", // 9..13 context-built
];

function buildVocab(): Matrix {
  const E: Matrix = Array.from({ length: VOCAB_NAMES.length }, () =>
    new Array(D_MODEL).fill(0),
  );
  for (let i = 0; i < 9; i++) E[i][i] = 1.0; // one-hot function words, mask, sounds
  for (let a = 0; a < 5; a++) {
    // animal a: (e_the + e_big + e_today + e_sound) / 2  — unit norm
    for (let j = 0; j < D_MODEL; j++) {
      E[9 + a][j] = (E[0][j] + E[1][j] + E[2][j] + E[4 + a][j]) / 2.0;
    }
  }
  return E;
}

/**
 * Five sentences "the big <animal> <sound> today", already masked:
 * tokenIds has [MASK] (id 3) at MASK_POS; trueId is the animal that belongs there.
 */
function makeSequences(): { tokenIds: number[]; trueId: number }[] {
  const seqs: { tokenIds: number[]; trueId: number }[] = [];
  for (let a = 0; a < 5; a++) {
    seqs.push({ tokenIds: [0, 1, 3, 4 + a, 2], trueId: 9 + a });
  }
  return seqs;
}

// ---------------------------------------------------------------------------
// Core functions — implement these
// ---------------------------------------------------------------------------

/**
 * BIDIRECTIONAL (encoder / BERT-style) scaled dot-product attention — no mask.
 *
 * @param Q queries, shape (n × dK)
 * @param K keys,    shape (n × dK)
 * @param V values,  shape (n × dV)
 * @returns { output (n×dV) — every position's mix of ALL value vectors,
 *            weights (n×n) — each row a probability distribution summing to 1 }
 *
 * This is Task 1's scaledDotProductAttention with the mask branch deleted:
 * nothing stops position i from attending to j > i.
 *
 * TODO: implement. Steps:
 *   - Form scores = matMul(Q, transpose(K)) and scale every entry by dividing by
 *     Math.sqrt(dK) (dK = K[0].length). Do NOT add any mask.
 *   - Turn each score row into probabilities with the provided softmaxRow.
 *   - output = matMul(weights, V).
 *   - Return the { output, weights } object.
 */
function fullAttention(
  Q: Matrix,
  K: Matrix,
  V: Matrix,
): { output: Matrix; weights: Matrix } {
  // TODO: implement bidirectional (unmasked) attention
  throw new Error("TODO: implement fullAttention()");
}

/**
 * CAUSAL (decoder / GPT-style) scaled dot-product attention — Task 1's mask.
 *
 * Same signature and return as fullAttention, but position i must put ZERO
 * weight on every j > i.
 *
 * TODO: implement. Steps:
 *   - Form the scaled scores exactly as in fullAttention.
 *   - Apply Task 1's causal mask BEFORE the softmax: for every entry with
 *     j > i, add NEG_INF to the score (n = Q.length).
 *   - Push each row through the provided softmaxRow, then output = matMul(weights, V).
 *   - Return the { output, weights } object.
 */
function causalAttention(
  Q: Matrix,
  K: Matrix,
  V: Matrix,
): { output: Matrix; weights: Matrix } {
  // TODO: implement causal (masked) attention
  throw new Error("TODO: implement causalAttention()");
}

/**
 * How much attention mass lands on FUTURE positions (j > i)?
 *
 * @param weights (n × n) attention-weight matrix (rows sum to 1)
 * @returns for each row i, sum the entries strictly above the diagonal
 *          (weights[i][j] for j > i), then average those row sums over all n rows.
 *
 * A causal weight matrix must score exactly 0.0; a bidirectional one on this
 * data scores well above 0.
 *
 * TODO: implement. For each row i, add up its entries with column index j > i;
 * combine those per-row sums with a mean over the n rows.
 */
function attentionMassOnFuture(weights: Matrix): number {
  // TODO: implement the future-mass measurement
  throw new Error("TODO: implement attentionMassOnFuture()");
}

/**
 * Which vocabulary token is this contextual representation closest to?
 *
 * @param reprVec (d,) one position's representation after attention
 * @param E (vocab × d) embedding table — E[i] is token i's embedding
 * @returns the vocab index with the highest COSINE similarity to reprVec:
 *          cos(r, e_i) = (r . e_i) / (|r| * |e_i|)
 *
 * TODO: implement. Steps:
 *   - For every row of E, compute the cosine similarity against reprVec using
 *     the provided dot() and norm() helpers.
 *   - Track and return the index of the best (largest) similarity.
 */
function nearestToken(reprVec: number[], E: Matrix): number {
  // TODO: implement the cosine-similarity argmax readout
  throw new Error("TODO: implement nearestToken()");
}

// ---------------------------------------------------------------------------
// Harness — complete, do not edit
// ---------------------------------------------------------------------------

function pad(s: string, w: number): string {
  return s.length >= w ? s : s + " ".repeat(w - s.length);
}

function main(): void {
  const E = buildVocab();
  const seqs = makeSequences();
  const nSeq = seqs.length;

  console.log("=".repeat(66));
  console.log("Task 5 — Encoder vs decoder: same attention, different mask");
  console.log("=".repeat(66));
  console.log(
    `  vocab=${VOCAB_NAMES.length}  d=${D_MODEL}  sentences=${nSeq}  masked position=${MASK_POS}\n`,
  );

  // ── [1] Where does the attention mass go? ───────────────────────────────────
  const X0 = seqs[0].tokenIds.map((t) => E[t]); // first masked sentence: (5 × d)
  const { weights: wFull } = fullAttention(X0, X0, X0);
  const { weights: wCausal } = causalAttention(X0, X0, X0);
  const massFull = attentionMassOnFuture(wFull);
  const massCausal = attentionMassOnFuture(wCausal);
  console.log("[1] Mean attention mass on FUTURE positions (j > i):");
  console.log(`    bidirectional (no mask): ${massFull.toFixed(4)}`);
  console.log(
    `    causal (masked)        : ${massCausal.toFixed(10)}   (must be exactly 0)\n`,
  );

  // ── [2] Masked-token readout ────────────────────────────────────────────────
  console.log("[2] Masked-token readout — after ONE round of self-attention, which");
  console.log("    vocab token is the [MASK] position's representation closest to?");
  console.log("    (the disambiguating word is the sound, to the RIGHT of the mask)\n");
  let biCorrect = 0;
  let causalCorrect = 0;
  for (const { tokenIds, trueId } of seqs) {
    const X = tokenIds.map((t) => E[t]); // (5 × d) — [MASK] embedding at MASK_POS
    const { output: outBi } = fullAttention(X, X, X);
    const { output: outCa } = causalAttention(X, X, X);
    const predBi = nearestToken(outBi[MASK_POS], E);
    const predCa = nearestToken(outCa[MASK_POS], E);
    if (predBi === trueId) biCorrect++;
    if (predCa === trueId) causalCorrect++;
    const sentence = tokenIds.map((t) => VOCAB_NAMES[t]).join(" ");
    console.log(
      `    '${sentence}'  true=${pad(VOCAB_NAMES[trueId], 5)}  ` +
        `bidirectional→${pad(VOCAB_NAMES[predBi], 6)}  causal→${VOCAB_NAMES[predCa]}`,
    );
  }
  console.log(`\n    bidirectional correct: ${biCorrect}/${nSeq}`);
  console.log(`    causal        correct: ${causalCorrect}/${nSeq}`);
  console.log("    The left context 'the big' is IDENTICAL in all five sentences, so");
  console.log("    the causal representation of the mask is the same every time — it");
  console.log("    cannot recover a token that only the RIGHT neighbour determines.");
  console.log("    That's why BERT (masked-LM) trains with bidirectional attention,");
  console.log("    and why GPT (next-token) has to accept the causal mask.\n");

  // ── Acceptance checks ───────────────────────────────────────────────────────
  const okCausalZero = massCausal === 0.0;
  const okFullMass = massFull > 0.2;
  const okBi = biCorrect >= 4;
  const okLt = causalCorrect < biCorrect;

  console.log("Acceptance:");
  console.log(
    `  [${okCausalZero ? "x" : " "}] causal future mass == 0 exactly (got ${massCausal})`,
  );
  console.log(
    `  [${okFullMass ? "x" : " "}] bidirectional future mass > 0.2 (got ${massFull.toFixed(4)})`,
  );
  console.log(
    `  [${okBi ? "x" : " "}] bidirectional recovers the masked token in >= 4/${nSeq} sentences (got ${biCorrect}/${nSeq})`,
  );
  console.log(
    `  [${okLt ? "x" : " "}] causal recovers strictly fewer (${causalCorrect} < ${biCorrect})`,
  );

  if (okCausalZero && okFullMass && okBi && okLt) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
