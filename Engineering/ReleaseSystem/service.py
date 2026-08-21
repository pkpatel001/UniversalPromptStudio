"""Application service coordinating verified local package creation."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from Engineering.BuildSystem import (
    BuildContext,
    BuildProfile,
    BuildService,
    default_build_engine,
    profile_targets,
)
from Engineering.core.exceptions import ReleaseError
from Engineering.core.filesystem import ensure_directory, write_text

from .builder import CompositePackageBuilder
from .inspection import PackageInspector
from .manifest import RELEASE_MANIFEST_NAME, ReleaseManifest
from .models import (
    PackageArtifact,
    PackageFormat,
    PackageResult,
    PackageState,
    PackagingPlan,
    ReleaseContext,
    ReleasePreconditionReport,
    ReleaseReport,
)
from .planner import ReleasePlanner
from .preconditions import ReleasePreconditionChecker


@dataclass(frozen=True, slots=True)
class ReleaseExecution:
    """Complete result from release planning or execution."""

    plan: PackagingPlan
    preconditions: ReleasePreconditionReport
    report: ReleaseReport | None = None
    manifest: ReleaseManifest | None = None
    manifest_path: Path | None = None
    checksum_path: Path | None = None


class PreconditionChecker(Protocol):
    """Release-precondition port used by the application service."""

    def check(
        self,
        context: ReleaseContext,
        formats: tuple[PackageFormat, ...],
    ) -> ReleasePreconditionReport:
        """Evaluate release readiness."""


class PackageBuilder(Protocol):
    """Local package-builder port."""

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Create the requested packages."""


class ArtifactInspector(Protocol):
    """Package-inspection port."""

    def inspect(self, path: Path, output_root: Path) -> PackageArtifact:
        """Inspect one package artifact."""


class BuildGate(Protocol):
    """E-010 full-build gate consumed by release execution."""

    def verify(self, context: ReleaseContext) -> tuple[bool, str]:
        """Run and report the required build."""


class DefaultBuildGate:
    """Run E-010's full profile as the release build gate."""

    def verify(self, context: ReleaseContext) -> tuple[bool, str]:
        """Execute the established E-010 full build."""

        execution = BuildService(default_build_engine()).run(
            BuildContext(context.project_root, context.project_root / "build"),
            targets=profile_targets(BuildProfile.FULL),
        )
        return execution.report.success, execution.report.summary


class ReleaseService:
    """Plan, verify, package, inspect, and record local release artifacts."""

    def __init__(
        self,
        planner: ReleasePlanner | None = None,
        preconditions: PreconditionChecker | None = None,
        build_gate: BuildGate | None = None,
        builder: PackageBuilder | None = None,
        inspector: ArtifactInspector | None = None,
    ) -> None:
        self._planner = planner or ReleasePlanner()
        self._preconditions = preconditions or ReleasePreconditionChecker()
        self._build_gate = build_gate or DefaultBuildGate()
        self._builder = builder or CompositePackageBuilder()
        self._inspector = inspector or PackageInspector()

    def plan(
        self,
        context: ReleaseContext,
        formats: tuple[PackageFormat, ...],
    ) -> ReleaseExecution:
        """Create a plan and evaluate its preconditions without writing."""

        plan = self._planner.plan(context, formats)
        return ReleaseExecution(plan, self._preconditions.check(context, formats))

    def run(
        self,
        context: ReleaseContext,
        formats: tuple[PackageFormat, ...],
    ) -> ReleaseExecution:
        """Execute a verified local packaging plan."""

        execution = self.plan(context, formats)
        plan = execution.plan
        if not execution.preconditions.passed:
            results = tuple(
                PackageResult(
                    spec.package_format,
                    PackageState.FAILED,
                    "Release preconditions failed.",
                )
                for spec in plan.specs
            )
            return ReleaseExecution(
                plan,
                execution.preconditions,
                ReleaseReport(results, dry_run=context.dry_run),
            )
        if context.dry_run:
            results = tuple(
                PackageResult(
                    spec.package_format,
                    PackageState.SKIPPED,
                    "Package creation planned.",
                )
                for spec in plan.specs
            )
            return ReleaseExecution(
                plan,
                execution.preconditions,
                ReleaseReport(results, dry_run=True),
            )

        build_passed, build_message = self._build_gate.verify(context)
        if not build_passed:
            return self._failed(
                execution, f"Required E-010 full build failed: {build_message}"
            )

        ensure_directory(context.output_root)
        formats_to_build = tuple(spec.package_format for spec in plan.specs)
        try:
            with tempfile.TemporaryDirectory(
                prefix=".staging-", dir=context.output_root
            ) as temporary:
                staged = self._builder.build(
                    context.project_root, Path(temporary), formats_to_build
                )
                targets = tuple(
                    self._target_path(context.output_root, item) for item in staged
                )
                for target in targets:
                    ensure_directory(target.parent)
                for target in targets:
                    if target.exists() and not context.overwrite:
                        raise ReleaseError(f"Release artifact already exists: {target.name}")
                artifacts: list[PackageArtifact] = []
                for source, target in zip(staged, targets, strict=True):
                    if target.exists():
                        target.unlink()
                    shutil.move(str(source), target)
                    artifacts.append(self._inspector.inspect(target, context.output_root))
        except (OSError, ReleaseError) as exc:
            return self._failed(execution, str(exc))

        manifest = ReleaseManifest(
            context.version,
            tuple(sorted(artifacts, key=lambda artifact: artifact.relative_path)),
        )
        manifest_path = context.output_root / RELEASE_MANIFEST_NAME
        checksum_path = context.output_root / "checksums" / "SHA256SUMS"
        manifest.write(manifest_path)
        checksum_text = "".join(
            f"{item.sha256}  {item.relative_path}\n"
            for item in sorted(artifacts, key=lambda artifact: artifact.relative_path)
        )
        write_text(checksum_path, checksum_text)
        results = tuple(
            PackageResult(
                artifact.package_format,
                PackageState.SUCCEEDED,
                f"Created {artifact.relative_path}.",
                artifact,
            )
            for artifact in sorted(artifacts, key=lambda item: item.package_format.value)
        )
        return ReleaseExecution(
            plan,
            execution.preconditions,
            ReleaseReport(results),
            manifest,
            manifest_path,
            checksum_path,
        )

    @staticmethod
    def _failed(execution: ReleaseExecution, message: str) -> ReleaseExecution:
        results = tuple(
            PackageResult(spec.package_format, PackageState.FAILED, message)
            for spec in execution.plan.specs
        )
        return ReleaseExecution(
            execution.plan,
            execution.preconditions,
            ReleaseReport(results),
        )

    @staticmethod
    def _target_path(output_root: Path, artifact: Path) -> Path:
        ecosystem = "frontend" if artifact.suffix == ".zip" else "python"
        return output_root / "packages" / ecosystem / artifact.name
