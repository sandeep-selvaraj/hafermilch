"""Shared fixtures for hafermilch tests."""

from __future__ import annotations

from hafermilch.browser.context import PageContext
from hafermilch.core.models import (
    EvaluationPlan,
    LLMConfig,
    Persona,
    ScoringDimension,
    Task,
    TaskStep,
)


def make_llm_config(**overrides) -> LLMConfig:
    return LLMConfig(provider="openai", model="gpt-4o", **overrides)


def make_persona(name: str = "test_persona", **overrides) -> Persona:
    defaults: dict = {
        "display_name": "Test Persona",
        "description": "A test persona.",
        "background": "Background text.",
        "goals": ["Goal one", "Goal two"],
        "expertise_level": "intermediate",
        "technical": True,
        "llm": make_llm_config(),
        "scoring_dimensions": [
            ScoringDimension(name="Usability", description="How easy to use.", weight=1.0)
        ],
    }
    defaults.update(overrides)
    return Persona(name=name, **defaults)


def make_plan(**overrides) -> EvaluationPlan:
    defaults: dict = {
        "name": "test_plan",
        "description": "A test plan.",
        "target_url": "https://example.com",
        "personas": ["test_persona"],
        "tasks": [
            Task(
                name="explore",
                description="Explore the page.",
                steps=[TaskStep(instruction="Look around.", max_actions=3)],
            )
        ],
    }
    defaults.update(overrides)
    return EvaluationPlan(**defaults)


def make_page_context(**overrides) -> PageContext:
    return PageContext(
        url=overrides.pop("url", "https://example.com"),
        title=overrides.pop("title", "Example"),
        screenshot=overrides.pop("screenshot", b"\x89PNG"),
        accessibility_tree=overrides.pop("accessibility_tree", "- heading: Welcome"),
        **overrides,
    )
