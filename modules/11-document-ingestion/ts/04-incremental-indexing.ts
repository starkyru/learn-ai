/**
 * Task 4 🟢 — Incremental indexing.
 *
 * Re-embedding every document on every pipeline run is wasteful and slow.
 * Incremental indexing hashes each document's content, tracks which hashes
 * have already been embedded, and only re-embeds documents that changed or
 * are new.
 *
 * What you'll learn:
 *   - Content-addressable storage: hash → no change → skip embedding
 *   - A simple on-disk manifest (JSON) to track ingested document hashes
 *   - Freshness: what to do when a document is deleted or renamed
 *   - How this pattern works at production scale (e.g. with Qdrant upserts)
 *
 * How to run:
 *   pnpm tsx modules/11-document-ingestion/ts/04-incremental-indexing.ts
 *
 * Run twice: the second run should report 0 new / 0 changed.
 */

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider } from "@learn-ai/llm-core";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SAMPLE_DIR = join(__dirname, "..", "sample_docs");
const MANIFEST_PATH = join(__dirname, "..", ".index_manifest.json");

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ManifestEntry {
  source: string;
  contentHash: string;
  ingestedAt: string;    // ISO-8601
  numChunks: number;
  model: string;
}

interface IndexedChunk {
  id: string;
  text: string;
  source: string;
  vector: number[];
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Manifest helpers
// ---------------------------------------------------------------------------

/**
 * Load the manifest from disk.
 *
 * Hints:
 *   - If MANIFEST_PATH doesn't exist yet (first run), return an empty object.
 *   - Otherwise read and JSON-parse it, returning the result typed as
 *     `Record<string, ManifestEntry>`.
 */
function loadManifest(): Record<string, ManifestEntry> {
  // TODO: implement loadManifest().
  throw new Error("TODO: implement loadManifest()");
}

/**
 * Persist the manifest to disk as JSON.
 *
 * Hints:
 *   - Serialise the mapping to indented JSON and write it to MANIFEST_PATH.
 */
function saveManifest(manifest: Record<string, ManifestEntry>): void {
  // TODO: implement saveManifest().
  throw new Error("TODO: implement saveManifest()");
}

// ---------------------------------------------------------------------------
// Content hashing
// ---------------------------------------------------------------------------

/**
 * Return a short SHA-256 hex digest of the document text.
 *
 * Hints:
 *   - Feed the text through a SHA-256 hash (`createHash` from node:crypto) and
 *     take the hex digest.
 *   - Truncate to the first 16 hex chars — enough for a change-detection key and
 *     keeps the manifest readable.
 */
function contentHash(text: string): string {
  // TODO: implement contentHash().
  throw new Error("TODO: implement contentHash()");
}

// ---------------------------------------------------------------------------
// Chunker (simplified)
// ---------------------------------------------------------------------------

/** Split text into word-bounded chunks of at most maxWords words. */
function simpleChunks(text: string, source: string, maxWords = 150): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const chunks: string[] = [];
  for (let i = 0; i < words.length; i += maxWords) {
    chunks.push(words.slice(i, i + maxWords).join(" "));
  }
  return chunks.filter((c) => c.trim().length > 0);
}

// ---------------------------------------------------------------------------
// Incremental indexer
// ---------------------------------------------------------------------------

/**
 * Ingest a list of file paths, skipping unchanged ones.
 *
 * Returns the tally `{ newCount, changedCount, skippedCount }`.
 *
 * Hints — loop over each path and let the content hash decide the work:
 *   - Read the file text and compute its `contentHash(...)`.
 *   - Compare against the manifest entry for that path (if any):
 *       * same hash  → nothing changed: bump `skippedCount` and move on WITHOUT
 *         re-embedding (that's the whole point — save the API call).
 *       * different hash → count it as changed (fall through to re-embed).
 *       * no entry → count it as new (fall through to embed).
 *   - For new/changed docs: split with `simpleChunks(text, path)`, embed the
 *     whole batch in ONE `await provider.embed(...)` call, wrap each result in an
 *     `IndexedChunk`, and push to `inMemoryIndex`.
 *   - Write a fresh manifest entry back for that path: its source, the new hash, a
 *     current ISO timestamp (`new Date().toISOString()`), the chunk count, and the
 *     provider's embed model.
 *   - Return the three counts.
 */
async function ingestDocuments(
  paths: string[],
  provider: ReturnType<typeof getProvider>,
  manifest: Record<string, ManifestEntry>,
  inMemoryIndex: IndexedChunk[]
): Promise<{ newCount: number; changedCount: number; skippedCount: number }> {
  // TODO: implement ingestDocuments().
  throw new Error("TODO: implement ingestDocuments()");
}

/**
 * Remove manifest entries for documents that no longer exist on disk.
 *
 * Hints:
 *   - Find the manifest keys that are absent from `currentPaths` — those docs were
 *     deleted or renamed.
 *   - Delete each from the manifest (mutate it in place) and return the removed
 *     source paths.
 */
function removeStaleEntries(
  manifest: Record<string, ManifestEntry>,
  currentPaths: string[]
): string[] {
  // TODO: implement removeStaleEntries().
  throw new Error("TODO: implement removeStaleEntries()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const provider = getProvider();
  console.log(`\nProvider: ${provider.name}  |  Embed model: ${provider.embedModel}\n`);

  const paths = [
    join(SAMPLE_DIR, "intro_to_rag.md"),
    join(SAMPLE_DIR, "vector_databases.html"),
  ].filter((p) => existsSync(p));

  if (paths.length === 0) {
    console.log("No sample files found. Make sure sample_docs/ exists.");
    return;
  }

  const manifest = loadManifest();
  const index: IndexedChunk[] = [];

  console.log(`[Run 1] Ingesting ${paths.length} documents...`);
  const r1 = await ingestDocuments(paths, provider, manifest, index);
  saveManifest(manifest);
  console.log(`  New: ${r1.newCount}  |  Changed: ${r1.changedCount}  |  Skipped: ${r1.skippedCount}`);
  console.log(`  Index size: ${index.length} chunks`);

  console.log(`\n[Run 2] Re-running with same files (should skip all)...`);
  const index2: IndexedChunk[] = [];
  const r2 = await ingestDocuments(paths, provider, manifest, index2);
  saveManifest(manifest);
  console.log(`  New: ${r2.newCount}  |  Changed: ${r2.changedCount}  |  Skipped: ${r2.skippedCount}`);
  if (r2.skippedCount !== paths.length) {
    console.warn("  WARNING: expected all docs to be skipped on second run");
  }

  const stale = removeStaleEntries(manifest, paths);
  console.log(stale.length > 0 ? `\n  Removed stale: ${stale}` : "\n  No stale entries.");

  console.log(`\nManifest saved to: ${MANIFEST_PATH}`);
  console.log("Key insight: only changed or new docs get re-embedded — saves API costs.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
