/**
 * Task 6 🟡 — Multimodal PDF retrieval.
 *
 * What you'll learn:
 *   - Tasks 1–5 extracted *digital text*. But real PDFs carry meaning the text
 *     layer loses: scanned pages, tables rendered as lines, charts, screenshots.
 *     `pdf-parse` returns nothing for those. You need to look at the *pixels*.
 *   - The multimodal-retrieval pattern: render each page to an IMAGE, ask a
 *     vision LLM to describe it (transcribe tables, read figures) → a text
 *     "caption", embed the caption, and retrieve by text similarity. At answer
 *     time you hand the matched page IMAGE back to the vision model, so
 *     generation reasons over pixels, not a lossy transcription. Retrieve by
 *     text, answer over the image.
 *   - Where @learn-ai/llm-core leaks: its provider `chat()` is TEXT-ONLY. Image
 *     inputs require the raw vendor SDK (openai / @anthropic-ai/sdk), exactly as
 *     in module 09 Task 3. Embeddings still go through `provider.embed()`.
 *
 * Page images: rendering a PDF → PNG needs native libs in Node, so the PNGs are
 * produced by the PYTHON side of this task. Run it once first:
 *   LLM_PROVIDER=openai uv run python modules/11-document-ingestion/py/06_multimodal_pdf.py
 * That writes sample_docs/pages/page_*.png, which this file then consumes.
 *
 * How to run (needs a vision-capable provider):
 *   LLM_PROVIDER=openai pnpm tsx modules/11-document-ingestion/ts/06-multimodal-pdf.ts
 *   LLM_PROVIDER=anthropic pnpm tsx modules/11-document-ingestion/ts/06-multimodal-pdf.ts
 *
 * Note: Anthropic has vision but no embeddings — set EMBED_PROVIDER=openai (or
 * ollama) when LLM_PROVIDER=anthropic.
 */

import "dotenv/config";
import { readFileSync, existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { getProvider, type ProviderName } from "@learn-ai/llm-core";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PAGES_DIR = path.join(__dirname, "..", "sample_docs", "pages");

const CAPTION_PROMPT =
  "You are transcribing a document page for a search index. Write a thorough " +
  "plain-text description of EVERYTHING on this page: headings, body text, and " +
  "especially any TABLE (transcribe every row and number) or figure. Do not " +
  "summarise away the numbers — a search query may ask for them.";

// ---------------------------------------------------------------------------
// Provided helpers
// ---------------------------------------------------------------------------

function listPages(): string[] {
  if (!existsSync(PAGES_DIR)) {
    throw new Error(
      `No page images in ${PAGES_DIR}. Render them once with the Python side:\n` +
        "  LLM_PROVIDER=openai uv run python modules/11-document-ingestion/py/06_multimodal_pdf.py",
    );
  }
  const pages = readdirSync(PAGES_DIR)
    .filter((f) => /^page_\d+\.png$/.test(f))
    .sort()
    .map((f) => path.join(PAGES_DIR, f));
  if (pages.length === 0)
    throw new Error(`No page_*.png in ${PAGES_DIR} — run the Python side first.`);
  return pages;
}

function imageToBase64(imagePath: string): string {
  return readFileSync(imagePath).toString("base64");
}

/** The vision call (raw vendor SDK — llm-core chat is text-only). Reused for
 *  captioning (index time) and answering (query time) by swapping the prompt. */
async function visionAsk(imagePath: string, prompt: string): Promise<string> {
  const provider = process.env.LLM_PROVIDER ?? "openai";
  const b64 = imageToBase64(imagePath);
  const mime = "image/png";

  if (provider === "openai") {
    const { default: OpenAI } = await import("openai");
    const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    const model = process.env.OPENAI_VISION_MODEL ?? "gpt-4o-mini";
    const resp = await client.chat.completions.create({
      model,
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            { type: "image_url", image_url: { url: `data:${mime};base64,${b64}` } },
          ],
        },
      ],
    });
    return resp.choices[0]?.message?.content ?? "";
  }

  if (provider === "anthropic") {
    const { default: Anthropic } = await import("@anthropic-ai/sdk");
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const model = process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5";
    const msg = await client.messages.create({
      model,
      max_tokens: 1024,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image",
              source: { type: "base64", media_type: "image/png", data: b64 },
            },
            { type: "text", text: prompt },
          ],
        },
      ],
    });
    const block = msg.content[0];
    return block.type === "text" ? block.text : "";
  }

  throw new Error(`Provider '${provider}' has no vision. Use openai or anthropic.`);
}

