"""bpe.py — a Byte-Pair Encoding tokenizer from scratch (Task 1, 🔴 WORKED).

What it teaches:
    What a "token" actually is. We build BPE from the byte level up: start with
    256 base tokens (one per possible byte), then repeatedly merge the most
    frequent adjacent pair into a brand-new token id. encode() applies those
    learned merges; decode() reverses them. Because we start from raw UTF-8
    bytes, EVERY possible string is representable — there is no "unknown token".

    NO tiktoken is used for the implementation. tiktoken appears ONLY at the
    bottom, in an optional comparison section, to contrast our token counts
    with a production tokenizer's.

How to run (from the repo root):
    uv run python modules/01-fundamentals/py/bpe.py

Key invariant (the thing that makes it a tokenizer and not a lossy hash):
    decode(encode(s)) == s   for every string s.
"""

from __future__ import annotations

import os

# A "symbol sequence" during training is a list of token ids. Base ids 0..255
# are the raw bytes; ids >= 256 are merged pairs we invent during training.
Pair = tuple[int, int]


# A tiny corpus, inline so the file is self-contained. Repetition is on purpose:
# BPE learns by merging FREQUENT pairs, so repeated substrings ("token", "ization",
# "the ", "ing ") give the trainer something to actually merge.
CORPUS = (
    "the quick brown fox jumps over the lazy dog. "
    "tokenization turns text into tokens. tokens are the units a model reads. "
    "byte pair encoding merges the most frequent pair, again and again. "
    "the model reads tokens, the model predicts tokens, the model is a token machine. "
    "reading and writing and reading and writing builds intuition. "
)


def get_stats(ids: list[int]) -> dict[Pair, int]:
    """Count every adjacent pair of ids in the sequence.

    For [1, 2, 3, 2, 3] the pairs are (1,2),(2,3),(3,2),(2,3) so (2,3) -> 2.
    """
    counts: dict[Pair, int] = {}
    for a, b in zip(ids, ids[1:], strict=False):
        counts[(a, b)] = counts.get((a, b), 0) + 1
    return counts


