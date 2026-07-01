/**
 * 02-vision-agent.ts — Vision-grounded browser agent.  🟡
 *
 * What this teaches:
 *   A vision-grounded agent operates a browser by looking at screenshots.
 *   The loop:
 *     1. Take a screenshot of the current page.
 *     2. Send it to a multimodal LLM with the current goal.
 *     3. The LLM returns a JSON action: click(x,y), type, navigate, scroll, done.
 *     4. Execute the action with Playwright.
 *     5. Repeat until the goal is met or max steps reached.
 *
 *   Advantages of the vision approach:
 *     - Works on any page, including canvas-based and heavily JS-rendered ones.
 *     - No DOM parsing — the LLM interprets the visual layout.
 *     - Mirrors how Anthropic's computer-use API operates.
 *
 *   Disadvantages:
 *     - Expensive: screenshots encode as many tokens.
 *     - Pixel-coordinate clicks break when layout changes.
 *     - Slower per step than the DOM approach (task 3).
 *
 *   Uses raw OpenAI/Anthropic SDKs (not llm-core) — same reason as module 09
 *   task 3: llm-core is text-only; multimodal requires the vendor SDKs.
 *
 * How to run (from repo root):
 *   pnpm install && npx playwright install chromium
 *   pnpm tsx modules/18-computer-use/ts/02-vision-agent.ts
 *   LLM_PROVIDER=anthropic pnpm tsx modules/18-computer-use/ts/02-vision-agent.ts
 *
 * Env vars:
 *   OPENAI_API_KEY / ANTHROPIC_API_KEY
 *   LLM_PROVIDER      — "openai" (default) or "anthropic"
 *   BROWSER_HEADLESS  — "true" / "false"
 *   AGENT_GOAL        — (default: "Find the main heading on example.com")
 *   START_URL         — (default: https://example.com)
 *   AGENT_MAX_STEPS   — (default: 8)
 *
 * TS deps: playwright, openai, @anthropic-ai/sdk
 */

import "dotenv/config";
import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(__dirname, "../assets");

const HEADLESS = process.env.BROWSER_HEADLESS !== "false";
const AGENT_GOAL = process.env.AGENT_GOAL ?? "Find the main heading on example.com";
const START_URL = process.env.START_URL ?? "https://example.com";
const MAX_STEPS = parseInt(process.env.AGENT_MAX_STEPS ?? "8", 10);

// ---------------------------------------------------------------------------
// Action types
// ---------------------------------------------------------------------------

type Action =
  | { type: "click"; x: number; y: number; description?: string }
  | { type: "type"; text: string }
  | { type: "navigate"; url: string }
  | { type: "scroll"; direction: "up" | "down"; amount?: number }
  | { type: "done"; answer: string };

// ---------------------------------------------------------------------------
// Screenshot helper
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement pageScreenshotBase64.
 *
 * Take a PNG screenshot with `page.screenshot({ type: "png" })` — it resolves to a
 * Buffer. Convert that Buffer to a base64 string and return it.
 */
async function pageScreenshotBase64(page: any): Promise<string> {
  throw new Error("TODO 1: implement pageScreenshotBase64");
}

// ---------------------------------------------------------------------------
// LLM action decision
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `You are a browser agent. You see a screenshot of the current browser state.
Your goal: {goal}

Respond with a single JSON object describing your next action:
  {"action": "click",    "x": <int>, "y": <int>, "description": "<what you're clicking>"}
  {"action": "type",     "text": "<text to type>"}
  {"action": "navigate", "url": "<full URL>"}
  {"action": "scroll",   "direction": "up"|"down", "amount": 300}
  {"action": "done",     "answer": "<your final answer>"}

Rules:
- Only output valid JSON, nothing else.
- Use "done" when you have found the answer or cannot proceed.
- Prefer "navigate" over guessing coordinates for new pages.
- Viewport is 1280x720.`;

