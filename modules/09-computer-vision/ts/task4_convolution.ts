/**
 * task4_convolution.ts — 2-D convolution from scratch.  🔴
 *
 * What it teaches:
 *   Convolution is the fundamental operation in every CNN layer. A small matrix
 *   (the kernel or filter) slides over an image, computing a dot product at
 *   each position. The output — a feature map — highlights wherever the kernel's
 *   pattern matches the image.
 *
 *   Kernels you'll apply here:
 *     - Sobel horizontal: lights up horizontal edges (brightness changes top→bottom)
 *     - Sobel vertical:   lights up vertical edges   (brightness changes left→right)
 *     - Box blur:         averages each pixel with its 3×3 neighbourhood
 *
 *   In a trained CNN these kernels are *learned* from data, but they all work
 *   the same way: the conv inner loop you implement here is exactly what
 *   nn.Conv2d (PyTorch) or tf.keras.layers.Conv2D does under the hood (just
 *   massively parallelised on GPU).
 *
 *   We use raw TypedArrays (Float32Array) instead of a library so the
 *   computation is completely visible. No numpy, no tensor library.
 *
 * How to run (from the repo root):
 *   pnpm tsx modules/09-computer-vision/ts/task4_convolution.ts
 *
 *   Output: writes grayscale PGM files to assets/ so you can view them.
 *   (PGM is plain-text, viewable in any image viewer or by running:
 *    `open assets/edge_h.pgm` on macOS)
 *
 * Acceptance:
 *   - conv2d() passes the identity-kernel sanity check.
 *   - PGM files are written for each kernel.
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import https from "node:https";
import fs from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(__dirname, "..", "assets");
const SAMPLE_IMAGE = path.join(ASSETS_DIR, "cat.jpg");

// ---------------------------------------------------------------------------
// Kernels (stored as flat row-major Float32Array + size)
// ---------------------------------------------------------------------------

interface Kernel {
  data: Float32Array;
  size: number; // kernels are size×size
}

function makeKernel(rows: number[][]): Kernel {
  const size = rows.length;
  const data = new Float32Array(size * size);
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      data[r * size + c] = rows[r][c];
    }
  }
  return { data, size };
}

const EDGE_HORIZONTAL = makeKernel([
  [-1, -2, -1],
  [ 0,  0,  0],
  [ 1,  2,  1],
]);

const EDGE_VERTICAL = makeKernel([
  [-1, 0, 1],
  [-2, 0, 2],
  [-1, 0, 1],
]);

const BLUR = makeKernel([
  [1/9, 1/9, 1/9],
  [1/9, 1/9, 1/9],
  [1/9, 1/9, 1/9],
]);

// ---------------------------------------------------------------------------
// Image representation — grayscale, row-major Float32Array
// ---------------------------------------------------------------------------

interface GrayImage {
  data: Float32Array;
  width: number;
  height: number;
}

// ---------------------------------------------------------------------------
// Task: implement 2-D convolution
// ---------------------------------------------------------------------------

/**
 * Apply a 2-D convolution kernel to a single-channel grayscale image.
 *
 * @param image  GrayImage with pixel values in [0, 255].
 * @param kernel Kernel to apply (must be odd-sized square).
 * @returns      GrayImage — the feature map, same spatial size as input.
 *
 * Algorithm:
 *   1. Allocate output Float32Array of size height × width.
 *   2. Compute kHalf = (kernel.size - 1) / 2 — the padding radius.
 *   3. For each output pixel (row, col):
 *      a. Accumulate the dot product of the kernel with the kernel.size×kernel.size
 *         patch centred at (row, col) in the input.
 *      b. For positions that fall outside the image boundary, treat them as 0
 *         (zero-padding). Check bounds before reading.
 *      c. Write the accumulated sum to output[row * width + col].
 *
 * Correlation vs convolution:
 *   We implement correlation (no kernel flip) — this is what torch.nn.Conv2d
 *   does too (the flip is absorbed into learned weights).
 */
function conv2d(image: GrayImage, kernel: Kernel): GrayImage {
  const { width, height } = image;
  const K = kernel.size;
  const kHalf = (K - 1) / 2;
  const output = new Float32Array(width * height);

  // TODO (exercise): implement the convolution loop (4 nested loops).
  //   - Outer two loops walk every output pixel (row, col).
  //   - Inner two loops walk the K×K kernel (kr, kc). Map each kernel cell to an
  //     input coordinate: `ir = row - kHalf + kr`, `ic = col - kHalf + kc` (this
  //     centres the kernel on the current pixel).
  //   - Guard the input read with a bounds check — if (ir, ic) falls outside the
  //     image, skip it, which treats it as 0 (zero-padding).
  //   - Accumulate `image.data[ir * width + ic] * kernel.data[kr * K + kc]` into a
  //     running `sum`, then store it at `output[row * width + col]`.
  //   - Remember both `image.data` and `output` are flat row-major arrays: index
  //     row r, col c as `r * width + c`.

  throw new Error(
    "Implement the convolution loop. " +
    "See the TODO hints above, then remove this throw."
  );

  return { data: output, width, height };
}

