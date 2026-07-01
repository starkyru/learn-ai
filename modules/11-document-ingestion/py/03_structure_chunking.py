"""
Task 3 🟡 — Structure-aware chunking.

Naive fixed-size chunking (from module 04) ignores document structure and can
split in the middle of a thought or, worse, separate a heading from its body.
Section-aware chunking respects document structure so each chunk is semantically
self-contained.

What you'll learn:
  - Why chunk boundaries matter for retrieval quality
  - How to detect section boundaries from headings (Markdown H1/H2/H3)
  - Token-aware sizing: estimating tokens without a tokenizer (chars / 4)
  - Carrying metadata (source, section title, page number) into each chunk
  - Side-by-side comparison: naive fixed-size vs. section-aware

How to run:
  uv run python modules/11-document-ingestion/py/03_structure_chunking.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Chunk type (richer than module 04 — carries metadata)
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    # metadata keys: section, page, char_offset, estimated_tokens


# ---------------------------------------------------------------------------
# Token estimation (no tokenizer dependency)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """
    Rough token count: divide character count by 4.

    This approximates the GPT-family tokenizer ratio for English prose.
    Not exact, but avoids a tiktoken/transformers dependency for this task.
    """
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Chunkers
# ---------------------------------------------------------------------------


def naive_fixed_size_chunks(
    text: str,
    source: str,
    max_tokens: int = 200,
    overlap_tokens: int = 20,
) -> list[Chunk]:
    """
    Naive fixed-size chunker from module 04 (reproduced here for comparison).

    Hints:
      - Work in words (split on whitespace) so you never cut mid-word.
      - Grow a window until adding the next word would push the chunk past the
        `max_tokens` budget — remember the chars/token ratio from
        `estimate_tokens`, so the char budget is roughly `max_tokens * 4`.
      - Emit a `Chunk`, then slide the window forward but leave `overlap_tokens`
        worth of words behind so adjacent chunks share context (advance by the
        non-overlapping span).
      - Give each chunk a stable `id` like `"{source}-naive-{index}"` and record
        its `estimate_tokens(...)` under a metadata key such as
        "estimated_tokens".
      - Return the list of `Chunk` objects.
    """
    raise NotImplementedError("TODO: implement naive_fixed_size_chunks()")


def section_chunks(
    text: str,
    source: str,
    max_tokens: int = 300,
    overlap_tokens: int = 30,
) -> list[Chunk]:
    """
    Section-aware chunker: split first by Markdown headings, then sub-chunk
    any section that is too large.

    Hints:
      - First break the document into sections keyed by heading. Scan the lines
        for Markdown ATX headings (levels H1–H3) and start a new section at each
        one; capture each section as (heading_text, body_text). Any text before
        the first heading is its own section — label it something like
        "(preamble)".
      - For each section, decide whether it fits: if
        `estimate_tokens(heading + body)` is within `max_tokens`, emit it as a
        single `Chunk`. If it is too big, sub-chunk the body with
        `naive_fixed_size_chunks(...)` (passing `max_tokens`/`overlap_tokens`) and
        prepend the heading text to every sub-chunk so the section title always
        travels with the content.
      - Give chunks stable ids that encode both the section and sub-chunk index
        (e.g. `"{source}-section-{section_index}-{sub_index}"`), and store the
        section heading plus `estimate_tokens(...)` in each chunk's metadata.
      - Return the list of `Chunk` objects.
    """
    raise NotImplementedError("TODO: implement section_chunks()")


# ---------------------------------------------------------------------------
# Harness: side-by-side comparison
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent / "sample_docs"


def main() -> None:
    import importlib.util

    # Load task 1's parse_document without circular import
    spec = importlib.util.spec_from_file_location(
        "parse_documents",
        Path(__file__).parent / "01_parse_documents.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    parse_document = mod.parse_document

    md_path = str(SAMPLE_DIR / "intro_to_rag.md")
    doc = parse_document(md_path)
    text = doc.text

    print(f"\nDocument: {md_path}")
    print(f"  Total chars: {len(text)}  |  Estimated tokens: {estimate_tokens(text)}\n")

    naive = naive_fixed_size_chunks(text, source=md_path, max_tokens=200)
    sectioned = section_chunks(text, source=md_path, max_tokens=200)

    print(f"Naive fixed-size : {len(naive)} chunks")
    for c in naive:
        print(f"  [{c.id}] ~{c.metadata.get('estimated_tokens', '?')}t  "
              f"— {c.text[:60].replace(chr(10),' ')}...")

    print(f"\nSection-aware    : {len(sectioned)} chunks")
    for c in sectioned:
        section = c.metadata.get("section", "(preamble)")
        print(f"  [{c.id}] §{section!r} ~{c.metadata.get('estimated_tokens', '?')}t  "
              f"— {c.text[:60].replace(chr(10),' ')}...")

    print("\nKey observation: section-aware chunks have meaningful section titles "
          "in metadata and never split a heading from its body.")


if __name__ == "__main__":
    main()
