/**
 * 03-dom-agent.ts — DOM/accessibility-tree browser agent.  🟡
 *
 * What this teaches:
 *   Task 2 used screenshots (pixels). This task uses the accessibility tree
 *   (a11y tree) instead: a structured, semantic representation of the page
 *   that the LLM can read as text.
 *
 *   The DOM/a11y loop:
 *     1. Snapshot the accessibility tree: page.accessibility.snapshot()
 *     2. Convert it to a compact text representation.
 *     3. Send the text to an LLM (text-in, JSON-action-out — no images!).
 *     4. The LLM picks an action by role/label, not pixel coordinates.
 *     5. Execute with Playwright selectors / ARIA locators.
 *
 *   Advantages over vision (task 2):
 *     - Cheaper: text tokens vs. image tokens (10-100x less)
 *     - More stable: element identity via roles/labels survives layout changes
 *     - Works with any LLM, including text-only ones
 *
 *   Disadvantages:
 *     - Fails on canvas-based UIs (games, charts, PDF viewers)
 *     - Some sites have poor a11y trees (sparse or missing roles)
 *     - Cannot see visual cues (colour, position)
 *
 *   When to use which:
 *     Vision  → canvas, games, legacy sites, Anthropic computer-use
 *     DOM/a11y → modern web apps, forms, structured content, cost-sensitive
 *     Hybrid  → try a11y first, fall back to vision if the tree is empty
 *
 *   Uses llm-core (text-in, text-out) — unlike task 2 which needs the vendor SDKs.
 *
 * How to run (from repo root):
 *   pnpm install && npx playwright install chromium
 *   pnpm tsx modules/18-computer-use/ts/03-dom-agent.ts
 *   LLM_PROVIDER=anthropic pnpm tsx modules/18-computer-use/ts/03-dom-agent.ts
 *
 * Env vars:
 *   LLM_PROVIDER     — any provider supported by llm-core
 *   BROWSER_HEADLESS — "true" / "false"
 *   AGENT_GOAL       — (default: "Find all links on example.com")
 *   START_URL        — (default: https://example.com)
 *   AGENT_MAX_STEPS  — (default: 8)
 *
 * TS deps: playwright, @learn-ai/llm-core
 */

import "dotenv/config";
import { getProvider } from "@learn-ai/llm-core";
import type { ChatMessage } from "@learn-ai/llm-core";

const HEADLESS = process.env.BROWSER_HEADLESS !== "false";
const AGENT_GOAL = process.env.AGENT_GOAL ?? "Find all links on example.com";
const START_URL = process.env.START_URL ?? "https://example.com";
const MAX_STEPS = parseInt(process.env.AGENT_MAX_STEPS ?? "8", 10);

// ---------------------------------------------------------------------------
// Action types (selector-based — no pixel coordinates)
// ---------------------------------------------------------------------------

type Action =
  | { type: "click_selector"; selector: string; description?: string }
  | { type: "click_text"; text: string; description?: string }
  | { type: "fill"; selector: string; value: string }
  | { type: "navigate"; url: string }
  | { type: "done"; answer: string };

// ---------------------------------------------------------------------------
// Accessibility tree extraction
// ---------------------------------------------------------------------------

/**
 * TODO 1: Implement extractA11yTree.
 *
 * Snapshot the page accessibility tree and return a compact text string.
 *
 *   const snapshot = await page.accessibility.snapshot();
 *
 *   function walk(node: any, lines: string[], depth = 0): void {
 *     const role = node.role ?? "";
 *     const name = node.name ?? "";
 *     if (["none", "presentation", "generic"].includes(role)) {
 *       (node.children ?? []).forEach((c: any) => walk(c, lines, depth));
 *       return;
 *     }
 *     const indent = "  ".repeat(depth);
 *     let line = `${indent}[${role}] ${JSON.stringify(name)}`;
 *     if (node.url)   line += ` href=${node.url}`;
 *     if (node.value !== undefined) line += ` value=${JSON.stringify(node.value)}`;
 *     lines.push(line);
 *     (node.children ?? []).forEach((c: any) => walk(c, lines, depth + 1));
 *   }
 *
 *   const lines: string[] = [];
 *   if (snapshot) walk(snapshot, lines);
 *   return lines.join("\n") || "(no accessible content)";
 */
async function extractA11yTree(page: any): Promise<string> {
  throw new Error("TODO 1: implement extractA11yTree");
}

