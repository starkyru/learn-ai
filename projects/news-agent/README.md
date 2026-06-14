# news-agent — an LLM-driven Telegram daily news digest

A Telegram bot that an **LLM agent** drives: it collects fresh news on a topic
you choose, decides what actually matters, writes a tight digest, and posts it
to your chat or channel — on command and automatically once a day.

This is the flagship applied project for the `learn-ai` course. Build it after
module 06; it ties together everything you've learned into something you'll
actually keep running.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              news-agent                                    │
│                                                                            │
│   Telegram          ┌───────────────┐                                      │
│   /news, /settopic ─┤ telegram_bot  │◄──── commands from you               │
│   daily @ 09:00 ────┤  + scheduler  │                                      │
│                     └──────┬────────┘                                      │
│                            │ run_once(topic)                               │
│                            ▼                                               │
│                     ┌───────────────┐    pipeline.py (orchestration)       │
│                     │   pipeline    │                                      │
│                     └──┬─────────┬──┘                                      │
│              fetch_news│         │curate                                   │
│                        ▼         ▼                                         │
│              ┌───────────┐   ┌───────────────────────────┐                │
│              │ sources.py│   │        agent.py           │                 │
│              │  RSS +    │   │  ┌─────────┐  ┌─────────┐  │                 │
│              │  Google   │──►│  │  RANK   │─►│  WRITE  │  │                 │
│              │  News     │   │  │ (LLM)   │  │ (LLM)   │  │                 │
│              │ +dedupe   │   │  └─────────┘  └─────────┘  │                 │
│              │ +recency  │   └────────────┬──────────────┘                 │
│              └───────────┘                │ digest text                    │
│                                           ▼                                │
│                                    post_digest() ──► Telegram chat         │
│                                                                            │
│   every LLM call → llm_core.get_provider()  (Ollama / OpenAI / Claude / …) │
└──────────────────────────────────────────────────────────────────────────┘
```

## What it does

1. **Retrieve** — pulls recent articles for a topic from Google News' search
   RSS feed (plus any extra RSS feeds you configure), normalizes them, drops
   anything older than ~30h, and removes near-duplicate stories.
2. **Curate (the agent)** — a two-step LLM pipeline: first *rank* the items to
   pick the most important and distinct ones, then *write* a concise digest
   (one-line intro + 5–8 bulleted headlines, each with a one-sentence summary
   and the source link).
3. **Post** — sends the digest to your Telegram chat/channel, splitting long
   messages to respect Telegram's 4096-char limit. Runs on `/news` and
   automatically every day at `NEWS_POST_HOUR`.

Every model call goes through the shared `llm_core` provider, so it runs on a
**free local Ollama model** out of the box, or any cloud provider by changing
one env var.

## How the agent works

`agent.py` is intentionally a small **multi-step agent**, not one giant prompt
(the pattern from module 06):

- **RANK step** — the model gets a numbered list of candidate items and returns
  just the indices of the best, most distinct ones, best-first. We parse those
  numbers back into a reordered, trimmed list. Keeping this prompt tiny and the
  output format trivial (just numbers) is what makes it reliable on small local
  models.
- **WRITE step** — the model gets *only* the selected items and a strict format
  spec, and composes the digest in plain Markdown.

Both steps share one provider instance. If the LLM is unavailable or returns
junk at any point, the pipeline **degrades gracefully** to a deterministic,
LLM-free digest (`fallback_digest`) so the bot always posts something useful.
That robustness is deliberate — see the error handling throughout `sources.py`,
`agent.py`, and `pipeline.py`.

## How it ties back to the course

- **02 — LLM integration**: all model access goes through `get_provider()` /
  `ChatMessage` / `ChatOptions`; swap providers with one env var. You'll see the
  request/response loop, system prompts, and `max_tokens`/`temperature` in use.
- **05 — RAG-ish retrieval**: the agent doesn't answer from memory — it
  *retrieves* a fresh corpus (the web, via RSS), normalizes and filters it, then
  feeds only the relevant items to the model. That "retrieve, then generate"
  shape is the heart of RAG, with the open web as the knowledge base.
- **06 — agents**: the rank→write pipeline plus scheduled, autonomous action
  (it posts daily on its own and reacts to commands) is a minimal but real
  agent: it decides *what to do* (which stories) and *acts* (posts to Telegram).

---

## Setup

### 1. Create a Telegram bot and get a token

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, pick a name and a username ending in `bot`.
3. BotFather replies with an HTTP API **token** like
   `123456789:AAH...`. That's your `TELEGRAM_BOT_TOKEN`.

### 2. Find your chat id

The bot posts to a specific chat/channel id (`TELEGRAM_CHAT_ID`). Easiest ways:

- **Personal chat:** message your new bot anything, then visit
  `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and read
  `result[].message.chat.id` (a number, possibly negative).
