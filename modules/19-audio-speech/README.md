# Module 19 — Audio & Speech

> **Depth tags** 🟢 app-level · 🟡 build-one-piece-by-hand · 🔴 from-scratch

Voice is the most natural human interface. This module takes you from a raw
audio waveform through automatic speech recognition (ASR), text-to-speech
synthesis (TTS), and a full voice-tutor loop — then zooms into the signal
processing that makes recognition work in the real world.

You will transcribe speech with OpenAI Whisper, synthesise voice from text,
build a talking course assistant (STT → RAG → TTS), implement energy-based
voice activity detection from scratch, and explore the OpenAI Realtime API
that collapses the three-step pipeline into a single low-latency WebSocket.

---

## Concepts

### The audio modality

Audio is a one-dimensional time series: a sequence of pressure samples taken
at a fixed rate (typically 16 000 samples/second for speech, 44 100 for music).
A 2-second recording at 16 kHz is 32 000 integers — far smaller than a HD image
but large enough that sending the full stream to an LLM requires chunking,
streaming, or offline batching.

```
microphone → ADC → PCM samples (int16) → WAV file / streaming buffer
```

All ASR and TTS models ultimately consume or produce this raw sample stream.
The `.wav` container is just a header (44 bytes) followed by raw PCM; you can
inspect and generate it with pure Python or Node.js standard libraries (tasks 1
and 4 demonstrate this).

### Speech-to-text (STT / ASR)

Automatic speech recognition maps an audio waveform to a text transcript. The
dominant architecture is the **encoder–decoder transformer**: the encoder
converts mel-spectrogram frames into contextual representations, and the decoder
auto-regressively generates the word-piece token sequence.

**OpenAI Whisper** (2022) is the reference open-source ASR model, trained on
680 000 hours of multilingual internet audio. It is available:

- **Hosted** via `client.audio.transcriptions.create()` (whisper-1, ~$0.006/min)
- **Local** via `faster-whisper` — a CTranslate2 re-implementation that runs
  4-8× faster than the original PyTorch model on CPU.

**Groq** also offers a hosted Whisper endpoint with very low latency if you have
a Groq API key (`groq` library, same OpenAI-compatible endpoint shape).

### Text-to-speech (TTS)

TTS inverts the ASR process: given a text string, synthesise a natural-sounding
speech waveform. Modern neural TTS models (WaveNet → Tacotron → FastSpeech 2 →
diffusion-based) all follow the same high-level pattern:

```
text → phonemes → mel-spectrogram → vocoder → PCM waveform
```

**OpenAI TTS** (`client.audio.speech.create()`) offers six voices (alloy, echo,
fable, onyx, nova, shimmer) and two models:

| Model    | Quality | Latency | Cost       |
|----------|---------|---------|------------|
| tts-1    | good    | fast    | $15/M chars |
| tts-1-hd | better  | slower  | $30/M chars |

The response body is a binary audio stream you can write directly to disk as
an `.mp3` (or `.wav`, `.opus`, etc.).

### Voice agent pipeline (batch)

The simplest voice interaction loop:

```
mic audio → Whisper API → transcript
              ↓
          LLM + RAG → answer text
              ↓
          TTS API → speech → speaker
```

**Latency budget** (rough numbers for hosted APIs):
- Whisper transcription: 1–3 s for a 5-second clip
- LLM answer (gpt-4o-mini): 1–4 s
- TTS synthesis: 1–2 s for a short sentence
- Total: **3–9 s** round-trip

This is acceptable for asynchronous voice notes but too slow for natural
conversation. The Realtime API (task 5) addresses this.

### Audio preprocessing: why it matters

ASR models are trained on relatively clean speech. Real-world recordings
contain:

- **Background noise**: fan hum, HVAC, traffic
- **Codec artefacts**: MP3 compression at low bitrate
- **Silence pads**: several seconds of silence before speech starts
- **Overlapping speech**: multiple speakers at once

Even simple preprocessing cuts word error rate (WER) significantly:

