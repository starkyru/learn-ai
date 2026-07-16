/**
 * stub_image.test.ts — unit tests for the deterministic offline helpers (jest).
 *
 * These drive the REAL helper functions. Hash expectations use the canonical,
 * externally published FNV-1a 32-bit test vectors (isthe.com/chongo/fnv), so
 * the assertions are independently derived, not recomputed from the code.
 *
 * How to run (from the repo root):
 *   pnpm jest modules/10-image-generation/ts/stub_image.test.ts
 */

import { inflateSync } from "node:zlib";

import {
  decodePng,
  encodePng,
  fnv1a,
  hashBytes,
  isOffline,
  lerpRgb,
  rgbFromHash,
  solidGridPng,
  solidPixels,
  tintFor,
} from "./stub_image.ts";

function isPng(bytes: Uint8Array): boolean {
  const sig = [137, 80, 78, 71, 13, 10, 26, 10];
  return sig.every((b, i) => bytes[i] === b);
}

// IHDR width/height live right after the 8-byte signature + 8-byte chunk header.
function pngDims(bytes: Uint8Array): { width: number; height: number } {
  const buf = Buffer.from(bytes);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

// An INDEPENDENT bit-by-bit CRC-32 (PNG polynomial 0xEDB88320) — written from
// scratch here, not the encoder's table-driven version, so it is a real oracle.
function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) {
    crc ^= bytes[i];
    for (let k = 0; k < 8; k++) {
      crc = crc & 1 ? (crc >>> 1) ^ 0xedb88320 : crc >>> 1;
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

interface ParsedChunk {
  type: string;
  data: Buffer;
  crcOk: boolean;
}

// Independently parse the chunk stream, recomputing and checking each CRC.
function parseChunks(bytes: Uint8Array): {
  chunks: ParsedChunk[];
  fullyConsumed: boolean;
} {
  const buf = Buffer.from(bytes);
  const chunks: ParsedChunk[] = [];
  let pos = 8; // past the signature
  while (pos + 8 <= buf.length) {
    const len = buf.readUInt32BE(pos);
    const type = buf.toString("ascii", pos + 4, pos + 8);
    const dataStart = pos + 8;
    const dataEnd = dataStart + len;
    const data = Buffer.from(buf.subarray(dataStart, dataEnd));
    const storedCrc = buf.readUInt32BE(dataEnd);
    const crcInput = Buffer.concat([Buffer.from(type, "ascii"), data]);
    chunks.push({ type, data, crcOk: crc32(crcInput) === storedCrc });
    pos = dataEnd + 4;
    if (type === "IEND") break;
  }
  return { chunks, fullyConsumed: pos === buf.length };
}

const PNG_SIG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

// Build a single well-formed chunk (correct length + CRC) — used to craft
// CRC-valid but structurally malformed PNGs for the decoder rejection tests.
function buildChunk(type: string, data: Buffer): Buffer {
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);
  const typeBuf = Buffer.from(type, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])), 0);
  return Buffer.concat([length, typeBuf, data, crc]);
}

describe("fnv1a (canonical published vectors)", () => {
  test("empty string is the FNV offset basis", () => {
    expect(fnv1a("")).toBe(2166136261); // 0x811c9dc5
  });

  test('"a" and "foobar" match the reference vectors', () => {
    expect(fnv1a("a")).toBe(3826002220); // 0xe40c292c
    expect(fnv1a("foobar")).toBe(3214735720); // 0xbf9cf968
  });
});

describe("rgbFromHash / tintFor", () => {
  test("rgbFromHash extracts the top three bytes", () => {
    expect(rgbFromHash(0xaabbccdd)).toEqual([187, 204, 221]);
  });

  test('tintFor("foobar") is derived from its FNV hash 0xbf9cf968', () => {
    // 0xbf9cf968 -> [0x9c, 0xf9, 0x68] = [156, 249, 104]
    expect(tintFor("foobar")).toEqual([156, 249, 104]);
  });
});

describe("lerpRgb", () => {
  test("midpoint and clamped endpoints", () => {
    expect(lerpRgb([0, 0, 0], [100, 200, 50], 0.5)).toEqual([50, 100, 25]);
    expect(lerpRgb([10, 20, 30], [200, 100, 60], 0)).toEqual([10, 20, 30]);
    expect(lerpRgb([10, 20, 30], [200, 100, 60], 1)).toEqual([200, 100, 60]);
    expect(lerpRgb([10, 20, 30], [200, 100, 60], 5)).toEqual([200, 100, 60]);
    expect(lerpRgb([10, 20, 30], [200, 100, 60], -5)).toEqual([10, 20, 30]);
  });
});

