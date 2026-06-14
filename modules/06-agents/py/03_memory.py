"""
Task 3 — Agent memory  🟡

What this teaches:
  - LLMs have no memory between calls. "Memory" is an architecture you design.
  - Three kinds of memory, from cheapest to most powerful:
      1. In-context (history list)  — free but limited by context window.
      2. Persistent / external (file, DB) — survives restarts; unlimited size.
      3. Summarised — compress old turns so they always fit the window.
  - A scratchpad lets the agent accumulate structured notes across turns
    without sending the full conversation history each time.

How to run:
  uv run python modules/06-agents/py/03_memory.py
"""

from __future__ import annotations

import os
from pathlib import Path

from llm_core import get_provider, ChatMessage, ChatOptions

# ---------------------------------------------------------------------------
# Scratchpad — a file the agent reads/writes to persist notes
# ---------------------------------------------------------------------------

SCRATCHPAD_PATH = Path("modules/06-agents/scratchpad.txt")

# TODO 1: Implement read_scratchpad() and write_scratchpad().
#         read_scratchpad() returns "" if the file doesn't exist.
#         write_scratchpad() APPENDS a timestamped entry — don't overwrite.
#         Hint for timestamp: datetime.datetime.now().isoformat(timespec="seconds")

def read_scratchpad() -> str:
    """Return the current scratchpad content, or "" if it doesn't exist."""
    # TODO: return SCRATCHPAD_PATH.read_text() if SCRATCHPAD_PATH.exists() else ""
    raise NotImplementedError("TODO: implement read_scratchpad")


def write_scratchpad(note: str) -> None:
    """Append a timestamped note to the scratchpad file."""
    # TODO: open(SCRATCHPAD_PATH, "a").write(f"\n[{timestamp}] {note}")
    raise NotImplementedError("TODO: implement write_scratchpad")


# ---------------------------------------------------------------------------
# Sliding-window memory
# ---------------------------------------------------------------------------

MAX_HISTORY_TURNS = 10  # keep at most N user+assistant pairs

# TODO 2: Implement trim_history().
#         Always preserve history[0] (the system message).
#         If len(history) > 1 + MAX_HISTORY_TURNS * 2, drop the oldest pairs.
#         A "pair" = one user message + one assistant message (2 messages).

def trim_history(history: list[ChatMessage]) -> list[ChatMessage]:
    """Trim the conversation history to stay within MAX_HISTORY_TURNS pairs."""
    raise NotImplementedError("TODO: implement trim_history")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def build_system_prompt(scratchpad_content: str) -> str:
    """Build a system prompt that injects the current scratchpad state.

    TODO 3: Write a prompt that:
      - Tells the agent it has a persistent scratchpad it can use.
      - Shows scratchpad_content inside <scratchpad> ... </scratchpad> tags.
      - Instructs it to write notes in this format at the end of its reply:
            SCRATCHPAD: <note to save>
      - Tells it to say CLEAR_SCRATCHPAD to wipe the file.
    """
    return "TODO: write the system prompt with <scratchpad> injection."


# ---------------------------------------------------------------------------
# Response post-processing
# ---------------------------------------------------------------------------

def process_response(
    text: str,
) -> tuple[str, str | None, bool]:
    """Parse the agent's response.

    Returns (display_text, note_to_save_or_None, should_clear_scratchpad).

    TODO 4: Scan `text` for:
      - Lines starting with "SCRATCHPAD: <note>" — extract the note.
      - The token "CLEAR_SCRATCHPAD" — set clear=True.
      Strip those lines from display_text so they're not shown to the user.
    """
    raise NotImplementedError("TODO: implement process_response")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    provider = get_provider()
    print(f"Provider: {provider.name} / {provider.chat_model}")
    print(f"Scratchpad: {SCRATCHPAD_PATH.resolve()}\n")

    history: list[ChatMessage] = [
        ChatMessage("system", build_system_prompt(read_scratchpad())),
    ]

    print('Memory-enabled agent. Commands: "exit", "scratchpad" (view), or just chat.\n')

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "scratchpad":
            content = read_scratchpad()
            print("\n--- Scratchpad ---")
            print(content or "(empty)")
            print("--- End ---\n")
            continue

        # TODO 5: Implement the memory-aware chat loop:
        #   a) Append the user message to history.
        #   b) Call provider.chat(history).
        #   c) Call process_response(result.text) to get (display_text, note, clear).
        #   d) If note: call write_scratchpad(note).
        #   e) If clear: SCRATCHPAD_PATH.write_text("") to wipe it.
        #   f) Append ChatMessage("assistant", display_text) to history.
        #   g) Call trim_history() to cap context size.
        #   h) Rebuild the system prompt (history[0]) with the updated scratchpad.
        #   i) Print "Assistant: <display_text>".

        print("TODO: implement the memory-aware chat loop.\n")
        break  # remove once implemented


if __name__ == "__main__":
    main()
