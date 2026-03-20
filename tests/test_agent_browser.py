"""Tests for AgentBrowserAgent — subprocess interaction and URL tracking."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hafermilch.browser.agent_browser import AgentBrowserAgent
from hafermilch.core.exceptions import BrowserError
from hafermilch.core.models import BrowserAction


def _make_proc(stdout: str = "", returncode: int = 0) -> MagicMock:
    """Build a fake asyncio process."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), b""))
    return proc


def _snapshot_response(snapshot_text: str = "- heading: Hello") -> str:
    return json.dumps({"success": True, "data": {"snapshot": snapshot_text}})


def _title_response(title: str = "Example") -> str:
    return json.dumps({"success": True, "data": title})


# ---------------------------------------------------------------------------
# _run_raw
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_raw_raises_on_missing_binary():
    agent = AgentBrowserAgent()
    with (
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(BrowserError, match="not found on PATH"),
    ):
        await agent._run_raw("snapshot")


@pytest.mark.asyncio
async def test_run_raw_raises_on_nonzero_exit():
    agent = AgentBrowserAgent()
    proc = _make_proc(returncode=1)
    proc.communicate = AsyncMock(return_value=(b"", b"something went wrong"))
    with (
        patch("asyncio.create_subprocess_exec", return_value=proc),
        pytest.raises(BrowserError, match="agent-browser command failed"),
    ):
        await agent._run_raw("click", "@e1")


# ---------------------------------------------------------------------------
# navigate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_navigate_updates_current_url():
    agent = AgentBrowserAgent()
    proc = _make_proc(stdout=json.dumps({"success": True}))
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        await agent.navigate("https://example.com/login")
    assert agent._current_url == "https://example.com/login"


# ---------------------------------------------------------------------------
# capture
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_capture_uses_tracked_url():
    agent = AgentBrowserAgent()
    agent._current_url = "https://example.com"

    # capture() takes two snapshots (stability check) + one title call
    responses = [_snapshot_response(), _snapshot_response(), _title_response()]
    call_count = 0

    async def fake_exec(*args, **kwargs):
        nonlocal call_count
        proc = _make_proc(stdout=responses[call_count])
        call_count += 1
        return proc

    with (
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
        patch.object(agent, "_capture_screenshot", return_value=None),
    ):
        ctx = await agent.capture()

    assert ctx.url == "https://example.com"
    assert ctx.accessibility_tree == "- heading: Hello"
    assert ctx.title == "Example"


@pytest.mark.asyncio
async def test_capture_handles_null_title_gracefully():
    agent = AgentBrowserAgent()
    agent._current_url = "https://example.com"

    null_title = json.dumps({"success": True, "data": None})
    # capture() takes two snapshots (stability check) + one title call
    responses = [_snapshot_response(), _snapshot_response(), null_title]
    call_count = 0

    async def fake_exec(*args, **kwargs):
        nonlocal call_count
        proc = _make_proc(stdout=responses[call_count])
        call_count += 1
        return proc

    with (
        patch("asyncio.create_subprocess_exec", side_effect=fake_exec),
        patch.object(agent, "_capture_screenshot", return_value=None),
    ):
        ctx = await agent.capture()

    assert ctx.title == ""


# ---------------------------------------------------------------------------
# execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_navigate_updates_url():
    agent = AgentBrowserAgent()
    agent._current_url = "https://example.com"

    proc = _make_proc(stdout=json.dumps({"success": True}))
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        action = BrowserAction(
            action_type="navigate",
            url="https://example.com/signup",
            observation="Going to sign up",
            reasoning="Next step",
        )
        await agent.execute(action)

    assert agent._current_url == "https://example.com/signup"


@pytest.mark.asyncio
async def test_execute_done_does_not_call_subprocess():
    agent = AgentBrowserAgent()
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        action = BrowserAction(
            action_type="done",
            observation="All done",
            reasoning="Finished",
        )
        await agent.execute(action)
        mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_execute_click_requires_selector():
    agent = AgentBrowserAgent()
    action = BrowserAction(
        action_type="click",
        selector=None,
        observation="Clicked",
        reasoning="Test",
    )
    with pytest.raises(BrowserError, match="requires a selector"):
        await agent.execute(action)
