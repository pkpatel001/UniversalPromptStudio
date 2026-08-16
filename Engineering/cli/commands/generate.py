"""Generate command group."""

from __future__ import annotations

import typer

from Engineering.cli.output.console import console
from Engineering.Templates import built_in_definition_repository

app = typer.Typer(help="Generate project assets")


@app.callback(invoke_without_command=True)
def generate_main(ctx: typer.Context) -> None:
    """Generate project assets."""
    if ctx.invoked_subcommand is None:
        console.print("[yellow]Generation subsystem is not yet implemented.[/yellow]")


@app.command(name="templates")
def list_templates() -> None:
    """List built-in template definitions."""

    definitions = built_in_definition_repository().definitions()
    if not definitions:
        console.print("[yellow]No template definitions found.[/yellow]")
        return
    for definition in definitions:
        console.print(
            f"[cyan]{definition.template_id}[/cyan] "
            f"v{definition.version} "
            f"[{definition.metadata.category.value}] "
            f"{definition.metadata.name}"
        )


@app.command(name="provider")
def generate_provider() -> None:
    """Generate provider."""
    console.print("[yellow]Provider generation is not yet implemented.[/yellow]")


@app.command(name="plugin")
def generate_plugin() -> None:
    """Generate plugin."""
    console.print("[yellow]Plugin generation is not yet implemented.[/yellow]")