// ---------------------------------------------------------------------------
// Minimal JPEG decoder (via canvas-like approach using Node built-ins)
// We convert JPEG → PGM via a tiny manual parse — not production-grade.
// For a simpler approach: use `@huggingface/transformers` RawImage instead.
// ---------------------------------------------------------------------------

/**
 * Load a JPEG file and decode it to grayscale using transformers.js RawImage.
 * Falls back to a synthetic gradient image if loading fails.
 */
async function loadGrayscale(imagePath: string): Promise<GrayImage> {
  try {
    // transformers.js ships a RawImage utility that handles JPEG/PNG → RGB.
    const { RawImage } = await import("@huggingface/transformers") as any;
    const img = await RawImage.fromURL(`file://${imagePath}`);
    // Convert RGB to grayscale: Y = 0.299R + 0.587G + 0.114B
    const W = img.width as number;
    const H = img.height as number;
    const rgb = img.data as Uint8ClampedArray;
    const gray = new Float32Array(W * H);
    for (let i = 0; i < W * H; i++) {
      gray[i] = 0.299 * rgb[i * 3] + 0.587 * rgb[i * 3 + 1] + 0.114 * rgb[i * 3 + 2];
    }
    console.log(`Loaded   : ${imagePath} → ${W}×${H} grayscale`);
    return { data: gray, width: W, height: H };
  } catch {
    // Fallback: 64×64 synthetic gradient image.
    console.warn("Could not load JPEG — using a synthetic 64×64 gradient image.");
    const W = 64, H = 64;
    const data = new Float32Array(W * H);
    for (let r = 0; r < H; r++) {
      for (let c = 0; c < W; c++) {
        // Diagonal gradient with a hard edge at r === H/2
        data[r * W + c] = r < H / 2 ? (c / W) * 255 : 255 - (c / W) * 255;
      }
    }
    return { data, width: W, height: H };
  }
}

// ---------------------------------------------------------------------------
// Save as PGM (Portable GrayMap) — viewable in any image viewer
// ---------------------------------------------------------------------------

function saveAsPGM(image: GrayImage, filePath: string): void {
  const { data, width, height } = image;
  // Normalise to [0, 255]
  let max = 0;
  for (const v of data) if (Math.abs(v) > max) max = Math.abs(v);
  const scale = max > 0 ? 255 / max : 1;

  const pixels = new Uint8Array(width * height);
  for (let i = 0; i < pixels.length; i++) {
    pixels[i] = Math.min(255, Math.round(Math.abs(data[i]) * scale));
  }

  // PGM header + binary pixel data
  const header = `P5\n${width} ${height}\n255\n`;
  const buf = Buffer.concat([Buffer.from(header, "ascii"), Buffer.from(pixels)]);
  writeFileSync(filePath, buf);
  console.log(`Saved    : ${filePath}`);
}

// ---------------------------------------------------------------------------
// Sanity check
// ---------------------------------------------------------------------------

function sanityCheck(): void {
  // Identity kernel: convolution with it should return the image unchanged.
  const identity = makeKernel([[0, 0, 0], [0, 1, 0], [0, 0, 0]]);
  const img: GrayImage = {
    data: new Float32Array([1, 2, 3, 4, 5, 6, 7, 8, 9]),
    width: 3,
    height: 3,
  };
  const result = conv2d(img, identity);
  const ok = img.data.every((v, i) => Math.abs(v - result.data[i]) < 1e-5);
  if (!ok) {
    throw new Error(
      `Identity convolution failed!\nExpected: ${img.data}\nGot:      ${result.data}`
    );
  }
  console.log("Sanity check passed: identity convolution is correct.\n");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function ensureSampleImage(): Promise<string> {
  mkdirSync(ASSETS_DIR, { recursive: true });
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
  sanityCheck();

  const imagePath = await ensureSampleImage();
  const gray = await loadGrayscale(imagePath);

  const kernels: Array<{ name: string; kernel: Kernel; desc: string }> = [
    { name: "edge_h", kernel: EDGE_HORIZONTAL, desc: "Sobel horizontal edges" },
    { name: "edge_v", kernel: EDGE_VERTICAL,   desc: "Sobel vertical edges" },
    { name: "blur",   kernel: BLUR,             desc: "3×3 box blur" },
  ];

  for (const { name, kernel, desc } of kernels) {
    console.log(`Applying : ${desc}`);
    const featureMap = conv2d(gray, kernel);
    saveAsPGM(featureMap, path.join(ASSETS_DIR, `${name}.pgm`));
  }

  console.log();
  console.log("Open the .pgm files in assets/ to visualise the feature maps.");
  console.log("Edge kernels light up boundaries; blur removes high-frequency detail.");
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
