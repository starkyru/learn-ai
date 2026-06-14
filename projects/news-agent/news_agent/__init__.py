"""news_agent — a Telegram bot driven by an LLM agent that collects news on a
chosen topic and posts a concise daily digest.

This is the flagship applied project for the ``learn-ai`` course. It pulls
together several modules:

* **02 — LLM integration**: every model call goes through the shared
  ``llm_core`` provider abstraction, so it runs against a free local Ollama
  model or any configured cloud provider with no code change.
* **05 — RAG-ish retrieval**: we *retrieve* fresh news items from RSS feeds,
  normalize + dedupe them, then feed the most relevant ones to the model —
  the "retrieve, then generate" shape of RAG, with the web as the corpus.
* **06 — agents**: ``agent.py`` is a small multi-step pipeline (rank → write)
  that decides what matters and how to present it, rather than a single
  one-shot prompt.

Public surface:

    from news_agent import load_settings, run_once
    from news_agent.sources import fetch_news
    from news_agent.agent import curate

Run it::

    uv run python -m news_agent --dry-run    # prints a digest, no Telegram
    uv run python -m news_agent --once       # posts one digest to Telegram
    uv run python -m news_agent bot          # bot + daily scheduler
"""

from __future__ import annotations

from .config import Settings, load_settings
from .pipeline import post_digest, run_once

__all__ = [
    "Settings",
    "load_settings",
    "run_once",
    "post_digest",
]

__version__ = "0.1.0"
