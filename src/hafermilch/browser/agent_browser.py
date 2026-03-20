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

_POST_ACTION_DELAY_S = 1.0
_NAVIGATION_SETTLE_TIMEOUT_S = 15.0
_NAVIGATION_POLL_INTERVAL_S = 0.75
_STABLE_POLLS_REQUIRED = 3

logger = logging.getLogger(__name__)


class AgentBrowserAgent(BaseBrowserAgent):
    """Browser agent backed by the agent-browser CLI (Vercel Labs).

    Each instance gets its own isolated session ID so multiple personas
    can run concurrently without sharing browser state.

    Requires agent-browser to be installed and available on PATH:
        npm install -g agent-browser
    """

    def __init__(self, record: bool = False, record_dir: Path | None = None) -> None:
        self._session = f"hafermilch-{uuid.uuid4().hex[:8]}"
        # Track the current URL ourselves — more reliable than calling `get url`
        # because agent-browser may return it in an unpredictable JSON shape.
        self._current_url: str = ""
        self._record = record
        self._record_dir = record_dir or Path("reports")
        self._recording_path: Path | None = None

    @property
    def selector_hint(self) -> str:
        return (
            "Use @ref references from the snapshot (e.g. @e1, @e3). "
            "Do NOT use CSS selectors — only refs that appear in the snapshot above."
        )

    async def start(self) -> None:
        # The agent-browser daemon starts on the first command.
        # Set viewport to 1280x800 so screenshots aren't mostly black padding.
        await self._run_raw("set", "viewport", "1280", "800")

        if self._record:
            self._record_dir.mkdir(parents=True, exist_ok=True)
            self._recording_path = self._record_dir / f"recording-{self._session}.webm"
            await self._run_raw("record", "start", str(self._recording_path))
            logger.info("Recording to %s", self._recording_path)

    async def stop(self) -> None:
        if self._record:
            with contextlib.suppress(BrowserError):
                await self._run_raw("record", "stop")
                logger.info("Recording saved to %s", self._recording_path)
        with contextlib.suppress(BrowserError):
            await self._run("close")

    async def navigate(self, url: str) -> None:
        await self._run("open", url)
        self._current_url = url

    async def capture(self) -> PageContext:
        try:
            # Take an initial snapshot, then wait briefly and re-snapshot to
            # ensure the page has finished rendering before we screenshot.
            snapshot_raw = await self._run("snapshot", "--compact")
            snapshot_data = json.loads(snapshot_raw)
            data = snapshot_data.get("data") or {}
            tree_text = data.get("snapshot") or ""

            # Quick stability check: re-snapshot after a short pause and use
            # the newer version if the tree changed (page was still loading).
            await asyncio.sleep(_NAVIGATION_POLL_INTERVAL_S)
            raw2 = await self._run("snapshot", "--compact")
            data2 = json.loads(raw2).get("data") or {}
            tree2 = data2.get("snapshot") or ""
            if tree2 and tree2 != tree_text:
                # Page was still loading — use the fresher snapshot
                data = data2
                tree_text = tree2

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
                    url_before = self._current_url
                    await self._run("click", action.selector)
                    await self._wait_for_page_settle(url_before)

                case "type":
                    if not action.selector or action.text is None:
                        raise BrowserError("'type' action requires selector and text.")
                    await self._run("fill", action.selector, action.text)

                case "navigate":
                    if not action.url:
                        raise BrowserError("'navigate' action requires a url.")
                    url_before = self._current_url
                    await self._run("open", action.url)
                    self._current_url = action.url
                    await self._wait_for_page_settle(url_before)

                case "scroll":
                    direction = action.direction or "down"
                    amount = str(action.amount or 300)
                    await self._run("scroll", direction, amount)

                case "wait":
                    await asyncio.sleep((action.wait_ms or 1000) / 1000)

                case "login":
                    if not action.username or not action.password:
                        raise BrowserError("'login' action requires username and password.")
                    url_before = self._current_url
                    await self._login(action.username, action.password)
                    await self._wait_for_page_settle(url_before)

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
        data = json.loads(snapshot_raw).get("data", {})
        tree = data.get("snapshot") or ""
        refs = data.get("refs") or {}
        user_ref, pass_ref, submit_ref = _parse_login_refs(tree, refs)
        logger.info("Login — user=%s pass=%s submit=%s", user_ref, pass_ref, submit_ref)
        await self._run("fill", user_ref, username)
        await self._run("fill", pass_ref, password)
        await self._run("click", submit_ref)

    async def _wait_for_page_settle(self, url_before: str) -> None:
        """Wait for the page to settle after an action that may trigger navigation.

        Polls the agent-browser snapshot until either the URL changes from
        *url_before* and the tree stabilises, or the tree is identical across
        several consecutive polls (indicating the page has finished loading).
        """
        await asyncio.sleep(_POST_ACTION_DELAY_S)

        prev_tree: str | None = None
        stable_count = 0
        navigated = False
        elapsed = _POST_ACTION_DELAY_S

        while elapsed < _NAVIGATION_SETTLE_TIMEOUT_S:
            try:
                raw = await self._run("snapshot", "--compact")
                data = json.loads(raw).get("data", {})
                current_url = data.get("url") or data.get("currentUrl") or ""
                tree = data.get("snapshot") or ""

                if current_url:
                    self._current_url = current_url

                if current_url and current_url != url_before:
                    navigated = True

                # Check tree stability
                if prev_tree is not None and tree == prev_tree and tree:
                    stable_count += 1
                else:
                    stable_count = 0

                if stable_count >= _STABLE_POLLS_REQUIRED:
                    logger.debug("Snapshot stabilised on %s.", current_url or url_before)
                    return

                # If navigated and tree has been stable for at least 1 poll, accept
                if navigated and stable_count >= 1 and tree:
                    logger.debug("Page navigated to %s and stabilised.", current_url)
                    return

                prev_tree = tree
            except Exception:
                stable_count = 0
                prev_tree = None  # reset on error — page is mid-transition

            await asyncio.sleep(_NAVIGATION_POLL_INTERVAL_S)
            elapsed += _NAVIGATION_POLL_INTERVAL_S

        logger.debug("Page settle timeout reached (%.1fs), proceeding.", elapsed)

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


