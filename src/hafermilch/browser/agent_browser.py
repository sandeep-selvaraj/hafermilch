from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import tempfile
import uuid
from pathlib import Path

from hafermilch.browser.base import BaseBrowserAgent
from hafermilch.browser.context import PageContext
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction

_POST_ACTION_DELAY_S = 0.5

logger = logging.getLogger(__name__)


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
        with contextlib.suppress(BrowserError):
            await self._run("close")

    async def navigate(self, url: str) -> None:
        await self._run("open", url)
        self._current_url = url

    async def capture(self) -> PageContext:
        try:
            snapshot_raw = await self._run("snapshot", "--compact")
            snapshot_data = json.loads(snapshot_raw)
            data = snapshot_data.get("data", {})
            tree_text = data.get("snapshot") or ""

            # Prefer the URL reported by agent-browser over our tracked value
            reported_url = data.get("url") or data.get("currentUrl") or ""
            if reported_url:
                self._current_url = reported_url

            title = await self._get_title()
            screenshot = await self._capture_screenshot()

            logger.info(
                "Snapshot — url: %s | tree_len: %d\n%s",
                self._current_url,
                len(tree_text),
                tree_text,
            )

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

                case "login":
                    if not action.username or not action.password:
                        raise BrowserError("'login' action requires username and password.")
                    await self._login(action.username, action.password)

                case "done":
                    return

            await asyncio.sleep(_POST_ACTION_DELAY_S)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Failed to execute action '{action.action_type}': {exc}") from exc

    async def _login(self, username: str, password: str) -> None:
        """Fill the login form and submit it in one sequence."""
        snapshot_raw = await self._run("snapshot", "--compact")
        tree = json.loads(snapshot_raw).get("data", {}).get("snapshot") or ""
        user_ref, pass_ref, submit_ref = _parse_login_refs(tree)
        logger.info("Login — user=%s pass=%s submit=%s", user_ref, pass_ref, submit_ref)
        await self._run("fill", user_ref, username)
        await self._run("fill", pass_ref, password)
        await self._run("click", submit_ref)

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
        logger.info("agent-browser → %s", " ".join(args))
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise BrowserError(
                "agent-browser CLI not found on PATH. Install it with: npm install -g agent-browser"
            ) from exc

        stdout, stderr = await proc.communicate()
        out = stdout.decode()
        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.info("agent-browser ← ERROR: %s", err)
            raise BrowserError(f"agent-browser command failed ({' '.join(args)}): {err}")
        logger.info("agent-browser ← %s", out[:200].strip())
        return out


def _parse_login_refs(tree: str) -> tuple[str, str, str]:
    """Extract @refs for username field, password field, and submit button."""
    # All textboxes in order: [ref=eN]
    textboxes = re.findall(r'textbox\s+"([^"]+)"\s+\[ref=(e\d+)\]', tree, re.IGNORECASE)

    user_ref = pass_ref = submit_ref = None

    for label, ref in textboxes:
        label_l = label.lower()
        if pass_ref is None and "password" in label_l:
            pass_ref = ref
        elif user_ref is None and any(k in label_l for k in ("user", "email", "login")):
            user_ref = ref

    # Fallback: first textbox = username, second = password
    if user_ref is None and textboxes:
        user_ref = textboxes[0][1]
    if pass_ref is None and len(textboxes) > 1:
        pass_ref = textboxes[1][1]

    # Submit button: "Sign In", "Log In", "Login", "Submit" etc.
    m = re.search(
        r'button\s+"(sign\s*in|log\s*in|login|submit)[^"]*"\s+\[ref=(e\d+)\]',
        tree,
        re.IGNORECASE,
    )
    if m:
        submit_ref = m.group(2)

    if not user_ref or not pass_ref or not submit_ref:
        fields = [("username", user_ref), ("password", pass_ref), ("submit", submit_ref)]
        missing = [n for n, v in fields if not v]
        raise BrowserError(f"Could not find login form fields in snapshot: missing {missing}")

    return f"@{user_ref}", f"@{pass_ref}", f"@{submit_ref}"
