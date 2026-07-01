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
 * Hints:
 *   - Work in words (split on whitespace) so you never cut mid-word.
 *   - Grow a window until adding the next word would push the chunk past the
 *     `maxTokens` budget — recall `estimateTokens`' chars/token ratio, so the
 *     char budget is roughly `maxTokens * 4`.
 *   - Emit a `Chunk`, then slide the window forward but leave `overlapTokens`
 *     worth of words behind so adjacent chunks share context.
 *   - Give each chunk a stable `id` like `${source}-naive-${index}` and set
 *     `metadata.estimatedTokens` from `estimateTokens(...)`.
 *   - Return the list.
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
 * Hints:
 *   - First break the document into sections keyed by heading. Scan the lines
 *     for Markdown ATX headings (levels H1–H3) and start a new section at each;
 *     capture each as (headingText, bodyText). Any text before the first heading
 *     is its own section — label it something like "(preamble)".
 *   - For each section, decide whether it fits: if `estimateTokens(heading +
 *     body)` is within `maxTokens`, emit it as a single `Chunk`. If it's too big,
 *     sub-chunk the body with `naiveFixedSizeChunks(...)` and prepend the heading
 *     text to every sub-chunk so the section title always travels with it.
 *   - Give chunks stable ids encoding both indices (e.g.
 *     `${source}-section-${sectionIdx}-${subIdx}`), and store the section heading
 *     plus `estimateTokens(...)` in each chunk's metadata.
 *   - Return the list.
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
