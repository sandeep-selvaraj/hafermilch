from __future__ import annotations

import json
from pathlib import Path

from hafermilch.core.models import EvaluationReport, PersonaReport


class Reporter:
    """Renders an EvaluationReport as Markdown or JSON."""

    def to_json(self, report: EvaluationReport, path: Path) -> None:
        path.write_text(report.model_dump_json(indent=2))

    def to_markdown(self, report: EvaluationReport, path: Path) -> None:
        path.write_text(self._render_markdown(report))

    def _render_markdown(self, report: EvaluationReport) -> str:
        lines: list[str] = [
            f"# Hafermilch Evaluation Report",
            f"",
            f"**Target:** {report.target_url}  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            f"",
        ]

        # Summary table
        lines += [
            "## Persona Scorecards",
            "",
            "| Persona | Overall Score |",
            "| ------- | :-----------: |",
        ]
        for pr in report.persona_reports:
            lines.append(
                f"| {pr.persona_display_name} | {pr.overall_score:.1f} / 10 |"
            )
        lines.append("")

        for pr in report.persona_reports:
            lines += self._render_persona_section(pr)

        return "\n".join(lines)

    def _render_persona_section(self, pr: PersonaReport) -> list[str]:
        lines: list[str] = [
            f"---",
            f"",
            f"## {pr.persona_display_name}",
            f"",
            f"**Overall score:** {pr.overall_score:.1f} / 10",
            f"",
            f"### Summary",
            f"",
            pr.summary,
            f"",
            f"### Dimension Scores",
            f"",
            "| Dimension | Score | Rationale |",
            "| --------- | :---: | --------- |",
        ]
        for ds in pr.dimension_scores:
            lines.append(f"| {ds.dimension} | {ds.score:.1f} | {ds.rationale} |")

        lines += [
            "",
            "### Recommendations",
            "",
        ]
        for rec in pr.recommendations:
            lines.append(f"- {rec}")

        lines += [
            "",
            "### Evaluation Log",
            "",
            "| Task | Step | URL | Observation | Action |",
            "| ---- | ---- | --- | ----------- | ------ |",
        ]
        for f in pr.findings:
            obs = f.observation.replace("|", "&#124;").replace("\n", " ")
            lines.append(
                f"| {f.task_name} | {f.step_instruction} | {f.url} | {obs} | {f.action_taken} |"
            )
        lines.append("")

        return lines
