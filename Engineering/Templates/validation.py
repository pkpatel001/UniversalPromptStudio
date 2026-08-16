"""Validation for E-009 template definitions."""

from __future__ import annotations

import re

from Engineering.CodeGeneration.templates import TemplateRepository
from Engineering.core.validation import ValidationIssue, ValidationSeverity

from .models import TemplateDefinition, VariableKind

_DEFINITION_ID = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)+$")
_VARIABLE_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
_VALUE_TYPES = frozenset({"string", "integer", "number", "boolean", "list", "mapping"})


class TemplateDefinitionValidator:
    """Validate definition structure and E-008 source-template references."""

    def __init__(self, source_repository: TemplateRepository | None = None) -> None:
        self._source_repository = source_repository

    def validate(self, definition: TemplateDefinition) -> tuple[ValidationIssue, ...]:
        """Return all issues in deterministic declaration order."""

        issues: list[ValidationIssue] = []
        metadata = definition.metadata

        if not _DEFINITION_ID.fullmatch(metadata.template_id):
            issues.append(self._error("template.invalid-id", "Invalid template definition ID."))
        if not metadata.name.strip():
            issues.append(self._error("template.empty-name", "Template name must not be empty."))
        if not _VERSION.fullmatch(metadata.version):
            issues.append(
                self._error(
                    "template.invalid-version", "Template version must be semantic."
                )
            )
        if not definition.artifacts:
            issues.append(self._error("template.no-artifacts", "Template must define an artifact."))

        variable_names: set[str] = set()
        for variable in definition.variables:
            if not _VARIABLE_NAME.fullmatch(variable.name):
                issues.append(
                    self._error(
                        "template.invalid-variable",
                        f"Invalid variable: {variable.name!r}.",
                    )
                )
            if variable.name in variable_names:
                issues.append(
                    self._error(
                        "template.duplicate-variable",
                        f"Duplicate variable: {variable.name!r}.",
                    )
                )
            variable_names.add(variable.name)
            if variable.value_type not in _VALUE_TYPES:
                issues.append(
                    self._error(
                        "template.invalid-variable-type",
                        f"Unsupported type {variable.value_type!r} for {variable.name!r}.",
                    )
                )
            if variable.kind == VariableKind.DEFAULTED and variable.default is None:
                issues.append(
                    self._error(
                        "template.missing-default",
                        f"Defaulted variable {variable.name!r} has no default.",
                    )
                )
            elif variable.kind == VariableKind.DEFAULTED and not value_matches_type(
                variable.default, variable.value_type
            ):
                issues.append(
                    self._error(
                        "template.invalid-default-type",
                        f"Default for {variable.name!r} does not match "
                        f"{variable.value_type!r}.",
                    )
                )

        artifact_paths: set[str] = set()
        for artifact in definition.artifacts:
            normalized = artifact.relative_path.replace("\\", "/")
            if (
                not normalized
                or normalized.startswith("/")
                or ".." in normalized.split("/")
            ):
                issues.append(
                    self._error(
                        "template.invalid-artifact-path",
                        f"Invalid artifact path: {artifact.relative_path!r}.",
                    )
                )
            if normalized in artifact_paths:
                issues.append(
                    self._error(
                        "template.duplicate-artifact",
                        f"Duplicate artifact path: {artifact.relative_path!r}.",
                    )
                )
            artifact_paths.add(normalized)
            if (
                self._source_repository is not None
                and not self._source_repository.contains(artifact.source_template_id)
            ):
                issues.append(
                    self._error(
                        "template.unknown-source",
                        f"Unknown source template: {artifact.source_template_id!r}.",
                    )
                )

        return tuple(issues)

    @staticmethod
    def _error(rule_id: str, message: str) -> ValidationIssue:
        return ValidationIssue(
            severity=ValidationSeverity.ERROR,
            rule_id=rule_id,
            message=message,
        )


def value_matches_type(value: object, value_type: str) -> bool:
    """Return whether a runtime value satisfies a declared template type."""

    if value_type == "string":
        return isinstance(value, str)
    if value_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if value_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if value_type == "boolean":
        return isinstance(value, bool)
    if value_type == "list":
        return isinstance(value, (list, tuple))
    if value_type == "mapping":
        return isinstance(value, dict)
    return False
