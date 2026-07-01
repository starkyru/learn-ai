"""
Task 4 — Audio preprocessing & recognition  🟡

What this teaches:
  - Why clean audio dramatically improves ASR accuracy: Whisper's WER (word
    error rate) degrades sharply below ~20 dB SNR.
  - Energy-based Voice Activity Detection (VAD): the simplest baseline that
    still works surprisingly well for recorded speech.
  - Optional noise reduction via noisereduce (spectral subtraction) and
    WebRTC VAD (Google's production-grade VAD shipped in Chrome).
  - Speaker diarisation: what it is, why it's hard, and the hosted path
    via pyannote.audio.

Why this matters for ASR:
  The Whisper model was trained on relatively clean speech from the internet.
  Real-world audio often contains background music, overlapping speakers, or
  codec noise.  Even simple preprocessing — trimming silence, attenuating
  noise — can reduce WER by 10-30%.

How to run:
  uv run python modules/19-audio-speech/py/task4_audio_preprocessing.py

  The script runs on assets/sample.wav (auto-generated if absent) and writes
  preprocessed versions back to assets/.

Optional extras:
  uv sync --extra audio   # noisereduce, webrtcvad, soundfile, librosa
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path
from typing import NamedTuple

# Make sibling task files importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).parent))

ASSETS_DIR = Path(__file__).parent.parent / "assets"


# ---------------------------------------------------------------------------
# Utility: read / write WAV as list of int16 samples
# ---------------------------------------------------------------------------


class WavData(NamedTuple):
    samples: list[int]       # int16 PCM values
    sample_rate: int
    n_channels: int


def read_wav(path: Path) -> WavData:
    """Read a WAV file into a list of int16 PCM samples."""
    with wave.open(str(path), "r") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    n_samples = len(raw) // 2  # 16-bit = 2 bytes per sample
    samples = list(struct.unpack(f"<{n_samples}h", raw))
    return WavData(samples=samples, sample_rate=sample_rate, n_channels=n_channels)


def write_wav(path: Path, data: WavData) -> None:
    """Write int16 PCM samples back to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = struct.pack(f"<{len(data.samples)}h", *data.samples)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(data.n_channels)
        wf.setsampwidth(2)
        wf.setframerate(data.sample_rate)
        wf.writeframes(raw)


# ---------------------------------------------------------------------------
# Task A — Energy-based Voice Activity Detection (VAD)
# ---------------------------------------------------------------------------


def energy_vad(
    samples: list[int],
    sample_rate: int,
    frame_ms: int = 30,
    threshold_ratio: float = 0.05,
) -> list[bool]:
    """Classify each audio frame as speech (True) or silence (False).

    Algorithm:
      1. Split samples into frames of `frame_ms` milliseconds.
      2. Compute root-mean-square (RMS) energy per frame.
      3. Find the maximum RMS across all frames.
      4. Mark frames whose RMS > threshold_ratio * max_rms as speech.

    Args:
        samples:         PCM int16 samples (mono).
        sample_rate:     Samples per second (e.g. 16000).
        frame_ms:        Frame duration in milliseconds.
        threshold_ratio: Speech threshold as a fraction of the peak RMS.

    Returns:
        List of bool, one entry per frame (True = speech detected).
    """
    frame_size = int(sample_rate * frame_ms / 1000)
    frames = [
        samples[i : i + frame_size]
        for i in range(0, len(samples) - frame_size + 1, frame_size)
    ]

    # TODO 1: Turn `frames` into a per-frame speech/silence mask.
    #   - Compute the RMS energy of each frame — the root-mean-square of its
    #     samples (square each sample, average, take the sqrt via `math.sqrt`).
    #   - Find the peak RMS across all frames.
    #   - Return one bool per frame: True when that frame's RMS clears
    #     `threshold_ratio * max_rms` (i.e. it's loud enough to be speech).
    raise NotImplementedError("TODO 1: implement energy-based VAD")


