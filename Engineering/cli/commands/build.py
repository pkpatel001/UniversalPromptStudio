"""
Build command group (placeholder).
"""

from __future__ import annotations

import typer

from Engineering.cli.output.console import console

app = typer.Typer(help="Build engineering artifacts")


@app.callback(invoke_without_command=True)
def build_main() -> None:
    """Build engineering artifacts."""
    console.print("[yellow]Build subsystem is not yet implemented.[/yellow]")


@app.command(name="clean")
def build_clean() -> None:
    """Clean build artifacts."""
    console.print("[yellow]Build clean is not yet implemented.[/yellow]")


@app.command(name="run")
def build_run() -> None:
    """Run build process."""
    console.print("[yellow]Build run is not yet implemented.[/yellow]")