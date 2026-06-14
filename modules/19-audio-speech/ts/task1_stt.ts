/**
 * Task 1 — Speech-to-text (STT / ASR)  🟢
 *
 * What this teaches:
 *   - How to call the OpenAI Whisper API from Node.js to transcribe audio.
 *   - How the audio endpoint differs from the chat endpoint: you send a
 *     multipart/form-data body with the binary audio file, not JSON text.
 *   - How to provide a synthetic WAV file so the exercise runs without a
 *     real microphone recording.
 *
 * How to run:
 *   pnpm tsx modules/19-audio-speech/ts/task1_stt.ts
 *
 *   Looks for modules/19-audio-speech/assets/sample.wav; generates a short
 *   synthetic tone if the file is absent.
 *
 * Requirements:
 *   OPENAI_API_KEY must be set in .env.
 */

import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import OpenAI from "openai";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.resolve(__dirname, "../assets");
const SAMPLE_WAV = path.join(ASSETS_DIR, "sample.wav");

// ---------------------------------------------------------------------------
// Helper — generate a minimal synthetic WAV (16-bit mono sine tone)
// ---------------------------------------------------------------------------

function ensureSampleWav(): string {
  if (fs.existsSync(SAMPLE_WAV)) return SAMPLE_WAV;

  fs.mkdirSync(ASSETS_DIR, { recursive: true });

  const sampleRate = 16_000;
  const durationS = 2;
  const frequency = 440; // A4
  const nSamples = sampleRate * durationS;

  // Build PCM samples
  const pcm = Buffer.alloc(nSamples * 2);
  for (let i = 0; i < nSamples; i++) {
    const value = Math.round(32767 * Math.sin((2 * Math.PI * frequency * i) / sampleRate));
    pcm.writeInt16LE(value, i * 2);
  }

  // WAV header (44 bytes)
  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16);        // chunk size
  header.writeUInt16LE(1, 20);         // PCM format
  header.writeUInt16LE(1, 22);         // mono
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(sampleRate * 2, 28); // byte rate
  header.writeUInt16LE(2, 32);         // block align
  header.writeUInt16LE(16, 34);        // bits per sample
  header.write("data", 36);
  header.writeUInt32LE(pcm.length, 40);

  fs.writeFileSync(SAMPLE_WAV, Buffer.concat([header, pcm]));
  console.log(`[info] Generated synthetic sample: ${SAMPLE_WAV}`);
  return SAMPLE_WAV;
}

// ---------------------------------------------------------------------------
// Hosted path — OpenAI Whisper API
// ---------------------------------------------------------------------------

/**
 * Transcribe an audio file using the OpenAI Whisper API.
 *
 * @param audioPath - Absolute path to a WAV (or MP3/M4A/etc.) file.
 * @returns The transcript text.
 */
async function transcribeHosted(audioPath: string): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set. Add it to .env.");

  const client = new OpenAI({ apiKey });

  // TODO 1: Call client.audio.transcriptions.create({
  //   model: "whisper-1",
  //   file: fs.createReadStream(audioPath),
  //   response_format: "text",
  // }) and return the result.
  //
  // HINT: the return type is `string` when response_format is "text".
  throw new Error("TODO 1: call client.audio.transcriptions.create()");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const wavPath = ensureSampleWav();
console.log(`Transcribing: ${wavPath}`);

const transcript = await transcribeHosted(wavPath);
console.log(`\nTranscript (hosted Whisper):\n  ${JSON.stringify(transcript)}`);
