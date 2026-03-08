from __future__ import annotations

from hafermilch.browser.context import PageContext
from hafermilch.core.models import Persona, TaskStep
from hafermilch.llm.base import Message

_REPORT_SCHEMA_HINT = """
{
  "overall_score": 7.5,
  "summary": "Plain-language summary of the experience from your perspective",
  "dimension_scores": [
    {"dimension": "<name>", "score": 8.0, "rationale": "<why>"}
  ],
  "recommendations": ["Specific, actionable suggestion 1", "..."]
}
Scores are from 0 (terrible) to 10 (excellent).
"""

_ACTION_SCHEMA_TEMPLATE = """\
{{
  "observation": "What you notice about this page, in your own voice",
  "reasoning": "Why you are taking the next action",
  "action_type": "click | type | scroll | navigate | wait | done",
  "selector": "{selector_hint}",
  "text": "Text to enter (required for type)",
  "url": "Destination URL (required for navigate)",
  "direction": "up | down (required for scroll)",
  "amount": 300,
  "wait_ms": 1000
}}
Use action_type 'done' when you have completed the instruction or cannot proceed.
"""


class Prompter:
    """Builds prompts that frame the LLM as a specific persona."""

    def build_system_prompt(self, persona: Persona) -> Message:
        goals = "\n".join(f"  - {g}" for g in persona.goals)
        return Message(
            role="system",
            content=(
                f"You are {persona.display_name}.\n\n"
                f"Background: {persona.background}\n\n"
                f"Your goals when evaluating this product:\n{goals}\n\n"
                f"Expertise level: {persona.expertise_level}. "
                f"Technical mindset: {'yes' if persona.technical else 'no'}.\n\n"
                "Stay completely in character throughout the session. "
                "Your observations, frustrations, and praise should reflect "
                "your background and level of technical knowledge."
            ),
        )

    def build_action_prompt(
        self,
        persona: Persona,
        context: PageContext,
        step: TaskStep,
        selector_hint: str,
        include_screenshot: bool = True,
    ) -> list[Message]:
        """Return the full message list for a single action decision."""
        system = self.build_system_prompt(persona)

        schema_hint = _ACTION_SCHEMA_TEMPLATE.format(selector_hint=selector_hint)

        page_parts = context.to_llm_parts(include_screenshot=include_screenshot)
        page_parts.append(
            {
                "type": "text",
                "text": (
                    f"\nYour current instruction: {step.instruction}\n\n"
                    f"Respond with a JSON object that matches this schema:\n"
                    f"{schema_hint}"
                ),
            }
        )

        return [system, Message(role="user", content=page_parts)]

    def build_report_prompt(
        self,
        persona: Persona,
        findings_summary: str,
    ) -> list[Message]:
        """Return the message list that asks the persona to produce a final report."""
        system = self.build_system_prompt(persona)

        dimensions = "\n".join(f"  - {d.name}: {d.description}" for d in persona.scoring_dimensions)

        user_text = (
            f"You have finished evaluating the product. "
            f"Here is a log of what you observed:\n\n"
            f"{findings_summary}\n\n"
            f"Now write your final evaluation. Score the product on these dimensions:\n"
            f"{dimensions}\n\n"
            f"Respond with a JSON object that matches this schema:\n"
            f"{_REPORT_SCHEMA_HINT}"
        )

        return [system, Message(role="user", content=user_text)]
