"""Read-only E-007 through E-016 readiness checks for self-generation."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .models import (
    SelfGenerationPrecondition,
    SelfGenerationPreconditionReport,
    SelfGenerationPreconditionResult,
    ToolkitMilestone,
)

DEFAULT_SELF_GENERATION_PRECONDITIONS: tuple[SelfGenerationPrecondition, ...] = (
    SelfGenerationPrecondition(
        ToolkitMilestone.E_007,
        "documentation generation",
        (PurePosixPath("Engineering/Documentation/generator.py"),),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_008,
        "safe code-generation planning and execution",
        (PurePosixPath("Engineering/CodeGeneration/engine.py"),),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_009,
        "template definitions and artifact manifests",
        (
            PurePosixPath("Engineering/Templates/executor.py"),
            PurePosixPath("Engineering/Templates/Definitions/project.basic.template.yaml"),
        ),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_010,
        "build planning and evidence",
        (PurePosixPath("Engineering/BuildSystem/engine.py"),),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_011,
        "release planning and verification",
        (PurePosixPath("Engineering/ReleaseSystem/service.py"),),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_012,
        "shared manifest validation",
        (PurePosixPath("Engineering/ManifestSystem/service.py"),),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_013,
        "controlled plugin scaffolding",
        (
            PurePosixPath("Engineering/PluginSystem/scaffold.py"),
            PurePosixPath("Engineering/Templates/Definitions/plugin.python-basic.template.yaml"),
        ),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_014,
        "controlled provider scaffolding",
        (
            PurePosixPath("Engineering/ProviderSystem/scaffold.py"),
            PurePosixPath("Engineering/Templates/Definitions/provider.python-basic.template.yaml"),
        ),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_015,
        "controlled theme scaffolding",
        (
            PurePosixPath("Engineering/ThemeSystem/scaffold.py"),
            PurePosixPath(
                "Engineering/Templates/Definitions/theme.declarative-basic.template.yaml"
            ),
        ),
    ),
    SelfGenerationPrecondition(
        ToolkitMilestone.E_016,
        "controlled workflow scaffolding and execution",
        (
            PurePosixPath("Engineering/WorkflowSystem/scaffold.py"),
            PurePosixPath("Engineering/WorkflowSystem/execution.py"),
            PurePosixPath(
                "Engineering/Templates/Definitions/workflow.declarative-basic.template.yaml"
            ),
        ),
    ),
)


class SelfGenerationPreconditionChecker:
    """Confirm exact regular-file evidence without importing or executing it."""

    def __init__(
        self,
        preconditions: tuple[
            SelfGenerationPrecondition, ...
        ] = DEFAULT_SELF_GENERATION_PRECONDITIONS,
    ) -> None:
        self._preconditions = preconditions

    def check(self, project_root: Path) -> SelfGenerationPreconditionReport:
        """Return stable milestone results; never create or modify a path."""

        root = project_root.resolve()
        results: list[SelfGenerationPreconditionResult] = []
        for precondition in self._preconditions:
            missing = tuple(
                relative
                for relative in precondition.evidence_paths
                if not self._is_regular_beneath(root, relative)
            )
            results.append(SelfGenerationPreconditionResult(precondition, missing))
        return SelfGenerationPreconditionReport(tuple(results))

    @staticmethod
    def _is_regular_beneath(root: Path, relative: PurePosixPath) -> bool:
        candidate = root.joinpath(*relative.parts)
        current = root
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                return False
        try:
            candidate.resolve().relative_to(root)
        except (OSError, ValueError):
            return False
        return candidate.is_file()
