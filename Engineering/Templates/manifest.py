"""Deterministic artifact manifests for E-009 generation results."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from Engineering.CodeGeneration.models import ArtifactState, GenerationReport
from Engineering.core.exceptions import TemplateError
from Engineering.core.filesystem import read_json, write_json

from .models import TemplateDefinition


@dataclass(frozen=True, slots=True)
class ArtifactManifestEntry:
    """Manifest record for one E-008 artifact result."""

    relative_path: str
    artifact_type: str
    source_template: str
    state: str
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Stable record of artifacts produced from a template definition."""

    template_id: str
    template_version: str
    artifacts: tuple[ArtifactManifestEntry, ...]
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "schema_version": self.schema_version,
            "template": {
                "id": self.template_id,
                "version": self.template_version,
            },
            "artifacts": [asdict(entry) for entry in self.artifacts],
        }

    def write(self, path: Path) -> None:
        """Write the manifest using canonical Engineering JSON I/O."""

        write_json(path, self.to_dict())

    @classmethod
    def read(cls, path: Path) -> ArtifactManifest:
        """Load and validate a manifest from JSON."""

        try:
            data = read_json(path)
            template = data["template"]
            artifacts = data["artifacts"]
            if not isinstance(template, dict) or not isinstance(artifacts, list):
                raise TypeError("template and artifacts have invalid types")
            entries = tuple(
                ArtifactManifestEntry(
                    relative_path=_required_string(item, "relative_path"),
                    artifact_type=_required_string(item, "artifact_type"),
                    source_template=_required_string(item, "source_template"),
                    state=_required_string(item, "state"),
                    sha256=_required_string(item, "sha256"),
                )
                for item in artifacts
                if isinstance(item, dict)
            )
            if len(entries) != len(artifacts):
                raise TypeError("artifact entries must be mappings")
            schema_version = data["schema_version"]
            if schema_version != 1:
                raise ValueError(f"Unsupported manifest schema: {schema_version!r}")
            return cls(
                template_id=_required_string(template, "id"),
                template_version=_required_string(template, "version"),
                artifacts=entries,
                schema_version=1,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TemplateError(f"Invalid artifact manifest {path}: {exc}") from exc

    def verify(self, destination_root: Path) -> ManifestVerificationReport:
        """Verify every recorded artifact against its content hash."""

        issues: list[ManifestVerificationIssue] = []
        for entry in self.artifacts:
            path = destination_root / entry.relative_path
            if not path.is_file():
                issues.append(
                    ManifestVerificationIssue(entry.relative_path, "Artifact is missing.")
                )
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if not entry.sha256 or actual != entry.sha256:
                issues.append(
                    ManifestVerificationIssue(
                        entry.relative_path, "Artifact content hash does not match."
                    )
                )
        return ManifestVerificationReport(tuple(issues))


@dataclass(frozen=True, slots=True)
class ManifestVerificationIssue:
    """An integrity problem found while verifying an artifact manifest."""

    relative_path: str
    message: str


@dataclass(frozen=True, slots=True)
class ManifestVerificationReport:
    """Deterministic result of artifact manifest verification."""

    issues: tuple[ManifestVerificationIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return True when every artifact matches its manifest."""

        return not self.issues


class ArtifactManifestBuilder:
    """Build manifests from completed E-008 generation reports."""

    def build(
        self,
        definition: TemplateDefinition,
        report: GenerationReport,
        destination_root: Path,
    ) -> ArtifactManifest:
        """Create a deterministic manifest without modifying artifacts."""

        entries = tuple(
            ArtifactManifestEntry(
                relative_path=result.relative_path,
                artifact_type=result.artifact_type,
                source_template=result.source_template,
                state=result.state.value,
                sha256=self._digest(destination_root / result.relative_path)
                if result.state
                in (
                    ArtifactState.CREATED,
                    ArtifactState.OVERWRITTEN,
                    ArtifactState.UNCHANGED,
                )
                else "",
            )
            for result in sorted(report.results, key=lambda item: item.relative_path)
        )
        return ArtifactManifest(
            template_id=definition.template_id,
            template_version=definition.version,
            artifacts=entries,
        )

    @staticmethod
    def _digest(path: Path) -> str:
        if not path.is_file():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()


def _required_string(data: dict[str, object], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"{key!r} must be a string")
    return value
