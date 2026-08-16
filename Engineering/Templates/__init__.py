"""Reusable template and artifact definitions for the Engineering Toolkit.

E-009 builds on :mod:`Engineering.CodeGeneration`; it describes what a
template produces while the code-generation package remains responsible for
planning, rendering, safety checks, and filesystem writes.
"""

from .catalog import TemplateCatalog
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
    "TemplateArtifactService",
    "TemplateCatalog",
    "TemplateCategory",
    "TemplateDefinition",
    "TemplateDefinitionValidator",
    "TemplateMetadata",
    "TemplateVariable",
    "VariableKind",
]
