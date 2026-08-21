"""Deterministic release manifests for E-011."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Engineering.core.exceptions import EngineeringError, ReleaseError
from Engineering.core.filesystem import read_json, write_json

from .models import PackageArtifact, PackageFormat, ReleaseVersion

RELEASE_MANIFEST_NAME = "release-manifest.json"


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """Portable record of locally created release packages."""

    version: ReleaseVersion
    artifacts: tuple[PackageArtifact, ...]
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable representation."""

        return {
            "schema_version": self.schema_version,
            "release": {
                "version": self.version.value,
                "python_version": self.version.normalized,
            },
            "artifacts": [
                {
                    "relative_path": item.relative_path,
                    "format": item.package_format.value,
                    "size": item.size,
                    "sha256": item.sha256,
                }
                for item in sorted(self.artifacts, key=lambda artifact: artifact.relative_path)
            ],
        }

    def write(self, path: Path) -> None:
        """Write the manifest with canonical Engineering JSON I/O."""

        write_json(path, self.to_dict())

    @classmethod
    def read(cls, path: Path) -> ReleaseManifest:
        """Read and validate a schema-version-one manifest."""

        try:
            data = read_json(path)
            if data.get("schema_version") != 1:
                raise ValueError("unsupported schema version")
            release = data["release"]
            raw_artifacts = data["artifacts"]
            if not isinstance(release, dict) or not isinstance(raw_artifacts, list):
                raise TypeError("release and artifacts have invalid types")
            version = release["version"]
            if not isinstance(version, str):
                raise TypeError("release version must be a string")
            artifacts: list[PackageArtifact] = []
            for raw in raw_artifacts:
                if not isinstance(raw, dict):
                    raise TypeError("artifact entries must be mappings")
                relative_path = raw["relative_path"]
                format_value = raw["format"]
                size = raw["size"]
                sha256 = raw["sha256"]
                if not isinstance(relative_path, str) or not isinstance(format_value, str):
                    raise TypeError("artifact path and format must be strings")
                if not isinstance(size, int) or not isinstance(sha256, str):
                    raise TypeError("artifact size and checksum have invalid types")
                artifacts.append(
                    PackageArtifact(
                        relative_path,
                        PackageFormat(format_value),
                        size,
                        sha256,
                    )
                )
            return cls(ReleaseVersion(version), tuple(artifacts))
        except (AttributeError, EngineeringError, KeyError, TypeError, ValueError) as exc:
            raise ReleaseError(f"Invalid release manifest {path}: {exc}") from exc