| Preprocessing step | Typical WER reduction |
|---|---|
| Silence trimming (VAD) | 5–10% (faster inference, fewer hallucinations) |
| Noise reduction (spectral subtraction) | 10–25% in noisy conditions |
| Speaker diarisation | Enables per-speaker transcription |

**Voice Activity Detection (VAD)**: the problem of detecting which frames
contain speech vs. silence. Task 4 implements an energy-based baseline:
split the audio into 30ms frames, compute RMS energy per frame, mark frames
above a threshold as "speech". This is the simplest possible approach and
works surprisingly well for studio recordings.

More sophisticated VAD: **WebRTC VAD** (Google, C library, Python bindings via
`webrtcvad`) uses a Gaussian mixture model; **Silero VAD** is a tiny LSTM-based
model that runs in real time on CPU.

**Noise reduction**: `noisereduce` (Python) implements spectral subtraction — it
estimates the noise spectrum from a silent segment and subtracts it from the
signal spectrum frame by frame. Good for stationary noise (fan, hiss); less
effective for non-stationary noise (speech, music).

**Speaker diarisation**: "who spoke when?" — segments the audio by speaker
identity without knowing the speakers in advance. The canonical open-source
library is `pyannote.audio` (requires a HuggingFace token). The hosted path
is AssemblyAI or Deepgram.

### Realtime voice architecture

The OpenAI **Realtime API** replaces the three-step batch pipeline with a
single persistent WebSocket:

```
audio stream ──► WebSocket ──► GPT-4o-realtime ──► audio stream
                    (STT + LLM + TTS in one step, streaming)
```

The model begins speaking before it has finished generating the full text
(streaming text tokens drive streaming audio synthesis in parallel). First
audio byte arrives in **300–500 ms** vs. 3–9 s for the batch pipeline.

Trade-offs vs. batch pipeline:

| | Batch (tasks 1–3) | Realtime (task 5) |
|---|---|---|
| Latency | 3–9 s | 300–500 ms |
| Cost | Pay per STT + LLM + TTS | Higher per-minute rate |
| Control | Full: inject RAG context, filter output | Limited: model handles everything |
| Reliability | Each step independently retried | Single WebSocket failure = full restart |
| Use case | Voice notes, async queries | Conversational voice agents |

---

## Setup

### Python

All tasks require:

```bash
OPENAI_API_KEY=... # in .env
```

Tasks 1, 2, 3, 5 work with the base install:

```bash
uv sync
```

Tasks 3 (microphone mode) and 4 (noise reduction, WebRTC VAD) require:

```bash
uv sync --extra audio   # installs sounddevice, soundfile, noisereduce
```

The `audio` extra is **optional**: all tasks have a file-mode path that works
without microphone access.

### TypeScript

```bash
pnpm install   # from repo root — picks up openai dep in ts/package.json
```

The TypeScript tasks use the `openai` npm package directly (same as Python).
No additional npm packages are required for basic operation.

### New env vars

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | required | Whisper STT, TTS, Realtime API |
| `LLM_PROVIDER` | `openai` | Chat + embed provider for task 3 voice tutor |

---

## Running the exercises

**Python** (from the repo root):

```bash
uv run python modules/19-audio-speech/py/task1_stt.py
uv run python modules/19-audio-speech/py/task2_tts.py
uv run python modules/19-audio-speech/py/task3_voice_tutor.py --file assets/sample.wav
uv run python modules/19-audio-speech/py/task4_audio_preprocessing.py
uv run python modules/19-audio-speech/py/task5_realtime.py --dry-run
```

**TypeScript** (from the repo root):

```bash
pnpm tsx modules/19-audio-speech/ts/task1_stt.ts
pnpm tsx modules/19-audio-speech/ts/task2_tts.ts
pnpm tsx modules/19-audio-speech/ts/task3_voice_tutor.ts
pnpm tsx modules/19-audio-speech/ts/task4_audio_preprocessing.ts
pnpm tsx modules/19-audio-speech/ts/task5_realtime.ts --dry-run
```

The sample WAV (`assets/sample.wav`) is generated automatically if absent.

---

## Tasks

### Task 1 — Speech-to-text  🟢

**Goal:** transcribe an audio clip using the OpenAI Whisper API; optionally
run the same model locally with faster-whisper.

