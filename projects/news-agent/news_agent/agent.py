"""The agent: turn a pile of raw news items into a tight, readable digest.

This is the "brain" of the project. Rather than a single giant prompt, it's a
small **two-step pipeline** — the agent shape taught in module 06:

    1. RANK   — ask the model which items actually matter for the topic, and
                in what order. We parse its answer back to a reordered/trimmed
                list of items. This is the "decide what to do" step.
    2. WRITE  — give the model only the selected items and ask for a clean
                digest: a one-line intro + 5-8 bullets, each a headline, a
                one-sentence summary, and the source link.

Splitting ranking from writing keeps each prompt short and focused, which is
exactly what small local models (e.g. Ollama llama3.2) need to stay reliable.

Every model call goes through the shared ``llm_core`` provider, so the same
code runs against Ollama, OpenAI, Anthropic or NVIDIA by changing one env var.

If the LLM is unavailable or returns junk, the pipeline degrades gracefully to
a deterministic, non-LLM digest so the bot still posts *something* useful.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from llm_core import ChatMessage, ChatOptions, get_provider

from .sources import NewsItem

log = logging.getLogger("news_agent.agent")

# Hard cap on items we ever send to the model, to bound prompt size / cost.
MAX_CANDIDATES = 30


# --------------------------------------------------------------------------- #
# Prompt construction
# --------------------------------------------------------------------------- #
def _format_candidates(items: list[NewsItem]) -> str:
    """Number the candidate items for the model to reference by index."""
    lines = []
    for i, it in enumerate(items, start=1):
        summary = it.short_summary(200)
        line = f"[{i}] {it.title} (source: {it.source})"
        if summary:
            line += f"\n    {summary}"
        lines.append(line)
    return "\n".join(lines)


RANK_SYSTEM = (
    "You are a sharp news editor. You are given a numbered list of news items "
    "about a topic. Pick the most important, relevant, and distinct stories — "
    "drop near-duplicates, press releases, and off-topic noise. "
    "Respond with ONLY a comma-separated list of the item numbers you choose, "
    "best first. Example: 4, 1, 7, 2. Do not add any other text."
)

WRITE_SYSTEM = (
    "You are a concise news editor writing a daily digest for a Telegram "
    "channel. Write in plain Markdown. Structure:\n"
    "- A single short intro line (one sentence) naming the topic and the vibe "
    "of today's news.\n"
    "- Then 5 to 8 bullet points. Each bullet: a bolded headline, then a "
    "single plain-English sentence of context, then the source link in "
    "parentheses.\n"
    "Rules: be factual and neutral, no hype, no emojis, no preamble, no "
    "closing remarks. Use only the items provided; never invent facts or "
    "links. Keep the whole thing under ~250 words."
)


# --------------------------------------------------------------------------- #
# Step 1 — rank / select
# --------------------------------------------------------------------------- #
def _parse_ranking(text: str, n: int) -> list[int]:
    """Pull 1-based item indices out of the model's free-form ranking reply.

    Robust to extra prose, brackets, newlines, etc. Returns 0-based indices,
    de-duplicated, in the model's stated order, dropping out-of-range numbers."""
    nums = re.findall(r"\d+", text or "")
    seen: set[int] = set()
    order: list[int] = []
    for raw in nums:
        idx = int(raw) - 1
        if 0 <= idx < n and idx not in seen:
            seen.add(idx)
            order.append(idx)
    return order


