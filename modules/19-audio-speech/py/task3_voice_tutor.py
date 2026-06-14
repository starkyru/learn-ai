"""
Task 3 — Voice tutor loop  🟡  (flagship)

What this teaches:
  - How to chain STT → LLM → TTS into a real-time voice interaction loop.
  - RAG-style retrieval over module READMEs so the tutor can answer questions
    about course content (re-uses the same cosine-similarity retrieval from
    module 05 — no external vector DB needed).
  - The practical latency budget for a voice pipeline and where to spend it.

How it works:
  1. Record a short audio clip (via sounddevice, optional) or load a WAV file.
  2. Transcribe the clip with Whisper (task1_stt.py's transcribe_hosted).
  3. Retrieve the top-k matching chunks from the module READMEs (RAG).
  4. Ask the LLM to answer using only the retrieved context.
  5. Synthesise the answer as speech (task2_tts.py's synthesise) and play it.

How to run:
  # Microphone mode (requires: uv sync --extra audio)
  uv run python modules/19-audio-speech/py/task3_voice_tutor.py --mic

  # File mode (no extra deps needed beyond OPENAI_API_KEY):
  uv run python modules/19-audio-speech/py/task3_voice_tutor.py --file assets/sample.wav

Requirements:
  OPENAI_API_KEY — for Whisper STT and TTS.
  LLM_PROVIDER   — any provider for the chat step (defaults to openai).

Optional extras:
  uv sync --extra audio   # sounddevice + soundfile for microphone recording
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Optional

# Make sibling task files importable when running from the repo root.
sys.path.insert(0, str(Path(__file__).parent))

from llm_core import ChatMessage, get_provider

# Reuse helpers from the earlier tasks in this module.
from task1_stt import transcribe_hosted, _ensure_sample_wav  # noqa: E402
from task2_tts import synthesise  # noqa: E402

ASSETS_DIR = Path(__file__).parent.parent / "assets"
MODULES_DIR = Path(__file__).parent.parent.parent  # learn-ai/modules/

# ---------------------------------------------------------------------------
# Step 1 — Corpus: load all module READMEs
# ---------------------------------------------------------------------------


def load_readme_corpus() -> list[dict[str, str]]:
    """Walk learn-ai/modules/*/README.md and return a list of text chunks.

    Each chunk is a dict with keys "source" and "text".
    The README text is split into paragraphs (double-newline boundary) so
    individual chunks remain focused.
    """
    docs: list[dict[str, str]] = []
    for readme in sorted(MODULES_DIR.glob("*/README.md")):
        raw = readme.read_text(encoding="utf-8", errors="ignore")
        # Split on blank lines; keep non-trivial paragraphs.
        paragraphs = [p.strip() for p in raw.split("\n\n") if len(p.strip()) > 80]
        for i, para in enumerate(paragraphs):
            docs.append({"source": f"{readme.parent.name}#{i}", "text": para})
    return docs


# ---------------------------------------------------------------------------
# Step 2 — Embed corpus and build an in-memory index
# ---------------------------------------------------------------------------


def build_index(corpus: list[dict[str, str]]) -> tuple[list[list[float]], list[dict[str, str]]]:
    """Embed all corpus chunks and return (vectors, corpus).

    Uses get_provider().embed() — works with openai, ollama, etc.

    Args:
        corpus: List of {"source": ..., "text": ...} dicts.

    Returns:
        (vectors, corpus) where vectors[i] corresponds to corpus[i].
    """
    provider = get_provider()
    texts = [doc["text"] for doc in corpus]

    # TODO 1: Call provider.embed(texts) and return (result.vectors, corpus).
    #         HINT: result = provider.embed(texts); return result.vectors, corpus
    #         Note: embedding all READMEs in one batch may hit token limits on
    #         some providers. If needed, batch in groups of 50.
    raise NotImplementedError("TODO 1: embed the corpus chunks")


# ---------------------------------------------------------------------------
# Step 3 — Retrieve: cosine similarity search
# ---------------------------------------------------------------------------


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors (pure Python)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b + 1e-9)


def retrieve(
    query: str,
    vectors: list[list[float]],
    corpus: list[dict[str, str]],
    top_k: int = 3,
) -> list[dict[str, str]]:
    """Return the top-k corpus chunks most similar to the query.

    Args:
        query:   The user's question text.
        vectors: Pre-computed embedding vectors for each corpus chunk.
        corpus:  The corresponding chunk dicts.
        top_k:   Number of chunks to return.

    Returns:
        List of {"source": ..., "text": ..., "score": ...} dicts.
    """
    provider = get_provider()

    # TODO 2: Embed the query string (provider.embed([query]).vectors[0]),
    #         compute cosine_similarity against every vector in `vectors`,
    #         sort by descending similarity, and return the top_k chunks with
    #         their score added under the key "score".
    raise NotImplementedError("TODO 2: embed query and rank corpus chunks")


