/**
 * img2img.test.ts — Task 3 stub-path tests (jest).
 *
 * Drives the REAL deterministic stubs (img2imgStub / inpaintStub) — the network
 * is never touched. Assertions target the defining behaviours: strength blends
 * input→prompt, and inpainting PRESERVES the unmasked band pixel-for-pixel.
 *
 * How to run (from the repo root):
 *   pnpm jest modules/10-image-generation/ts/img2img.test.ts
 */

import {
  img2imgStub,
  inpaintStub,
  makeTopMaskPng,
  maskedRowCount,
  syntheticInput,
  toDataUri,
} from "./img2img.ts";
import { decodePng } from "./stub_image.ts";

// A real 16x16 PNG so the inpaint stub can decode and preserve its pixels.
const INPUT = syntheticInput(16, 16);

function isPng(bytes: Uint8Array): boolean {
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  return sig.every((b, i) => bytes[i] === b);
}
function pngDims(bytes: Uint8Array): { width: number; height: number } {
  const buf = Buffer.from(bytes);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

describe("toDataUri", () => {
  test("base64-encodes bytes as a PNG data URI", () => {
    // bytes 0x00 0x01 0x02 base64-encode to "AAEC".
    expect(toDataUri(Uint8Array.from([0, 1, 2]))).toBe("data:image/png;base64,AAEC");
  });
});

describe("maskedRowCount", () => {
  test("rounds fraction * height and clamps to [0, height]", () => {
    expect(maskedRowCount(512, 0.4)).toBe(205); // round(204.8)
    expect(maskedRowCount(100, 0.5)).toBe(50);
    expect(maskedRowCount(100, 2)).toBe(100);
    expect(maskedRowCount(100, -1)).toBe(0);
  });
});

describe("img2imgStub", () => {
  test("is deterministic for identical inputs", () => {
    const a = img2imgStub(INPUT, { prompt: "ukiyo-e", strength: 0.65, seed: 42 }, 16);
    const b = img2imgStub(INPUT, { prompt: "ukiyo-e", strength: 0.65, seed: 42 }, 16);
    expect(a.digest).toBe(b.digest);
    expect(Buffer.from(a.imageBytes).equals(Buffer.from(b.imageBytes))).toBe(true);
    expect(isPng(a.imageBytes)).toBe(true);
    expect(pngDims(a.imageBytes)).toEqual({ width: 16, height: 16 });
  });

  test("strength=0 keeps the input fingerprint; strength=1 takes the prompt's", () => {
    const keep = img2imgStub(INPUT, { prompt: "ukiyo-e", strength: 0, seed: 42 }, 16);
    expect(keep.tint).toEqual(keep.inputTint);

    const full = img2imgStub(INPUT, { prompt: "ukiyo-e", strength: 1, seed: 42 }, 16);
    expect(full.tint).toEqual(full.promptTint);
  });

  test("at strength=0 the output ignores the prompt (pure input)", () => {
    const one = img2imgStub(INPUT, { prompt: "prompt-A", strength: 0, seed: 1 }, 16);
    const two = img2imgStub(INPUT, { prompt: "prompt-B", strength: 0, seed: 2 }, 16);
    expect(one.tint).toEqual(two.tint);
  });

  test("changing seed or strength changes the output when strength>0", () => {
    const base = img2imgStub(
      INPUT,
      { prompt: "ukiyo-e", strength: 0.65, seed: 42 },
      16,
    );
    const seedChanged = img2imgStub(
      INPUT,
      { prompt: "ukiyo-e", strength: 0.65, seed: 7 },
      16,
    );
    const strengthChanged = img2imgStub(
      INPUT,
      { prompt: "ukiyo-e", strength: 0.3, seed: 42 },
      16,
    );
    expect(base.tint).not.toEqual(seedChanged.tint);
    expect(base.tint).not.toEqual(strengthChanged.tint);
  });
});

describe("inpaintStub", () => {
  test("preserves the unmasked band PIXEL-FOR-PIXEL from the input", () => {
    const r = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.4 });
    const input = decodePng(INPUT);
    const output = decodePng(r.imageBytes);

    expect(output.width).toBe(input.width);
    expect(output.height).toBe(input.height);
    expect(r.maskedRows).toBe(6); // round(16 * 0.4)

    const stride = input.width * 3;
    // Unmasked (bottom) rows: byte-identical to the input.
    for (let y = r.maskedRows; y < input.height; y++) {
      const start = y * stride;
      expect(Array.from(output.pixels.subarray(start, start + stride))).toEqual(
        Array.from(input.pixels.subarray(start, start + stride)),
      );
    }
    // Masked (top) rows: filled with the regenerated colour.
    const [rr, gg, bb] = r.regeneratedTint;
    for (let y = 0; y < r.maskedRows; y++) {
      const p = y * stride;
      expect([output.pixels[p], output.pixels[p + 1], output.pixels[p + 2]]).toEqual([
        rr,
        gg,
        bb,
      ]);
    }
    // preservedTint is genuinely the input's colour, and the masked band was
    // actually changed (regenerated != preserved).
    expect(r.preservedTint).toEqual([
      input.pixels[0],
      input.pixels[1],
      input.pixels[2],
    ]);
    expect(r.regeneratedTint).not.toEqual(r.preservedTint);
  });

  test("preserved band is independent of prompt/seed; regenerated band is not", () => {
    const a = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.4 });
    const b = inpaintStub(INPUT, { prompt: "sunset", seed: 2, maskFraction: 0.4 });
    expect(a.preservedTint).toEqual(b.preservedTint);
    expect(a.regeneratedTint).not.toEqual(b.regeneratedTint);
  });

  test("regenerated band changes with the seed alone", () => {
    const a = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.4 });
    const b = inpaintStub(INPUT, { prompt: "storm", seed: 2, maskFraction: 0.4 });
    expect(a.regeneratedTint).not.toEqual(b.regeneratedTint);
    expect(a.preservedTint).toEqual(b.preservedTint);
  });

  test("masked rows follow the fraction, output is a valid PNG", () => {
    const r = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.25 });
    expect(r.maskedRows).toBe(4); // round(16 * 0.25)
    expect(isPng(r.imageBytes)).toBe(true);
    expect(pngDims(r.imageBytes)).toEqual({ width: 16, height: 16 });
  });

  test("is deterministic for identical inputs", () => {
    const a = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.4 });
    const b = inpaintStub(INPUT, { prompt: "storm", seed: 1, maskFraction: 0.4 });
    expect(a.digest).toBe(b.digest);
    expect(Buffer.from(a.imageBytes).equals(Buffer.from(b.imageBytes))).toBe(true);
  });
});

describe("mask and synthetic input", () => {
  test("makeTopMaskPng and syntheticInput are valid, correctly sized PNGs", () => {
    const mask = makeTopMaskPng(32, 32, 0.4);
    expect(isPng(mask)).toBe(true);
    expect(pngDims(mask)).toEqual({ width: 32, height: 32 });

    const input = syntheticInput(32, 32);
    expect(isPng(input)).toBe(true);
    expect(pngDims(input)).toEqual({ width: 32, height: 32 });
  });
});
