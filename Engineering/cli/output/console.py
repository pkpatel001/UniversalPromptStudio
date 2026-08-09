"""
CLI output helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from Engineering.core.constants import ENGINEERING_NAME, PROJECT_NAME
from Engineering.core.version import VERSION

if TYPE_CHECKING:
    from Engineering.core.validation import ValidationReport

console = Console()


def print_banner() -> None:
    """Display the application banner."""
    console.print()
    console.rule(f"[bold cyan]{PROJECT_NAME}[/bold cyan]")
    console.print(
        f"[bold green]{ENGINEERING_NAME}[/bold green] "
        f"[white]v{VERSION}[/white]"
    )
    console.print()


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]OK[/bold green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]ERROR[/bold red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]![/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]INFO[/bold blue] {message}")


def print_validation_report(report: ValidationReport) -> None:
    """
    Render a ValidationReport to the console.
    """
    from Engineering.core.validation import ValidationSeverity

    print_banner()
    console.print("[bold]Engineering Validation[/bold]")
    console.print()

    for issue in report.issues:
        if issue.severity == ValidationSeverity.ERROR:
            print_error(f"{issue.message}")
        elif issue.severity == ValidationSeverity.WARNING:
            print_warning(f"{issue.message}")
        elif issue.severity == ValidationSeverity.CRITICAL:
            print_error(f"[CRITICAL] {issue.message}")
        else:
            print_info(f"{issue.message}")

    console.print()

    error_count = len(report.errors)
    warning_count = len(report.warnings)

    if report.passed:
        console.print("[bold green]Validation passed.[/bold green]")
    else:
        console.print("[bold red]Validation failed.[/bold red]")

    console.print(f"{error_count} error(s), {warning_count} warning(s)")