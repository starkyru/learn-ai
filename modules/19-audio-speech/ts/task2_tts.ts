/**
 * Task 2 — Text-to-speech (TTS)  🟢
 *
 * What this teaches:
 *   - How to call the OpenAI TTS API from Node.js.
 *   - The key options: voice, model (tts-1 vs tts-1-hd), speed, output format.
 *   - How to write the response body to disk using Node streams — important
 *     for larger texts where buffering the full audio wastes memory.
 *
 * How to run:
 *   pnpm tsx modules/19-audio-speech/ts/task2_tts.ts
 *
 *   Saves the result to modules/19-audio-speech/assets/output.mp3.
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
const OUTPUT_MP3 = path.join(ASSETS_DIR, "output.mp3");

const SAMPLE_TEXT =
  "Hello! I am your AI study assistant. " +
  "Today we will explore how text-to-speech synthesis works. " +
  "The model converts this text into natural-sounding audio in real time.";

// OpenAI TTS voices: alloy | echo | fable | onyx | nova | shimmer
const DEFAULT_VOICE = "nova" as const;

// tts-1 is fast and cheap; tts-1-hd is higher quality.
const DEFAULT_MODEL = "tts-1" as const;

// ---------------------------------------------------------------------------
// Synthesis — buffered
// ---------------------------------------------------------------------------

/**
 * Convert text to speech and save to outputPath.
 *
 * @param text       - The text to speak.
 * @param outputPath - Where to save the .mp3 file.
 * @param voice      - One of: alloy | echo | fable | onyx | nova | shimmer.
 * @param model      - "tts-1" (fast) or "tts-1-hd" (high quality).
 * @param speed      - Playback speed multiplier, 0.25–4.0.
 * @returns          Absolute path to the saved file.
 */
async function synthesise(
  text: string,
  outputPath: string,
  voice: OpenAI.Audio.Speech.SpeechCreateParams["voice"] = DEFAULT_VOICE,
  model: OpenAI.Audio.Speech.SpeechModel = DEFAULT_MODEL,
  speed = 1.0,
): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set. Add it to .env.");

  const client = new OpenAI({ apiKey });
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  // TODO 1: Call `client.audio.speech.create({ ... })` passing the `model`,
  //   `voice`, the text as `input:`, the `speed`, and `response_format: "mp3"`.
  //   Then persist the audio to `outputPath` and return `outputPath`.
  //   HINT: the response exposes `.arrayBuffer()`; wrap it in a `Buffer` and
  //   write it to disk with the fs API.
  throw new Error("TODO 1: call client.audio.speech.create()");
}

// ---------------------------------------------------------------------------
// Synthesis — streaming (stretch goal)
// ---------------------------------------------------------------------------

/**
 * Synthesise speech and pipe response bytes to disk as they arrive.
 *
 * Demonstrates the streaming response API surface for lower memory footprint.
 *
 * @param text       - The text to speak.
 * @param outputPath - Where to save the .mp3 file.
 * @param voice      - OpenAI voice name.
 * @param model      - TTS model id.
 * @returns          Absolute path to the saved file.
 */
async function synthesiseStreaming(
  text: string,
  outputPath: string,
  voice: OpenAI.Audio.Speech.SpeechCreateParams["voice"] = DEFAULT_VOICE,
  model: OpenAI.Audio.Speech.SpeechModel = DEFAULT_MODEL,
): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set. Add it to .env.");

  const client = new OpenAI({ apiKey });
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  // TODO 2 (stretch): Same output as synthesise(), but stream the bytes to disk
  //   instead of buffering the whole response. Call `client.audio.speech.create`
  //   as before, then pipe the response's readable body into a write stream over
  //   `outputPath` (e.g. `fs.createWriteStream(...)`). Return `outputPath`.
  //   HINT: the response object exposes its stream via `response.body`.
  throw new Error("TODO 2 (stretch): implement streaming TTS");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

console.log(`Synthesising: ${SAMPLE_TEXT.slice(0, 60)}...`);
const out = await synthesise(SAMPLE_TEXT, OUTPUT_MP3);
console.log(`Saved to: ${out}`);
console.log("Open the file in any audio player to hear the result.");

// Experiment prompts:
// 1. Change DEFAULT_VOICE to "onyx" or "shimmer" and re-run.
// 2. Change DEFAULT_MODEL to "tts-1-hd" and listen for quality difference.
// 3. Set speed=0.75 for a slower narration.

export { synthesise, synthesiseStreaming };
