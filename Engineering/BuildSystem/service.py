"""Application service coordinating E-010 build execution and manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .engine import BuildEngine
from .manifest import BUILD_MANIFEST_NAME, BuildManifest
from .models import BuildContext, BuildPlan, BuildReport


@dataclass(frozen=True, slots=True)
class BuildExecution:
    """Result returned by the build application service."""

    plan: BuildPlan
    report: BuildReport
    manifest: BuildManifest | None = None
    manifest_path: Path | None = None


class BuildService:
    """Plan, execute, and record builds without owning individual steps."""

    def __init__(self, engine: BuildEngine) -> None:
        self._engine = engine

    def run(
        self,
        context: BuildContext,
        targets: tuple[str, ...] | None = None,
    ) -> BuildExecution:
        """Run selected targets and persist only successful real builds."""

        plan = self._engine.plan(targets=targets, dry_run=context.dry_run)
        report = self._engine.execute(plan, context)
        if context.dry_run or not report.success:
            return BuildExecution(plan, report)

        manifest = BuildManifest.from_build(plan, report)
        manifest_path = context.output_root / BUILD_MANIFEST_NAME
        manifest.write(manifest_path)
        return BuildExecution(plan, report, manifest, manifest_path)
