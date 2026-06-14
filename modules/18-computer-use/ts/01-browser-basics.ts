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
 * Navigate to a URL and return basic page info.
 *
 * Steps:
 *   import { chromium } from "playwright";
 *   const browser = await chromium.launch({ headless: HEADLESS });
 *   const page = await browser.newPage();
 *   await page.goto(url, { waitUntil: "domcontentloaded" });
 *
 *   const title = await page.title();
 *   const finalUrl = page.url();
 *   // Get visible body text (not raw HTML):
 *   const text = await page.locator("body").innerText();
 *   const linkCount = await page.locator("a").count();
 *
 *   await browser.close();
 *   return { title, url: finalUrl, text: text.slice(0, 1000), linkCount };
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
 * Navigate to a URL and save a full-page screenshot as PNG.
 * Returns the output file path.
 *
 *   await page.screenshot({ path: outputPath, fullPage: true });
 *   await browser.close();
 *   return outputPath;
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
 * Navigate to a URL, type a query into a search input, press Enter,
 * and return the result page title.
 *
 *   await page.locator(searchSelector).fill(query);
 *   await page.keyboard.press("Enter");
 *   await page.waitForLoadState("domcontentloaded");
 *   return page.title();
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
  // TODO 4: Call navigateAndRead(TARGET_URL) and print the result.
  throw new Error("TODO 4: call navigateAndRead and print results");

  // TODO 5: Call takeScreenshot and print where the file was saved.
  // console.log("\n=== Screenshot ===");
  // const saved = await takeScreenshot(TARGET_URL, SCREENSHOT_PATH);
  // console.log(`Saved to : ${saved}`);

  // TODO 6 (stretch): Call searchOnPage on DuckDuckGo.
  // const resultTitle = await searchOnPage(
  //   "https://duckduckgo.com",
  //   "input[name='q']",
  //   "model context protocol"
  // );
  // console.log(`\nSearch result page title: ${resultTitle}`);
}

main().catch(console.error);