def merge(ids: list[int], pair: Pair, new_id: int) -> list[int]:
    """Replace every occurrence of `pair` in `ids` with `new_id`.

    We scan left to right; when the current and next id match the pair we emit
    new_id and skip two positions, otherwise we copy one id and advance one.
    """
    out: list[int] = []
    i = 0
    while i < len(ids):
        if i < len(ids) - 1 and ids[i] == pair[0] and ids[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(ids[i])
            i += 1
    return out


class BPETokenizer:
    """A minimal byte-level BPE tokenizer.

    Attributes:
        merges: ordered map {pair -> new_id}. Insertion order == learn order,
            which is the order encode() must re-apply them in.
        vocab:  map {id -> bytes} so decode() can reconstruct the original bytes.
    """

    def __init__(self) -> None:
        self.merges: dict[Pair, int] = {}
        # Base vocabulary: ids 0..255 map to the single byte with that value.
        self.vocab: dict[int, bytes] = {i: bytes([i]) for i in range(256)}

    def train(self, text: str, num_merges: int) -> None:
        """Learn `num_merges` merges from `text`.

        Each round: count adjacent pairs, pick the most frequent, mint a new id
        for it, and rewrite the sequence with that pair merged. Repeat.
        """
        # Start from raw bytes -> base ids. UTF-8 means non-ASCII becomes
        # multiple byte-ids, which BPE can then merge back together.
        ids = list(text.encode("utf-8"))

        for i in range(num_merges):
            stats = get_stats(ids)
            if not stats:
                break  # sequence collapsed to a single token; nothing left to merge
            # Most frequent pair. max() ties break on the pair tuple, making the
            # training deterministic (same corpus -> same merges every run).
            best = max(stats, key=lambda p: (stats[p], p))
            if stats[best] < 2:
                break  # no pair repeats; further merges would just memorise noise
            new_id = 256 + i
            self.merges[best] = new_id
            # Record the new token's bytes = concatenation of its two parts'
            # bytes. This is what lets decode() expand it later.
            self.vocab[new_id] = self.vocab[best[0]] + self.vocab[best[1]]
            ids = merge(ids, best, new_id)

    def encode(self, text: str) -> list[int]:
        """Turn a string into a list of token ids.

        We re-apply the learned merges IN THE ORDER THEY WERE LEARNED. Applying
        them in learn-order is what reproduces training-time tokenisation: a
        later merge may depend on a token created by an earlier one.
        """
        ids = list(text.encode("utf-8"))
        for pair, new_id in self.merges.items():
            ids = merge(ids, pair, new_id)
        return ids

    def decode(self, ids: list[int]) -> str:
        """Turn token ids back into the original string.

        Each id maps to a byte sequence (base ids -> 1 byte, merged ids -> the
        concatenation recorded at train time). Join them and UTF-8 decode.
        """
        data = b"".join(self.vocab[i] for i in ids)
        # errors="replace" guards against an id list that was hand-mangled into
        # an invalid byte sequence; for encode()'d input it's always clean.
        return data.decode("utf-8", errors="replace")

    @property
    def vocab_size(self) -> int:
        return len(self.vocab)


def main() -> None:
    tok = BPETokenizer()
    tok.train(CORPUS, num_merges=50)

    sample = "the model reads tokens"
    ids = tok.encode(sample)
    back = tok.decode(ids)

    print(f"Trained vocab size : {tok.vocab_size} (256 base + {len(tok.merges)} merges)")
    print(f"Sample            : {sample!r}")
    print(f"Encoded ({len(ids)} ids)   : {ids}")
    print(f"Decoded            : {back!r}")
    print(f"Round-trips losslessly: {back == sample}")
    # Self-check: the defining invariant of a tokenizer. Assert (don't just print)
    # so a regression fails loudly — including under the offline smoke runner.
    assert back == sample, f"BPE round-trip mismatch: {back!r} != {sample!r}"

    # Show the compression effect: a learned tokenizer should need far fewer
    # tokens than raw bytes for text resembling its training corpus.
    raw_bytes = len(sample.encode("utf-8"))
    print(f"\nRaw UTF-8 bytes    : {raw_bytes}")
    print(f"BPE tokens         : {len(ids)}  (fewer = better compression)")

    # Round-trip a string with non-ASCII to prove byte-level handling is lossless
    # even for characters never seen in the corpus (no 'unknown token').
    tricky = "café — 日本語 😀"
    assert tok.decode(tok.encode(tricky)) == tricky
    print(f"\nUnseen/Unicode round-trip OK: {tricky!r}")

    # The comparison downloads tiktoken's vocab on first use. In the offline
    # smoke run (OFFLINE_SMOKE / CI set) skip it so this file stays network-free;
    # the from-scratch BPE core above is what we actually verify. Normal learners
    # (no env var) still see the full production-tokenizer comparison.
    if os.environ.get("OFFLINE_SMOKE") or os.environ.get("CI"):
        print("\n--- tiktoken comparison skipped (offline smoke mode) ---")
    else:
        _tiktoken_comparison(sample)


def _tiktoken_comparison(text: str) -> None:
    """OPTIONAL: compare our token count to a production tokenizer's.

    tiktoken is the ONLY library allowed in this task, and ONLY here for
    comparison — never in the implementation above. It's skipped gracefully if
    tiktoken isn't installed (it's a base dependency via pyproject, but the
    encoding data is downloaded on first use and may be offline).
    """
    print("\n--- tiktoken comparison (production tokenizer) ---")
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")  # the GPT-3.5/4 tokenizer
        tk_ids = enc.encode(text)
        print(f"  cl100k_base vocab size : {enc.n_vocab}")
        print(f"  tiktoken tokens for {text!r}: {len(tk_ids)} -> {tk_ids}")
        print(
            "  Note: tiktoken was trained on a huge corpus, so common English "
            "words are single tokens. Our toy tokenizer, trained on a few "
            "sentences, splits more finely. Same algorithm, vastly more data."
        )
    except Exception as exc:  # noqa: BLE001 — comparison is best-effort only
        print(f"  [skipped] tiktoken unavailable: {exc}")


if __name__ == "__main__":
    main()
