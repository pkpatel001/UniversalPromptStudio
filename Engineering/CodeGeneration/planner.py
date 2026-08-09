"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Generation Planner

This module constructs and validates GenerationPlans from GenerationRequests
without touching the filesystem. The planner ensures structural validity
before the engine commits to any I/O.

Responsibilities
----------------
* Validate that the request contains at least one artifact
* Detect duplicate destination paths within a plan
* Reuse E-004 ValidationIssue/ValidationReport for plan issues
* Enforce path format constraints on artifact relative paths

Public API
----------
from Engineering.CodeGeneration.planner import GenerationPlanner

planner = GenerationPlanner()
plan = planner.plan(request)

===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from Engineering.core.exceptions import GenerationValidationError
from Engineering.core.validation import ValidationIssue, ValidationSeverity

from .models import ArtifactSpec, GenerationPlan, GenerationRequest

__all__ = ["GenerationPlanner"]


class GenerationPlanner:
    """
    Constructs validated GenerationPlans from GenerationRequests.

    The planner performs only structural validation: it does not resolve
    templates, render content, or write files. It reuses the E-004
    ``ValidationIssue`` model for structured issue reporting.
    """

    def plan(
        self,
        request: GenerationRequest,
        project_root: Path,
        template_ids: tuple[str, ...] | None = None,
    ) -> GenerationPlan:
        """
        Construct and validate a GenerationPlan from a request.

        Parameters
        ----------
        request
            The generation request to plan.
        project_root
            Absolute path to the project root.
        template_ids
            Optional list of available template identifiers for
            cross-reference validation.

        Returns
        -------
        GenerationPlan
            Validated plan (may contain issues; check ``is_valid``).

        Raises
        ------
        GenerationValidationError
            If the request is structurally invalid.
        """

        if not request.artifacts:
            raise GenerationValidationError(
                f"Generation request {request.generator_id!r} "
                f"contains no artifacts."
            )

        destination_root = (project_root / request.destination).resolve()

        issues: list[ValidationIssue] = []
        seen_paths: dict[str, str] = {}

        for spec in request.artifacts:
            path_issues = self._validate_artifact_spec(spec, template_ids)
            issues.extend(path_issues)

            normalized = spec.relative_path.replace("\\", "/")
            if normalized in seen_paths:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        rule_id="generation.duplicate-destination",
                        message=(
                            f"Duplicate artifact destination: {spec.relative_path!r} "
                            f"(first declared by {seen_paths[normalized]!r})"
                        ),
                        location=spec.relative_path,
                    )
                )
            else:
                seen_paths[normalized] = spec.template_id

        return GenerationPlan(
            generator_id=request.generator_id,
            destination_root=destination_root,
            context=request.context,
            overwrite=request.overwrite,
            artifacts=request.artifacts,
            issues=tuple(issues),
            dry_run=request.dry_run,
        )

    def _validate_artifact_spec(
        self,
        spec: ArtifactSpec,
        template_ids: tuple[str, ...] | None,
    ) -> list[ValidationIssue]:
        """
        Validate a single artifact specification.

        Parameters
        ----------
        spec
            The artifact spec to validate.
        template_ids
            Available template identifiers, or None to skip
            template existence checks.

        Returns
        -------
        list[ValidationIssue]
            Issues found. Empty list means the spec passed.
        """

        issues: list[ValidationIssue] = []

        if not spec.relative_path:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_id="generation.empty-path",
                    message="Artifact relative_path must not be empty.",
                )
            )

        if spec.relative_path.startswith("/") or spec.relative_path.startswith("\\"):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_id="generation.absolute-path",
                    message=(
                        f"Artifact relative_path must not be absolute: "
                        f"{spec.relative_path!r}"
                    ),
                    location=spec.relative_path,
                )
            )

        parts = spec.relative_path.replace("\\", "/").split("/")
        for part in parts:
            if part in ("..", ""):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        rule_id="generation.path-traversal",
                        message=(
                            f"Artifact relative_path contains traversal "
                            f"component: {part!r} in {spec.relative_path!r}"
                        ),
                        location=spec.relative_path,
                    )
                )
                break

        if not spec.template_id:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule_id="generation.empty-template-id",
                    message=(
                        f"Artifact {spec.relative_path!r} "
                        f"has no template_id."
                    ),
                    location=spec.relative_path,
                )
            )

        if template_ids is not None and spec.template_id not in template_ids:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule_id="generation.unknown-template",
                    message=(
                        f"Template {spec.template_id!r} not found "
                        f"in the available template repository."
                    ),
                    location=spec.relative_path,
                )
            )

        return issues
