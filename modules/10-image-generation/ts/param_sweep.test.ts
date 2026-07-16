/**
 * param_sweep.test.ts — Task 2 stub-path tests (jest).
 *
 * Drives the REAL sweep functions with a small controlled config. The grid
 * structure is hand-written; determinism and discrimination are asserted as
 * behaviours, never by recomputing the tint through the code under test.
 *
 * How to run (from the repo root):
 *   pnpm jest modules/10-image-generation/ts/param_sweep.test.ts
 */

import {
  buildSweepCells,
  buildSweepStub,
  cellFilename,
  cellToOptions,
  type SweepConfig,
} from "./param_sweep.ts";

const CONFIG: SweepConfig = {
  prompt: "P",
  negativePrompt: "N",
  guidanceScales: [3, 7.5, 15],
  stepsList: [10, 30],
  seed: 42,
  width: 8,
  height: 8,
};

function pngDims(bytes: Uint8Array): { width: number; height: number } {
  const buf = Buffer.from(bytes);
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

describe("buildSweepCells", () => {
  test("produces the exact row-major grid (rows=steps, cols=guidance)", () => {
    const cells = buildSweepCells(CONFIG);
    expect(cells).toHaveLength(6);

    expect(cells[0]).toEqual({
      row: 0,
      col: 0,
      steps: 10,
      guidanceScale: 3,
      seed: 42,
      prompt: "P",
      negativePrompt: "N",
      width: 8,
      height: 8,
    });
    // Same row, next columns advance guidance scale.
    expect(cells[1]).toMatchObject({ row: 0, col: 1, steps: 10, guidanceScale: 7.5 });
    expect(cells[2]).toMatchObject({ row: 0, col: 2, steps: 10, guidanceScale: 15 });
    // Next row advances the step count, column resets.
    expect(cells[3]).toMatchObject({ row: 1, col: 0, steps: 30, guidanceScale: 3 });
    expect(cells[5]).toMatchObject({ row: 1, col: 2, steps: 30, guidanceScale: 15 });
  });
});

describe("cellToOptions", () => {
  test("maps a cell to the provider-agnostic options", () => {
    const [cell] = buildSweepCells(CONFIG);
    expect(cellToOptions(cell)).toEqual({
      prompt: "P",
      negativePrompt: "N",
      width: 8,
      height: 8,
      guidanceScale: 3,
      numInferenceSteps: 10,
      seed: 42,
    });
  });
});

describe("buildSweepStub", () => {
  test("records every parameter + seed per cell in reproducible metadata", () => {
    const { metadata, cellImages } = buildSweepStub(CONFIG);

    expect(metadata.offline).toBe(true);
    expect(metadata.cols).toBe(3);
    expect(metadata.rows).toBe(2);
    expect(metadata.grid).toBe("sweep_grid.png");
    expect(metadata.cells).toHaveLength(6);
    expect(cellImages).toHaveLength(6);

    const first = metadata.cells[0];
    expect(first).toMatchObject({
      row: 0,
      col: 0,
      steps: 10,
      guidanceScale: 3,
      seed: 42,
      output: "sweep_cell_r0_c0.png",
      provider: "stub",
      model: "stub-solid-v1",
    });
    expect(first.digest).toMatch(/^[0-9a-f]{8}$/);
    expect(first.tint).toHaveLength(3);
    // Filenames follow the (row, col) grid coordinates.
    expect(metadata.cells.map((c) => c.output)).toEqual([
      "sweep_cell_r0_c0.png",
      "sweep_cell_r0_c1.png",
      "sweep_cell_r0_c2.png",
      "sweep_cell_r1_c0.png",
      "sweep_cell_r1_c1.png",
      "sweep_cell_r1_c2.png",
    ]);
    expect(cellFilename(buildSweepCells(CONFIG)[4])).toBe("sweep_cell_r1_c1.png");
  });

  test("is byte-for-byte reproducible across runs", () => {
    const a = buildSweepStub(CONFIG);
    const b = buildSweepStub(CONFIG);
    expect(a.metadata).toEqual(b.metadata);
    expect(Buffer.from(a.gridImage).equals(Buffer.from(b.gridImage))).toBe(true);
  });

  test("different guidance scales and different seeds yield different swatches", () => {
    const { metadata } = buildSweepStub(CONFIG);
    // Cells 0/1/2 differ only in guidance scale -> different fingerprints.
    expect(metadata.cells[0].tint).not.toEqual(metadata.cells[1].tint);
    expect(metadata.cells[1].tint).not.toEqual(metadata.cells[2].tint);

    const other = buildSweepStub({ ...CONFIG, seed: 43 });
    expect(other.metadata.cells[0].tint).not.toEqual(metadata.cells[0].tint);
  });

  test("the grid PNG has the composited dimensions", () => {
    const { gridImage } = buildSweepStub(CONFIG);
    // 3 cols * 8px wide, 2 rows * 8px tall.
    expect(pngDims(gridImage)).toEqual({ width: 24, height: 16 });
  });
});
