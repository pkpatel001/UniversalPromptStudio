"""Generate command group."""

from __future__ import annotations

import typer

from Engineering.cli.output.console import console
from Engineering.Templates import built_in_definition_repository

app = typer.Typer(help="Generate project assets")
templates_app = typer.Typer(help="Discover and validate template definitions")


@app.callback(invoke_without_command=True)
def generate_main(ctx: typer.Context) -> None:
    """Generate project assets."""
    if ctx.invoked_subcommand is None:
        console.print("[yellow]Generation subsystem is not yet implemented.[/yellow]")


@templates_app.callback(invoke_without_command=True)
def list_templates(ctx: typer.Context) -> None:
    """List built-in template definitions."""

    if ctx.invoked_subcommand is not None:
        return
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


@templates_app.command(name="inspect")
def inspect_template(template_id: str, version: str | None = None) -> None:
    """Display one built-in template definition."""

    definition = built_in_definition_repository().resolve(template_id, version)
    console.print(f"[bold cyan]{definition.template_id}[/bold cyan]")
    console.print(f"Version: {definition.version}")
    console.print(f"Name: {definition.metadata.name}")
    console.print(f"Category: {definition.metadata.category.value}")
    if definition.metadata.description:
        console.print(f"Description: {definition.metadata.description}")
    console.print("Variables:")
    for variable in definition.variables:
        console.print(
            f"  {variable.name}: {variable.value_type} ({variable.kind.value})"
        )
    console.print("Artifacts:")
    for artifact in definition.artifacts:
        console.print(
            f"  {artifact.relative_path} <- {artifact.source_template_id}"
        )


@templates_app.command(name="validate")
def validate_templates() -> None:
    """Validate all built-in template definitions and source references."""

    definitions = built_in_definition_repository().definitions()
    console.print(
        f"[green]Validated {len(definitions)} template definition(s).[/green]"
    )


@app.command(name="provider")
def generate_provider() -> None:
    """Generate provider."""
    console.print("[yellow]Provider generation is not yet implemented.[/yellow]")


@app.command(name="plugin")
def generate_plugin() -> None:
    """Generate plugin."""
    console.print("[yellow]Plugin generation is not yet implemented.[/yellow]")


app.add_typer(templates_app, name="templates")
