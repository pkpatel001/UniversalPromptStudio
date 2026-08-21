"""Immutable domain models for the E-010 build system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BuildState(Enum):
    """Outcome of a build step."""

    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class BuildContext:
    """Filesystem context shared by build steps."""

    project_root: Path
    output_root: Path
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class BuildStepResult:
    """Structured result returned by one build step."""

    step_id: str
    state: BuildState
    message: str = ""
    artifacts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildPlan:
    """Validated, dependency-ordered build plan."""

    step_ids: tuple[str, ...]
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class BuildReport:
    """Aggregate result of executing a build plan."""

    results: tuple[BuildStepResult, ...] = ()
    dry_run: bool = False

    @property
    def success(self) -> bool:
        """Return True when no build step failed."""

        return all(result.state != BuildState.FAILED for result in self.results)

    @property
    def failed_count(self) -> int:
        """Return the number of failed steps."""

        return sum(result.state == BuildState.FAILED for result in self.results)

    @property
    def succeeded_count(self) -> int:
        """Return the number of successful steps."""

        return sum(result.state == BuildState.SUCCEEDED for result in self.results)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped steps."""

        return sum(result.state == BuildState.SKIPPED for result in self.results)

    @property
    def summary(self) -> str:
        """Return a stable human-readable build summary."""

        prefix = "Dry-run " if self.dry_run else ""
        return (
            f"{prefix}Build {'succeeded' if self.success else 'failed'}: "
            f"{self.succeeded_count} succeeded, {self.skipped_count} skipped, "
            f"{self.failed_count} failed."
        )
