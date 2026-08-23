"""Read-only CLI adapter for E-015 theme metadata."""

from __future__ import annotations

from pathlib import Path

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ThemeError
from Engineering.ThemeSystem import ThemeManifestReader

app = typer.Typer(help="Inspect declarative theme metadata without applying styles")


@app.callback(invoke_without_command=True)
def theme_main(ctx: typer.Context) -> None:
    """Inspect theme SDK metadata."""

    if ctx.invoked_subcommand is None:
        console.print(
            "Run 'python -m Engineering theme inspect MANIFEST' "
            "to validate declarative theme metadata."
        )


@app.command(name="inspect")
def theme_inspect(manifest: Path) -> None:
    """Validate and display one exact theme manifest."""

    try:
        parsed = ThemeManifestReader().read(manifest)
    except ThemeError as exc:
        console.print(f"FAILED theme.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    metadata = parsed.metadata
    console.print(f"Theme: {metadata.theme_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Default appearance: {parsed.default_appearance.value}")
    console.print("Appearances: " + ", ".join(item.appearance.value for item in parsed.palettes))
    console.print(f"Description: {metadata.description}")
    console.print("Theme assets loaded: no")
    console.print("Styles applied: no")
    console.print("Code executed: no")


__all__ = ["app"]
