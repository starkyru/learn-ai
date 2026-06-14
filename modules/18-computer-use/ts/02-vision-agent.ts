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
 * Take a PNG screenshot of the current page and return it as a base64 string.
 *
 *   const buf = await page.screenshot({ type: "png" });
 *   return buf.toString("base64");
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
 * Send the screenshot to GPT-4o-mini and parse the JSON action.
 *
 * Build a multimodal message (same pattern as module 09 task 3):
 *   messages = [
 *     { role: "system", content: SYSTEM_PROMPT.replace("{goal}", goal) },
 *     { role: "user", content: [
 *         { type: "text", text: `Step ${step}. Goal: ${goal}` },
 *         { type: "image_url", image_url: { url: `data:image/png;base64,${b64}` } },
 *     ]},
 *   ]
 *   const response = await client.chat.completions.create({
 *       model, messages, max_tokens: 256,
 *       response_format: { type: "json_object" },
 *   });
 *   return parseAction(JSON.parse(response.choices[0].message.content!));
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
 * Send the screenshot to Claude and parse the JSON action.
 *
 *   const message = await client.messages.create({
 *       model, max_tokens: 256,
 *       system: SYSTEM_PROMPT.replace("{goal}", goal),
 *       messages: [{ role: "user", content: [
 *           { type: "image", source: { type: "base64", media_type: "image/png", data: b64 } },
 *           { type: "text", text: `Step ${step}. What is your next action?` },
 *       ]}],
 *   });
 *   const raw = (message.content[0] as any).text;
 *   return parseAction(JSON.parse(raw));
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
 * Convert a raw JSON object from the LLM to a typed Action.
 *
 *   switch (data.action) {
 *     case "click":    return { type: "click", x: data.x, y: data.y, description: data.description };
 *     case "type":     return { type: "type", text: data.text };
 *     case "navigate": return { type: "navigate", url: data.url };
 *     case "scroll":   return { type: "scroll", direction: data.direction, amount: data.amount ?? 300 };
 *     case "done":     return { type: "done", answer: data.answer };
 *     default: throw new Error(`Unknown action: ${data.action}`);
 *   }
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
 * Execute an Action on the Playwright page. Return an observation string.
 *
 *   switch (action.type) {
 *     case "click":    await page.mouse.click(action.x, action.y); return `Clicked (${action.x},${action.y})`;
 *     case "type":     await page.keyboard.type(action.text); return `Typed: ${action.text}`;
 *     case "navigate": await page.goto(action.url, { waitUntil: "domcontentloaded" }); return `Navigated to ${action.url}`;
 *     case "scroll":   await page.mouse.wheel(0, action.direction === "down" ? (action.amount ?? 300) : -(action.amount ?? 300));
 *                      return `Scrolled ${action.direction}`;
 *     case "done":     return `Done: ${action.answer}`;
 *   }
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
 * Loop until ActionDone or MAX_STEPS:
 *   a) b64 = await pageScreenshotBase64(page)
 *   b) Save debug screenshot to ASSETS_DIR/step_NN.png
 *   c) action = await decideFn(b64, goal, step)
 *   d) console.log the action
 *   e) If action.type === "done": close browser, return action.answer
 *   f) obs = await executeAction(page, action)
 *   g) await page.waitForLoadState("domcontentloaded")
 *   h) console.log obs
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
