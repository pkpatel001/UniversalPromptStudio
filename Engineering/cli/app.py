"""
Central CLI application definition.
"""

from __future__ import annotations

import typer
from rich.console import Console

from .commands import (
    build,
    config,
    docs,
    doctor,
    generate,
    manifest,
    plugin,
    provider,
    release,
    validate,
    version,
)
from .output.console import print_banner

console = Console()

app = typer.Typer(
    add_completion=False,
    help="Engineering Toolkit for Universal Prompt Studio",
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """
    Universal Prompt Studio Engineering Toolkit
    """
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print("[bold yellow]Quick Start[/bold yellow]")
        console.print()
        console.print("  python -m Engineering validate")
        console.print("  python -m Engineering config")
        console.print("  python -m Engineering version")
        console.print()


# Operational commands
app.command(name="version")(version.version)
app.command(name="validate")(validate.validate)
app.command(name="config")(config.config)

# Future command groups (clean registration, no fake implementations)
app.add_typer(doctor.app, name="doctor")
app.add_typer(docs.app, name="docs")
app.add_typer(build.app, name="build")
app.add_typer(generate.app, name="generate")
app.add_typer(release.app, name="release")
app.add_typer(manifest.app, name="manifest")
app.add_typer(plugin.app, name="plugin")
app.add_typer(provider.app, name="provider")
