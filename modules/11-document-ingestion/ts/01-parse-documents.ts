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
 * TODO: implement this function.
 *
 * Steps:
 *   1. Read the file: `readFileSync(path, "utf-8")`.
 *   2. Extract the title from the first line matching /^# (.+)/.
 *   3. Return a Document with:
 *        text     = raw file content (cleaning happens in task 2)
 *        source   = path
 *        format   = "markdown"
 *        metadata = { title: <extracted title or basename> }
 */
export function parseMarkdown(path: string): Document {
  // TODO: implement parseMarkdown().
  throw new Error("TODO: implement parseMarkdown()");
}

/**
 * Parse an HTML file or URL using cheerio (preferred).
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Read/fetch the HTML as a string.
 *      - If path starts with "http", use `fetch()` (Node 18+): await fetch(url).text()
 *        Make the function async in that case, or use a sync HTTP call.
 *        For simplicity: read from disk for file paths, fetch for URLs.
 *   2. Load into cheerio: `const $ = cheerio.load(html)`.
 *   3. Remove boilerplate: $("nav, header, footer, script, style").remove().
 *   4. Extract title: $("title").text() || $("h1").first().text().
 *   5. Extract body text: $("body").text() — cheerio strips tags automatically.
 *   6. Return a Document with format="html".
 *
 * Import: `import * as cheerio from "cheerio"` (already in package.json).
 * Fallback if cheerio unavailable: use parseHtmlFallback().
 */
export function parseHtml(pathOrUrl: string): Document {
  // TODO: implement parseHtml() using cheerio.
  // Fallback: parseHtmlFallback(pathOrUrl)
  throw new Error("TODO: implement parseHtml()");
}

/**
 * Parse HTML using only Node stdlib (no cheerio) — less accurate, always available.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Read/fetch the HTML string.
 *   2. Strip <script>...</script> and <style>...</style> with regex.
 *   3. Strip all remaining tags: text.replace(/<[^>]+>/g, " ").
 *   4. Collapse runs of whitespace.
 *   5. Extract title via /<title>([^<]*)<\/title>/i.
 *   6. Return a Document with format="html".
 */
export function parseHtmlFallback(pathOrUrl: string): Document {
  // TODO: implement parseHtmlFallback().
  throw new Error("TODO: implement parseHtmlFallback()");
}

/**
 * Parse a PDF file using pdf-parse.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. `import pdfParse from "pdf-parse"` (dynamic import to handle missing dep).
 *   2. Read file as Buffer: `readFileSync(path)`.
 *   3. Await pdfParse(buffer) → { text, numpages, info }.
 *   4. Return a Document with:
 *        text     = parsed text
 *        format   = "pdf"
 *        metadata = { numPages: numpages, title: info?.Title || basename }
 *
 * Note: pdf-parse is async. Make this an async function and call it with await
 * in the harness.
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
