from __future__ import annotations

import logging
from pathlib import Path

from hafermilch.browser.base import BaseBrowserAgent
from hafermilch.browser.factory import BrowserBackend, create_browser_agent
from hafermilch.core.exceptions import EvaluationError
from hafermilch.core.models import (
    BrowserAction,
    Credentials,
    DimensionScore,
    EvaluationPlan,
    EvaluationReport,
    Finding,
    LLMReport,
    Persona,
    PersonaReport,
    Task,
    TaskStep,
    TokenUsage,
)
from hafermilch.evaluation.prompter import Prompter
from hafermilch.llm.base import LLMProvider
from hafermilch.llm.factory import create_llm_provider

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Orchestrates personas, browser agents, and LLM providers."""

    def __init__(
        self,
        browser_backend: BrowserBackend = "playwright",
        headless: bool = True,
        record: bool = False,
        output_dir: Path | None = None,
    ) -> None:
        self._browser_backend = browser_backend
        self._headless = headless
        self._record = record
        self._output_dir = output_dir
        self._prompter = Prompter()

    async def run(
        self,
        plan: EvaluationPlan,
        personas: list[Persona],
    ) -> EvaluationReport:
        """Run all personas through the plan and return a combined report."""
        persona_reports: list[PersonaReport] = []

        for persona in personas:
            logger.info(
                "Starting evaluation — persona: %s [browser: %s]",
                persona.display_name,
                self._browser_backend,
            )
            try:
                report = await self._run_persona(persona, plan)
                persona_reports.append(report)
            except Exception as exc:
                raise EvaluationError(
                    f"Evaluation failed for persona '{persona.name}': {exc}"
                ) from exc

        total_usage: TokenUsage | None = None
        for pr in persona_reports:
            total_usage = TokenUsage.accumulate(total_usage, pr.total_usage)

        return EvaluationReport(
            plan_name=plan.name,
            target_url=plan.target_url,
            persona_reports=persona_reports,
            total_usage=total_usage,
        )

    async def _run_persona(self, persona: Persona, plan: EvaluationPlan) -> PersonaReport:
        provider = create_llm_provider(persona.llm)
        all_findings: list[Finding] = []

        agent = create_browser_agent(
            self._browser_backend,
            self._headless,
            record=self._record,
            record_dir=self._output_dir,
        )
        async with agent:
            for task in plan.tasks:
                start_url = task.start_url or plan.target_url
                logger.info("  Task: %s → %s", task.name, start_url)
                await agent.navigate(start_url)

                for step in task.steps:
                    findings = await self._run_step(
                        agent=agent,
                        persona=persona,
                        provider=provider,
                        task=task,
                        step=step,
                        credentials=plan.credentials,
                    )
                    all_findings.extend(findings)

        return await self._build_persona_report(
            persona=persona,
            plan=plan,
            provider=provider,
            findings=all_findings,
        )

    async def _run_step(
        self,
        agent: BaseBrowserAgent,
        persona: Persona,
        provider: LLMProvider,
        task: Task,
        step: TaskStep,
        credentials: Credentials | None = None,
    ) -> list[Finding]:
        findings: list[Finding] = []

        for action_num in range(step.max_actions):
            page_ctx = await agent.capture()
            messages = self._prompter.build_action_prompt(
                persona=persona,
                context=page_ctx,
                step=step,
                selector_hint=agent.selector_hint,
                credentials=credentials,
                include_screenshot=provider.supports_vision,
            )

            logger.debug(
                "    [%d/%d] %s | tree_len=%d",
                action_num + 1,
                step.max_actions,
                step.instruction,
                len(page_ctx.accessibility_tree or ""),
            )

            action, usage = await provider.complete_json(messages, BrowserAction)
            logger.info(
                "    Action: %s | selector=%s | text=%s",
                action.action_type,
                action.selector,
                action.text,
            )

            findings.append(
                Finding(
                    task_name=task.name,
                    step_instruction=step.instruction,
                    url=page_ctx.url,
                    observation=action.observation,
                    reasoning=action.reasoning,
                    action_taken=action.action_type,
                    screenshot=page_ctx.screenshot,
                    usage=usage,
                )
            )

            if action.action_type == "done":
                break

            try:
                await agent.execute(action)
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
        llm_report, report_usage = await provider.complete_json(messages, LLMReport)

        dimension_scores = [
            DimensionScore(
                dimension=d["dimension"],
                score=d["score"],
                rationale=d["rationale"],
            )
            for d in llm_report.dimension_scores
        ]

        total_usage: TokenUsage | None = None
        for f in findings:
            total_usage = TokenUsage.accumulate(total_usage, f.usage)
        total_usage = TokenUsage.accumulate(total_usage, report_usage)

        return PersonaReport(
            persona_name=persona.name,
            persona_display_name=persona.display_name,
            target_url=plan.target_url,
            findings=findings,
            dimension_scores=dimension_scores,
            overall_score=llm_report.overall_score,
            summary=llm_report.summary,
            recommendations=llm_report.recommendations,
            total_usage=total_usage,
        )
