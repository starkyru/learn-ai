"""test_fundamentals.py — unit tests for the WORKED fundamentals (pytest).

What it teaches:
    The from-scratch pieces (BPE, cosine) have simple, checkable invariants:
    BPE must round-trip losslessly, and cosine has known values for identical /
    orthogonal vectors. These tests never touch the network — they exercise the
    pure logic, which is exactly what unit tests are for.

How to run (from the repo root):
    uv run pytest modules/01-fundamentals/py/test_fundamentals.py
"""

from __future__ import annotations

import math

from bpe import CORPUS, BPETokenizer
from cosine import cosine, dot, norm


# --- BPE -----------------------------------------------------------------


def _trained_tokenizer() -> BPETokenizer:
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=50)
    return tok


def test_bpe_roundtrip_on_sample() -> None:
    tok = _trained_tokenizer()
    sample = "the model reads tokens"
    assert tok.decode(tok.encode(sample)) == sample


def test_bpe_roundtrip_on_full_corpus() -> None:
    tok = _trained_tokenizer()
    assert tok.decode(tok.encode(CORPUS)) == CORPUS


def test_bpe_roundtrip_on_unseen_and_unicode() -> None:
    # Byte-level BPE has no "unknown token": anything UTF-8-encodable round-trips,
    # even characters never present in the training corpus.
    tok = _trained_tokenizer()
    for s in ["café — 日本語 😀", "zzz!!!", "", "  spaces  "]:
        assert tok.decode(tok.encode(s)) == s


def test_bpe_actually_merges() -> None:
    # Training on a repetitive corpus must learn at least one merge, and merging
    # must shorten the encoding of corpus-like text vs. raw bytes.
    tok = _trained_tokenizer()
    assert len(tok.merges) > 0
    text = "the model reads tokens"
    assert len(tok.encode(text)) < len(text.encode("utf-8"))


def test_bpe_vocab_size() -> None:
    tok = _trained_tokenizer()
    assert tok.vocab_size == 256 + len(tok.merges)


# --- cosine --------------------------------------------------------------


def test_cosine_identity_is_one() -> None:
    v = [1.0, 2.0, 3.0, 4.0]
    assert math.isclose(cosine(v, v), 1.0, rel_tol=1e-9)


def test_cosine_orthogonal_is_zero() -> None:
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert math.isclose(cosine(a, b), 0.0, abs_tol=1e-12)


def test_cosine_opposite_is_minus_one() -> None:
    a = [1.0, 2.0, 3.0]
    b = [-1.0, -2.0, -3.0]
    assert math.isclose(cosine(a, b), -1.0, rel_tol=1e-9)


def test_cosine_zero_vector_is_safe() -> None:
    # Undefined angle for a zero vector — our implementation returns 0.0, not NaN.
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_dot_and_norm() -> None:
    assert dot([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]) == 32.0
    assert math.isclose(norm([3.0, 4.0]), 5.0, rel_tol=1e-12)
