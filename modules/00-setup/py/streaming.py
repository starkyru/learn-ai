"""streaming.py — print tokens as they arrive.

What it teaches:
    Streaming. Instead of waiting for the full answer, chat_stream() yields text
    chunks as the model generates them. This is what makes chat UIs feel fast —
    the user reads token 1 while token 50 is still being computed.

How to run (from the repo root):
    uv run python modules/00-setup/py/streaming.py

    Uses your default provider (LLM_PROVIDER). All four support streaming.
"""

from __future__ import annotations

import sys

from llm_core import ChatMessage, get_provider

PROMPT = "In 3 short sentences, explain why streaming output feels faster to a user."


def main() -> None:
    llm = get_provider()
    print(f"Provider: {llm.name} ({llm.chat_model})\n")

    messages = [ChatMessage(role="user", content=PROMPT)]

    # chat_stream() returns an iterator of string chunks. Print each one with no
    # trailing newline and flush so it appears immediately, not when the OS
    # buffer fills.
    for chunk in llm.chat_stream(messages):
        sys.stdout.write(chunk)
        sys.stdout.flush()

    print()  # final newline once the stream is exhausted


if __name__ == "__main__":
    main()
