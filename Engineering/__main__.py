"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Entry Point

Run with:

    python -m Engineering

===============================================================================
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

APP_NAME = "Universal Prompt Studio"
TOOLKIT_NAME = "Engineering Toolkit"
VERSION = "0.1.0-alpha"

console = Console()
app = typer.Typer(
    add_completion=False,
    help="Engineering Toolkit for Universal Prompt Studio",
)


def show_banner() -> None:
    """Display application banner."""

    console.print()
    console.rule(f"[bold cyan]{APP_NAME}[/bold cyan]")
    console.print(
        f"[bold green]{TOOLKIT_NAME}[/bold green] "
        f"[white]v{VERSION}[/white]"
    )
    console.print()


def show_commands() -> None:
    """Display available command groups."""

    table = Table(title="Available Commands", show_header=True)

    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("docs", "Documentation generation and validation")
    table.add_row("build", "Build engineering artifacts")
    table.add_row("generate", "Generate project assets")
    table.add_row("validate", "Validate manifests and documentation")
    table.add_row("doctor", "Check project health")
    table.add_row("config", "Display configuration information")
    table.add_row("version", "Display toolkit version")
    table.add_row("help", "Display help")

    console.print(table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    Universal Prompt Studio Engineering Toolkit
    """

    if ctx.invoked_subcommand is None:
        show_banner()
        show_commands()

        console.print()
        console.print(
            "[bold yellow]Quick Start[/bold yellow]"
        )
        console.print()

        console.print("  python -m Engineering docs generate")
        console.print("  python -m Engineering docs validate")
        console.print("  python -m Engineering build")
        console.print("  python -m Engineering doctor")

        console.print()


@app.command()
def version() -> None:
    """Display toolkit version."""

    console.print(f"{TOOLKIT_NAME} {VERSION}")


@app.command()
def doctor() -> None:
    """Future project diagnostics."""

    console.print("[yellow]Doctor is not implemented yet.[/yellow]")


@app.command()
def docs() -> None:
    """Documentation command placeholder."""

    console.print("[yellow]Documentation subsystem coming soon.[/yellow]")


@app.command()
def build() -> None:
    """Build command placeholder."""

    console.print("[yellow]Build subsystem coming soon.[/yellow]")


@app.command()
def validate() -> None:
    """Validation command placeholder."""

    console.print("[yellow]Validation subsystem coming soon.[/yellow]")


@app.command()
def generate() -> None:
    """Generation command placeholder."""

    console.print("[yellow]Generation subsystem coming soon.[/yellow]")


@app.command()
def config() -> None:
    """Configuration placeholder."""

    console.print("[yellow]Configuration subsystem coming soon.[/yellow]")


if __name__ == "__main__":
    app()