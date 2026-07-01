"""
Task 5 🟡 — Encoder vs decoder: same attention, different mask (BERT vs GPT).

What you'll learn:
  - The classic interview question "what's the difference between BERT and GPT?"
    made concrete: BOTH use exactly the scaled dot-product attention you built in
    Task 1. What differs is the MASK (none vs causal) and the training OBJECTIVE
    (masked-token prediction vs next-token prediction).
  - Bidirectional (encoder / BERT-style) attention: no mask — every position sees
    the whole sequence, left AND right. Great contextual representations; useless
    for left-to-right generation (it would see the answer).
  - Causal (decoder / GPT-style) attention: the Task-1 mask — position i sees only
    j <= i. Enables generation; but a position can never use its RIGHT context.
  - The masked-token readout experiment: replace one token with [MASK], run one
    round of attention, and ask "which vocabulary token is this position's
    contextual representation now closest to?" When the disambiguating word sits
    to the RIGHT of the mask, bidirectional attention recovers the true token and
    causal attention provably cannot (its view of every sequence is identical).

The math (all pieces from Task 1, minus/plus the mask):

  Full (bidirectional) attention — NO mask:
    scores  = Q @ K.T / sqrt(d_k)        shape (n, n)
    weights = softmax(scores)            row-wise, each row sums to 1
    output  = weights @ V                every position mixes ALL positions

  Causal attention — Task 1's additive mask:
    mask[i, j] = 0     if j <= i
    mask[i, j] = -inf  if j >  i         (use NEG_INF)
    weights = softmax(scores + mask)     future weights become exactly 0

  Future mass (how much a weight matrix "looks right"):
    per row i: sum of weights[i, j] over j > i; report the mean over rows.
    Causal must give exactly 0. Bidirectional gives a healthy chunk.

  Nearest-token readout (cosine argmax):
    cos(r, e) = (r . e) / (|r| * |e|)
    prediction = the vocab index whose embedding maximises cos with the
    position's contextual representation.

No ML library. Only numpy.

How to run:
  uv run python modules/01d-transformer/py/05_encoder_vs_decoder.py

The harness builds a tiny vocabulary, five toy sentences whose masked token is
determined by its RIGHT neighbour, and prints the acceptance evidence. The four
core functions are left as TODOs for you.
"""

from __future__ import annotations

import numpy as np

NEG_INF = -1e9  # a large negative number; "-inf" for masking purposes

D_MODEL = 16  # embedding dimension
MASK_POS = 2  # the position we hide in every toy sentence


def softmax(z: np.ndarray) -> np.ndarray:
    """Numerically-stable softmax over the last axis. Provided."""
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


# ---------------------------------------------------------------------------
# Toy vocabulary + sentences  (provided — do not edit)
# ---------------------------------------------------------------------------
#
# A miniature "distributional" embedding table. Function words and sounds get
# one-hot embeddings; each ANIMAL's embedding is built from the contexts it
# appears in (the company it keeps — word2vec's idea in miniature):
#
#   emb(animal_i) = ( emb(the) + emb(big) + emb(today) + emb(sound_i) ) / 2
#
# So "cat" points along {the, big, today, meow}; "dog" along {the, big, today,
# woof}; only the SOUND distinguishes the animals. Every toy sentence is
#
#   the  big  <animal_i>  <sound_i>  today
#    0    1       2           3        4
#
# and we hide position 2 with [MASK]. The LEFT context ("the big") is identical
# across all five sentences — only the RIGHT neighbour (the sound) says which
# animal is hidden. That is exactly what a causal model can never see.


def build_vocab() -> tuple[list[str], np.ndarray]:
    """Return (token_names, E) where E[i] is the embedding of token i."""
    names = [
        "the",
        "big",
        "today",
        "[MASK]",  # 0..3  one-hot e0..e3
        "meow",
        "woof",
        "moo",
        "quack",
        "baa",  # 4..8  one-hot e4..e8
        "cat",
        "dog",
        "cow",
        "duck",
        "sheep",  # 9..13 context-built
    ]
    E = np.zeros((len(names), D_MODEL))
    for i in range(9):  # one-hot function words, mask, sounds
        E[i, i] = 1.0
    for a in range(5):  # animal a: (e_the + e_big + e_today + e_sound) / 2
        E[9 + a] = (E[0] + E[1] + E[2] + E[4 + a]) / 2.0  # unit norm
    return names, E


