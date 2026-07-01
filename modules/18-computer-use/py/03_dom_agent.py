"""03_dom_agent.py — DOM/accessibility-tree browser agent.  🟡

What this teaches:
    Task 2 used screenshots: the LLM sees pixels and guesses coordinates.
    This task uses the accessibility tree (a11y tree) instead: a structured
    representation of the page that exposes roles, labels, and values.

    The DOM/a11y approach:
      1. Extract the accessibility tree using page.accessibility.snapshot().
      2. Simplify the tree to a concise text representation.
      3. Send that text (not an image) to the LLM.
      4. The LLM picks an action by role/name/selector, not coordinates.
      5. Execute with Playwright using selectors or ARIA attributes.

    Advantages over vision (task 2):
      - Cheaper: text tokens instead of image tokens.
      - More stable: clicks by semantic role/label survive layout changes.
      - Works even when rendering is slow or the screenshot is cluttered.
      - Accessibility tree is what screen readers use — well-structured.

    Disadvantages:
      - Does not work on canvas-based UIs (games, PDF viewers, charts).
      - JavaScript-heavy sites sometimes have poor a11y trees.
      - Cannot see visual cues (colour, position) that influence decisions.

    DOM approach (alternative to a11y):
      - page.content() → full HTML → strip to important elements.
      - More verbose than the a11y tree; harder to parse.
      - Sometimes the only option for sites with no a11y support.

    When to use which:
      Vision  → canvas, games, legacy sites, Anthropic computer-use
      DOM/a11y → modern web apps, forms, structured content
      Hybrid  → try a11y first, fall back to vision if tree is empty

How to run (from repo root):
    uv sync --extra browser
    uv run playwright install chromium
    LLM_PROVIDER=openai   uv run python modules/18-computer-use/py/03_dom_agent.py
    LLM_PROVIDER=anthropic uv run python modules/18-computer-use/py/03_dom_agent.py

Environment variables:
    OPENAI_API_KEY / ANTHROPIC_API_KEY
    LLM_PROVIDER     — "openai" (default) or "anthropic"
    BROWSER_HEADLESS — "true" (default) or "false"
    AGENT_GOAL       — (default: "Find all links on example.com")
    START_URL        — (default: https://example.com)
    AGENT_MAX_STEPS  — (default: 8)

Python deps: playwright, openai or anthropic
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"
AGENT_GOAL = os.getenv("AGENT_GOAL", "Find all links on example.com")
START_URL = os.getenv("START_URL", "https://example.com")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))


# ---------------------------------------------------------------------------
# Action types (text/selector-based — no pixel coordinates)
# ---------------------------------------------------------------------------

@dataclass
class ActionClickSelector:
    selector: str          # CSS selector or aria role e.g. 'a[href*="more"]'
    description: str = ""

@dataclass
class ActionClickText:
    text: str              # Click the element whose visible text matches this
    description: str = ""

@dataclass
class ActionFill:
    selector: str
    value: str

@dataclass
class ActionNavigate:
    url: str

@dataclass
class ActionDone:
    answer: str

Action = ActionClickSelector | ActionClickText | ActionFill | ActionNavigate | ActionDone


# ---------------------------------------------------------------------------
# Accessibility tree extraction
# ---------------------------------------------------------------------------

def extract_a11y_tree(page) -> str:
    """Snapshot the accessibility tree and return a compact text representation.

    Returns a string like:
      [link] "More information..." href=/more
      [heading] "Example Domain"
      [paragraph] "This domain is for use in..."
    """
    # TODO 1: Get the raw a11y snapshot with `page.accessibility.snapshot()`. It is a
    #   nested dict (each node has "role", "name", optional "url"/"value", and
    #   "children"), or None when the page has no accessible nodes.
    #
    # TODO 2: Write a recursive helper that walks the tree and appends one indented
    #   line per meaningful node (indent by depth). For each node:
    #     - Roles like "none"/"presentation"/"generic" are noise: recurse into their
    #       children WITHOUT emitting a line or increasing depth.
    #     - Otherwise emit `[role] "name"` and append ` href=...` / ` value=...` when
    #       those keys are present, then recurse into children at depth+1.
    #   Join the collected lines with newlines; fall back to a "(no accessible content)"
    #   string when the snapshot is empty.
    raise NotImplementedError("TODO 1-2: implement extract_a11y_tree")


def extract_dom_summary(page) -> str:
    """Extract a simplified DOM summary as a fallback when the a11y tree is sparse.

    Returns a text list of headings, links, and form inputs.
    """
    # TODO 3 (stretch): Use `page.evaluate(js)` to run a JS function in the page that
    #   queries the DOM and returns a plain object of:
    #   - heading texts (h1-h6)
    #   - link texts + hrefs
    #   - input names/types/placeholders
    #   Then format that object into a readable text summary and return it.
    raise NotImplementedError("TODO 3: implement extract_dom_summary (optional)")


# ---------------------------------------------------------------------------
# LLM action decision (text-in, text-out — no images)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a browser agent that controls a web browser.
You receive the page's accessibility tree as text, not a screenshot.
Your goal: {goal}

Respond with a single JSON object describing your next action:
  {{"action": "click_selector", "selector": "<CSS or ARIA selector>", "description": "..."}}
  {{"action": "click_text",     "text": "<visible text of element to click>"}}
  {{"action": "fill",           "selector": "<input selector>", "value": "<text to type>"}}
  {{"action": "navigate",       "url": "<full URL>"}}
  {{"action": "done",           "answer": "<your final answer>"}}

Rules:
- Only output valid JSON, nothing else.
- Prefer click_text (more stable) over click_selector when the text is unique.
- Use "done" when you have the answer or cannot proceed.
- Base your decisions entirely on the accessibility tree provided.
"""


