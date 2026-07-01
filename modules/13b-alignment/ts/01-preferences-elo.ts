/**
 * Task 1 🟢 — Preference data: pairwise comparisons, win rates, and Elo.
 *
 * What you'll learn:
 *   - Why pairwise comparisons ("A is better than B") are the raw material of
 *     alignment — humans are bad at absolute scores but good at picking a winner
 *   - Win-rate matrices: the simplest aggregate of preference data
 *   - The Elo rating system — how Chatbot Arena turns millions of pairwise
 *     votes into a single leaderboard number per model
 *
 * The math (README derives each step):
 *
 *   Expected score of A vs B (Elo):   E_A = 1 / (1 + 10^((R_B - R_A) / 400))
 *   Update after a match:             R_A ← R_A + k · (S_A - E_A)
 *                                     R_B ← R_B + k · (S_B - E_B)
 *   where S_A ∈ {0, 1} is the actual outcome and S_A + S_B = 1, E_A + E_B = 1.
 *
 *   Match outcomes here are sampled from the models' hidden true quality gap:
 *   P(A beats B) = σ(q_A - q_B), the same Bradley–Terry shape Task 2 builds on.
 *
 * You implement the three core functions (winRateMatrix, eloUpdate, runElo)
 * using plain arrays only (no math libraries). The match schedule, outcome
 * sampling, and the report are provided and runnable.
 *
 * How to run:
 *   pnpm tsx modules/13b-alignment/ts/01-preferences-elo.ts
 */

const SEED = 13;
const M = 5; // number of "models" being compared
const ROUNDS = 60; // each unordered pair plays this many matches
const K_FACTOR = 16.0; // Elo K
const START_RATING = 1000.0;

// Hidden true quality of each model (index = model id). The whole point of the
// exercise: can win rates + Elo recover this ordering from noisy pairwise data?
const TRUE_QUALITY = [-1.2, -0.4, 0.4, 1.2, 2.0];

type Outcome = { i: number; j: number; scoreI: number };

// ---------------------------------------------------------------------------
// Seeded RNG (provided) — LCG for reproducible uniforms
// ---------------------------------------------------------------------------

function makeRng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    // Numerical Recipes LCG
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
    return s / 4294967296; // uniform in [0, 1)
  };
}

// ---------------------------------------------------------------------------
// Match schedule + outcomes  (provided — do not edit)
// ---------------------------------------------------------------------------

/** σ(z) = 1 / (1 + e^{-z}). */
function sigmoid(z: number): number {
  return 1 / (1 + Math.exp(-z));
}

/**
 * Deterministic schedule: ROUNDS round-robins over every pair (i < j).
 * Each match outcome is sampled from the hidden quality gap:
 *   P(i beats j) = σ(q_i - q_j).
 *
 * Returns a list of { i, j, scoreI } with scoreI ∈ {0, 1}
 * (score of j is implicitly 1 - scoreI).
 */
function playMatches(): Outcome[] {
  const rng = makeRng(SEED);
  const outcomes: Outcome[] = [];
  for (let r = 0; r < ROUNDS; r++) {
    for (let i = 0; i < M; i++) {
      for (let j = i + 1; j < M; j++) {
        const pIWins = sigmoid(TRUE_QUALITY[i] - TRUE_QUALITY[j]);
        outcomes.push({ i, j, scoreI: rng() < pIWins ? 1 : 0 });
      }
    }
  }
  return outcomes;
}

// ---------------------------------------------------------------------------
// Core functions — YOU implement these three (plain arrays only)
// ---------------------------------------------------------------------------

/**
 * Aggregate raw match outcomes into an m×m win-rate matrix W where
 * W[a][b] = (matches a won against b) / (matches a played against b).
 *
 * Conventions:
 *   - Each outcome { i, j, scoreI } counts for BOTH cells: it gives i a
 *     score of scoreI vs j, and j a score of (1 - scoreI) vs i.
 *   - Diagonal W[a][a] = 0.5 (a model neither beats nor loses to itself).
 *   - Note the symmetry you should end up with: W[a][b] + W[b][a] = 1.
 *
 * TODO: implement.
 *   - Accumulate two m×m arrays: total score per ordered pair, and match
 *     counts per ordered pair.
 *   - Divide cell-by-cell (only where count > 0), set the diagonal to 0.5,
 *     and return the m×m matrix.
 */
function winRateMatrix(outcomes: Outcome[], m: number): number[][] {
  // TODO: accumulate scores + counts per ordered pair, then divide
  throw new Error("TODO: implement winRateMatrix()");
}