**Steps**

1. Read `task1_stt.py` / `task1_stt.ts`. Note how the synthetic WAV is
   generated — you can see the 44-byte header structure directly.
2. **Python**: complete `TODO 1` inside `transcribe_hosted()` — call
   `client.audio.transcriptions.create(model="whisper-1", file=..., response_format="text")`.
3. **TypeScript**: complete `TODO 1` inside `transcribeHosted()` — call the
   same method via the `openai` Node SDK.
4. Run the exercise. The synthetic sine-tone will produce a short or empty
   transcript (Whisper needs real speech). Replace `assets/sample.wav` with a
   real recording for a meaningful transcript.
5. **Optional** (`TODO 2` in Python): uncomment and complete `transcribe_local()`
   using `faster-whisper`. Run `uv sync --extra audio` first.

**Acceptance**
- Script runs without error and prints a transcript (or "(empty)" for a sine tone).
- Replacing the WAV with a real recording produces a readable transcript.

---

### Task 2 — Text-to-speech  🟢

**Goal:** synthesise speech from text using the OpenAI TTS API and save the
audio to disk.

**Steps**

1. Read `task2_tts.py` / `task2_tts.ts`. Note the voice and model options.
2. **Python**: complete `TODO 1` inside `synthesise()` — call
   `client.audio.speech.create(model=..., voice=..., input=..., speed=...)` and
   write the result to disk.
3. **TypeScript**: complete `TODO 1` — same call via the Node SDK. Convert the
   response `.arrayBuffer()` to a Buffer and `fs.writeFileSync` it.
4. Run the exercise. Open `assets/output.mp3` in any audio player.
5. Experiment: change the voice, model, speed, and text.

**Acceptance**
- `assets/output.mp3` exists and contains audible speech.
- Changing `DEFAULT_VOICE` to a different value produces a different voice.

---

### Task 3 — Voice tutor loop  🟡  (flagship)

**Goal:** chain STT → RAG retrieval over module READMEs → LLM answer → TTS
into a complete voice-interaction loop.

**Steps**

1. Read `task3_voice_tutor.py` / `task3_voice_tutor.ts` end to end. Trace the
   five steps: load corpus, embed, retrieve, generate, synthesise.
2. **Python** — `TODO 1`: embed the corpus in `build_index()`.
3. **Python** — `TODO 2`: embed the query and rank chunks in `retrieve()`.
4. **Python** — `TODO 3`: build a RAG prompt and call `provider.chat()` in
   `answer_with_rag()`.
5. **TypeScript**: mirror the same three TODOs in the TS file.
6. Run `task1_stt` first to generate `assets/sample.wav`, then run the voice
   tutor in file mode:
   ```bash
   uv run python modules/19-audio-speech/py/task3_voice_tutor.py --file assets/sample.wav
   ```
7. Replace the sample WAV with a real recording of a question like "What is
   RAG?" and listen to the synthesised answer.
8. **Optional** — `TODO 4` (Python mic mode): implement `record_from_mic()`
   and run with `--mic`. Requires `uv sync --extra audio`.

**Acceptance**
- Running in file mode produces an answer MP3 that answers the question in
  the audio file, drawing on the module READMEs as context.
- The latency breakdown (embed, retrieve, LLM, TTS) is visible in the logs.

---

### Task 4 — Audio preprocessing & recognition  🟡

**Goal:** implement energy-based VAD from scratch and understand how
preprocessing improves ASR accuracy.

**Steps**

1. Read `task4_audio_preprocessing.py` / `task4_audio_preprocessing.ts` top to
   bottom. Understand the WAV I/O helpers.
2. **Python / TypeScript** — `TODO 1`: implement `energy_vad()` /
   `energyVad()` — split into frames, compute RMS per frame, threshold against
   peak RMS.
3. **Python / TypeScript** — `TODO 2`: implement `trim_silence()` /
   `trimSilence()` — find the first and last speech frame, slice the samples.
4. Run the exercise. Check that `assets/sample_trimmed.wav` is shorter than
   the original.
