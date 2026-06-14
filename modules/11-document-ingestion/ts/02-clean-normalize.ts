/**
 * Task 2 🟡 — Clean & normalize documents.
 *
 * Raw parsed text contains boilerplate, excessive whitespace, duplicate passages,
 * and noise from layout artifacts. Cleaning before chunking and embedding
 * dramatically improves retrieval quality.
 *
 * What you'll learn:
 *   - Why raw extraction is noisy (footers, menus, whitespace, encoding issues)
 *   - Simple heuristics for boilerplate removal (line-length, repetition rate)
 *   - Near-duplicate detection using shingle fingerprints
 *   - How table formatting degrades embedding quality vs. prose
 *
 * How to run:
 *   pnpm tsx modules/11-document-ingestion/ts/02-clean-normalize.ts
 */

import { parseDocument, type Document } from "./01-parse-documents.js";

// ---------------------------------------------------------------------------
// Cleaned document type
// ---------------------------------------------------------------------------

export interface CleanedDocument {
  text: string;
  source: string;
  format: string;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Cleaning functions
// ---------------------------------------------------------------------------

/**
 * Remove Markdown formatting characters, leaving prose.
 *
 * TODO: implement this function.
 *
 * Steps (apply in order):
 *   1. Remove ATX heading markers: replace /^#{1,6}\s+/gm with "".
 *      Keep the heading text — strip only the "#" characters.
 *   2. Remove bold/italic: replace **text**, __text__, *text*, _text_ with text.
 *      Use a regex like /(\*\*|__)(.*?)\1/g → "$2".
 *   3. Remove inline code backticks: /`([^`]+)`/g → "$1".
 *   4. Remove fenced code blocks: /```[\s\S]*?```/g → "".
 *   5. Remove Markdown table rows (lines with "|"): strip "|", collapse whitespace.
 *   6. Remove link syntax: /\[([^\]]+)\]\([^)]+\)/g → "$1".
 *   7. Return cleaned string.
 */
export function stripMarkdownSyntax(text: string): string {
  // TODO: implement stripMarkdownSyntax().
  throw new Error("TODO: implement stripMarkdownSyntax()");
}

/**
 * Normalise whitespace: collapse runs of spaces/tabs and trim excess blank lines.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Normalise line endings: replace /\r\n|\r/g with "\n".
 *   2. Collapse horizontal whitespace per line: replace /[ \t]+/g with " ".
 *   3. Trim each line.
 *   4. Collapse runs of 3+ blank lines to 2: replace /\n{3,}/g with "\n\n".
 *   5. Return trimmed result.
 */
export function collapseWhitespace(text: string): string {
  // TODO: implement collapseWhitespace().
  throw new Error("TODO: implement collapseWhitespace()");
}

/**
 * Heuristically drop lines that are likely navigation or boilerplate.
 *
 * TODO: implement this function.
 *
 * Heuristics — drop a line if ANY of these apply:
 *   - Length < minChars AND matches /^[A-Z\s]+$/ or /^[A-Z][a-z]+(\s[A-Z][a-z]+)*$/
 *     (all-caps or title-case nav items like "HOME", "About Us").
 *   - Only words + pipe/slash chars, length < 60:  /^[\w\s|/·•–—]+$/.test(line)
 *   - Pure horizontal rule: /^[-=*_]{3,}$/.test(line.trim()).
 *   - Starts with "Cookie" | "Privacy" | "Terms" (footer text).
 *
 * Return the filtered lines joined with "\n".
 */
export function removeBoilerplateLines(text: string, minChars = 20): string {
  // TODO: implement removeBoilerplateLines().
  throw new Error("TODO: implement removeBoilerplateLines()");
}

/**
 * Compute a shingle fingerprint for near-duplicate detection.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Tokenise: words = text.toLowerCase().split(/\s+/).filter(Boolean).
 *   2. Build n-gram shingles: words.slice(i, i+n).join(" ") for i in range.
 *   3. Hash each shingle with a simple hash (e.g. FNV-like or just the string itself
 *      — a Set<string> is fine for this exercise since we don't need a fixed bit size).
 *   4. Return a Set<string> of shingles (or short hashes).
 *
 * Used by dedupeBlocks() below.
 */
export function fingerprint(text: string, n = 5): Set<string> {
  // TODO: implement fingerprint().
  throw new Error("TODO: implement fingerprint()");
}

/**
 * Remove near-duplicate text blocks using Jaccard similarity of shingle sets.
 *
 * TODO: implement this function.
 *
 * Algorithm:
 *   1. For each block, compute fingerprint(block).
 *   2. Keep a list of accepted fingerprint sets.
 *   3. For a new block, compute Jaccard(A, B) = |A ∩ B| / |A ∪ B| against each accepted.
 *   4. If max Jaccard >= similarityThreshold, skip (near-duplicate).
 *   5. Otherwise accept.
 *   6. Return accepted blocks in original order.
 *
 * Tip: short blocks (< 10 words) are always kept (shingles unreliable).
 */
export function dedupeBlocks(
  blocks: string[],
  similarityThreshold = 0.8
): string[] {
  // TODO: implement dedupeBlocks().
  throw new Error("TODO: implement dedupeBlocks()");
}

// ---------------------------------------------------------------------------
// Main cleaner
// ---------------------------------------------------------------------------

/**
 * Run the full cleaning pipeline on a parsed Document.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. If format === "markdown": stripMarkdownSyntax(text).
 *      Otherwise: use text as-is (HTML boilerplate stripped in task 1).
 *   2. collapseWhitespace(text).
 *   3. removeBoilerplateLines(text).
 *   4. Split on "\n\n", run dedupeBlocks(), rejoin with "\n\n".
 *   5. Return CleanedDocument.
 */
export function clean(doc: Document): CleanedDocument {
  // TODO: implement clean().
  throw new Error("TODO: implement clean()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SAMPLE_DIR = join(__dirname, "..", "sample_docs");

async function main() {
  const files = ["intro_to_rag.md", "vector_databases.html"];

  for (const filename of files) {
    const path = join(SAMPLE_DIR, filename);
    console.log(`\n${"=".repeat(60)}`);
    console.log(`Cleaning: ${path}`);

    const raw = await parseDocument(path);
    console.log(`  Raw length  : ${raw.text.length} chars`);

    const cleaned = clean(raw);
    console.log(`  Clean length: ${cleaned.text.length} chars`);
    const reduction = 100 * (1 - cleaned.text.length / Math.max(raw.text.length, 1));
    console.log(`  Reduction   : ${reduction.toFixed(1)}%`);
    const preview = cleaned.text.slice(0, 300).replace(/\n/g, " ").trim();
    console.log(`  Preview     : ${preview}...`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
