from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from hafermilch import __version__
from hafermilch.browser.factory import BrowserBackend
from hafermilch.core.exceptions import HafermilchError
from hafermilch.evaluation.runner import EvaluationRunner
from hafermilch.personas.loader import (
    load_personas_from_dir,
    load_plan,
    resolve_plan_personas,
)
from hafermilch.reporting.reporter import Reporter

app = typer.Typer(
    name="hafermilch",
    help="Multi-persona LLM agents that evaluate your product's UI/UX.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(RichHandler(console=console, show_path=False))


@app.command()
def run(
    plan: Annotated[
        Path,
        typer.Argument(help="Path to the evaluation plan YAML file."),
    ],
    personas_dir: Annotated[
        Path,
        typer.Option("--personas-dir", "-p", help="Directory of persona YAML files."),
    ] = Path("examples/personas"),
    output_dir: Annotated[
        Path,
        typer.Option("--output", "-o", help="Directory to write reports into."),
    ] = Path("reports"),
    browser: Annotated[
        BrowserBackend,
        typer.Option("--browser", "-b", help="Browser backend to use."),
    ] = "playwright",
    headless: Annotated[
        bool,
        typer.Option("--headless/--no-headless", help="Run browser in headless mode."),
    ] = True,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v"),
    ] = False,
) -> None:
    """Run an evaluation plan against a live product URL."""
    _setup_logging(verbose)

    try:
        evaluation_plan = load_plan(plan)
        all_personas = load_personas_from_dir(personas_dir)
        resolved = resolve_plan_personas(evaluation_plan, all_personas)
    except HafermilchError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1) from None

    console.rule(f"[bold]hafermilch v{__version__}[/bold]")
    console.print(f"Plan:     [cyan]{evaluation_plan.name}[/cyan]")
    console.print(f"Target:   [cyan]{evaluation_plan.target_url}[/cyan]")
    console.print(f"Browser:  [cyan]{browser}[/cyan]")
    console.print(f"Personas: {', '.join(p.display_name for p in resolved)}\n")

    try:
        report = asyncio.run(
            EvaluationRunner(
                browser_backend=browser,
                headless=headless,
            ).run(evaluation_plan, resolved)
        )
    except HafermilchError as exc:
        console.print(f"[red]Evaluation error:[/red] {exc}")
        raise typer.Exit(code=1) from None

    # Print summary table
    table = Table(title="Results", show_header=True)
    table.add_column("Persona")
    table.add_column("Score", justify="center")
    table.add_column("Findings", justify="right")
    for pr in report.persona_reports:
        table.add_row(
            pr.persona_display_name,
            f"{pr.overall_score:.1f} / 10",
            str(len(pr.findings)),
        )
    console.print(table)

    # Write output
    output_dir.mkdir(parents=True, exist_ok=True)
    reporter = Reporter()
    reporter.to_json(report, output_dir / "report.json")
    reporter.to_markdown(report, output_dir / "report.md")
    reporter.to_html(report, output_dir / "report.html")
    console.print(f"\nReports written to [green]{output_dir}/[/green]")


@app.command()
def validate(
    personas_dir: Annotated[
        Path | None,
        typer.Option("--personas-dir", "-p", help="Directory of persona YAML files."),
    ] = None,
    plan: Annotated[
        Path | None,
        typer.Option("--plan", help="Path to an evaluation plan YAML file."),
    ] = None,
) -> None:
    """Validate persona and/or plan YAML files without running an evaluation."""
    _setup_logging(verbose=False)

    if personas_dir:
        try:
            personas = load_personas_from_dir(personas_dir)
            console.print(f"[green]{len(personas)} persona(s) valid:[/green]")
            for p in personas.values():
                console.print(
                    f"  [cyan]{p.name}[/cyan] — {p.display_name} ({p.llm.provider}/{p.llm.model})"
                )
        except HafermilchError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from None

    if plan:
        try:
            evaluation_plan = load_plan(plan)
            console.print(f"[green]Plan valid:[/green] {evaluation_plan.name}")
            console.print(f"  Target: {evaluation_plan.target_url}")
            console.print(f"  Personas: {', '.join(evaluation_plan.personas)}")
            console.print(f"  Tasks: {len(evaluation_plan.tasks)}")
        except HafermilchError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from None

    if not personas_dir and not plan:
        console.print("Provide --personas-dir and/or --plan to validate.")
        raise typer.Exit(code=1) from None


@app.callback(invoke_without_command=True)
def version_flag(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", is_eager=True, help="Show version and exit.")
    ] = False,
) -> None:
    if version:
        console.print(f"hafermilch {__version__}")
        raise typer.Exit()
