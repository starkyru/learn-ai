/**
 * param_sweep.ts — Task 2 🟡: explore guidance scale, steps, and negative prompts.
 *
 * What it teaches:
 *   Every "knob" on an image request has a concrete effect rooted in the math.
 *   This script sweeps two axes — guidance_scale (columns) and
 *   num_inference_steps (rows) — at a fixed seed, so the only thing that varies
 *   across a cell is the parameter being studied. It records EVERY parameter
 *   plus the seed for every cell in a reproducible sidecar JSON, so any run can
 *   be reconstructed exactly.
 *
 *   Parameters explored:
 *     guidanceScale       — how strongly the denoiser follows the text prompt
 *                           (classifier-free guidance weight, README Concept 5)
 *     numInferenceSteps   — how many denoising steps to run
 *                           (more ≈ more detail, diminishing returns past ~40)
 *   The negativePrompt is held constant; its effect is explained below.
 *
 * How to run (from the repo root):
 *   Hosted (sends ~6 API calls, needs a key):
 *     pnpm tsx modules/10-image-generation/ts/param_sweep.ts
 *   Deterministic offline stub (no key, no network — used by CI/tests):
 *     IMAGE_STUB=1 pnpm tsx modules/10-image-generation/ts/param_sweep.ts
 *
 * Note on negative prompts:
 *   Classifier-free guidance runs the U-Net TWICE per step:
 *     ε_guided = ε_uncond + scale * (ε_cond - ε_uncond)
 *   The negative prompt is encoded by CLIP and used as ε_uncond, steering the
 *   model AWAY from those features. Common value:
 *   "blurry, low quality, watermark, deformed".
 */

import { writeFileSync } from "node:fs";

import { generateImage, saveImage, type GenerateOptions } from "./image_client.ts";
import {
  encodePng,
  hashBytes,
  isOffline,
  solidGridPng,
  solidPixels,
  tintFor,
  type RGB,
} from "./stub_image.ts";

// ---------------------------------------------------------------------------
// Sweep configuration — change these to explore
// ---------------------------------------------------------------------------

export interface SweepConfig {
  prompt: string;
  negativePrompt: string;
  /** guidance_scale values — one column each. */
  guidanceScales: number[];
  /** num_inference_steps values — one row each. */
  stepsList: number[];
  /** Fixed seed so every cell shares the same noise starting point. */
  seed: number;
  width: number;
  height: number;
}

export const CONFIG: SweepConfig = {
  prompt:
    "A majestic snow leopard on a mountain ridge at dusk, cinematic lighting, " +
    "ultra-detailed fur, professional wildlife photography",
  // Try: ""  vs  "blurry, low quality, watermark, cartoon, deformed"
  negativePrompt: "blurry, low quality, watermark, cartoon, deformed",
  guidanceScales: [3.0, 7.5, 15.0], // columns
  stepsList: [10, 30], // rows
  seed: 42,
  width: 512, // smaller for speed in a sweep
  height: 512,
};

const GRID_OUTPUT = "sweep_grid.png";
const METADATA_OUTPUT = "sweep_metadata.json";

// ---------------------------------------------------------------------------
// Pure sweep model (deterministic — this is what the tests drive)
// ---------------------------------------------------------------------------

export interface SweepCell {
  row: number; // index into stepsList
  col: number; // index into guidanceScales
  steps: number;
  guidanceScale: number;
  seed: number;
  prompt: string;
  negativePrompt: string;
  width: number;
  height: number;
}

/**
 * Build the row-major grid of cells. Rows are step counts, columns are
 * guidance scales — the same ordering the Python `product(STEPS, GUIDANCE)`
 * uses. Every cell carries the full parameter set plus the shared seed.
 */
export function buildSweepCells(config: SweepConfig): SweepCell[] {
  const cells: SweepCell[] = [];
  config.stepsList.forEach((steps, row) => {
    config.guidanceScales.forEach((guidanceScale, col) => {
      cells.push({
        row,
        col,
        steps,
        guidanceScale,
        seed: config.seed,
        prompt: config.prompt,
        negativePrompt: config.negativePrompt,
        width: config.width,
        height: config.height,
      });
    });
  });
  return cells;
}

/** Map a cell to the provider-agnostic generate options. */
export function cellToOptions(cell: SweepCell): GenerateOptions {
  return {
    prompt: cell.prompt,
    negativePrompt: cell.negativePrompt,
    width: cell.width,
    height: cell.height,
    guidanceScale: cell.guidanceScale,
    numInferenceSteps: cell.steps,
    seed: cell.seed,
  };
}

/** Canonical identity string for a cell — the fingerprint the stub renders. */
export function cellKey(cell: SweepCell): string {
  return [
    cell.prompt,
    cell.negativePrompt,
    `${cell.width}x${cell.height}`,
    `cfg=${cell.guidanceScale}`,
    `steps=${cell.steps}`,
    `seed=${cell.seed}`,
  ].join("|");
}

/** Deterministic offline swatch colour for a cell. */
export function cellTint(cell: SweepCell): RGB {
  return tintFor(cellKey(cell));
}

/** Output filename for a cell's individual image. */
export function cellFilename(cell: SweepCell): string {
  return `sweep_cell_r${cell.row}_c${cell.col}.png`;
}