/**
 * One Elo update after a single match between A and B.
 *
 *   E_A = 1 / (1 + 10^((R_B - R_A) / 400))    (expected score of A)
 *   R_A ← R_A + k · (S_A - E_A)
 *   R_B ← R_B + k · (S_B - E_B)   with  S_B = 1 - S_A  and  E_B = 1 - E_A
 *
 * Return the pair [newRatingA, newRatingB].
 *
 * TODO: implement.
 *   - Compute A's expected score E_A from the rating gap per the formula
 *     (Math.pow / the ** operator).
 *   - Move each rating by k times (actual score minus expected score).
 *   - Return both updated ratings as a two-element array.
 */
function eloUpdate(
  ratingA: number,
  ratingB: number,
  scoreA: number,
  k: number,
): [number, number] {
  // TODO: compute E_A, then step both ratings by k·(S − E)
  throw new Error("TODO: implement eloUpdate()");
}

/**
 * Replay the match schedule in order, applying eloUpdate after every match.
 *
 * Every model starts at `start`. Returns the final array of m ratings.
 *
 * TODO: implement.
 *   - Initialise an array of m ratings at `start`.
 *   - For each outcome in order, call eloUpdate on ratings i and j and store
 *     both results back.
 *   - Return the ratings array.
 */
function runElo(outcomes: Outcome[], m: number, k: number, start: number): number[] {
  // TODO: replay the outcomes through eloUpdate
  throw new Error("TODO: implement runElo()");
}

// ---------------------------------------------------------------------------
// Harness  (provided — do not edit)
// ---------------------------------------------------------------------------

/** Indices 0..n-1 sorted ascending by the values they index. */
function argsort(values: number[]): number[] {
  return values
    .map((v, idx) => [v, idx] as [number, number])
    .sort((a, b) => a[0] - b[0])
    .map(([, idx]) => idx);
}

function main(): void {
  console.log("Task 1 — Preference data: win rates and Elo\n");

  const outcomes = playMatches();
  const nPairs = (M * (M - 1)) / 2;
  console.log(`  Models: ${M} (true quality: [${TRUE_QUALITY}])`);
  console.log(`  Matches: ${outcomes.length} (${ROUNDS} rounds x ${nPairs} pairs)\n`);

  // ── Win-rate matrix ──────────────────────────────────────────────────────
  console.log("[1/2] Win-rate matrix (row = model, col = opponent)...");
  const W = winRateMatrix(outcomes, M);
  const header =
    "        " + Array.from({ length: M }, (_, j) => `  vs m${j}`).join("");
  console.log(header);
  for (let i = 0; i < M; i++) {
    const row = W[i].map((v) => `  ${v.toFixed(3)}`).join("");
    console.log(`    m${i}: ${row}`);
  }

  // ── Elo ──────────────────────────────────────────────────────────────────
  console.log("\n[2/2] Elo ratings (replaying the match log)...");
  const ratings = runElo(outcomes, M, K_FACTOR, START_RATING);
  for (let i = 0; i < M; i++) {
    const q =
      TRUE_QUALITY[i] >= 0
        ? `+${TRUE_QUALITY[i].toFixed(1)}`
        : TRUE_QUALITY[i].toFixed(1);
    console.log(
      `    m${i}: true quality ${q}  →  Elo ${ratings[i].toFixed(1).padStart(7)}`,
    );
  }

  const trueOrder = argsort(TRUE_QUALITY);
  const eloOrder = argsort(ratings);
  const best = trueOrder[trueOrder.length - 1];
  const othersMax = Math.max(...ratings.filter((_, i) => i !== best));
  const margin = ratings[best] - othersMax;
  console.log(`\n  true ordering (worst→best): [${trueOrder}]`);
  console.log(`  Elo ordering  (worst→best): [${eloOrder}]`);
  console.log(`  Elo margin of best model over runner-up: ${margin.toFixed(1)}`);

  // ── Acceptance checks ────────────────────────────────────────────────────
  console.log("\nAcceptance:");
  const okOrder = eloOrder.every((v, idx) => v === trueOrder[idx]);
  let okWr = true;
  for (let i = 0; i < M; i++) {
    for (let j = 0; j < M; j++) {
      if (TRUE_QUALITY[i] > TRUE_QUALITY[j] && !(W[i][j] > 0.5)) okWr = false;
    }
  }
  const okMargin = margin > 40;
  console.log(`  [${okOrder ? "x" : " "}] Elo ordering matches true quality ordering`);
  console.log(
    `  [${okWr ? "x" : " "}] win-rate rows consistent: better model > 0.5 vs every worse one`,
  );
  console.log(
    `  [${okMargin ? "x" : " "}] best model's Elo clearly highest (margin = ${margin.toFixed(1)} > 40)`,
  );

  if (okOrder && okWr && okMargin) {
    console.log("\n  All acceptance checks passed.");
  } else {
    console.log("\n  Some checks failed — revisit your implementation.");
  }
}

main();

// This file has no imports; the empty export marks it as an ES module so its
// top-level names stay file-scoped (keeps `pnpm typecheck` happy across modules).
export {};