def make_sequences() -> list[tuple[list[int], int]]:
    """
    Five sentences "the big <animal> <sound> today", already masked.

    Returns a list of (token_ids, true_id): token_ids has [MASK] (id 3) at
    MASK_POS; true_id is the animal that belongs there.
    """
    seqs = []
    for a in range(5):
        animal, sound = 9 + a, 4 + a
        token_ids = [0, 1, 3, sound, 2]  # the big [MASK] <sound> today
        seqs.append((token_ids, animal))
    return seqs


# ---------------------------------------------------------------------------
# Core functions — implement these
# ---------------------------------------------------------------------------


def full_attention(Q: np.ndarray, K: np.ndarray, V: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    BIDIRECTIONAL (encoder / BERT-style) scaled dot-product attention — no mask.

    Args:
      Q : queries, shape (n, d_k)
      K : keys,    shape (n, d_k)
      V : values,  shape (n, d_v)

    Returns:
      (output, weights)
        output  : (n, d_v)  — every position's mix of ALL value vectors
        weights : (n, n)    — each row a probability distribution summing to 1

    This is Task 1's scaled_dot_product_attention with the mask branch deleted:
    nothing stops position i from attending to j > i.

    TODO: implement. Steps:
      - Form the raw scores as Q @ K.T, scaled by dividing by sqrt(d_k)
        (d_k = K.shape[-1]). Do NOT add any mask.
      - Push the scores through the provided softmax() (it is row-wise stable).
      - Multiply the weights by V to get the (n, d_v) output.
      - Return the (output, weights) pair.
    """
    # TODO: implement bidirectional (unmasked) attention
    raise NotImplementedError("TODO: implement full_attention()")


def causal_attention(Q: np.ndarray, K: np.ndarray, V: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    CAUSAL (decoder / GPT-style) scaled dot-product attention — Task 1's mask.

    Same signature and return as full_attention, but position i must put ZERO
    weight on every j > i.

    TODO: implement. Steps:
      - Form the scaled scores exactly as in full_attention.
      - Build the (n, n) additive causal mask from Task 1: 0 on and below the
        diagonal, NEG_INF strictly above it (np.triu(..., k=1) selects the
        strictly-upper triangle). n = Q.shape[0].
      - Add the mask to the scores BEFORE the provided softmax().
      - Multiply the weights by V and return the (output, weights) pair.
    """
    # TODO: implement causal (masked) attention
    raise NotImplementedError("TODO: implement causal_attention()")


def attention_mass_on_future(weights: np.ndarray) -> float:
    """
    How much attention mass lands on FUTURE positions (j > i)?

    Args:
      weights : (n, n) attention-weight matrix (rows sum to 1)

    Returns:
      float — for each row i, sum the entries strictly above the diagonal
      (weights[i, j] for j > i), then average those row sums over all n rows.

    A causal weight matrix must score exactly 0.0; a bidirectional one on this
    data scores well above 0.

    TODO: implement. np.triu(weights, k=1) keeps exactly the strictly-upper-
    triangular entries (and zeroes the rest); combine its per-row sums with a
    mean over rows.
    """
    # TODO: implement the future-mass measurement
    raise NotImplementedError("TODO: implement attention_mass_on_future()")


def nearest_token(repr_vec: np.ndarray, E: np.ndarray) -> int:
    """
    Which vocabulary token is this contextual representation closest to?

    Args:
      repr_vec : (d,) one position's representation after attention
      E        : (vocab, d) embedding table — E[i] is token i's embedding

    Returns:
      int — the vocab index with the highest COSINE similarity to repr_vec:
        cos(r, e_i) = (r . e_i) / (|r| * |e_i|)

    TODO: implement. Steps:
      - Compute the dot product of repr_vec against every row of E (one
        matrix-vector product gives all of them at once).
      - Divide by the norms: |repr_vec| times each row's norm
        (np.linalg.norm with axis=-1 gives all row norms).
      - Return the argmax as a plain int.
    """
    # TODO: implement the cosine-similarity argmax readout
    raise NotImplementedError("TODO: implement nearest_token()")


# ---------------------------------------------------------------------------
# Harness — complete, do not edit
# ---------------------------------------------------------------------------


def main() -> None:
    names, E = build_vocab()
    seqs = make_sequences()
    n_seq = len(seqs)

    print("=" * 66)
    print("Task 5 — Encoder vs decoder: same attention, different mask")
    print("=" * 66)
    print(f"  vocab={len(names)}  d={D_MODEL}  sentences={n_seq}  masked position={MASK_POS}\n")

    # ── [1] Where does the attention mass go? ─────────────────────────────────
    X0 = E[seqs[0][0]]  # first masked sentence, embedded: (5, d)
    _, w_full = full_attention(X0, X0, X0)
    _, w_causal = causal_attention(X0, X0, X0)
    mass_full = attention_mass_on_future(w_full)
    mass_causal = attention_mass_on_future(w_causal)
    print("[1] Mean attention mass on FUTURE positions (j > i):")
    print(f"    bidirectional (no mask): {mass_full:.4f}")
    print(f"    causal (masked)        : {mass_causal:.10f}   (must be exactly 0)\n")

    # ── [2] Masked-token readout ──────────────────────────────────────────────
    print("[2] Masked-token readout — after ONE round of self-attention, which")
    print("    vocab token is the [MASK] position's representation closest to?")
    print("    (the disambiguating word is the sound, to the RIGHT of the mask)\n")
    bi_correct = 0
    causal_correct = 0
    for token_ids, true_id in seqs:
        X = E[token_ids]  # (5, d) — [MASK] embedding at MASK_POS
        out_bi, _ = full_attention(X, X, X)
        out_ca, _ = causal_attention(X, X, X)
        pred_bi = nearest_token(out_bi[MASK_POS], E)
        pred_ca = nearest_token(out_ca[MASK_POS], E)
        bi_correct += int(pred_bi == true_id)
        causal_correct += int(pred_ca == true_id)
        sentence = " ".join(names[t] for t in token_ids)
        print(
            f"    '{sentence}'  true={names[true_id]:<5}  "
            f"bidirectional→{names[pred_bi]:<6}  causal→{names[pred_ca]}"
        )
    print(f"\n    bidirectional correct: {bi_correct}/{n_seq}")
    print(f"    causal        correct: {causal_correct}/{n_seq}")
    print("    The left context 'the big' is IDENTICAL in all five sentences, so")
    print("    the causal representation of the mask is the same every time — it")
    print("    cannot recover a token that only the RIGHT neighbour determines.")
    print("    That's why BERT (masked-LM) trains with bidirectional attention,")
    print("    and why GPT (next-token) has to accept the causal mask.\n")

    # ── Acceptance checks ─────────────────────────────────────────────────────
    ok_causal_zero = mass_causal == 0.0
    ok_full_mass = mass_full > 0.2
    ok_bi = bi_correct >= 4
    ok_lt = causal_correct < bi_correct

    print("Acceptance:")
    print(
        f"  [{'x' if ok_causal_zero else ' '}] causal future mass == 0 exactly (got {mass_causal})"
    )
    print(
        f"  [{'x' if ok_full_mass else ' '}] bidirectional future mass > 0.2 (got {mass_full:.4f})"
    )
    print(
        f"  [{'x' if ok_bi else ' '}] bidirectional recovers the masked token in "
        f">= 4/{n_seq} sentences (got {bi_correct}/{n_seq})"
    )
    print(
        f"  [{'x' if ok_lt else ' '}] causal recovers strictly fewer "
        f"({causal_correct} < {bi_correct})"
    )

    if ok_causal_zero and ok_full_mass and ok_bi and ok_lt:
        print("\n  All acceptance checks passed.")
    else:
        print("\n  Some checks failed — revisit your implementation.")


if __name__ == "__main__":
    main()
