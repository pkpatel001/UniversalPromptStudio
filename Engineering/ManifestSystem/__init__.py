"""E-012 typed manifest discovery, validation, and migration planning."""

from .adapters import (
    AIProviderManifestAdapter,
    BuildManifestAdapter,
    DocumentationManifestAdapter,
    PluginManifestAdapter,
    ReleaseManifestAdapter,
    TemplateArtifactManifestAdapter,
    default_manifest_adapters,
)
from .migrations import (
    ManifestMigrationPlanner,
    ManifestMigrationRegistry,
    ManifestMigrationService,
    default_manifest_migrations,
)
from .models import (
    ManifestInspectionReport,
    ManifestIssue,
    ManifestKind,
    ManifestMigrationPlan,
    ManifestMigrationReport,
    ManifestMigrationStep,
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
    "AIProviderManifestAdapter",
    "BuildManifestAdapter",
    "DocumentationManifestAdapter",
    "ManifestAdapter",
    "ManifestDependency",
    "ManifestInspectionReport",
    "ManifestInspectionService",
    "ManifestIssue",
    "ManifestKind",
    "ManifestMigrationPlan",
    "ManifestMigrationPlanner",
    "ManifestMigrationRegistry",
    "ManifestMigrationReport",
    "ManifestMigrationService",
    "ManifestMigrationStep",
    "ManifestRecord",
    "ManifestRegistry",
    "ManifestRelationshipValidator",
    "ManifestSchemaContract",
    "ManifestSpec",
    "ManifestValidationReport",
    "ManifestValidationService",
    "PluginManifestAdapter",
    "ReleaseManifestAdapter",
    "SchemaCompatibility",
    "TemplateArtifactManifestAdapter",
    "default_manifest_adapters",
    "default_manifest_dependencies",
    "default_manifest_migrations",
]
