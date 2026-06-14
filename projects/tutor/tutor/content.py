"""Module content discovery + light retrieval for the tutor CLI.

This is the "R" in RAG, kept deliberately small so it runs on a laptop with a
local model. We:

1. Discover every ``modules/*/README.md`` (the lesson text — the course's source
   of truth for what the learner is studying).
2. Given a question, pick the most relevant module README(s). We try real
   embeddings via ``provider.embed`` when available, and fall back to plain
   keyword overlap so the tool still works when the provider has no embeddings
   endpoint (e.g. Anthropic) or the embedding model isn't pulled in Ollama.

You'll recognize this pattern after module 04 (embeddings & vectors) and
module 05 (RAG).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Module:
    """One course module, loaded from its README.md."""

    module_id: str  # e.g. "04"
    slug: str  # e.g. "04-embeddings-vectors"
    title: str  # first markdown H1, or the slug if none
    path: Path  # path to the README.md
    text: str  # full README text

    @property
    def excerpt(self) -> str:
        """A short, prompt-friendly slice of the README (keeps context small)."""
        return self.text[:6000]


# --------------------------------------------------------------------------- #
# Locating the repo + the modules/ dir
# --------------------------------------------------------------------------- #

def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` (or this file) until we find a ``modules/`` dir.

    Falls back to two levels up from this file (``projects/tutor/tutor`` ->
    repo root) so the CLI keeps working even if invoked oddly.
    """
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "modules").is_dir():
            return parent
    # Fallback: tutor/ -> projects/ -> repo root
    return Path(__file__).resolve().parents[2]


_ID_RE = re.compile(r"^(\d{2})[-_]?(.*)$")


def _module_id_from_slug(slug: str) -> str:
    m = _ID_RE.match(slug)
    return m.group(1) if m else slug


def _first_h1(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def discover_modules(repo_root: Path | None = None) -> list[Module]:
    """Scan ``modules/*/README.md`` and return them sorted by id.

    Modules without a README.md are skipped (the course is built incrementally,
    so this is expected — handle it gracefully upstream).
    """
    root = repo_root or find_repo_root()
    modules_dir = root / "modules"
    found: list[Module] = []
    if not modules_dir.is_dir():
        return found
    for child in sorted(modules_dir.iterdir()):
        if not child.is_dir():
            continue
        readme = child / "README.md"
        if not readme.is_file():
            continue
        try:
            text = readme.read_text(encoding="utf-8")
        except OSError:
            continue
        slug = child.name
        found.append(
            Module(
                module_id=_module_id_from_slug(slug),
                slug=slug,
                title=_first_h1(text, slug),
                path=readme,
                text=text,
            )
        )
    return found


def get_module(modules: list[Module], wanted: str) -> Module | None:
    """Resolve a user-supplied module reference to a Module.

    Accepts an id ("04"), a slug ("04-embeddings-vectors" / "embeddings-vectors"),
    or a loose topic substring matched against the title/slug.
    """
    if not wanted:
        return None
    w = wanted.strip().lower()
    w_id = w.zfill(2) if w.isdigit() else w

    # Exact id or slug.
    for m in modules:
        if m.module_id == w_id or m.slug.lower() == w:
            return m
    # Slug without the numeric prefix, or substring of slug/title.
    for m in modules:
        slug_no_id = _ID_RE.sub(r"\2", m.slug).lower()
        if w in (slug_no_id, m.slug.lower()) or w in m.title.lower():
            return m
    return None


# --------------------------------------------------------------------------- #
# Light retrieval
# --------------------------------------------------------------------------- #

_WORD_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "on",
    "how", "what", "why", "do", "does", "i", "my", "this", "that", "with", "as",
    "be", "are", "can", "should", "would", "module", "modules", "learn",
}


def _tokens(text: str) -> list[str]:
    return [t for t in _WORD_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


def _keyword_scores(question: str, modules: list[Module]) -> list[float]:
    """Overlap of question terms with each README, lightly weighted by title."""
    q = set(_tokens(question))
    scores: list[float] = []
    for m in modules:
        body = set(_tokens(m.text))
        title = set(_tokens(m.title))
        if not q:
            scores.append(0.0)
            continue
        overlap = len(q & body)
        title_overlap = len(q & title)
        scores.append(overlap + 2.0 * title_overlap)
    return scores


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _embedding_scores(question: str, modules: list[Module], provider) -> list[float] | None:
    """Try to score by embedding cosine similarity. Returns None on any failure
    (no embed endpoint, model not pulled, network error) so the caller can fall
    back to keywords. We embed a title+excerpt per module to keep inputs small.
    """
    embed = getattr(provider, "embed", None)
    if embed is None:
        return None
    docs = [f"{m.title}\n\n{m.excerpt[:2000]}" for m in modules]
    try:
        result = embed([question, *docs])
        vectors = result.vectors
    except NotImplementedError:
        return None  # e.g. Anthropic has no embeddings endpoint
    except Exception:
        return None  # model missing, offline, etc. — degrade to keywords
    if not vectors or len(vectors) != len(docs) + 1:
        return None
    q_vec = vectors[0]
    return [_cosine(q_vec, dv) for dv in vectors[1:]]


def select_relevant(
    question: str,
    modules: list[Module],
    provider=None,
    top_k: int = 2,
) -> list[Module]:
    """Return the top_k modules most relevant to the question.

    Uses embeddings when ``provider`` is given and supports them; otherwise (or
    on any embedding failure) falls back to keyword overlap. Always returns at
    least one module if any exist.
    """
    if not modules:
        return []
    scores: list[float] | None = None
    if provider is not None:
        scores = _embedding_scores(question, modules, provider)
    if scores is None:
        scores = _keyword_scores(question, modules)

    ranked = sorted(zip(modules, scores), key=lambda pair: pair[1], reverse=True)
    # If nothing matched at all (all-zero scores), still return the top_k by
    # natural order so the learner gets *some* grounding.
    chosen = [m for m, _ in ranked[: max(1, top_k)]]
    return chosen
