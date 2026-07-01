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
 * Hints — apply these transforms in order (a `.replace(regex, ...)` per step):
 *   1. ATX heading markers: strip the leading "#" run + space at line start,
 *      keeping the heading text (use a multiline anchor).
 *   2. Bold/italic emphasis: unwrap paired `**`, `__`, `*`, `_`, keeping the
 *      inner text (a back-reference lets you match the same delimiter on both
 *      sides).
 *   3. Inline code: drop the surrounding backticks, keep the code text.
 *   4. Fenced code blocks (``` ... ```): remove them entirely.
 *   5. Markdown table rows (lines with "|"): keep only the cell text — remove the
 *      "|" characters and collapse the whitespace.
 *   6. Links `[text](url)`: keep just the link text.
 *   7. Return the cleaned string.
 */
export function stripMarkdownSyntax(text: string): string {
  // TODO: implement stripMarkdownSyntax().
  throw new Error("TODO: implement stripMarkdownSyntax()");
}

/**
 * Normalise whitespace: collapse runs of spaces/tabs and trim excess blank lines.
 *
 * Hints:
 *   - Normalise line endings to "\n" first (handle both \r\n and lone \r).
 *   - Collapse each line's horizontal whitespace (spaces/tabs) to a single space
 *     and trim its ends.
 *   - Cap vertical whitespace: collapse runs of 3+ blank lines down to 2.
 *   - Return the trimmed result.
 */
export function collapseWhitespace(text: string): string {
  // TODO: implement collapseWhitespace().
  throw new Error("TODO: implement collapseWhitespace()");
}

/**
 * Heuristically drop lines that are likely navigation or boilerplate.
 *
 * Hints — drop a line if ANY of these signals fire (keep everything else):
 *   - It is shorter than `minChars` AND looks like a menu label (all-caps or
 *     title-case), e.g. "HOME", "About Us".
 *   - It looks like a nav strip: short (say < 60 chars) and made only of words
 *     plus separator glyphs like "|", "/", or bullet dashes.
 *   - It is a pure horizontal rule (a short line of only -, =, *, or _).
 *   - It starts with a common footer word: "Cookie", "Privacy", "Terms".
 *
 * Return the surviving lines joined with "\n".
 */
export function removeBoilerplateLines(text: string, minChars = 20): string {
  // TODO: implement removeBoilerplateLines().
  throw new Error("TODO: implement removeBoilerplateLines()");
}

/**
 * Compute a shingle fingerprint for near-duplicate detection.
 *
 * Hints:
 *   - Tokenise the lowercased text into words.
 *   - Form the shingles: every window of `n` consecutive words joined into one
 *     string (slide the window one word at a time across the token list).
 *   - Collect them into a `Set<string>` — the shingle strings themselves work
 *     fine as keys here (no fixed-width hash needed for this exercise).
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
 * Hints — a greedy one-pass dedupe:
 *   - Walk the blocks in order, keeping the fingerprint sets you've accepted.
 *   - For each new block, compute its `fingerprint(...)` and its Jaccard
 *     similarity against every accepted set:
 *         jaccard(A, B) = |A ∩ B| / |A ∪ B|
 *   - If it's a near-duplicate of any accepted block (max Jaccard >=
 *     `similarityThreshold`), skip it; otherwise accept it.
 *   - Return the accepted blocks in their original order.
 *
 * Tip: very short blocks (< ~10 words) have unreliable shingle overlap — always
 * keep them.
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
 * Hints — chain the helpers above in a sensible order:
 *   - Markdown documents need `stripMarkdownSyntax()` first; other formats had
 *     their boilerplate stripped in task 1, so start from doc.text.
 *   - Run the text through `collapseWhitespace()` and `removeBoilerplateLines()`.
 *   - Split into paragraph blocks (on blank-line boundaries), pass them through
 *     `dedupeBlocks()`, and rejoin them.
 *   - Return a `CleanedDocument` carrying the cleaned text and the original
 *     source/format/metadata.
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
