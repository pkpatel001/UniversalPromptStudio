"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Diagnostics Framework Tests

Tests cover:
- DiagnosticIssue creation and immutability
- DiagnosticReport aggregation, health, summary
- HealthState determinism
- DiagnosticContext access to paths/config
- Individual diagnostic checks (healthy/error/info)
- Doctor orchestration
- Validation integration
- Read-only behavior

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

import pytest

from Engineering.core.diagnostics import (
    ConfigurationLoadCheck,
    DiagnosticCategory,
    DiagnosticCheck,
    DiagnosticContext,
    DiagnosticIssue,
    DiagnosticReport,
    DiagnosticSeverity,
    Doctor,
    EngineeringValidationCheck,
    EnvironmentEngineeringPackageCheck,
    EnvironmentGitAvailableCheck,
    EnvironmentPythonVersionCheck,
    HealthState,
    ProjectRootCheck,
)
from Engineering.core.validation import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)


class TestDiagnosticIssue:
    """Tests for DiagnosticIssue."""

    def test_issue_creation(self) -> None:
        issue = DiagnosticIssue(
            severity=DiagnosticSeverity.ERROR,
            diagnostic_id="project.structure",
            message="Required directory is missing",
            category=DiagnosticCategory.PROJECT,
            location="Database/",
            recommendation="Restore the required directory.",
        )
        assert issue.severity == DiagnosticSeverity.ERROR
        assert issue.diagnostic_id == "project.structure"
        assert issue.message == "Required directory is missing"
        assert issue.category == DiagnosticCategory.PROJECT
        assert issue.location == "Database/"
        assert issue.recommendation == "Restore the required directory."

    def test_issue_without_optional_fields(self) -> None:
        issue = DiagnosticIssue(
            severity=DiagnosticSeverity.INFO,
            diagnostic_id="info-check",
            message="Info message",
            category=DiagnosticCategory.ENVIRONMENT,
        )
        assert issue.location is None
        assert issue.recommendation is None

    def test_issue_is_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        issue = DiagnosticIssue(
            severity=DiagnosticSeverity.INFO,
            diagnostic_id="info-check",
            message="Info message",
            category=DiagnosticCategory.ENVIRONMENT,
        )
        with pytest.raises(FrozenInstanceError):
            issue.message = "Changed"


class TestDiagnosticReport:
    """Tests for DiagnosticReport."""

    def test_empty_report_passes_and_healthy(self) -> None:
        report = DiagnosticReport()
        assert report.passed is True
        assert report.health == HealthState.HEALTHY
        assert len(report.issues) == 0

    def test_report_with_warning_is_degraded(self) -> None:
        issues = (
            DiagnosticIssue(
                severity=DiagnosticSeverity.WARNING,
                diagnostic_id="environment.git.available",
                message="Git not found",
                category=DiagnosticCategory.ENVIRONMENT,
            ),
        )
        report = DiagnosticReport(issues=issues)
        assert report.passed is True
        assert report.health == HealthState.DEGRADED
        assert len(report.warnings) == 1

    def test_report_with_error_is_unhealthy(self) -> None:
        issues = (
            DiagnosticIssue(
                severity=DiagnosticSeverity.ERROR,
                diagnostic_id="project.root.discovered",
                message="Root not found",
                category=DiagnosticCategory.PROJECT,
            ),
        )
        report = DiagnosticReport(issues=issues)
        assert report.passed is False
        assert report.health == HealthState.UNHEALTHY
        assert len(report.errors) == 1

    def test_report_with_critical_is_critical(self) -> None:
        issues = (
            DiagnosticIssue(
                severity=DiagnosticSeverity.CRITICAL,
                diagnostic_id="configuration.load",
                message="Config corrupted",
                category=DiagnosticCategory.CONFIGURATION,
            ),
        )
        report = DiagnosticReport(issues=issues)
        assert report.passed is False
        assert report.health == HealthState.CRITICAL

    def test_report_info_issues(self) -> None:
        issues = (
            DiagnosticIssue(
                severity=DiagnosticSeverity.INFO,
                diagnostic_id="info-1",
                message="Info",
                category=DiagnosticCategory.ENVIRONMENT,
            ),
        )
        report = DiagnosticReport(issues=issues)
        assert len(report.info_issues) == 1
        assert report.health == HealthState.HEALTHY

    def test_validation_failure_affects_health(self) -> None:
        validation = ValidationReport(
            issues=(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_id="required-file",
                    message="Missing file",
                ),
            )
        )
        report = DiagnosticReport(
            issues=(),
            validation=validation,
        )
        assert report.passed is False
        assert report.health == HealthState.UNHEALTHY

    def test_validation_critical_affects_health(self) -> None:
        validation = ValidationReport(
            issues=(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    rule_id="critical-rule",
                    message="Critical issue",
                ),
            )
        )
        report = DiagnosticReport(issues=(), validation=validation)
        assert report.health == HealthState.CRITICAL

    def test_summary_contains_health(self) -> None:
        report = DiagnosticReport()
        assert "healthy" in report.summary


