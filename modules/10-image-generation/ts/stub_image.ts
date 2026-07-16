/**
 * stub_image.ts — deterministic OFFLINE image helpers for module 10.
 *
 * What it teaches:
 *   The hosted image API is a non-deterministic, keyed, network boundary. To
 *   run the sweep / img2img exercises in CI (and to write discriminating tests)
 *   we need a stand-in that is *fully deterministic and offline*: same inputs →
 *   byte-identical output, no API key, no network. This file is that stand-in.
 *
 *   It also carries a tiny, dependency-free PNG encoder (Node's built-in zlib
 *   for DEFLATE + a hand-written CRC-32) so the stub produces *real, viewable*
 *   PNG files — a solid colour derived deterministically from the request. The
 *   colour is a fingerprint of the parameters, so two different requests render
 *   as two visibly different swatches.
 *
 * Offline switch:
 *   isOffline() is true when IMAGE_STUB or OFFLINE_SMOKE is a truthy env value.
 *   The hosted providers stay isolated in image_client.ts; nothing here talks
 *   to the network.
 */

import { deflateSync, inflateSync } from "node:zlib";
import { env } from "node:process";

export type RGB = [number, number, number];

// ---------------------------------------------------------------------------
// Offline switch
// ---------------------------------------------------------------------------

function truthy(value: string | undefined): boolean {
  if (!value) return false;
  const s = value.trim().toLowerCase();
  return s === "1" || s === "true" || s === "yes" || s === "on";
}

/** True when the deterministic offline stub path should be used (no network). */
export function isOffline(): boolean {
  return truthy(env["IMAGE_STUB"]) || truthy(env["OFFLINE_SMOKE"]);
}

// ---------------------------------------------------------------------------
// Deterministic hashing (FNV-1a, 32-bit)
// ---------------------------------------------------------------------------

/** FNV-1a 32-bit hash of a string. Returns an unsigned 32-bit integer. */
export function fnv1a(input: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** FNV-1a 32-bit hash of raw bytes, returned as an 8-char hex digest. */
export function hashBytes(bytes: Uint8Array): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < bytes.length; i++) {
    h ^= bytes[i];
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

/** Map a 32-bit hash to an RGB triple (top three bytes). */
export function rgbFromHash(hash: number): RGB {
  return [(hash >>> 16) & 0xff, (hash >>> 8) & 0xff, hash & 0xff];
}

/** Deterministic RGB swatch for an arbitrary key string. */
export function tintFor(key: string): RGB {
  return rgbFromHash(fnv1a(key));
}

/** Linear interpolation between two colours; t is clamped to [0, 1]. */
export function lerpRgb(a: RGB, b: RGB, t: number): RGB {
  const k = Math.max(0, Math.min(1, t));
  return [
    Math.round(a[0] + (b[0] - a[0]) * k),
    Math.round(a[1] + (b[1] - a[1]) * k),
    Math.round(a[2] + (b[2] - a[2]) * k),
  ];
}

// ---------------------------------------------------------------------------
// Minimal PNG encoder (8-bit truecolour RGB) — no external image deps
// ---------------------------------------------------------------------------

const CRC_TABLE: Uint32Array = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes: Uint8Array): number {
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) {
    c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type: string, data: Uint8Array): Buffer {
  const body = Buffer.concat([Buffer.from(type, "ascii"), Buffer.from(data)]);
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(body), 0);
  return Buffer.concat([length, body, crc]);
}

/**
 * Encode a raw RGB pixel buffer (length = width*height*3) as PNG bytes.
 * Uses filter type 0 (none) on every scanline and DEFLATE via zlib.
 */