describe("encodePng", () => {
  test("writes the PNG signature and the exact IHDR dimensions", () => {
    const png = encodePng(4, 3, solidPixels(4, 3, [10, 20, 30]));
    expect(isPng(png)).toBe(true);
    expect(pngDims(png)).toEqual({ width: 4, height: 3 });
  });

  test("rejects a pixel buffer of the wrong length", () => {
    expect(() => encodePng(4, 3, new Uint8Array(10))).toThrow();
  });

  test("rejects zero, fractional, negative, and non-finite dimensions", () => {
    expect(() => encodePng(0, 1, new Uint8Array(0))).toThrow(/dimension/i);
    expect(() => encodePng(1, 0, new Uint8Array(0))).toThrow(/dimension/i);
    expect(() => encodePng(1.5, 2, new Uint8Array(9))).toThrow(/dimension/i);
    expect(() => encodePng(-2, 2, new Uint8Array(0))).toThrow(/dimension/i);
    expect(() => encodePng(Number.NaN, 2, new Uint8Array(0))).toThrow(/dimension/i);
  });
});

describe("solidGridPng", () => {
  test("composites cells into a grid of the expected size", () => {
    const grid = solidGridPng(
      [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
        [4, 4, 4],
      ],
      2,
      2,
      3,
      3,
    );
    expect(isPng(grid)).toBe(true);
    expect(pngDims(grid)).toEqual({ width: 6, height: 6 });
  });

  test("rejects a wrong number of cells", () => {
    expect(() => solidGridPng([[0, 0, 0]], 2, 2, 3, 3)).toThrow();
  });
});

describe("PNG encoder invariants (independent validation)", () => {
  // A 3x2 image with all-distinct pixel values so the scanline layout is
  // actually exercised (not a solid colour that hides ordering bugs).
  const width = 3;
  const height = 2;
  const pixels = Uint8Array.from([
    0,
    0,
    0,
    10,
    20,
    30,
    40,
    50,
    60, // row 0
    70,
    80,
    90,
    100,
    110,
    120,
    130,
    140,
    150, // row 1
  ]);

  test("chunk order, sizes and every CRC-32 are valid", () => {
    const png = encodePng(width, height, pixels);
    const { chunks, fullyConsumed } = parseChunks(png);

    expect(chunks.map((c) => c.type)).toEqual(["IHDR", "IDAT", "IEND"]);
    expect(chunks.every((c) => c.crcOk)).toBe(true);
    // pos must land exactly on the end — a mis-sized chunk would not.
    expect(fullyConsumed).toBe(true);

    const ihdr = chunks[0].data;
    expect(ihdr.length).toBe(13);
    expect(ihdr.readUInt32BE(0)).toBe(width);
    expect(ihdr.readUInt32BE(4)).toBe(height);
    expect([ihdr[8], ihdr[9], ihdr[10], ihdr[11], ihdr[12]]).toEqual([8, 2, 0, 0, 0]);

    expect(chunks[2].data.length).toBe(0); // IEND is empty
  });

  test("IDAT inflates to the exact filtered scanlines (zlib oracle)", () => {
    const png = encodePng(width, height, pixels);
    const { chunks } = parseChunks(png);
    const idat = chunks.find((c) => c.type === "IDAT");
    expect(idat).toBeDefined();

    const raw = inflateSync(idat!.data);
    // Each scanline = 1 filter byte (0 = none) + width*3 RGB bytes.
    const expected = Buffer.from([
      0,
      0,
      0,
      0,
      10,
      20,
      30,
      40,
      50,
      60, // filter 0 + row 0
      0,
      70,
      80,
      90,
      100,
      110,
      120,
      130,
      140,
      150, // filter 0 + row 1
    ]);
    expect(raw.length).toBe(height * (width * 3 + 1));
    expect(Buffer.from(raw).equals(expected)).toBe(true);
  });
});

