"""Daily scheduling with APScheduler.

We use the async scheduler so it shares the bot's event loop. One cron job
fires every day at ``NEWS_POST_HOUR`` (local time) and runs the full
collect -> curate -> post pipeline for the *current* topic.

The topic is read fresh from a ``get_topic`` callback on every run, so when a
user changes it at runtime via ``/settopic`` the next scheduled digest uses the
new topic without restarting.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from .config import Settings
from .pipeline import post_digest, run_once

log = logging.getLogger("news_agent.scheduler")


def build_scheduler(
    settings: Settings,
    get_topic: Callable[[], str],
    bot,
    *,
    notify: Callable[[str], Awaitable[None]] | None = None,
):
    """Create (but do not start) an ``AsyncIOScheduler`` with the daily job.

    Parameters
    ----------
    settings   : runtime settings (uses ``post_hour``).
    get_topic  : callable returning the *current* topic at fire time.
    bot        : a python-telegram-bot ``Bot`` to post with.
    notify     : optional async callback to report errors somewhere visible.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler()

    async def daily_job() -> None:
        topic = get_topic()
        log.info("Scheduled digest firing for topic %r", topic)
        try:
            digest = run_once(topic, settings)
            await post_digest(digest, settings, bot=bot)
        except Exception as exc:  # noqa: BLE001 — a job error must not kill the loop
            log.exception("Scheduled digest failed: %s", exc)
            if notify is not None:
                try:
                    await notify(f"Daily digest failed: {exc}")
                except Exception:  # noqa: BLE001
                    log.exception("Failed to send failure notification")

    scheduler.add_job(
        daily_job,
        trigger=CronTrigger(hour=settings.post_hour, minute=0),
        id="daily_digest",
        name="Daily news digest",
        replace_existing=True,
        misfire_grace_time=3600,  # still fire if we were briefly down
        coalesce=True,
    )
    log.info("Scheduler configured: daily at %02d:00 local time", settings.post_hour)
    return scheduler
