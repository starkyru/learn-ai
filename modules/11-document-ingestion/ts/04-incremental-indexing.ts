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
 * TODO: implement this function.
 *
 * Steps:
 *   1. If MANIFEST_PATH does not exist, return {}.
 *   2. Read JSON: JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")).
 *   3. Return the parsed object typed as Record<string, ManifestEntry>.
 */
function loadManifest(): Record<string, ManifestEntry> {
  // TODO: implement loadManifest().
  throw new Error("TODO: implement loadManifest()");
}

/**
 * Persist the manifest to disk as JSON.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Serialise to JSON with JSON.stringify(manifest, null, 2).
 *   2. writeFileSync(MANIFEST_PATH, json, "utf-8").
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
 * TODO: implement this function.
 *
 * Steps:
 *   1. createHash("sha256").update(text, "utf-8").digest("hex").
 *   2. Return the first 16 characters.
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
 * TODO: implement this function.
 *
 * Returns { newCount, changedCount, skippedCount }.
 *
 * Algorithm for each path:
 *   1. Read file text: readFileSync(path, "utf-8").
 *   2. Compute hash = contentHash(text).
 *   3. Look up path in manifest:
 *      - Present & hash matches → skippedCount++; continue.
 *      - Present & hash differs → changedCount++ (will re-embed).
 *      - Absent               → newCount++.
 *   4. Chunk the text: simpleChunks(text, path).
 *   5. Embed all chunks: await provider.embed(chunks).
 *   6. Build IndexedChunk objects, push to inMemoryIndex.
 *   7. Update manifest[path] = { source, contentHash: hash,
 *        ingestedAt: new Date().toISOString(), numChunks, model }.
 *   8. Return the counts.
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
 * TODO: implement this function.
 *
 * Steps:
 *   1. Find keys in manifest that are NOT in currentPaths.
 *   2. Delete them from manifest.
 *   3. Return the list of removed source paths.
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
