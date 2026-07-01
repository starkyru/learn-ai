"""
Task 1 🟢 — Preference data: pairwise comparisons, win rates, and Elo.

What you'll learn:
  - Why pairwise comparisons ("A is better than B") are the raw material of
    alignment — humans are bad at absolute scores but good at picking a winner
  - Win-rate matrices: the simplest aggregate of preference data
  - The Elo rating system — how Chatbot Arena turns millions of pairwise
    votes into a single leaderboard number per model

The math (README derives each step):

  Expected score of A vs B (Elo):   E_A = 1 / (1 + 10^((R_B - R_A) / 400))
  Update after a match:             R_A ← R_A + k · (S_A - E_A)
                                    R_B ← R_B + k · (S_B - E_B)
  where S_A ∈ {0, 1} is the actual outcome and S_A + S_B = 1, E_A + E_B = 1.

  Match outcomes here are sampled from the models' hidden true quality gap:
  P(A beats B) = σ(q_A - q_B), the same Bradley–Terry shape Task 2 builds on.

You implement the three core functions (win_rate_matrix, elo_update, run_elo).
The match schedule, outcome sampling, and the report are provided and runnable.

How to run:
  uv run python modules/13b-alignment/py/01_preferences_elo.py
"""

from __future__ import annotations

import numpy as np

SEED = 13
M = 5  # number of "models" being compared
ROUNDS = 60  # each unordered pair plays this many matches
K_FACTOR = 16.0  # Elo K
START_RATING = 1000.0

# Hidden true quality of each model (index = model id). The whole point of the
# exercise: can win rates + Elo recover this ordering from noisy pairwise data?
TRUE_QUALITY = [-1.2, -0.4, 0.4, 1.2, 2.0]


# ---------------------------------------------------------------------------
# Match schedule + outcomes  (provided — do not edit)
# ---------------------------------------------------------------------------


def sigmoid(z: float) -> float:
    """σ(z) = 1 / (1 + e^{-z})."""
    return 1.0 / (1.0 + np.exp(-z))


def play_matches() -> list[tuple[int, int, float]]:
    """
    Deterministic schedule: ROUNDS round-robins over every pair (i < j).
    Each match outcome is sampled from the hidden quality gap:
      P(i beats j) = σ(q_i - q_j).

    Returns a list of (i, j, score_i) with score_i ∈ {0.0, 1.0}
    (score_j is implicitly 1 - score_i).
    """
    rng = np.random.default_rng(SEED)
    outcomes: list[tuple[int, int, float]] = []
    for _ in range(ROUNDS):
        for i in range(M):
            for j in range(i + 1, M):
                p_i_wins = sigmoid(TRUE_QUALITY[i] - TRUE_QUALITY[j])
                score_i = 1.0 if rng.random() < p_i_wins else 0.0
                outcomes.append((i, j, score_i))
    return outcomes


# ---------------------------------------------------------------------------
# Core functions — YOU implement these three
# ---------------------------------------------------------------------------


def win_rate_matrix(outcomes: list[tuple[int, int, float]], m: int) -> np.ndarray:
    """
    Aggregate raw match outcomes into an (m, m) win-rate matrix W where
    W[a][b] = (matches a won against b) / (matches a played against b).

    Conventions:
      - Each outcome (i, j, score_i) counts for BOTH cells: it gives i a
        score of score_i vs j, and j a score of (1 - score_i) vs i.
      - Diagonal W[a][a] = 0.5 (a model neither beats nor loses to itself).
      - Note the symmetry you should end up with: W[a][b] + W[b][a] = 1.

    TODO: implement.
      - Accumulate two (m, m) arrays: total score per ordered pair, and match
        counts per ordered pair.
      - Divide (element-wise, only where count > 0), set the diagonal to 0.5,
        and return the (m, m) float matrix.
    """
    # TODO: accumulate scores + counts per ordered pair, then divide
    raise NotImplementedError("TODO: implement win_rate_matrix()")


