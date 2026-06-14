/**
 * Task 3 🟡 — Structure-aware chunking.
 *
 * Naive fixed-size chunking (from module 04) ignores document structure and can
 * split in the middle of a thought or, worse, separate a heading from its body.
 * Section-aware chunking respects document structure so each chunk is semantically
 * self-contained.
 *
 * What you'll learn:
 *   - Why chunk boundaries matter for retrieval quality
 *   - How to detect section boundaries from headings (Markdown H1/H2/H3)
 *   - Token-aware sizing: estimating tokens without a tokenizer (chars / 4)
 *   - Carrying metadata (source, section title) into each chunk
 *   - Side-by-side comparison: naive fixed-size vs. section-aware
 *
 * How to run:
 *   pnpm tsx modules/11-document-ingestion/ts/03-structure-chunking.ts
 */

import { parseDocument } from "./01-parse-documents.js";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// ---------------------------------------------------------------------------
// Chunk type
// ---------------------------------------------------------------------------

export interface Chunk {
  id: string;
  text: string;
  source: string;
  metadata: {
    section?: string;
    estimatedTokens: number;
    [key: string]: unknown;
  };
}

// ---------------------------------------------------------------------------
// Token estimation
// ---------------------------------------------------------------------------

/** Rough token count: chars / 4. Approximates GPT-family ratio for English. */
export function estimateTokens(text: string): number {
  return Math.max(1, Math.floor(text.length / 4));
}

// ---------------------------------------------------------------------------
// Chunkers
// ---------------------------------------------------------------------------

/**
 * Naive fixed-size chunker — reproduced from module 04 for comparison.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Split text on whitespace into words.
 *   2. Accumulate words. When the running chunk would exceed maxTokens * 4 chars,
 *      emit a Chunk and slide forward by (maxTokens - overlapTokens) * 4 chars
 *      worth of words.
 *   3. id = `${source}-naive-${index}` (0-based).
 *   4. metadata.estimatedTokens = estimateTokens(chunkText).
 *   5. Return the list.
 */
export function naiveFixedSizeChunks(
  text: string,
  source: string,
  maxTokens = 200,
  overlapTokens = 20
): Chunk[] {
  // TODO: implement naiveFixedSizeChunks().
  throw new Error("TODO: implement naiveFixedSizeChunks()");
}

/**
 * Section-aware chunker: split first by Markdown headings, then sub-chunk any
 * section that is too large.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Split the document into (heading, body) pairs:
 *      - Scan line by line for /^(#{1,3})\s+(.+)/ matches.
 *      - When a heading is found, start a new section.
 *      - Text before the first heading → section ("(preamble)", text).
 *   2. For each section:
 *      a. If estimateTokens(heading + body) <= maxTokens: emit one Chunk.
 *      b. Otherwise: sub-chunk the body with naiveFixedSizeChunks(), then
 *         prepend the heading text to each sub-chunk so the section title
 *         is always present in context.
 *   3. id = `${source}-section-${sectionIdx}-${subIdx}`.
 *   4. metadata = { section: headingText, estimatedTokens: estimateTokens(...) }.
 *   5. Return the list.
 */
export function sectionChunks(
  text: string,
  source: string,
  maxTokens = 300,
  overlapTokens = 30
): Chunk[] {
  // TODO: implement sectionChunks().
  throw new Error("TODO: implement sectionChunks()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SAMPLE_DIR = join(__dirname, "..", "sample_docs");

async function main() {
  const mdPath = join(SAMPLE_DIR, "intro_to_rag.md");
  const doc = await parseDocument(mdPath);
  const text = doc.text;

  console.log(`\nDocument: ${mdPath}`);
  console.log(
    `  Total chars: ${text.length}  |  Estimated tokens: ${estimateTokens(text)}\n`
  );

  const naive = naiveFixedSizeChunks(text, mdPath, 200);
  const sectioned = sectionChunks(text, mdPath, 200);

  console.log(`Naive fixed-size : ${naive.length} chunks`);
  for (const c of naive) {
    console.log(
      `  [${c.id}] ~${c.metadata.estimatedTokens}t  ` +
        `— ${c.text.slice(0, 60).replace(/\n/g, " ")}...`
    );
  }

  console.log(`\nSection-aware    : ${sectioned.length} chunks`);
  for (const c of sectioned) {
    const section = c.metadata.section ?? "(preamble)";
    console.log(
      `  [${c.id}] §"${section}" ~${c.metadata.estimatedTokens}t  ` +
        `— ${c.text.slice(0, 60).replace(/\n/g, " ")}...`
    );
  }

  console.log(
    "\nKey observation: section-aware chunks have meaningful section titles " +
      "in metadata and never split a heading from its body."
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
