"""Read-only CLI adapter for E-014 AI-provider metadata."""

from __future__ import annotations

from pathlib import Path

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import ProviderManifestReader

app = typer.Typer(help="Inspect AI-provider SDK metadata without executing code")


@app.callback(invoke_without_command=True)
def provider_main(ctx: typer.Context) -> None:
    """Inspect AI-provider SDK metadata."""

    if ctx.invoked_subcommand is None:
        console.print(
            "Run 'python -m Engineering provider inspect MANIFEST' "
            "to validate provider metadata."
        )


@app.command(name="inspect")
def provider_inspect(manifest: Path) -> None:
    """Validate and display one exact AI-provider manifest."""

    try:
        parsed = ProviderManifestReader().read(manifest)
    except ProviderError as exc:
        console.print(f"FAILED provider.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    metadata = parsed.metadata
    console.print(f"Provider: {metadata.provider_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Entry point: {metadata.entry_point.value}")
    console.print(f"Transport: {metadata.transport.value}")
    console.print(f"Authentication: {metadata.authentication.value}")
    console.print(
        "Capabilities: " + ", ".join(capability.value for capability in parsed.capabilities)
    )
    console.print(f"Description: {metadata.description}")
    console.print("Provider code imported: no")
    console.print("Network requests: none")
    console.print("Credential access: none")
