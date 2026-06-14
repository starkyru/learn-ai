"""News retrieval.

We treat the open web (via RSS) as our corpus. The default source is Google
News' search RSS endpoint, which returns recent articles for an arbitrary
query — perfect for "news about <topic>". Extra RSS feeds can be added via
config.

The interesting (and testable) logic here is *not* the HTTP call but the
normalization that follows it:

* ``NewsItem`` — one normalized record (title, url, source, published, summary).
* ``filter_recent`` — drop anything older than N hours.
* ``dedupe`` — collapse near-duplicate stories that several outlets ran.

Those two are pure functions over data, so the test-suite exercises them with
fixtures and never touches the network.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

log = logging.getLogger("news_agent.sources")

# Build a Google News search RSS URL for a topic + locale.
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q={query}&hl={lang}&gl={country}&ceid={country}:{lang0}"
)

# A polite, real-looking UA — some feeds reject the default urllib agent.
USER_AGENT = (
    "Mozilla/5.0 (compatible; learn-ai-news-agent/0.1; +https://github.com/learn-ai)"
)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9 ]+")


@dataclass
class NewsItem:
    """A single normalized news article."""

    title: str
    url: str
    source: str
    published: datetime | None
    summary: str

    def short_summary(self, limit: int = 280) -> str:
        s = self.summary.strip()
        if len(s) <= limit:
            return s
        return s[: limit - 1].rstrip() + "…"


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def strip_html(text: str) -> str:
    """Turn an RSS HTML snippet into plain text."""
    if not text:
        return ""
    no_tags = _HTML_TAG_RE.sub(" ", text)
    # Decode the handful of entities feedparser tends to leave behind.
    no_tags = (
        no_tags.replace("&amp;", "&")
        .replace("&nbsp;", " ")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return _WS_RE.sub(" ", no_tags).strip()


def _normalize_title(title: str) -> str:
    """Lowercased, punctuation-free, whitespace-collapsed title for comparison.

    Google News often suffixes the source: "Headline - The Verge". We drop a
    trailing ' - Source' so the same story from two outlets compares equal."""
    t = title.lower()
    t = re.sub(r"\s+-\s+[^-]+$", "", t)  # trailing " - Source"
    t = _NON_WORD_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip()


def _canonical_url(url: str) -> str:
    """Strip tracking params + fragments so URL-equality is meaningful."""
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return url
    keep = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query)
        if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
    ]
    query = urllib.parse.urlencode(keep)
    path = parts.path.rstrip("/")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, ""))


def _title_similarity(a: str, b: str) -> float:
    na, nb = _normalize_title(a), _normalize_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


# --------------------------------------------------------------------------- #
# Pure data transforms (network-free, unit-tested)
# --------------------------------------------------------------------------- #
def filter_recent(
    items: list[NewsItem],
    hours: int,
    *,
    now: datetime | None = None,
    keep_undated: bool = True,
) -> list[NewsItem]:
    """Keep items published within the last ``hours``.

    Items with no parseable date are kept by default (``keep_undated``), since
    some feeds omit timestamps and dropping them would lose real news."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)
    out: list[NewsItem] = []
    for it in items:
        if it.published is None:
            if keep_undated:
                out.append(it)
            continue
        published = it.published
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published >= cutoff:
            out.append(it)
    return out


def dedupe(items: list[NewsItem], *, title_threshold: float = 0.82) -> list[NewsItem]:
    """Remove duplicate / near-duplicate stories.

    Two items are considered the same when they share a canonical URL OR have
    titles whose similarity ratio exceeds ``title_threshold``. The first
    occurrence wins (we keep input order, which lets callers pre-sort by
    recency/importance)."""
    kept: list[NewsItem] = []
    seen_urls: set[str] = set()
    for it in items:
        canon = _canonical_url(it.url) if it.url else ""
        if canon and canon in seen_urls:
            continue
        is_dup = False
        for k in kept:
            if _title_similarity(it.title, k.title) >= title_threshold:
                is_dup = True
                break
        if is_dup:
            continue
        kept.append(it)
        if canon:
            seen_urls.add(canon)
    return kept


