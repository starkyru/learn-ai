"""02_vision_agent.py — Vision-grounded browser agent.  🟡

What this teaches:
    A vision-grounded agent operates a browser by looking at screenshots.
    The loop is:
      1. Take a screenshot of the current page.
      2. Send the screenshot to a multimodal LLM with the current goal.
      3. The LLM returns an action: click (x, y), type text, scroll, navigate, done.
      4. Execute the action with Playwright.
      5. Repeat until goal is met or max steps reached.

    This mirrors human browsing: you see the screen, decide what to click,
    then check whether it worked. The LLM is the "vision" layer.

    Advantages of the vision approach:
      - Works on any page, including highly dynamic JS-rendered pages.
      - No need to parse the DOM or understand the page structure.
      - Matches how Anthropic's computer-use API works.

    Disadvantages:
      - Expensive: a screenshot is many tokens (resized or tiled).
      - Fragile at pixel coordinates: small layout changes break coordinate-based clicks.
      - Slower: every step needs an LLM call + screenshot.

    Compare to Task 3 (DOM/accessibility agent):
      Vision:       screenshot → LLM picks coordinates
      DOM/a11y:     accessibility tree → LLM picks selector/role → more reliable

    Multimodal LLM:
      This file uses the raw OpenAI or Anthropic SDK directly (like module 09
      task 3) because llm_core is text-only. The image is base64-encoded and
      embedded in the message content.

How to run (from repo root):
    uv sync --extra browser
    uv run playwright install chromium
    LLM_PROVIDER=openai   uv run python modules/18-computer-use/py/02_vision_agent.py
    LLM_PROVIDER=anthropic uv run python modules/18-computer-use/py/02_vision_agent.py

Environment variables:
    OPENAI_API_KEY / ANTHROPIC_API_KEY
    LLM_PROVIDER      — "openai" (default) or "anthropic"
    BROWSER_HEADLESS  — "true" (default) or "false"
    AGENT_GOAL        — what the agent should accomplish
                        (default: "Find the main heading on example.com")
    AGENT_MAX_STEPS   — max number of browser steps (default: 8)
    START_URL         — starting URL (default: https://example.com)

Python deps: playwright, openai or anthropic
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"
AGENT_GOAL = os.getenv("AGENT_GOAL", "Find the main heading on example.com")
START_URL = os.getenv("START_URL", "https://example.com")
MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))

ASSETS_DIR = Path(__file__).parent.parent / "assets"


# ---------------------------------------------------------------------------
# Action types
# ---------------------------------------------------------------------------

@dataclass
class ActionClick:
    x: int
    y: int
    description: str = ""

@dataclass
class ActionType:
    text: str

@dataclass
class ActionNavigate:
    url: str

@dataclass
class ActionScroll:
    direction: Literal["up", "down"]
    amount: int = 300

@dataclass
class ActionDone:
    answer: str

Action = ActionClick | ActionType | ActionNavigate | ActionScroll | ActionDone


# ---------------------------------------------------------------------------
# Screenshot helper
# ---------------------------------------------------------------------------

def page_screenshot_b64(page) -> str:
    """Take a screenshot of the current page and return it as a base64 string."""
    # TODO 1: Call `page.screenshot(type="png")` (it returns raw bytes), then
    #   base64-encode those bytes and decode to a UTF-8 `str` before returning.
    raise NotImplementedError("TODO 1: implement page_screenshot_b64")


# ---------------------------------------------------------------------------
# LLM action decision
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a browser agent. You see a screenshot of the current browser state.
Your goal: {goal}

Respond with a single JSON object describing your next action:
  {{"action": "click",    "x": <int>, "y": <int>, "description": "<what you're clicking>"}}
  {{"action": "type",     "text": "<text to type>"}}
  {{"action": "navigate", "url": "<full URL>"}}
  {{"action": "scroll",   "direction": "up"|"down", "amount": 300}}
  {{"action": "done",     "answer": "<your final answer>"}}

Rules:
- Only output valid JSON, nothing else.
- Use "done" when you have found the answer or cannot proceed.
- Prefer "navigate" for going to a new page rather than guessing coordinates.
- Coordinates are relative to the viewport (usually 1280x720).
"""