5. **Optional** — `TODO 3` (Python only): implement `reduce_noise_nr()` using
   the `noisereduce` library. Run `uv sync --extra audio` first.
6. **Optional** — `TODO 4` (Python only): implement `compare_transcriptions()`
   to measure whether denoising improved the Whisper transcript.

**Acceptance**
- `sample_trimmed.wav` exists and the log shows reduced duration.
- You can explain, in one sentence, why trimming silence reduces WER.

---

### Task 5 — Realtime voice  🟢

**Goal:** understand the realtime WebSocket architecture and contrast it with
the batch pipeline. Optionally send a live audio turn to the OpenAI Realtime API.

**Steps**

1. Run the dry-run mode first — no API key needed:
   ```bash
   uv run python modules/19-audio-speech/py/task5_realtime.py --dry-run
   pnpm tsx modules/19-audio-speech/ts/task5_realtime.ts --dry-run
   ```
   Read the printed event sequence carefully. Match each event to the
   conceptual diagram in the Concepts section.
2. Compare the event sequence to the batch pipeline in task 3. Where does
   "streaming" save time?
3. **Python** — `TODO 1` (optional, needs Realtime API access): implement
   `run_realtime_session()` using the `websockets` library.
4. **TypeScript** — `TODO 1` (optional): implement `runRealtimeSession()` using
   the `openai` SDK's WebSocket helper.

**Acceptance**
- `--dry-run` mode runs without errors and prints the full event sequence.
- You can describe the latency difference and the architectural trade-offs
  between the batch pipeline and the Realtime API.

---

## Done when

- [ ] Task 1: transcribed an audio clip with hosted Whisper.
- [ ] Task 2: synthesised speech from text, opened the MP3, heard it.
- [ ] Task 3: asked the voice tutor a question about the course and received
       a spoken answer drawn from the module READMEs.
- [ ] Task 4: implemented energy-based VAD and trimmed silence from a WAV.
- [ ] Task 5: can explain the realtime pipeline and when you'd choose it over
       the batch pipeline.

---

## Going deeper

### Local ASR models

- **faster-whisper** — CTranslate2 port of Whisper; 4–8× faster on CPU with
  int8 quantisation. `tiny` is 75 MB and runs in real time on a 2019 MacBook Pro.
  [github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **whisper.cpp** — C++ port; runs on Apple Silicon Metal GPU.
  [github.com/ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- **Parakeet / Canary** (NVIDIA NeMo) — SOTA open ASR models for English with
  WER approaching human-level on clean speech.

### Groq Whisper endpoint

Groq hosts Whisper at very low latency (often under 300 ms for a short clip).
The endpoint is OpenAI-compatible; just change `base_url`:

```python
import groq
client = groq.Groq()
result = client.audio.transcriptions.create(
    model="whisper-large-v3-turbo", file=audio_file
)
```

### Diarisation

- **pyannote.audio** — the standard open-source pipeline; requires a HuggingFace
  token for the gated model.
  [huggingface.co/pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
- **AssemblyAI** / **Deepgram** — hosted diarisation via REST API.

### Neural TTS alternatives

- **Coqui TTS** — open-source, many voices, local inference.
- **ElevenLabs** — highest-quality voice cloning; REST API.
- **Bark** (Suno) — expressive TTS including laughter and non-speech sounds.

### Streaming audio from browsers

In production voice agents, the browser streams audio directly to your backend
via **WebRTC** or **WebSocket**. The backend pipes chunks to the STT API and
streams TTS audio back. Libraries:

- Python: `aiortc` (WebRTC), `websockets`
- Node.js: `ws`, `@anthropic-ai/sdk` streaming, Twilio Media Streams
- [LiveKit](https://livekit.io) — managed WebRTC infra with first-class LLM
  agent integration.

### Papers

- [Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)](https://arxiv.org/abs/2212.04356)
- [Natural TTS Synthesis by Conditioning WaveNet on Mel Spectrogram Predictions (Tacotron 2)](https://arxiv.org/abs/1712.05884)
- [FastSpeech 2: Fast and High-Quality End-to-End Text to Speech](https://arxiv.org/abs/2006.04558)