def trim_silence(data: WavData, frame_ms: int = 30, threshold_ratio: float = 0.05) -> WavData:
    """Remove leading and trailing silence frames from a WAV.

    Args:
        data:            Input WAV data.
        frame_ms:        Frame duration in ms (must match energy_vad).
        threshold_ratio: Silence threshold (see energy_vad).

    Returns:
        A new WavData with silence trimmed from both ends.
    """
    frame_size = int(data.sample_rate * frame_ms / 1000)

    # TODO 2: Use `energy_vad(...)` to label frames, then keep only the speech span.
    #   - Find the first and last frame index marked True (the speech boundaries).
    #     If no frame is speech, decide on a sensible fallback (e.g. return data).
    #   - Convert those frame indices back to sample indices via `frame_size` and
    #     slice `data.samples` between them (include the last speech frame).
    #   - Return a new `WavData` with the trimmed samples, keeping the original
    #     sample_rate and n_channels.
    raise NotImplementedError("TODO 2: implement silence trimming")


# ---------------------------------------------------------------------------
# Task B — Optional: noise reduction via noisereduce
# ---------------------------------------------------------------------------


def reduce_noise_nr(data: WavData) -> WavData:
    """Apply spectral-subtraction noise reduction using noisereduce.

    Requires: uv sync --extra audio   (installs noisereduce, numpy)

    How it works:
      noisereduce estimates the noise floor from a short segment of the audio
      (the first 0.5 s by default) and subtracts that spectrum from the rest.
      This attenuates stationary noise (fan hum, mic hiss) without harming speech.

    Args:
        data: Input WAV data (mono, 16-bit PCM).

    Returns:
        Denoised WavData.
    """
    try:
        import numpy as np
        import noisereduce as nr  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "noisereduce not installed. Run: uv sync --extra audio"
        ) from exc

    # TODO 3 (optional): Denoise via noisereduce.
    #   - Convert `data.samples` to a float32 numpy array normalised to [-1, 1]
    #     (int16 PCM ranges up to 32767).
    #   - Run `nr.reduce_noise(y=..., sr=data.sample_rate)` to get the cleaned
    #     float signal.
    #   - Undo the normalisation back to int16 samples.
    #   - Return a new `WavData` with the denoised samples, same sample_rate and
    #     n_channels.
    raise NotImplementedError("TODO 3 (optional): apply noisereduce")


# ---------------------------------------------------------------------------
# Task C — Spot-check: compare transcription before vs. after denoising
# ---------------------------------------------------------------------------


def compare_transcriptions(original: Path, denoised: Path) -> None:
    """Transcribe both WAVs with Whisper and print side-by-side.

    This is the acceptance test: if your denoising actually helps ASR,
    the denoised transcript should be more accurate.

    Args:
        original: Path to the original WAV.
        denoised: Path to the denoised WAV.
    """
    from task1_stt import transcribe_hosted

    # TODO 4: Transcribe both files and print each transcript with a label.
    #   Use a try/except so that a missing OPENAI_API_KEY gives a clear message
    #   rather than a cryptic crash.
    raise NotImplementedError("TODO 4: transcribe and compare")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    from task1_stt import _ensure_sample_wav

    sample = _ensure_sample_wav()
    data = read_wav(sample)
    print(f"Loaded: {sample}  ({len(data.samples)} samples @ {data.sample_rate} Hz)")

    # --- VAD / silence trim ---
    trimmed_path = ASSETS_DIR / "sample_trimmed.wav"
    try:
        trimmed = trim_silence(data)
        write_wav(trimmed_path, trimmed)
        orig_s = len(data.samples) / data.sample_rate
        trim_s = len(trimmed.samples) / data.sample_rate
        print(f"Trimmed silence: {orig_s:.2f}s → {trim_s:.2f}s  ({trimmed_path})")
    except NotImplementedError as e:
        print(f"[skip] {e}")

    # --- Optional noise reduction ---
    denoised_path = ASSETS_DIR / "sample_denoised.wav"
    try:
        denoised = reduce_noise_nr(data)
        write_wav(denoised_path, denoised)
        print(f"Denoised audio saved to: {denoised_path}")
    except (NotImplementedError, ImportError) as e:
        print(f"[skip] {e}")

    # --- Compare transcriptions ---
    if denoised_path.exists():
        compare_transcriptions(sample, denoised_path)


if __name__ == "__main__":
    main()