def decide_action_openai(screenshot_b64: str, goal: str, step: int) -> Action:
    """Ask GPT-4o-mini to decide the next browser action given a screenshot."""
    from openai import OpenAI  # noqa: PLC0415

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")

    # TODO 2: Build the multimodal message list (same pattern as module 09 task 3).
    #   - Start with a system message whose content is `SYSTEM_PROMPT.format(goal=goal)`.
    #   - Add a user message whose `content` is a LIST mixing a text part (step + goal)
    #     and an image part. For OpenAI the image part is
    #     `{"type": "image_url", "image_url": {"url": ...}}` where the url is a
    #     `data:image/png;base64,<screenshot_b64>` URI.
    #   - Call `client.chat.completions.create(model=model, messages=..., max_tokens=...)`
    #     and request JSON with `response_format={"type": "json_object"}`.
    #   - Pull the message content off the first choice, `json.loads(...)` it, and hand
    #     the dict to `_parse_action(...)`.
    raise NotImplementedError("TODO 2: implement decide_action_openai")


def decide_action_anthropic(screenshot_b64: str, goal: str, step: int) -> Action:
    """Ask Claude to decide the next browser action given a screenshot."""
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # TODO 3: Same idea as TODO 2 but with the Anthropic SDK (module 09 task 3 pattern).
    #   - `client.messages.create(model=model, max_tokens=..., system=..., messages=...)`.
    #     Anthropic takes the system prompt as the top-level `system=` argument (formatted
    #     with the goal), NOT as a message.
    #   - The single user message's `content` is a list with an image part
    #     `{"type": "image", "source": {"type": "base64", "media_type": "image/png",
    #     "data": screenshot_b64}}` plus a text part asking what to do next.
    #   - Read the text off the first content block, `json.loads(...)` it, and pass the
    #     dict to `_parse_action(...)`.
    raise NotImplementedError("TODO 3: implement decide_action_anthropic")


def _parse_action(data: dict) -> Action:
    """Convert a raw action dict from the LLM into a typed Action."""
    # TODO 4: Branch on data["action"] and construct the matching dataclass, reading
    #   each field from `data` (use `.get(..., default)` for the optional description
    #   and scroll amount). The five action strings map to ActionClick / ActionType /
    #   ActionNavigate / ActionScroll / ActionDone. Raise ValueError for anything else.
    raise NotImplementedError("TODO 4: implement _parse_action")


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

def execute_action(page, action: Action) -> str:
    """Execute an action on the browser page. Returns a short observation string."""
    # TODO 5: Dispatch on the action type (isinstance) and drive Playwright:
    #   - ActionClick    -> click at the (x, y) via `page.mouse.click(...)`
    #   - ActionType     -> type the text via `page.keyboard.type(...)`
    #   - ActionNavigate -> `page.goto(url, wait_until="domcontentloaded")`
    #   - ActionScroll   -> `page.mouse.wheel(0, dy)` where dy is +amount for "down",
    #                       -amount for "up"
    #   - ActionDone     -> no browser call; just report the answer
    #   Return a short observation string for each so the loop can print it.
    raise NotImplementedError("TODO 5: implement execute_action")


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_vision_agent(goal: str, start_url: str, max_steps: int = MAX_STEPS) -> str:
    """Run a vision-grounded browser agent until it answers the goal or hits max_steps.

    Returns the final answer string.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    provider = os.getenv("LLM_PROVIDER", "openai")
    decide_fn = decide_action_openai if provider != "anthropic" else decide_action_anthropic

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(start_url, wait_until="domcontentloaded")

        print(f"Goal      : {goal}")
        print(f"Provider  : {provider}")
        print(f"Max steps : {max_steps}\n")

        for step in range(1, max_steps + 1):
            # TODO 6: Implement the agent loop body.
            #   a) Grab the current screenshot as base64 via page_screenshot_b64(page).
            #   b) Also save a debug PNG per step to ASSETS_DIR (e.g. f"step_{step:02d}.png").
            #   c) Ask the LLM for the next action: decide_fn(screenshot_b64, goal, step).
            #   d) Print the action so the learner can trace the run.
            #   e) When the action is an ActionDone, close the browser and return its answer.
            #   f) Otherwise execute it, wait for any navigation to settle, and print the
            #      observation before looping again.
            raise NotImplementedError("TODO 6: implement the agent loop body")

        browser.close()
        return "Max steps reached without a final answer."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    answer = run_vision_agent(AGENT_GOAL, START_URL)
    print(f"\nFinal answer: {answer}")


if __name__ == "__main__":
    main()
