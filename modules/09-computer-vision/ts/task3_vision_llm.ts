/**
 * task3_vision_llm.ts — image understanding via a multimodal LLM.  🟡
 *
 * What it teaches:
 *   Modern LLMs (GPT-4o, Claude 3+) accept images alongside text. Under the
 *   hood they use a vision encoder (ViT) to produce "image tokens" that are
 *   interleaved with text tokens before the language model's attention layers.
 *   The result is flexible, natural-language image understanding.
 *
 *   Going beyond the abstraction:
 *     @learn-ai/llm-core's LLMProvider is TEXT-ONLY. Sending an image requires
 *     the raw vendor SDKs (openai, anthropic) because the multimodal message
 *     format — content arrays with image blocks — is not part of the shared
 *     interface. This exercise uses the SDKs directly so you see the real
 *     request shape. That's the lesson: know where your abstraction leaks and
 *     how to step around it cleanly.
 *
 *   When to use a multimodal LLM vs tasks 1/2:
 *     - Task 1 (classifier): fast, deterministic, cheap — great for a fixed set
 *       of labels.
 *     - Task 2 (CLIP): open vocabulary zero-shot, good for ranking candidates.
 *     - Task 3 (LLM): rich understanding, OCR, answering questions — use when
 *       you need reasoning, not just classification.
 *
 * How to run (from the repo root):
 *   # With OpenAI (gpt-4o-mini is cheapest):
 *   LLM_PROVIDER=openai pnpm tsx modules/09-computer-vision/ts/task3_vision_llm.ts
 *
 *   # With Anthropic (Claude):
 *   LLM_PROVIDER=anthropic pnpm tsx modules/09-computer-vision/ts/task3_vision_llm.ts
 *
 * Environment variables (in .env):
 *   OPENAI_API_KEY      — for the OpenAI path
 *   OPENAI_VISION_MODEL — model to use (default: gpt-4o-mini)
 *   ANTHROPIC_API_KEY   — for the Anthropic path
 *   ANTHROPIC_MODEL     — model to use (default: claude-haiku-4-5)
 *   LLM_PROVIDER        — "openai" or "anthropic"
 *
 * Acceptance:
 *   - Prints a natural-language description of the sample image.
 *   - Prints a one-word classification label.
 *   - Works with at least one of OpenAI or Anthropic.
 */

import "dotenv/config";
import { readFileSync, existsSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import https from "node:https";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(__dirname, "..", "assets");
const SAMPLE_IMAGE = path.join(ASSETS_DIR, "cat.jpg");

const DESCRIBE_PROMPT =
  "Describe this image in 2-3 sentences. " +
  "Then on a new line starting with 'Label:', give a single word that best " +
  "classifies the main subject (e.g. 'cat', 'car', 'mountain').";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function imageToBase64(imagePath: string): string {
  return readFileSync(imagePath).toString("base64");
}

function mimeType(imagePath: string): string {
  return imagePath.endsWith(".png") ? "image/png" : "image/jpeg";
}

// ---------------------------------------------------------------------------
// OpenAI path
// ---------------------------------------------------------------------------

async function describeWithOpenAI(imagePath: string, prompt: string): Promise<string> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) throw new Error("Missing OPENAI_API_KEY in .env");

  // We import OpenAI SDK directly — not via llm-core — because we need
  // the raw multimodal message format.
  const { default: OpenAI } = await import("openai");
  const client = new OpenAI({ apiKey });

  const model = process.env.OPENAI_VISION_MODEL ?? "gpt-4o-mini";
  const b64 = imageToBase64(imagePath);
  const mime = mimeType(imagePath);

  // TODO (exercise): build a multimodal messages array and call the API.
  //
  // The OpenAI multimodal message format wraps content as an array of parts:
  //
  // const response = await client.chat.completions.create({
  //   model,
  //   messages: [
  //     {
  //       role: "user",
  //       content: [
  //         { type: "text", text: prompt },
  //         {
  //           type: "image_url",
  //           image_url: { url: `data:${mime};base64,${b64}` },
  //         },
  //       ],
  //     },
  //   ],
  //   max_tokens: 512,
  // });
  //
  // return response.choices[0].message.content ?? "";

  throw new Error(
    "Complete the TODO: build the multimodal messages array and call " +
    "client.chat.completions.create(). Return the reply text."
  );
}

// ---------------------------------------------------------------------------
// Anthropic path
// ---------------------------------------------------------------------------

async function describeWithAnthropic(imagePath: string, prompt: string): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("Missing ANTHROPIC_API_KEY in .env");

  const { default: Anthropic } = await import("@anthropic-ai/sdk");
  const client = new Anthropic({ apiKey });

  const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5";
  const b64 = imageToBase64(imagePath);
  const mime = mimeType(imagePath) as "image/jpeg" | "image/png" | "image/gif" | "image/webp";

  // TODO (exercise): build an Anthropic multimodal message and call the API.
  //
  // Anthropic's image format uses a "source" block:
  //
  // const message = await client.messages.create({
  //   model,
  //   max_tokens: 512,
  //   messages: [
  //     {
  //       role: "user",
  //       content: [
  //         {
  //           type: "image",
  //           source: { type: "base64", media_type: mime, data: b64 },
  //         },
  //         { type: "text", text: prompt },
  //       ],
  //     },
  //   ],
  // });
  //
  // const block = message.content[0];
  // return block.type === "text" ? block.text : "";

  throw new Error(
    "Complete the TODO: build the Anthropic multimodal message and call " +
    "client.messages.create(). Return the reply text."
  );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function ensureSampleImage(): Promise<string> {
  await mkdir(ASSETS_DIR, { recursive: true });
  if (existsSync(SAMPLE_IMAGE)) return SAMPLE_IMAGE;

  const url =
    "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg";
  console.log(`Downloading sample image → ${SAMPLE_IMAGE}`);

  await new Promise<void>((resolve, reject) => {
    const file = fs.createWriteStream(SAMPLE_IMAGE);
    https.get(url, (res) => {
      res.pipe(file);
      file.on("finish", () => { file.close(); resolve(); });
    }).on("error", reject);
  });

  return SAMPLE_IMAGE;
}

async function main(): Promise<void> {
  const imagePath = await ensureSampleImage();
  const provider = process.env.LLM_PROVIDER ?? "openai";

  console.log(`Image    : ${path.basename(imagePath)}`);
  console.log(`Provider : ${provider}`);
  console.log(`Prompt   : ${DESCRIBE_PROMPT}`);
  console.log();

  let reply: string;

  if (provider === "openai") {
    reply = await describeWithOpenAI(imagePath, DESCRIBE_PROMPT);
  } else if (provider === "anthropic") {
    reply = await describeWithAnthropic(imagePath, DESCRIBE_PROMPT);
  } else {
    throw new Error(
      `Provider '${provider}' does not support vision in this exercise. ` +
      "Set LLM_PROVIDER=openai or LLM_PROVIDER=anthropic."
    );
  }

  console.log("Model reply:");
  console.log(reply);
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