/**
 * TODO 2: Implement decideActionOpenAI.
 *
 * Construct an `OpenAI` client, then build a multimodal message array (module 09
 * task 3 pattern):
 *   - a system message carrying `SYSTEM_PROMPT.replace("{goal}", goal)`,
 *   - a user message whose `content` is a LIST mixing a text part (step + goal) and
 *     an image part `{ type: "image_url", image_url: { url: ... } }`, where the url
 *     is a `data:image/png;base64,<b64>` URI.
 * Call `client.chat.completions.create({ model, messages, max_tokens: ...,
 * response_format: { type: "json_object" } })`, then `JSON.parse` the first choice's
 * message content and hand the object to `parseAction(...)`.
 */
async function decideActionOpenAI(
  b64: string,
  goal: string,
  step: number
): Promise<Action> {
  throw new Error("TODO 2: implement decideActionOpenAI");
}

/**
 * TODO 3: Implement decideActionAnthropic.
 *
 * Same idea as TODO 2 but with the `Anthropic` SDK. Call
 * `client.messages.create({ model, max_tokens: ..., system, messages })` where:
 *   - `system` is the prompt formatted with the goal (Anthropic takes it as a
 *     top-level field, not a message),
 *   - the single user message's `content` is a list with an image part
 *     `{ type: "image", source: { type: "base64", media_type: "image/png", data: b64 } }`
 *     plus a text part asking for the next action.
 * Read the text off the first content block, `JSON.parse` it, and pass the object to
 * `parseAction(...)`.
 */
async function decideActionAnthropic(
  b64: string,
  goal: string,
  step: number
): Promise<Action> {
  throw new Error("TODO 3: implement decideActionAnthropic");
}

/**
 * TODO 4: Implement parseAction.
 *
 * Switch on `data.action` and return the matching typed `Action` variant, reading
 * each field off `data` (default the scroll amount when it is missing). The five
 * action strings map to the click / type / navigate / scroll / done variants of the
 * `Action` union. Throw for an unknown action string.
 */
function parseAction(data: Record<string, any>): Action {
  throw new Error("TODO 4: implement parseAction");
}

// ---------------------------------------------------------------------------
// Action execution
// ---------------------------------------------------------------------------

/**
 * TODO 5: Implement executeAction.
 *
 * Switch on `action.type` and drive Playwright, returning a short observation string:
 *   - "click"    -> `page.mouse.click(x, y)`
 *   - "type"     -> `page.keyboard.type(text)`
 *   - "navigate" -> `page.goto(url, { waitUntil: "domcontentloaded" })`
 *   - "scroll"   -> `page.mouse.wheel(0, dy)` where dy is +amount for "down" and
 *                   -amount for "up" (default the amount when absent)
 *   - "done"     -> no browser call; just report the answer
 */
async function executeAction(page: any, action: Action): Promise<string> {
  throw new Error("TODO 5: implement executeAction");
}

// ---------------------------------------------------------------------------
// Agent loop
// ---------------------------------------------------------------------------

/**
 * TODO 6: Implement runVisionAgent.
 *
 * Launch chromium (viewport 1280x720), navigate to startUrl, then pick the decide
 * function based on LLM_PROVIDER (anthropic -> decideActionAnthropic, else OpenAI).
 * Loop up to maxSteps:
 *   - capture the screenshot as base64 and also save a per-step debug PNG to ASSETS_DIR,
 *   - ask the chosen decide function for the next action and log it,
 *   - when it is a "done" action, close the browser and return its answer,
 *   - otherwise execute it, wait for load to settle, and log the observation.
 * If the loop finishes without a "done", return a "max steps reached" message.
 */
async function runVisionAgent(
  goal: string,
  startUrl: string,
  maxSteps: number = MAX_STEPS
): Promise<string> {
  throw new Error("TODO 6: implement runVisionAgent");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  fs.mkdirSync(ASSETS_DIR, { recursive: true });
  const answer = await runVisionAgent(AGENT_GOAL, START_URL);
  console.log(`\nFinal answer: ${answer}`);
}

main().catch(console.error);