describe("decodePng (round-trips encodePng)", () => {
  test("recovers exact dimensions and pixels", () => {
    const width = 3;
    const height = 2;
    const pixels = Uint8Array.from([
      1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
    ]);
    const decoded = decodePng(encodePng(width, height, pixels));
    expect(decoded.width).toBe(width);
    expect(decoded.height).toBe(height);
    expect(Array.from(decoded.pixels)).toEqual(Array.from(pixels));
  });

  test("rejects non-PNG bytes", () => {
    expect(() => decodePng(Uint8Array.from([1, 2, 3, 4]))).toThrow();
  });

  test("rejects malformed PNGs (corrupt CRC, missing IEND, trailing garbage)", () => {
    const good = encodePng(2, 2, solidPixels(2, 2, [1, 2, 3]));

    // 1) Corrupt the IHDR CRC (last of the first chunk's 4 CRC bytes at offset
    //    8 + 4 + 4 + 13 + 3 = 32). Flipping it must make the CRC check fail.
    const badCrc = Buffer.from(good);
    badCrc[32] ^= 0xff;
    expect(() => decodePng(badCrc)).toThrow(/CRC/i);

    // 2) Drop the trailing IEND chunk (last 12 bytes: len+type+crc, no data).
    const noIend = Buffer.from(good).subarray(0, good.length - 12);
    expect(() => decodePng(noIend)).toThrow(/IEND/i);

    // 3) Append trailing garbage after IEND.
    const trailing = Buffer.concat([Buffer.from(good), Buffer.from([0, 0, 0, 0])]);
    expect(() => decodePng(trailing)).toThrow(/trailing/i);
  });

  test("rejects CRC-valid PNGs with a mis-sized IHDR or a non-empty IEND", () => {
    // Valid 1x1 IHDR payload (13 bytes): 1x1, depth 8, RGB(2), comp/filter/interlace 0.
    const validIhdr = Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 2, 0, 0, 0]);
    // The decoder rejects IHDR/IEND before ever inflating, so any CRC-valid IDAT
    // body works here.
    const idat = buildChunk("IDAT", Buffer.from([1, 2, 3]));

    // IHDR payload of 12 bytes (must be 13) — CRC is valid for the wrong length.
    const badIhdr = Buffer.concat([
      PNG_SIG,
      buildChunk("IHDR", Buffer.alloc(12)),
      idat,
      buildChunk("IEND", Buffer.alloc(0)),
    ]);
    expect(() => decodePng(badIhdr)).toThrow(/IHDR length/i);

    // Non-empty IEND (must be 0 bytes) — CRC valid for the wrong content.
    const badIend = Buffer.concat([
      PNG_SIG,
      buildChunk("IHDR", validIhdr),
      idat,
      buildChunk("IEND", Buffer.from([1])),
    ]);
    expect(() => decodePng(badIend)).toThrow(/IEND length/i);
  });

  test("rejects CRC-valid PNGs with a zero width or height", () => {
    const idat = buildChunk("IDAT", Buffer.from([1, 2, 3]));
    const iend = buildChunk("IEND", Buffer.alloc(0));
    // depth 8, colorType 2 (RGB), comp/filter/interlace 0 — only the dims are bad.
    const zeroWidth = Buffer.from([0, 0, 0, 0, 0, 0, 0, 1, 8, 2, 0, 0, 0]); // 0x1
    const zeroHeight = Buffer.from([0, 0, 0, 1, 0, 0, 0, 0, 8, 2, 0, 0, 0]); // 1x0

    const w0 = Buffer.concat([PNG_SIG, buildChunk("IHDR", zeroWidth), idat, iend]);
    const h0 = Buffer.concat([PNG_SIG, buildChunk("IHDR", zeroHeight), idat, iend]);
    expect(() => decodePng(w0)).toThrow(/dimension/i);
    expect(() => decodePng(h0)).toThrow(/dimension/i);

    // A valid 1x1 still decodes.
    const ok = encodePng(1, 1, solidPixels(1, 1, [7, 8, 9]));
    expect(decodePng(ok)).toEqual({
      width: 1,
      height: 1,
      pixels: Uint8Array.from([7, 8, 9]),
    });
  });

  test("enforces a strict IHDR -> IDAT+ -> IEND chunk order", () => {
    const ihdr = buildChunk(
      "IHDR",
      Buffer.from([0, 0, 0, 1, 0, 0, 0, 1, 8, 2, 0, 0, 0]),
    );
    const idat = buildChunk("IDAT", Buffer.from([1, 2, 3]));
    const iend = buildChunk("IEND", Buffer.alloc(0));

    // Unknown CRITICAL chunk (uppercase first byte) before IEND — must reject.
    const unknownCritical = Buffer.concat([
      PNG_SIG,
      ihdr,
      idat,
      buildChunk("ABCD", Buffer.from([9])),
      iend,
    ]);
    expect(() => decodePng(unknownCritical)).toThrow(/ABCD/);

    // Unknown ANCILLARY chunk (lowercase first byte) — also unsupported here.
    const unknownAncillary = Buffer.concat([
      PNG_SIG,
      ihdr,
      idat,
      buildChunk("teXt", Buffer.from([9])),
      iend,
    ]);
    expect(() => decodePng(unknownAncillary)).toThrow(/teXt/);

    // Non-contiguous IDAT (IDAT, other, IDAT) — must reject.
    const nonContiguous = Buffer.concat([
      PNG_SIG,
      ihdr,
      idat,
      buildChunk("gAMA", Buffer.from([1, 2, 3, 4])),
      idat,
      iend,
    ]);
    expect(() => decodePng(nonContiguous)).toThrow(/gAMA/);

    // IHDR not first — must reject.
    const ihdrNotFirst = Buffer.concat([PNG_SIG, idat, ihdr, iend]);
    expect(() => decodePng(ihdrNotFirst)).toThrow(/IHDR first/i);

    // A repeated IHDR — must reject (second IHDR appears where IDAT is expected).
    const repeatedIhdr = Buffer.concat([PNG_SIG, ihdr, ihdr, idat, iend]);
    expect(() => decodePng(repeatedIhdr)).toThrow(/expected IDAT/i);

    // A valid IHDR -> IDAT -> IEND still decodes.
    const good = encodePng(1, 1, solidPixels(1, 1, [4, 5, 6]));
    expect(decodePng(good)).toEqual({
      width: 1,
      height: 1,
      pixels: Uint8Array.from([4, 5, 6]),
    });
  });

  test("rejects bytes appended after the zlib stream inside IDAT", () => {
    const pixels = solidPixels(2, 2, [5, 6, 7]);
    const good = encodePng(2, 2, pixels);
    const { chunks } = parseChunks(good);
    const ihdrData = chunks.find((c) => c.type === "IHDR")!.data;
    const idatData = chunks.find((c) => c.type === "IDAT")!.data;

    // Append 4 bytes to the valid zlib stream and fix the IDAT length + CRC.
    // inflateSync would silently ignore them, but the decoder must reject.
    const tamperedIdat = Buffer.concat([idatData, Buffer.from([0, 0, 0, 0])]);
    const tampered = Buffer.concat([
      PNG_SIG,
      buildChunk("IHDR", ihdrData),
      buildChunk("IDAT", tamperedIdat),
      buildChunk("IEND", Buffer.alloc(0)),
    ]);
    expect(() => decodePng(tampered)).toThrow(/trailing data inside IDAT/i);

    // The untampered PNG still decodes to the exact pixels.
    expect(decodePng(good)).toEqual({
      width: 2,
      height: 2,
      pixels,
    });
  });
});

