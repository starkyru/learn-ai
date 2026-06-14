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
    # TODO 1: Import playwright and navigate.
    #   from playwright.sync_api import sync_playwright
    #
    #   with sync_playwright() as p:
    #       browser = p.chromium.launch(headless=HEADLESS)
    #       page = browser.new_page()
    #       page.goto(url, wait_until="domcontentloaded")
    #
    # TODO 2: Read page info.
    #   title = page.title()
    #   final_url = page.url
    #   # Get visible text (inner text of the body, not raw HTML):
    #   text = page.locator("body").inner_text()
    #   link_count = page.locator("a").count()
    #
    # TODO 3: Return the dict and close the browser.
    #   browser.close()
    #   return {"title": title, "url": final_url, "text": text[:1000], "link_count": link_count}
    raise NotImplementedError("TODO 1-3: implement navigate_and_read")


def take_screenshot(url: str, output_path: Path) -> Path:
    """Navigate to a URL and save a screenshot as a PNG.

    Returns the path to the saved file.
    """
    # TODO 4: Use playwright to take a full-page screenshot.
    #   page.screenshot(path=str(output_path), full_page=True)
    #   browser.close()
    #   return output_path
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
    #   b) page.locator(search_selector).fill(query)
    #   c) page.keyboard.press("Enter")
    #   d) page.wait_for_load_state("domcontentloaded")
    #   e) Return page.title()
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
    # TODO 6: Repeat the navigation using the async Playwright API.
    #   from playwright.async_api import async_playwright
    #
    #   async with async_playwright() as p:
    #       browser = await p.chromium.launch(headless=HEADLESS)
    #       page = await browser.new_page()
    #       await page.goto(url, wait_until="domcontentloaded")
    #       title = await page.title()
    #       await browser.close()
    #       return title
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

    # TODO 7 (stretch): Demonstrate the async API.
    #   import asyncio
    #   title = asyncio.run(navigate_async(TARGET_URL))
    #   print(f"\nAsync title: {title}")


if __name__ == "__main__":
    main()
