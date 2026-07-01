/**
 * Task 5 — Realtime / streaming voice architectures  🟢
 *
 * What this teaches:
 *   - The architectural difference between the batch STT→LLM→TTS pipeline
 *     (tasks 1-3) and a realtime streaming voice session.
 *   - The OpenAI Realtime API: a persistent WebSocket where audio chunks
 *     stream in/out and the model responds in hundreds of milliseconds.
 *   - When to choose batch vs. realtime (cost, latency, complexity trade-offs).
 *
 * Batch pipeline (tasks 1-3):
 *   Audio clip ──► Whisper API ──► LLM chat ──► TTS API ──► Audio clip
 *   Latency: STT (1-3 s) + LLM (1-5 s) + TTS (1-2 s) ≈ 3-10 s total
 *
 * Realtime pipeline (this task):
 *   Audio stream ──► WebSocket ──► GPT-4o-realtime ──► Audio stream
 *   Latency: ~300-500 ms to first audio byte
 *
 * How to run:
 *   # Print the WebSocket protocol without making an API call:
 *   pnpm tsx modules/19-audio-speech/ts/task5_realtime.ts --dry-run
 *
 *   # Run a real session (OPENAI_API_KEY required):
 *   pnpm tsx modules/19-audio-speech/ts/task5_realtime.ts --file assets/sample.wav
 *
 * Requirements:
 *   OPENAI_API_KEY — gated to gpt-4o-realtime-preview model access.
 *
 * Note: this file uses the openai Node SDK's WebSocket helper (available
 * since openai@4.57.0). The Python mirror uses the raw websockets library to
 * show the protocol more explicitly.
 */

import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import OpenAI from "openai";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.resolve(__dirname, "../assets");
const REALTIME_MODEL = "gpt-4o-realtime-preview";

// ---------------------------------------------------------------------------
// Realtime session
// ---------------------------------------------------------------------------

/**
 * Send one audio turn to the OpenAI Realtime API and save the reply audio.
 *
 * Protocol overview:
 *   client → session.update             (configure voice/modalities)
 *   client → input_audio_buffer.append  (send PCM16 audio, base64-encoded)
 *   client → input_audio_buffer.commit  (end of audio input)
 *   client → response.create            (request model response)
 *   server ← response.audio.delta       (audio chunks arrive)
 *   server ← response.audio_transcript.delta  (text transcript arrives)
 *   server ← response.done              (session complete)
 *
 * @param audioPath - Path to a 16 kHz mono 16-bit PCM WAV file.
 */
async function runRealtimeSession(audioPath: string): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set. Add it to .env.");

  const client = new OpenAI({ apiKey });

  // TODO 1: Drive one realtime turn over the WebSocket. Each event has a `type`
  //   field (see the docstring and dryRun() for the exact event names/shapes).
  //
  //   - Open a session with the openai SDK's realtime WebSocket helper, passing
  //     REALTIME_MODEL.
  //   - Send a `session.update` event whose session config enables both audio and
  //     text modalities, picks a voice, and sets pcm16 for input and output audio.
  //   - Read the WAV's PCM bytes (skip the 44-byte header), base64-encode them,
  //     and send them in an `input_audio_buffer.append`; then `commit` the buffer
  //     and request a `response.create`.
  //   - Subscribe to incoming messages (e.g. `session.on("message", ...)`):
  //       * accumulate the base64 audio from each `response.audio.delta`,
  //       * print the text from each `response.audio_transcript.delta`.
  //   - When `response.done` arrives, decode the collected audio and write it to
  //     ASSETS_DIR/realtime_reply.raw.
  throw new Error("TODO 1: implement realtime WebSocket session");
}

// ---------------------------------------------------------------------------
// Dry-run: print the protocol events without connecting
// ---------------------------------------------------------------------------

function dryRun(): void {
  console.log("=== Realtime API protocol (dry run) ===\n");

  const events = [
    {
      direction: "client → server",
      type: "session.update",
      payload: {
        session: {
          modalities: ["audio", "text"],
          voice: "nova",
          input_audio_format: "pcm16",
          output_audio_format: "pcm16",
        },
      },
    },
    {
      direction: "client → server",
      type: "input_audio_buffer.append",
      payload: { audio: "<base64-encoded PCM16 chunk>" },
    },
    {
      direction: "client → server",
      type: "input_audio_buffer.commit",
      payload: {},
    },
    {
      direction: "client → server",
      type: "response.create",
      payload: {},
    },
    {
      direction: "server → client",
      type: "response.audio_transcript.delta",
      payload: { delta: "Hello! How can I help…" },
    },
    {
      direction: "server → client",
      type: "response.audio.delta",
      payload: { delta: "<base64-encoded PCM16 audio chunk>" },
    },
    {
      direction: "server → client",
      type: "response.done",
      payload: {},
    },
  ];

  for (const ev of events) {
    console.log(`  [${ev.direction}]`);
    console.log(`  type: ${ev.type}`);
    console.log(`  payload: ${JSON.stringify(ev.payload, null, 4)}\n`);
  }

  console.log("Key insight:");
  console.log(
    "  In the batch pipeline (tasks 1–3) the full audio must be uploaded\n" +
    "  before transcription starts, and TTS output arrives only AFTER the\n" +
    "  LLM finishes. In the realtime session, audio chunks are processed\n" +
    "  incrementally and the model can begin speaking before it has finished\n" +
    "  generating the full response text. This cuts perceived latency by ~5x.",
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const arg = process.argv[2];

if (arg === "--dry-run") {
  dryRun();
} else if (arg === "--file") {
  const audioPath = process.argv[3];
  if (!audioPath) {
    console.error("Usage: task5_realtime.ts --file <wav-path>");
    process.exit(1);
  }
  await runRealtimeSession(audioPath);
} else if (!arg) {
  // Default: dry run
  dryRun();
} else {
  // Treat positional arg as a file path
  await runRealtimeSession(arg);
}
