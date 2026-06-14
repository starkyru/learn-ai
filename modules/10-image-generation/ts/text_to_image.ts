/**
 * text_to_image.ts — Task 1 🟢: generate an image from a text prompt.
 *
 * What it teaches:
 *   The simplest possible hosted image generation call: prompt → PNG file.
 *   Varying the seed shows that generation is fully deterministic given the
 *   same seed, but explores completely different compositions with different
 *   seeds — all from the same starting distribution N(0,I).
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/10-image-generation/ts/text_to_image.ts
 *
 * Requires: REPLICATE_API_TOKEN in .env  (or set IMAGE_PROVIDER and its key)
 */

import { generateImage, saveImage } from "./image_client.ts";

// Change this to explore what the model can generate.
const PROMPT =
  "A photorealistic red fox sitting in a snowy pine forest at golden hour, " +
  "soft bokeh background, National Geographic style";

// Negative prompt — steer the model away from low-quality features.
const NEGATIVE_PROMPT = "blurry, low quality, cartoon, watermark, text, logo";

// Seeds to generate — same prompt, different noise starting points.
// Same seed + same prompt = identical output every time (reproducibility).
const SEEDS = [42, 1337];

async function main(): Promise<void> {
  console.log(`Prompt: "${PROMPT}"\n`);

  for (const seed of SEEDS) {
    console.log(`Generating with seed=${seed} …`);

    const { imageBytes, provider, model } = await generateImage({
      prompt: PROMPT,
      negativePrompt: NEGATIVE_PROMPT,
      width: 1024,
      height: 1024,
      guidanceScale: 7.5,
      numInferenceSteps: 25,
      seed,
    });

    const path = `output_seed_${seed}.png`;
    saveImage(imageBytes, path);
    console.log(`  Provider: ${provider}  Model: ${model}\n`);
  }

  console.log("Done! Open the PNG files to compare outputs across seeds.");
  console.log(
    "Notice: the fox is in the same setting (same prompt) but the exact",
    "composition, pose, and lighting differ — because the noise starting",
    "point (seed) is different.",
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
