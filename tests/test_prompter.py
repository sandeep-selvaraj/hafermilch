"""Tests for prompt building — correct structure and backend-specific hints."""

from __future__ import annotations

from hafermilch.core.models import TaskStep
from hafermilch.evaluation.prompter import Prompter
from tests.conftest import make_page_context, make_persona

prompter = Prompter()


def test_system_prompt_contains_persona_name():
    persona = make_persona(display_name="Office Clerk")
    msg = prompter.build_system_prompt(persona)
    assert "Office Clerk" in msg.content
    assert msg.role == "system"


def test_system_prompt_contains_goals():
    persona = make_persona(goals=["Find bugs", "Check clarity"])
    msg = prompter.build_system_prompt(persona)
    assert "Find bugs" in msg.content
    assert "Check clarity" in msg.content


def test_action_prompt_has_system_and_user_messages():
    persona = make_persona()
    step = TaskStep(instruction="Click the login button.", max_actions=5)
    context = make_page_context()

    messages = prompter.build_action_prompt(
        persona=persona,
        context=context,
        step=step,
        selector_hint="Use CSS selectors.",
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"


def test_action_prompt_embeds_selector_hint():
    persona = make_persona()
    step = TaskStep(instruction="Do something.", max_actions=3)
    context = make_page_context()

    hint = "Use @ref references (e.g. @e1)."
    messages = prompter.build_action_prompt(
        persona=persona,
        context=context,
        step=step,
        selector_hint=hint,
    )

    user_content = messages[1].content
    # User content is a list of parts
    combined = " ".join(p["text"] for p in user_content if p.get("type") == "text")
    assert hint in combined


def test_action_prompt_excludes_screenshot_when_flagged():
    persona = make_persona()
    step = TaskStep(instruction="Look around.", max_actions=3)
    context = make_page_context(screenshot=b"\x89PNG")

    messages = prompter.build_action_prompt(
        persona=persona,
        context=context,
        step=step,
        selector_hint="CSS",
        include_screenshot=False,
    )

    user_content = messages[1].content
    image_parts = [p for p in user_content if p.get("type") == "image"]
    assert image_parts == []


def test_action_prompt_includes_screenshot_when_flagged():
    persona = make_persona()
    step = TaskStep(instruction="Look around.", max_actions=3)
    context = make_page_context(screenshot=b"\x89PNG")

    messages = prompter.build_action_prompt(
        persona=persona,
        context=context,
        step=step,
        selector_hint="CSS",
        include_screenshot=True,
    )

    user_content = messages[1].content
    image_parts = [p for p in user_content if p.get("type") == "image"]
    assert len(image_parts) == 1


def test_report_prompt_contains_findings_and_dimensions():
    persona = make_persona()
    findings = "Task: login\nObservation: Button was hard to find."

    messages = prompter.build_report_prompt(persona, findings)

    assert len(messages) == 2
    user_text = messages[1].content
    assert "Button was hard to find." in user_text
    assert "Usability" in user_text  # from scoring_dimensions in make_persona
