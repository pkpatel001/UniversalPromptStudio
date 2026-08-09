"""
Doctor command group.
"""

from __future__ import annotations

import platform
import shutil
import sys

import typer

from Engineering.cli.errors import EXIT_CODE_SUCCESS, EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import (
    console,
    print_diagnostic_report,
    print_doctor_info,
)
from Engineering.core.diagnostics import Doctor, HealthState
from Engineering.core.version import VERSION

app = typer.Typer(help="Project diagnostics")


@app.callback(invoke_without_command=True)
def doctor_main() -> None:
    """Project diagnostics."""
    console.print("[yellow]Use 'doctor check' or 'doctor info'.[/yellow]")


@app.command(name="check")
def doctor_check() -> None:
    """Run project health diagnostics."""
    doctor = Doctor()
    report = doctor.run()
    print_diagnostic_report(report)

    if report.health in (HealthState.UNHEALTHY, HealthState.CRITICAL):
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)

    raise typer.Exit(code=EXIT_CODE_SUCCESS)


@app.command(name="info")
def doctor_info() -> None:
    """Show project and environment information."""
    project_root = None
    project_name = None
    project_version = None
    project_license = None
    config_available = False

    try:
        from Engineering.core.paths import get_paths

        paths = get_paths()
        project_root = str(paths.root)
    except Exception:
        pass

    try:
        from Engineering.core.config import get_config

        cfg = get_config()
        project_name = cfg.project.name
        project_version = cfg.project.version
        project_license = cfg.project.license
        config_available = True
    except Exception:
        pass

    print_doctor_info(
        project_root=project_root,
        project_name=project_name,
        project_version=project_version,
        project_license=project_license,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform_name=platform.system(),
        architecture=platform.machine(),
        engineering_version=VERSION,
        config_available=config_available,
        git_available=shutil.which("git") is not None,
    )