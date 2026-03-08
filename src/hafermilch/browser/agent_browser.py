from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from pathlib import Path

from hafermilch.browser.base import BaseBrowserAgent
from hafermilch.browser.context import PageContext
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction

_POST_ACTION_DELAY_S = 0.5


class AgentBrowserAgent(BaseBrowserAgent):
    """Browser agent backed by the agent-browser CLI (Vercel Labs).

    Each instance gets its own isolated session ID so multiple personas
    can run concurrently without sharing browser state.

    Requires agent-browser to be installed and available on PATH:
        npm install -g agent-browser
    """

    def __init__(self) -> None:
        self._session = f"hafermilch-{uuid.uuid4().hex[:8]}"
        # Track the current URL ourselves — more reliable than calling `get url`
        # because agent-browser may return it in an unpredictable JSON shape.
        self._current_url: str = ""

    @property
    def selector_hint(self) -> str:
        return (
            "Use @ref references from the snapshot (e.g. @e1, @e3). "
            "Do NOT use CSS selectors — only refs that appear in the snapshot above."
        )

    async def start(self) -> None:
        # The agent-browser daemon starts automatically on the first command.
        pass

    async def stop(self) -> None:
        try:
            await self._run("close")
        except BrowserError:
            pass  # session may already be gone

    async def navigate(self, url: str) -> None:
        await self._run("open", url)
        self._current_url = url

    async def capture(self) -> PageContext:
        try:
            snapshot_raw = await self._run("snapshot", "--compact")
            snapshot_data = json.loads(snapshot_raw)
            tree_text = snapshot_data.get("data", {}).get("snapshot") or ""

            title = await self._get_title()
            screenshot = await self._capture_screenshot()

            return PageContext(
                url=self._current_url,
                title=title,
                screenshot=screenshot,
                accessibility_tree=tree_text,
            )
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Failed to capture page context: {exc}") from exc

    async def execute(self, action: BrowserAction) -> None:
        try:
            match action.action_type:
                case "click":
                    if not action.selector:
                        raise BrowserError("'click' action requires a selector (@ref).")
                    await self._run("click", action.selector)

                case "type":
                    if not action.selector or action.text is None:
                        raise BrowserError("'type' action requires selector and text.")
                    await self._run("fill", action.selector, action.text)

                case "navigate":
                    if not action.url:
                        raise BrowserError("'navigate' action requires a url.")
                    await self._run("open", action.url)
                    self._current_url = action.url

                case "scroll":
                    direction = action.direction or "down"
                    amount = str(action.amount or 300)
                    await self._run("scroll", direction, amount)

                case "wait":
                    await asyncio.sleep((action.wait_ms or 1000) / 1000)

                case "done":
                    return

            await asyncio.sleep(_POST_ACTION_DELAY_S)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(
                f"Failed to execute action '{action.action_type}': {exc}"
            ) from exc

    async def _get_title(self) -> str:
        try:
            raw = await self._run("get", "title")
            data = json.loads(raw).get("data")
            return data if isinstance(data, str) else ""
        except Exception:
            return ""

    async def _capture_screenshot(self) -> bytes | None:
        """Save a screenshot to a temp file and return its bytes."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = Path(f.name)
        try:
            await self._run_raw("screenshot", str(tmp_path))
            return tmp_path.read_bytes()
        except Exception:
            return None
        finally:
            tmp_path.unlink(missing_ok=True)

    async def _run(self, *args: str) -> str:
        """Run an agent-browser command with --json output and return stdout."""
        return await self._run_raw(*args, "--json")

    async def _run_raw(self, *args: str) -> str:
        """Run an agent-browser command and return raw stdout."""
        cmd = ["agent-browser", "--session", self._session, *args]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise BrowserError(
                "agent-browser CLI not found on PATH. "
                "Install it with: npm install -g agent-browser"
            ) from exc

        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise BrowserError(
                f"agent-browser command failed ({' '.join(args)}): "
                f"{stderr.decode().strip()}"
            )
        return stdout.decode()
