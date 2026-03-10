from __future__ import annotations

import asyncio
import contextlib

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from hafermilch.browser.base import BaseBrowserAgent
from hafermilch.browser.context import PageContext
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction

_POST_ACTION_DELAY_S = 0.8
_CLICK_TIMEOUT_MS = 15_000  # generous timeout for slow / JS-heavy pages

# Injected into every page in non-headless mode: a red dot that follows the
# real mouse pointer so you can see exactly where the AI is clicking.
_CURSOR_SCRIPT = """
(() => {
  if (document.getElementById('__hm_cursor__')) return;
  const dot = document.createElement('div');
  dot.id = '__hm_cursor__';
  Object.assign(dot.style, {
    position:      'fixed',
    width:         '18px',
    height:        '18px',
    borderRadius:  '50%',
    background:    'rgba(220, 38, 38, 0.85)',
    border:        '2px solid white',
    boxShadow:     '0 0 6px rgba(0,0,0,0.5)',
    pointerEvents: 'none',
    zIndex:        '2147483647',
    transform:     'translate(-50%, -50%)',
    transition:    'left 0.05s linear, top 0.05s linear',
    top: '-40px', left: '-40px',
  });
  document.body.appendChild(dot);
  document.addEventListener('mousemove', e => {
    dot.style.left = e.clientX + 'px';
    dot.style.top  = e.clientY + 'px';
  }, { passive: true });
})();
"""

# Highlight script: briefly flash a blue ring around the target element
_HIGHLIGHT_SCRIPT = """
(selector) => {
  let el;
  try { el = document.querySelector(selector); } catch (_) {}
  if (!el) return;
  const prev = el.style.outline;
  el.style.outline = '3px solid #2563eb';
  el.scrollIntoView({ block: 'center', behavior: 'smooth' });
  setTimeout(() => { el.style.outline = prev; }, 1200);
}
"""


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

        if not self._headless:
            # Inject cursor tracker on every new page/navigation
            await self._context.add_init_script(_CURSOR_SCRIPT)

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
                    await self._click(page, action.selector)

                case "type":
                    if not action.selector or action.text is None:
                        raise BrowserError("'type' action requires selector and text.")
                    await page.fill(action.selector, action.text, timeout=_CLICK_TIMEOUT_MS)

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

                case "login":
                    if not action.username or not action.password:
                        raise BrowserError("'login' action requires username and password.")
                    # Fill username: try common selectors in order
                    for sel in [
                        'input[type="email"]',
                        'input[name="username"]',
                        'input[id="username"]',
                        'input[type="text"]',
                    ]:
                        if await page.locator(sel).count() > 0:
                            await page.fill(sel, action.username, timeout=_CLICK_TIMEOUT_MS)
                            break
                    await page.fill(
                        'input[type="password"]', action.password, timeout=_CLICK_TIMEOUT_MS
                    )
                    await page.click(
                        'button[type="submit"], input[type="submit"]', timeout=_CLICK_TIMEOUT_MS
                    )

                case "done":
                    return

            await asyncio.sleep(_POST_ACTION_DELAY_S)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Failed to execute action '{action.action_type}': {exc}") from exc

    async def _click(self, page: Page, selector: str) -> None:
        """Click a selector, highlighting it first (non-headless) and falling
        back to a text-content search when the exact selector times out."""
        if not self._headless:
            with contextlib.suppress(Exception):
                await page.evaluate(_HIGHLIGHT_SCRIPT, selector)

        try:
            await page.click(selector, timeout=_CLICK_TIMEOUT_MS)
            return
        except Exception as primary_exc:
            # Fallback: try matching by visible text extracted from the selector.
            # e.g. role=button[name="Add to cart"] → try page.get_by_text("Add to cart")
            text = _extract_text_from_selector(selector)
            if text:
                try:
                    await page.get_by_text(text, exact=False).first.click(timeout=_CLICK_TIMEOUT_MS)
                    return
                except Exception:
                    pass  # let the original error surface

            raise primary_exc


def _extract_text_from_selector(selector: str) -> str | None:
    """Pull a human-readable label out of a Playwright selector string.

    Examples:
      'role=button[name="Add to cart"]'  → 'Add to cart'
      ':text("Sign up")'                 → 'Sign up'
      '#submit'                          → None
    """
    import re

    for pattern in (
        r'name=["\']([^"\']+)["\']',  # role=...[name="..."]
        r':text\(["\']([^"\']+)["\']\)',  # :text("...")
        r'text=["\']([^"\']+)["\']',  # text="..."
    ):
        m = re.search(pattern, selector, re.IGNORECASE)
        if m:
            return m.group(1)
    return None
