from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Persona — who the agent is (reusable across any product)
# ---------------------------------------------------------------------------


class LLMConfig(BaseModel):
    provider: Literal["openai", "gemini", "ollama"]
    model: str
    temperature: float = 0.7
    # Optionally override the env-var API key (useful for multi-key setups)
    api_key: str | None = None
    # Azure OpenAI / Ollama endpoint override
    base_url: str | None = None
    # Azure OpenAI API version (e.g. "2024-02-01"); ignored for other providers
    api_version: str | None = None


class ScoringDimension(BaseModel):
    name: str
    description: str
    # Relative weight when computing the weighted overall score
    weight: float = Field(default=1.0, gt=0)


class Persona(BaseModel):
    name: str
    display_name: str
    description: str
    background: str
    goals: list[str]
    expertise_level: Literal["novice", "intermediate", "expert"]
    technical: bool
    llm: LLMConfig
    scoring_dimensions: list[ScoringDimension]


# ---------------------------------------------------------------------------
# Evaluation plan — what to test on a specific product
# ---------------------------------------------------------------------------


class TaskStep(BaseModel):
    instruction: str
    # Safety cap: how many browser actions the agent may take for this step
    max_actions: int = Field(default=10, ge=1)


class Task(BaseModel):
    name: str
    description: str
    # If omitted, the runner uses the plan's target_url
    start_url: str | None = None
    steps: list[TaskStep]

    @model_validator(mode="after")
    def _at_least_one_step(self) -> Task:
        if not self.steps:
            raise ValueError(f"Task '{self.name}' must define at least one step.")
        return self


class EvaluationPlan(BaseModel):
    """A plan describes what to test on a specific product/URL.

    It references personas by name — they are resolved at load time from the
    personas directory configured by the user.
    """

    name: str
    description: str
    target_url: str
    # Names that must match the `name` field of loaded Persona files
    personas: list[str]
    tasks: list[Task]

    @model_validator(mode="after")
    def _non_empty(self) -> EvaluationPlan:
        if not self.personas:
            raise ValueError("Plan must reference at least one persona.")
        if not self.tasks:
            raise ValueError("Plan must define at least one task.")
        return self


# ---------------------------------------------------------------------------
# Runtime / evaluation result models
# ---------------------------------------------------------------------------


class BrowserAction(BaseModel):
    """Structured response returned by the LLM at each evaluation step."""

    action_type: Literal["click", "type", "scroll", "navigate", "wait", "done"]
    # CSS selector or ARIA role/label used for click / type actions
    selector: str | None = None
    # Text to fill into an input (for "type" actions)
    text: str | None = None
    # Destination URL (for "navigate" actions)
    url: str | None = None
    # Scroll direction and pixel amount (for "scroll" actions)
    direction: Literal["up", "down"] | None = None
    amount: int | None = None
    # Milliseconds to pause (for "wait" actions)
    wait_ms: int | None = None
    # The persona's in-character observation of the current page
    observation: str
    # Why the persona is taking this particular action
    reasoning: str


class Finding(BaseModel):
    """A single moment captured during an evaluation step."""

    task_name: str
    step_instruction: str
    url: str
    observation: str
    reasoning: str
    action_taken: str
    timestamp: datetime = Field(default_factory=datetime.now)


class DimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0, le=10)
    rationale: str


class PersonaReport(BaseModel):
    persona_name: str
    persona_display_name: str
    target_url: str
    findings: list[Finding]
    dimension_scores: list[DimensionScore]
    overall_score: float = Field(ge=0, le=10)
    summary: str
    recommendations: list[str]
    generated_at: datetime = Field(default_factory=datetime.now)


class EvaluationReport(BaseModel):
    plan_name: str
    target_url: str
    persona_reports: list[PersonaReport]
    generated_at: datetime = Field(default_factory=datetime.now)
