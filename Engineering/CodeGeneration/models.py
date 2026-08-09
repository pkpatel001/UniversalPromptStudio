"""
===============================================================================
Universal Prompt Studio
Engineering Toolkit

Code Generation Domain Model

This module defines the strongly typed, immutable domain model for the
Code Generation framework. Every public type is a frozen dataclass or
enum to guarantee immutability and testability.

The model separates:
* What is requested    — GenerationRequest
* What context exists  — GenerationContext
* What will be done    — GenerationPlan
* What was produced    — GeneratedArtifact
* What happened        — ArtifactResult / GenerationReport

Public API
----------
from Engineering.CodeGeneration.models import (
    ArtifactState,
    ArtifactSpec,
    ArtifactResult,
    GenerationContext,
    GenerationPlan,
    GenerationReport,
    GenerationRequest,
    GeneratedArtifact,
    GeneratorInfo,
    OverwritePolicy,
    ProjectGenerationInfo,
)

===============================================================================
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Engineering.core.config import Configuration

__all__ = [
    "ArtifactState",
    "OverwritePolicy",
    "ProjectGenerationInfo",
    "GeneratorInfo",
    "ArtifactInfo",
    "GenerationContext",
    "ArtifactSpec",
    "GenerationPlan",
    "GeneratedArtifact",
    "ArtifactResult",
    "GenerationRequest",
    "GenerationReport",
    "project_context_from_config",
]


# ---------------------------------------------------------------------------
# Artifact State
# ---------------------------------------------------------------------------


class ArtifactState(Enum):
    """
    Outcome of generating a single artifact.

    Attributes
    ----------
    CREATED
        Destination was absent; file was written.
    UNCHANGED
        Destination exists with identical content; no write.
    OVERWRITTEN
        Destination exists with different content; file was written
        (only when OverwritePolicy.ALLOWED).
    SKIPPED
        Artifact was deliberately skipped by the planner.
    CONFLICT
        Destination exists with different content and overwrite
        is not permitted.
    FAILED
        An error prevented the artifact from being produced.
    """

    CREATED = "created"
    UNCHANGED = "unchanged"
    OVERWRITTEN = "overwritten"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Overwrite Policy
# ---------------------------------------------------------------------------


class OverwritePolicy(Enum):
    """
    Controls what happens when an artifact would overwrite a file.

    NEVER (default)
        Report CONFLICT; do not write.
    ALLOWED
        Overwrite existing files and report OVERWRITTEN.
    """

    NEVER = "never"
    ALLOWED = "allowed"


# ---------------------------------------------------------------------------
# Generation Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProjectGenerationInfo:
    """
    Project metadata used in template rendering.

    Population source: Engineering Toolkit Configuration.
    """

    name: str
    short_name: str
    version: str
    company: str
    license: str


@dataclass(frozen=True, slots=True)
class GeneratorInfo:
    """
    Metadata identifying the generator producing the request.
    """

    generator_id: str
    name: str = ""
    version: str = ""


@dataclass(frozen=True, slots=True)
class ArtifactInfo:
    """
    Metadata about the specific artifact being generated.
    """

    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class GenerationContext:
    """
    Immutable context provided to templates during rendering.

    Provides typed access to project metadata, generator metadata,
    and template-specific values without relying on raw dictionaries.

    Jinja2 attribute access on dataclasses resolves fields via
    attribute lookup, and ``values`` supports item access for
    template-specific data.
    """

    project: ProjectGenerationInfo
    generator: GeneratorInfo
    artifact: ArtifactInfo
    values: Mapping[str, object] = field(default_factory=dict)


def project_context_from_config(config: Configuration) -> ProjectGenerationInfo:
    """
    Build a ProjectGenerationInfo from the Engineering Toolkit Configuration.

    Parameters
    ----------
    config
        Loaded Engineering Toolkit configuration.

    Returns
    -------
    ProjectGenerationInfo
    """

    return ProjectGenerationInfo(
        name=config.project.name,
        short_name=config.project.short_name,
        version=config.project.version,
        company=config.project.company,
        license=config.project.license,
    )


# ---------------------------------------------------------------------------
# Artifact Specification (in request)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """
    Declares a single artifact to be generated within a request.

    Attributes
    ----------
    relative_path
        Path relative to the generation destination directory.
    template_id
        Identifier resolving to a template in the template repository.
    artifact_type
        Category string (e.g. ``"source"``, ``"manifest"``, ``"config"``).
    name
        Human-readable artifact name for context.
    description
        Optional artifact description for context.
    values
        Artifact-specific template variables merged into the context.
    """

    relative_path: str
    template_id: str
    artifact_type: str = "source"
    name: str = ""
    description: str = ""
    values: Mapping[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Generation Plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerationPlan:
    """
    Validated plan describing artifacts to be produced.

    The plan is constructed by a planner and consumed by the engine.
    It does not contain rendered content — that is the engine's
    responsibility.

    Attributes
    ----------
    generator_id
        Identifier of the generator that produced this plan.
    destination_root
        Absolute path where artifacts will be written.
    context
        Base generation context carrying project and generator metadata.
    overwrite
        Overwrite policy applied during execution.
    artifacts
        Ordered artifact specifications.
    issues
        Validation issues discovered during planning (reuses
        ``ValidationIssue`` from ``core.validation``).
    dry_run
        Whether this plan is for dry-run execution.
    """

    generator_id: str
    destination_root: Path
    context: GenerationContext | None = None
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    artifacts: tuple[ArtifactSpec, ...] = ()
    issues: tuple[object, ...] = ()
    dry_run: bool = False

    @property
    def is_valid(self) -> bool:
        """
        Return True if the plan has no validation issues with ERROR
        or CRITICAL severity.
        """

        from Engineering.core.validation import ValidationSeverity

        for issue in self.issues:
            if isinstance(issue, object) and hasattr(issue, "severity"):
                if issue.severity in (ValidationSeverity.ERROR, ValidationSeverity.CRITICAL):
                    return False
        return True


# ---------------------------------------------------------------------------
# Generated Artifact (rendered, pre-write)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    """
    A fully rendered artifact ready for filesystem validation and writing.
    """

    relative_path: str
    content: str
    artifact_type: str
    source_template: str
    metadata: Mapping[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Artifact Result (post-write)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactResult:
    """
    Outcome of processing a single artifact through the engine.
    """

    state: ArtifactState
    relative_path: str
    artifact_type: str = ""
    source_template: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Generation Request
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """
    A caller's request to produce artifacts.

    Attributes
    ----------
    generator_id
        Identifier of the generator handling this request.
    destination
        Relative directory (under project root) for output.
    context
        Template rendering context.
    artifacts
        Artifacts to produce.
    overwrite
        Policy for handling existing files.
    dry_run
        If True, compute the plan and report without writing.
    """

    generator_id: str
    destination: str
    context: GenerationContext
    artifacts: tuple[ArtifactSpec, ...] = ()
    overwrite: OverwritePolicy = OverwritePolicy.NEVER
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Generation Report
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerationReport:
    """
    Aggregated results from a generation run.

    Provides structured access to per-artifact outcomes and
    computed summary statistics without parsing console output.
    """

    results: tuple[ArtifactResult, ...] = ()
    dry_run: bool = False

    @property
    def generated_count(self) -> int:
        """Count of artifacts created (CREATED + OVERWRITTEN)."""

        return sum(
            1
            for r in self.results
            if r.state in (ArtifactState.CREATED, ArtifactState.OVERWRITTEN)
        )

    @property
    def unchanged_count(self) -> int:
        """Count of artifacts left unchanged."""

        return sum(1 for r in self.results if r.state == ArtifactState.UNCHANGED)

    @property
    def overwritten_count(self) -> int:
        """Count of artifacts overwritten."""

        return sum(1 for r in self.results if r.state == ArtifactState.OVERWRITTEN)

    @property
    def skipped_count(self) -> int:
        """Count of artifacts skipped by planner."""

        return sum(1 for r in self.results if r.state == ArtifactState.SKIPPED)

    @property
    def conflict_count(self) -> int:
        """Count of artifacts in conflict with existing files."""

        return sum(1 for r in self.results if r.state == ArtifactState.CONFLICT)

    @property
    def failed_count(self) -> int:
        """Count of artifacts that failed to generate."""

        return sum(1 for r in self.results if r.state == ArtifactState.FAILED)

    @property
    def success(self) -> bool:
        """True if no artifacts failed or are in conflict."""

        return self.failed_count == 0 and self.conflict_count == 0

    @property
    def summary(self) -> str:
        """Human-readable summary of the generation report."""

        total = len(self.results)
        parts: list[str] = []

        created = self.generated_count
        if created:
            parts.append(f"{created} created")
        if self.unchanged_count:
            parts.append(f"{self.unchanged_count} unchanged")
        if self.overwritten_count:
            parts.append(f"{self.overwritten_count} overwritten")
        if self.skipped_count:
            parts.append(f"{self.skipped_count} skipped")
        if self.conflict_count:
            parts.append(f"{self.conflict_count} conflict(s)")
        if self.failed_count:
            parts.append(f"{self.failed_count} failed")

        prefix = "Dry-run " if self.dry_run else ""
        if not parts:
            return f"{prefix}Generation completed: {total} artifact(s), no changes."

        return f"{prefix}Generation completed: {', '.join(parts)}."
