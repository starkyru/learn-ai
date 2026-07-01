"""
Task 2 🟡 — Clean & normalize documents.

Raw parsed text contains boilerplate, excessive whitespace, duplicate passages,
and noise from layout artifacts. Cleaning before chunking and embedding
dramatically improves retrieval quality.

What you'll learn:
  - Why raw extraction is noisy (footers, menus, whitespace, encoding issues)
  - Simple heuristics for boilerplate removal (line-length, repetition rate)
  - Near-duplicate detection using MinHash or simple fingerprinting
  - How table formatting degrades embedding quality vs. prose

How to run:
  uv run python modules/11-document-ingestion/py/02_clean_normalize.py
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Document type — mirrors 01_parse_documents.Document so this file is runnable
# standalone. In a real project you would import from the shared module.


@dataclass
class Document:
    text: str
    source: str
    format: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cleaning pipeline
# ---------------------------------------------------------------------------


def strip_markdown_syntax(text: str) -> str:
    """
    Remove Markdown formatting characters, leaving prose.

    Hints — apply these transforms in order (reach for `re.sub` on each):
      1. ATX heading markers: strip the leading "#" run (and its space) at the
         start of a line, keeping the heading text. A MULTILINE anchor helps.
      2. Bold/italic emphasis: unwrap paired `**`, `__`, `*`, `_` delimiters,
         keeping the wrapped words.
      3. Inline code: drop the surrounding backticks, keep the code text.
      4. Fenced code blocks (``` ... ```): remove them entirely (dot-matches-all).
      5. Markdown table rows (lines containing "|"): keep only the cell text —
         remove the "|" characters and collapse the extra whitespace.
      6. Links `[text](url)`: keep just the link text.
      7. Return the cleaned text.
    """
    raise NotImplementedError("TODO: implement strip_markdown_syntax()")


def collapse_whitespace(text: str) -> str:
    """
    Normalise whitespace: collapse runs of spaces/tabs and trim blank lines.

    Hints:
      - Normalise line endings to "\\n" first (handle both \\r\\n and lone \\r).
      - Collapse each line's horizontal whitespace (spaces/tabs) to a single space
        and strip its leading/trailing space.
      - Cap vertical whitespace: collapse runs of 3+ blank lines down to 2.
      - Return the trimmed result.
    """
    raise NotImplementedError("TODO: implement collapse_whitespace()")


def remove_boilerplate_lines(text: str, min_chars: int = 20) -> str:
    """
    Heuristically drop lines that are likely navigation/boilerplate.

    Hints — drop a line if ANY of these signals fire (keep everything else):
      - It is shorter than `min_chars` AND looks like a menu label (all-caps or
        title-case), e.g. "HOME", "ABOUT US", "Contact".
      - It looks like a nav strip: short (say < 60 chars) and made only of words
        plus separator glyphs like "|", "/", or bullet dashes.
      - It is a pure horizontal rule (a short line of only -, =, *, or _).
      - It starts with a common footer word such as "Cookie", "Privacy", "Terms".
    Return the surviving lines joined back together.
    """
    raise NotImplementedError("TODO: implement remove_boilerplate_lines()")


def fingerprint(text: str, n: int = 5) -> frozenset[str]:
    """
    Compute a set of n-gram shingle hashes for near-duplicate detection.

    Hints:
      - Tokenise the lowercased text into words.
      - Form the shingles: every window of `n` consecutive words, joined into one
        string (slide the window one word at a time across the token list).
      - Hash each shingle to a short digest with `hashlib` (a truncated md5 hex is
        plenty here) so comparisons are cheap.
      - Return the hashes as a `frozenset[str]`.

    Used by dedupe_blocks() below.
    """
    raise NotImplementedError("TODO: implement fingerprint()")


def dedupe_blocks(
    blocks: list[str], similarity_threshold: float = 0.8
) -> list[str]:
    """
    Remove near-duplicate text blocks using Jaccard similarity of shingle sets.

    Hints — a greedy one-pass dedupe:
      - Walk the blocks in order, keeping the fingerprint sets you have already
        accepted.
      - For each new block, compute its `fingerprint(...)` and its Jaccard
        similarity against every accepted set:
            jaccard(A, B) = |A ∩ B| / |A ∪ B|
      - If it is near-duplicate of any accepted block (max Jaccard >= the
        `similarity_threshold`), skip it; otherwise accept it.
      - Return the accepted blocks in their original order.

    Tip: very short blocks (< ~10 words) have unreliable shingle overlap — always
    keep them rather than risk dropping distinct content.
    """
    raise NotImplementedError("TODO: implement dedupe_blocks()")


# ---------------------------------------------------------------------------
# Main cleaner
# ---------------------------------------------------------------------------


@dataclass
class CleanedDocument:
    text: str
    source: str
    format: str
    metadata: dict


def clean(doc: Document) -> CleanedDocument:
    """
    Run the full cleaning pipeline on a parsed Document.

    Hints — chain the helpers above in a sensible order:
      - Markdown documents need `strip_markdown_syntax()` first; other formats
        already had their boilerplate stripped in task 1, so start from doc.text.
      - Run the text through `collapse_whitespace()` and
        `remove_boilerplate_lines()`.
      - Split the text into paragraph blocks (on blank-line boundaries), pass them
        through `dedupe_blocks()`, and rejoin them.
      - Return a `CleanedDocument` carrying the cleaned text and the original
        source/format/metadata.
    """
    raise NotImplementedError("TODO: implement clean()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent / "sample_docs"


def main() -> None:
    import importlib.util

    # Dynamically import task 1 so this file works standalone
    spec = importlib.util.spec_from_file_location(
        "parse_documents",
        Path(__file__).parent / "01_parse_documents.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore
    spec.loader.exec_module(mod)  # type: ignore
    parse_doc_fn = mod.parse_document

    for filename in ["intro_to_rag.md", "vector_databases.html"]:
        path = str(SAMPLE_DIR / filename)
        print(f"\n{'='*60}")
        print(f"Cleaning: {path}")

        raw = parse_doc_fn(path)
        print(f"  Raw length  : {len(raw.text)} chars")

        cleaned = clean(raw)
        print(f"  Clean length: {len(cleaned.text)} chars")
        reduction = 100 * (1 - len(cleaned.text) / max(len(raw.text), 1))
        print(f"  Reduction   : {reduction:.1f}%")
        preview = cleaned.text[:300].replace("\n", " ").strip()
        print(f"  Preview     : {preview}...")


if __name__ == "__main__":
    main()
