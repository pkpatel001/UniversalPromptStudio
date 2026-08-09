"""
Doctor command group (placeholder).
"""

from __future__ import annotations

import typer

from Engineering.cli.output.console import console

app = typer.Typer(help="Project diagnostics")


@app.callback(invoke_without_command=True)
def doctor_main() -> None:
    """Project diagnostics."""
    console.print("[yellow]Doctor subsystem is not yet implemented.[/yellow]")


@app.command(name="check")
def doctor_check() -> None:
    """Run project health checks."""
    console.print("[yellow]Doctor check is not yet implemented.[/yellow]")


@app.command(name="info")
def doctor_info() -> None:
    """Show project information."""
    console.print("[yellow]Doctor info is not yet implemented.[/yellow]")