# ---------------------------------------------------------------------------
# Step 4 — Generate: RAG prompt + LLM answer
# ---------------------------------------------------------------------------


def answer_with_rag(question: str, chunks: list[dict[str, str]]) -> str:
    """Build a RAG prompt from retrieved chunks and return the LLM's answer.

    Args:
        question: The user's question (already transcribed from speech).
        chunks:   Top-k retrieved context chunks.

    Returns:
        The assistant's answer as a plain string (will be spoken via TTS).
    """
    provider = get_provider()

    context_block = "\n\n".join(
        f"[{c['source']}]\n{c['text']}" for c in chunks
    )

    system = (
        "You are a voice tutor for the learn-ai course. "
        "Answer the student's question using ONLY the provided context excerpts. "
        "If the context does not contain the answer, say so honestly. "
        "Keep your answer under 3 sentences — it will be read aloud."
    )

    # TODO 3: Build a messages list:
    #   [ChatMessage("system", system),
    #    ChatMessage("user", f"Context:\n{context_block}\n\nQuestion: {question}")]
    #   Call provider.chat(messages) and return result.text.
    raise NotImplementedError("TODO 3: call provider.chat() with RAG context")


# ---------------------------------------------------------------------------
# Step 5 — Record (optional microphone path)
# ---------------------------------------------------------------------------


def record_from_mic(duration_s: int = 5, sample_rate: int = 16_000) -> Path:
    """Record from the default microphone and save to a temporary WAV file.

    Requires: uv sync --extra audio  (installs sounddevice + soundfile).

    Args:
        duration_s:  Recording length in seconds.
        sample_rate: Sample rate in Hz (Whisper expects 16 kHz).

    Returns:
        Path to the recorded WAV file.
    """
    try:
        import sounddevice as sd  # type: ignore[import]
        import soundfile as sf   # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "sounddevice and soundfile are required for microphone input. "
            "Run: uv sync --extra audio"
        ) from exc

    out_path = ASSETS_DIR / "mic_recording.wav"
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # TODO 4 (optional): Use sd.rec(int(duration_s * sample_rate),
    #   samplerate=sample_rate, channels=1, dtype="int16") to record audio.
    #   Wait for completion with sd.wait(), then save to out_path with sf.write().
    raise NotImplementedError("TODO 4 (optional): implement microphone recording")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def build_corpus_index() -> tuple[list[list[float]], list[dict[str, str]]]:
    """Load module READMEs and build the embedding index (cached in-memory)."""
    print("[tutor] Loading module READMEs...")
    corpus = load_readme_corpus()
    print(f"[tutor] Loaded {len(corpus)} chunks from {MODULES_DIR}")
    print("[tutor] Embedding corpus (this may take a moment)...")
    vectors, corpus = build_index(corpus)
    print(f"[tutor] Index built. {len(vectors)} embeddings ready.")
    return vectors, corpus


def run_voice_loop(audio_path: Optional[Path], use_mic: bool) -> None:
    """Main voice-tutor interaction loop."""
    vectors, corpus = build_corpus_index()

    print("\n[tutor] Voice Tutor ready. Ctrl-C to quit.\n")

    while True:
        # --- Acquire audio ---
        if use_mic:
            input("Press Enter, then speak for 5 seconds...")
            wav = record_from_mic(duration_s=5)
        else:
            wav = audio_path or _ensure_sample_wav()
            print(f"[tutor] Using audio file: {wav}")

        # --- STT ---
        print("[tutor] Transcribing...")
        question = transcribe_hosted(wav)
        print(f"[tutor] You said: {question!r}")

        if not question.strip():
            print("[tutor] No speech detected. Skipping.")
            continue

        # --- Retrieve ---
        chunks = retrieve(question, vectors, corpus, top_k=3)
        print(f"[tutor] Retrieved {len(chunks)} context chunks.")

        # --- Generate ---
        print("[tutor] Generating answer...")
        answer = answer_with_rag(question, chunks)
        print(f"[tutor] Answer: {answer}")

        # --- TTS ---
        answer_wav = ASSETS_DIR / "tutor_answer.mp3"
        synthesise(answer, answer_wav)
        print(f"[tutor] Answer saved to: {answer_wav}")
        print("       (Play the file to hear the response.)\n")

        if not use_mic:
            # Single-shot mode when using a file.
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Voice tutor for learn-ai")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--mic", action="store_true", help="Record from microphone")
    group.add_argument("--file", type=Path, metavar="WAV", help="Path to a WAV file")
    args = parser.parse_args()

    run_voice_loop(audio_path=args.file, use_mic=args.mic)


if __name__ == "__main__":
    main()
