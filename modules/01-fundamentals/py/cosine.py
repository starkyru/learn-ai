"""cosine.py — embeddings & cosine similarity by hand (Task 2, 🟡 WORKED).

What it teaches:
    Cosine similarity is the engine of semantic search and RAG. We implement it
    from first principles (no numpy), embed ~6 sentences with a real provider,
    then print a similarity matrix and a nearest-neighbour ranking so you can
    SEE that semantically related sentences score higher.

How to run (from the repo root):
    uv run python modules/01-fundamentals/py/cosine.py

Provider note:
    Needs an embeddings model. Works out of the box with Ollama:
        ollama pull nomic-embed-text
    OpenAI and NVIDIA also have embeddings. Anthropic does NOT — Claude has no
    embeddings endpoint, so this script forces an embeddings-capable provider if
    LLM_PROVIDER is set to anthropic.
"""

from __future__ import annotations

import math
import os

from llm_core import get_provider

# Sentences in three loose topic clusters. Cosine should reveal the clusters:
#   0,1 -> dogs/pets   2,3 -> programming   4,5 -> weather
SENTENCES = [
    "The dog chased the ball across the park.",
    "My puppy loves to play fetch outside.",
    "Python is a popular programming language.",
    "I write a lot of code in TypeScript and Python.",
    "It is raining heavily and the sky is grey.",
    "The weather today is wet and stormy.",
]


def dot(a: list[float], b: list[float]) -> float:
    """Dot product: sum of element-wise products. a·b = Σ aᵢbᵢ."""
    return sum(x * y for x, y in zip(a, b))


def norm(a: list[float]) -> float:
    """Euclidean magnitude (L2 norm): ‖a‖ = √(Σ aᵢ²)."""
    return math.sqrt(dot(a, a))


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity: cos(a,b) = (a·b) / (‖a‖‖b‖), in [-1, 1].

    Measures the ANGLE between vectors, ignoring their length — so it compares
    direction (meaning) rather than magnitude. Guards against a zero vector
    (undefined angle) by returning 0.0.
    """
    denom = norm(a) * norm(b)
    if denom == 0.0:
        return 0.0
    return dot(a, b) / denom


def pick_embedding_provider():
    """Return a provider that can embed (anthropic can't)."""
    requested = os.getenv("LLM_PROVIDER", "ollama")
    if requested == "anthropic":
        print("Anthropic has no embeddings endpoint — falling back to ollama.\n")
        return get_provider("ollama")
    return get_provider()


def main() -> None:
    llm = pick_embedding_provider()
    print(f"Embedding with: {llm.name} ({llm.embed_model})\n")

    result = llm.embed(SENTENCES)
    vecs = result.vectors
    n = len(vecs)

    # --- Full similarity matrix ------------------------------------------
    print("Cosine similarity matrix (higher = more similar):\n")
    header = "      " + "".join(f"  s{j} " for j in range(n))
    print(header)
    for i in range(n):
        row = "".join(f" {cosine(vecs[i], vecs[j]):+.2f}" for j in range(n))
        print(f"  s{i} {row}")

    # Sanity check: a vector vs itself must be ~1.0.
    print(f"\nSelf-similarity cosine(s0, s0) = {cosine(vecs[0], vecs[0]):.4f} (expect ~1.0)")

    # --- Nearest neighbours of one query ---------------------------------
    query_idx = 0
    ranked = sorted(
        (j for j in range(n) if j != query_idx),
        key=lambda j: cosine(vecs[query_idx], vecs[j]),
        reverse=True,
    )
    print(f'\nNearest neighbours of s{query_idx}: "{SENTENCES[query_idx]}"')
    for rank, j in enumerate(ranked, start=1):
        sim = cosine(vecs[query_idx], vecs[j])
        print(f"  {rank}. s{j} ({sim:+.3f})  {SENTENCES[j]}")

    print(
        "\nNotice: the top neighbour should be the other pet sentence (s1), "
        "scoring higher than the programming/weather sentences."
    )


if __name__ == "__main__":
    main()
