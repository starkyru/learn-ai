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
    # TODO 1: Get the raw a11y snapshot.
    #   snapshot = page.accessibility.snapshot()
    #   # snapshot is a nested dict; None if the page has no accessible nodes.
    #
    # TODO 2: Walk the tree and emit lines.
    #   def _walk(node: dict, lines: list[str], depth: int = 0) -> None:
    #       role = node.get("role", "")
    #       name = node.get("name", "")
    #       # Skip noise roles
    #       if role in ("none", "presentation", "generic"):
    #           for child in node.get("children", []):
    #               _walk(child, lines, depth)
    #           return
    #       indent = "  " * depth
    #       line = f"{indent}[{role}] {name!r}"
    #       if "url" in node:
    #           line += f" href={node['url']}"
    #       if "value" in node:
    #           line += f" value={node['value']!r}"
    #       lines.append(line)
    #       for child in node.get("children", []):
    #           _walk(child, lines, depth + 1)
    #
    #   lines: list[str] = []
    #   if snapshot:
    #       _walk(snapshot, lines)
    #   return "\n".join(lines) or "(no accessible content)"
    raise NotImplementedError("TODO 1-2: implement extract_a11y_tree")


def extract_dom_summary(page) -> str:
    """Extract a simplified DOM summary as a fallback when the a11y tree is sparse.

    Returns a text list of headings, links, and form inputs.
    """
    # TODO 3 (stretch): Use page.evaluate() to run JS in the page and collect:
    #   - All heading texts (h1-h6)
    #   - All link texts + hrefs
    #   - All input names/types/placeholders
    #   Return a formatted string.
    #
    # Example JS:
    #   js = """() => {
    #       const headings = [...document.querySelectorAll('h1,h2,h3')].map(h => h.innerText);
    #       const links = [...document.querySelectorAll('a')].map(a => ({text: a.innerText, href: a.href}));
    #       return { headings, links };
    #   }"""
    #   data = page.evaluate(js)
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

    # TODO 4: Call the LLM and parse the JSON response.
    #   Use llm.chat([system_msg, user_msg], options=ChatOptions(max_tokens=256))
    #   where system_msg has role="system" and content=SYSTEM_PROMPT.format(goal=goal).
    #   Parse the result.text as JSON and call _parse_action(data).
    #   If JSON parsing fails, return ActionDone(answer=f"Parse error: {result.text}")
    raise NotImplementedError("TODO 4: implement decide_action")


def _parse_action(data: dict) -> Action:
    """Convert a raw action dict from the LLM into a typed Action."""
    # TODO 5: Map data["action"] to the appropriate dataclass.
    #   "click_selector" -> ActionClickSelector(selector=data["selector"], description=...)
    #   "click_text"     -> ActionClickText(text=data["text"])
    #   "fill"           -> ActionFill(selector=data["selector"], value=data["value"])
    #   "navigate"       -> ActionNavigate(url=data["url"])
    #   "done"           -> ActionDone(answer=data["answer"])
    raise NotImplementedError("TODO 5: implement _parse_action")


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

def execute_action(page, action: Action) -> str:
    """Execute a text/selector-based action. Returns an observation string."""
    # TODO 6: Dispatch on action type.
    #   ActionClickSelector:
    #     page.locator(action.selector).first.click()
    #     return f"Clicked selector {action.selector!r}"
    #   ActionClickText:
    #     page.get_by_text(action.text, exact=False).first.click()
    #     return f"Clicked text {action.text!r}"
    #   ActionFill:
    #     page.locator(action.selector).fill(action.value)
    #     return f"Filled {action.selector!r} with {action.value!r}"
    #   ActionNavigate:
    #     page.goto(action.url, wait_until="domcontentloaded")
    #     return f"Navigated to {action.url}"
    #   ActionDone:
    #     return f"Done: {action.answer}"
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
            #   a) Extract a11y tree: a11y_text = extract_a11y_tree(page)
            #   b) Print step info and a11y preview.
            #   c) Decide action: action = decide_action(a11y_text, goal, step, provider)
            #   d) Print the action.
            #   e) If isinstance(action, ActionDone): browser.close(); return action.answer
            #   f) Execute: observation = execute_action(page, action)
            #   g) page.wait_for_load_state("domcontentloaded")
            #   h) Print observation.
            raise NotImplementedError("TODO 7: implement the DOM agent loop")

        browser.close()
        return "Max steps reached without a final answer."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    answer = run_dom_agent(AGENT_GOAL, START_URL)
    print(f"\nFinal answer: {answer}")

    # TODO 8 (stretch): Run both vision and DOM agents on the same goal.
    #   Compare: token cost (vision >> DOM), reliability, speed.
    #   from modules_18.task2 import run_vision_agent
    #   vision_answer = run_vision_agent(AGENT_GOAL, START_URL)
    #   print(f"Vision answer: {vision_answer}")


if __name__ == "__main__":
    main()
