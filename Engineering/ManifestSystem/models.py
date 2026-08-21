"""Immutable domain models for the E-012 manifest system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ManifestKind(Enum):
    """Manifest families supported by the shared catalog."""

    BUILD = "build"
    TEMPLATE_ARTIFACT = "template-artifact"
    RELEASE = "release"


@dataclass(frozen=True, slots=True)
class ManifestSpec:
    """Stable registration metadata for one manifest family."""

    manifest_id: str
    kind: ManifestKind
    filename: str
    supported_schema_versions: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    """Portable inventory record for one validated manifest."""

    manifest_id: str
    kind: ManifestKind
    relative_path: str
    schema_version: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ManifestIssue:
    """A deterministic manifest discovery or validation problem."""

    relative_path: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ManifestInspectionReport:
    """Aggregate result of a read-only manifest inspection."""

    records: tuple[ManifestRecord, ...] = ()
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return True when every discovered manifest is valid."""

        return not self.issues

    @property
    def summary(self) -> str:
        """Return a stable human-readable inspection summary."""

        state = "succeeded" if self.passed else "failed"
        return (
            f"Manifest inspection {state}: {len(self.records)} valid, "
            f"{len(self.issues)} invalid."
        )
