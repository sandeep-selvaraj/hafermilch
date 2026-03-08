from __future__ import annotations

import asyncio

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from hafermilch.browser.base import BaseBrowserAgent
from hafermilch.browser.context import PageContext
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction

_POST_ACTION_DELAY_S = 0.8


class PlaywrightBrowserAgent(BaseBrowserAgent):
    """Browser agent backed by Playwright (Chromium)."""

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def selector_hint(self) -> str:
        return (
            "Use CSS selectors (e.g. '#submit', 'button[type=submit]', '.nav-link') "
            "or ARIA roles (e.g. 'role=button[name=\"Sign in\"]')."
        )

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(viewport={"width": 1280, "height": 800})
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def navigate(self, url: str) -> None:
        await self._page.goto(url, wait_until="domcontentloaded")

    async def capture(self) -> PageContext:
        try:
            page = self._page
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

    async def execute(self, action: BrowserAction) -> None:
        page = self._page
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
                    await asyncio.sleep((action.wait_ms or 1000) / 1000)

                case "done":
                    return

            await asyncio.sleep(_POST_ACTION_DELAY_S)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Failed to execute action '{action.action_type}': {exc}") from exc