def decide_action(a11y_text: str, goal: str, step: int, provider: str) -> Action:
    """Ask an LLM to decide the next action based on the a11y tree text.

    No image involved — this is pure text in, structured JSON out.
    Works with any provider that supports JSON output.
    """
    from llm_core import ChatMessage, ChatOptions, get_provider  # noqa: PLC0415

    llm = get_provider(provider if provider in ("openai", "anthropic", "ollama", "nvidia") else None)

    prompt = (
        f"Step {step}. Accessibility tree:\n\n{a11y_text}\n\n"
        "What is your next action?"
    )

    # TODO 4: Build a `list[ChatMessage]`: a system message whose content is
    #   `SYSTEM_PROMPT.format(goal=goal)`, plus a user message carrying the `prompt`
    #   assembled above. Call `llm.chat(messages, options=ChatOptions(max_tokens=...))`.
    #   Try to `json.loads(result.text)` and pass the dict to `_parse_action(...)`;
    #   if parsing raises, degrade gracefully by returning an ActionDone whose answer
    #   reports the parse error and the raw text.
    raise NotImplementedError("TODO 4: implement decide_action")


def _parse_action(data: dict) -> Action:
    """Convert a raw action dict from the LLM into a typed Action."""
    # TODO 5: Branch on data["action"] and build the matching dataclass, reading each
    #   field from `data`. The five action strings map to ActionClickSelector /
    #   ActionClickText / ActionFill / ActionNavigate / ActionDone. Raise ValueError
    #   for anything unexpected.
    raise NotImplementedError("TODO 5: implement _parse_action")


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

def execute_action(page, action: Action) -> str:
    """Execute a text/selector-based action. Returns an observation string."""
    # TODO 6: Dispatch on the action type (isinstance) and drive Playwright:
    #   - ActionClickSelector -> locate by CSS selector and click the first match
    #     (`page.locator(...).first.click()`)
    #   - ActionClickText     -> locate by visible text and click the first match
    #     (`page.get_by_text(..., exact=False)`)
    #   - ActionFill          -> locate by selector and `.fill(value)`
    #   - ActionNavigate      -> `page.goto(url, wait_until="domcontentloaded")`
    #   - ActionDone          -> no browser call; report the answer
    #   Return a short observation string for each.
    raise NotImplementedError("TODO 6: implement execute_action")


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_dom_agent(goal: str, start_url: str, max_steps: int = MAX_STEPS) -> str:
    """Run a DOM/a11y-grounded browser agent.

    Returns the agent's final answer.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    provider = os.getenv("LLM_PROVIDER", "openai")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(start_url, wait_until="domcontentloaded")

        print(f"Goal      : {goal}")
        print(f"Provider  : {provider}")
        print(f"Max steps : {max_steps}\n")

        for step in range(1, max_steps + 1):
            # TODO 7: Implement the DOM agent loop.
            #   a) Extract the a11y tree text for the current page.
            #   b) Print the step number and a short preview of the tree.
            #   c) Ask the LLM for the next action via decide_action(...).
            #   d) Print the action so the run is traceable.
            #   e) When the action is an ActionDone, close the browser and return its answer.
            #   f) Otherwise execute it, wait for load to settle, and print the observation.
            raise NotImplementedError("TODO 7: implement the DOM agent loop")

        browser.close()
        return "Max steps reached without a final answer."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    answer = run_dom_agent(AGENT_GOAL, START_URL)
    print(f"\nFinal answer: {answer}")

    # TODO 8 (stretch): Import and run the vision agent from task 2 on the same goal,
    #   then compare the two runs on token cost (vision >> DOM), reliability, and speed.


if __name__ == "__main__":
    main()
