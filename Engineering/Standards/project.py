"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Project Standards

This module contains validation rules for the canonical UPS repository
structure and required artifacts.

===============================================================================
"""

from __future__ import annotations

from Engineering.core.paths import verify_structure
from Engineering.core.validation import (
    ValidationContext,
    ValidationIssue,
    ValidationRule,
    ValidationSeverity,
)

__all__ = [
    "RequiredDirectoryRule",
    "RequiredFileRule",
    "StructureValidationRule",
]


class RequiredDirectoryRule(ValidationRule):
    """
    Validate that a required directory exists relative to the project root.
    """

    def __init__(self, relative_path: str, description: str) -> None:
        self._relative_path = relative_path
        self._description = description

    @property
    def rule_id(self) -> str:
        return f"required-directory:{self._relative_path}"

    @property
    def severity(self) -> ValidationSeverity:
        return ValidationSeverity.ERROR

    def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.directory_exists(self._relative_path):
            return ()
        return (
            ValidationIssue(
                severity=self.severity,
                rule_id=self.rule_id,
                message=f"Required directory missing: {self._description}",
                location=self._relative_path,
            ),
        )


class RequiredFileRule(ValidationRule):
    """
    Validate that a required file exists relative to the project root.
    """

    def __init__(self, relative_path: str, description: str) -> None:
        self._relative_path = relative_path
        self._description = description

    @property
    def rule_id(self) -> str:
        return f"required-file:{self._relative_path}"

    @property
    def severity(self) -> ValidationSeverity:
        return ValidationSeverity.ERROR

    def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        if context.file_exists(self._relative_path):
            return ()
        return (
            ValidationIssue(
                severity=self.severity,
                rule_id=self.rule_id,
                message=f"Required file missing: {self._description}",
                location=self._relative_path,
            ),
        )


class StructureValidationRule(ValidationRule):
    """
    Validate the canonical UPS repository structure.

    This rule delegates to ``paths.verify_structure()`` and converts
    the resulting error messages into structured ValidationIssue instances.
    """

    @property
    def rule_id(self) -> str:
        return "project-structure"

    @property
    def severity(self) -> ValidationSeverity:
        return ValidationSeverity.ERROR

    def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        issues: list[ValidationIssue] = []
        errors = verify_structure()

        for error in errors:
            if ":" in error:
                _, name = error.split(":", 1)
                location = name.strip()
            else:
                location = None

            issues.append(
                ValidationIssue(
                    severity=self.severity,
                    rule_id=self.rule_id,
                    message=error,
                    location=location,
                )
            )

        return tuple(issues)
