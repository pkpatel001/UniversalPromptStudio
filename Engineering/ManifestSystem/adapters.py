"""Adapters connecting E-012 to existing producer-owned manifest readers."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from Engineering.BuildSystem import BUILD_MANIFEST_NAME, BuildManifest
from Engineering.core.constants import DEFAULT_MANIFEST_FILENAME
from Engineering.core.exceptions import EngineeringError, ManifestError
from Engineering.core.filesystem import read_json, read_yaml
from Engineering.PluginSystem import PLUGIN_MANIFEST_NAME, PluginManifestReader
from Engineering.ProviderSystem import (
    AI_PROVIDER_MANIFEST_NAME,
    ProviderManifestReader,
)
from Engineering.ReleaseSystem import RELEASE_MANIFEST_NAME, ReleaseManifest
from Engineering.Templates import ArtifactManifest
from Engineering.Templates.executor import DEFAULT_MANIFEST_NAME

from .models import ManifestKind, ManifestSpec
from .registry import ManifestAdapter


class _ReaderAdapter:
    """Common error translation for producer-owned readers."""

    spec: ManifestSpec

    def detect_schema_version(self, path: Path) -> int:
        """Read a versioned JSON envelope without invoking the producer reader."""

        data = read_json(path)
        schema_version = data["schema_version"]
        if type(schema_version) is not int:
            raise TypeError("schema_version must be an integer")
        return schema_version

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

    spec = ManifestSpec(
        "ups.build",
        ManifestKind.BUILD,
        BUILD_MANIFEST_NAME,
        (1,),
        current_schema_version=1,
    )

    def _read_schema_version(self, path: Path) -> int:
        return BuildManifest.read(path).schema_version


class TemplateArtifactManifestAdapter(_ReaderAdapter):
    """Validate E-009 template artifact manifests."""

    spec = ManifestSpec(
        "ups.template-artifact",
        ManifestKind.TEMPLATE_ARTIFACT,
        DEFAULT_MANIFEST_NAME,
        (1,),
        current_schema_version=1,
        allow_multiple=True,
    )

    def _read_schema_version(self, path: Path) -> int:
        return ArtifactManifest.read(path).schema_version


class ReleaseManifestAdapter(_ReaderAdapter):
    """Validate E-011 release manifests."""

    spec = ManifestSpec(
        "ups.release",
        ManifestKind.RELEASE,
        RELEASE_MANIFEST_NAME,
        (1,),
        current_schema_version=1,
    )

    def _read_schema_version(self, path: Path) -> int:
        return ReleaseManifest.read(path).schema_version


class DocumentationManifestAdapter(_ReaderAdapter):
    """Validate legacy and versioned documentation manifests."""

    spec = ManifestSpec(
        "ups.documentation",
        ManifestKind.DOCUMENTATION,
        DEFAULT_MANIFEST_FILENAME,
        (0, 1),
        current_schema_version=1,
    )

    def detect_schema_version(self, path: Path) -> int:
        """Treat the historical unversioned YAML envelope as schema zero."""

        data = read_yaml(path)
        schema_version = data.get("schema_version", 0)
        if type(schema_version) is not int:
            raise TypeError("schema_version must be an integer")
        return schema_version

    def _read_schema_version(self, path: Path) -> int:
        data = read_yaml(path)
        schema_version = data.get("schema_version", 0)
        if type(schema_version) is not int:
            raise TypeError("schema_version must be an integer")
        self._validate_root(data, schema_version)
        return schema_version

    @classmethod
    def _validate_root(cls, data: dict[str, Any], schema_version: int) -> None:
        allowed_root = {"manifest"} if schema_version == 0 else {"schema_version", "manifest"}
        unexpected = sorted(set(data) - allowed_root)
        if unexpected:
            raise ManifestError(
                f"Unexpected documentation manifest keys: {', '.join(unexpected)}."
            )
        payload = data.get("manifest")
        if not isinstance(payload, dict):
            raise ManifestError("manifest must be a mapping")
        cls._require_nonempty_string(payload, "generated_by")
        cls._require_portable_path(payload, "output_root")
        cls._validate_entries(payload.get("documents"), "documents", "title")
        if "failed" in payload:
            cls._validate_entries(payload["failed"], "failed", "reason")

    @classmethod
    def _validate_entries(
        cls, entries: object, field: str, detail_field: str
    ) -> None:
        if not isinstance(entries, list):
            raise ManifestError(f"manifest.{field} must be a list")
        identifiers: set[str] = set()
        paths: set[str] = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ManifestError(f"manifest.{field}[{index}] must be a mapping")
            identifier = cls._require_nonempty_string(entry, "identifier")
            path = cls._require_portable_path(entry, "path")
            cls._require_nonempty_string(entry, detail_field)
            if identifier in identifiers:
                raise ManifestError(f"Duplicate documentation identifier: {identifier}")
            if path in paths:
                raise ManifestError(f"Duplicate documentation path: {path}")
            identifiers.add(identifier)
            paths.add(path)

    @staticmethod
    def _require_nonempty_string(data: dict[str, Any], field: str) -> str:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ManifestError(f"{field} must be a non-empty string")
        return value


    @classmethod
    def _require_portable_path(cls, data: dict[str, Any], field: str) -> str:
        value = cls._require_nonempty_string(data, field)
        if "\\" in value:
            raise ManifestError(f"{field} must use portable forward slashes")
        path = PurePosixPath(value)
        has_drive_prefix = bool(path.parts and path.parts[0].endswith(":"))
        if (
            path.is_absolute()
            or has_drive_prefix
            or any(part in {"", ".", ".."} for part in value.split("/"))
        ):
            raise ManifestError(f"{field} must be a safe relative path")
        return value


class PluginManifestAdapter(_ReaderAdapter):
    """Validate E-013 plugin manifests through their owning subsystem."""

    spec = ManifestSpec(
        "ups.plugin",
        ManifestKind.PLUGIN,
        PLUGIN_MANIFEST_NAME,
        (1,),
        current_schema_version=1,
        allow_multiple=True,
    )
    _reader = PluginManifestReader()

    def detect_schema_version(self, path: Path) -> int:
        """Delegate YAML schema-envelope detection to the plugin owner."""

        return self._reader.detect_schema_version(path)

    def _read_schema_version(self, path: Path) -> int:
        return self._reader.read(path).schema_version


class AIProviderManifestAdapter(_ReaderAdapter):
    """Validate E-014 AI-provider manifests through their owning subsystem."""

    spec = ManifestSpec(
        "ups.ai-provider",
        ManifestKind.AI_PROVIDER,
        AI_PROVIDER_MANIFEST_NAME,
        (1,),
        current_schema_version=1,
        allow_multiple=True,
    )
    _reader = ProviderManifestReader()

    def detect_schema_version(self, path: Path) -> int:
        """Delegate YAML schema-envelope detection to the provider owner."""

        return self._reader.detect_schema_version(path)

    def _read_schema_version(self, path: Path) -> int:
        return self._reader.read(path).schema_version


def default_manifest_adapters() -> tuple[ManifestAdapter, ...]:
    """Return all built-in adapters in stable registration order."""

    return (
        AIProviderManifestAdapter(),
        BuildManifestAdapter(),
        DocumentationManifestAdapter(),
        PluginManifestAdapter(),
        ReleaseManifestAdapter(),
        TemplateArtifactManifestAdapter(),
    )
