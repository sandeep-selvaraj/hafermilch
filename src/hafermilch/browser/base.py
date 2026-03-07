from __future__ import annotations

from abc import ABC, abstractmethod

from hafermilch.browser.context import PageContext
from hafermilch.core.models import BrowserAction


class BaseBrowserAgent(ABC):
    """Abstract browser agent.

    Each implementation owns its own browser session lifecycle. The runner
    uses the async context manager to start and stop the session, then calls
    navigate / capture / execute without needing to know which backend is in use.
    """

    async def __aenter__(self) -> BaseBrowserAgent:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    @abstractmethod
    async def start(self) -> None:
        """Initialise the browser session."""

    @abstractmethod
    async def stop(self) -> None:
        """Tear down the browser session."""

    @abstractmethod
    async def navigate(self, url: str) -> None:
        """Navigate to a URL and wait for the page to settle."""

    @abstractmethod
    async def capture(self) -> PageContext:
        """Return a snapshot of the current page state."""

    @abstractmethod
    async def execute(self, action: BrowserAction) -> None:
        """Execute a single browser action."""

    @property
    @abstractmethod
    def selector_hint(self) -> str:
        """One-line instruction for the LLM on how to specify element selectors."""
