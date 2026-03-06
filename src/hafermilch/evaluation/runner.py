from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

from hafermilch.browser.agent import BrowserAgent
from hafermilch.core.exceptions import EvaluationError
from hafermilch.core.models import (
    BrowserAction,
    DimensionScore,
    EvaluationPlan,
    EvaluationReport,
    Finding,
    Persona,
    PersonaReport,
    Task,
    TaskStep,
)
from hafermilch.evaluation.prompter import Prompter
from hafermilch.llm.base import LLMProvider
from hafermilch.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


class _LLMReport(BaseModel):
    """Schema for the LLM's final evaluation response."""

    overall_score: float = Field(ge=0, le=10)
    summary: str
    dimension_scores: list[dict[str, Any]]
    recommendations: list[str]


class EvaluationRunner:
    """Orchestrates personas, browser, and LLM providers to produce reports."""

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._prompter = Prompter()
        self._browser_agent = BrowserAgent()

    async def run(
        self,
        plan: EvaluationPlan,
        personas: list[Persona],
    ) -> EvaluationReport:
        """Run all personas through the plan and return a combined report."""
        persona_reports: list[PersonaReport] = []

        for persona in personas:
            logger.info("Starting evaluation — persona: %s", persona.display_name)
            try:
                report = await self._run_persona(persona, plan)
                persona_reports.append(report)
            except Exception as exc:
                raise EvaluationError(
                    f"Evaluation failed for persona '{persona.name}': {exc}"
                ) from exc

        return EvaluationReport(
            plan_name=plan.name,
            target_url=plan.target_url,
            persona_reports=persona_reports,
        )

    async def _run_persona(
        self, persona: Persona, plan: EvaluationPlan
    ) -> PersonaReport:
        provider = LLMProviderFactory.create(persona.llm)
        all_findings: list[Finding] = []

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self._headless)
            ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()

            for task in plan.tasks:
                start_url = task.start_url or plan.target_url
                logger.info("  Task: %s → %s", task.name, start_url)
                await page.goto(start_url, wait_until="domcontentloaded")

                for step in task.steps:
                    findings = await self._run_step(
                        page=page,
                        persona=persona,
                        provider=provider,
                        task=task,
                        step=step,
                    )
                    all_findings.extend(findings)

            await browser.close()

        return await self._build_persona_report(
            persona=persona,
            plan=plan,
            provider=provider,
            findings=all_findings,
        )

    async def _run_step(
        self,
        page: Any,
        persona: Persona,
        provider: LLMProvider,
        task: Task,
        step: TaskStep,
    ) -> list[Finding]:
        findings: list[Finding] = []
        use_vision = provider.supports_vision

        for action_num in range(step.max_actions):
            page_ctx = await self._browser_agent.capture(page)
            messages = self._prompter.build_action_prompt(
                persona=persona,
                context=page_ctx,
                step=step,
                include_screenshot=use_vision,
            )

            logger.debug(
                "    [%d/%d] %s", action_num + 1, step.max_actions, step.instruction
            )

            action: BrowserAction = await provider.complete_json(
                messages, BrowserAction
            )

            findings.append(
                Finding(
                    task_name=task.name,
                    step_instruction=step.instruction,
                    url=page_ctx.url,
                    observation=action.observation,
                    reasoning=action.reasoning,
                    action_taken=action.action_type,
                )
            )

            if action.action_type == "done":
                break

            try:
                await self._browser_agent.execute(page, action)
            except Exception as exc:
                logger.warning("    Browser action failed: %s", exc)
                findings[-1].observation += f" [action failed: {exc}]"
                break

        return findings

    async def _build_persona_report(
        self,
        persona: Persona,
        plan: EvaluationPlan,
        provider: LLMProvider,
        findings: list[Finding],
    ) -> PersonaReport:
        findings_summary = "\n\n".join(
            f"[{f.task_name} / {f.step_instruction}]\n"
            f"URL: {f.url}\n"
            f"Observation: {f.observation}\n"
            f"Action taken: {f.action_taken}"
            for f in findings
        )

        messages = self._prompter.build_report_prompt(persona, findings_summary)
        llm_report: _LLMReport = await provider.complete_json(messages, _LLMReport)

        dimension_scores = [
            DimensionScore(
                dimension=d["dimension"],
                score=d["score"],
                rationale=d["rationale"],
            )
            for d in llm_report.dimension_scores
        ]

        return PersonaReport(
            persona_name=persona.name,
            persona_display_name=persona.display_name,
            target_url=plan.target_url,
            findings=findings,
            dimension_scores=dimension_scores,
            overall_score=llm_report.overall_score,
            summary=llm_report.summary,
            recommendations=llm_report.recommendations,
        )
