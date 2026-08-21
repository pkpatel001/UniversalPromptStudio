"""Adapters connecting E-012 to existing producer-owned manifest readers."""

from __future__ import annotations

from pathlib import Path

from Engineering.BuildSystem import BUILD_MANIFEST_NAME, BuildManifest
from Engineering.core.exceptions import EngineeringError, ManifestError
from Engineering.ReleaseSystem import RELEASE_MANIFEST_NAME, ReleaseManifest
from Engineering.Templates import ArtifactManifest
from Engineering.Templates.executor import DEFAULT_MANIFEST_NAME

from .models import ManifestKind, ManifestSpec
from .registry import ManifestAdapter


class _ReaderAdapter:
    """Common error translation for producer-owned readers."""

    spec: ManifestSpec

    def validate(self, path: Path) -> int:
        """Validate through the concrete producer reader."""

        try:
            schema_version = self._read_schema_version(path)
        except (EngineeringError, KeyError, OSError, TypeError, UnicodeError, ValueError) as exc:
            raise ManifestError(str(exc)) from exc
        if schema_version not in self.spec.supported_schema_versions:
            raise ManifestError(
                f"Unsupported schema version {schema_version} for {self.spec.manifest_id}."
            )
        return schema_version

    def _read_schema_version(self, path: Path) -> int:
        raise NotImplementedError


class BuildManifestAdapter(_ReaderAdapter):
    """Validate E-010 build manifests."""

    spec = ManifestSpec("ups.build", ManifestKind.BUILD, BUILD_MANIFEST_NAME, (1,))

    def _read_schema_version(self, path: Path) -> int:
        return BuildManifest.read(path).schema_version


class TemplateArtifactManifestAdapter(_ReaderAdapter):
    """Validate E-009 template artifact manifests."""

    spec = ManifestSpec(
        "ups.template-artifact",
        ManifestKind.TEMPLATE_ARTIFACT,
        DEFAULT_MANIFEST_NAME,
        (1,),
    )

    def _read_schema_version(self, path: Path) -> int:
        return ArtifactManifest.read(path).schema_version


class ReleaseManifestAdapter(_ReaderAdapter):
    """Validate E-011 release manifests."""

    spec = ManifestSpec("ups.release", ManifestKind.RELEASE, RELEASE_MANIFEST_NAME, (1,))

    def _read_schema_version(self, path: Path) -> int:
        return ReleaseManifest.read(path).schema_version


def default_manifest_adapters() -> tuple[ManifestAdapter, ...]:
    """Return all built-in adapters in stable registration order."""

    return (
        BuildManifestAdapter(),
        ReleaseManifestAdapter(),
        TemplateArtifactManifestAdapter(),
    )
