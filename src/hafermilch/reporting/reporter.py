from __future__ import annotations

import base64
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, select_autoescape

from hafermilch.core.models import EvaluationReport, PersonaReport

_ACTION_BADGE: dict[str, tuple[str, str]] = {
    "click": ("#dbeafe", "#1d4ed8"),
    "type": ("#d1fae5", "#065f46"),
    "navigate": ("#ede9fe", "#5b21b6"),
    "scroll": ("#f3f4f6", "#374151"),
    "wait": ("#fef3c7", "#92400e"),
    "done": ("#dcfce7", "#166534"),
}


def _score_color(score: float) -> str:
    if score >= 7.5:
        return "#16a34a"
    if score >= 5.0:
        return "#d97706"
    return "#dc2626"


def _action_badge(action: str) -> dict[str, str]:
    bg, fg = _ACTION_BADGE.get(action, ("#f3f4f6", "#374151"))
    return {"bg": bg, "fg": fg}


def _b64png(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _format_tokens(n: int) -> str:
    return f"{n:,}"


class Reporter:
    """Renders an EvaluationReport as Markdown, JSON, or HTML."""

    def __init__(self) -> None:
        self._env = Environment(autoescape=select_autoescape(["html"]))
        self._env.filters["score_color"] = _score_color
        self._env.filters["action_badge"] = _action_badge
        self._env.filters["b64png"] = _b64png
        self._env.filters["format_tokens"] = _format_tokens

    def to_json(self, report: EvaluationReport, path: Path) -> None:
        path.write_text(report.model_dump_json(indent=2))

    def to_markdown(self, report: EvaluationReport, path: Path) -> None:
        path.write_text(self._render_markdown(report))

    def to_html(self, report: EvaluationReport, path: Path) -> None:
        template_text = (
            files("hafermilch.reporting").joinpath("templates/report.html").read_text("utf-8")
        )
        tmpl = self._env.from_string(template_text)
        path.write_text(tmpl.render(report=report), encoding="utf-8")

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    def _render_markdown(self, report: EvaluationReport) -> str:
        lines: list[str] = [
            "# Hafermilch Evaluation Report",
            "",
            f"**Target:** {report.target_url}  ",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
        ]

        lines += [
            "## Persona Scorecards",
            "",
            "| Persona | Overall Score |",
            "| ------- | :-----------: |",
        ]
        for pr in report.persona_reports:
            lines.append(f"| {pr.persona_display_name} | {pr.overall_score:.1f} / 10 |")
        lines.append("")

        for pr in report.persona_reports:
            lines += self._render_persona_section(pr)

        return "\n".join(lines)

    def _render_persona_section(self, pr: PersonaReport) -> list[str]:
        lines: list[str] = [
            "---",
            "",
            f"## {pr.persona_display_name}",
            "",
            f"**Overall score:** {pr.overall_score:.1f} / 10",
            "",
            "### Summary",
            "",
            pr.summary,
            "",
            "### Dimension Scores",
            "",
            "| Dimension | Score | Rationale |",
            "| --------- | :---: | --------- |",
        ]
        for ds in pr.dimension_scores:
            lines.append(f"| {ds.dimension} | {ds.score:.1f} | {ds.rationale} |")

        lines += ["", "### Recommendations", ""]
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
