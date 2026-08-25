"""CLI adapter for safe E-011 local packaging."""

from __future__ import annotations

import shutil
from typing import Annotated

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import console
from Engineering.core.exceptions import ReleaseError
from Engineering.core.paths import get_paths
from Engineering.core.version import VERSION
from Engineering.ReleaseSystem import (
    PackageFormat,
    ReleaseArtifactVerifier,
    ReleaseContext,
    ReleaseService,
    ReleaseVersion,
)

app = typer.Typer(help="Plan and create local release packages")
_LOCAL_FORMATS = (
    PackageFormat.SDIST,
    PackageFormat.WHEEL,
    PackageFormat.FRONTEND_ZIP,
    PackageFormat.DESKTOP_NSIS,
    PackageFormat.DESKTOP_SIDECAR,
)


@app.callback(invoke_without_command=True)
def release_main(ctx: typer.Context) -> None:
    """Plan and create local release packages."""

    if ctx.invoked_subcommand is None:
        console.print("Run 'python -m Engineering release plan' to inspect readiness.")


def _context(*, dry_run: bool = False, overwrite: bool = False) -> ReleaseContext:
    paths = get_paths()
    return ReleaseContext(
        project_root=paths.root,
        output_root=paths.root / "release",
        version=ReleaseVersion(VERSION),
        dry_run=dry_run,
        overwrite=overwrite,
    )


@app.command(name="plan")
def release_plan() -> None:
    """Display the deterministic local packaging plan and preconditions."""

    execution = ReleaseService().plan(_context(dry_run=True), _LOCAL_FORMATS)
    for index, spec in enumerate(execution.plan.specs, start=1):
        console.print(f"{index}. {_package_id(spec.package_format)}")
    if execution.preconditions.passed:
        console.print("Release preconditions passed.")
        return
    for issue in execution.preconditions.issues:
        console.print(f"FAILED {issue.code}: {issue.message}")
    raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="run")
def release_run(
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
) -> None:
    """Create inspected Python, frontend, desktop, and sidecar packages locally."""

    execution = ReleaseService().run(_context(dry_run=dry_run, overwrite=overwrite), _LOCAL_FORMATS)
    for issue in execution.preconditions.issues:
        console.print(f"FAILED {issue.code}: {issue.message}")
    if execution.report is None:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)
    for result in execution.report.results:
        console.print(
            f"{result.state.value.upper():9} {_package_id(result.package_format)}: {result.message}"
        )
    console.print(execution.report.summary)
    if execution.manifest_path is not None:
        console.print(f"Manifest: {execution.manifest_path}")
    if execution.checksum_path is not None:
        console.print(f"Checksums: {execution.checksum_path}")
    if not execution.report.success:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)


@app.command(name="clean")
def release_clean() -> None:
    """Remove only the canonical ignored release output directory."""

    output_root = (get_paths().root / "release").resolve()
    if output_root.is_dir():
        shutil.rmtree(output_root)
        console.print(f"[green]Removed release output: {output_root}[/green]")
    else:
        console.print("[green]Release output is already clean.[/green]")


@app.command(name="verify")
def release_verify() -> None:
    """Verify an existing release manifest, package set, and checksums."""

    try:
        report = ReleaseArtifactVerifier().verify(get_paths().root / "release")
    except ReleaseError as exc:
        console.print(f"FAILED release.verify: {exc}")
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE) from exc
    console.print(report.summary)


def _package_id(package_format: PackageFormat) -> str:
    if package_format == PackageFormat.FRONTEND_ZIP:
        return "package.frontend.zip"
    if package_format == PackageFormat.DESKTOP_NSIS:
        return "package.desktop.nsis"
    if package_format == PackageFormat.DESKTOP_SIDECAR:
        return "package.desktop.sidecar"
    return f"package.python.{package_format.value}"
