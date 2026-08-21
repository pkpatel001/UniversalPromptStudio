"""E-010 build-system domain and CLI tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from Engineering.BuildSystem import (
    BuildContext,
    BuildEngine,
    BuildService,
    BuildState,
    BuildStep,
    BuildStepResult,
    ProjectValidationStep,
    PythonSyntaxStep,
)
from Engineering.core.exceptions import BuildError


class FakeStep(BuildStep):
    def __init__(
        self,
        step_id: str,
        *,
        dependencies: tuple[str, ...] = (),
        state: BuildState = BuildState.SUCCEEDED,
        raises: bool = False,
    ) -> None:
        self._step_id = step_id
        self._dependencies = dependencies
        self._state = state
        self._raises = raises

    @property
    def step_id(self) -> str:
        return self._step_id

    @property
    def dependencies(self) -> tuple[str, ...]:
        return self._dependencies

    def execute(self, context: BuildContext) -> BuildStepResult:
        if self._raises:
            raise RuntimeError("step exploded")
        return BuildStepResult(self.step_id, self._state, str(context.dry_run))


def _context(tmp_path: Path, dry_run: bool = False) -> BuildContext:
    return BuildContext(tmp_path, tmp_path / "build", dry_run=dry_run)


class TestBuildPlanning:
    def test_orders_dependencies_before_targets(self) -> None:
        engine = BuildEngine(
            [FakeStep("compile", dependencies=("validate",)), FakeStep("validate")]
        )

        plan = engine.plan(targets=("compile",))

        assert plan.step_ids == ("validate", "compile")

    def test_plan_is_deterministic_and_deduplicated(self) -> None:
        engine = BuildEngine(
            [
                FakeStep("validate"),
                FakeStep("compile", dependencies=("validate",)),
                FakeStep("docs", dependencies=("validate",)),
            ]
        )

        assert engine.plan().step_ids == ("validate", "compile", "docs")
        assert engine.plan(targets=("compile", "docs")).step_ids == (
            "validate",
            "compile",
            "docs",
        )

    def test_rejects_duplicate_unknown_and_cyclic_steps(self) -> None:
        with pytest.raises(BuildError, match="unique"):
            BuildEngine([FakeStep("same"), FakeStep("same")])
        with pytest.raises(BuildError, match="Unknown"):
            BuildEngine([FakeStep("one")]).plan(targets=("missing",))
        with pytest.raises(BuildError, match="Cyclic"):
            BuildEngine(
                [
                    FakeStep("one", dependencies=("two",)),
                    FakeStep("two", dependencies=("one",)),
                ]
            ).plan()


class TestBuildExecution:
    def test_success_report(self, tmp_path: Path) -> None:
        engine = BuildEngine([FakeStep("one"), FakeStep("two")])

        report = engine.execute(engine.plan(), _context(tmp_path))

        assert report.success
        assert report.succeeded_count == 2
        assert report.summary == "Build succeeded: 2 succeeded, 0 skipped, 0 failed."

    def test_failure_is_fail_fast(self, tmp_path: Path) -> None:
        engine = BuildEngine(
            [
                FakeStep("fail", state=BuildState.FAILED),
                FakeStep("later"),
            ]
        )

        report = engine.execute(engine.plan(), _context(tmp_path))

        assert report.success is False
        assert report.failed_count == 1
        assert report.results[1].state == BuildState.SKIPPED

    def test_unexpected_exception_becomes_failure(self, tmp_path: Path) -> None:
        engine = BuildEngine([FakeStep("explode", raises=True)])

        report = engine.execute(engine.plan(), _context(tmp_path))

        assert report.success is False
        assert report.results[0].message == "step exploded"

    def test_dry_run_is_preserved(self, tmp_path: Path) -> None:
        engine = BuildEngine([FakeStep("one")])
        plan = engine.plan(dry_run=True)

        report = engine.execute(plan, _context(tmp_path, dry_run=True))

        assert report.dry_run
        assert report.summary.startswith("Dry-run Build succeeded")


class TestBuildService:
    def test_success_writes_deterministic_manifest(self, tmp_path: Path) -> None:
        service = BuildService(BuildEngine([FakeStep("one"), FakeStep("two")]))
        context = _context(tmp_path)

        execution = service.run(context)

        assert execution.report.success
        assert execution.manifest is not None
        assert execution.manifest_path == tmp_path / "build" / "build-manifest.json"
        assert execution.manifest_path.is_file()
        first = execution.manifest_path.read_text(encoding="utf-8")
        second = service.run(context)
        assert second.manifest_path is not None
        assert second.manifest_path.read_text(encoding="utf-8") == first

    def test_dry_run_and_failure_do_not_write_manifest(self, tmp_path: Path) -> None:
        dry_service = BuildService(BuildEngine([FakeStep("dry")]))
        failed_service = BuildService(
            BuildEngine([FakeStep("failed", state=BuildState.FAILED)])
        )

        dry = dry_service.run(_context(tmp_path, dry_run=True))
        failed = failed_service.run(_context(tmp_path))

        assert dry.manifest is None
        assert failed.manifest is None
        assert not (tmp_path / "build" / "build-manifest.json").exists()


class TestPythonSyntaxStep:
    def test_validates_python_without_bytecode(self, tmp_path: Path) -> None:
        backend = tmp_path / "Backend"
        backend.mkdir()
        (backend / "valid.py").write_text("value: int = 1\n", encoding="utf-8")

        result = PythonSyntaxStep().execute(_context(tmp_path))

        assert result.state == BuildState.SUCCEEDED
        assert "1 Python source" in result.message
        assert not (backend / "__pycache__").exists()

    def test_reports_syntax_failure(self, tmp_path: Path) -> None:
        engineering = tmp_path / "Engineering"
        engineering.mkdir()
        (engineering / "broken.py").write_text("def broken(:\n", encoding="utf-8")

        result = PythonSyntaxStep().execute(_context(tmp_path))

        assert result.state == BuildState.FAILED
        assert "Engineering/broken.py" in result.message

    def test_dry_run_does_not_read_sources(self, tmp_path: Path) -> None:
        result = PythonSyntaxStep().execute(_context(tmp_path, dry_run=True))

        assert result.state == BuildState.SKIPPED


class TestProjectValidationStep:
    def test_uses_build_context_project_root(self, tmp_path: Path) -> None:
        for directory in (
            "Engineering/config",
            "Backend",
            "Frontend",
            "Docs",
        ):
            (tmp_path / directory).mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# Project\n", encoding="utf-8")

        result = ProjectValidationStep().execute(_context(tmp_path))

        assert result.state == BuildState.SUCCEEDED

    def test_reports_missing_project_inputs(self, tmp_path: Path) -> None:
        result = ProjectValidationStep().execute(_context(tmp_path))

        assert result.state == BuildState.FAILED
        assert "error(s)" in result.message


class TestBuildCLI:
    def test_plan_and_dry_run(self) -> None:
        from typer.testing import CliRunner

        from Engineering.cli.app import app

        runner = CliRunner()
        plan = runner.invoke(app, ["build", "plan"])
        dry_run = runner.invoke(app, ["build", "run", "--dry-run"])

        assert plan.exit_code == 0
        assert "build.validate-project" in plan.output
        assert "build.python-syntax" in plan.output
        assert dry_run.exit_code == 0
        assert "Dry-run Build succeeded" in dry_run.output
