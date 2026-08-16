"""Deterministic in-memory catalog for E-009 template definitions."""

from __future__ import annotations

from packaging.version import Version

from Engineering.core.exceptions import CodeGenerationError

from .models import TemplateCategory, TemplateDefinition


class TemplateCatalog:
    """Register and resolve versioned template definitions.

    The catalog intentionally handles lookup only. Source-template discovery
    remains the responsibility of E-008 ``TemplateRepository`` implementations.
    """

    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], TemplateDefinition] = {}

    def register(self, definition: TemplateDefinition) -> None:
        """Register a definition, rejecting duplicate ID/version pairs."""

        key = (definition.template_id, definition.version)
        if key in self._definitions:
            raise CodeGenerationError(
                "Template definition already registered: "
                f"{definition.template_id!r} version {definition.version!r}"
            )
        self._definitions[key] = definition

    def resolve(self, template_id: str, version: str | None = None) -> TemplateDefinition:
        """Resolve an exact version or the highest registered version."""

        candidates = [
            definition
            for (registered_id, registered_version), definition in self._definitions.items()
            if registered_id == template_id
            and (version is None or registered_version == version)
        ]
        if not candidates:
            suffix = f" version {version!r}" if version is not None else ""
            raise CodeGenerationError(
                f"No template definition registered: {template_id!r}{suffix}"
            )
        return max(candidates, key=lambda item: Version(item.version))

    def contains(self, template_id: str, version: str | None = None) -> bool:
        """Return whether the requested definition is registered."""

        return any(
            registered_id == template_id
            and (version is None or registered_version == version)
            for registered_id, registered_version in self._definitions
        )

    def definitions(
        self, category: TemplateCategory | None = None
    ) -> tuple[TemplateDefinition, ...]:
        """Return definitions in stable ID/version order, optionally filtered."""

        definitions = (
            definition
            for definition in self._definitions.values()
            if category is None or definition.metadata.category == category
        )
        return tuple(sorted(definitions, key=lambda item: (item.template_id, item.version)))