# --------------------------------------------------------------------------- #
# Feed parsing
# --------------------------------------------------------------------------- #
def _entry_published(entry: object) -> datetime | None:
    """Extract a UTC datetime from a feedparser entry, if present."""
    import time

    for attr in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, attr, None)
        if struct:
            try:
                return datetime.fromtimestamp(time.mktime(struct), tz=timezone.utc)
            except (OverflowError, ValueError, OSError):
                continue
    return None


def _entry_source(entry: object, fallback: str) -> str:
    """Best-effort source/outlet name for an entry."""
    src = getattr(entry, "source", None)
    if src is not None:
        title = getattr(src, "title", None) or (src.get("title") if isinstance(src, dict) else None)
        if title:
            return str(title).strip()
    # Google News encodes the outlet as a trailing ' - Outlet' in the title.
    title = getattr(entry, "title", "") or ""
    m = re.search(r"\s+-\s+([^-]+)$", title)
    if m:
        return m.group(1).strip()
    return fallback


def google_news_url(topic: str, lang: str = "en-US", country: str = "US") -> str:
    """Construct the Google News search RSS URL for a topic."""
    query = urllib.parse.quote(topic)
    lang0 = lang.split("-")[0]
    return GOOGLE_NEWS_RSS.format(
        query=query, lang=lang, country=country, lang0=lang0
    )


def parse_feed(content: bytes | str, *, fallback_source: str = "RSS") -> list[NewsItem]:
    """Parse raw feed bytes/text into normalized ``NewsItem``s.

    Pure-ish: it only depends on feedparser, not the network, so it can be
    fed canned fixture content in tests."""
    import feedparser

    parsed = feedparser.parse(content)
    items: list[NewsItem] = []
    for entry in getattr(parsed, "entries", []) or []:
        title = strip_html(getattr(entry, "title", "") or "")
        if not title:
            continue
        # Prefer a clean source, then strip the ' - Outlet' suffix from titles.
        source = _entry_source(entry, fallback_source)
        clean_title = re.sub(r"\s+-\s+[^-]+$", "", title).strip() or title
        summary = strip_html(
            getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        )
        items.append(
            NewsItem(
                title=clean_title,
                url=(getattr(entry, "link", "") or "").strip(),
                source=source,
                published=_entry_published(entry),
                summary=summary,
            )
        )
    return items


def _http_get(url: str, timeout: float = 15.0) -> bytes:
    """Fetch a URL with httpx, following redirects, with a real UA."""
    import httpx

    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, */*"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content


def fetch_feed(url: str, *, fallback_source: str = "RSS") -> list[NewsItem]:
    """Fetch + parse one feed URL. Network/parse errors are logged, not raised,
    so one bad feed never kills the whole run; returns ``[]`` on failure."""
    try:
        raw = _http_get(url)
    except Exception as exc:  # noqa: BLE001 — we deliberately degrade gracefully
        log.warning("Failed to fetch feed %s: %s", url, exc)
        return []
    try:
        return parse_feed(raw, fallback_source=fallback_source)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to parse feed %s: %s", url, exc)
        return []


def fetch_news(
    topic: str,
    *,
    recency_hours: int = 30,
    extra_feeds: list[str] | None = None,
    lang: str = "en-US",
    country: str = "US",
    now: datetime | None = None,
) -> list[NewsItem]:
    """Top-level retrieval: fetch Google News + any extra feeds for ``topic``,
    normalize, filter to recent, dedupe, and sort newest-first.

    Returns a possibly-empty list. Never raises on network failure — callers
    should handle the empty case (e.g. "no fresh news today")."""
    feeds: list[tuple[str, str]] = [
        (google_news_url(topic, lang=lang, country=country), "Google News")
    ]
    for f in extra_feeds or []:
        feeds.append((f, "RSS"))

    collected: list[NewsItem] = []
    for url, fallback in feeds:
        items = fetch_feed(url, fallback_source=fallback)
        log.info("Fetched %d items from %s", len(items), url)
        collected.extend(items)

    recent = filter_recent(collected, recency_hours, now=now)
    # Sort newest-first so dedupe keeps the freshest copy of a duplicated story.
    recent.sort(key=lambda i: (i.published or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    deduped = dedupe(recent)
    log.info(
        "Topic %r: %d raw -> %d recent -> %d deduped",
        topic, len(collected), len(recent), len(deduped),
    )
    return deduped
