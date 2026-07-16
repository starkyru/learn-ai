/**
 * img2img.ts — Task 3 🟡: image-to-image and inpainting via a hosted API.
 *
 * What it teaches:
 *   Text-to-image always starts from pure Gaussian noise (x_T). img2img starts
 *   from a PARTIALLY noised version of a real image, so the denoiser can build
 *   on the existing composition while still following the prompt. The
 *   `strength` parameter controls how noisy the start is:
 *
 *     strength = 1.0  → fully noised   ≈ text-to-image (ignores the input)
 *     strength = 0.5  → half-noised    → keeps rough layout, changes details
 *     strength = 0.2  → lightly noised  → very close to the original
 *
 *   Inpainting is img2img with a binary mask: the masked region is regenerated
 *   from the prompt; the unmasked region is preserved. This exercise mirrors
 *   that behaviour offline — the stub's output tint is a blend of the input's
 *   fingerprint and the prompt's fingerprint weighted by `strength`, and the
 *   inpaint stub keeps the unmasked band's colour independent of the prompt.
 *
 * How to run (from the repo root):
 *   Hosted (downloads a sample image, sends 2 API calls, needs a key):
 *     pnpm tsx modules/10-image-generation/ts/img2img.ts
 *   Deterministic offline stub (no key, no network — used by CI/tests):
 *     IMAGE_STUB=1 pnpm tsx modules/10-image-generation/ts/img2img.ts
 *
 * Requires (hosted path): REPLICATE_API_TOKEN in .env.
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";

import { saveImage } from "./image_client.ts";
import {
  bandedPng,
  decodePng,
  hashBytes,
  isOffline,
  lerpRgb,
  rgbFromHash,
  solidPixels,
  solidPng,
  tintFor,
  encodePng,
  fnv1a,
  type RGB,
} from "./stub_image.ts";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

// A freely licensed landscape photo (Unsplash — CC0).
const SAMPLE_IMAGE_URL =
  "https://images.unsplash.com/photo-1506905925346-21bda4d32df4" +
  "?w=512&h=512&fit=crop&auto=format";
const SAMPLE_IMAGE_PATH = "sample_input.png";

const IMG2IMG_PROMPT =
  "The same mountain landscape in the style of a Japanese woodblock print, " +
  "ukiyo-e, bold outlines, muted ink colours";
const IMG2IMG_STRENGTH = 0.65; // 0 = keep everything; 1 = full text-to-image
const IMG2IMG_OUTPUT = "img2img_output.png";

const INPAINT_PROMPT = "A dramatic stormy sky with lightning bolts, photorealistic";
const INPAINT_OUTPUT = "inpaint_output.png";
const MASK_OUTPUT = "inpaint_mask.png";
const MASK_FRACTION = 0.4; // top 40% of the image = the sky

const IMAGE_SIZE = 512;
const SEED = 42;
const METADATA_OUTPUT = "edit_metadata.json";

// ---------------------------------------------------------------------------
// Image utilities
// ---------------------------------------------------------------------------

/** Encode image bytes as a base64 data URI (for APIs that require it). */
export function toDataUri(bytes: Uint8Array, mime = "image/png"): string {
  return `data:${mime};base64,${Buffer.from(bytes).toString("base64")}`;
}

/**
 * White-on-black mask covering the top `fraction` of the image.
 * White (255) = regenerate; black (0) = preserve. Emitted as an RGB PNG.
 */
export function makeTopMaskPng(
  width = IMAGE_SIZE,
  height = IMAGE_SIZE,
  fraction = MASK_FRACTION,
): Uint8Array {
  const maskedRows = maskedRowCount(height, fraction);
  return bandedPng(width, height, maskedRows, [255, 255, 255], [0, 0, 0]);
}

/** Number of top rows the mask covers for a given fraction. */
export function maskedRowCount(height: number, fraction: number): number {
  return Math.round(height * Math.max(0, Math.min(1, fraction)));
}

/**
 * Deterministic offline stand-in for the sample photo — a solid swatch whose
 * colour is fixed, so the stub pipeline needs no download and no network.
 */
export function syntheticInput(width = IMAGE_SIZE, height = IMAGE_SIZE): Uint8Array {
  return solidPng(width, height, tintFor("sample_input:mountain-landscape"));
}

