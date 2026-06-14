"""Configuration for the news agent.

Settings come from environment variables (loaded from a ``.env`` file via
``python-dotenv``). The whole config is gathered into one immutable
``Settings`` object so the rest of the code never reads ``os.environ``
directly — that makes it trivial to test and reason about.

Required for posting to Telegram (NOT required for ``--dry-run``):
    TELEGRAM_BOT_TOKEN   token from @BotFather
    TELEGRAM_CHAT_ID     chat / channel id to post into

Optional (sensible defaults):
    NEWS_TOPIC           default topic to track (default: "artificial intelligence")
    NEWS_POST_HOUR       local 24h hour for the daily post (default: 9)
    NEWS_MAX_ITEMS       headlines to keep in a digest (default: 7)
    NEWS_RECENCY_HOURS   only consider items newer than this (default: 30)
    NEWS_EXTRA_FEEDS     comma/space/newline-separated extra RSS feed URLs
    NEWS_LANG / NEWS_COUNTRY  Google News locale (default: en-US / US)

The LLM provider is configured by ``llm_core`` itself (``LLM_PROVIDER`` etc.).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load .env from the current working directory / nearest parent. Calling this
# at import time mirrors what llm_core does, so env vars are available whether
# the project is run standalone or from the repo root.
load_dotenv()

DEFAULT_TOPIC = "artificial intelligence"
DEFAULT_POST_HOUR = 9
DEFAULT_MAX_ITEMS = 7
DEFAULT_RECENCY_HOURS = 30


def _split_feeds(raw: str | None) -> list[str]:
    """Parse extra feed URLs from a string separated by commas, whitespace or
    newlines. Ignores blanks and anything that does not look like a URL."""
    if not raw:
        return []
    parts = re.split(r"[\s,]+", raw.strip())
    feeds: list[str] = []
    for p in parts:
        p = p.strip()
        if p and (p.startswith("http://") or p.startswith("https://")):
            feeds.append(p)
    return feeds


def _int_env(name: str, default: int, *, lo: int | None = None, hi: int | None = None) -> int:
    """Read an int env var, falling back to ``default`` on missing/garbage,
    and clamping into ``[lo, hi]`` when given."""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        try:
            value = int(raw.strip())
        except ValueError:
            value = default
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of everything the agent needs to run."""

    telegram_bot_token: str | None
    telegram_chat_id: str | None
    topic: str
    post_hour: int
    max_items: int
    recency_hours: int
    extra_feeds: list[str] = field(default_factory=list)
    lang: str = "en-US"
    country: str = "US"

    @property
    def telegram_ready(self) -> bool:
        """True only when we have both a token and a destination chat."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    def require_telegram(self) -> None:
        """Raise a clear error if Telegram is needed but not configured."""
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if missing:
            raise RuntimeError(
                "Missing Telegram config: "
                + ", ".join(missing)
                + ". Set them in your .env (see README), or use --dry-run "
                "to print a digest without posting."
            )


def load_settings() -> Settings:
    """Build a ``Settings`` from the environment, applying defaults + validation."""
    topic = (os.getenv("NEWS_TOPIC") or DEFAULT_TOPIC).strip() or DEFAULT_TOPIC

    return Settings(
        telegram_bot_token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip() or None,
        telegram_chat_id=(os.getenv("TELEGRAM_CHAT_ID") or "").strip() or None,
        topic=topic,
        post_hour=_int_env("NEWS_POST_HOUR", DEFAULT_POST_HOUR, lo=0, hi=23),
        max_items=_int_env("NEWS_MAX_ITEMS", DEFAULT_MAX_ITEMS, lo=1, hi=20),
        recency_hours=_int_env("NEWS_RECENCY_HOURS", DEFAULT_RECENCY_HOURS, lo=1, hi=168),
        extra_feeds=_split_feeds(os.getenv("NEWS_EXTRA_FEEDS")),
        lang=(os.getenv("NEWS_LANG") or "en-US").strip() or "en-US",
        country=(os.getenv("NEWS_COUNTRY") or "US").strip() or "US",
    )
