/**
 * task2_clip.ts — zero-shot image classification with CLIP.  🟢
 *
 * What it teaches:
 *   CLIP (Contrastive Language–Image Pretraining) learns a shared embedding
 *   space where images and text captions are pulled together if they match and
 *   pushed apart if they don't. At inference time you can ask "which of these
 *   text labels best describes this image?" by computing cosine similarities
 *   between the image embedding and each candidate label embedding.
 *
 *   Zero-shot: CLIP was never trained on a labelled dataset for *your* classes.
 *   You supply arbitrary candidate labels at runtime — the model generalises.
 *
 *   transformers.js ships a CLIP pipeline for Node, so this task runs locally
 *   without a server. A hosted fallback (HF Inference API) is also provided.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/09-computer-vision/ts/task2_clip.ts
 *
 *   # Force the hosted API path:
 *   USE_HF_API=true pnpm tsx modules/09-computer-vision/ts/task2_clip.ts
 *
 * Environment variables (in .env):
 *   HF_TOKEN     — required only when USE_HF_API=true
 *   USE_HF_API   — "true" to use hosted API instead of local model
 *
 * Acceptance:
 *   - Prints each candidate label with its CLIP score.
 *   - The correct label (matching the image content) ranks highest.
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

// CLIP model — transformers.js downloads the ONNX-quantised version (~300 MB).
const HF_CLIP_MODEL = "Xenova/clip-vit-base-patch32";

// Candidate labels for zero-shot classification — change these freely!
const CANDIDATE_LABELS = [
  "a photo of a cat",
  "a photo of a dog",
  "a photo of a bird",
  "a photo of a car",
  "a photo of a landscape",
];

interface ScoredLabel {
  label: string;
  score: number;
}

// ---------------------------------------------------------------------------
// LOCAL path — CLIP via transformers.js
// ---------------------------------------------------------------------------

async function clipLocal(
  imagePath: string,
  labels: string[]
): Promise<ScoredLabel[]> {
  // TODO (exercise): import the pipeline and run CLIP.
  //
  // import { pipeline } from "@huggingface/transformers";
  //
  // const classifier = await pipeline("zero-shot-image-classification", HF_CLIP_MODEL);
  //
  // The pipeline accepts the image path and an array of candidate labels:
  //   const output = await classifier(imagePath, { candidate_labels: labels });
  //
  // output is an object: { labels: string[], scores: number[] }
  // Zip them into ScoredLabel[] and sort by score descending.

  throw new Error(
    "Complete the TODO: import pipeline from @huggingface/transformers and " +
    "call the zero-shot-image-classification pipeline."
  );
}

// ---------------------------------------------------------------------------
// HOSTED path — HF Inference API
// ---------------------------------------------------------------------------

async function clipHosted(
  imagePath: string,
  labels: string[]
): Promise<ScoredLabel[]> {
  const token = process.env.HF_TOKEN;
  if (!token) {
    throw new Error(
      "Missing HF_TOKEN. Add HF_TOKEN=... to your .env file."
    );
  }

  const imageBytes = readFileSync(imagePath);
  const hostedModel = "openai/clip-vit-base-patch32";

  const payload = {
    inputs: imageBytes.toString("base64"),
    parameters: { candidate_labels: labels },
  };

  // TODO (exercise): POST to the HF zero-shot-image-classification endpoint.
  //
  // URL: https://api-inference.huggingface.co/models/<hostedModel>
  // Headers: Authorization: Bearer <token>, Content-Type: application/json
  // Body: JSON.stringify(payload)
  //
  // The response JSON is: [{ "label": "...", "score": 0.9 }, ...]
  // Parse and return as ScoredLabel[], sorted by score descending.

  throw new Error(
    "Complete the TODO: send a fetch() POST to the HF API and parse the results."
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
  console.log(`Labels   : ${CANDIDATE_LABELS.join(", ")}`);
  console.log();

  const results = useApi
    ? await clipHosted(imagePath, CANDIDATE_LABELS)
    : await clipLocal(imagePath, CANDIDATE_LABELS);

  console.log("CLIP similarity scores (higher = more similar):");
  results.forEach((item) => {
    const bar = "#".repeat(Math.round(item.score * 30));
    console.log(`  ${item.label.padEnd(35)} ${item.score.toFixed(4)}  ${bar}`);
  });

  const winner = results[0];
  console.log(`\nBest match: ${winner?.label ?? "n/a"}`);
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
