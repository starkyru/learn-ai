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

    TODO: implement this function.

    Steps (apply in order):
      1. Remove ATX headings markers: re.sub(r"^#{1,6}\\s+", "", text, flags=MULTILINE)
         — keep the heading text, just strip the "#" characters.
      2. Remove bold/italic markers: `**`, `__`, `*`, `_`
         (use re.sub to remove paired delimiters around words).
      3. Remove inline code backticks: `code` → code.
      4. Remove fenced code blocks (``` ... ```) entirely.
      5. Remove Markdown table rows (lines containing "|") by keeping only the
         cell text: strip "|" chars and collapse whitespace.
      6. Strip link syntax: [text](url) → text.
      7. Return cleaned text.
    """
    raise NotImplementedError("TODO: implement strip_markdown_syntax()")


def collapse_whitespace(text: str) -> str:
    """
    Normalise whitespace: collapse runs of spaces/tabs and trim blank lines.

    TODO: implement this function.

    Steps:
      1. Replace \\r\\n and \\r with \\n.
      2. Replace horizontal whitespace runs (spaces/tabs) with a single space
         on each line.
      3. Strip leading/trailing space from each line.
      4. Collapse runs of 3+ blank lines to at most 2.
      5. Return stripped result.
    """
    raise NotImplementedError("TODO: implement collapse_whitespace()")


def remove_boilerplate_lines(text: str, min_chars: int = 20) -> str:
    """
    Heuristically drop lines that are likely navigation/boilerplate.

    TODO: implement this function.

    Heuristics (drop a line if ANY of these apply):
      - Shorter than `min_chars` characters AND all uppercase or title-case
        (e.g. "HOME", "ABOUT US", "Contact").
      - Matches a common nav pattern: only words + "|" + "/" characters
        (regex: r"^[\\w\\s|/·•–—]+$" and len < 60).
      - Is a pure horizontal rule: re.match(r"^[-=*_]{3,}$").
      - Starts with "Cookie" or "Privacy" or "Terms" (common footer patterns).

    Keep all other lines. Return the joined result.
    """
    raise NotImplementedError("TODO: implement remove_boilerplate_lines()")


def fingerprint(text: str, n: int = 5) -> frozenset[str]:
    """
    Compute a set of n-gram shingle hashes for near-duplicate detection.

    TODO: implement this function.

    Steps:
      1. Tokenise: words = text.lower().split()
      2. Build shingles: n consecutive words joined with " "
         e.g. for n=5, words[i:i+5] for i in range(len(words)-n+1)
      3. Hash each shingle: hashlib.md5(shingle.encode()).hexdigest()[:8]
      4. Return frozenset of hashes.

    Used by dedupe_blocks() below.
    """
    raise NotImplementedError("TODO: implement fingerprint()")


def dedupe_blocks(
    blocks: list[str], similarity_threshold: float = 0.8
) -> list[str]:
    """
    Remove near-duplicate text blocks using Jaccard similarity of shingle sets.

    TODO: implement this function.

    Algorithm:
      1. For each block, compute fingerprint(block).
      2. Keep a list of accepted fingerprints.
      3. For a new block, compute Jaccard similarity against each accepted:
           jaccard(A, B) = |A ∩ B| / |A ∪ B|
      4. If the max Jaccard with any accepted block >= similarity_threshold,
         skip this block (it's a near-duplicate).
      5. Otherwise add it to accepted.
      6. Return accepted blocks in original order.

    Tip: if the block is very short (< 10 words), always keep it (short blocks
    have unreliable shingle similarity).
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

    TODO: implement this function.

    Steps:
      1. If format == "markdown": call strip_markdown_syntax(doc.text).
         Otherwise: just use doc.text (HTML boilerplate was stripped in task 1).
      2. collapse_whitespace(text).
      3. remove_boilerplate_lines(text).
      4. Split into paragraphs (split on "\\n\\n"), run dedupe_blocks(),
         rejoin with "\\n\\n".
      5. Return CleanedDocument with the cleaned text and original metadata.
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
