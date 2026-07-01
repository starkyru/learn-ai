"""
Task 1 🟢 — Parse documents.

Extract text from PDF, HTML, and Markdown files into a normalized record
so downstream tasks can treat all formats identically.

What you'll learn:
  - Why "read the file" is nontrivial for real-world document formats
  - How PDF layout breaks naive text extraction (columns, footers, tables)
  - How to strip HTML boilerplate so only body text reaches the LLM
  - The value of a single normalized schema across all formats

How to run:
  uv run python modules/11-document-ingestion/py/01_parse_documents.py

Python deps (not in stdlib):
  - pypdf or pdfplumber  (PDF parsing)  — `uv add pypdf` or `uv add pdfplumber`
  - beautifulsoup4       (HTML parsing)  — `uv add beautifulsoup4`
  - httpx                (HTML fetching) — `uv add httpx`

The HTML fallback (no BS4) uses stdlib urllib + regex; it is less accurate
but keeps the exercise runnable without installing anything.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Normalized document record
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """A parsed document ready for cleaning and chunking."""

    text: str
    source: str                       # file path or URL
    format: str                       # "pdf" | "html" | "markdown"
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parser implementations
# ---------------------------------------------------------------------------


def parse_markdown(path: str | Path) -> Document:
    """
    Parse a Markdown file.

    Hints:
      - Read the whole file as UTF-8 text (`Path(path).read_text(...)`).
      - Find a title: scan for the first H1 heading (a line beginning with "# ")
        and take the text after the marker; fall back to the file's stem if there
        is no H1.
      - Return a `Document`: the raw Markdown as `text` (cleaning is task 2),
        `source` as the path string, `format` "markdown", and a `metadata` dict
        carrying the title.
    """
    raise NotImplementedError("TODO: implement parse_markdown()")


def parse_html_bs4(path_or_url: str) -> Document:
    """
    Parse an HTML file or URL using BeautifulSoup (preferred).

    Hints:
      - Get the HTML string: fetch it (httpx or urllib) when `path_or_url` looks
        like an "http..." URL, otherwise read it from disk.
      - Parse it with `BeautifulSoup(html, "html.parser")`.
      - Strip boilerplate: for the navigation/header/footer/script/style tags,
        remove each matching element from the tree entirely (decompose them) so
        their text never reaches the body.
      - Pick a title from the <title> element, falling back to the first <h1>.
      - Get the visible body text via `soup.get_text(...)` (choose a newline
        separator and strip whitespace).
      - Return a `Document` with `format` "html" and the title in `metadata`.
      - Import guard: put `from bs4 import BeautifulSoup` inside a try/except so
        an ImportError falls through to `parse_html_fallback()`.
    """
    raise NotImplementedError("TODO: implement parse_html_bs4()")


def parse_html_fallback(path_or_url: str) -> Document:
    """
    Parse HTML using only stdlib (urllib + re) — less accurate, always available.

    Hints:
      - Fetch/read the HTML as a string (same source logic as parse_html_bs4).
      - Use `re.sub` to drop entire <script>...</script> and <style>...</style>
        blocks first, then to strip every remaining tag (replace tags with a
        space so words don't run together), then to collapse whitespace runs.
      - Pull the title out of the <title>...</title> element with `re.search`.
      - Return a `Document` with `format` "html".
    """
    raise NotImplementedError("TODO: implement parse_html_fallback()")


def parse_html(path_or_url: str) -> Document:
    """Dispatch to BS4 parser or stdlib fallback."""
    try:
        return parse_html_bs4(path_or_url)
    except ImportError:
        return parse_html_fallback(path_or_url)


def parse_pdf(path: str | Path) -> Document:
    """
    Parse a PDF file using pypdf (or pdfplumber as an alternative).

    Hints:
      - Import `PdfReader` from pypdf *inside* the function; if the import fails,
        raise an ImportError whose message tells the user to `uv add pypdf`.
      - Open the file with `PdfReader(path)` and extract text one page at a time
        (each page has an `.extract_text()` that may return None — coalesce to "").
      - Join the pages with a visible page-break separator so downstream chunking
        can split on page boundaries.
      - Return a `Document` with `format` "pdf" and `metadata` carrying the page
        count (`len(reader.pages)`) and a title (the PDF's own metadata title, or
        the file stem as fallback).
    """
    raise NotImplementedError("TODO: implement parse_pdf()")


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------


def parse_document(path_or_url: str) -> Document:
    """
    Detect format from extension (or URL) and dispatch to the right parser.

    TODO: implement this function.

    Rules:
      - Ends with .pdf              → parse_pdf()
      - Ends with .html or .htm     → parse_html()
      - Ends with .md or .markdown  → parse_markdown()
      - Starts with "http"          → parse_html() (assume HTML URL)
      - Otherwise                   → raise ValueError("Unsupported format: ...")
    """
    raise NotImplementedError("TODO: implement parse_document()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).parent.parent / "sample_docs"


def main() -> None:
    targets = [
        str(SAMPLE_DIR / "intro_to_rag.md"),
        str(SAMPLE_DIR / "vector_databases.html"),
    ]

    for target in targets:
        print(f"\n{'='*60}")
        print(f"Parsing: {target}")
        doc = parse_document(target)
        print(f"  Format   : {doc.format}")
        print(f"  Source   : {doc.source}")
        print(f"  Metadata : {doc.metadata}")
        print(f"  Length   : {len(doc.text)} chars")
        preview = doc.text[:300].replace("\n", " ").strip()
        print(f"  Preview  : {preview}...")


if __name__ == "__main__":
    main()