describe("hashBytes", () => {
  test("is deterministic and distinguishes different bytes", () => {
    const a = Uint8Array.from([1, 2, 3]);
    const b = Uint8Array.from([1, 2, 4]);
    expect(hashBytes(a)).toBe(hashBytes(Uint8Array.from([1, 2, 3])));
    expect(hashBytes(a)).not.toBe(hashBytes(b));
    expect(hashBytes(a)).toMatch(/^[0-9a-f]{8}$/);
  });
});

describe("isOffline", () => {
  const saved = {
    stub: process.env["IMAGE_STUB"],
    smoke: process.env["OFFLINE_SMOKE"],
  };
  afterEach(() => {
    if (saved.stub === undefined) delete process.env["IMAGE_STUB"];
    else process.env["IMAGE_STUB"] = saved.stub;
    if (saved.smoke === undefined) delete process.env["OFFLINE_SMOKE"];
    else process.env["OFFLINE_SMOKE"] = saved.smoke;
  });

  test("reads truthy values from either flag", () => {
    delete process.env["IMAGE_STUB"];
    delete process.env["OFFLINE_SMOKE"];
    expect(isOffline()).toBe(false);

    process.env["IMAGE_STUB"] = "1";
    expect(isOffline()).toBe(true);

    process.env["IMAGE_STUB"] = "0";
    expect(isOffline()).toBe(false);

    process.env["OFFLINE_SMOKE"] = "true";
    expect(isOffline()).toBe(true);
  });
});
