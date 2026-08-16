"""Immutable domain models for E-009 templates and artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


class TemplateCategory(Enum):
    """Initial built-in template classifications.

    Categories live in metadata rather than in discovery or rendering logic,
    allowing later milestones to introduce additional families cleanly.
    """

    PYTHON = "python"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    PROJECT = "project"
    PLUGIN = "plugin"
    PROVIDER = "provider"
    THEME = "theme"
    WORKFLOW = "workflow"


class VariableKind(Enum):
    """How a variable obtains its value during request construction."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    DEFAULTED = "defaulted"


@dataclass(frozen=True, slots=True)
class TemplateVariable:
    """A declared input accepted by a template definition."""

    name: str
    kind: VariableKind = VariableKind.REQUIRED
    value_type: str = "string"
    default: object | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class TemplateMetadata:
    """Identity and descriptive metadata for a template definition."""

    template_id: str
    name: str
    version: str
    category: TemplateCategory
    description: str = ""
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactDefinition:
    """An intended output backed by an E-008 source template."""

    relative_path: str
    source_template_id: str
    artifact_type: str = "source"
    name: str = ""
    description: str = ""
    values: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TemplateDefinition:
    """A versioned collection of variables and generated artifacts."""

    metadata: TemplateMetadata
    variables: tuple[TemplateVariable, ...] = ()
    artifacts: tuple[ArtifactDefinition, ...] = ()

    @property
    def template_id(self) -> str:
        """Return the stable definition identifier."""

        return self.metadata.template_id

    @property
    def version(self) -> str:
        """Return the definition version."""

        return self.metadata.version
