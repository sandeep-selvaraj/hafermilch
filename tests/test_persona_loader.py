"""Tests for YAML persona and plan loading."""

from __future__ import annotations

import pytest

from hafermilch.core.exceptions import PersonaLoadError
from hafermilch.personas.loader import load_persona, load_plan, resolve_plan_personas
from tests.conftest import make_persona, make_plan

VALID_PERSONA_YAML = """\
name: engineer
display_name: "Engineer"
description: "A test engineer."
background: "Works in tech."
goals:
  - Evaluate performance
expertise_level: expert
technical: true
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.5
scoring_dimensions:
  - name: Performance
    description: Page speed
    weight: 1.0
"""

VALID_PLAN_YAML = """\
name: my_plan
description: "A test plan."
target_url: "https://example.com"
personas:
  - engineer
tasks:
  - name: explore
    description: Look around.
    steps:
      - instruction: "Navigate to the homepage."
        max_actions: 5
"""


def test_load_persona_valid(tmp_path):
    f = tmp_path / "engineer.yaml"
    f.write_text(VALID_PERSONA_YAML)
    persona = load_persona(f)
    assert persona.name == "engineer"
    assert persona.llm.provider == "openai"
    assert persona.expertise_level == "expert"


def test_load_persona_missing_file(tmp_path):
    with pytest.raises(PersonaLoadError, match="not found"):
        load_persona(tmp_path / "ghost.yaml")


def test_load_persona_invalid_yaml(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("name: [unclosed bracket")
    with pytest.raises(PersonaLoadError, match="YAML parse error"):
        load_persona(f)


def test_load_persona_missing_required_field(tmp_path):
    # Missing 'goals' field
    f = tmp_path / "incomplete.yaml"
    f.write_text("name: x\ndisplay_name: X\n")
    with pytest.raises(PersonaLoadError, match="Invalid persona"):
        load_persona(f)


def test_load_plan_valid(tmp_path):
    f = tmp_path / "plan.yaml"
    f.write_text(VALID_PLAN_YAML)
    plan = load_plan(f)
    assert plan.name == "my_plan"
    assert plan.target_url == "https://example.com"
    assert plan.personas == ["engineer"]
    assert len(plan.tasks) == 1


def test_load_plan_no_tasks_raises(tmp_path):
    tasks_block = (
        "tasks:\n  - name: explore\n    description: Look around.\n"
        '    steps:\n      - instruction: "Navigate to the homepage."\n'
        "        max_actions: 5"
    )
    yaml = VALID_PLAN_YAML.replace(tasks_block, "tasks: []")
    f = tmp_path / "plan.yaml"
    f.write_text(yaml)
    with pytest.raises(PersonaLoadError, match="Invalid plan"):
        load_plan(f)


def test_resolve_plan_personas_success():
    plan = make_plan(personas=["test_persona"])
    persona = make_persona("test_persona")
    resolved = resolve_plan_personas(plan, {"test_persona": persona})
    assert resolved == [persona]


def test_resolve_plan_personas_unknown_name():
    plan = make_plan(personas=["ghost"])
    with pytest.raises(PersonaLoadError, match="unknown persona 'ghost'"):
        resolve_plan_personas(plan, {"other": make_persona("other")})