export function encodePng(width: number, height: number, rgb: Uint8Array): Uint8Array {
  if (
    !Number.isInteger(width) ||
    !Number.isInteger(height) ||
    width <= 0 ||
    height <= 0
  ) {
    throw new Error(
      `invalid PNG dimensions ${width}x${height} (must be positive integers)`,
    );
  }
  if (rgb.length !== width * height * 3) {
    throw new Error(
      `pixel buffer length ${rgb.length} != ${width}x${height}x3 (${width * height * 3})`,
    );
  }
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 2; // colour type: truecolour RGB
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  const stride = width * 3;
  const raw = Buffer.alloc(height * (stride + 1));
  for (let y = 0; y < height; y++) {
    const offset = y * (stride + 1);
    raw[offset] = 0; // filter byte: none
    raw.set(rgb.subarray(y * stride, (y + 1) * stride), offset + 1);
  }
  const idat = deflateSync(raw);

  return Buffer.concat([
    signature,
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", idat),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

export interface DecodedPng {
  width: number;
  height: number;
  /** Raw RGB pixels, length = width*height*3. */
  pixels: Uint8Array;
}

function paeth(a: number, b: number, c: number): number {
  const p = a + b - c;
  const pa = Math.abs(p - a);
  const pb = Math.abs(p - b);
  const pc = Math.abs(p - c);
  if (pa <= pb && pa <= pc) return a;
  if (pb <= pc) return b;
  return c;
}

/**
 * Decode an 8-bit truecolour (RGB) non-interlaced PNG — the inverse of
 * encodePng, and a real, STRICT decoder. It validates every chunk's CRC-32,
 * requires a well-formed IHDR → IDAT(s) → IEND sequence, bounds-checks chunk
 * lengths, rejects trailing bytes after IEND, and verifies the inflated
 * scanline length. Malformed input therefore throws rather than silently
 * entering the pipeline. Used so the inpaint stub can copy the input's pixels.
 */
export function decodePng(bytes: Uint8Array): DecodedPng {
  const buf = Buffer.from(bytes);
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  if (buf.length < 8) throw new Error("truncated PNG (no signature)");
  for (let i = 0; i < 8; i++) {
    if (buf[i] !== sig[i]) throw new Error("not a PNG (bad signature)");
  }

  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idatParts: Buffer[] = [];

  // Strict chunk-order state machine. This narrow RGB decoder accepts ONLY the
  // sequence IHDR → IDAT(one or more, contiguous) → IEND(empty) and rejects
  // everything else: unknown critical OR ancillary chunks, a misplaced/repeated
  // IHDR, IDAT before IHDR / non-contiguous / after IEND, a missing IDAT, and
  // any bytes after IEND.
  type ChunkState = "expect-ihdr" | "expect-idat" | "in-idat" | "done";
  let state: ChunkState = "expect-ihdr";
  let pos = 8;
  while (pos < buf.length) {
    if (state === "done") throw new Error("trailing data after IEND");
    if (pos + 8 > buf.length) throw new Error("truncated chunk header");
    const len = buf.readUInt32BE(pos);
    const dataStart = pos + 8;
    const dataEnd = dataStart + len;
    if (dataEnd + 4 > buf.length) throw new Error("chunk length out of bounds");
    const type = buf.toString("ascii", pos + 4, pos + 8);
    const storedCrc = buf.readUInt32BE(dataEnd);
    // CRC covers the chunk type + data.
    if (crc32(buf.subarray(pos + 4, dataEnd)) !== storedCrc) {
      throw new Error(`bad CRC-32 for ${type} chunk`);
    }

    if (state === "expect-ihdr") {
      if (type !== "IHDR") throw new Error(`expected IHDR first, got ${type}`);
      if (len !== 13) throw new Error(`invalid IHDR length ${len} (must be 13)`);
      const data = buf.subarray(dataStart, dataEnd);
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      if (width <= 0 || height <= 0) {
        throw new Error(`invalid PNG dimensions ${width}x${height} (must be positive)`);
      }
      bitDepth = data[8];
      colorType = data[9];
      if (data[10] !== 0) throw new Error("unsupported compression method");
      if (data[11] !== 0) throw new Error("unsupported filter method");
      if (data[12] !== 0) throw new Error("interlaced PNG unsupported");
      state = "expect-idat";
    } else if (state === "expect-idat") {
      if (type !== "IDAT") throw new Error(`expected IDAT, got ${type}`);
      idatParts.push(Buffer.from(buf.subarray(dataStart, dataEnd)));
      state = "in-idat";
    } else {
      // state === "in-idat": more IDATs (contiguous) or the closing IEND.
      if (type === "IDAT") {
        idatParts.push(Buffer.from(buf.subarray(dataStart, dataEnd)));
      } else if (type === "IEND") {
        if (len !== 0) throw new Error(`invalid IEND length ${len} (must be 0)`);
        state = "done";
      } else {
        throw new Error(`unexpected ${type} chunk (expected IDAT or IEND)`);
      }
    }
    pos = dataEnd + 4; // length(4) + type(4) + data + crc(4)
  }

  if (state === "expect-ihdr") throw new Error("missing IHDR chunk");
  if (state === "expect-idat") throw new Error("missing IDAT chunk");
  if (state === "in-idat") throw new Error("missing IEND chunk");
  if (bitDepth !== 8 || colorType !== 2) {
    throw new Error(
      `decodePng supports 8-bit RGB only (got depth=${bitDepth}, colorType=${colorType})`,
    );
  }

  // The concatenated IDAT data MUST be a single conforming zlib stream with no
  // trailing bytes. `inflateSync` silently ignores anything after the stream
  // ends, so we inflate with `{ info: true }` and require the engine to have
  // consumed the whole input (bytesWritten == input length).
  const idatData = Buffer.concat(idatParts);
  const inflated = inflateSync(idatData, { info: true }) as unknown as {
    buffer: Buffer;
    engine: { bytesWritten: number };
  };
  if (inflated.engine.bytesWritten !== idatData.length) {
    throw new Error(
      `trailing data inside IDAT: zlib stream consumed ` +
        `${inflated.engine.bytesWritten} of ${idatData.length} bytes`,
    );
  }
  const raw = inflated.buffer;
  const stride = width * 3;
  if (raw.length !== height * (stride + 1)) {
    throw new Error(
      `unexpected scanline length ${raw.length}, expected ${height * (stride + 1)}`,
    );
  }
  const bpp = 3;
  const pixels = new Uint8Array(width * height * 3);
  let prev = new Uint8Array(stride);
  let rp = 0;
  for (let y = 0; y < height; y++) {
    const filter = raw[rp++];
    const cur = new Uint8Array(stride);
    for (let i = 0; i < stride; i++) {
      const x = raw[rp++];
      const a = i >= bpp ? cur[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      let value: number;
      switch (filter) {
        case 0:
          value = x;
          break;
        case 1:
          value = x + a;
          break;
        case 2:
          value = x + b;
          break;
        case 3:
          value = x + ((a + b) >> 1);
          break;
        case 4:
          value = x + paeth(a, b, c);
          break;
        default:
          throw new Error(`unknown PNG filter type ${filter}`);
      }
      cur[i] = value & 0xff;
    }
    pixels.set(cur, y * stride);
    prev = cur;
  }
  return { width, height, pixels };
}

/** Build a solid-colour raw RGB pixel buffer. */
export function solidPixels(width: number, height: number, rgb: RGB): Uint8Array {
  const px = new Uint8Array(width * height * 3);
  for (let i = 0; i < px.length; i += 3) {
    px[i] = rgb[0];
    px[i + 1] = rgb[1];
    px[i + 2] = rgb[2];
  }
  return px;
}

/** Encode a solid-colour PNG in one call. */
export function solidPng(width: number, height: number, rgb: RGB): Uint8Array {
  return encodePng(width, height, solidPixels(width, height, rgb));
}

/**
 * Composite a row-major list of solid cell colours into one grid PNG.
 * cellRgbs[row * cols + col] is the colour of that cell.
 */
export function solidGridPng(
  cellRgbs: RGB[],
  cols: number,
  rows: number,
  cellW: number,
  cellH: number,
): Uint8Array {
  if (cellRgbs.length !== cols * rows) {
    throw new Error(`expected ${cols * rows} cells, got ${cellRgbs.length}`);
  }
  const width = cols * cellW;
  const height = rows * cellH;
  const px = new Uint8Array(width * height * 3);
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const [r, g, b] = cellRgbs[row * cols + col];
      for (let y = row * cellH; y < (row + 1) * cellH; y++) {
        for (let x = col * cellW; x < (col + 1) * cellW; x++) {
          const idx = (y * width + x) * 3;
          px[idx] = r;
          px[idx + 1] = g;
          px[idx + 2] = b;
        }
      }
    }
  }
  return encodePng(width, height, px);
}

/**
 * Raw RGB pixel buffer of two stacked horizontal bands: the top `topRows` rows
 * use `topRgb`, the remainder uses `bottomRgb`.
 */
export function bandedPixels(
  width: number,
  height: number,
  topRows: number,
  topRgb: RGB,
  bottomRgb: RGB,
): Uint8Array {
  const px = new Uint8Array(width * height * 3);
  for (let y = 0; y < height; y++) {
    const [r, g, b] = y < topRows ? topRgb : bottomRgb;
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 3;
      px[idx] = r;
      px[idx + 1] = g;
      px[idx + 2] = b;
    }
  }
  return px;
}

/**
 * Composite two stacked horizontal bands into one PNG: the top `topRows` rows
 * use `topRgb`, the remainder uses `bottomRgb`. Used to model an inpaint mask
 * (top band = regenerated region, bottom band = preserved region).
 */
export function bandedPng(
  width: number,
  height: number,
  topRows: number,
  topRgb: RGB,
  bottomRgb: RGB,
): Uint8Array {
  return encodePng(
    width,
    height,
    bandedPixels(width, height, topRows, topRgb, bottomRgb),
  );
}
