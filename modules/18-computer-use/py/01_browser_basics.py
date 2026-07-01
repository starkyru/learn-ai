"""01_browser_basics.py — Browser automation basics with Playwright.  🟢

What this teaches:
    Playwright is a browser automation library that lets you drive a real
    browser (Chromium, Firefox, WebKit) from Python. You navigate pages,
    read their content, fill forms, click buttons, and take screenshots —
    all programmatically, without a human at the keyboard.

    This is the foundation for the browser agents in tasks 2 and 3:
    before an LLM can decide what action to take, you need the machinery
    to execute the action and observe the result.

    Core Playwright concepts:
      Browser      — the browser instance (can run headless)
      BrowserContext — an isolated session (cookies, local storage)
      Page         — one browser tab

    Common operations:
      page.goto(url)             — navigate
      page.title()               — page title
      page.content()             — full HTML
      page.locator("selector")   — find element
      page.screenshot(path=...)  — capture a PNG

    Headless vs. headed:
      headless=True  — no visible window; fast, runs in CI
      headless=False — visible browser; useful for debugging

How to run (from repo root):
    # Install deps first:
    uv sync --extra browser
    uv run playwright install chromium   # downloads the browser binary

    uv run python modules/18-computer-use/py/01_browser_basics.py

Environment variables:
    BROWSER_HEADLESS  — "true" (default) or "false" to show the browser window
    TARGET_URL        — URL to navigate to (default: https://example.com)

Python deps: playwright  (uv sync --extra browser  +  playwright install)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"
TARGET_URL = os.getenv("TARGET_URL", "https://example.com")
SCREENSHOT_PATH = Path(__file__).parent.parent / "assets" / "screenshot.png"


# ---------------------------------------------------------------------------
# Navigation and content extraction
# ---------------------------------------------------------------------------

def navigate_and_read(url: str) -> dict:
    """Navigate to a URL and return basic page info.

    Returns a dict with:
      title       — page title
      url         — final URL after any redirects
      text        — visible text content (stripped of most HTML)
      link_count  — number of anchor tags found
    """
    # TODO 1: Import playwright's `sync_playwright` and open a browser inside a
    #   `with sync_playwright() as p:` block. Launch chromium with `headless=HEADLESS`,
    #   open a new page, and navigate to `url` (pass `wait_until="domcontentloaded"`
    #   so goto returns once the DOM is parsed).
    #
    # TODO 2: Read the page info you need for the dict:
    #   - title from `page.title()`
    #   - the final URL from the page (after any redirects)
    #   - the visible body text — locate the "body" element and read its INNER TEXT
    #     (not raw HTML/content)
    #   - the number of anchors — locate "a" elements and count them
    #
    # TODO 3: Close the browser and return the dict with keys
    #   title / url / text / link_count. Truncate the text to its first ~1000 chars.
    raise NotImplementedError("TODO 1-3: implement navigate_and_read")


def take_screenshot(url: str, output_path: Path) -> Path:
    """Navigate to a URL and save a screenshot as a PNG.

    Returns the path to the saved file.
    """
    # TODO 4: Open a browser as in TODO 1, navigate to `url`, then capture a
    #   full-page screenshot with `page.screenshot(...)` — pass the file path as a
    #   string and enable the full-page option. Close the browser and return output_path.
    raise NotImplementedError("TODO 4: implement take_screenshot")


# ---------------------------------------------------------------------------
# Element interaction
# ---------------------------------------------------------------------------

def search_on_page(url: str, search_selector: str, query: str) -> str:
    """Navigate to a URL, type a query into a search box, and return the result page title.

    Args:
        url             — starting URL
        search_selector — CSS selector for the input field (e.g. 'input[name="q"]')
        query           — text to type
    """
    # TODO 5: Implement a search flow.
    #   a) Navigate to url.
    #   b) Locate the input via `search_selector` and `.fill(query)` it.
    #   c) Submit by pressing Enter on the keyboard.
    #   d) Wait for the new page to load (`wait_for_load_state("domcontentloaded")`).
    #   e) Return the resulting page title.
    #
    # Note: search_selector="input[name='q']" works for DuckDuckGo.
    #       Use TARGET_URL="https://duckduckgo.com" and
    #       search_selector="input[name='q']" to test this.
    raise NotImplementedError("TODO 5: implement search_on_page")


# ---------------------------------------------------------------------------
# Async version (Playwright also has a full async API)
# ---------------------------------------------------------------------------

async def navigate_async(url: str) -> str:
    """Async version of navigate_and_read — returns the page title.

    Many browser agents use the async API so they can await tool calls
    alongside LLM responses.
    """
    # TODO 6: Mirror navigate_and_read using the ASYNC Playwright API instead.
    #   Import `async_playwright`, use `async with ... as p:`, and `await` every
    #   browser call (launch, new_page, goto, title, close). Return just the title.
    raise NotImplementedError("TODO 6: implement navigate_async")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    SCREENSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"URL      : {TARGET_URL}")
    print(f"Headless : {HEADLESS}\n")

    print("=== navigate_and_read ===")
    info = navigate_and_read(TARGET_URL)
    print(f"Title     : {info['title']}")
    print(f"Final URL : {info['url']}")
    print(f"Links     : {info['link_count']}")
    print(f"Text preview: {info['text'][:200]}")

    print("\n=== Screenshot ===")
    path = take_screenshot(TARGET_URL, SCREENSHOT_PATH)
    print(f"Saved to : {path}")

    # TODO 7 (stretch): Demonstrate the async API — drive `navigate_async` to
    #   completion with `asyncio.run(...)` and print the title it returns.


if __name__ == "__main__":
    main()
