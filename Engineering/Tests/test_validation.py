"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Validation Framework Tests

Tests cover:
- ValidationIssue creation and properties
- ValidationReport aggregation, passed/failed, errors, warnings, summary
- ValidationContext helpers
- Validator rule execution
- RequiredDirectoryRule
- RequiredFileRule
- StructureValidationRule

===============================================================================
"""

from __future__ import annotations

import pytest

from Engineering.core.validation import (
    ValidationContext,
    ValidationIssue,
    ValidationReport,
    ValidationRule,
    ValidationSeverity,
    Validator,
)
from Engineering.Standards.project import (
    RequiredDirectoryRule,
    RequiredFileRule,
    StructureValidationRule,
)

# -----------------------------------------------------------------------------
# ValidationIssue
# -----------------------------------------------------------------------------


class TestValidationIssue:
    def test_issue_creation(self) -> None:
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule_id="test-rule",
            message="Something went wrong",
            location="some/path",
            context={"key": "value"},
        )
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.rule_id == "test-rule"
        assert issue.message == "Something went wrong"
        assert issue.location == "some/path"
        assert issue.context == {"key": "value"}

    def test_issue_without_optional_fields(self) -> None:
        issue = ValidationIssue(
            severity=ValidationSeverity.INFO,
            rule_id="info-rule",
            message="Info message",
        )
        assert issue.location is None
        assert issue.context is None


# -----------------------------------------------------------------------------
# ValidationReport
# -----------------------------------------------------------------------------


class TestValidationReport:
    def test_empty_report_passes(self) -> None:
        report = ValidationReport(issues=())
        assert report.passed is True
        assert report.summary == "Validation passed: no issues found."

    def test_report_with_info_only_passes(self) -> None:
        issues = (
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                rule_id="info",
                message="Info",
            ),
        )
        report = ValidationReport(issues=issues)
        assert report.passed is True
        assert len(report.errors) == 0
        assert len(report.warnings) == 0

    def test_report_with_error_fails(self) -> None:
        issues = (
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_id="e1",
                message="Error 1",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule_id="w1",
                message="Warning 1",
            ),
        )
        report = ValidationReport(issues=issues)
        assert report.passed is False
        assert len(report.errors) == 1
        assert len(report.warnings) == 1
        assert report.errors[0].rule_id == "e1"
        assert report.warnings[0].rule_id == "w1"

    def test_report_with_critical_fails(self) -> None:
        issues = (
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                rule_id="c1",
                message="Critical 1",
            ),
        )
        report = ValidationReport(issues=issues)
        assert report.passed is False
        assert len(report.errors) == 1
        assert report.errors[0].rule_id == "c1"

    def test_report_summary_passed(self) -> None:
        report = ValidationReport(issues=())
        assert "passed" in report.summary
        assert "no issues found" in report.summary

    def test_report_summary_failed(self) -> None:
        issues = (
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                rule_id="e1",
                message="Error",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule_id="w1",
                message="Warning",
            ),
        )
        report = ValidationReport(issues=issues)
        assert "failed" in report.summary
        assert "1 error(s)" in report.summary
        assert "1 warning(s)" in report.summary


# -----------------------------------------------------------------------------
# ValidationContext
# -----------------------------------------------------------------------------


class TestValidationContext:
    def test_context_has_paths(self) -> None:
        context = ValidationContext()
        assert context.paths is not None
        assert context.paths.root.is_dir()

    def test_context_has_config(self) -> None:
        context = ValidationContext()
        assert context.config is not None
        assert context.config.project.name == "Universal Prompt Studio"

    def test_file_exists_true(self) -> None:
        context = ValidationContext()
        assert context.file_exists("pyproject.toml") is True

    def test_file_exists_false(self) -> None:
        context = ValidationContext()
        assert context.file_exists("nonexistent_file_xyz.txt") is False

    def test_directory_exists_true(self) -> None:
        context = ValidationContext()
        assert context.directory_exists("Engineering") is True

    def test_directory_exists_false(self) -> None:
        context = ValidationContext()
        assert context.directory_exists("nonexistent_directory_xyz") is False

    def test_read_text_existing_file(self) -> None:
        context = ValidationContext()
        content = context.read_text("pyproject.toml")
        assert content is not None
        assert "[build-system]" in content

    def test_read_text_missing_file(self) -> None:
        context = ValidationContext()
        assert context.read_text("nonexistent_file_xyz.txt") is None


# -----------------------------------------------------------------------------
# Validator
# -----------------------------------------------------------------------------


class TestValidator:
    def test_validator_runs_single_rule(self) -> None:
        class FakeRule(ValidationRule):
            @property
            def rule_id(self) -> str:
                return "fake-rule"

            @property
            def severity(self) -> ValidationSeverity:
                return ValidationSeverity.INFO

            def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
                return (
                    ValidationIssue(
                        severity=self.severity,
                        rule_id=self.rule_id,
                        message="Fake issue",
                    ),
                )

        validator = Validator(rules=[FakeRule()])
        report = validator.validate()
        assert len(report.issues) == 1
        assert report.issues[0].rule_id == "fake-rule"

    def test_validator_runs_multiple_rules(self) -> None:
        class Rule1(ValidationRule):
            @property
            def rule_id(self) -> str:
                return "rule-1"

            @property
            def severity(self) -> ValidationSeverity:
                return ValidationSeverity.INFO

            def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
                return (
                    ValidationIssue(
                        severity=self.severity,
                        rule_id=self.rule_id,
                        message="Issue 1",
                    ),
                )

        class Rule2(ValidationRule):
            @property
            def rule_id(self) -> str:
                return "rule-2"

            @property
            def severity(self) -> ValidationSeverity:
                return ValidationSeverity.WARNING

            def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
                return (
                    ValidationIssue(
                        severity=self.severity,
                        rule_id=self.rule_id,
                        message="Issue 2",
                    ),
                )

        validator = Validator(rules=[Rule1(), Rule2()])
        report = validator.validate()
        assert len(report.issues) == 2
        assert len(report.warnings) == 1

    def test_validator_empty_rules(self) -> None:
        validator = Validator()
        report = validator.validate()
        assert report.passed is True
        assert len(report.issues) == 0

    def test_validator_add_rule(self) -> None:
        class AddRule(ValidationRule):
            @property
            def rule_id(self) -> str:
                return "added-rule"

            @property
            def severity(self) -> ValidationSeverity:
                return ValidationSeverity.ERROR

            def check(self, context: ValidationContext) -> tuple[ValidationIssue, ...]:
                return (
                    ValidationIssue(
                        severity=self.severity,
                        rule_id=self.rule_id,
                        message="Added",
                    ),
                )

        validator = Validator()
        validator.add_rule(AddRule())
        report = validator.validate()
        assert len(report.issues) == 1
        assert report.issues[0].rule_id == "added-rule"


# -----------------------------------------------------------------------------
# RequiredDirectoryRule
# -----------------------------------------------------------------------------


class TestRequiredDirectoryRule:
    def test_existing_directory_passes(self) -> None:
        rule = RequiredDirectoryRule(
            relative_path="Engineering",
            description="Engineering Toolkit",
        )
        context = ValidationContext()
        issues = rule.check(context)
        assert len(issues) == 0

    def test_missing_directory_fails(self) -> None:
        rule = RequiredDirectoryRule(
            relative_path="nonexistent_directory_xyz",
            description="Fake directory",
        )
        context = ValidationContext()
        issues = rule.check(context)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert issues[0].rule_id == "required-directory:nonexistent_directory_xyz"
        assert "missing" in issues[0].message.lower()

    def test_rule_severity(self) -> None:
        rule = RequiredDirectoryRule(
            relative_path="Engineering",
            description="Engineering Toolkit",
        )
        assert rule.severity == ValidationSeverity.ERROR

    def test_rule_id(self) -> None:
        rule = RequiredDirectoryRule(
            relative_path="Engineering",
            description="Engineering Toolkit",
        )
        assert rule.rule_id == "required-directory:Engineering"


# -----------------------------------------------------------------------------
# RequiredFileRule
# -----------------------------------------------------------------------------


class TestRequiredFileRule:
    def test_existing_file_passes(self) -> None:
        rule = RequiredFileRule(
            relative_path="pyproject.toml",
            description="Project manifest",
        )
        context = ValidationContext()
        issues = rule.check(context)
        assert len(issues) == 0

    def test_missing_file_fails(self) -> None:
        rule = RequiredFileRule(
            relative_path="nonexistent_file_xyz.txt",
            description="Fake file",
        )
        context = ValidationContext()
        issues = rule.check(context)
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert issues[0].rule_id == "required-file:nonexistent_file_xyz.txt"
        assert "missing" in issues[0].message.lower()

    def test_rule_id(self) -> None:
        rule = RequiredFileRule(
            relative_path="README.md",
            description="Readme",
        )
        assert rule.rule_id == "required-file:README.md"


# -----------------------------------------------------------------------------
# StructureValidationRule
# -----------------------------------------------------------------------------


class TestStructureValidationRule:
    def test_valid_structure_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from Engineering.Standards import project as project_module

        original_verify_structure = project_module.verify_structure

        monkeypatch.setattr(project_module, "verify_structure", lambda: [])

        rule = StructureValidationRule()
        context = ValidationContext()
        issues = rule.check(context)
        assert len(issues) == 0

        monkeypatch.setattr(project_module, "verify_structure", original_verify_structure)

    def test_rule_id(self) -> None:
        rule = StructureValidationRule()
        assert rule.rule_id == "project-structure"

    def test_rule_severity(self) -> None:
        rule = StructureValidationRule()
        assert rule.severity == ValidationSeverity.ERROR

    def test_missing_directory_reported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from Engineering.Standards import project as project_module

        original_verify_structure = project_module.verify_structure

        def fake_verify_structure() -> list[str]:
            return ["Missing required directory: FakeDir"]

        monkeypatch.setattr(project_module, "verify_structure", fake_verify_structure)

        rule = StructureValidationRule()
        context = ValidationContext()
        issues = rule.check(context)

        assert len(issues) == 1
        assert issues[0].rule_id == "project-structure"
        assert issues[0].location == "FakeDir"
        assert "FakeDir" in issues[0].message

        monkeypatch.setattr(project_module, "verify_structure", original_verify_structure)
