"""CLI adapter for E-012 read-only manifest inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ManifestError
from Engineering.core.paths import get_paths
from Engineering.ManifestSystem import ManifestInspectionService

app = typer.Typer(help="Discover and validate engineering manifests")


@app.callback(invoke_without_command=True)
def manifest_main(ctx: typer.Context) -> None:
    """Discover and validate engineering manifests."""

    if ctx.invoked_subcommand is None:
        console.print("Run 'python -m Engineering manifest inspect' to scan manifests.")


@app.command(name="types")
def manifest_types() -> None:
    """List registered manifest families."""

    service = ManifestInspectionService()
    for adapter in service.registry.adapters:
        versions = ", ".join(str(item) for item in adapter.spec.supported_schema_versions)
        console.print(
            f"{adapter.spec.manifest_id}: {adapter.spec.filename} (schemas: {versions})"
        )


@app.command(name="inspect")
def manifest_inspect(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Recursively discover and validate registered manifests."""

    inspection_root = root or get_paths().root
    try:
        report = ManifestInspectionService().inspect(inspection_root)
    except ManifestError as exc:
        console.print(f"FAILED manifest.inspect: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    for record in report.records:
        console.print(
            f"VALID {record.manifest_id} schema={record.schema_version} "
            f"path={record.relative_path} sha256={record.sha256}"
        )
    for issue in report.issues:
        console.print(f"FAILED {issue.code} path={issue.relative_path}: {issue.message}")
    console.print(report.summary)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
