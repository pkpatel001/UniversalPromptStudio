"""Bridge E-009 definitions into E-008 generation requests."""

from __future__ import annotations

import re
from collections.abc import Mapping
from string import Formatter

from Engineering.CodeGeneration.models import (
    ArtifactSpec,
    GenerationContext,
    GenerationRequest,
    OverwritePolicy,
)
from Engineering.core.exceptions import GenerationValidationError

from .models import TemplateDefinition, VariableKind
from .validation import TemplateDefinitionValidator, value_matches_type

_PATH_FIELD = re.compile(r"^[a-z_][a-z0-9_]*$")


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
                relative_path=_resolve_artifact_path(artifact.relative_path, resolved),
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


def _resolve_artifact_path(pattern: str, values: Mapping[str, object]) -> str:
    """Expand simple declared string fields in one artifact path."""

    parts: list[str] = []
    try:
        parsed = tuple(Formatter().parse(pattern))
    except ValueError as exc:
        raise GenerationValidationError("Invalid artifact path placeholder syntax.") from exc
    for literal, field, format_spec, conversion in parsed:
        parts.append(literal)
        if field is None:
            continue
        if _PATH_FIELD.fullmatch(field) is None or format_spec or conversion is not None:
            raise GenerationValidationError(
                "Artifact paths accept only simple declared variable placeholders."
            )
        value = values.get(field)
        if not isinstance(value, str):
            raise GenerationValidationError(
                f"Artifact path variable {field!r} must be a supplied string."
            )
        parts.append(value)
    return "".join(parts)