def elo_update(rating_a: float, rating_b: float, score_a: float, k: float) -> tuple[float, float]:
    """
    One Elo update after a single match between A and B.

      E_A = 1 / (1 + 10^((R_B - R_A) / 400))    (expected score of A)
      R_A ← R_A + k · (S_A - E_A)
      R_B ← R_B + k · (S_B - E_B)   with  S_B = 1 - S_A  and  E_B = 1 - E_A

    Return the pair (new_rating_a, new_rating_b). Do not mutate anything —
    ratings are plain floats.

    TODO: implement.
      - Compute A's expected score E_A from the rating gap per the formula.
      - Move each rating by k times (actual score minus expected score).
      - Return both updated ratings as a tuple.
    """
    # TODO: compute E_A, then step both ratings by k·(S − E)
    raise NotImplementedError("TODO: implement elo_update()")


def run_elo(outcomes: list[tuple[int, int, float]], m: int, k: float, start: float) -> list[float]:
    """
    Replay the match schedule in order, applying elo_update after every match.

    Every model starts at `start`. Returns the final list of m ratings.

    TODO: implement.
      - Initialise a list of m ratings at `start`.
      - For each (i, j, score_i) in order, call elo_update on ratings i and j
        and store both results back.
      - Return the ratings list.
    """
    # TODO: replay the outcomes through elo_update
    raise NotImplementedError("TODO: implement run_elo()")


# ---------------------------------------------------------------------------
# Harness  (provided — do not edit)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Task 1 — Preference data: win rates and Elo\n")

    outcomes = play_matches()
    n_pairs = M * (M - 1) // 2
    print(f"  Models: {M} (true quality: {TRUE_QUALITY})")
    print(f"  Matches: {len(outcomes)} ({ROUNDS} rounds x {n_pairs} pairs)\n")

    # ── Win-rate matrix ──────────────────────────────────────────────────────
    print("[1/2] Win-rate matrix (row = model, col = opponent)...")
    W = win_rate_matrix(outcomes, M)
    header = "        " + "".join(f"  vs m{j}" for j in range(M))
    print(header)
    for i in range(M):
        row = "".join(f"  {W[i, j]:.3f}" for j in range(M))
        print(f"    m{i}: {row}")

    # ── Elo ──────────────────────────────────────────────────────────────────
    print("\n[2/2] Elo ratings (replaying the match log)...")
    ratings = run_elo(outcomes, M, K_FACTOR, START_RATING)
    for i in range(M):
        print(f"    m{i}: true quality {TRUE_QUALITY[i]:+.1f}  →  Elo {ratings[i]:7.1f}")

    true_order = [int(i) for i in np.argsort(TRUE_QUALITY)]
    elo_order = [int(i) for i in np.argsort(ratings)]
    best = int(np.argmax(TRUE_QUALITY))
    others_max = max(r for i, r in enumerate(ratings) if i != best)
    margin = ratings[best] - others_max
    print(f"\n  true ordering (worst→best): {true_order}")
    print(f"  Elo ordering  (worst→best): {elo_order}")
    print(f"  Elo margin of best model over runner-up: {margin:.1f}")

    # ── Acceptance checks ────────────────────────────────────────────────────
    print("\nAcceptance:")
    ok_order = elo_order == true_order
    ok_wr = all(
        W[i, j] > 0.5 for i in range(M) for j in range(M) if TRUE_QUALITY[i] > TRUE_QUALITY[j]
    )
    ok_margin = margin > 40.0
    print(f"  [{'x' if ok_order else ' '}] Elo ordering matches true quality ordering")
    print(
        f"  [{'x' if ok_wr else ' '}] win-rate rows consistent: better model > 0.5 vs every worse one"
    )
    print(
        f"  [{'x' if ok_margin else ' '}] best model's Elo clearly highest (margin = {margin:.1f} > 40)"
    )

    if ok_order and ok_wr and ok_margin:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
