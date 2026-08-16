"""Bridge E-009 definitions into E-008 generation requests."""

from __future__ import annotations

from collections.abc import Mapping

from Engineering.CodeGeneration.models import (
    ArtifactSpec,
    GenerationContext,
    GenerationRequest,
    OverwritePolicy,
)
from Engineering.core.exceptions import GenerationValidationError

from .models import TemplateDefinition, VariableKind
from .validation import TemplateDefinitionValidator, value_matches_type


class TemplateArtifactService:
    """Construct E-008 requests from validated E-009 definitions."""

    def __init__(self, validator: TemplateDefinitionValidator | None = None) -> None:
        self._validator = validator or TemplateDefinitionValidator()

    def build_request(
        self,
        definition: TemplateDefinition,
        *,
        destination: str,
        context: GenerationContext,
        values: Mapping[str, object] | None = None,
        overwrite: OverwritePolicy = OverwritePolicy.NEVER,
        dry_run: bool = False,
    ) -> GenerationRequest:
        """Validate a definition and convert it to a generation request."""

        issues = self._validator.validate(definition)
        if issues:
            details = "; ".join(issue.message for issue in issues)
            raise GenerationValidationError(f"Invalid template definition: {details}")

        supplied = dict(values or {})
        declared = {variable.name: variable for variable in definition.variables}
        unknown = sorted(set(supplied) - set(declared))
        if unknown:
            raise GenerationValidationError(
                f"Unknown template variable(s): {', '.join(unknown)}"
            )

        invalid_types = sorted(
            name
            for name, value in supplied.items()
            if not value_matches_type(value, declared[name].value_type)
        )
        if invalid_types:
            details = ", ".join(
                f"{name} (expected {declared[name].value_type})"
                for name in invalid_types
            )
            raise GenerationValidationError(
                f"Invalid template variable type(s): {details}"
            )

        resolved: dict[str, object] = {}
        missing: list[str] = []
        for variable in definition.variables:
            if variable.name in supplied:
                resolved[variable.name] = supplied[variable.name]
            elif variable.kind == VariableKind.DEFAULTED:
                resolved[variable.name] = variable.default
            elif variable.kind == VariableKind.REQUIRED:
                missing.append(variable.name)
        if missing:
            raise GenerationValidationError(
                f"Missing required template variable(s): {', '.join(sorted(missing))}"
            )

        artifacts = tuple(
            ArtifactSpec(
                relative_path=artifact.relative_path,
                template_id=artifact.source_template_id,
                artifact_type=artifact.artifact_type,
                name=artifact.name,
                description=artifact.description,
                values={**resolved, **dict(artifact.values)},
            )
            for artifact in definition.artifacts
        )
        return GenerationRequest(
            generator_id=definition.template_id,
            destination=destination,
            context=context,
            artifacts=artifacts,
            overwrite=overwrite,
            dry_run=dry_run,
        )
