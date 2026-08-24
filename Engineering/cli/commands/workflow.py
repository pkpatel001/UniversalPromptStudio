"""Read-only CLI adapter for E-016.1 workflow definitions."""

from __future__ import annotations

from pathlib import Path

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import WorkflowManifestReader

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