def _parse_login_refs(tree: str, refs: dict | None = None) -> tuple[str, str, str]:
    """Extract @refs for username field, password field, and submit button.

    Language-agnostic: uses the structured ``refs`` dict (role-based) when
    available, falling back to regex on the text tree.  Login forms almost
    universally follow the pattern textbox → textbox → button, so positional
    heuristics work across languages.
    """
    refs = refs or {}

    # ── Build ordered lists from the refs dict ──────────────────────────
    # refs keys are like "e1", "e2", … in document order.
    textboxes: list[str] = []  # ref ids of textbox/input elements
    buttons: list[str] = []  # ref ids of button elements

    for ref_id in sorted(refs, key=lambda r: int(r[1:]) if r[1:].isdigit() else 0):
        info = refs[ref_id]
        role = (info.get("role") or "").lower()
        if role in ("textbox", "input", "searchbox"):
            textboxes.append(ref_id)
        elif role == "button":
            buttons.append(ref_id)

    # ── If refs dict was empty/missing, fall back to tree regex ─────────
    if not textboxes:
        for _, _, ref_id in re.findall(
            r'(textbox|input)\s+"[^"]*?"\s+\[ref=(e\d+)\]', tree, re.IGNORECASE
        ):
            textboxes.append(ref_id)
    if not buttons:
        for _, ref_id in re.findall(r'button\s+"[^"]*?"\s+\[ref=(e\d+)\]', tree, re.IGNORECASE):
            buttons.append(ref_id)

    # ── Assign: first textbox = username, second = password ─────────────
    user_ref = textboxes[0] if len(textboxes) >= 1 else None
    pass_ref = textboxes[1] if len(textboxes) >= 2 else None

    # ── Submit: first button after the password field ───────────────────
    submit_ref = None
    if pass_ref is not None and buttons:
        pass_idx = int(pass_ref[1:]) if pass_ref[1:].isdigit() else 0
        for btn in buttons:
            btn_idx = int(btn[1:]) if btn[1:].isdigit() else 0
            if btn_idx > pass_idx:
                submit_ref = btn
                break
    # Last resort: first button
    if submit_ref is None and buttons:
        submit_ref = buttons[0]

    if not user_ref or not pass_ref or not submit_ref:
        fields_status = [("username", user_ref), ("password", pass_ref), ("submit", submit_ref)]
        missing = [n for n, v in fields_status if not v]
        raise BrowserError(f"Could not find login form fields in snapshot: missing {missing}")

    return f"@{user_ref}", f"@{pass_ref}", f"@{submit_ref}"
