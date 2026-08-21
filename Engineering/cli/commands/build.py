"""CLI adapter for the E-010 build system."""

from __future__ import annotations

from typing import Annotated

import typer

from Engineering.BuildSystem import (
    BuildContext,
    BuildProfile,
    BuildService,
    default_build_engine,
    profile_targets,
)
from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.paths import get_paths

app = typer.Typer(help="Build engineering artifacts")


@app.callback(invoke_without_command=True)
def build_main(ctx: typer.Context) -> None:
    """Build engineering artifacts."""
    if ctx.invoked_subcommand is None:
        console.print("Run 'python -m Engineering build run' to execute the build.")


@app.command(name="clean")
def build_clean() -> None:
    """Clean build artifacts."""
    import shutil

    output_root = (get_paths().root / "build").resolve()
    if output_root.is_dir():
        shutil.rmtree(output_root)
        console.print(f"[green]Removed build output: {output_root}[/green]")
    else:
        console.print("[green]Build output is already clean.[/green]")


@app.command(name="run")
def build_run(
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    profile: Annotated[BuildProfile, typer.Option("--profile")] = BuildProfile.FULL,
) -> None:
    """Run build process."""
    paths = get_paths()
    context = BuildContext(
        project_root=paths.root,
        output_root=paths.root / "build",
        dry_run=dry_run,
    )
    execution = BuildService(default_build_engine()).run(
        context, targets=profile_targets(profile)
    )
    for result in execution.report.results:
        console.print(f"{result.state.value.upper():9} {result.step_id}: {result.message}")
    console.print(execution.report.summary)
    if execution.manifest_path is not None:
        console.print(f"Manifest: {execution.manifest_path}")
    if not execution.report.success:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="plan")
def build_plan(
    profile: Annotated[BuildProfile, typer.Option("--profile")] = BuildProfile.FULL,
) -> None:
    """Display the deterministic default build plan."""

    plan = default_build_engine().plan(
        targets=profile_targets(profile), dry_run=True
    )
    for index, step_id in enumerate(plan.step_ids, start=1):
        console.print(f"{index}. {step_id}")
