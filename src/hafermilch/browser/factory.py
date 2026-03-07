from __future__ import annotations

from typing import Literal

from hafermilch.browser.base import BaseBrowserAgent

BrowserBackend = Literal["playwright", "agent-browser"]


def create_browser_agent(
    backend: BrowserBackend = "playwright",
    headless: bool = True,
) -> BaseBrowserAgent:
    match backend:
        case "playwright":
            from hafermilch.browser.playwright_agent import PlaywrightBrowserAgent

            return PlaywrightBrowserAgent(headless=headless)
        case "agent-browser":
            from hafermilch.browser.agent_browser import AgentBrowserAgent

            return AgentBrowserAgent()
        case _:
            raise ValueError(f"Unknown browser backend: '{backend}'")
