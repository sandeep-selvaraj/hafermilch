from __future__ import annotations

from pathlib import Path
from typing import Literal

from hafermilch.browser.base import BaseBrowserAgent

BrowserBackend = Literal["playwright", "agent-browser"]


def create_browser_agent(
    backend: BrowserBackend = "playwright",
    headless: bool = True,
    record: bool = False,
    record_dir: Path | None = None,
) -> BaseBrowserAgent:
    match backend:
        case "playwright":
            from hafermilch.browser.playwright_agent import PlaywrightBrowserAgent

            return PlaywrightBrowserAgent(headless=headless)
        case "agent-browser":
            from hafermilch.browser.agent_browser import AgentBrowserAgent

            return AgentBrowserAgent(record=record, record_dir=record_dir)
        case _:
            raise ValueError(f"Unknown browser backend: '{backend}'")
