"""
Task 1 — Speech-to-text (STT / ASR)  🟢

What this teaches:
  - How to call the OpenAI Whisper API to transcribe audio.
  - How multimodal APIs differ from text-only chat APIs: you send binary audio
    data, not a string, and receive a transcript string back.
  - Optional: how to run whisper locally via faster-whisper for offline use.

How to run:
  uv run python modules/19-audio-speech/py/task1_stt.py

  The file uses the sample clip at modules/19-audio-speech/assets/sample.wav.
  If the file is absent the script generates a short sine-wave WAV so you
  always have something to transcribe.

Requirements:
  OPENAI_API_KEY must be set in .env (LLM_PROVIDER=openai not required —
  the OpenAI SDK is used directly for the audio endpoints).

Optional local path:
  uv sync --extra audio        # installs faster-whisper
  Then uncomment and call transcribe_local() at the bottom.
"""

from __future__ import annotations

import os
import struct
import wave
from pathlib import Path

# ---------------------------------------------------------------------------
# Audio helper — generate a sample .wav if none exists
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).parent.parent / "assets"
SAMPLE_WAV = ASSETS_DIR / "sample.wav"


def _ensure_sample_wav() -> Path:
    """Return path to a sample WAV, generating a short sine tone if needed."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_WAV.exists():
        import math

        sample_rate = 16_000
        duration_s = 2
        frequency = 440  # A4 note

        n_samples = sample_rate * duration_s
        samples = [
            int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            for i in range(n_samples)
        ]
        with wave.open(str(SAMPLE_WAV), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack(f"<{n_samples}h", *samples))
        print(f"[info] Generated synthetic sample: {SAMPLE_WAV}")
    return SAMPLE_WAV


# ---------------------------------------------------------------------------
# Hosted path — OpenAI Whisper API
# ---------------------------------------------------------------------------


def transcribe_hosted(audio_path: Path) -> str:
    """Transcribe audio using the OpenAI Whisper API.

    The API accepts .mp3, .mp4, .mpeg, .mpga, .m4a, .wav, .webm.

    Args:
        audio_path: Path to the audio file to transcribe.

    Returns:
        The transcript string.
    """
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env.")

    client = openai.OpenAI(api_key=api_key)

    # TODO 1: Transcribe the file via the Whisper endpoint.
    #   - Open audio_path in binary mode (a `with open(..., "rb")` block so the
    #     handle closes cleanly).
    #   - Call `client.audio.transcriptions.create(...)` with the Whisper model,
    #     the open file as `file=`, and `response_format="text"` so the call
    #     returns a plain string rather than a JSON object.
    #   - Return that transcript string.
    #   HINT: some SDK/server combos want `file=` as a
    #     (filename, fileobj, mimetype) tuple, e.g. built from `audio_path.name`.
    raise NotImplementedError("TODO 1: call client.audio.transcriptions.create()")


# ---------------------------------------------------------------------------
# Optional local path — faster-whisper
# ---------------------------------------------------------------------------


def transcribe_local(audio_path: Path, model_size: str = "base") -> str:
    """Transcribe audio locally using faster-whisper (no API key needed).

    Requires: uv sync --extra audio
    Download: the model weights are fetched automatically on first use
              (~74 MB for 'base', ~1.4 GB for 'large-v3').

    Args:
        audio_path: Path to the audio file.
        model_size: One of 'tiny', 'base', 'small', 'medium', 'large-v3'.

    Returns:
        The full transcript as a single string.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "faster-whisper not installed. Run: uv sync --extra audio"
        ) from exc

    # TODO 2 (optional): Run whisper locally.
    #   - Instantiate `WhisperModel(model_size, device=..., compute_type=...)` —
    #     pick a CPU-friendly device and a small compute type (e.g. int8) so it
    #     runs without a GPU.
    #   - Call `model.transcribe(str(audio_path))`; it returns a (segments,
    #     info) pair where `segments` is a generator.
    #   - Join the `.text` of each segment into one string and return it.
    raise NotImplementedError("TODO 2 (optional): implement local transcription")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    wav_path = _ensure_sample_wav()
    print(f"Transcribing: {wav_path}")

    transcript = transcribe_hosted(wav_path)
    print(f"\nTranscript (hosted Whisper):\n  {transcript!r}")

    # Uncomment to try the local path:
    # transcript_local = transcribe_local(wav_path)
    # print(f"\nTranscript (local faster-whisper):\n  {transcript_local!r}")


if __name__ == "__main__":
    main()
