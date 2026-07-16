/**
 * image_client.ts — hosted text-to-image client for module 10.
 *
 * What it teaches:
 *   A single, swappable async function `generateImage()` that hides the
 *   provider-specific HTTP details, exactly like llm-core hides chat provider
 *   differences. Change IMAGE_PROVIDER (or the env var) and the rest of your
 *   code stays identical.
 *
 * Supported providers (set IMAGE_PROVIDER env var or the constant below):
 *   "replicate"  — REPLICATE_API_TOKEN   (default; poll-based, ~$0.004/image)
 *   "hf"         — HF_TOKEN             (HuggingFace Inference API, free tier)
 *   "stability"  — STABILITY_API_KEY    (Stability AI REST)
 *   "nvidia"     — NVIDIA_API_KEY       (NVIDIA NIM image endpoint)
 */

import { readFileSync, writeFileSync } from "node:fs";
import { env } from "node:process";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GenerateOptions {
  /** Text description of the image to create. */
  prompt: string;
  /** Optional negative prompt — features to steer away from. */
  negativePrompt?: string;
  /** Image width in pixels (must be a multiple of 8). Default 1024. */
  width?: number;
  /** Image height in pixels (must be a multiple of 8). Default 1024. */
  height?: number;
  /** Classifier-free guidance scale. Higher = more prompt adherence. Default 7. */
  guidanceScale?: number;
  /** Number of denoising steps. More = higher quality (diminishing returns >40). Default 25. */
  numInferenceSteps?: number;
  /** RNG seed for reproducibility. Same seed + same prompt = same image. */
  seed?: number;
}

export interface GenerateResult {
  /** Raw PNG bytes. */
  imageBytes: Uint8Array;
  /** Which provider was used. */
  provider: string;
  /** Model identifier used. */
  model: string;
}

// ---------------------------------------------------------------------------
// Provider implementations
// ---------------------------------------------------------------------------

/**
 * Replicate text-to-image via the REST polling API.
 * Docs: https://replicate.com/docs/reference/http
 * Model: stability-ai/sdxl (SDXL 1.0)
 */
async function generateReplicate(opts: GenerateOptions): Promise<GenerateResult> {
  const token = env["REPLICATE_API_TOKEN"];
  if (!token) throw new Error("Missing REPLICATE_API_TOKEN in .env");

  const model = "stability-ai/sdxl";
  const version = "39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b";

  // 1. Create a prediction
  const createRes = await fetch("https://api.replicate.com/v1/predictions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      version,
      input: {
        prompt: opts.prompt,
        negative_prompt: opts.negativePrompt ?? "",
        width: opts.width ?? 1024,
        height: opts.height ?? 1024,
        guidance_scale: opts.guidanceScale ?? 7,
        num_inference_steps: opts.numInferenceSteps ?? 25,
        seed: opts.seed,
      },
    }),
  });

  if (!createRes.ok) {
    const body = await createRes.text();
    throw new Error(`Replicate create failed: ${createRes.status} ${body}`);
  }

  const prediction = (await createRes.json()) as { id: string; urls: { get: string } };
  const pollUrl = prediction.urls.get;

  // 2. Poll until done (Replicate is asynchronous)
  let imageUrl: string | undefined;
  for (let attempt = 0; attempt < 60; attempt++) {
    await delay(2000);
    const pollRes = await fetch(pollUrl, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const status = (await pollRes.json()) as {
      status: string;
      output?: string[];
      error?: string;
    };

    if (status.status === "succeeded") {
      imageUrl = status.output?.[0];
      break;
    }
    if (status.status === "failed") {
      throw new Error(`Replicate prediction failed: ${status.error ?? "unknown"}`);
    }
  }

  if (!imageUrl) throw new Error("Replicate prediction timed out after 120 s");

  // 3. Download the image bytes
  const imgRes = await fetch(imageUrl);
  const imageBytes = new Uint8Array(await imgRes.arrayBuffer());
  return { imageBytes, provider: "replicate", model };
}

/**
 * HuggingFace Inference API text-to-image.
 * Docs: https://huggingface.co/docs/api-inference/tasks/text-to-image
 * Model: stabilityai/stable-diffusion-xl-base-1.0
 */
async function generateHuggingFace(opts: GenerateOptions): Promise<GenerateResult> {
  const token = env["HF_TOKEN"];
  if (!token) throw new Error("Missing HF_TOKEN in .env");

  const model = "stabilityai/stable-diffusion-xl-base-1.0";
  const url = `https://api-inference.huggingface.co/models/${model}`;

  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      inputs: opts.prompt,
      parameters: {
        negative_prompt: opts.negativePrompt,
        width: opts.width ?? 1024,
        height: opts.height ?? 1024,
        guidance_scale: opts.guidanceScale ?? 7,
        num_inference_steps: opts.numInferenceSteps ?? 25,
        seed: opts.seed,
      },
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HuggingFace request failed: ${res.status} ${body}`);
  }

  const imageBytes = new Uint8Array(await res.arrayBuffer());
  return { imageBytes, provider: "huggingface", model };
}

/**
 * Stability AI text-to-image REST API.
 * Docs: https://platform.stability.ai/docs/api-reference#tag/Generate
 * Model: stable-image/generate/core (SDXL-based)
 */
async function generateStability(opts: GenerateOptions): Promise<GenerateResult> {
  const apiKey = env["STABILITY_API_KEY"];
  if (!apiKey) throw new Error("Missing STABILITY_API_KEY in .env");

  const model = "stability-ai/stable-image-core";
  const formData = new FormData();
  formData.append("prompt", opts.prompt);
  if (opts.negativePrompt) formData.append("negative_prompt", opts.negativePrompt);
  formData.append("aspect_ratio", "1:1");
  if (opts.seed !== undefined) formData.append("seed", String(opts.seed));
  formData.append("output_format", "png");

  const res = await fetch(
    "https://api.stability.ai/v2beta/stable-image/generate/core",
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: "image/*",
      },
      body: formData,
    },
  );

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Stability AI request failed: ${res.status} ${body}`);
  }

  const imageBytes = new Uint8Array(await res.arrayBuffer());
  return { imageBytes, provider: "stability", model };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Which provider to use. Override with the IMAGE_PROVIDER env var. */
const DEFAULT_PROVIDER = "replicate";

/**
 * Generate an image from a text prompt using the configured hosted provider.
 *
 * @example
 * const { imageBytes } = await generateImage({ prompt: "a red fox in a snowy forest" });
 * writeFileSync("fox.png", imageBytes);
 */
export async function generateImage(opts: GenerateOptions): Promise<GenerateResult> {
  const provider = env["IMAGE_PROVIDER"] ?? DEFAULT_PROVIDER;
  switch (provider) {
    case "replicate":
      return generateReplicate(opts);
    case "hf":
    case "huggingface":
      return generateHuggingFace(opts);
    case "stability":
      return generateStability(opts);
    default:
      throw new Error(
        `Unknown IMAGE_PROVIDER="${provider}". Choose: replicate | hf | stability`,
      );
  }
}

/**
 * Save image bytes to a PNG file and return the path.
 */
export function saveImage(imageBytes: Uint8Array, path: string): void {
  writeFileSync(path, imageBytes);
  console.log(`Saved → ${path}  (${(imageBytes.byteLength / 1024).toFixed(1)} KB)`);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