def rank_items(
    items: list[NewsItem],
    topic: str,
    max_items: int,
    *,
    provider=None,
) -> list[NewsItem]:
    """Use the LLM to select + order the most relevant items.

    Falls back to the input order (already recency-sorted) if the model is
    unavailable or its answer is unusable."""
    if not items:
        return []
    candidates = items[:MAX_CANDIDATES]
    if len(candidates) <= max_items:
        # Nothing to prune; skip the round-trip.
        return candidates

    provider = provider or get_provider()
    user = (
        f"Topic: {topic}\n\n"
        f"Items:\n{_format_candidates(candidates)}\n\n"
        f"Choose the {max_items} best, most distinct items. "
        "Reply with only their numbers, comma-separated, best first."
    )
    try:
        result = provider.chat(
            [ChatMessage("system", RANK_SYSTEM), ChatMessage("user", user)],
            ChatOptions(temperature=0.2, max_tokens=120),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Ranking LLM call failed (%s); using recency order.", exc)
        return candidates[:max_items]

    order = _parse_ranking(result.text, len(candidates))
    if not order:
        log.warning("Could not parse ranking %r; using recency order.", result.text[:120])
        return candidates[:max_items]

    chosen = [candidates[i] for i in order][:max_items]
    # If the model under-selected, top up with the next recent items.
    if len(chosen) < max_items:
        for it in candidates:
            if it not in chosen:
                chosen.append(it)
            if len(chosen) >= max_items:
                break
    return chosen


# --------------------------------------------------------------------------- #
# Step 2 — write the digest
# --------------------------------------------------------------------------- #
def _digest_header(topic: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"*Daily {topic} digest* — {now.strftime('%b %d, %Y')}"


def fallback_digest(items: list[NewsItem], topic: str, now: datetime | None = None) -> str:
    """A deterministic, LLM-free digest. Used when the model fails, and handy
    for offline testing."""
    header = _digest_header(topic, now)
    if not items:
        return f"{header}\n\nNo fresh news found in the lookback window."
    lines = [header, f"\nTop {len(items)} stories on {topic}:\n"]
    for it in items:
        summary = it.short_summary(160)
        bullet = f"• *{it.title}*"
        if summary:
            bullet += f"\n  {summary}"
        bullet += f"\n  {it.source}: {it.url}"
        lines.append(bullet)
    return "\n".join(lines)


def write_digest(items: list[NewsItem], topic: str, *, provider=None, now=None) -> str:
    """Ask the LLM to compose the digest from the selected items.

    On any failure, returns the deterministic ``fallback_digest`` so the bot
    always has something to post."""
    if not items:
        return fallback_digest(items, topic, now)

    provider = provider or get_provider()
    body_lines = []
    for it in items:
        summary = it.short_summary(220)
        body_lines.append(
            f"- Title: {it.title}\n  Source: {it.source}\n  Link: {it.url}"
            + (f"\n  Context: {summary}" if summary else "")
        )
    user = (
        f"Topic: {topic}\n\n"
        f"Use ONLY these items:\n" + "\n".join(body_lines) + "\n\n"
        "Write the digest now."
    )
    try:
        result = provider.chat(
            [ChatMessage("system", WRITE_SYSTEM), ChatMessage("user", user)],
            ChatOptions(temperature=0.4, max_tokens=700),
        )
        text = (result.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Digest LLM call failed (%s); using fallback digest.", exc)
        return fallback_digest(items, topic, now)

    if not text:
        log.warning("LLM returned an empty digest; using fallback.")
        return fallback_digest(items, topic, now)

    header = _digest_header(topic, now)
    # Prepend a dated header unless the model already started with one.
    if topic.lower() not in text[:80].lower():
        text = f"{header}\n\n{text}"
    return text


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def curate(
    items: list[NewsItem],
    topic: str,
    max_items: int = 7,
    *,
    provider=None,
    now: datetime | None = None,
) -> str:
    """Full agent pipeline: rank -> write -> digest string.

    Shares a single provider instance across both steps. Robust to empty input
    and LLM failures (always returns a non-empty string)."""
    if not items:
        return fallback_digest([], topic, now)
    try:
        provider = provider or get_provider()
    except Exception as exc:  # noqa: BLE001
        log.warning("No LLM provider available (%s); using fallback digest.", exc)
        return fallback_digest(items[:max_items], topic, now)

    selected = rank_items(items, topic, max_items, provider=provider)
    return write_digest(selected, topic, provider=provider, now=now)
