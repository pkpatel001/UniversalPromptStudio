"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Validation Framework

This module provides the canonical validation infrastructure for the
Engineering Toolkit. It defines:

* ValidationSeverity
* ValidationIssue
* ValidationReport
* ValidationRule
* ValidationContext
* Validator

The validation framework is:
* deterministic
* reusable
* strongly typed
* composable
* testable
* non-destructive by default
* independent of CLI presentation

Public API
----------
from Engineering.core.validation import Validator, ValidationContext

validator = Validator(rules=[...])
report = validator.validate()

if report.passed:
    ...

for issue in report.errors:
    print(issue.message)

===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .exceptions import EngineeringError

if TYPE_CHECKING:
    from .config import Configuration
    from .paths import ProjectPaths

__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationReport",
    "ValidationRule",
    "ValidationContext",
    "Validator",
]


# -----------------------------------------------------------------------------
# Severity
# -----------------------------------------------------------------------------


class ValidationSeverity(Enum):
    """
    Severity levels for validation issues.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# -----------------------------------------------------------------------------
# Issue
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """
    A single validation issue discovered by a rule.
    """

    severity: ValidationSeverity
    rule_id: str
    message: str
    location: str | None = None
    context: dict[str, str] | None = None


# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """
    Aggregated validation results from a validator run.
    """

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """
        Return True if no ERROR or CRITICAL issues were found.
        """

        return not any(
            issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
            for issue in self.issues
        )

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        """
        Return all ERROR and CRITICAL issues.
        """

        return tuple(
            issue for issue in self.issues
            if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL)
        )

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        """
        Return all WARNING issues.
        """

        return tuple(
            issue for issue in self.issues
            if issue.severity == ValidationSeverity.WARNING
        )

    @property
    def summary(self) -> str:
        """
        Return a human-readable summary of the validation report.
        """

        if not self.issues:
            return "Validation passed: no issues found."

        return (
            f"Validation {'passed' if self.passed else 'failed'}: "
            f"{len(self.issues)} issue(s) "
            f"({len(self.errors)} error(s), {len(self.warnings)} warning(s))."
        )


# -----------------------------------------------------------------------------
# Context
# -----------------------------------------------------------------------------


class ValidationContext:
    """
    Context object provided to validation rules.

    Provides access to project paths, configuration, and filesystem utilities
    without duplicating the responsibilities of existing infrastructure modules.
    """

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        config: Configuration | None = None,
    ) -> None:
        from .config import get_config
        from .filesystem import exists, is_directory, is_file, read_text
        from .paths import get_paths

        self.paths = paths if paths is not None else get_paths()
        self.config = config if config is not None else get_config()
        self._read_text = read_text
        self._exists = exists
        self._is_directory = is_directory
        self._is_file = is_file

    def read_text(self, relative_path: str) -> str | None:
        """
        Read a text file relative to the project root.

        Parameters
        ----------
        relative_path
            Path relative to the project root.

        Returns
        -------
        str | None
            File contents, or None if the file cannot be read.
        """

        full_path = self.paths.root / relative_path
        if not self._is_file(full_path):
            return None
        try:
            return self._read_text(full_path)
        except EngineeringError:
            return None

    def file_exists(self, relative_path: str) -> bool:
        """
        Check whether a file exists relative to the project root.

        Parameters
        ----------
        relative_path
            Path relative to the project root.

        Returns
        -------
        bool
        """

        return self._is_file(self.paths.root / relative_path)

    def directory_exists(self, relative_path: str) -> bool:
        """
        Check whether a directory exists relative to the project root.

        Parameters
        ----------
        relative_path
            Path relative to the project root.

        Returns
        -------
        bool
        """

        return self._is_directory(self.paths.root / relative_path)


# -----------------------------------------------------------------------------
# Rule
# -----------------------------------------------------------------------------


class ValidationRule(ABC):
    """
    Abstract base class for validation rules.

    Each rule examines the project context and produces zero or more
    ValidationIssue instances.
    """

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """
        Unique identifier for this rule.
        """

    @property
    @abstractmethod
    def severity(self) -> ValidationSeverity:
        """
        Default severity for issues produced by this rule.
        """

    @abstractmethod
    def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
        """
        Evaluate the rule against the given context.

        Parameters
        ----------
        context
            Project context for validation.

        Returns
        -------
        tuple[ValidationIssue, ...]
            Issues found by this rule. Empty tuple means the rule passed.
        """


# -----------------------------------------------------------------------------
# Validator
# -----------------------------------------------------------------------------


class Validator:
    """
    Runs a collection of validation rules and produces a report.

    The validator is independent of any CLI or presentation layer.
    """

    def __init__(self, rules: Sequence[ValidationRule] | None = None) -> None:
        self.rules: list[ValidationRule] = list(rules) if rules else []

    def add_rule(self, rule: ValidationRule) -> None:
        """
        Add a validation rule to the validator.

        Parameters
        ----------
        rule
            Rule to add.
        """

        self.rules.append(rule)

    def validate(self) -> ValidationReport:
        """
        Run all rules and return a validation report.

        Returns
        -------
        ValidationReport
            Aggregated validation results.
        """

        context = ValidationContext()
        issues: list[ValidationIssue] = []

        for rule in self.rules:
            issues.extend(rule.check(context))

        return ValidationReport(issues=tuple(issues))
