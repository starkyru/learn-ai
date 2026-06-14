/**
 * Task 3 — Voice tutor loop  🟡  (flagship)
 *
 * What this teaches:
 *   - How to chain STT → LLM → TTS into a complete voice interaction loop.
 *   - RAG-style retrieval over the module READMEs (plain cosine similarity,
 *     no external vector DB) so the tutor answers questions about course content.
 *   - Practical latency: where each step spends time and what to optimise first.
 *
 * Pipeline:
 *   WAV file ──► Whisper (STT) ──► embed query ──► cosine search over READMEs
 *            ──► LLM (RAG answer) ──► TTS ──► MP3 file
 *
 * How to run:
 *   # File mode (default — uses assets/sample.wav):
 *   pnpm tsx modules/19-audio-speech/ts/task3_voice_tutor.ts
 *
 *   # Point at any WAV:
 *   pnpm tsx modules/19-audio-speech/ts/task3_voice_tutor.ts path/to/audio.wav
 *
 * Requirements:
 *   OPENAI_API_KEY — for Whisper STT and TTS.
 *   LLM_PROVIDER   — any provider for the chat+embed steps.
 */

import "dotenv/config";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider } from "@learn-ai/llm-core";
import OpenAI from "openai";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.resolve(__dirname, "../assets");
const MODULES_DIR = path.resolve(__dirname, "../../"); // learn-ai/modules/

// ---------------------------------------------------------------------------
// Step 1 — Corpus: load all module READMEs
// ---------------------------------------------------------------------------

interface Chunk {
  source: string;
  text: string;
}

/**
 * Walk learn-ai/modules/*/README.md and return paragraph-level chunks.
 * Splitting by blank lines keeps each chunk focused on a single idea.
 */
function loadReadmeCorpus(): Chunk[] {
  const chunks: Chunk[] = [];
  const moduleDirs = fs.readdirSync(MODULES_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort();

  for (const dir of moduleDirs) {
    const readmePath = path.join(MODULES_DIR, dir, "README.md");
    if (!fs.existsSync(readmePath)) continue;
    const raw = fs.readFileSync(readmePath, "utf-8");
    const paragraphs = raw.split(/\n\n+/).map((p) => p.trim()).filter((p) => p.length > 80);
    paragraphs.forEach((text, i) => {
      chunks.push({ source: `${dir}#${i}`, text });
    });
  }
  return chunks;
}

// ---------------------------------------------------------------------------
// Step 2 — Embed corpus and build in-memory index
// ---------------------------------------------------------------------------

/**
 * Embed all corpus chunks using the configured provider.
 *
 * @param corpus - Array of text chunks.
 * @returns      Tuple of [vectors, corpus].
 */
async function buildIndex(corpus: Chunk[]): Promise<[number[][], Chunk[]]> {
  const provider = getProvider();
  const texts = corpus.map((c) => c.text);

  // TODO 1: Call provider.embed(texts) and return [result.vectors, corpus].
  //   If the provider has token limits, consider batching in groups of 50.
  //   HINT: const result = await provider.embed(texts);
  //         return [result.vectors, corpus];
  throw new Error("TODO 1: embed the corpus chunks");
}

// ---------------------------------------------------------------------------
// Step 3 — Retrieve: cosine similarity search
// ---------------------------------------------------------------------------

function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB) + 1e-9);
}

/**
 * Return the top-k corpus chunks most similar to the query.
 *
 * @param query   - The user's question.
 * @param vectors - Pre-computed embeddings for each corpus chunk.
 * @param corpus  - The corresponding chunk objects.
 * @param topK    - Number of chunks to return.
 */
async function retrieve(
  query: string,
  vectors: number[][],
  corpus: Chunk[],
  topK = 3,
): Promise<Array<Chunk & { score: number }>> {
  const provider = getProvider();

  // TODO 2: Embed the query with provider.embed([query]).
  //   Compute cosineSimilarity between queryVec and each entry in vectors.
  //   Sort by descending score and return the top topK chunks with a "score" field.
  throw new Error("TODO 2: embed query and rank corpus chunks");
}

// ---------------------------------------------------------------------------
// Step 4 — Generate: RAG answer via LLM
// ---------------------------------------------------------------------------

/**
 * Build a RAG prompt from retrieved chunks and return the LLM's answer.
 * The answer is intentionally kept short (≤3 sentences) for TTS readability.
 *
 * @param question - The transcribed user question.
 * @param chunks   - Top-k retrieved context chunks.
 * @returns        The assistant's plain-text answer.
 */
async function answerWithRag(
  question: string,
  chunks: Array<Chunk & { score: number }>,
): Promise<string> {
  const provider = getProvider();

  const contextBlock = chunks
    .map((c) => `[${c.source}]\n${c.text}`)
    .join("\n\n");

  const system =
    "You are a voice tutor for the learn-ai course. " +
    "Answer the student's question using ONLY the provided context excerpts. " +
    "If the context does not contain the answer, say so honestly. " +
    "Keep your answer under 3 sentences — it will be read aloud.";

  // TODO 3: Build a messages array and call provider.chat(messages).
  //   messages = [
  //     { role: "system", content: system },
  //     { role: "user",   content: `Context:\n${contextBlock}\n\nQuestion: ${question}` },
  //   ];
  //   Return result.text.
  throw new Error("TODO 3: call provider.chat() with RAG context");
}

// ---------------------------------------------------------------------------
// Step 5 — STT helper (reuse Whisper from task1)
// ---------------------------------------------------------------------------

async function transcribeHosted(audioPath: string): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set.");
  const client = new OpenAI({ apiKey });

  // TODO 4: Same as task1_stt.ts — call client.audio.transcriptions.create()
  //   and return the transcript text.
  throw new Error("TODO 4: transcribe audio");
}

// ---------------------------------------------------------------------------
// Step 6 — TTS helper (reuse from task2)
// ---------------------------------------------------------------------------

async function synthesise(text: string, outputPath: string): Promise<void> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("OPENAI_API_KEY is not set.");
  const client = new OpenAI({ apiKey });
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  // TODO 5: Same as task2_tts.ts — synthesise speech and write to outputPath.
  throw new Error("TODO 5: synthesise TTS audio");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const audioArg = process.argv[2];
const audioPath = audioArg ?? path.join(ASSETS_DIR, "sample.wav");

if (!fs.existsSync(audioPath)) {
  console.error(`Audio file not found: ${audioPath}`);
  console.error("Run task1_stt.ts first (it generates the sample WAV).");
  process.exit(1);
}

console.log("[tutor] Loading module READMEs...");
const corpus = loadReadmeCorpus();
console.log(`[tutor] Loaded ${corpus.length} chunks`);

console.log("[tutor] Embedding corpus...");
const [vectors, indexedCorpus] = await buildIndex(corpus);
console.log(`[tutor] Index ready — ${vectors.length} embeddings`);

console.log(`[tutor] Transcribing: ${audioPath}`);
const question = await transcribeHosted(audioPath);
console.log(`[tutor] You said: ${JSON.stringify(question)}`);

const chunks = await retrieve(question, vectors, indexedCorpus);
console.log(`[tutor] Retrieved ${chunks.length} context chunks`);

const answer = await answerWithRag(question, chunks);
console.log(`[tutor] Answer: ${answer}`);

const answerMp3 = path.join(ASSETS_DIR, "tutor_answer.mp3");
await synthesise(answer, answerMp3);
console.log(`[tutor] Answer audio saved to: ${answerMp3}`);