- **Channel:** add your bot as an **admin** of the channel, post a message in
  the channel, then check `getUpdates` (or use `@username` of a public channel,
  e.g. `TELEGRAM_CHAT_ID=@my_news_channel`).
- Or message [@userinfobot](https://t.me/userinfobot) / `@RawDataBot` to read
  your own id.

### 3. Install dependencies

This project uses the `telegram` extra already declared in the repo's root
`pyproject.toml`:

```bash
# from the repo root
uv sync --extra telegram
```

That installs `python-telegram-bot>=21`, `feedparser>=6`, `httpx>=0.27`, and
`apscheduler>=3.10` (in addition to the base `llm_core`).

### 4. Set environment variables

Add these to your repo-root `.env` (alongside the usual `LLM_PROVIDER` keys):

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | for posting | — | token from @BotFather |
| `TELEGRAM_CHAT_ID` | for posting | — | chat/channel to post into |
| `NEWS_TOPIC` | no | `artificial intelligence` | default topic to track |
| `NEWS_POST_HOUR` | no | `9` | local 24h hour for the daily post |
| `NEWS_MAX_ITEMS` | no | `7` | headlines per digest (1–20) |
| `NEWS_RECENCY_HOURS` | no | `30` | only consider items newer than this |
| `NEWS_EXTRA_FEEDS` | no | — | extra RSS URLs (comma/space/newline separated) |
| `NEWS_LANG` / `NEWS_COUNTRY` | no | `en-US` / `US` | Google News locale |
| `LLM_PROVIDER` + provider keys | yes | `ollama` | see the repo's `.env.example` |

**Zero-cost path:** install [Ollama](https://ollama.com), run
`ollama pull llama3.2`, leave `LLM_PROVIDER=ollama`, and you need no API keys at
all for the digest itself.

### 5. Run it

Always start with `--dry-run` — it needs **only** an LLM provider (no Telegram
setup) and prints the digest to your console so you can see the whole pipeline
work immediately:

```bash
# 1) See it work end-to-end with zero Telegram setup:
uv run python -m news_agent --dry-run
uv run python -m news_agent --dry-run --topic "open source LLMs" -v

# 2) Post a single digest to Telegram (needs the token + chat id):
uv run python -m news_agent --once

# 3) Run the bot + daily scheduler (posts every day at NEWS_POST_HOUR):
uv run python -m news_agent bot
```

While the bot is running, message it:

| Command | Effect |
| --- | --- |
| `/start` | intro + current topic |
| `/help` | list commands |
| `/news` | collect + post a digest right now |
| `/topic` | show the current topic |
| `/settopic <topic>` | change the topic (used by the next digest too) |

## Run the tests

The tests cover the **pure logic only** — no network, no LLM:

```bash
uv run pytest projects/news-agent/test_news_agent.py
```

They verify dedupe, the recency filter, the Telegram message splitter, HTML
stripping, URL building, and config parsing/validation against small fixtures.

## Project layout

```
projects/news-agent/
├── news_agent/
│   ├── __init__.py        # public surface + docs
│   ├── config.py          # env → Settings, defaults + validation
│   ├── sources.py         # RSS retrieval, normalize, dedupe, recency filter
│   ├── agent.py           # LLM rank→write curation pipeline (the "agent")
│   ├── pipeline.py        # run_once / post_digest orchestration + splitter
│   ├── scheduler.py       # APScheduler daily job
│   ├── telegram_bot.py    # python-telegram-bot Application + commands
│   └── __main__.py        # CLI: bot | --once | --dry-run
├── test_news_agent.py     # pytest unit tests (pure logic)
└── README.md
```

## Ideas to extend

- **Per-user topics**: store each chat's topic (and schedule) in
  `Application` persistence or a tiny SQLite DB so multiple users get their own
  digest, and persist topics across restarts.
- **More & better sources**: add Bing News / Hacker News / arXiv / subreddit
  RSS feeds via `NEWS_EXTRA_FEEDS`, or fetch full article text and summarize it
  instead of the RSS blurb.
- **Dedupe via embeddings**: replace the title-similarity heuristic in
  `sources.dedupe` with semantic clustering using `llm_core`'s `embed()` and a
  cosine threshold (module 04) to catch reworded duplicates.
- **Sentiment / categorization**: have the agent tag each story
  (positive/negative, research vs. product vs. policy) and group bullets by
  category.
- **Citations & faithfulness check**: add an LLM-as-judge pass (module 07) that
  verifies every bullet is supported by its linked source before posting.
- **Inline buttons**: add Telegram inline keyboards to "read more", change
  topic, or trigger a fresh digest without typing a command.
```
