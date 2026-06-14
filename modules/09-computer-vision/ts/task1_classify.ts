/**
 * task1_classify.ts — image classification with a pretrained model.  🟢
 *
 * What it teaches:
 *   A pretrained ViT (Vision Transformer) model assigns ImageNet labels to an
 *   image. We use @huggingface/transformers (transformers.js) so this runs
 *   entirely in Node — no Python, no GPU, no server required. The model is
 *   downloaded once (~90 MB for the quantised version) and cached locally.
 *
 *   If you prefer NOT to download the model, use the HOSTED path below which
 *   calls the HuggingFace Inference API instead (requires HF_TOKEN).
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/09-computer-vision/ts/task1_classify.ts
 *
 *   # Force the hosted API path:
 *   USE_HF_API=true pnpm tsx modules/09-computer-vision/ts/task1_classify.ts
 *
 * Environment variables (in .env):
 *   HF_TOKEN     — required only when USE_HF_API=true
 *   USE_HF_API   — set to "true" to skip local model download
 *
 * Acceptance:
 *   - Prints a ranked list of label/score pairs for the sample image.
 *   - Works via local transformers.js (default) or hosted API.
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

// ViT-base pretrained on ImageNet (1000 classes).
// transformers.js will download + cache this on first run.
const HF_MODEL = "Xenova/vit-base-patch16-224";

interface ClassificationResult {
  label: string;
  score: number;
}

// ---------------------------------------------------------------------------
// LOCAL path — transformers.js runs the model in Node (default)
// ---------------------------------------------------------------------------

async function classifyLocal(imagePath: string): Promise<ClassificationResult[]> {
  // TODO (exercise): import the pipeline from @huggingface/transformers and
  // create an image-classification pipeline, then run it on the image.
  //
  // import { pipeline } from "@huggingface/transformers";
  //
  // const classifier = await pipeline("image-classification", HF_MODEL);
  //
  // The pipeline accepts a file path (as a string) or a URL.
  // const results = await classifier(imagePath);
  //
  // results is an array of { label: string; score: number }[].
  // Return them sorted by score descending.

  throw new Error(
    "Complete the TODO: import pipeline from @huggingface/transformers, " +
    "create a classifier, and call it with imagePath."
  );
}

// ---------------------------------------------------------------------------
// HOSTED path — HuggingFace Inference API (no local model download)
// ---------------------------------------------------------------------------

async function classifyHosted(imagePath: string): Promise<ClassificationResult[]> {
  const token = process.env.HF_TOKEN;
  if (!token) {
    throw new Error(
      "Missing HF_TOKEN. Get a free token at huggingface.co/settings/tokens " +
      "and add HF_TOKEN=... to your .env file."
    );
  }

  const imageBytes = readFileSync(imagePath);
  const model = "google/vit-base-patch16-224";

  // TODO (exercise): call the HF Inference API endpoint:
  //   POST https://api-inference.huggingface.co/models/<model>
  //   Headers: Authorization: Bearer <token>, Content-Type: application/octet-stream
  //   Body: raw image bytes
  //
  // The response is JSON: [{ "label": "...", "score": 0.9 }, ...]
  //
  // Hint: use the built-in `fetch` (Node 18+) or `node:https`.

  const response = await fetch(
    `https://api-inference.huggingface.co/models/${model}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/octet-stream",
      },
      body: imageBytes,
    }
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HF API error ${response.status}: ${body}`);
  }

  // TODO (exercise): parse the JSON response and return it as ClassificationResult[].
  const data = (await response.json()) as ClassificationResult[];

  // Replace the throw below with: return data.sort((a, b) => b.score - a.score);
  throw new Error(
    "Parse the response JSON and return sorted results. " +
    "Remove this throw and add: return data.sort((a, b) => b.score - a.score);"
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
  const useApi = process.env.USE_HF_API === "true";

  console.log(`Image    : ${path.basename(imagePath)}`);
  console.log(`Mode     : ${useApi ? "HF Inference API (hosted)" : "transformers.js (local)"}`);
  console.log(`Model    : ${useApi ? "google/vit-base-patch16-224" : HF_MODEL}`);
  console.log();

  const results = useApi
    ? await classifyHosted(imagePath)
    : await classifyLocal(imagePath);

  console.log("Top predictions:");
  results.slice(0, 5).forEach((item, i) => {
    console.log(`  ${i + 1}. ${item.label.padEnd(40)} ${item.score.toFixed(3)}`);
  });
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
