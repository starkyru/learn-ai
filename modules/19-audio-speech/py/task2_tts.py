"""
Task 2 — Text-to-speech (TTS)  🟢

What this teaches:
  - How to call the OpenAI TTS API to synthesise speech from text.
  - The key knobs: voice, model (tts-1 vs tts-1-hd), speed, response_format.
  - How to stream TTS output directly to a file without buffering the full
    response in memory — important for longer texts.

How to run:
  uv run python modules/19-audio-speech/py/task2_tts.py

  Saves the output to modules/19-audio-speech/assets/output.mp3.

Requirements:
  OPENAI_API_KEY must be set in .env.
"""

from __future__ import annotations

import os
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"
OUTPUT_MP3 = ASSETS_DIR / "output.mp3"

# Text that will be spoken; feel free to change it.
SAMPLE_TEXT = (
    "Hello! I am your AI study assistant. "
    "Today we will explore how text-to-speech synthesis works. "
    "The model converts this text into natural-sounding audio in real time."
)

# OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
DEFAULT_VOICE = "nova"

# tts-1 is fast and cheap; tts-1-hd is higher quality (slower, costs ~2x more).
DEFAULT_MODEL = "tts-1"


# ---------------------------------------------------------------------------
# Synthesis — buffered
# ---------------------------------------------------------------------------


def synthesise(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
    speed: float = 1.0,
) -> Path:
    """Convert text to speech and save to output_path.

    Args:
        text:        The text to speak.
        output_path: Where to save the .mp3 file.
        voice:       One of: alloy, echo, fable, onyx, nova, shimmer.
        model:       "tts-1" (fast) or "tts-1-hd" (higher quality).
        speed:       Playback speed multiplier, 0.25–4.0.

    Returns:
        output_path (for chaining / printing).
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")

    client = openai.OpenAI(api_key=api_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # TODO 1: Call client.audio.speech.create(model=..., voice=..., input=...,
    #         speed=..., response_format="mp3") and write the result to
    #         output_path using response.stream_to_file(output_path).
    #         HINT: the return value has a .stream_to_file() method.
    raise NotImplementedError("TODO 1: call client.audio.speech.create()")


# ---------------------------------------------------------------------------
# Synthesis — streaming (stretch goal)
# ---------------------------------------------------------------------------


def synthesise_streaming(
    text: str,
    output_path: Path,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
) -> Path:
    """Synthesise speech and write chunks as they arrive (lower latency).

    Uses the streaming context manager to avoid loading the full audio into
    memory before writing.  Useful when generating long texts.

    Args:
        text:        The text to speak.
        output_path: Where to save the .mp3 file.
        voice:       OpenAI voice name.
        model:       TTS model id.

    Returns:
        output_path.
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")

    client = openai.OpenAI(api_key=api_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # TODO 2 (stretch): Use client.audio.speech.with_streaming_response.create(...)
    #   as a context manager. Inside the block, open output_path in "wb" mode
    #   and call response.stream_to_file(output_path).
    #   This is functionally identical to synthesise() above but demonstrates
    #   the streaming API surface.
    raise NotImplementedError("TODO 2 (stretch): implement streaming TTS")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Synthesising: {SAMPLE_TEXT[:60]}...")
    out = synthesise(SAMPLE_TEXT, OUTPUT_MP3)
    print(f"Saved to: {out}")
    print("Open the file in any audio player to hear the result.")

    # Experiment prompts:
    # 1. Change DEFAULT_VOICE to "onyx" or "shimmer" and re-run.
    # 2. Change DEFAULT_MODEL to "tts-1-hd" and listen for quality difference.
    # 3. Set speed=0.75 for a slower narration.
    # 4. Replace SAMPLE_TEXT with a passage from one of the module READMEs.


if __name__ == "__main__":
    main()
