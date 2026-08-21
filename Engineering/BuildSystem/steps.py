"""Build-step abstractions and foundational E-010 steps."""

from __future__ import annotations

import json
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


class BackendInventoryStep(BuildStep):
    """Verify and inventory backend package sources."""

    @property
    def step_id(self) -> str:
        return "build.backend-inventory"

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ("build.python-syntax",)

    def execute(self, context: BuildContext) -> BuildStepResult:
        if context.dry_run:
            return BuildStepResult(
                self.step_id, BuildState.SKIPPED, "Backend inventory planned."
            )
        root = context.project_root / "Backend"
        if not (root / "__init__.py").is_file():
            return BuildStepResult(
                self.step_id,
                BuildState.FAILED,
                "Backend package is missing Backend/__init__.py.",
            )
        files = tuple(
            path.relative_to(context.project_root).as_posix()
            for path in sorted(root.rglob("*.py"))
            if path.is_file()
        )
        if not files:
            return BuildStepResult(
                self.step_id, BuildState.FAILED, "Backend contains no Python sources."
            )
        return BuildStepResult(
            self.step_id,
            BuildState.SUCCEEDED,
            f"Inventoried {len(files)} backend source file(s).",
            artifacts=files,
        )


class FrontendReadinessStep(BuildStep):
    """Validate Vite and Tauri frontend build configuration."""

    _REQUIRED_SCRIPTS = ("build", "dev", "tauri")
    _REQUIRED_SOURCES = ("index.html", "src/main.js", "src/styles.css")

    @property
    def step_id(self) -> str:
        return "build.frontend-readiness"

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ("build.validate-project",)

    def execute(self, context: BuildContext) -> BuildStepResult:
        if context.dry_run:
            return BuildStepResult(
                self.step_id, BuildState.SKIPPED, "Frontend readiness check planned."
            )
        frontend = context.project_root / "Frontend"
        problems: list[str] = []
        package = self._read_mapping(frontend / "package.json", problems)
        scripts = package.get("scripts") if package is not None else None
        if not isinstance(scripts, dict):
            problems.append("Frontend/package.json has no scripts mapping.")
        else:
            for script in self._REQUIRED_SCRIPTS:
                if not isinstance(scripts.get(script), str):
                    problems.append(f"Frontend npm script is missing: {script}.")

        tauri = self._read_mapping(
            frontend / "src-tauri" / "tauri.conf.json", problems
        )
        build = tauri.get("build") if tauri is not None else None
        if not isinstance(build, dict):
            problems.append("Tauri configuration has no build mapping.")
        else:
            if build.get("beforeBuildCommand") != "npm run build":
                problems.append("Tauri beforeBuildCommand must run the frontend build.")
            if build.get("frontendDist") != "../dist":
                problems.append("Tauri frontendDist must target ../dist.")

        for relative in self._REQUIRED_SOURCES:
            if not (frontend / relative).is_file():
                problems.append(f"Frontend source is missing: {relative}.")
        if problems:
            return BuildStepResult(
                self.step_id, BuildState.FAILED, "; ".join(problems)
            )

        artifacts = tuple(
            f"Frontend/{relative}"
            for relative in (
                "package.json",
                "src-tauri/tauri.conf.json",
                *self._REQUIRED_SOURCES,
            )
        )
        return BuildStepResult(
            self.step_id,
            BuildState.SUCCEEDED,
            "Frontend Vite/Tauri build configuration is ready.",
            artifacts=artifacts,
        )

    @staticmethod
    def _read_mapping(path: Path, problems: list[str]) -> dict[str, object] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            problems.append(f"Cannot read {path.name}: {exc}")
            return None
        if not isinstance(data, dict):
            problems.append(f"{path.name} root must be a mapping.")
            return None
        return data
