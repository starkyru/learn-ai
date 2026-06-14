"""bigram.py — a count-based bigram "language model" (Task 5, 🟡 optional STUB).

What it teaches:
    Demystifies "prediction". A language model is just a next-token predictor.
    The simplest real one: count how often each token follows each other token,
    then generate by sampling the next token from those counts. No neural net,
    no attention — yet it IS a language model (a bad one). A transformer is this
    same idea with a much longer memory and learned representations.

    We tokenize on whitespace here (words) to keep the counting obvious — not
    the BPE from Task 1, though you could swap it in.

How to run (from the repo root):
    uv run python modules/01-fundamentals/py/bigram.py
"""

from __future__ import annotations

import random

CORPUS = (
    "the cat sat on the mat the cat ran to the dog the dog sat on the log "
    "the cat and the dog sat on the mat the dog ran to the cat"
)


def build_bigram_counts(tokens: list[str]) -> dict[str, dict[str, int]]:
    """Build {token -> {next_token -> count}} from a token sequence.

    TODO:
      For each adjacent pair (tokens[i], tokens[i+1]), increment
      counts[tokens[i]][tokens[i+1]]. Return the nested dict.
    """
    raise NotImplementedError("Count token -> next-token frequencies — see the TODO.")


def predict_next(
    counts: dict[str, dict[str, int]], token: str, rng: random.Random
) -> str:
    """Sample the next token given the current one, using the counts as weights.

    TODO:
      1. Look up the follower counts for `token`. If none exist (unseen token),
         fall back to picking a random known token.
      2. Sample a follower with probability proportional to its count.
         (Hint: rng.choices(list(followers), weights=list(counts), k=1)[0].)
    """
    raise NotImplementedError("Sample the next token from the counts — see the TODOs.")


def generate(
    counts: dict[str, dict[str, int]], start: str, length: int, rng: random.Random
) -> list[str]:
    """Generate `length` tokens by repeatedly predicting the next one."""
    out = [start]
    for _ in range(length - 1):
        out.append(predict_next(counts, out[-1], rng))
    return out


def main() -> None:
    rng = random.Random(0)
    tokens = CORPUS.split()
    counts = build_bigram_counts(tokens)

    print("Learned followers for 'the':", counts.get("the"))
    print()
    generated = generate(counts, start="the", length=20, rng=rng)
    print("Generated:", " ".join(generated))
    print(
        "\nLocally plausible, globally nonsense — because it only remembers the "
        "PREVIOUS token. Attention is what gives a transformer a longer memory."
    )


if __name__ == "__main__":
    main()
