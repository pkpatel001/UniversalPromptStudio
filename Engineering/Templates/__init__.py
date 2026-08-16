"""Reusable template and artifact definitions for the Engineering Toolkit.

E-009 builds on :mod:`Engineering.CodeGeneration`; it describes what a
template produces while the code-generation package remains responsible for
planning, rendering, safety checks, and filesystem writes.
"""

from .catalog import TemplateCatalog
from .discovery import (
    DirectoryTemplateDefinitionRepository,
    built_in_definition_repository,
)
from .executor import TemplateExecutionResult, TemplateExecutor
from .manifest import (
    ArtifactManifest,
    ArtifactManifestBuilder,
    ArtifactManifestEntry,
    ManifestVerificationIssue,
    ManifestVerificationReport,
)
from .models import (
    ArtifactDefinition,
    TemplateCategory,
    TemplateDefinition,
    TemplateMetadata,
    TemplateVariable,
    VariableKind,
)
from .service import TemplateArtifactService
from .validation import TemplateDefinitionValidator

__all__ = [
    "ArtifactDefinition",
    "ArtifactManifest",
    "ArtifactManifestBuilder",
    "ArtifactManifestEntry",
    "DirectoryTemplateDefinitionRepository",
    "ManifestVerificationIssue",
    "ManifestVerificationReport",
    "TemplateArtifactService",
    "TemplateCatalog",
    "TemplateCategory",
    "TemplateDefinition",
    "TemplateDefinitionValidator",
    "TemplateExecutionResult",
    "TemplateExecutor",
    "TemplateMetadata",
    "TemplateVariable",
    "VariableKind",
    "built_in_definition_repository",
]
