# /// script
# requires-python = ">=3.10"
# dependencies = ["markdown>=3.6"]
# ///
"""Build a static HTML site from the course markdown.

Converts README.md, CURRICULUM.md, docs/*.md, and every modules/*/README.md
into styled HTML pages under site/, with:
  - an index grouping every module by theme (nothing skipped),
  - Mermaid diagrams rendered from ```mermaid fences,
  - internal .md links rewritten to the matching .html page.

Run:  uv run scripts/build_site.py        # then open site/index.html
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

MD_EXTENSIONS = ["fenced_code", "tables", "toc", "sane_lists", "attr_list"]

PAGE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — learn-ai</title>
<style>
:root {{
  --bg: #ffffff; --fg: #1f2328; --muted: #59636e; --border: #d1d9e0;
  --code-bg: #f6f8fa; --link: #0969da; --accent: #8250df;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0d1117; --fg: #e6edf3; --muted: #9198a1; --border: #3d444d;
    --code-bg: #161b22; --link: #4493f8; --accent: #ab7df8;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0 auto; max-width: 860px; padding: 2rem 1.25rem 4rem;
  background: var(--bg); color: var(--fg);
  font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
}}
nav.crumbs {{
  font-size: 0.875rem; color: var(--muted); margin-bottom: 1.5rem;
  padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);
}}
nav.crumbs a {{ color: var(--link); text-decoration: none; }}
h1, h2, h3, h4 {{ line-height: 1.25; margin-top: 1.6em; margin-bottom: 0.5em; }}
h1 {{ font-size: 1.9rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
h2 {{ font-size: 1.4rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }}
a {{ color: var(--link); }}
code {{
  background: var(--code-bg); border-radius: 6px; padding: 0.15em 0.35em;
  font: 0.875em ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
}}
pre {{
  background: var(--code-bg); border-radius: 8px; padding: 1rem;
  overflow-x: auto; border: 1px solid var(--border);
}}
pre code {{ background: none; padding: 0; }}
table {{ border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }}
th, td {{ border: 1px solid var(--border); padding: 0.4rem 0.75rem; text-align: left; }}
th {{ background: var(--code-bg); }}
blockquote {{
  margin: 1rem 0; padding: 0.25rem 1rem; color: var(--muted);
  border-left: 4px solid var(--border);
}}
.mermaid {{ background: none; border: none; text-align: center; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 2rem 0; }}
</style>
</head>
<body>
<nav class="crumbs">{crumbs}</nav>
{body}
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  mermaid.initialize({{ startOnLoad: true, theme: dark ? "dark" : "default" }});
</script>
</body>
</html>
"""

MERMAID_FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def collect_sources() -> dict[Path, Path]:
    """Map each source markdown file to its output path inside site/."""
    pages: dict[Path, Path] = {}
    pages[ROOT / "README.md"] = SITE / "readme.html"
    pages[ROOT / "CURRICULUM.md"] = SITE / "curriculum.html"
    for doc in sorted((ROOT / "docs").glob("*.md")):
        pages[doc] = SITE / "docs" / f"{doc.stem.lower()}.html"
    for readme in sorted((ROOT / "modules").glob("*/README.md")):
        pages[readme] = SITE / "modules" / f"{readme.parent.name}.html"
    return pages


def protect_mermaid(md_text: str) -> tuple[str, list[str]]:
    """Swap ```mermaid fences for placeholders so the md parser skips them."""
    blocks: list[str] = []

    def stash(m: re.Match[str]) -> str:
        blocks.append(m.group(1))
        return f"\x00MERMAID{len(blocks) - 1}\x00"

    return MERMAID_FENCE.sub(stash, md_text), blocks


def restore_mermaid(html: str, blocks: list[str]) -> str:
    for i, block in enumerate(blocks):
        placeholder = f"\x00MERMAID{i}\x00"
        div = f'<pre class="mermaid">\n{block}</pre>'
        html = html.replace(f"<p>{placeholder}</p>", div).replace(placeholder, div)
    return html


def rewrite_links(html: str, src: Path, pages: dict[Path, Path], out: Path) -> str:
    """Point internal links at generated pages; leave external links alone."""

    def fix(m: re.Match[str]) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "#", "mailto:")):
            return m.group(0)
        target, _, frag = href.partition("#")
        resolved = (src.parent / target).resolve()
        if resolved in pages:
            rel = pages[resolved].relative_to(SITE)
            depth = len(out.relative_to(SITE).parts) - 1
            new = "../" * depth + str(rel) + (f"#{frag}" if frag else "")
            return f'href="{new}"'
        # Directory link like modules/05-rag/ → its README page.
        readme = (resolved / "README.md") if resolved.is_dir() else None
        if readme and readme in pages:
            rel = pages[readme].relative_to(SITE)
            depth = len(out.relative_to(SITE).parts) - 1
            return f'href="{"../" * depth}{rel}"'
        return m.group(0)

    return re.sub(r'href="([^"]+)"', fix, html)


