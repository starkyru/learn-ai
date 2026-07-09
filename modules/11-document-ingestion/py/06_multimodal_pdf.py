"""
Task 6 🟡 — Multimodal PDF retrieval.

What you'll learn:
  - Tasks 1–5 extracted *digital text*. But real PDFs carry meaning the text
    layer loses: scanned pages, tables rendered as lines, charts, screenshots.
    `pypdf` returns "" for those. You need to look at the *pixels*.
  - The multimodal-retrieval pattern: render each page to an IMAGE, ask a
    vision LLM to describe it (transcribe tables, read figures) → a text
    "caption", embed the caption, and retrieve by text similarity. At answer
    time you hand the matched page IMAGE back to the vision model, so generation
    reasons over pixels, not a lossy transcription. Retrieve by text, answer
    over the image.
  - Where the `llm_core` abstraction leaks: `LLMProvider.chat()` is TEXT-ONLY.
    Image inputs require the raw vendor SDK (openai / anthropic), exactly as in
    module 09 Task 3. Embeddings still go through `provider.embed()`.

How to run (needs a vision-capable provider):
  # Render sample pages (once) + run, with OpenAI:
  LLM_PROVIDER=openai uv run python modules/11-document-ingestion/py/06_multimodal_pdf.py
  # or Anthropic:
  LLM_PROVIDER=anthropic uv run python modules/11-document-ingestion/py/06_multimodal_pdf.py

Note: OpenAI/Anthropic have vision but only OpenAI has embeddings. Anthropic has
no embed() — so with LLM_PROVIDER=anthropic, set EMBED_PROVIDER=openai (or
ollama) for the embedding step. The harness reads that env var.

Deps: `uv sync --extra ingest` (now includes pymupdf for rendering) and the
`openai` / `anthropic` SDK for the vision call.
"""

from __future__ import annotations

import base64
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_core import get_provider

PAGES_DIR = Path(__file__).parent.parent / "sample_docs" / "pages"

CAPTION_PROMPT = (
    "You are transcribing a document page for a search index. Write a thorough "
    "plain-text description of EVERYTHING on this page: headings, body text, and "
    "especially any TABLE (transcribe every row and number) or figure. Do not "
    "summarise away the numbers — a search query may ask for them."
)


# ---------------------------------------------------------------------------
# Provided: render a small sample PDF to page images (so the task is offline)
# ---------------------------------------------------------------------------


def ensure_sample_pages() -> list[Path]:
    """Create sample_docs/pages/*.png once, using pymupdf. Returns the paths.

    Page 2 holds a TABLE — the case where text extraction underperforms and a
    vision model shines. This is harness plumbing, not the exercise.
    """
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(PAGES_DIR.glob("page_*.png"))
    if existing:
        return existing

    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise ImportError("Run: uv sync --extra ingest  (installs pymupdf)") from e

    pages_text = [
        "Acme Cloud — Annual Report 2024\n\nOverview\n\nAcme Cloud delivers "
        "managed vector databases to enterprises. Fiscal 2024 saw record "
        "adoption across the financial and healthcare sectors, with net revenue "
        "retention above 120 percent.",
        "Quarterly Revenue (USD millions)\n\n"
        "Quarter      Revenue    Growth\n"
        "Q1 2024        41.2       8%\n"
        "Q2 2024        47.9      16%\n"
        "Q3 2024        55.3      15%\n"
        "Q4 2024        63.8      15%\n\n"
        "Full-year revenue reached 208.2 million, up from 151.0 million in 2023.",
        "Risk Factors\n\nConcentration: the top ten customers account for 38 "
        "percent of revenue. Competition from open-source vector indexes may "
        "pressure pricing. Foreign-exchange movements affect the 22 percent of "
        "revenue billed outside the United States.",
    ]
    doc = fitz.open()
    paths: list[Path] = []
    for i, text in enumerate(pages_text, start=1):
        page = doc.new_page()
        page.insert_text((72, 96), text, fontsize=13, fontname="courier")
        pix = page.get_pixmap(dpi=120)
        out = PAGES_DIR / f"page_{i}.png"
        pix.save(out)
        paths.append(out)
    doc.close()
    print(f"Rendered {len(paths)} sample pages → {PAGES_DIR}")
    return paths


