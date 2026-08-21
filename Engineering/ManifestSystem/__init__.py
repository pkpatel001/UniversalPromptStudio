"""E-012 typed manifest discovery and validation system."""

from .adapters import (
    BuildManifestAdapter,
    ReleaseManifestAdapter,
    TemplateArtifactManifestAdapter,
    default_manifest_adapters,
)
from .models import (
    ManifestInspectionReport,
    ManifestIssue,
    ManifestKind,
    ManifestRecord,
    ManifestSchemaContract,
    ManifestSpec,
    ManifestValidationReport,
    SchemaCompatibility,
)
from .registry import ManifestAdapter, ManifestRegistry
from .relationships import (
    ManifestDependency,
    ManifestRelationshipValidator,
    default_manifest_dependencies,
)
from .service import ManifestInspectionService, ManifestValidationService

__all__ = [
    "BuildManifestAdapter",
    "ManifestAdapter",
    "ManifestInspectionReport",
    "ManifestInspectionService",
    "ManifestIssue",
    "ManifestKind",
    "ManifestDependency",
    "ManifestRecord",
    "ManifestRegistry",
    "ManifestRelationshipValidator",
    "ManifestSchemaContract",
    "ManifestSpec",
    "ManifestValidationReport",
    "ManifestValidationService",
    "ReleaseManifestAdapter",
    "TemplateArtifactManifestAdapter",
    "default_manifest_adapters",
    "default_manifest_dependencies",
    "SchemaCompatibility",
]
