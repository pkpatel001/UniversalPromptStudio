"""Immutable domain models for the E-012 manifest system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ManifestKind(Enum):
    """Manifest families supported by the shared catalog."""

    BUILD = "build"
    DOCUMENTATION = "documentation"
    TEMPLATE_ARTIFACT = "template-artifact"
    RELEASE = "release"


class SchemaCompatibility(Enum):
    """Compatibility of a document with a registered schema contract."""

    CURRENT = "current"
    READABLE = "readable"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ManifestSchemaContract:
    """Readable versions and the version emitted by the current producer."""

    current_version: int
    readable_versions: tuple[int, ...]

    def compatibility(self, version: int) -> SchemaCompatibility:
        """Classify a schema version without modifying its document."""

        if type(version) is not int:
            return SchemaCompatibility.UNSUPPORTED
        if version == self.current_version:
            return SchemaCompatibility.CURRENT
        if version in self.readable_versions:
            return SchemaCompatibility.READABLE
        return SchemaCompatibility.UNSUPPORTED


@dataclass(frozen=True, slots=True)
class ManifestSpec:
    """Stable registration metadata for one manifest family."""

    manifest_id: str
    kind: ManifestKind
    filename: str
    supported_schema_versions: tuple[int, ...]
    current_schema_version: int | None = None
    allow_multiple: bool = False

    @property
    def schema_contract(self) -> ManifestSchemaContract:
        """Return the explicit compatibility contract for this family."""

        current = self.current_schema_version
        if current is None:
            current = max(self.supported_schema_versions, default=0)
        return ManifestSchemaContract(current, self.supported_schema_versions)


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    """Portable inventory record for one validated manifest."""

    manifest_id: str
    kind: ManifestKind
    relative_path: str
    schema_version: int
    sha256: str
    compatibility: SchemaCompatibility = SchemaCompatibility.CURRENT


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


@dataclass(frozen=True, slots=True)
class ManifestValidationReport:
    """Combined structural, schema, cardinality, and relationship result."""

    records: tuple[ManifestRecord, ...] = ()
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return True when the complete manifest set is coherent."""

        return not self.issues

    @property
    def summary(self) -> str:
        """Return a stable human-readable validation summary."""

        state = "succeeded" if self.passed else "failed"
        return (
            f"Manifest validation {state}: {len(self.records)} valid, "
            f"{len(self.issues)} issues."
        )


@dataclass(frozen=True, slots=True)
class ManifestMigrationStep:
    """One registered, non-mutating schema transition."""

    manifest_id: str
    source_version: int
    target_version: int
    migration_id: str
    description: str


@dataclass(frozen=True, slots=True)
class ManifestMigrationPlan:
    """Ordered migration steps for one discovered manifest."""

    manifest_id: str
    relative_path: str
    source_version: int
    target_version: int
    steps: tuple[ManifestMigrationStep, ...]


@dataclass(frozen=True, slots=True)
class ManifestMigrationReport:
    """Aggregate result of read-only schema-migration planning."""

    plans: tuple[ManifestMigrationPlan, ...] = ()
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return True when every readable legacy manifest has a plan."""

        return not self.issues

    @property
    def summary(self) -> str:
        """Return a stable human-readable planning summary."""

        state = "succeeded" if self.passed else "failed"
        plan_count = len(self.plans)
        step_count = sum(len(plan.steps) for plan in self.plans)
        plan_label = "plan" if plan_count == 1 else "plans"
        step_label = "step" if step_count == 1 else "steps"
        issue_label = "issue" if len(self.issues) == 1 else "issues"
        return (
            f"Manifest migration planning {state}: {plan_count} {plan_label}, "
            f"{step_count} {step_label}, {len(self.issues)} {issue_label}."
        )
