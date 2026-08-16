"""File-backed discovery for E-009 template definitions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from Engineering.CodeGeneration.templates import DirectoryTemplateRepository
from Engineering.core.exceptions import TemplateError, TemplateNotFoundError
from Engineering.core.filesystem import read_yaml

from .models import (
    ArtifactDefinition,
    TemplateCategory,
    TemplateDefinition,
    TemplateMetadata,
    TemplateVariable,
    VariableKind,
)
from .validation import TemplateDefinitionValidator

_DEFINITION_SUFFIX = ".template.yaml"


def built_in_definition_repository() -> DirectoryTemplateDefinitionRepository:
    """Return the repository for definitions bundled with Engineering."""

    root = Path(__file__).resolve().parent
    source_repository = DirectoryTemplateRepository(root / "CodeGeneration")
    return DirectoryTemplateDefinitionRepository(
        root / "Definitions",
        TemplateDefinitionValidator(source_repository),
    )


class DirectoryTemplateDefinitionRepository:
    """Discover validated template definitions from a directory tree.

    Definition files use the deterministic ``*.template.yaml`` convention.
    Their identity comes from file content rather than their location, which
    lets callers organize collections without changing stable template IDs.
    """

    def __init__(
        self,
        root: Path,
        validator: TemplateDefinitionValidator | None = None,
    ) -> None:
        self._root = root.resolve()
        self._validator = validator or TemplateDefinitionValidator()

    @property
    def root(self) -> Path:
        """Return the resolved discovery root."""

        return self._root

    def definition_ids(self) -> tuple[str, ...]:
        """Return discovered definition IDs in stable order."""

        return tuple(definition.template_id for definition in self.definitions())

    def definitions(self) -> tuple[TemplateDefinition, ...]:
        """Load every definition in deterministic path order."""

        if not self._root.is_dir():
            return ()
        definitions = tuple(
            self._load(path)
            for path in sorted(self._root.rglob(f"*{_DEFINITION_SUFFIX}"))
            if path.is_file()
        )
        keys = [(item.template_id, item.version) for item in definitions]
        if len(keys) != len(set(keys)):
            raise TemplateError("Duplicate template definition ID/version discovered.")
        return tuple(sorted(definitions, key=lambda item: (item.template_id, item.version)))

    def resolve(self, template_id: str, version: str | None = None) -> TemplateDefinition:
        """Resolve an exact definition or the newest registered version."""

        from .catalog import TemplateCatalog

        catalog = TemplateCatalog()
        for definition in self.definitions():
            catalog.register(definition)
        try:
            return catalog.resolve(template_id, version)
        except Exception as exc:
            raise TemplateNotFoundError(str(exc)) from exc

    def _load(self, path: Path) -> TemplateDefinition:
        """Parse and validate one YAML definition file."""

        try:
            data = read_yaml(path)
            definition = _definition_from_mapping(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise TemplateError(f"Invalid template definition {path}: {exc}") from exc

        issues = self._validator.validate(definition)
        if issues:
            details = "; ".join(issue.message for issue in issues)
            raise TemplateError(f"Invalid template definition {path}: {details}")
        return definition


def _definition_from_mapping(data: Mapping[str, Any]) -> TemplateDefinition:
    metadata_data = _mapping(data, "metadata")
    metadata = TemplateMetadata(
        template_id=_string(metadata_data, "id"),
        name=_string(metadata_data, "name"),
        version=_string(metadata_data, "version"),
        category=TemplateCategory(_string(metadata_data, "category")),
        description=_optional_string(metadata_data, "description"),
        tags=tuple(_string_list(metadata_data, "tags")),
    )
    variables = tuple(
        TemplateVariable(
            name=_string(item, "name"),
            kind=VariableKind(_optional_string(item, "kind") or "required"),
            value_type=_optional_string(item, "type") or "string",
            default=item.get("default"),
            description=_optional_string(item, "description"),
        )
        for item in _mapping_list(data, "variables")
    )
    artifacts = tuple(
        ArtifactDefinition(
            relative_path=_string(item, "path"),
            source_template_id=_string(item, "template"),
            artifact_type=_optional_string(item, "type") or "source",
            name=_optional_string(item, "name"),
            description=_optional_string(item, "description"),
            values=_optional_mapping(item, "values"),
        )
        for item in _mapping_list(data, "artifacts")
    )
    return TemplateDefinition(metadata=metadata, variables=variables, artifacts=artifacts)


def _mapping(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = data[key]
    if not isinstance(value, dict):
        raise TypeError(f"{key!r} must be a mapping")
    return value


def _mapping_list(data: Mapping[str, Any], key: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise TypeError(f"{key!r} must be a list of mappings")
    return tuple(value)


def _string(data: Mapping[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"{key!r} must be a string")
    return value


def _optional_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key, "")
    if not isinstance(value, str):
        raise TypeError(f"{key!r} must be a string")
    return value


def _string_list(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{key!r} must be a list of strings")
    return tuple(value)


def _optional_mapping(data: Mapping[str, Any], key: str) -> Mapping[str, object]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise TypeError(f"{key!r} must be a mapping")
    return value
