/**
 * Task 4 — Audio preprocessing & recognition  🟡
 *
 * What this teaches:
 *   - Why clean audio dramatically improves ASR accuracy.
 *   - Energy-based Voice Activity Detection (VAD) implemented from scratch:
 *     split into frames, compute RMS, threshold against the peak.
 *   - How to read and write WAV files in pure Node.js (no native deps).
 *   - Optional: how the same pattern maps to the noisereduce / WebRTC VAD
 *     libraries on the Python side.
 *
 * Why this matters:
 *   Whisper was trained on relatively clean speech. Real-world recordings
 *   contain background noise, silence pads, and codec artefacts.  Even
 *   simple silence-trimming reduces token cost and WER.
 *
 * How to run:
 *   pnpm tsx modules/19-audio-speech/ts/task4_audio_preprocessing.ts
 *
 *   Reads assets/sample.wav (auto-generated if absent by task1_stt.ts).
 *   Writes preprocessed files back to assets/.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.resolve(__dirname, "../assets");

// ---------------------------------------------------------------------------
// WAV I/O helpers
// ---------------------------------------------------------------------------

interface WavData {
  samples: Int16Array;
  sampleRate: number;
  nChannels: number;
}

/**
 * Read a 16-bit PCM WAV file and return its samples as Int16Array.
 */
function readWav(filePath: string): WavData {
  const buf = fs.readFileSync(filePath);
  // Parse the canonical 44-byte RIFF/WAV header.
  const nChannels = buf.readUInt16LE(22);
  const sampleRate = buf.readUInt32LE(24);
  // Find the "data" chunk (may not always start at byte 44).
  let dataOffset = 12;
  while (dataOffset < buf.length - 8) {
    const tag = buf.toString("ascii", dataOffset, dataOffset + 4);
    const chunkSize = buf.readUInt32LE(dataOffset + 4);
    if (tag === "data") {
      dataOffset += 8;
      break;
    }
    dataOffset += 8 + chunkSize;
  }
  const pcm = buf.subarray(dataOffset);
  const samples = new Int16Array(pcm.buffer, pcm.byteOffset, pcm.byteLength / 2);
  return { samples: new Int16Array(samples), sampleRate, nChannels };
}

/**
 * Write a WavData object to a 16-bit mono WAV file.
 */
function writeWav(filePath: string, data: WavData): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const pcmBytes = data.samples.byteLength;
  const header = Buffer.alloc(44);
  header.write("RIFF", 0);
  header.writeUInt32LE(36 + pcmBytes, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);                          // PCM
  header.writeUInt16LE(data.nChannels, 22);
  header.writeUInt32LE(data.sampleRate, 24);
  header.writeUInt32LE(data.sampleRate * 2 * data.nChannels, 28);
  header.writeUInt16LE(2 * data.nChannels, 32);
  header.writeUInt16LE(16, 34);
  header.write("data", 36);
  header.writeUInt32LE(pcmBytes, 40);
  const pcmBuf = Buffer.from(data.samples.buffer, data.samples.byteOffset, pcmBytes);
  fs.writeFileSync(filePath, Buffer.concat([header, pcmBuf]));
}

// ---------------------------------------------------------------------------
// Task A — Energy-based VAD
// ---------------------------------------------------------------------------

/**
 * Classify each audio frame as speech (true) or silence (false).
 *
 * Algorithm:
 *  1. Split samples into frames of `frameMs` milliseconds.
 *  2. Compute RMS energy per frame.
 *  3. Find the maximum RMS across all frames.
 *  4. Mark frames with RMS > thresholdRatio * maxRms as speech.
 *
 * @param samples        - PCM int16 samples (mono).
 * @param sampleRate     - Samples per second.
 * @param frameMs        - Frame duration in milliseconds.
 * @param thresholdRatio - Speech threshold as a fraction of peak RMS.
 * @returns              Array of booleans, one per frame.
 */
function energyVad(
  samples: Int16Array,
  sampleRate: number,
  frameMs = 30,
  thresholdRatio = 0.05,
): boolean[] {
  const frameSize = Math.floor((sampleRate * frameMs) / 1000);
  const nFrames = Math.floor(samples.length / frameSize);

  // TODO 1: Return one boolean per frame (`nFrames` total).
  //   - For each frame, take its slice of `samples` (length `frameSize`) and
  //     compute the RMS energy: root-mean-square of the samples (square, average,
  //     sqrt via Math.sqrt).
  //   - Find the peak RMS across all frames.
  //   - Map each frame's RMS to `true` when it clears `thresholdRatio * maxRms`.
  throw new Error("TODO 1: implement energy-based VAD");
}

// ---------------------------------------------------------------------------
// Task B — Silence trimmer
// ---------------------------------------------------------------------------

/**
 * Remove leading and trailing silence from a WAV.
 *
 * @param data           - Input WavData.
 * @param frameMs        - Frame size in ms (must match energyVad).
 * @param thresholdRatio - Silence threshold.
 * @returns              WavData with silence trimmed from both ends.
 */
function trimSilence(data: WavData, frameMs = 30, thresholdRatio = 0.05): WavData {
  const frameSize = Math.floor((data.sampleRate * frameMs) / 1000);

  // TODO 2: Use `energyVad(...)` to label frames, then keep only the speech span.
  //   - Find the first and last frame index marked `true` (the speech bounds); if
  //     nothing is speech, pick a sensible fallback (e.g. return `data` unchanged).
  //   - Convert those frame indices to sample offsets via `frameSize` and slice
  //     `data.samples` between them (include the final speech frame).
  //   - Return a `WavData` with the trimmed samples and the original sampleRate /
  //     nChannels.
  throw new Error("TODO 2: implement silence trimming");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const samplePath = path.join(ASSETS_DIR, "sample.wav");

if (!fs.existsSync(samplePath)) {
  console.error(`Sample WAV not found: ${samplePath}`);
  console.error("Run task1_stt.ts first — it generates the sample.wav file.");
  process.exit(1);
}

const data = readWav(samplePath);
console.log(
  `Loaded: ${samplePath}  (${data.samples.length} samples @ ${data.sampleRate} Hz)`,
);

// --- VAD / silence trim ---
try {
  const trimmed = trimSilence(data);
  const trimmedPath = path.join(ASSETS_DIR, "sample_trimmed.wav");
  writeWav(trimmedPath, trimmed);
  const origS = (data.samples.length / data.sampleRate).toFixed(2);
  const trimS = (trimmed.samples.length / trimmed.sampleRate).toFixed(2);
  console.log(`Trimmed silence: ${origS}s → ${trimS}s  (${trimmedPath})`);
} catch (e) {
  if (e instanceof Error && e.message.startsWith("TODO")) {
    console.log(`[skip] ${e.message}`);
  } else {
    throw e;
  }
}
