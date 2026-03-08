"""Tests for EvaluationRunner — orchestration logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hafermilch.core.models import (
    BrowserAction,
    DimensionScore,
    PersonaReport,
)
from hafermilch.evaluation.runner import EvaluationRunner
from tests.conftest import make_page_context, make_persona, make_plan


def _make_persona_report(name: str = "test_persona") -> PersonaReport:
    return PersonaReport(
        persona_name=name,
        persona_display_name="Test Persona",
        target_url="https://example.com",
        findings=[],
        dimension_scores=[DimensionScore(dimension="Usability", score=8.0, rationale="Good")],
        overall_score=8.0,
        summary="Looks decent.",
        recommendations=["Improve contrast"],
    )


# ---------------------------------------------------------------------------
# run — top-level orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_produces_one_report_per_persona():
    plan = make_plan()
    personas = [make_persona("p1"), make_persona("p2")]
    runner = EvaluationRunner()

    fixed_report = _make_persona_report()
    with patch.object(runner, "_run_persona", new=AsyncMock(return_value=fixed_report)):
        report = await runner.run(plan, personas)

    assert report.plan_name == plan.name
    assert report.target_url == plan.target_url
    assert len(report.persona_reports) == 2


@pytest.mark.asyncio
async def test_run_raises_evaluation_error_on_persona_failure():
    from hafermilch.core.exceptions import EvaluationError

    plan = make_plan()
    personas = [make_persona()]
    runner = EvaluationRunner()

    with (
        patch.object(runner, "_run_persona", new=AsyncMock(side_effect=RuntimeError("boom"))),
        pytest.raises(EvaluationError, match="boom"),
    ):
        await runner.run(plan, personas)


# ---------------------------------------------------------------------------
# _run_step — LLM action loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_step_stops_on_done_action():
    """Runner should stop calling the LLM once it receives action_type='done'."""
    from hafermilch.core.models import Task, TaskStep

    runner = EvaluationRunner()
    persona = make_persona()
    task = Task(
        name="test",
        description="test",
        steps=[TaskStep(instruction="Do something", max_actions=10)],
    )
    step = task.steps[0]

    done_action = BrowserAction(
        action_type="done",
        observation="Page looks fine.",
        reasoning="Nothing left to do.",
    )

    mock_provider = MagicMock()
    mock_provider.supports_vision = False
    mock_provider.complete_json = AsyncMock(return_value=done_action)

    mock_agent = MagicMock()
    mock_agent.selector_hint = "Use CSS"
    mock_agent.capture = AsyncMock(return_value=make_page_context())

    findings = await runner._run_step(
        agent=mock_agent,
        persona=persona,
        provider=mock_provider,
        task=task,
        step=step,
    )

    # complete_json called exactly once — stopped immediately on 'done'
    mock_provider.complete_json.assert_awaited_once()
    assert len(findings) == 1
    assert findings[0].action_taken == "done"


@pytest.mark.asyncio
async def test_run_step_continues_after_browser_action_failure():
    """A failed browser action should record the error and break the loop gracefully."""
    from hafermilch.core.exceptions import BrowserError
    from hafermilch.core.models import Task, TaskStep

    runner = EvaluationRunner()
    persona = make_persona()
    task = Task(
        name="test",
        description="test",
        steps=[TaskStep(instruction="Click something", max_actions=5)],
    )
    step = task.steps[0]

    click_action = BrowserAction(
        action_type="click",
        selector="#btn",
        observation="I see a button.",
        reasoning="Clicking it.",
    )

    mock_provider = MagicMock()
    mock_provider.supports_vision = False
    mock_provider.complete_json = AsyncMock(return_value=click_action)

    mock_agent = MagicMock()
    mock_agent.selector_hint = "Use CSS"
    mock_agent.capture = AsyncMock(return_value=make_page_context())
    mock_agent.execute = AsyncMock(side_effect=BrowserError("Element not found"))

    findings = await runner._run_step(
        agent=mock_agent,
        persona=persona,
        provider=mock_provider,
        task=task,
        step=step,
    )

    assert len(findings) == 1
    assert "Element not found" in findings[0].observation


# ---------------------------------------------------------------------------
# LLM factory integration
# ---------------------------------------------------------------------------


def test_runner_uses_correct_browser_backend():
    """Factory is called with the backend specified at construction time."""
    from hafermilch.browser.agent_browser import AgentBrowserAgent
    from hafermilch.browser.factory import create_browser_agent
    from hafermilch.browser.playwright_agent import PlaywrightBrowserAgent

    pw = create_browser_agent("playwright", headless=True)
    ab = create_browser_agent("agent-browser")

    assert isinstance(pw, PlaywrightBrowserAgent)
    assert isinstance(ab, AgentBrowserAgent)
