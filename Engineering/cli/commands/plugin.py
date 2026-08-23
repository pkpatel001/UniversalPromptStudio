"""Read-only CLI adapter for E-013 plugin metadata validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import PluginError
from Engineering.core.paths import get_paths
from Engineering.PluginSystem import (
    PluginCatalog,
    PluginDiscoveryRoot,
    PluginService,
    PluginValidationReport,
)

app = typer.Typer(help="Discover, validate, and inspect plugin metadata")


@app.callback(invoke_without_command=True)
def plugin_main(ctx: typer.Context) -> None:
    """Discover, validate, and inspect plugin metadata."""

    if ctx.invoked_subcommand is None:
        console.print("Run 'python -m Engineering plugin list' to discover plugins.")


def _roots(values: list[Path] | None) -> tuple[PluginDiscoveryRoot, ...]:
    if not values:
        return (PluginDiscoveryRoot("project", get_paths().plugins),)
    return tuple(
        PluginDiscoveryRoot(f"explicit-{index:04d}", path)
        for index, path in enumerate(values, start=1)
    )


def _print_report(report: PluginValidationReport) -> None:
    for record in report.records:
        console.print(
            f"VALID {record.plugin_id} version={record.version} "
            f"root={record.root_id} path={record.relative_path}"
        )
    for resolution in report.dependency_resolutions:
        console.print(
            f"RESOLVED {resolution.owner_plugin_id}@{resolution.owner_version} -> "
            f"{resolution.dependency_plugin_id}@{resolution.resolved_version} "
            f"({resolution.version_specifier})"
        )
    for issue in report.issues:
        console.print(
            f"FAILED {issue.code} root={issue.root_id} "
            f"path={issue.relative_path}: {issue.message}"
        )
    console.print(report.summary)


def _validate(roots: tuple[PluginDiscoveryRoot, ...]) -> PluginValidationReport:
    try:
        return PluginService().validate_roots(roots)
    except PluginError as exc:
        console.print(f"FAILED plugin.validate: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc


@app.command(name="list")
def plugin_list(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """List dependency-coherent plugins below one or more roots."""

    report = _validate(_roots(root))
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="inspect")
def plugin_inspect(
    plugin_id: str,
    version: Annotated[str | None, typer.Option("--version")] = None,
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Inspect one plugin by ID and optional exact version."""

    roots = _roots(root)
    report = _validate(roots)
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
    console.print(f"Manifest: {record.root_id}:{record.relative_path}")


@app.command(name="validate")
def plugin_validate(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Validate compatibility and dependencies below one or more roots."""

    report = _validate(_roots(root))
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="dependencies")
def plugin_dependencies(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Show deterministic dependency selections without installing anything."""

    report = _validate(_roots(root))
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
