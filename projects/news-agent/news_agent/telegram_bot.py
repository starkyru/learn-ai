"""The Telegram bot.

Built on python-telegram-bot v21+ (async ``Application``). Commands:

    /start            greet + show what the bot does
    /help             list commands
    /topic            show the current topic
    /settopic <text>  change the topic at runtime
    /news             collect + curate + post a digest right now

The bot also starts the APScheduler daily job (see ``scheduler.py``) so it
posts automatically at ``NEWS_POST_HOUR`` without any external cron.

State note: the current topic lives in ``bot_data`` so it's shared between the
command handlers and the scheduler, and survives across updates within a run.
(Persisting across restarts is left as an extension — see the README.)
"""

from __future__ import annotations

import logging

from .config import Settings, load_settings
from .pipeline import post_digest, run_once, split_message
from .scheduler import build_scheduler

log = logging.getLogger("news_agent.telegram_bot")

TOPIC_KEY = "topic"


def _get_topic(application, settings: Settings) -> str:
    return application.bot_data.get(TOPIC_KEY, settings.topic)


def build_application(settings: Settings | None = None):
    """Construct the python-telegram-bot ``Application`` with handlers + a
    daily scheduler wired in. Returns the ready-to-run application."""
    settings = settings or load_settings()
    settings.require_telegram()

    from telegram import Update
    from telegram.constants import ParseMode
    from telegram.ext import Application, CommandHandler, ContextTypes

    SCHED_KEY = "_scheduler"

    # --- application lifecycle: start/stop the scheduler with the bot ------- #
    # These run inside the bot's event loop. We build the scheduler here (not at
    # construction time) so application.bot is fully initialized, and stash it
    # in bot_data so post_shutdown can stop it.
    async def _post_init(app: Application) -> None:
        async def _notify(text: str) -> None:
            try:
                for chunk in split_message(text):
                    await app.bot.send_message(chat_id=settings.telegram_chat_id, text=chunk)
            except Exception:  # noqa: BLE001
                log.exception("Failed to notify chat of scheduler error")

        scheduler = build_scheduler(
            settings,
            get_topic=lambda: app.bot_data.get(TOPIC_KEY, settings.topic),
            bot=app.bot,
            notify=_notify,
        )
        scheduler.start()
        app.bot_data[SCHED_KEY] = scheduler
        log.info("Bot started; daily digest scheduled at %02d:00.", settings.post_hour)

    async def _post_shutdown(app: Application) -> None:
        scheduler = app.bot_data.get(SCHED_KEY)
        if scheduler is not None and scheduler.running:
            scheduler.shutdown(wait=False)

    application = (
        Application.builder()
        .token(settings.telegram_bot_token)  # type: ignore[arg-type]
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.bot_data[TOPIC_KEY] = settings.topic

    async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        topic = _get_topic(application, settings)
        await update.effective_message.reply_text(
            "Hi! I'm your news agent. I collect news on a topic and post a "
            f"concise daily digest at {settings.post_hour:02d}:00.\n\n"
            f"Current topic: *{topic}*\n\n"
            "Try /news for a digest now, or /help for commands.",
            parse_mode=ParseMode.MARKDOWN,
        )

    async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(
            "Commands:\n"
            "/news — collect + post a digest now\n"
            "/topic — show the current topic\n"
            "/settopic <topic> — change the topic\n"
            "/start — intro\n"
            "/help — this message"
        )

    async def cmd_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        topic = _get_topic(application, settings)
        await update.effective_message.reply_text(f"Current topic: {topic}")

    async def cmd_settopic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        new_topic = " ".join(context.args).strip() if context.args else ""
        if not new_topic:
            await update.effective_message.reply_text(
                "Usage: /settopic <topic>\nExample: /settopic open source LLMs"
            )
            return
        application.bot_data[TOPIC_KEY] = new_topic
        await update.effective_message.reply_text(f"Topic set to: {new_topic}")
        log.info("Topic changed to %r by chat %s", new_topic, update.effective_chat.id)

    async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        topic = _get_topic(application, settings)
        msg = await update.effective_message.reply_text(
            f"Collecting and curating news on '{topic}'… this can take a moment."
        )
        try:
            # run_once is blocking (network + LLM); offload so we don't stall
            # the event loop / other updates.
            import asyncio

            digest = await asyncio.to_thread(run_once, topic, settings)
            await post_digest(digest, settings, bot=context.bot)
            # Confirm in the originating chat if it differs from the digest chat.
            if str(update.effective_chat.id) != str(settings.telegram_chat_id):
                await msg.edit_text("Posted today's digest to the channel.")
            else:
                await msg.delete()
        except Exception as exc:  # noqa: BLE001
            log.exception("/news failed: %s", exc)
            await msg.edit_text(f"Sorry, I couldn't build the digest: {exc}")

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("topic", cmd_topic))
    application.add_handler(CommandHandler("settopic", cmd_settopic))
    application.add_handler(CommandHandler("news", cmd_news))

    return application


def run_bot(settings: Settings | None = None) -> None:
    """Build and run the bot (blocking). Polls Telegram for updates and runs
    the daily scheduler until interrupted."""
    application = build_application(settings)
    log.info("Starting Telegram polling…")
    application.run_polling()
