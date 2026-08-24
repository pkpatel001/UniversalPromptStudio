"""Read-only CLI adapter for E-016.1 workflow definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    WorkflowDiscoveryRoot,
    WorkflowManifestReader,
    WorkflowService,
    WorkflowValidationReport,
)

app = typer.Typer(help="Inspect passive workflow definitions without executing operations")


@app.callback(invoke_without_command=True)
def workflow_main(ctx: typer.Context) -> None:
    """Inspect workflow SDK definitions."""

    if ctx.invoked_subcommand is None:
        console.print(
            "Run 'python -m Engineering workflow inspect MANIFEST' "
            "to validate a passive workflow definition."
        )


@app.command(name="inspect")
def workflow_inspect(manifest: Path) -> None:
    """Validate and display one exact workflow manifest."""

    try:
        parsed = WorkflowManifestReader().read(manifest)
    except WorkflowError as exc:
        console.print(f"FAILED workflow.inspect: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    metadata = parsed.metadata
    console.print(f"Workflow: {metadata.workflow_id.value}")
    console.print(f"Name: {metadata.name}")
    console.print(f"Version: {metadata.version.value}")
    console.print(f"SDK API level: {metadata.sdk_version.api_level}")
    console.print(f"Inputs: {len(parsed.inputs)}")
    console.print(f"Outputs: {len(parsed.outputs)}")
    console.print(f"Nodes: {len(parsed.nodes)}")
    console.print(f"Edges: {len(parsed.edges)}")
    console.print(f"Description: {metadata.description}")
    console.print("Operation modules imported: no")
    console.print("Operations executed: no")
    console.print("Network requests: none")
    console.print("Credential access: none")
    console.print("Filesystem changes: none")


def _roots(values: list[Path] | None) -> tuple[WorkflowDiscoveryRoot, ...]:
    if not values:
        raise WorkflowError("Workflow catalog commands require at least one explicit --root.")
    return tuple(
        WorkflowDiscoveryRoot(f"explicit-{index:04d}", path)
        for index, path in enumerate(values, start=1)
    )


def _validate(roots: tuple[WorkflowDiscoveryRoot, ...]) -> WorkflowValidationReport:
    try:
        return WorkflowService().validate_roots(roots)
    except WorkflowError as exc:
        console.print(f"FAILED workflow.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc


def _print_report(report: WorkflowValidationReport) -> None:
    for record in report.records:
        metadata = record.manifest.metadata
        operations = ",".join(record.operations)
        console.print(
            f"VALID {record.workflow_id} version={record.version} "
            f"sdk={metadata.sdk_version.api_level} "
            f"nodes={len(record.manifest.nodes)} operations={operations} "
            f"root={record.root_id} path={record.relative_path}"
        )
    for issue in report.issues:
        console.print(
            f"FAILED {issue.code} root={issue.root_id} path={issue.relative_path}: {issue.message}",
            soft_wrap=True,
        )
    console.print(report.summary)
    console.print("Operation modules imported: no")
    console.print("Operations executed: no")
    console.print("Network requests: none")
    console.print("Credential access: none")
    console.print("Filesystem changes: none")


@app.command(name="list")
def workflow_list(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """List SDK-compatible workflows below explicit roots."""

    try:
        roots = _roots(root)
    except WorkflowError as exc:
        console.print(f"FAILED workflow.list: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="validate")
def workflow_validate(
    root: Annotated[list[Path] | None, typer.Option("--root")] = None,
) -> None:
    """Validate discovery, graph invariants, identities, and SDK compatibility."""

    try:
        roots = _roots(root)
    except WorkflowError as exc:
        console.print(f"FAILED workflow.validate: {exc}", soft_wrap=True)
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    report = _validate(roots)
    _print_report(report)
    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
