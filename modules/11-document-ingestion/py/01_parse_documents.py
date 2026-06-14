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

    TODO: implement this function.

    Steps:
      1. Read the file with UTF-8 encoding.
      2. Extract the title from the first H1 heading (line starting with "# ").
      3. Return a Document with:
           text     = full file contents (raw Markdown — cleaning happens in task 2)
           source   = str(path)
           format   = "markdown"
           metadata = {"title": <extracted title or filename stem>}

    Tip: `Path(path).read_text(encoding="utf-8")` is all you need for the read.
    """
    raise NotImplementedError("TODO: implement parse_markdown()")


def parse_html_bs4(path_or_url: str) -> Document:
    """
    Parse an HTML file or URL using BeautifulSoup (preferred).

    TODO: implement this function.

    Steps:
      1. If `path_or_url` starts with "http", fetch with httpx or urllib.
         Otherwise read the file from disk.
      2. Parse with BeautifulSoup(html, "html.parser").
      3. Remove <nav>, <header>, <footer>, <script>, <style> tags entirely
         (soup.find_all(tag) → tag.decompose()).
      4. Extract the page title from <title> (fallback: first <h1>).
      5. Extract body text: soup.get_text(separator="\\n", strip=True).
      6. Return a Document with:
           text     = extracted body text
           source   = path_or_url
           format   = "html"
           metadata = {"title": <page title>}

    Import guard: wrap the `from bs4 import BeautifulSoup` inside a try/except
    ImportError and call parse_html_fallback() if BS4 is not installed.
    """
    raise NotImplementedError("TODO: implement parse_html_bs4()")


def parse_html_fallback(path_or_url: str) -> Document:
    """
    Parse HTML using only stdlib (urllib + re) — less accurate, always available.

    TODO: implement this function.

    Steps:
      1. Fetch/read the HTML as a string (same as parse_html_bs4 step 1).
      2. Strip <script>...</script> and <style>...</style> blocks with re.sub.
      3. Strip all remaining HTML tags with re.sub(r"<[^>]+>", " ", html).
      4. Collapse whitespace: re.sub(r"[ \\t]+", " ", text).
      5. Extract the title from <title>...</title> with re.search.
      6. Return a Document with format="html".
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

    TODO: implement this function.

    Steps (using pypdf):
      1. `from pypdf import PdfReader` (inside the function so the import error
         is descriptive).
      2. Open the PDF: `reader = PdfReader(path)`.
      3. Extract text page by page:
           pages_text = [page.extract_text() or "" for page in reader.pages]
      4. Join pages with "\\n\\n--- page break ---\\n\\n" so downstream chunking
         can split on page boundaries if desired.
      5. Return a Document with:
           text     = joined text
           source   = str(path)
           format   = "pdf"
           metadata = {"num_pages": len(reader.pages),
                       "title": reader.metadata.title or Path(path).stem}

    If pypdf is not installed, raise ImportError with a helpful message:
    "PDF parsing requires pypdf: uv add pypdf"
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
