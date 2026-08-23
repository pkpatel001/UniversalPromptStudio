"""CLI adapter for E-012 read-only manifest inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ManifestError
from Engineering.core.paths import get_paths
from Engineering.ManifestSystem import (
    ManifestInspectionService,
    ManifestMigrationService,
    ManifestValidationService,
)

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
        cardinality = "many" if adapter.spec.allow_multiple else "one"
        console.print(
            f"{adapter.spec.manifest_id}: {adapter.spec.filename} "
            f"(current: {adapter.spec.schema_contract.current_version}; "
            f"readable: {versions}; cardinality: {cardinality})"
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


@app.command(name="validate")
def manifest_validate(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Validate schemas, cardinality, and cross-manifest relationships."""

    validation_root = root or get_paths().root
    try:
        report = ManifestValidationService().validate(validation_root)
    except ManifestError as exc:
        console.print(f"FAILED manifest.validate: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    for record in report.records:
        console.print(
            f"VALID {record.manifest_id} schema={record.schema_version} "
            f"compatibility={record.compatibility.value} path={record.relative_path}"
        )
    for issue in report.issues:
        console.print(f"FAILED {issue.code} path={issue.relative_path}: {issue.message}")
    console.print(report.summary)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="migrations")
def manifest_migrations(
    root: Annotated[Path | None, typer.Option("--root")] = None,
) -> None:
    """Plan schema upgrades without modifying manifest files."""

    migration_root = root or get_paths().root
    try:
        report = ManifestMigrationService().plan(migration_root)
    except ManifestError as exc:
        console.print(f"FAILED manifest.migrations: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    for plan in report.plans:
        console.print(
            f"PLAN {plan.manifest_id} schema={plan.source_version}->{plan.target_version} "
            f"path={plan.relative_path}"
        )
        for step in plan.steps:
            console.print(
                f"  STEP {step.migration_id} schema={step.source_version}->"
                f"{step.target_version}: {step.description}"
            )
    for issue in report.issues:
        console.print(f"FAILED {issue.code} path={issue.relative_path}: {issue.message}")
    console.print(report.summary)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
