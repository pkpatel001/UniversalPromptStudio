"""Immutable domain models for E-011 release packaging."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from packaging.version import InvalidVersion, Version

from Engineering.core.exceptions import ReleaseError


class PackageFormat(Enum):
    """Locally supported package formats."""

    SDIST = "sdist"
    WHEEL = "wheel"


class PackageState(Enum):
    """Outcome of one package operation."""

    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ReleaseVersion:
    """Validated release version and its normalized Python representation."""

    value: str

    def __post_init__(self) -> None:
        try:
            Version(self.value)
        except InvalidVersion as exc:
            raise ReleaseError(f"Invalid release version: {self.value!r}") from exc

    @property
    def normalized(self) -> str:
        """Return the PEP 440-normalized version."""

        return str(Version(self.value))


@dataclass(frozen=True, slots=True)
class PackageSpec:
    """One requested local package format."""

    package_format: PackageFormat


@dataclass(frozen=True, slots=True)
class ReleaseContext:
    """Filesystem and safety context for one release operation."""

    project_root: Path
    output_root: Path
    version: ReleaseVersion
    dry_run: bool = False
    overwrite: bool = False


@dataclass(frozen=True, slots=True)
class PackagingPlan:
    """Deterministic plan for local package creation."""

    version: ReleaseVersion
    specs: tuple[PackageSpec, ...]
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class ReleasePreconditionIssue:
    """One failed release precondition."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ReleasePreconditionReport:
    """Stable collection of release-readiness problems."""

    issues: tuple[ReleasePreconditionIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return whether every precondition passed."""

        return not self.issues


@dataclass(frozen=True, slots=True)
class PackageArtifact:
    """Inspected, checksummed release artifact."""

    relative_path: str
    package_format: PackageFormat
    size: int
    sha256: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PackageResult:
    """Structured result for one requested package format."""

    package_format: PackageFormat
    state: PackageState
    message: str = ""
    artifact: PackageArtifact | None = None


@dataclass(frozen=True, slots=True)
class ReleaseReport:
    """Aggregate local packaging result."""

    results: tuple[PackageResult, ...] = ()
    dry_run: bool = False

    @property
    def success(self) -> bool:
        """Return whether no package operation failed."""

        return all(result.state != PackageState.FAILED for result in self.results)

    @property
    def summary(self) -> str:
        """Return a stable human-readable summary."""

        succeeded = sum(r.state == PackageState.SUCCEEDED for r in self.results)
        skipped = sum(r.state == PackageState.SKIPPED for r in self.results)
        failed = sum(r.state == PackageState.FAILED for r in self.results)
        prefix = "Dry-run " if self.dry_run else ""
        state = "succeeded" if self.success else "failed"
        return (
            f"{prefix}Release {state}: {succeeded} succeeded, "
            f"{skipped} skipped, {failed} failed."
        )