def first_heading(md_text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def crumbs_for(out: Path) -> str:
    depth = len(out.relative_to(SITE).parts) - 1
    home = "../" * depth + "index.html"
    return f'<a href="{home}">learn-ai</a> / {out.stem}'


def render(src: Path, out: Path, pages: dict[Path, Path]) -> str:
    text = src.read_text(encoding="utf-8")
    title = first_heading(text, src.stem)
    protected, blocks = protect_mermaid(text)
    body = markdown.markdown(protected, extensions=MD_EXTENSIONS)
    body = restore_mermaid(body, blocks)
    body = rewrite_links(body, src, pages, out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        PAGE_TMPL.format(title=title, crumbs=crumbs_for(out), body=body),
        encoding="utf-8",
    )
    return title


THEMES: list[tuple[str, list[str]]] = [
    (
        "Foundations — ML, deep learning, LLMs & transformers",
        [
            "01-fundamentals",
            "01b-ml-foundations",
            "01c-deep-learning",
            "01d-transformer",
            "01e-trees-ensembles",
            "01f-stats-foundations",
        ],
    ),
    ("Building with LLMs", ["00-setup", "02-llm-integration", "03-prompting"]),
    (
        "Embeddings, retrieval & RAG",
        [
            "04-embeddings-vectors",
            "05-rag",
            "05b-advanced-rag",
            "11-document-ingestion",
            "12-text-to-sql",
        ],
    ),
    (
        "Agents",
        [
            "06-agents",
            "06b-langgraph",
            "06c-agent-frameworks",
            "06d-agent-memory",
            "16-context-engineering",
            "17-mcp",
            "18-computer-use",
        ],
    ),
    (
        "Training & inference",
        [
            "13-fine-tuning",
            "13b-alignment",
            "14-local-inference-optimization",
            "15-reasoning-test-time-compute",
        ],
    ),
    (
        "Modalities & applications",
        ["08-classification", "09-computer-vision", "10-image-generation", "19-audio-speech"],
    ),
    (
        "Production",
        [
            "07-advanced-production",
            "20-ai-security",
            "21-llmops-eval",
            "22-ai-product-ux",
            "23-capstone",
        ],
    ),
]


def build_index(pages: dict[Path, Path], titles: dict[Path, str]) -> None:
    by_module = {
        p.parent.name: (p, titles[p]) for p in pages if p.parent.parent == ROOT / "modules"
    }
    sections = [
        "<h1>learn-ai — course site</h1>",
        "<p>Every module and reference doc, grouped by theme. "
        "Built by <code>scripts/build_site.py</code>.</p>",
        "<h2>Start here</h2><ul>",
        '<li><a href="readme.html">Course overview (README)</a></li>',
        '<li><a href="curriculum.html">Full curriculum</a></li>',
        "</ul>",
    ]
    listed: set[str] = set()
    for theme, ids in THEMES:
        sections.append(f"<h2>{theme}</h2><ul>")
        for mod_id in ids:
            if mod_id in by_module:
                src, title = by_module[mod_id]
                rel = pages[src].relative_to(SITE)
                sections.append(f'<li><a href="{rel}">{title}</a></li>')
                listed.add(mod_id)
        sections.append("</ul>")
    orphans = sorted(set(by_module) - listed)
    if orphans:
        sections.append("<h2>Other modules</h2><ul>")
        for mod_id in orphans:
            src, title = by_module[mod_id]
            rel = pages[src].relative_to(SITE)
            sections.append(f'<li><a href="{rel}">{title}</a></li>')
        sections.append("</ul>")
    sections.append("<h2>Reference docs</h2><ul>")
    for src, out in pages.items():
        if out.parent == SITE / "docs":
            sections.append(f'<li><a href="{out.relative_to(SITE)}">{titles[src]}</a></li>')
    sections.append("</ul>")
    index = SITE / "index.html"
    index.write_text(
        PAGE_TMPL.format(
            title="Course index",
            crumbs='<a href="index.html">learn-ai</a>',
            body="\n".join(sections),
        ),
        encoding="utf-8",
    )


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    pages = collect_sources()
    titles = {src: render(src, out, pages) for src, out in pages.items()}
    build_index(pages, titles)
    print(f"Built {len(pages) + 1} pages → {SITE}/index.html")


if __name__ == "__main__":
    main()
