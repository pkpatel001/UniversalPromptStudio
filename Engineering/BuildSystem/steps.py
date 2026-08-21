"""Build-step abstractions and foundational E-010 steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from Engineering.core.validation import ValidationContext, Validator
from Engineering.Standards.project import (
    RequiredDirectoryRule,
    RequiredFileRule,
)

from .models import BuildContext, BuildState, BuildStepResult


class BuildStep(ABC):
    """One deterministic operation in a build plan."""

    @property
    @abstractmethod
    def step_id(self) -> str:
        """Return the stable step identifier."""

    @property
    def dependencies(self) -> tuple[str, ...]:
        """Return IDs that must complete before this step."""

        return ()

    @abstractmethod
    def execute(self, context: BuildContext) -> BuildStepResult:
        """Execute the step and return a structured result."""


class ProjectValidationStep(BuildStep):
    """Run the established E-004 project validation rules."""

    @property
    def step_id(self) -> str:
        return "build.validate-project"

    def execute(self, context: BuildContext) -> BuildStepResult:
        if context.dry_run:
            return BuildStepResult(
                self.step_id, BuildState.SKIPPED, "Project validation planned."
            )
        validator = Validator(
            rules=[
                RequiredDirectoryRule("Engineering", "Engineering Toolkit"),
                RequiredDirectoryRule("Backend", "Backend"),
                RequiredDirectoryRule("Frontend", "Frontend"),
                RequiredDirectoryRule("Docs", "Documentation"),
                RequiredDirectoryRule(
                    "Engineering/config", "Engineering configuration"
                ),
                RequiredFileRule("pyproject.toml", "Project manifest"),
                RequiredFileRule("README.md", "Project readme"),
            ]
        )
        report = validator.validate(
            ValidationContext(project_root=context.project_root)
        )
        state = BuildState.SUCCEEDED if report.passed else BuildState.FAILED
        return BuildStepResult(self.step_id, state, report.summary)


class PythonSyntaxStep(BuildStep):
    """Compile Python source in memory to detect syntax failures."""

    _SOURCE_ROOTS = ("Backend", "Engineering")

    @property
    def step_id(self) -> str:
        return "build.python-syntax"

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ("build.validate-project",)

    def execute(self, context: BuildContext) -> BuildStepResult:
        if context.dry_run:
            return BuildStepResult(
                self.step_id, BuildState.SKIPPED, "Python syntax check planned."
            )
        files = self._source_files(context.project_root)
        failures: list[str] = []
        for path in files:
            try:
                source = path.read_text(encoding="utf-8")
                compile(source, str(path), "exec")
            except (OSError, SyntaxError, UnicodeError) as exc:
                relative = path.relative_to(context.project_root).as_posix()
                failures.append(f"{relative}: {exc}")
        if failures:
            return BuildStepResult(
                self.step_id, BuildState.FAILED, "; ".join(failures)
            )
        return BuildStepResult(
            self.step_id,
            BuildState.SUCCEEDED,
            f"Validated {len(files)} Python source file(s).",
        )

    def _source_files(self, project_root: Path) -> tuple[Path, ...]:
        files = (
            path
            for root_name in self._SOURCE_ROOTS
            for path in (project_root / root_name).rglob("*.py")
            if path.is_file()
        )
        return tuple(sorted(files))
