"""Unit tests for the pure logic of the news agent.

These tests deliberately avoid the network and the LLM — they exercise only the
deterministic data transforms:

* dedupe        — collapses duplicate / near-duplicate items
* filter_recent — drops items older than the lookback window
* split_message — chunks long digests under Telegram's size limit
* config        — env parsing + validation

Run with:  uv run pytest projects/news-agent/test_news_agent.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from news_agent.config import _split_feeds, load_settings
from news_agent.pipeline import TELEGRAM_MAX_CHARS, split_message
from news_agent.sources import (
    NewsItem,
    dedupe,
    filter_recent,
    google_news_url,
    strip_html,
)

NOW = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)


def item(title, url="https://ex.com/a", source="Src", published=NOW, summary="s"):
    return NewsItem(title=title, url=url, source=source, published=published, summary=summary)


# --------------------------------------------------------------------------- #
# dedupe
# --------------------------------------------------------------------------- #
def test_dedupe_removes_exact_url_duplicates():
    items = [
        item("Story A", url="https://ex.com/a?utm_source=x"),
        item("Totally different headline B", url="https://ex.com/a"),  # same canonical url
    ]
    out = dedupe(items)
    assert len(out) == 1
    assert out[0].title == "Story A"


def test_dedupe_removes_near_duplicate_titles():
    items = [
        item("OpenAI launches new model GPT-X today", url="https://a.com/1"),
        item("OpenAI launches new model GPT-X today!", url="https://b.com/2"),  # near-dup title
        item("Apple announces something unrelated", url="https://c.com/3"),
    ]
    out = dedupe(items)
    titles = [i.title for i in out]
    assert len(out) == 2
    assert "Apple announces something unrelated" in titles


def test_dedupe_strips_source_suffix_when_comparing():
    items = [
        item("Big AI news happened - The Verge", url="https://a.com/1"),
        item("Big AI news happened - Reuters", url="https://b.com/2"),
    ]
    out = dedupe(items)
    assert len(out) == 1  # same story, different outlets


def test_dedupe_keeps_distinct_items_and_order():
    items = [item("First"), item("Second", url="https://ex.com/b"), item("Third", url="https://ex.com/c")]
    out = dedupe(items)
    assert [i.title for i in out] == ["First", "Second", "Third"]


def test_dedupe_empty():
    assert dedupe([]) == []


# --------------------------------------------------------------------------- #
# filter_recent
# --------------------------------------------------------------------------- #
def test_filter_recent_drops_old_items():
    items = [
        item("fresh", published=NOW - timedelta(hours=2)),
        item("stale", published=NOW - timedelta(hours=50)),
    ]
    out = filter_recent(items, hours=30, now=NOW)
    assert [i.title for i in out] == ["fresh"]


def test_filter_recent_boundary_inclusive():
    items = [item("edge", published=NOW - timedelta(hours=30))]
    out = filter_recent(items, hours=30, now=NOW)
    assert len(out) == 1


def test_filter_recent_keeps_undated_by_default():
    items = [item("nodate", published=None)]
    assert len(filter_recent(items, hours=30, now=NOW)) == 1
    assert filter_recent(items, hours=30, now=NOW, keep_undated=False) == []


def test_filter_recent_handles_naive_datetimes():
    naive = datetime(2026, 6, 13, 11, 0)  # tz-naive, 1h ago, treated as UTC
    items = [item("naive", published=naive)]
    out = filter_recent(items, hours=30, now=NOW)
    assert len(out) == 1


# --------------------------------------------------------------------------- #
# split_message
# --------------------------------------------------------------------------- #
def test_split_short_message_unchanged():
    assert split_message("hello") == ["hello"]


def test_split_empty_message():
    assert split_message("") == []
    assert split_message("   \n  ") == []


def test_split_long_message_under_limit():
    para = "\n".join(f"line {i} " + "x" * 100 for i in range(200))
    chunks = split_message(para)
    assert len(chunks) > 1
    assert all(len(c) <= TELEGRAM_MAX_CHARS for c in chunks)


def test_split_does_not_lose_content():
    text = "\n".join(f"bullet {i}" for i in range(500))
    chunks = split_message(text, limit=200)
    rejoined = " ".join(chunks)
    for i in range(500):
        assert f"bullet {i}" in rejoined


def test_split_hard_wraps_oversized_line():
    giant = "y" * 500
    chunks = split_message(giant, limit=200)
    assert len(chunks) == 3
    assert all(len(c) <= 200 for c in chunks)


# --------------------------------------------------------------------------- #
# misc helpers
# --------------------------------------------------------------------------- #
def test_strip_html():
    assert strip_html("<b>Hello</b>&nbsp;world &amp; more") == "Hello world & more"
    assert strip_html("") == ""


def test_google_news_url_encodes_topic():
    url = google_news_url("artificial intelligence", lang="en-US", country="US")
    assert "artificial%20intelligence" in url
    assert "hl=en-US" in url
    assert "ceid=US:en" in url


def test_split_feeds_parses_urls_only():
    raw = "https://a.com/feed, not-a-url\nhttps://b.com/rss  https://c.com"
    assert _split_feeds(raw) == ["https://a.com/feed", "https://b.com/rss", "https://c.com"]
    assert _split_feeds("") == []
    assert _split_feeds(None) == []


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
def test_load_settings_defaults(monkeypatch):
    for k in [
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "NEWS_TOPIC",
        "NEWS_POST_HOUR", "NEWS_MAX_ITEMS", "NEWS_RECENCY_HOURS", "NEWS_EXTRA_FEEDS",
    ]:
        monkeypatch.delenv(k, raising=False)
    s = load_settings()
    assert s.topic == "artificial intelligence"
    assert s.post_hour == 9
    assert s.max_items == 7
    assert s.recency_hours == 30
    assert s.telegram_ready is False
    with pytest.raises(RuntimeError):
        s.require_telegram()


def test_load_settings_clamps_and_parses(monkeypatch):
    monkeypatch.setenv("NEWS_POST_HOUR", "99")      # clamps to 23
    monkeypatch.setenv("NEWS_MAX_ITEMS", "garbage")  # falls back to default 7
    monkeypatch.setenv("NEWS_TOPIC", "  robotics  ")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    s = load_settings()
    assert s.post_hour == 23
    assert s.max_items == 7
    assert s.topic == "robotics"
    assert s.telegram_ready is True
    s.require_telegram()  # should not raise


if __name__ == "__main__":
    raise SystemExit(pytest.main([os.path.abspath(__file__), "-q"]))
