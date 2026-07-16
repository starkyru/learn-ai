/**
 * Contract tests for data_map.json (Module 20b, Task 1 "Done when").
 *
 * Validates the governance artifact itself: it must cover the whole data
 * lifecycle (not just the source document), and every store must carry an
 * owner, purpose, retention, and deletion decision. The required categories and
 * keys are hand-written here as the contract; the test asserts the shared JSON
 * file satisfies them.
 *
 * Run: pnpm jest modules/20b-governance-privacy/ts/data-map.test.ts
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

const DATA_MAP_PATH = join(__dirname, "..", "data_map.json");

interface Store {
  id: string;
  category: string;
  data_class: string;
  purpose: string;
  owner: string;
  access_control: string;
  retention: string;
  deletion_mechanism: string;
}

interface DataMap {
  not_legal_advice: boolean;
  stores: Store[];
}

// Task 1 requires the map to reach past the source document into the derived
// and operational stores. Each must be represented at least once.
const REQUIRED_CATEGORIES = [
  "app_db",
  "prompt",
  "provider",
  "embeddings",
  "cache",
  "logs",
  "tracing",
  "feedback",
  "tools",
  "derived",
  "backups",
];

const REQUIRED_KEYS = [
  "id",
  "category",
  "data_class",
  "purpose",
  "owner",
  "access_control",
  "retention",
  "deletion_mechanism",
];

const VALID_DATA_CLASSES = ["public", "internal", "confidential", "restricted"];

function loadDataMap(): DataMap {
  return JSON.parse(readFileSync(DATA_MAP_PATH, "utf-8")) as DataMap;
}

describe("data_map.json", () => {
  test("exists, parses, and has at least one store per required category", () => {
    const map = loadDataMap();
    expect(Array.isArray(map.stores)).toBe(true);
    expect(map.stores.length).toBeGreaterThanOrEqual(REQUIRED_CATEGORIES.length);
  });

  test("covers every full-lifecycle category", () => {
    const map = loadDataMap();
    const categories = new Set(map.stores.map((s) => s.category));
    const missing = REQUIRED_CATEGORIES.filter((c) => !categories.has(c));
    expect(missing).toEqual([]);
  });

  test("every store has real governance decisions", () => {
    const map = loadDataMap();
    for (const store of map.stores) {
      for (const key of REQUIRED_KEYS) {
        expect(store).toHaveProperty(key);
      }
      for (const key of [
        "owner",
        "purpose",
        "retention",
        "deletion_mechanism",
      ] as const) {
        expect(store[key].trim().length).toBeGreaterThan(0);
      }
      expect(VALID_DATA_CLASSES).toContain(store.data_class);
    }
  });

  test("store ids are unique", () => {
    const map = loadDataMap();
    const ids = map.stores.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  test("declares it is not legal advice", () => {
    expect(loadDataMap().not_legal_advice).toBe(true);
  });
});