/** Download the sample image (hosted path only), caching it to disk. */
async function downloadSampleImage(): Promise<Uint8Array> {
  if (existsSync(SAMPLE_IMAGE_PATH)) {
    console.log(`Using cached ${SAMPLE_IMAGE_PATH}`);
    return new Uint8Array(readFileSync(SAMPLE_IMAGE_PATH));
  }
  console.log("Downloading sample image from Unsplash …");
  const res = await fetch(SAMPLE_IMAGE_URL, { redirect: "follow" });
  if (!res.ok) throw new Error(`Sample download failed: ${res.status}`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  writeFileSync(SAMPLE_IMAGE_PATH, bytes);
  console.log(`  Saved → ${SAMPLE_IMAGE_PATH}`);
  return bytes;
}

// ---------------------------------------------------------------------------
// Deterministic offline stubs (this is what the tests drive)
// ---------------------------------------------------------------------------

export interface Img2ImgOptions {
  prompt: string;
  strength: number;
  seed: number;
}

export interface InpaintOptions {
  prompt: string;
  seed: number;
  maskFraction: number;
}

export interface StubImg2ImgResult {
  imageBytes: Uint8Array;
  provider: "stub";
  model: string;
  digest: string;
  inputTint: RGB;
  promptTint: RGB;
  tint: RGB;
}

export interface StubInpaintResult {
  imageBytes: Uint8Array;
  provider: "stub";
  model: string;
  digest: string;
  width: number;
  height: number;
  maskedRows: number;
  regeneratedTint: RGB;
  /** The input's ACTUAL colour sampled from the preserved (unmasked) band. */
  preservedTint: RGB;
}

/**
 * Offline img2img: the output tint interpolates from the input's fingerprint
 * (strength → 0) toward the prompt's fingerprint (strength → 1), so `strength`
 * has the same qualitative meaning as the real knob.
 */
export function img2imgStub(
  inputBytes: Uint8Array,
  opts: Img2ImgOptions,
  size = IMAGE_SIZE,
): StubImg2ImgResult {
  const inputDigest = hashBytes(inputBytes);
  const inputTint = rgbFromHash(fnv1a(`img2img-input:${inputDigest}`));
  const promptTint = rgbFromHash(
    fnv1a(`img2img-prompt:${opts.prompt}:seed=${opts.seed}`),
  );
  const tint = lerpRgb(inputTint, promptTint, opts.strength);
  const pixels = solidPixels(size, size, tint);
  return {
    imageBytes: encodePng(size, size, pixels),
    provider: "stub",
    model: "stub-img2img-v1",
    digest: hashBytes(pixels),
    inputTint,
    promptTint,
    tint,
  };
}

/**
 * Offline inpainting. The defining property of inpainting is that the UNMASKED
 * region is PRESERVED. So we decode the input, copy its pixels verbatim, and
 * overwrite ONLY the top masked band with a colour regenerated from the
 * prompt+seed. The unmasked (bottom) band is therefore byte-identical to the
 * input; the masked band changes with the prompt/seed.
 */
export function inpaintStub(
  inputBytes: Uint8Array,
  opts: InpaintOptions,
): StubInpaintResult {
  const { width, height, pixels } = decodePng(inputBytes);
  const regeneratedTint = rgbFromHash(
    fnv1a(`inpaint-regen:${opts.prompt}:seed=${opts.seed}`),
  );
  const maskedRows = maskedRowCount(height, opts.maskFraction);

  const out = new Uint8Array(pixels); // start from a copy → unmasked band preserved
  const [r, g, b] = regeneratedTint;
  for (let y = 0; y < maskedRows; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 3;
      out[idx] = r;
      out[idx + 1] = g;
      out[idx + 2] = b;
    }
  }

  // Sample the input's real colour from the first preserved row (falls back to
  // the last row when the whole image is masked).
  const sampleRow = maskedRows < height ? maskedRows : height - 1;
  const si = sampleRow * width * 3;
  const preservedTint: RGB = [pixels[si], pixels[si + 1], pixels[si + 2]];

  return {
    imageBytes: encodePng(width, height, out),
    provider: "stub",
    // Digest over the raw output pixels — same representation as img2imgStub.
    digest: hashBytes(out),
    model: "stub-inpaint-v1",
    width,
    height,
    maskedRows,
    regeneratedTint,
    preservedTint,
  };
}

// ---------------------------------------------------------------------------
// Hosted providers (Replicate) — the network boundary, kept isolated
// ---------------------------------------------------------------------------

const REPLICATE_IMG2IMG_VERSION =
  "7762fd07cf82c948538e41f63f77d685e02b063e37e496e96eefd46c929f9bdc";
const REPLICATE_INPAINT_VERSION =
  "ca1f5e306e5721e19c473e0d094e6603f0456fe759c10715fcd6c1b79242d4a5";

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** POST a Replicate prediction, poll to completion, and return the PNG bytes. */
async function runReplicatePrediction(
  version: string,
  input: Record<string, unknown>,
): Promise<Uint8Array> {
  const token = process.env["REPLICATE_API_TOKEN"];
  if (!token) throw new Error("Missing REPLICATE_API_TOKEN in .env");

  const createRes = await fetch("https://api.replicate.com/v1/predictions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ version, input }),
  });
  if (!createRes.ok) {
    throw new Error(
      `Replicate create failed: ${createRes.status} ${await createRes.text()}`,
    );
  }
  const prediction = (await createRes.json()) as { urls: { get: string } };
  const pollUrl = prediction.urls.get;

  for (let attempt = 0; attempt < 60; attempt++) {
    await delay(2000);
    const pollRes = await fetch(pollUrl, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = (await pollRes.json()) as {
      status: string;
      output?: string[];
      error?: string;
    };
    if (data.status === "succeeded") {
      const url = data.output?.[0];
      if (!url) throw new Error("Replicate succeeded with no output");
      const imgRes = await fetch(url);
      return new Uint8Array(await imgRes.arrayBuffer());
    }
    if (data.status === "failed") {
      throw new Error(`Replicate prediction failed: ${data.error ?? "unknown"}`);
    }
  }
  throw new Error("Replicate prediction timed out after 120 s");
}

