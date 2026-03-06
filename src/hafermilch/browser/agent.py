from __future__ import annotations

import asyncio

from playwright.async_api import Page

from hafermilch.browser.context import PageContext
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction


class BrowserAgent:
    """Drives a Playwright page and captures page context snapshots."""

    # Milliseconds to wait after each action before capturing the next context
    _POST_ACTION_DELAY_MS = 800

    async def capture(self, page: Page) -> PageContext:
        """Take a screenshot and build an accessibility tree snapshot."""
        try:
            screenshot = await page.screenshot(full_page=False, type="png")
            tree_text = await page.locator("body").aria_snapshot()
            viewport = page.viewport_size or {"width": 1280, "height": 800}
            return PageContext(
                url=page.url,
                title=await page.title(),
                screenshot=screenshot,
                accessibility_tree=tree_text,
                viewport_width=viewport["width"],
                viewport_height=viewport["height"],
            )
        except Exception as exc:
            raise BrowserError(f"Failed to capture page context: {exc}") from exc

    async def execute(self, page: Page, action: BrowserAction) -> None:
        """Execute a BrowserAction on the given Playwright page."""
        try:
            match action.action_type:
                case "click":
                    if not action.selector:
                        raise BrowserError("'click' action requires a selector.")
                    await page.click(action.selector, timeout=5000)

                case "type":
                    if not action.selector or action.text is None:
                        raise BrowserError("'type' action requires selector and text.")
                    await page.fill(action.selector, action.text)

                case "navigate":
                    if not action.url:
                        raise BrowserError("'navigate' action requires a url.")
                    await page.goto(action.url, wait_until="domcontentloaded")

                case "scroll":
                    direction = action.direction or "down"
                    amount = action.amount or 300
                    delta_y = amount if direction == "down" else -amount
                    await page.mouse.wheel(0, delta_y)

                case "wait":
                    ms = action.wait_ms or 1000
                    await asyncio.sleep(ms / 1000)

                case "done":
                    return  # No-op; caller handles termination

            await asyncio.sleep(self._POST_ACTION_DELAY_MS / 1000)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(
                f"Failed to execute action '{action.action_type}': {exc}"
            ) from exc