// ---------------------------------------------------------------------------
// LLM action decision (text-in, JSON-out — uses llm-core)
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `You are a browser agent that controls a web browser.
You receive the page's accessibility tree as text, not a screenshot.
Your goal: {goal}

Respond with a single JSON object describing your next action:
  {"action": "click_selector", "selector": "<CSS or ARIA selector>", "description": "..."}
  {"action": "click_text",     "text": "<visible text of element to click>"}
  {"action": "fill",           "selector": "<input selector>", "value": "<text>"}
  {"action": "navigate",       "url": "<full URL>"}
  {"action": "done",           "answer": "<your final answer>"}

Rules:
- Only output valid JSON, nothing else.
- Prefer click_text (more stable) over click_selector when text is unique.
- Use "done" when you have the answer or cannot proceed.`;

/**
 * TODO 2: Implement decideAction.
 *
 * Use llm-core to decide the next action based on the a11y tree text.
 * No images — this is pure text in, structured JSON out.
 *
 *   const llm = getProvider();
 *   const system: ChatMessage = { role: "system", content: SYSTEM_PROMPT.replace("{goal}", goal) };
 *   const user: ChatMessage = {
 *       role: "user",
 *       content: `Step ${step}. Accessibility tree:\n\n${a11yText}\n\nWhat is your next action?`,
 *   };
 *   const result = await llm.chat([system, user]);
 *   try {
 *       return parseAction(JSON.parse(result.text));
 *   } catch {
 *       return { type: "done", answer: `Parse error: ${result.text}` };
 *   }
 */
async function decideAction(
  a11yText: string,
  goal: string,
  step: number
): Promise<Action> {
  throw new Error("TODO 2: implement decideAction");
}

/**
 * TODO 3: Implement parseAction.
 *
 *   switch (data.action) {
 *     case "click_selector": return { type: "click_selector", selector: data.selector, description: data.description };
 *     case "click_text":     return { type: "click_text", text: data.text };
 *     case "fill":           return { type: "fill", selector: data.selector, value: data.value };
 *     case "navigate":       return { type: "navigate", url: data.url };
 *     case "done":           return { type: "done", answer: data.answer };
 *     default: throw new Error(`Unknown action: ${data.action}`);
 *   }
 */
function parseAction(data: Record<string, any>): Action {
  throw new Error("TODO 3: implement parseAction");
}

// ---------------------------------------------------------------------------
// Action execution
// ---------------------------------------------------------------------------

/**
 * TODO 4: Implement executeAction.
 *
 * Execute an Action using Playwright selectors. Return an observation string.
 *
 *   case "click_selector":
 *     await page.locator(action.selector).first().click();
 *     return `Clicked selector ${action.selector}`;
 *   case "click_text":
 *     await page.getByText(action.text, { exact: false }).first().click();
 *     return `Clicked text "${action.text}"`;
 *   case "fill":
 *     await page.locator(action.selector).fill(action.value);
 *     return `Filled ${action.selector} with "${action.value}"`;
 *   case "navigate":
 *     await page.goto(action.url, { waitUntil: "domcontentloaded" });
 *     return `Navigated to ${action.url}`;
 *   case "done":
 *     return `Done: ${action.answer}`;
 */
async function executeAction(page: any, action: Action): Promise<string> {
  throw new Error("TODO 4: implement executeAction");
}

// ---------------------------------------------------------------------------
// Agent loop
// ---------------------------------------------------------------------------

/**
 * TODO 5: Implement runDomAgent.
 *
 * Loop until ActionDone or maxSteps:
 *   a) a11yText = await extractA11yTree(page)
 *   b) console.log step number and a11y preview (first 300 chars)
 *   c) action = await decideAction(a11yText, goal, step)
 *   d) console.log the action
 *   e) If action.type === "done": close browser, return action.answer
 *   f) obs = await executeAction(page, action)
 *   g) await page.waitForLoadState("domcontentloaded")
 *   h) console.log obs
 */
async function runDomAgent(
  goal: string,
  startUrl: string,
  maxSteps: number = MAX_STEPS
): Promise<string> {
  throw new Error("TODO 5: implement runDomAgent");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const answer = await runDomAgent(AGENT_GOAL, START_URL);
  console.log(`\nFinal answer: ${answer}`);
}

main().catch(console.error);
