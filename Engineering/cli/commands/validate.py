"""
Validation command.
"""

from __future__ import annotations

import typer

from Engineering.cli.errors import EXIT_CODE_VALIDATION_FAILURE
from Engineering.cli.output.console import print_validation_report
from Engineering.core.validation import Validator
from Engineering.Standards.project import (
    RequiredDirectoryRule,
    RequiredFileRule,
    StructureValidationRule,
)


def validate() -> None:
    """
    Validate project structure and configuration.
    """
    validator = Validator(rules=[
        StructureValidationRule(),
        RequiredDirectoryRule("Engineering", "Engineering Toolkit"),
        RequiredDirectoryRule("Backend", "Backend"),
        RequiredDirectoryRule("Frontend", "Frontend"),
        RequiredDirectoryRule("Docs", "Documentation"),
        RequiredDirectoryRule("Engineering/config", "Engineering configuration"),
        RequiredFileRule("pyproject.toml", "Project manifest"),
        RequiredFileRule("README.md", "Project readme"),
    ])

    report = validator.validate()
    print_validation_report(report)

    if not report.passed:
        raise typer.Exit(code=EXIT_CODE_VALIDATION_FAILURE)