"""SwarmFlow CLI — Typer-based command-line interface."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="swarmflow",
    help="🐝 SwarmFlow — Lightweight multi-agent swarm orchestration with LangGraph",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


@app.command()
def launch(
    template: str = typer.Argument(
        help="Template name (e.g. hedge-fund, research-lab, startup-pitch)",
    ),
    goal: str = typer.Option(None, "--goal", "-g", help="Override the template's default goal"),
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
    output: str = typer.Option(None, "--output", "-o", help="Save final report to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
):
    """Launch a swarm from a template."""
    _setup_logging(verbose)

    from swarmflow.config import get_config
    from swarmflow.engine.graph import run_swarm
    from swarmflow.engine.templates import list_templates, load_template_by_name

    # Load config
    cfg = get_config(config)

    # Load template
    try:
        tmpl = load_template_by_name(template, cfg.templates_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        available = list_templates(cfg.templates_dir)
        console.print(f"Available templates: {', '.join(available)}")
        raise typer.Exit(1)

    goal_text = goal or tmpl.default_goal
    if not goal_text:
        console.print(
            "[red]Error:[/red] No goal provided. "
            "Use --goal or set default_goal in template."
        )
        raise typer.Exit(1)

    # Display launch info
    console.print(Panel.fit(
        f"[bold cyan]🐝 SwarmFlow[/bold cyan]\n\n"
        f"[bold]Template:[/bold] {tmpl.name}\n"
        f"[bold]Goal:[/bold] {goal_text}\n"
        f"[bold]Workers:[/bold] {len(tmpl.workers)}\n"
        f"[bold]LLM:[/bold] {cfg.llm.provider.value} / {cfg.llm.model}",
        title="Launching Swarm",
        border_style="cyan",
    ))

    # Show worker roster
    table = Table(title="Agent Roster", show_header=True, header_style="bold magenta")
    table.add_column("Agent", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Specialty", style="white")
    table.add_row("leader", "🦞 Leader", "Plans, coordinates, synthesizes")
    for w in tmpl.workers:
        table.add_row(w.name, "🤖 Worker", w.system_prompt[:80] + "...")
    console.print(table)
    console.print()

    # Run the swarm
    worker_configs = tmpl.get_worker_configs()

    try:
        final_state = asyncio.run(
            run_swarm(
                team_name=tmpl.name,
                goal=goal_text,
                worker_configs=worker_configs,
                description=tmpl.description,
            )
        )
    except Exception as e:
        console.print(f"[red]Swarm failed:[/red] {e}")
        logging.exception("Swarm execution error")
        raise typer.Exit(1)

    # Display results
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ Swarm Completed[/bold green]",
        border_style="green",
    ))

    # Show task summary
    tasks = final_state.get("tasks", [])
    if tasks:
        task_table = Table(title="Task Summary", show_header=True, header_style="bold")
        task_table.add_column("ID", style="dim")
        task_table.add_column("Title")
        task_table.add_column("Owner", style="cyan")
        task_table.add_column("Status")
        for task in tasks:
            status_map = {
                "completed": "[green]✅ Done[/green]",
                "failed": "[red]❌ Failed[/red]",
                "in_progress": "[yellow]🔄 Running[/yellow]",
                "pending": "⏳ Pending",
                "blocked": "🚫 Blocked",
            }
            task_table.add_row(
                task.id,
                task.title,
                task.owner,
                status_map.get(task.status.value, task.status.value),
            )
        console.print(task_table)

    # Show final report
    final_report = final_state.get("final_report", "")
    if final_report:
        console.print()
        console.print(Panel(
            final_report,
            title="📊 Final Report",
            border_style="blue",
            expand=True,
        ))

        if output:
            Path(output).write_text(final_report)
            console.print(f"\n[green]Report saved to {output}[/green]")

    # Show errors if any
    errors = final_state.get("errors", [])
    if errors:
        console.print()
        for err in errors:
            console.print(f"[red]⚠️  {err}[/red]")


@app.command()
def templates(
    config: str = typer.Option(None, "--config", "-c", help="Path to config.yaml"),
):
    """List available swarm templates."""
    from swarmflow.config import get_config
    from swarmflow.engine.templates import list_templates, load_template_by_name

    cfg = get_config(config)
    names = list_templates(cfg.templates_dir)

    if not names:
        console.print("[yellow]No templates found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Available Templates", show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Workers", justify="center")
    table.add_column("Description")

    for name in names:
        try:
            tmpl = load_template_by_name(name, cfg.templates_dir)
            table.add_row(name, str(len(tmpl.workers)), tmpl.description[:100])
        except Exception:
            table.add_row(name, "?", "[red]Error loading[/red]")

    console.print(table)


@app.command()
def dashboard(
    port: int = typer.Option(8080, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Dashboard host"),
):
    """Start the real-time monitoring dashboard."""
    import uvicorn

    from swarmflow.dashboard.app import create_app

    console.print(Panel.fit(
        f"[bold cyan]🐝 SwarmFlow Dashboard[/bold cyan]\n\n"
        f"Running at [link]http://{host}:{port}[/link]",
        border_style="cyan",
    ))

    dash_app = create_app()
    uvicorn.run(dash_app, host=host, port=port, log_level="info")


@app.command()
def version():
    """Show SwarmFlow version."""
    from swarmflow import __version__
    console.print(f"SwarmFlow v{__version__}")


if __name__ == "__main__":
    app()
