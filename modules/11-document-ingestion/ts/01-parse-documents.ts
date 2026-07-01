/**
 * Task 1 🟢 — Parse documents.
 *
 * Extract text from PDF, HTML, and Markdown files into a normalized record
 * so downstream tasks can treat all formats identically.
 *
 * What you'll learn:
 *   - Why "read the file" is nontrivial for real-world document formats
 *   - How PDF layout breaks naive text extraction (columns, footers, tables)
 *   - How to strip HTML boilerplate so only body text reaches the LLM
 *   - The value of a single normalized schema across all formats
 *
 * How to run:
 *   pnpm tsx modules/11-document-ingestion/ts/01-parse-documents.ts
 *
 * npm deps (added to package.json):
 *   - pdf-parse   (PDF parsing)
 *   - cheerio     (HTML parsing)
 *
 * Install: pnpm install  (from the module ts/ dir or repo root with pnpm -r)
 */

import { readFileSync } from "node:fs";
import { extname } from "node:path";
import { URL } from "node:url";

// ---------------------------------------------------------------------------
// Normalized document record
// ---------------------------------------------------------------------------

export interface Document {
  text: string;
  source: string;                     // file path or URL
  format: "pdf" | "html" | "markdown";
  metadata: Record<string, unknown>;  // title, numPages, etc.
}

// ---------------------------------------------------------------------------
// Parser implementations
// ---------------------------------------------------------------------------

/**
 * Parse a Markdown file.
 *
 * Hints:
 *   - Read the whole file as a UTF-8 string (`readFileSync`).
 *   - Find a title: the text of the first H1 line ("# ..."); fall back to the
 *     file's basename when there is no H1.
 *   - Return a `Document`: the raw file content as `text` (cleaning is task 2),
 *     the path as `source`, `format` "markdown", and the title in `metadata`.
 */
export function parseMarkdown(path: string): Document {
  // TODO: implement parseMarkdown().
  throw new Error("TODO: implement parseMarkdown()");
}

/**
 * Parse an HTML file or URL using cheerio (preferred).
 *
 * Hints:
 *   - Get the HTML string: read it from disk for file paths, or fetch it for
 *     "http..." URLs.
 *   - Load it into cheerio (`cheerio.load(html)`) so you can query with CSS
 *     selectors.
 *   - Strip boilerplate by selecting the nav/header/footer/script/style elements
 *     and removing them from the tree.
 *   - Pick a title from the <title> element, falling back to the first <h1>.
 *   - Take the visible body text (cheerio's `.text()` drops the tags for you).
 *   - Return a `Document` with `format` "html" and the title in `metadata`.
 *
 * Import: `import * as cheerio from "cheerio"` (already in package.json).
 * Fallback if cheerio is unavailable: delegate to parseHtmlFallback().
 */
export function parseHtml(pathOrUrl: string): Document {
  // TODO: implement parseHtml() using cheerio.
  // Fallback: parseHtmlFallback(pathOrUrl)
  throw new Error("TODO: implement parseHtml()");
}

/**
 * Parse HTML using only Node stdlib (no cheerio) — less accurate, always available.
 *
 * Hints:
 *   - Read/fetch the HTML string (same source logic as parseHtml).
 *   - With regex replaces: first drop whole <script>...</script> and
 *     <style>...</style> blocks, then strip every remaining tag (replace with a
 *     space so words don't merge), then collapse the whitespace runs.
 *   - Extract the title from the <title>...</title> element.
 *   - Return a `Document` with `format` "html".
 */
export function parseHtmlFallback(pathOrUrl: string): Document {
  // TODO: implement parseHtmlFallback().
  throw new Error("TODO: implement parseHtmlFallback()");
}

/**
 * Parse a PDF file using pdf-parse.
 *
 * Hints:
 *   - Bring in pdf-parse with a dynamic `import(...)` so a missing dependency
 *     surfaces as a runtime error rather than a load-time crash.
 *   - Read the file as a Buffer and await the parser — it resolves to an object
 *     exposing the extracted `text`, the page count, and an `info` block.
 *   - Return a `Document` with `format` "pdf" and `metadata` carrying the page
 *     count and a title (the PDF info's title, or the file basename as fallback).
 *
 * Note: pdf-parse is async, hence this function is already `async`.
 */
export async function parsePdf(path: string): Promise<Document> {
  // TODO: implement parsePdf() using pdf-parse.
  throw new Error("TODO: implement parsePdf()");
}

// ---------------------------------------------------------------------------
// Unified entry point
// ---------------------------------------------------------------------------

/**
 * Detect document format from extension (or URL) and dispatch to the right parser.
 *
 * TODO: implement this function.
 *
 * Rules (case-insensitive extension):
 *   .pdf              → parsePdf()       (returns Promise<Document>)
 *   .html | .htm      → parseHtml()
 *   .md | .markdown   → parseMarkdown()
 *   starts with "http" → parseHtml() (assume HTML URL)
 *   otherwise          → throw new Error("Unsupported format: ...")
 *
 * Return type: Promise<Document> — wrap sync parsers with Promise.resolve().
 */
export async function parseDocument(pathOrUrl: string): Promise<Document> {
  // TODO: implement parseDocument().
  throw new Error("TODO: implement parseDocument()");
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
  const targets = [
    join(SAMPLE_DIR, "intro_to_rag.md"),
    join(SAMPLE_DIR, "vector_databases.html"),
  ];

  for (const target of targets) {
    console.log(`\n${"=".repeat(60)}`);
    console.log(`Parsing: ${target}`);
    const doc = await parseDocument(target);
    console.log(`  Format   : ${doc.format}`);
    console.log(`  Source   : ${doc.source}`);
    console.log(`  Metadata : ${JSON.stringify(doc.metadata)}`);
    console.log(`  Length   : ${doc.text.length} chars`);
    const preview = doc.text.slice(0, 300).replace(/\n/g, " ").trim();
    console.log(`  Preview  : ${preview}...`);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
