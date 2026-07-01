/**
 * 01-browser-basics.ts — Browser automation basics with Playwright.  🟢
 *
 * What this teaches:
 *   Playwright is a browser automation library that lets you control a real
 *   browser (Chromium, Firefox, WebKit) from TypeScript/JavaScript.
 *   You navigate pages, read content, fill forms, click, and take screenshots —
 *   all programmatically.
 *
 *   This is the foundation for the browser agents in tasks 2 and 3.
 *   Before the LLM can decide what to do, you need the machinery to execute
 *   actions and observe results.
 *
 *   Core Playwright concepts (TypeScript):
 *     Browser      — the browser instance (headless or headed)
 *     BrowserContext — isolated session (cookies, storage)
 *     Page         — one browser tab
 *
 *   Playwright Node API uses Promises; all browser operations are async.
 *
 * How to run (from repo root):
 *   pnpm install                                 # picks up playwright
 *   npx playwright install chromium              # downloads the browser
 *   pnpm tsx modules/18-computer-use/ts/01-browser-basics.ts
 *
 * Env vars:
 *   BROWSER_HEADLESS — "true" (default) or "false"
 *   TARGET_URL       — URL to navigate to (default: https://example.com)
 *
 * TS deps: playwright (in package.json)
 */

import "dotenv/config";
import * as path from "node:path";
import * as fs from "node:fs";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(__dirname, "../assets");

const HEADLESS = process.env.BROWSER_HEADLESS !== "false";
const TARGET_URL = process.env.TARGET_URL ?? "https://example.com";
const SCREENSHOT_PATH = path.join(ASSETS_DIR, "screenshot.png");

// ---------------------------------------------------------------------------
// Navigation and content extraction
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement navigateAndRead.
 *
 * Navigate to a URL and return basic page info. Every Playwright call is async.
 *
 * Steps:
 *   - Import `chromium` from "playwright", launch it with `{ headless: HEADLESS }`,
 *     open a new page, and `goto(url, { waitUntil: "domcontentloaded" })`.
 *   - Collect: the title, the final URL (after redirects), the visible body text
 *     (locate "body" and read its INNER TEXT, not raw HTML), and the count of "a"
 *     elements.
 *   - Close the browser and return the object below, truncating `text` to ~1000 chars:
 *     { title, url, text, linkCount }.
 */
async function navigateAndRead(url: string): Promise<{
  title: string;
  url: string;
  text: string;
  linkCount: number;
}> {
  throw new Error("TODO 1: implement navigateAndRead");
}

/**
 * TODO 2: Implement takeScreenshot.
 *
 * Open a browser and navigate to `url` as in TODO 1, then call
 * `page.screenshot(...)` with the output path and the full-page option enabled.
 * Close the browser and return outputPath.
 */
async function takeScreenshot(url: string, outputPath: string): Promise<string> {
  throw new Error("TODO 2: implement takeScreenshot");
}

// ---------------------------------------------------------------------------
// Element interaction
// ---------------------------------------------------------------------------

/**
 * TODO 3: Implement searchOnPage.
 *
 * Navigate to `url`, then:
 *   - locate the input via `searchSelector` and `.fill(query)` it,
 *   - submit by pressing Enter on the keyboard,
 *   - wait for the result page to load (`waitForLoadState("domcontentloaded")`),
 *   - return the resulting page title.
 *
 * Example: searchSelector="input[name='q']" for DuckDuckGo.
 */
async function searchOnPage(
  url: string,
  searchSelector: string,
  query: string
): Promise<string> {
  throw new Error("TODO 3: implement searchOnPage");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  fs.mkdirSync(ASSETS_DIR, { recursive: true });

  console.log(`URL      : ${TARGET_URL}`);
  console.log(`Headless : ${HEADLESS}\n`);

  console.log("=== navigateAndRead ===");
  // TODO 4: Await navigateAndRead(TARGET_URL) and print the fields it returns
  //   (title, url, linkCount, and a preview of text). Remove the throw below once done.
  throw new Error("TODO 4: call navigateAndRead and print results");

  // TODO 5: Await takeScreenshot(TARGET_URL, SCREENSHOT_PATH) and print where the
  //   file was saved.

  // TODO 6 (stretch): Await searchOnPage on DuckDuckGo (searchSelector "input[name='q']")
  //   with a query of your choice and print the resulting page title.
}

main().catch(console.error);