class TestDiagnosticContext:
    """Tests for DiagnosticContext."""

    def test_context_has_paths(self) -> None:
        context = DiagnosticContext()
        assert context.paths is not None
        assert context.paths.root.is_dir()

    def test_context_has_config(self) -> None:
        context = DiagnosticContext()
        assert context.config is not None
        assert context.config.project.name == "Universal Prompt Studio"

    def test_context_paths_none_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from Engineering.core import diagnostics as diagnostics_module
        from Engineering.core.exceptions import ProjectRootNotFoundError

        original_get_paths = diagnostics_module.get_paths

        def fake_get_paths():
            raise ProjectRootNotFoundError("cannot find root")

        monkeypatch.setattr(diagnostics_module, "get_paths", fake_get_paths)
        context = DiagnosticContext()
        assert context.paths is None

        monkeypatch.setattr(diagnostics_module, "get_paths", original_get_paths)

    def test_context_config_none_on_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from Engineering.core import diagnostics as diagnostics_module
        from Engineering.core.exceptions import ConfigurationError

        original_get_config = diagnostics_module.get_config

        def fake_get_config():
            raise ConfigurationError("cannot load config")

        monkeypatch.setattr(diagnostics_module, "get_config", fake_get_config)
        context = DiagnosticContext()
        assert context.config is None

        monkeypatch.setattr(diagnostics_module, "get_config", original_get_config)


class TestDiagnosticChecks:
    """Tests for individual diagnostic checks."""

    def test_project_root_check_passes(self) -> None:
        check = ProjectRootCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].severity == DiagnosticSeverity.INFO
        assert issues[0].diagnostic_id == "project.root.discovered"

    def test_configuration_load_check_passes(self) -> None:
        check = ConfigurationLoadCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].severity == DiagnosticSeverity.INFO
        assert issues[0].diagnostic_id == "configuration.load"

    def test_environment_python_check_passes(self) -> None:
        check = EnvironmentPythonVersionCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].diagnostic_id == "environment.python.version"

    def test_environment_engineering_package(self) -> None:
        check = EnvironmentEngineeringPackageCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].severity == DiagnosticSeverity.INFO
        assert "importable" in issues[0].message.lower()

    def test_engineering_validation_operational(self) -> None:
        check = EngineeringValidationCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].severity == DiagnosticSeverity.INFO

    def test_git_check_returns_issue(self) -> None:
        check = EnvironmentGitAvailableCheck()
        context = DiagnosticContext()
        issues = check.check(context)
        assert len(issues) == 1
        assert issues[0].diagnostic_id == "environment.git.available"


class TestDoctor:
    """Tests for the Doctor orchestrator."""

    def test_doctor_run_returns_report(self) -> None:
        doctor = Doctor()
        report = doctor.run()
        assert isinstance(report, DiagnosticReport)

    def test_doctor_run_has_diagnostics(self) -> None:
        doctor = Doctor()
        report = doctor.run()
        assert len(report.issues) > 0

    def test_doctor_run_includes_validation(self) -> None:
        doctor = Doctor()
        report = doctor.run()
        assert isinstance(report.validation, ValidationReport)

    def test_doctor_deterministic(self) -> None:
        doctor = Doctor()
        report1 = doctor.run()
        report2 = doctor.run()
        assert report1 == report2

    def test_doctor_issues_ordered(self) -> None:
        doctor = Doctor()
        report = doctor.run()
        categories = [issue.category.value for issue in report.issues]
        assert categories == sorted(categories)

    def test_doctor_accepts_custom_checks(self) -> None:
        class FakeCheck(DiagnosticCheck):
            @property
            def diagnostic_id(self) -> str:
                return "fake.check"

            @property
            def category(self) -> DiagnosticCategory:
                return DiagnosticCategory.ENVIRONMENT

            def check(self, context: DiagnosticContext) -> tuple[DiagnosticIssue, ...]:
                return (
                    DiagnosticIssue(
                        severity=DiagnosticSeverity.INFO,
                        diagnostic_id=self.diagnostic_id,
                        message="Fake check",
                        category=self.category,
                    ),
                )

        doctor = Doctor(diagnostic_checks=[FakeCheck()])
        report = doctor.run()
        assert any(issue.diagnostic_id == "fake.check" for issue in report.issues)


class TestDoctorReadOnly:
    """Tests verifying the Doctor is read-only."""

    def test_doctor_does_not_create_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from Engineering.core import diagnostics as diagnostics_module

        original_get_paths = diagnostics_module.get_paths
        fake_root = tmp_path / "root"
        fake_root.mkdir()

        class FakePaths:
            root = fake_root  # type: ignore[assignment]

        monkeypatch.setattr(
            diagnostics_module,
            "get_paths",
            lambda: FakePaths(),  # type: ignore[return-value]
        )

        doctor = Doctor()
        report = doctor.run()

        assert report is not None
        assert not any(path for path in fake_root.iterdir())

        monkeypatch.setattr(diagnostics_module, "get_paths", original_get_paths)