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
 * Get the snapshot via `await page.accessibility.snapshot()` (a nested tree of nodes
 * with role/name, optional url/value, and children — or null when empty). Write a
 * recursive `walk` that appends one indented line per meaningful node:
 *   - Noise roles ("none" / "presentation" / "generic") emit no line: recurse into
 *     their children WITHOUT indenting further.
 *   - Otherwise push a `[role] "name"` line (indent by depth), appending ` href=...`
 *     / ` value=...` when those fields exist, then recurse into children at depth+1.
 * Join the lines with newlines, or return a "(no accessible content)" fallback.
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
 * Use llm-core (text-in, JSON-out — no images). Get the provider with `getProvider()`
 * and build a `ChatMessage[]`: a system message carrying
 * `SYSTEM_PROMPT.replace("{goal}", goal)`, and a user message that embeds the step
 * number and the `a11yText`, asking for the next action. Call `llm.chat([...])`, then
 * `JSON.parse` the result text and pass it to `parseAction(...)`. Wrap that in a
 * try/catch so a parse failure degrades to a "done" action whose answer reports the
 * error and the raw text.
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
 * Switch on `data.action` and return the matching `Action` variant, reading each
 * field off `data`. The five action strings map to click_selector / click_text /
 * fill / navigate / done. Throw for an unknown action string.
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
 * Switch on `action.type` and drive Playwright, returning a short observation string:
 *   - "click_selector" -> locate by CSS selector and click the first match
 *     (`page.locator(...).first().click()`)
 *   - "click_text"     -> locate by visible text and click the first match
 *     (`page.getByText(..., { exact: false })`)
 *   - "fill"           -> locate by selector and `.fill(value)`
 *   - "navigate"       -> `page.goto(url, { waitUntil: "domcontentloaded" })`
 *   - "done"           -> no browser call; report the answer
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
 * Launch chromium (viewport 1280x720) and navigate to startUrl. Loop up to maxSteps:
 *   - extract the a11y tree text and log the step number plus a short preview,
 *   - ask decideAction(...) for the next action and log it,
 *   - when it is a "done" action, close the browser and return its answer,
 *   - otherwise execute it, wait for load to settle, and log the observation.
 * If the loop finishes without a "done", return a "max steps reached" message.
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
