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
    ManifestSpec,
)
from .registry import ManifestAdapter, ManifestRegistry
from .service import ManifestInspectionService

__all__ = [
    "BuildManifestAdapter",
    "ManifestAdapter",
    "ManifestInspectionReport",
    "ManifestInspectionService",
    "ManifestIssue",
    "ManifestKind",
    "ManifestRecord",
    "ManifestRegistry",
    "ManifestSpec",
    "ReleaseManifestAdapter",
    "TemplateArtifactManifestAdapter",
    "default_manifest_adapters",
]