// ---------------------------------------------------------------------------
// Reproducible metadata
// ---------------------------------------------------------------------------

export interface SweepCellRecord {
  row: number;
  col: number;
  steps: number;
  guidanceScale: number;
  seed: number;
  output: string;
  provider: string;
  model: string;
  digest: string;
  tint: RGB | null;
}

export interface SweepMetadata {
  prompt: string;
  negativePrompt: string;
  seed: number;
  guidanceScales: number[];
  stepsList: number[];
  cols: number;
  rows: number;
  offline: boolean;
  grid: string | null;
  cells: SweepCellRecord[];
}

/**
 * Run the whole sweep deterministically offline. Returns the reproducible
 * metadata, the per-cell PNG bytes, and a composited grid PNG. No filesystem
 * or network access — the tests assert directly on the return value.
 */
export function buildSweepStub(config: SweepConfig): {
  metadata: SweepMetadata;
  cellImages: Uint8Array[];
  gridImage: Uint8Array;
} {
  const cells = buildSweepCells(config);
  const cellImages: Uint8Array[] = [];
  const tints: RGB[] = [];
  const records: SweepCellRecord[] = [];

  for (const cell of cells) {
    const tint = cellTint(cell);
    const pixels = solidPixels(cell.width, cell.height, tint);
    tints.push(tint);
    cellImages.push(encodePng(cell.width, cell.height, pixels));
    records.push({
      row: cell.row,
      col: cell.col,
      steps: cell.steps,
      guidanceScale: cell.guidanceScale,
      seed: cell.seed,
      output: cellFilename(cell),
      provider: "stub",
      model: "stub-solid-v1",
      digest: hashBytes(pixels),
      tint,
    });
  }

  const gridImage = solidGridPng(
    tints,
    config.guidanceScales.length,
    config.stepsList.length,
    config.width,
    config.height,
  );

  const metadata: SweepMetadata = {
    prompt: config.prompt,
    negativePrompt: config.negativePrompt,
    seed: config.seed,
    guidanceScales: config.guidanceScales,
    stepsList: config.stepsList,
    cols: config.guidanceScales.length,
    rows: config.stepsList.length,
    offline: true,
    grid: GRID_OUTPUT,
    cells: records,
  };

  return { metadata, cellImages, gridImage };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function runOffline(config: SweepConfig): Promise<void> {
  console.log("Offline stub mode (IMAGE_STUB/OFFLINE_SMOKE) — no API calls.\n");
  const { metadata, cellImages, gridImage } = buildSweepStub(config);

  metadata.cells.forEach((record, idx) => {
    saveImage(cellImages[idx], record.output);
  });
  saveImage(gridImage, GRID_OUTPUT);
  writeFileSync(METADATA_OUTPUT, JSON.stringify(metadata, null, 2));
  console.log(`Reproducible metadata → ${METADATA_OUTPUT}`);
}

async function runHosted(config: SweepConfig): Promise<void> {
  const cells = buildSweepCells(config);
  const records: SweepCellRecord[] = [];

  for (const cell of cells) {
    console.log(`  Generating steps=${cell.steps}, cfg=${cell.guidanceScale} …`);
    const result = await generateImage(cellToOptions(cell));
    const output = cellFilename(cell);
    saveImage(result.imageBytes, output);
    records.push({
      row: cell.row,
      col: cell.col,
      steps: cell.steps,
      guidanceScale: cell.guidanceScale,
      seed: cell.seed,
      output,
      provider: result.provider,
      model: result.model,
      digest: hashBytes(result.imageBytes),
      tint: null,
    });
  }

  const metadata: SweepMetadata = {
    prompt: config.prompt,
    negativePrompt: config.negativePrompt,
    seed: config.seed,
    guidanceScales: config.guidanceScales,
    stepsList: config.stepsList,
    cols: config.guidanceScales.length,
    rows: config.stepsList.length,
    offline: false,
    grid: null, // compositing hosted PNGs needs an image library; view cells individually
    cells: records,
  };
  writeFileSync(METADATA_OUTPUT, JSON.stringify(metadata, null, 2));
  console.log(`Reproducible metadata → ${METADATA_OUTPUT}`);
  console.log(
    "(Install an image library to composite the individual cells into a grid.)",
  );
}

async function main(): Promise<void> {
  console.log(`Prompt: "${CONFIG.prompt}"`);
  console.log(`Negative: ${JSON.stringify(CONFIG.negativePrompt)}`);
  console.log(
    `Grid: ${CONFIG.guidanceScales.length} guidance scales × ` +
      `${CONFIG.stepsList.length} step counts\n`,
  );

  if (isOffline()) {
    await runOffline(CONFIG);
  } else {
    await runHosted(CONFIG);
  }

  console.log("\nWhat to look for:");
  console.log(
    "  CFG  3.0 (left col) : loosely follows the prompt; painterly, creative.",
  );
  console.log("  CFG  7.5 (mid col)  : balanced — the default for most use cases.");
  console.log(
    "  CFG 15.0 (right col): strong adherence; may oversaturate/over-sharpen.",
  );
  console.log("  low steps (top row) : faster but coarser; some coherence issues.");
  console.log("  high steps (bot row): more detail; diminishing returns above ~40.");
}

// Run only when invoked directly (so the test file can import without executing).
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
