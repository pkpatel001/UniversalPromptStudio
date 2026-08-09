"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Diagnostic Framework

This module provides the canonical diagnostic infrastructure for the
Engineering Toolkit. It defines:

* DiagnosticCategory
* DiagnosticSeverity
* DiagnosticIssue
* HealthState
* DiagnosticReport
* DiagnosticCheck
* DiagnosticContext
* Doctor

The diagnostic framework is:
* deterministic
* read-only by default
* diagnostic rather than destructive
* reusable outside the CLI
* strongly typed
* composable
* testable
* independent of presentation
* compatible with E-004 validation

Public API
----------
from Engineering.core.diagnostics import Doctor

doctor = Doctor()
report = doctor.run()

report.health
report.issues
report.validation
report.summary

===============================================================================
"""

from __future__ import annotations

import shutil
import sys
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .config import get_config
from .exceptions import (
    ConfigurationError,
    ProjectRootNotFoundError,
)
from .paths import get_paths
from .validation import (
    ValidationReport,
    ValidationRule,
    ValidationSeverity,
    Validator,
)

if TYPE_CHECKING:
    from .config import Configuration
    from .paths import ProjectPaths

__all__ = [
    "DiagnosticCategory",
    "DiagnosticSeverity",
    "DiagnosticIssue",
    "HealthState",
    "DiagnosticReport",
    "DiagnosticCheck",
    "DiagnosticContext",
    "Doctor",
    "EnvironmentPythonVersionCheck",
    "EnvironmentEngineeringPackageCheck",
    "EnvironmentGitAvailableCheck",
    "ProjectRootCheck",
    "ConfigurationLoadCheck",
    "EngineeringValidationCheck",
]


# -----------------------------------------------------------------------------
# Severity (reuses ValidationSeverity for consistency)
# -----------------------------------------------------------------------------

DiagnosticSeverity = ValidationSeverity


# -----------------------------------------------------------------------------
# Categories
# -----------------------------------------------------------------------------


class DiagnosticCategory(Enum):
    """
    Categories for organizing diagnostic checks.
    """

    PROJECT = "project"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    ENVIRONMENT = "environment"
    ENGINEERING = "engineering"


# -----------------------------------------------------------------------------
# Health State
# -----------------------------------------------------------------------------


class HealthState(Enum):
    """
    Deterministic project health states.

    Computed from the highest-severity diagnostic issue:
    * No errors or critical issues  -> HEALTHY
    * Warnings only                  -> DEGRADED
    * Errors                         -> UNHEALTHY
    * Critical errors                -> CRITICAL
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


# -----------------------------------------------------------------------------
# Issue
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiagnosticIssue:
    """
    A single diagnostic finding.

    Attributes
    ----------
    severity
        Severity of this diagnostic issue.
    diagnostic_id
        Stable identifier for this diagnostic (e.g. "environment.python.version").
    category
        Diagnostic category this issue belongs to.
    message
        Human-readable description of the finding.
    location
        Optional file path or directory related to this finding.
    recommendation
        Optional actionable guidance for addressing this issue.
    """

    severity: DiagnosticSeverity
    diagnostic_id: str
    message: str
    category: DiagnosticCategory
    location: str | None = None
    recommendation: str | None = None


# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    """
    Aggregated diagnostic results from a Doctor run.

    Contains both the original E-004 ValidationReport and any
    additional diagnostic findings.
    """

    issues: tuple[DiagnosticIssue, ...] = ()
    validation: ValidationReport = field(default_factory=ValidationReport)

    @property
    def passed(self) -> bool:
        """
        Return True if no ERROR or CRITICAL diagnostic issues exist
        and the validation report passed.
        """
        if not self.validation.passed:
            return False
        return not any(
            issue.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL)
            for issue in self.issues
        )

    @property
    def errors(self) -> tuple[DiagnosticIssue, ...]:
        """
        Return all ERROR and CRITICAL diagnostic issues.
        """
        return tuple(
            issue
            for issue in self.issues
            if issue.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.CRITICAL)
        )

    @property
    def warnings(self) -> tuple[DiagnosticIssue, ...]:
        """
        Return all WARNING diagnostic issues.
        """
        return tuple(
            issue for issue in self.issues
            if issue.severity == DiagnosticSeverity.WARNING
        )

    @property
    def info_issues(self) -> tuple[DiagnosticIssue, ...]:
        """
        Return all informational diagnostic issues.
        """
        return tuple(
            issue for issue in self.issues
            if issue.severity == DiagnosticSeverity.INFO
        )

    @property
    def health(self) -> HealthState:
        """
        Compute deterministic health state from diagnostic issues and
        validation results.

        Returns
        -------
        HealthState
        """
        if not self.validation.passed:
            has_critical = any(
                issue.severity == DiagnosticSeverity.CRITICAL
                for issue in self.validation.issues
            )
            if has_critical:
                return HealthState.CRITICAL
            return HealthState.UNHEALTHY

        has_critical = any(
            issue.severity == DiagnosticSeverity.CRITICAL for issue in self.issues
        )
        if has_critical:
            return HealthState.CRITICAL

        has_errors = any(
            issue.severity == DiagnosticSeverity.ERROR for issue in self.issues
        )
        if has_errors:
            return HealthState.UNHEALTHY

        has_warnings = any(
            issue.severity == DiagnosticSeverity.WARNING for issue in self.issues
        )
        if has_warnings:
            return HealthState.DEGRADED

        return HealthState.HEALTHY

    @property
    def summary(self) -> str:
        """
        Return a human-readable summary of the diagnostic report.
        """
        diagnostic_error_count = len(self.errors)
        diagnostic_warning_count = len(self.warnings)
        validation_error_count = len(self.validation.errors)
        validation_warning_count = len(self.validation.warnings)

        total_errors = diagnostic_error_count + validation_error_count
        total_warnings = diagnostic_warning_count + validation_warning_count

        return (
            f"Health: {self.health.value}: "
            f"{total_errors} error(s), {total_warnings} warning(s)."
        )


# -----------------------------------------------------------------------------
# Diagnostic Check
# -----------------------------------------------------------------------------


class DiagnosticCheck(ABC):
    """
    Abstract base class for diagnostic checks.

    Each check examines a specific aspect of the project or environment
    and produces zero or more DiagnosticIssue instances.
    """

    @property
    @abstractmethod
    def diagnostic_id(self) -> str:
        """
        Unique stable identifier for this check.
        """

    @property
    @abstractmethod
    def category(self) -> DiagnosticCategory:
        """
        Category this check belongs to.
        """

    @abstractmethod
    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        """
        Run this diagnostic check.

        Parameters
        ----------
        context
            Diagnostic context providing access to project paths,
            configuration, and validation infrastructure.

        Returns
        -------
        tuple[DiagnosticIssue, ...]
            Issues found. Empty tuple means the check passed.
        """


# -----------------------------------------------------------------------------
# Diagnostic Context
# -----------------------------------------------------------------------------


class DiagnosticContext:
    """
    Context object provided to diagnostic checks.

    Provides access to project paths, configuration, and validation
    infrastructure without duplicating responsibilities of existing modules.
    """

    def __init__(
        self,
        paths: ProjectPaths | None = None,
        config: Configuration | None = None,
    ) -> None:
        self.paths: ProjectPaths | None = None
        self.config: Configuration | None = None

        try:
            self.paths = paths if paths is not None else get_paths()
        except ProjectRootNotFoundError:
            self.paths = None

        try:
            self.config = config if config is not None else get_config()
        except ConfigurationError:
            self.config = None


# -----------------------------------------------------------------------------
# Foundational Diagnostic Checks
# -----------------------------------------------------------------------------


class EnvironmentPythonVersionCheck(DiagnosticCheck):
    """
    Verify the running Python version satisfies the configured minimum.
    """

    @property
    def diagnostic_id(self) -> str:
        return "environment.python.version"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.ENVIRONMENT

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        current = sys.version_info[:2]
        minimum = (3, 12)

        if context.config is not None:
            try:
                parts = context.config.project.python.minimum_version.split(".")
                minimum = (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                pass

        if current >= minimum:
            return (
                DiagnosticIssue(
                    severity=DiagnosticSeverity.INFO,
                    diagnostic_id=self.diagnostic_id,
                    message=(
                        f"Python {current[0]}.{current[1]} "
                        f"satisfies the minimum requirement of "
                        f"{minimum[0]}.{minimum[1]}."
                    ),
                    category=self.category,
                ),
            )

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.ERROR,
                diagnostic_id=self.diagnostic_id,
                message=(
                    f"Running Python {current[0]}.{current[1]} does not satisfy "
                    f"the configured minimum Python version of "
                    f"{minimum[0]}.{minimum[1]}."
                ),
                category=self.category,
                recommendation="Upgrade to the required minimum Python version.",
            ),
        )


class EnvironmentEngineeringPackageCheck(DiagnosticCheck):
    """
    Verify the Engineering package is importable.
    """

    @property
    def diagnostic_id(self) -> str:
        return "engineering.package.importable"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.ENGINEERING

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        from Engineering.core.version import VERSION

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.INFO,
                diagnostic_id=self.diagnostic_id,
                message=f"Engineering Toolkit {VERSION} is importable.",
                category=self.category,
            ),
        )


class EnvironmentGitAvailableCheck(DiagnosticCheck):
    """
    Verify Git is available on the system PATH.
    """

    @property
    def diagnostic_id(self) -> str:
        return "environment.git.available"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.ENVIRONMENT

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        git_path = shutil.which("git")

        if git_path is not None:
            return (
                DiagnosticIssue(
                    severity=DiagnosticSeverity.INFO,
                    diagnostic_id=self.diagnostic_id,
                    message="Git is available on the system PATH.",
                    category=self.category,
                ),
            )

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.WARNING,
                diagnostic_id=self.diagnostic_id,
                message="Git was not found on the system PATH.",
                category=self.category,
                recommendation="Install Git or ensure it is available on the system PATH.",
            ),
        )


class ProjectRootCheck(DiagnosticCheck):
    """
    Verify the project root can be discovered.
    """

    @property
    def diagnostic_id(self) -> str:
        return "project.root.discovered"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.PROJECT

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        if context.paths is not None:
            return (
                DiagnosticIssue(
                    severity=DiagnosticSeverity.INFO,
                    diagnostic_id=self.diagnostic_id,
                    message=f"Project root discovered: {context.paths.root}",
                    category=self.category,
                    location=str(context.paths.root),
                ),
            )

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.ERROR,
                diagnostic_id=self.diagnostic_id,
                message="Project root could not be discovered.",
                category=self.category,
                recommendation=(
                    "Ensure the Engineering package is located within "
                    "the Universal Prompt Studio repository."
                ),
            ),
        )


class ConfigurationLoadCheck(DiagnosticCheck):
    """
    Verify the Engineering configuration can be loaded.
    """

    @property
    def diagnostic_id(self) -> str:
        return "configuration.load"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.CONFIGURATION

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        if context.config is not None:
            return (
                DiagnosticIssue(
                    severity=DiagnosticSeverity.INFO,
                    diagnostic_id=self.diagnostic_id,
                    message="Engineering configuration loaded successfully.",
                    category=self.category,
                ),
            )

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.ERROR,
                diagnostic_id=self.diagnostic_id,
                message="Engineering configuration could not be loaded.",
                category=self.category,
                recommendation=(
                    "Verify that all required configuration files exist "
                    "in Engineering/config/."
                ),
            ),
        )


class EngineeringValidationCheck(DiagnosticCheck):
    """
    Report on the status of the validation infrastructure.
    """

    @property
    def diagnostic_id(self) -> str:
        return "engineering.validation.operational"

    @property
    def category(self) -> DiagnosticCategory:
        return DiagnosticCategory.ENGINEERING

    def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
        from .validation import Validator

        validator = Validator()
        report = validator.validate()

        if isinstance(report, ValidationReport):
            return (
                DiagnosticIssue(
                    severity=DiagnosticSeverity.INFO,
                    diagnostic_id=self.diagnostic_id,
                    message="Validation infrastructure is operational.",
                    category=self.category,
                ),
            )

        return (
            DiagnosticIssue(
                severity=DiagnosticSeverity.ERROR,
                diagnostic_id=self.diagnostic_id,
                message="Validation infrastructure is not operational.",
                category=self.category,
            ),
        )


# -----------------------------------------------------------------------------
# Default Diagnostic Checks
# -----------------------------------------------------------------------------

DEFAULT_DIAGNOSTIC_CHECKS: list[DiagnosticCheck] = [
    ProjectRootCheck(),
    ConfigurationLoadCheck(),
    EnvironmentPythonVersionCheck(),
    EnvironmentEngineeringPackageCheck(),
    EnvironmentGitAvailableCheck(),
    EngineeringValidationCheck(),
]


# -----------------------------------------------------------------------------
# Doctor
# -----------------------------------------------------------------------------


class Doctor:
    """
    Orchestrates diagnostic checks and validation to produce
    a comprehensive DiagnosticReport.

    The Doctor is:
    * read-only (does not modify the project)
    * deterministic (same input produces equivalent results)
    * independent of CLI or presentation layers

    The Doctor consumes the E-004 Validator for compliance checking
    and adds environment/project/configuration diagnostics.
    """

    def __init__(
        self,
        validation_rules: Sequence[ValidationRule] | None = None,
        diagnostic_checks: Sequence[DiagnosticCheck] | None = None,
    ) -> None:
        from Engineering.Standards.project import (
            RequiredDirectoryRule,
            RequiredFileRule,
            StructureValidationRule,
        )

        if validation_rules is not None:
            self._validator = Validator(rules=list(validation_rules))
        else:
            self._validator = Validator(
                rules=[
                    StructureValidationRule(),
                    RequiredDirectoryRule("Engineering", "Engineering Toolkit"),
                    RequiredDirectoryRule("Backend", "Backend"),
                    RequiredDirectoryRule("Frontend", "Frontend"),
                    RequiredDirectoryRule("Docs", "Documentation"),
                    RequiredDirectoryRule("Engineering/config", "Engineering configuration"),
                    RequiredFileRule("pyproject.toml", "Project manifest"),
                    RequiredFileRule("README.md", "Project readme"),
                ]
            )

        self._checks: list[DiagnosticCheck] = (
            list(diagnostic_checks)
            if diagnostic_checks is not None
            else list(DEFAULT_DIAGNOSTIC_CHECKS)
        )

    def run(self) -> DiagnosticReport:
        """
        Run all validation rules and diagnostic checks.

        Returns
        -------
        DiagnosticReport
            Aggregated diagnostic and validation results.
        """
        context = DiagnosticContext()
        validation_report = self._validator.validate()

        issues: list[DiagnosticIssue] = []

        for check in self._checks:
            issues.extend(check.check(context))

        issues.sort(key=lambda i: (i.category.value, i.diagnostic_id))

        return DiagnosticReport(
            issues=tuple(issues),
            validation=validation_report,
        )