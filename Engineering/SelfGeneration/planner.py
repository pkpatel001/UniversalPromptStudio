"""Deterministic no-write planning and reporting for E-017.1."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .inventory import derive_self_generation_artifacts
from .models import (
    SelfGenerationDryRunReport,
    SelfGenerationIssue,
    SelfGenerationPlan,
    SelfGenerationRequest,
)
from .preconditions import SelfGenerationPreconditionChecker


class SelfGenerationPlanner:
    """Build allowlisted plans without rendering, importing, or writing."""

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()
        self._checker = SelfGenerationPreconditionChecker()

    def plan(self, request: SelfGenerationRequest) -> SelfGenerationPlan:
        """Derive a stable plan exclusively from the closed artifact inventory."""

        preconditions = self._checker.check(self._project_root)
        artifacts = derive_self_generation_artifacts(request)
        issues: list[SelfGenerationIssue] = []
        if not (self._project_root / "pyproject.toml").is_file():
            issues.append(
                SelfGenerationIssue(
                    "project-root.invalid",
                    "Self-generation requires a project root containing pyproject.toml.",
                    "pyproject.toml",
                )
            )
        for result in preconditions.results:
            for missing in result.missing_paths:
                issues.append(
                    SelfGenerationIssue(
                        f"precondition.{result.precondition.milestone.value.lower()}.missing",
                        (
                            f"{result.precondition.milestone.value} "
                            f"{result.precondition.capability} evidence is unavailable."
                        ),
                        missing.as_posix(),
                    )
                )
        for artifact in artifacts:
            candidate = self._project_root.joinpath(*artifact.relative_path.parts)
            if self._has_symlink_component(artifact.relative_path):
                issues.append(
                    SelfGenerationIssue(
                        "destination.symlink",
                        "An allowlisted destination traverses a symlinked component.",
                        artifact.relative_path.as_posix(),
                    )
                )
            elif candidate.exists():
                issues.append(
                    SelfGenerationIssue(
                        "destination.conflict",
                        "Default no-overwrite planning found an existing destination.",
                        artifact.relative_path.as_posix(),
                    )
                )
        return SelfGenerationPlan(
            request=request,
            artifacts=artifacts,
            preconditions=preconditions,
            issues=tuple(sorted(issues, key=lambda issue: (issue.code, issue.location))),
        )

    def dry_run(self, request: SelfGenerationRequest) -> SelfGenerationDryRunReport:
        """Return deterministic reporting for a plan and perform no writes."""

        plan = self.plan(request)
        state = "ready" if plan.ready else "blocked"
        lines = [
            f"Self-generation dry run: {state}",
            f"Target: {request.target.value}",
            f"Package: {request.package_name}",
            (
                "Preconditions: "
                f"{plan.preconditions.satisfied_count}/{len(plan.preconditions.results)} satisfied"
            ),
            f"Artifacts: {len(plan.artifacts)}",
        ]
        lines.extend(
            "PLAN "
            f"{artifact.artifact_type.value} {artifact.relative_path.as_posix()} "
            f"[{artifact.template_key.value}]"
            for artifact in plan.artifacts
        )
        lines.extend(
            f"BLOCK {issue.code} {issue.location}: {issue.message}" for issue in plan.issues
        )
        lines.append("No files written.")
        return SelfGenerationDryRunReport(plan, tuple(lines))

    def _has_symlink_component(self, relative: PurePosixPath) -> bool:
        current = self._project_root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return True
        return False
