"""Command-line entrypoint for the news agent.

Modes::

    python -m news_agent --dry-run        # collect + curate + PRINT (no Telegram)
    python -m news_agent --once           # collect + curate + POST one digest
    python -m news_agent bot              # run the bot + daily scheduler

``--dry-run`` needs only an LLM provider (e.g. a local Ollama), so it's the
ideal first run: it proves the retrieval + agent pipeline works before you set
up any Telegram credentials.

Common flags:
    --topic "<topic>"   override NEWS_TOPIC for this run
    -v / --verbose      enable INFO logging
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from .config import load_settings


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="news_agent",
        description="LLM-driven Telegram news digest agent.",
    )
    p.add_argument(
        "mode",
        nargs="?",
        choices=["bot"],
        help="Run mode. 'bot' runs the Telegram bot + daily scheduler. "
        "Omit it and pass --once or --dry-run for a single run.",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Collect, curate, and POST one digest to Telegram, then exit.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Collect + curate and PRINT the digest to the console. "
        "No Telegram needed — only an LLM provider.",
    )
    p.add_argument(
        "--topic",
        default=None,
        help="Override NEWS_TOPIC for this run.",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose (INFO) logging.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    settings = load_settings()
    topic = args.topic or settings.topic

    # Validate mode selection.
    if sum([bool(args.once), bool(args.dry_run), args.mode == "bot"]) > 1:
        parser.error("Choose exactly one of: bot, --once, --dry-run.")

    if args.dry_run:
        # Import here so missing optional deps don't break the other modes.
        from .pipeline import run_once

        print(f"# Dry run — topic: {topic!r}\n", file=sys.stderr)
        digest = run_once(topic, settings)
        print(digest)
        return 0

    if args.once:
        from .pipeline import run_and_post

        try:
            settings.require_telegram()
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        digest = asyncio.run(run_and_post(topic, settings))
        print("Posted digest:\n", file=sys.stderr)
        print(digest)
        return 0

    if args.mode == "bot":
        from .telegram_bot import run_bot

        try:
            settings.require_telegram()
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        run_bot(settings)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
