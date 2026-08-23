"""Read-only CLI adapter for E-013.1 plugin metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import PluginError
from Engineering.core.paths import get_paths
from Engineering.PluginSystem import PluginCatalog, PluginInspectionReport, PluginService

app = typer.Typer(help="Discover, validate, and inspect plugin metadata")


@app.callback(invoke_without_command=True)
def plugin_main(ctx: typer.Context) -> None:
    """Discover, validate, and inspect plugin metadata."""

    if ctx.invoked_subcommand is None:
        console.print("Run 'python -m Engineering plugin list' to discover plugins.")


def _root(value: Path | None) -> Path:
    return value or get_paths().plugins


def _print_report(report: PluginInspectionReport) -> None:
    for record in report.records:
        console.print(
            f"VALID {record.plugin_id} version={record.version} "
            f"path={record.relative_path}"
        )
    for issue in report.issues:
        console.print(f"FAILED {issue.code} path={issue.relative_path}: {issue.message}")
    console.print(report.summary)


def _inspect(root: Path) -> PluginInspectionReport:
    try:
        return PluginService().inspect(root)
    except PluginError as exc:
        console.print(f"FAILED plugin.inspect: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc


@app.command(name="list")
def plugin_list(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """List all validated plugin manifests below a root."""

    report = _inspect(_root(root))
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="inspect")
def plugin_inspect(
    plugin_id: str,
    version: Annotated[str | None, typer.Option("--version")] = None,
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Inspect one plugin by ID and optional exact version."""

    report = _inspect(_root(root))
    if not report.passed:
        _print_report(report)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
    try:
        record = PluginCatalog(report.records).resolve(plugin_id, version)
    except PluginError as exc:
        console.print(f"FAILED plugin.resolve: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc

    metadata = record.manifest.metadata
    console.print(f"Plugin: {metadata.plugin_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Entry point: {metadata.entry_point.value}")
    console.print(f"Description: {metadata.description}")
    capabilities = ", ".join(
        item.capability_id for item in record.manifest.capabilities
    )
    permissions = ", ".join(
        item.permission_id for item in record.manifest.permissions
    )
    console.print(f"Capabilities: {capabilities or 'none'}")
    console.print(f"Permissions (metadata only): {permissions or 'none'}")
    for dependency in record.manifest.dependencies:
        console.print(
            f"Dependency: {dependency.plugin_id.value} "
            f"{dependency.version_specifier}"
        )
    console.print(f"Manifest: {record.relative_path}")


@app.command(name="validate")
def plugin_validate(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Validate every plugin manifest below a root."""

    report = _inspect(_root(root))
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