def image_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Provided: the vision call (raw vendor SDK — llm_core.chat is text-only).
# Copied in the same shape as module 09 Task 3. Reused for both captioning
# (index time) and answering (query time) by swapping the prompt.
# ---------------------------------------------------------------------------


def vision_ask(image_path: Path, prompt: str) -> str:
    """Send an image + text prompt to a vision LLM, return the reply text."""
    provider = os.getenv("LLM_PROVIDER", "openai")
    b64 = image_to_base64(image_path)
    mime = "image/png"

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                    ],
                }
            ],
        )
        return resp.choices[0].message.content or ""

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return msg.content[0].text

    raise RuntimeError(f"Provider '{provider}' has no vision. Use openai or anthropic.")


def _embedder() -> Any:
    """Embeddings provider (Anthropic has none — fall back via EMBED_PROVIDER)."""
    name = os.getenv("EMBED_PROVIDER") or os.getenv("LLM_PROVIDER", "openai")
    if name == "anthropic":
        name = "openai"
    return get_provider(name=name)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    ma = math.sqrt(sum(x * x for x in a))
    mb = math.sqrt(sum(x * x for x in b))
    return dot / (ma * mb) if ma and mb else 0.0


# ---------------------------------------------------------------------------
# The exercise — implement the multimodal retrieval flow
# ---------------------------------------------------------------------------


@dataclass
class PageEntry:
    path: Path
    caption: str
    vector: list[float] = field(default_factory=list)


@dataclass
class PageHit:
    path: Path
    caption: str
    score: float


def build_multimodal_index(page_paths: list[Path], embedder: Any) -> list[PageEntry]:
    """Caption each page image with the vision model, then embed the captions.

    TODO: implement this function.

    Steps:
      1. For each page path, get a text caption with `vision_ask(path, CAPTION_PROMPT)`.
      2. Embed ALL captions in one `embedder.embed([...])` call.
      3. Return one `PageEntry(path, caption, vector)` per page, aligned by order.

    Note: the vision call is the leaky-abstraction part (vendor SDK); embedding
    stays on `llm_core`. This is the index-time cost, paid once.
    """
    raise NotImplementedError("TODO: implement build_multimodal_index()")


def retrieve_pages(query: str, index: list[PageEntry], embedder: Any, k: int = 2) -> list[PageHit]:
    """Retrieve the top-k pages whose captions best match the query.

    TODO: implement this function.

    Steps:
      1. Embed the query with `embedder.embed([query])`.
      2. Score each PageEntry by `cosine(query_vec, entry.vector)`.
      3. Return the top-k as `PageHit` sorted by score descending.
    """
    raise NotImplementedError("TODO: implement retrieve_pages()")


def answer_over_page(query: str, page_path: Path) -> str:
    """Answer the query by looking at the retrieved page IMAGE (not the caption).

    TODO: implement this function.

    Steps:
      1. Build an answer prompt that instructs the model to answer the query
         using ONLY what is visible on the page, and to say so if the page
         doesn't contain the answer (interpolate `query`).
      2. Return `vision_ask(page_path, that_prompt)`.

    This is the payoff: we retrieved by text, but generate over the pixels, so
    numbers in a table are read straight from the image.
    """
    raise NotImplementedError("TODO: implement answer_over_page()")


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def main() -> None:
    page_paths = ensure_sample_pages()
    embedder = _embedder()
    print(f"Vision: {os.getenv('LLM_PROVIDER', 'openai')} | embed: {embedder.name}\n")

    print("Building multimodal index (captioning pages)…")
    index = build_multimodal_index(page_paths, embedder)
    print(f"  indexed {len(index)} pages\n")

    queries = [
        "What was Q3 2024 revenue?",  # answer lives in the TABLE (page 2)
        "How concentrated is the customer base?",  # risk factors (page 3)
    ]
    for q in queries:
        print(f'Question: "{q}"')
        hits = retrieve_pages(q, index, embedder, k=2)
        for h in hits:
            print(f"  [{h.score:.4f}] {h.path.name}")
        top = hits[0]
        print(f"  → answering over {top.path.name}:")
        print(f"    {answer_over_page(q, top.path)}\n")

    print("Reflection:")
    print("  1. Did the table question retrieve page_2 (the table page)?")
    print("  2. Would pypdf's text layer have captured those numbers?")
    print("  3. Why answer over the image instead of the caption text?")


if __name__ == "__main__":
    main()