/** img2img via Replicate SDXL img2img. */
export async function img2imgHosted(
  inputBytes: Uint8Array,
  opts: Img2ImgOptions,
): Promise<Uint8Array> {
  return runReplicatePrediction(REPLICATE_IMG2IMG_VERSION, {
    prompt: opts.prompt,
    image: toDataUri(inputBytes),
    prompt_strength: opts.strength, // Replicate names this "prompt_strength"
    num_inference_steps: 30,
    guidance_scale: 7.5,
    seed: opts.seed,
  });
}

/** Inpainting via Replicate SDXL inpainting. */
export async function inpaintHosted(
  inputBytes: Uint8Array,
  maskBytes: Uint8Array,
  opts: { prompt: string; seed: number },
): Promise<Uint8Array> {
  return runReplicatePrediction(REPLICATE_INPAINT_VERSION, {
    prompt: opts.prompt,
    image: toDataUri(inputBytes),
    mask: toDataUri(maskBytes),
    num_inference_steps: 30,
    guidance_scale: 8.0,
    seed: opts.seed,
  });
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function runOffline(inputBytes: Uint8Array): Promise<void> {
  console.log(
    "Offline stub mode (IMAGE_STUB/OFFLINE_SMOKE) — no download, no API calls.\n",
  );

  console.log("Running img2img …");
  console.log(`  Strength : ${IMG2IMG_STRENGTH}  (0=keep original, 1=full text2img)`);
  const img = img2imgStub(inputBytes, {
    prompt: IMG2IMG_PROMPT,
    strength: IMG2IMG_STRENGTH,
    seed: SEED,
  });
  saveImage(img.imageBytes, IMG2IMG_OUTPUT);

  console.log("\nCreating inpaint mask (top 40% = sky) …");
  saveImage(makeTopMaskPng(), MASK_OUTPUT);
  console.log("Running inpainting …");
  const inpaint = inpaintStub(inputBytes, {
    prompt: INPAINT_PROMPT,
    seed: SEED,
    maskFraction: MASK_FRACTION,
  });
  saveImage(inpaint.imageBytes, INPAINT_OUTPUT);

  const metadata = {
    offline: true,
    seed: SEED,
    img2img: {
      prompt: IMG2IMG_PROMPT,
      strength: IMG2IMG_STRENGTH,
      output: IMG2IMG_OUTPUT,
      digest: img.digest,
      inputTint: img.inputTint,
      promptTint: img.promptTint,
      tint: img.tint,
    },
    inpaint: {
      prompt: INPAINT_PROMPT,
      maskFraction: MASK_FRACTION,
      maskedRows: inpaint.maskedRows,
      output: INPAINT_OUTPUT,
      mask: MASK_OUTPUT,
      digest: inpaint.digest,
      preservedTint: inpaint.preservedTint,
      regeneratedTint: inpaint.regeneratedTint,
    },
  };
  writeFileSync(METADATA_OUTPUT, JSON.stringify(metadata, null, 2));
  console.log(`\nReproducible metadata → ${METADATA_OUTPUT}`);
}

async function runHosted(inputBytes: Uint8Array): Promise<void> {
  console.log("\nRunning img2img …");
  console.log(`  Prompt   : ${IMG2IMG_PROMPT}`);
  console.log(`  Strength : ${IMG2IMG_STRENGTH}  (0=keep original, 1=full text2img)`);
  const img2imgBytes = await img2imgHosted(inputBytes, {
    prompt: IMG2IMG_PROMPT,
    strength: IMG2IMG_STRENGTH,
    seed: SEED,
  });
  saveImage(img2imgBytes, IMG2IMG_OUTPUT);

  console.log("\nCreating inpaint mask (top 40% = sky) …");
  const maskBytes = makeTopMaskPng();
  saveImage(maskBytes, MASK_OUTPUT);
  console.log("Running inpainting …");
  console.log(`  Prompt : ${INPAINT_PROMPT}`);
  const inpaintBytes = await inpaintHosted(inputBytes, maskBytes, {
    prompt: INPAINT_PROMPT,
    seed: SEED,
  });
  saveImage(inpaintBytes, INPAINT_OUTPUT);
}

async function main(): Promise<void> {
  const inputBytes = isOffline() ? syntheticInput() : await downloadSampleImage();
  if (isOffline()) {
    saveImage(inputBytes, SAMPLE_IMAGE_PATH);
    await runOffline(inputBytes);
  } else {
    await runHosted(inputBytes);
  }

  console.log("\nCompare:");
  console.log("  sample_input.png   — original / stub input");
  console.log("  img2img_output.png — same composition, restyled");
  console.log("  inpaint_output.png — bottom band preserved, top band regenerated");
  console.log("\nKey insight: img2img starts from x_t (partially noised), not x_T");
  console.log("(pure noise), so the input's structure is preserved. Strength sets t.");
}

// Run only when invoked directly (so the test file can import without executing).
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
