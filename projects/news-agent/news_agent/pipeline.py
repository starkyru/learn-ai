"""Orchestration: glue retrieval + agent + Telegram together.

Two public functions, reused by both the CLI and the scheduler:

* ``run_once(topic, settings)`` -> digest text. Collect news, curate it with
  the LLM agent, return the digest string. No Telegram involved — this is the
  unit the ``--dry-run`` mode prints.
* ``post_digest(text, settings, bot=None)`` — send a (possibly long) digest to
  the configured Telegram chat, splitting it to respect Telegram's 4096-char
  message limit.

Keeping the Telegram-free ``run_once`` separate is what lets ``--dry-run`` work
with zero Telegram setup — only an LLM provider is needed.
"""

from __future__ import annotations

import logging

from .agent import curate
from .config import Settings, load_settings
from .sources import fetch_news

log = logging.getLogger("news_agent.pipeline")

# Telegram hard limit is 4096 chars per message; leave headroom.
TELEGRAM_MAX_CHARS = 3800


def split_message(text: str, limit: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """Split ``text`` into chunks that each fit within ``limit`` characters.

    Splits on paragraph then line boundaries so we never cut a word — and never
    split inside a single oversized line unless that line alone exceeds the
    limit (then it's hard-wrapped). Pure function: unit-tested directly."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    # Split into blocks on blank lines, then on single newlines, preserving order.
    blocks = text.split("\n")
    for block in blocks:
        piece = block + "\n"
        if len(piece) > limit:
            # A single very long line: flush what we have, then hard-wrap it.
            flush()
            for i in range(0, len(block), limit):
                chunks.append(block[i : i + limit])
            continue
        if len(current) + len(piece) > limit:
            flush()
        current += piece
    flush()
    return chunks


def run_once(topic: str | None = None, settings: Settings | None = None) -> str:
    """Collect + curate news for ``topic`` and return the digest text.

    Network-resilient: if no news is found, returns a clear "no news" digest
    rather than raising. LLM failures are handled inside ``curate``."""
    settings = settings or load_settings()
    topic = (topic or settings.topic).strip() or settings.topic

    log.info("Collecting news for topic %r", topic)
    items = fetch_news(
        topic,
        recency_hours=settings.recency_hours,
        extra_feeds=settings.extra_feeds,
        lang=settings.lang,
        country=settings.country,
    )
    log.info("Curating %d items", len(items))
    digest = curate(items, topic, max_items=settings.max_items)
    return digest


async def post_digest(
    text: str,
    settings: Settings | None = None,
    bot=None,
) -> int:
    """Send ``text`` to the configured Telegram chat, split as needed.

    Returns the number of messages sent. Requires Telegram config; raises a
    clear error via ``Settings.require_telegram`` if it's missing. If ``bot``
    is None a throwaway ``Bot`` is created from the token."""
    settings = settings or load_settings()
    settings.require_telegram()

    # Imported lazily so --dry-run never needs python-telegram-bot installed.
    from telegram import Bot
    from telegram.constants import ParseMode
    from telegram.error import TelegramError

    async def _send_all(active_bot) -> int:
        chunks = split_message(text)
        sent = 0
        for chunk in chunks:
            try:
                # Try Markdown first; fall back to plain text if Telegram
                # rejects the (model-generated) markup, so a stray '*' never
                # drops a post.
                await active_bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=chunk,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
            except TelegramError as exc:
                log.warning("Markdown send failed (%s); retrying as plain text.", exc)
                await active_bot.send_message(
                    chat_id=settings.telegram_chat_id,
                    text=chunk,
                    disable_web_page_preview=True,
                )
            sent += 1
        log.info("Posted digest in %d message(s) to chat %s", sent, settings.telegram_chat_id)
        return sent

    if bot is None:
        # A standalone Bot must be initialized/shut down; the async context
        # manager handles both. A bot owned by an Application is already live,
        # so we just use it directly.
        async with Bot(token=settings.telegram_bot_token) as own:  # type: ignore[arg-type]
            return await _send_all(own)
    return await _send_all(bot)


async def run_and_post(topic: str | None = None, settings: Settings | None = None, bot=None) -> str:
    """Convenience: run the pipeline and post the result. Returns the digest."""
    settings = settings or load_settings()
    digest = run_once(topic, settings)
    await post_digest(digest, settings, bot=bot)
    return digest
