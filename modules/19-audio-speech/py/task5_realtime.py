"""
Task 5 — Realtime / streaming voice architectures  🟢

What this teaches:
  - The architectural difference between a *batch* STT→LLM→TTS pipeline
    (tasks 1-3) and a *realtime* streaming voice session.
  - The OpenAI Realtime API: a persistent WebSocket where audio chunks stream
    in, the model responds with both audio and text in parallel, and latency
    is measured in hundreds of milliseconds rather than multiple seconds.
  - When to choose batch vs. realtime, and why the answer is not always
    "realtime is better".

Batch pipeline (tasks 1-3):
  Audio clip ──► Whisper API ──► LLM chat ──► TTS API ──► Audio clip
  Latency: STT (1-3 s) + LLM (1-5 s) + TTS (1-2 s) ≈ 3-10 s total

Realtime pipeline (this task):
  Audio stream ──► WebSocket ──► GPT-4o-realtime ──► Audio stream
                                 (STT + LLM + TTS happen in one step)
  Latency: ~300-500 ms to first audio byte

How to run:
  # Inspect the client (no API call):
  uv run python modules/19-audio-speech/py/task5_realtime.py --dry-run

  # Run a single-turn realtime session (OPENAI_API_KEY required):
  uv run python modules/19-audio-speech/py/task5_realtime.py --file assets/sample.wav

Requirements:
  OPENAI_API_KEY — the Realtime API is gated to OpenAI keys with access to
                   the gpt-4o-realtime-preview model.

Note on the TS mirror:
  The TypeScript version (task5_realtime.ts) uses the same WebSocket-based
  protocol via the openai Node SDK.  Compare both to see how little differs
  across languages at the protocol level.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import wave
from pathlib import Path

ASSETS_DIR = Path(__file__).parent.parent / "assets"

# ---------------------------------------------------------------------------
# Realtime session helper
# ---------------------------------------------------------------------------

REALTIME_MODEL = "gpt-4o-realtime-preview"
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"


async def run_realtime_session(audio_path: Path) -> None:
    """Send one audio turn to the OpenAI Realtime API and print/save the reply.

    Protocol overview (simplified):
      client → {"type": "session.update", ...}          # configure voice
      client → {"type": "input_audio_buffer.append", ...} # send audio chunks
      client → {"type": "input_audio_buffer.commit"}    # end of input
      client → {"type": "response.create"}              # ask for response
      server ← {"type": "response.audio.delta", ...}   # audio chunks arrive
      server ← {"type": "response.audio_transcript.delta"} # text transcript
      server ← {"type": "response.done"}               # session complete

    Args:
        audio_path: Path to a PCM WAV file (16 kHz, mono, 16-bit preferred).
    """
    try:
        import websockets  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "websockets not installed. Run: pip install websockets\n"
            "Or add it to your venv: uv add websockets"
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "OpenAI-Beta": "realtime=v1",
    }

    # TODO 1: Drive one realtime turn over the WebSocket. Every event you send or
    #         receive is a JSON object with a "type" field (see the docstring and
    #         the dry_run() function for the exact event names/shapes to mirror).
    #
    #   - Connect with `websockets.connect(REALTIME_URL, additional_headers=headers)`
    #     (an async context manager).
    #   - Send a `session.update` event whose "session" configures both audio and
    #     text modalities, a voice, and pcm16 for input and output audio.
    #   - Read the WAV's PCM payload (use `_read_wav_pcm`), base64-encode it, and
    #     send it in an `input_audio_buffer.append` event; then `commit` the buffer
    #     and ask for a `response.create`.
    #   - Loop over incoming messages until you see a `response.done`:
    #       * accumulate the base64 audio from each `response.audio.delta`,
    #       * print the text from each `response.audio_transcript.delta` as it lands.
    #   - Decode and write the collected audio to ASSETS_DIR/"realtime_reply.raw",
    #     then print that path.
    #   HINT: `json.dumps(...)` to send, `json.loads(...)` to parse each message.
    raise NotImplementedError("TODO 1: implement realtime WebSocket session")


def _read_wav_pcm(path: Path) -> bytes:
    """Read raw PCM bytes from a WAV file (strips the WAV header)."""
    with wave.open(str(path), "r") as wf:
        return wf.readframes(wf.getnframes())


# ---------------------------------------------------------------------------
# Dry-run: show the protocol events without making an API call
# ---------------------------------------------------------------------------


def dry_run() -> None:
    """Print the sequence of WebSocket events without connecting."""
    print("=== Realtime API protocol (dry run) ===\n")
    events = [
        {
            "direction": "client → server",
            "type": "session.update",
            "payload": {
                "session": {
                    "modalities": ["audio", "text"],
                    "voice": "nova",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                }
            },
        },
        {
            "direction": "client → server",
            "type": "input_audio_buffer.append",
            "payload": {"audio": "<base64-encoded PCM16 chunk>"},
        },
        {
            "direction": "client → server",
            "type": "input_audio_buffer.commit",
            "payload": {},
        },
        {
            "direction": "client → server",
            "type": "response.create",
            "payload": {},
        },
        {
            "direction": "server → client",
            "type": "response.audio_transcript.delta",
            "payload": {"delta": "Hello! How can I help…"},
        },
        {
            "direction": "server → client",
            "type": "response.audio.delta",
            "payload": {"delta": "<base64-encoded PCM16 audio chunk>"},
        },
        {
            "direction": "server → client",
            "type": "response.done",
            "payload": {},
        },
    ]
    for ev in events:
        print(f"  [{ev['direction']}]")
        print(f"  type: {ev['type']}")
        print(f"  payload: {json.dumps(ev['payload'], indent=4)}\n")

    print("Key insight:")
    print("  In the batch pipeline (tasks 1–3) the full audio must be uploaded")
    print("  before transcription starts, and TTS output arrives only AFTER the")
    print("  LLM finishes. In the realtime session, audio chunks are processed")
    print("  incrementally and the model can begin speaking before it has finished")
    print("  generating the full response text. This cuts perceived latency by ~5x.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAI Realtime API demo")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the WebSocket protocol without making an API call",
    )
    group.add_argument(
        "--file",
        type=Path,
        metavar="WAV",
        help="Path to a WAV file to send to the Realtime API",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        asyncio.run(run_realtime_session(args.file))


if __name__ == "__main__":
    main()
