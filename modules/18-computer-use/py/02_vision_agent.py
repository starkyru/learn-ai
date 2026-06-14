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
    # TODO 1: Use page.screenshot(type="png") which returns bytes.
    #         Return base64.standard_b64encode(data).decode("utf-8").
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

    # TODO 2: Build the multimodal message (same pattern as module 09 task 3).
    #   messages = [{
    #       "role": "user",
    #       "content": [
    #           {"type": "text", "text": f"Step {step}. Goal: {goal}"},
    #           {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}},
    #       ]
    #   }]
    #   response = client.chat.completions.create(
    #       model=model,
    #       messages=messages,
    #       system=SYSTEM_PROMPT.format(goal=goal),  # Note: OpenAI uses messages[0] as system
    #       max_tokens=256,
    #       response_format={"type": "json_object"},  # request JSON output
    #   )
    #   raw = response.choices[0].message.content
    #   return _parse_action(json.loads(raw))
    #
    # Hint: pass the system prompt as a separate system message in the list.
    raise NotImplementedError("TODO 2: implement decide_action_openai")


def decide_action_anthropic(screenshot_b64: str, goal: str, step: int) -> Action:
    """Ask Claude to decide the next browser action given a screenshot."""
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

    # TODO 3: Build the Anthropic multimodal message (same as module 09 task 3).
    #   message = client.messages.create(
    #       model=model,
    #       max_tokens=256,
    #       system=SYSTEM_PROMPT.format(goal=goal),
    #       messages=[{
    #           "role": "user",
    #           "content": [
    #               {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_b64}},
    #               {"type": "text", "text": f"Step {step}. What should I do next to achieve the goal?"},
    #           ],
    #       }],
    #   )
    #   raw = message.content[0].text
    #   return _parse_action(json.loads(raw))
    raise NotImplementedError("TODO 3: implement decide_action_anthropic")


def _parse_action(data: dict) -> Action:
    """Convert a raw action dict from the LLM into a typed Action."""
    # TODO 4: Map data["action"] to the appropriate dataclass.
    #   "click"    -> ActionClick(x=data["x"], y=data["y"], description=data.get("description",""))
    #   "type"     -> ActionType(text=data["text"])
    #   "navigate" -> ActionNavigate(url=data["url"])
    #   "scroll"   -> ActionScroll(direction=data["direction"], amount=data.get("amount", 300))
    #   "done"     -> ActionDone(answer=data["answer"])
    #   Raise ValueError for unknown actions.
    raise NotImplementedError("TODO 4: implement _parse_action")


# ---------------------------------------------------------------------------
# Action execution
# ---------------------------------------------------------------------------

def execute_action(page, action: Action) -> str:
    """Execute an action on the browser page. Returns a short observation string."""
    # TODO 5: Dispatch on action type and call the appropriate Playwright method.
    #   ActionClick:    page.mouse.click(action.x, action.y); return f"Clicked ({action.x},{action.y})"
    #   ActionType:     page.keyboard.type(action.text); return f"Typed: {action.text!r}"
    #   ActionNavigate: page.goto(action.url, wait_until="domcontentloaded"); return f"Navigated to {action.url}"
    #   ActionScroll:   page.mouse.wheel(0, action.amount if action.direction=="down" else -action.amount)
    #   ActionDone:     return f"Done: {action.answer}"  (no browser interaction)
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
            #   a) Take a screenshot: screenshot_b64 = page_screenshot_b64(page)
            #   b) Save a debug copy: page.screenshot(path=str(ASSETS_DIR / f"step_{step:02d}.png"))
            #   c) Decide: action = decide_fn(screenshot_b64, goal, step)
            #   d) Print the action for the learner to trace.
            #   e) If isinstance(action, ActionDone): browser.close(); return action.answer
            #   f) Observe: observation = execute_action(page, action)
            #   g) Wait for any navigation: page.wait_for_load_state("domcontentloaded")
            #   h) Print the observation.
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
