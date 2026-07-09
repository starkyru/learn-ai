"""
Task 5 🟡 — Semantic chunking.

What you'll learn:
  - Fixed/sentence/overlap chunkers (Task 3) ignore *meaning* — they cut at a
    character count or a sentence count, so one chunk can straddle two topics.
  - Semantic chunking places boundaries where the *topic shifts*: embed each
    sentence, walk the document, and start a new chunk wherever consecutive
    sentences become embedding-distant (a "semantic breakpoint").
  - How a percentile threshold turns a noisy distance signal into breakpoints
    without hand-tuning an absolute cutoff per corpus.

How to run:
  uv run python modules/04-embeddings-vectors/py/05_semantic_chunking.py

Needs an embedding provider (LLM_PROVIDER=openai|ollama|nvidia|lmstudio|gemini;
NOT anthropic — it has no embed()).
"""

from __future__ import annotations

import re
from typing import Any

from llm_core import get_provider

# ---------------------------------------------------------------------------
# Sample document — two clearly different topics glued together, so a good
# semantic chunker should place a boundary near the topic switch.
# ---------------------------------------------------------------------------

DOC = """
The espresso machine forces near-boiling water through finely ground coffee
under nine bars of pressure. The result is a concentrated shot topped with
crema, the reddish-brown foam of emulsified oils. Grind size is the single
biggest lever: too coarse and the water rushes through sour and thin, too fine
and it chokes, over-extracting into bitterness. Baristas dial in a shot by
tasting and adjusting the grind until the flow takes roughly 25 to 30 seconds.

The transit protocol assigns each train a movement authority: a block of track
it may occupy exclusively. Signals at block boundaries turn red once a train
enters, and only clear again after it has left and the block is proven vacant.
This fixed-block scheme trades capacity for safety, because a whole block is
reserved even when the train occupies a few metres of it. Modern moving-block
systems shrink that reservation to a safety envelope around the train itself,
letting trains run far closer together.
""".strip()


# ---------------------------------------------------------------------------
# Sentence splitting (provided) — reused from Task 3's heuristic.
# ---------------------------------------------------------------------------


def split_sentences(text: str) -> list[str]:
    """Split on whitespace that follows sentence-ending punctuation."""
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in parts if s.strip()]


def cosine(a: list[float], b: list[float]) -> float:
    """Inline cosine similarity — keeps the file self-contained."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


# ---------------------------------------------------------------------------
# Semantic chunking — implement this
# ---------------------------------------------------------------------------


def percentile(values: list[float], p: float) -> float:
    """Return the p-th percentile (0–100) of `values` via linear interpolation.

    TODO: implement this helper.

    Steps:
      1. Sort a copy of `values` ascending.
      2. Map p to a fractional rank: `rank = (p / 100) * (len - 1)`.
      3. Interpolate between the two neighbouring sorted samples
         (`floor(rank)` and `ceil(rank)`) by the fractional part of `rank`.

    Edge case: a single-element list returns that element.
    """
    raise NotImplementedError("TODO: implement percentile()")


def semantic_chunks(
    text: str,
    provider: Any,
    breakpoint_percentile: float = 90.0,
) -> list[str]:
    """Chunk `text` at semantic breakpoints.

    A breakpoint sits *between* sentence i and i+1 when the two are unusually
    embedding-distant — i.e. the topic just shifted.

    TODO: implement this function.

    Steps:
      1. `split_sentences(text)` → list of sentences. If ≤ 1, return [text].
      2. Embed ALL sentences in one `provider.embed(sentences)` call; use
         `.vectors`.
      3. For each adjacent pair (i, i+1), compute a *distance*
         `1 - cosine(v[i], v[i+1])`. You get `len(sentences) - 1` distances.
      4. Threshold: `t = percentile(distances, breakpoint_percentile)`. Any gap
         with distance > t is a breakpoint (start a new chunk after sentence i).
      5. Walk the sentences, accumulating into the current chunk; when you hit a
         breakpoint index, flush the accumulated sentences (joined with " ")
         and start fresh. Flush the trailing chunk at the end.

    Return: list of chunk strings (each one or more sentences joined by " ").
    Note: a higher percentile ⇒ fewer, larger chunks (only the sharpest topic
    shifts qualify).
    """
    raise NotImplementedError("TODO: implement semantic_chunks()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def fixed_sentence_baseline(text: str, per_chunk: int = 3) -> list[str]:
    """Naive baseline: N sentences per chunk, ignoring meaning."""
    sents = split_sentences(text)
    return [" ".join(sents[i : i + per_chunk]) for i in range(0, len(sents), per_chunk)]


def show(name: str, chunks: list[str]) -> None:
    print(f"\n[{name}] {len(chunks)} chunks")
    for i, c in enumerate(chunks):
        print(f'  {i}: "{c[:90]}{"…" if len(c) > 90 else ""}"')


def main() -> None:
    provider = get_provider()
    print(f"\nProvider: {provider.name} | embed model: {provider.embed_model}")

    show("fixed 3-sentence baseline", fixed_sentence_baseline(DOC, 3))
    show("semantic", semantic_chunks(DOC, provider, breakpoint_percentile=90.0))

    print("\nReflection:")
    print("  1. Did the semantic chunker put a boundary at the coffee→trains switch?")
    print("  2. Raise breakpoint_percentile to 95 — do you get fewer chunks?")
    print("  3. Where would fixed-size chunking have split mid-topic?")


if __name__ == "__main__":
    main()