function embedder(): ReturnType<typeof getProvider> {
  let name = (process.env.EMBED_PROVIDER ||
    process.env.LLM_PROVIDER ||
    "openai") as ProviderName;
  if (name === "anthropic") name = "openai";
  return getProvider(name);
}

function cosine(a: number[], b: number[]): number {
  let dot = 0,
    ma = 0,
    mb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    ma += a[i] * a[i];
    mb += b[i] * b[i];
  }
  const d = Math.sqrt(ma) * Math.sqrt(mb);
  return d === 0 ? 0 : dot / d;
}

// ---------------------------------------------------------------------------
// The exercise — implement the multimodal retrieval flow
// ---------------------------------------------------------------------------

interface PageEntry {
  path: string;
  caption: string;
  vector: number[];
}
interface PageHit {
  path: string;
  caption: string;
  score: number;
}

/**
 * Caption each page image with the vision model, then embed the captions.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. For each page path, get a text caption with visionAsk(p, CAPTION_PROMPT).
 *   2. Embed ALL captions in one embedder.embed([...]) call.
 *   3. Return one PageEntry { path, caption, vector } per page, aligned by order.
 *
 * The vision call is the leaky-abstraction part (vendor SDK); embedding stays on
 * llm-core. This is the index-time cost, paid once.
 */
async function buildMultimodalIndex(
  pagePaths: string[],
  embed: ReturnType<typeof getProvider>,
): Promise<PageEntry[]> {
  throw new Error("TODO: implement buildMultimodalIndex()");
}

/**
 * Retrieve the top-k pages whose captions best match the query.
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Embed the query with embed.embed([query]).
 *   2. Score each PageEntry by cosine(queryVec, entry.vector).
 *   3. Return the top-k as PageHit sorted by score descending.
 */
async function retrievePages(
  query: string,
  index: PageEntry[],
  embed: ReturnType<typeof getProvider>,
  k = 2,
): Promise<PageHit[]> {
  throw new Error("TODO: implement retrievePages()");
}

/**
 * Answer the query by looking at the retrieved page IMAGE (not the caption).
 *
 * TODO: implement this function.
 *
 * Steps:
 *   1. Build an answer prompt telling the model to answer using ONLY what is
 *      visible on the page, and to say so if the page lacks the answer
 *      (interpolate query).
 *   2. Return visionAsk(pagePath, that_prompt).
 *
 * The payoff: we retrieved by text, but generate over the pixels, so numbers in
 * a table are read straight from the image.
 */
async function answerOverPage(query: string, pagePath: string): Promise<string> {
  throw new Error("TODO: implement answerOverPage()");
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

async function main() {
  const pagePaths = listPages();
  const embed = embedder();
  console.log(
    `Vision: ${process.env.LLM_PROVIDER ?? "openai"} | embed: ${embed.name}\n`,
  );

  console.log("Building multimodal index (captioning pages)…");
  const index = await buildMultimodalIndex(pagePaths, embed);
  console.log(`  indexed ${index.length} pages\n`);

  const queries = [
    "What was Q3 2024 revenue?", // answer lives in the TABLE (page 2)
    "How concentrated is the customer base?", // risk factors (page 3)
  ];
  for (const q of queries) {
    console.log(`Question: "${q}"`);
    const hits = await retrievePages(q, index, embed, 2);
    for (const h of hits)
      console.log(`  [${h.score.toFixed(4)}] ${path.basename(h.path)}`);
    const top = hits[0];
    console.log(`  → answering over ${path.basename(top.path)}:`);
    console.log(`    ${await answerOverPage(q, top.path)}\n`);
  }

  console.log("Reflection:");
  console.log("  1. Did the table question retrieve page_2 (the table page)?");
  console.log("  2. Would pdf-parse's text layer have captured those numbers?");
  console.log("  3. Why answer over the image instead of the caption text?");
}

main().catch((err) => {
  console.error(err.message ?? err);
  process.exit(1);
});
