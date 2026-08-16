"""Deterministic artifact manifests for E-009 generation results."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from Engineering.CodeGeneration.models import ArtifactState, GenerationReport
from Engineering.core.filesystem import write_json

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
