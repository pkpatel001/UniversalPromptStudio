"""
CLI output helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from Engineering.core.constants import ENGINEERING_NAME, PROJECT_NAME
from Engineering.core.version import VERSION

if TYPE_CHECKING:
    from Engineering.core.diagnostics import DiagnosticIssue, DiagnosticReport
    from Engineering.core.validation import ValidationIssue, ValidationReport

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


def _render_diagnostic_issue(issue: DiagnosticIssue) -> None:
    """Render a single diagnostic issue."""
    from Engineering.core.diagnostics import DiagnosticSeverity

    if issue.severity == DiagnosticSeverity.ERROR:
        print_error(f"{issue.diagnostic_id}")
    elif issue.severity == DiagnosticSeverity.WARNING:
        print_warning(f"{issue.diagnostic_id}")
    elif issue.severity == DiagnosticSeverity.CRITICAL:
        print_error(f"[CRITICAL] {issue.diagnostic_id}")
    else:
        print_info(f"{issue.diagnostic_id}")

    console.print(f"  {issue.message}")

    if issue.recommendation:
        console.print(f"  [dim]Recommendation: {issue.recommendation}[/dim]")

    console.print()


def print_diagnostic_report(report: DiagnosticReport) -> None:
    """
    Render a DiagnosticReport to the console.
    """
    from Engineering.core.diagnostics import (
        DiagnosticCategory,
        HealthState,
    )
    from Engineering.core.validation import ValidationSeverity

    print_banner()
    console.print("[bold]Project Doctor[/bold]")
    console.print()

    health_color = {
        HealthState.HEALTHY: "bold green",
        HealthState.DEGRADED: "bold yellow",
        HealthState.UNHEALTHY: "bold red",
        HealthState.CRITICAL: "bold red",
    }

    color = health_color.get(report.health, "bold")
    console.print(f"Project Health: [{color}]{report.health.value.upper()}[/{color}]")
    console.print()

    category_order = [
        DiagnosticCategory.PROJECT,
        DiagnosticCategory.CONFIGURATION,
        DiagnosticCategory.VALIDATION,
        DiagnosticCategory.ENVIRONMENT,
        DiagnosticCategory.ENGINEERING,
    ]

    category_labels = {
        DiagnosticCategory.PROJECT: "Project",
        DiagnosticCategory.CONFIGURATION: "Configuration",
        DiagnosticCategory.VALIDATION: "Validation",
        DiagnosticCategory.ENVIRONMENT: "Environment",
        DiagnosticCategory.ENGINEERING: "Engineering Toolkit",
    }

    issues_by_category: dict[DiagnosticCategory, list[DiagnosticIssue]] = {}
    for issue in report.issues:
        issues_by_category.setdefault(issue.category, []).append(issue)

    validation_issues: list[ValidationIssue] = list(report.validation.issues)

    for category in category_order:
        cat_issues = issues_by_category.get(category, [])

        if not cat_issues and category != DiagnosticCategory.VALIDATION:
            continue

        console.print(f"[bold]{category_labels[category]}[/bold]")

        for issue in cat_issues:
            _render_diagnostic_issue(issue)

        if category == DiagnosticCategory.VALIDATION:
            for val_issue in validation_issues:
                if val_issue.severity == ValidationSeverity.ERROR:
                    print_error(f"{val_issue.rule_id}")
                elif val_issue.severity == ValidationSeverity.WARNING:
                    print_warning(f"{val_issue.rule_id}")
                elif val_issue.severity == ValidationSeverity.CRITICAL:
                    print_error(f"[CRITICAL] {val_issue.rule_id}")
                else:
                    print_info(f"{val_issue.rule_id}")

                console.print(f"  {val_issue.message}")
                console.print()

    console.print("[bold]Summary[/bold]")
    diagnostic_error_count = len(report.errors)
    diagnostic_warning_count = len(report.warnings)
    validation_error_count = len(report.validation.errors)
    validation_warning_count = len(report.validation.warnings)

    total_errors = diagnostic_error_count + validation_error_count
    total_warnings = diagnostic_warning_count + validation_warning_count

    console.print(f"  {total_errors} error(s), {total_warnings} warning(s)")
    console.print()


def print_doctor_info(
    project_root: str | None,
    project_name: str | None,
    project_version: str | None,
    project_license: str | None,
    python_version: str,
    platform_name: str,
    architecture: str,
    engineering_version: str,
    config_available: bool,
    git_available: bool,
) -> None:
    """
    Render project and environment information to the console.
    """
    print_banner()
    console.print("[bold]Project Doctor - Information[/bold]")
    console.print()

    console.print("[bold]Project[/bold]")
    console.print(f"  Root: {project_root or 'Not discovered'}")
    console.print(f"  Name: {project_name or 'Unknown'}")
    console.print(f"  Version: {project_version or 'Unknown'}")
    console.print(f"  License: {project_license or 'Unknown'}")
    console.print()

    console.print("[bold]Environment[/bold]")
    console.print(f"  Python: {python_version}")
    console.print(f"  Platform: {platform_name}")
    console.print(f"  Architecture: {architecture}")
    console.print(f"  Git: {'Available' if git_available else 'Not found'}")
    console.print()

    console.print("[bold]Engineering Toolkit[/bold]")
    console.print(f"  Version: {engineering_version}")
    console.print(f"  Configuration: {'Loaded' if config_available else 'Unavailable'}")
    console.print()