"""sampling.py — greedy / temperature / top-k / top-p sampling (Task 4, 🔴 STUB).

What it teaches:
    How a model's raw output (logits) becomes the next token. The four strategies
    here are exactly the temperature / top_k / top_p knobs you set on every API
    call. See README Concept 4 for the math. Fill in the TODOs.

How to run (from the repo root):
    uv run python modules/01-fundamentals/py/sampling.py
"""

from __future__ import annotations

import math
import random

# A toy logit vector over a 6-token vocabulary. Index 2 is the clear favourite.
LOGITS = [2.0, 1.0, 4.0, 0.5, 3.0, -1.0]


def softmax(logits: list[float], temperature: float = 1.0) -> list[float]:
    """Turn logits into a probability distribution, optionally temperatured.

    p_i = exp(logit_i / T) / Σ_j exp(logit_j / T)
    Subtracts the max before exp for numerical stability.
    (Provided for you — use it in the functions below.)
    """
    scaled = [x / temperature for x in logits]
    m = max(scaled)
    exps = [math.exp(x - m) for x in scaled]
    total = sum(exps)
    return [e / total for e in exps]


def greedy(logits: list[float]) -> int:
    """Return the index of the highest-logit (== highest-probability) token.

    TODO: return the argmax of `logits`. Deterministic; no randomness.
    """
    raise NotImplementedError("Implement greedy (argmax) — see the docstring TODO.")


def sample_temperature(logits: list[float], temperature: float, rng: random.Random) -> int:
    """Sample an index from softmax(logits / temperature).

    TODO:
      1. Turn the logits into probabilities with the provided `softmax`, passing
         `temperature` through.
      2. Draw one index at random according to those probabilities. (Either draw
         `rng.random()` and walk a cumulative sum until it's exceeded, or lean on
         `rng.choices(...)` with the probabilities as `weights`.)
    Lower T -> sharper distribution -> picks the top token more often.
    """
    raise NotImplementedError("Implement temperature sampling — see the TODOs.")


def sample_top_k(logits: list[float], k: int, rng: random.Random) -> int:
    """Keep only the k highest-logit tokens, renormalise, then sample.

    TODO:
      1. Find the indices of the top-k logits.
      2. Build a distribution over ONLY those k (softmax over their logits, or
         zero-out the rest and renormalise).
      3. Sample an index from that restricted distribution. The returned index
         must always be one of the top-k.
    """
    raise NotImplementedError("Implement top-k sampling — see the TODOs.")


def sample_top_p(logits: list[float], p: float, rng: random.Random) -> int:
    """Nucleus sampling: keep the smallest set of tokens whose cumulative
    probability ≥ p, renormalise, then sample.

    TODO:
      1. probs = softmax(logits)
      2. Sort tokens by probability, descending (keep track of original indices).
      3. Walk down accumulating probability; keep tokens until the running sum
         ≥ p (always keep at least the top-1).
      4. Renormalise over the kept set and sample an index from it. The returned
         index must always be one of the kept tokens.
    """
    raise NotImplementedError("Implement top-p (nucleus) sampling — see the TODOs.")


def main() -> None:
    rng = random.Random(42)  # seeded so runs are reproducible
    print("Logits     :", LOGITS)
    print("Probabilities (T=1):", [round(p, 3) for p in softmax(LOGITS)])
    print()
    print("greedy                 ->", greedy(LOGITS))
    print("temperature(T=0.5)     ->", sample_temperature(LOGITS, 0.5, rng))
    print("temperature(T=2.0)     ->", sample_temperature(LOGITS, 2.0, rng))
    print("top_k(k=2)             ->", sample_top_k(LOGITS, 2, rng))
    print("top_p(p=0.9)           ->", sample_top_p(LOGITS, 0.9, rng))


if __name__ == "__main__":
    main()
