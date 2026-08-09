"""
Documentation command group (placeholder).
"""

from __future__ import annotations

import typer

from Engineering.cli.output.console import console

app = typer.Typer(help="Documentation generation and validation")


@app.callback(invoke_without_command=True)
def docs_main() -> None:
    """Documentation subsystem."""
    console.print("[yellow]Documentation subsystem is not yet implemented.[/yellow]")


@app.command(name="generate")
def docs_generate() -> None:
    """Generate documentation."""
    console.print("[yellow]Documentation generation is not yet implemented.[/yellow]")


@app.command(name="validate")
def docs_validate() -> None:
    """Validate documentation."""
    console.print("[yellow]Documentation validation is not yet implemented.[/yellow]")