"""E-017.2 controlled self-generation execution and drift tests."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

import Engineering.CodeGeneration.engine as engine_module
from Engineering.CodeGeneration import (
    GenerationContext,
    ProjectGenerationInfo,
    TemplateRenderer,
)
from Engineering.core import filesystem
from Engineering.core.exceptions import (
    FileWriteError,
    GenerationValidationError,
    SelfGenerationError,
)
from Engineering.SelfGeneration import (
    DEFAULT_SELF_GENERATION_PRECONDITIONS,
    SELF_GENERATION_MANIFEST_NAME,
    SelfGenerationArtifact,
    SelfGenerationArtifactType,
    SelfGenerationExecutionResult,
    SelfGenerationPlanner,
    SelfGenerationRequest,
    SelfGenerationService,
    SelfGenerationTemplateKey,
)


def _project() -> ProjectGenerationInfo:
    return ProjectGenerationInfo(
        name="Test Project",
        short_name="TP",
        version="1.0.0",
        company="Test Company",
        license="MPL-2.0",
    )


def _request(*, include_cli_adapter: bool = False) -> SelfGenerationRequest:
    return SelfGenerationRequest(
        package_name="ExampleSystem",
        module_name="example_service",
        display_name="Example System",
        description='A deterministic "example" Engineering subsystem.',
        include_cli_adapter=include_cli_adapter,
    )


def _ready_project(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    for precondition in DEFAULT_SELF_GENERATION_PRECONDITIONS:
        for relative in precondition.evidence_paths:
            path = root.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("evidence\n", encoding="utf-8")
    return root


def _planned_paths(root: Path, request: SelfGenerationRequest) -> tuple[Path, ...]:
    plan = SelfGenerationPlanner(root).plan(request)
    return tuple(root.joinpath(*item.relative_path.parts) for item in plan.artifacts)


def _execute(root: Path, request: SelfGenerationRequest) -> SelfGenerationExecutionResult:
    plan = SelfGenerationPlanner(root).plan(request)
    assert plan.ready
    return SelfGenerationService.built_in(root, _project()).execute(plan)


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                path.read_bytes(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_executes_accepted_plan_with_manifest_and_import_verification(
    tmp_path: Path,
) -> None:
    root = _ready_project(tmp_path)
    request = _request(include_cli_adapter=True)

    result = _execute(root, request)

    assert result.generation_report.success
    assert result.generation_report.generated_count == 5
    assert result.verification.passed
    assert result.manifest_path == (
        root / "Engineering" / "ExampleSystem" / SELF_GENERATION_MANIFEST_NAME
    )
    assert result.manifest_path.is_file()
    assert result.manifest.verify(root).passed
    assert {entry.relative_path for entry in result.manifest.artifacts} == {
        "Engineering/ExampleSystem/__init__.py",
        "Engineering/ExampleSystem/example_service.py",
        "Engineering/ExampleSystem/README.md",
        "Engineering/Tests/test_example_service.py",
        "Engineering/cli/commands/example_service.py",
    }


def test_check_mode_is_no_write_and_detects_template_and_hash_drift(
    tmp_path: Path,
) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    result = _execute(root, request)
    service = SelfGenerationService.built_in(root, _project())
    before = _snapshot(root)

    clean = service.check(request)

    assert clean.passed
    assert _snapshot(root) == before

    module = root / "Engineering" / "ExampleSystem" / "example_service.py"
    module.write_text(module.read_text(encoding="utf-8") + "\nDRIFT = True\n", encoding="utf-8")

    drift = service.check(request)

    assert not drift.passed
    assert {(issue.code, issue.location) for issue in drift.issues} >= {
        ("artifact.template-drift", "Engineering/ExampleSystem/example_service.py"),
        ("manifest.hash-drift", "Engineering/ExampleSystem/example_service.py"),
    }
    assert result.manifest_path.is_file()


def test_rejects_forged_path_escape_plan_without_writes(tmp_path: Path) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    plan = SelfGenerationPlanner(root).plan(request)
    escaped = replace(
        plan,
        artifacts=(
            SelfGenerationArtifact(
                SelfGenerationArtifactType.MODULE,
                SelfGenerationTemplateKey.MODULE,
                PurePosixPath("../escape.py"),
            ),
        ),
    )
    before = _snapshot(root)

    with pytest.raises(SelfGenerationError, match="current unmodified ready plan"):
        SelfGenerationService.built_in(root, _project()).execute(escaped)

    assert _snapshot(root) == before
    assert not (root.parent / "escape.py").exists()


def test_conflict_is_rejected_before_execution(tmp_path: Path) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    plan = SelfGenerationPlanner(root).plan(request)
    conflict = root / "Engineering" / "ExampleSystem" / "README.md"
    conflict.parent.mkdir(parents=True)
    conflict.write_text("human content\n", encoding="utf-8")

    with pytest.raises(SelfGenerationError, match="current unmodified ready plan"):
        SelfGenerationService.built_in(root, _project()).execute(plan)

    assert conflict.read_text(encoding="utf-8") == "human content\n"
    assert not (root / "Engineering" / "ExampleSystem" / "__init__.py").exists()


def test_secret_like_injected_value_is_rejected_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    plan = SelfGenerationPlanner(root).plan(request)
    original = SelfGenerationService._values

    def unsafe_values(value: SelfGenerationRequest) -> dict[str, object]:
        values = original(value)
        values["api_key"] = "must-not-render"
        return values

    monkeypatch.setattr(SelfGenerationService, "_values", staticmethod(unsafe_values))
    before = _snapshot(root)

    with pytest.raises(GenerationValidationError, match="api_key"):
        SelfGenerationService.built_in(root, _project()).execute(plan)

    assert _snapshot(root) == before


def test_nondeterministic_render_is_rejected_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    plan = SelfGenerationPlanner(root).plan(request)
    original = TemplateRenderer.render
    counter = 0

    def varying_render(
        renderer: TemplateRenderer,
        template_source: str,
        context: GenerationContext,
    ) -> str:
        nonlocal counter
        counter += 1
        return original(renderer, template_source, context) + f"\n# render {counter}\n"

    monkeypatch.setattr(TemplateRenderer, "render", varying_render)
    before = _snapshot(root)

    with pytest.raises(SelfGenerationError, match="nondeterministically"):
        SelfGenerationService.built_in(root, _project()).execute(plan)

    assert _snapshot(root) == before


def test_partial_write_failure_rolls_back_all_generated_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _ready_project(tmp_path)
    request = _request()
    plan = SelfGenerationPlanner(root).plan(request)
    original: Callable[[Path, str], None] = filesystem.write_text
    calls = 0

    def fail_second(path: Path, text: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise FileWriteError("injected write failure")
        original(path, text)

    monkeypatch.setattr(engine_module, "write_text", fail_second)

    with pytest.raises(SelfGenerationError, match="rolled back"):
        SelfGenerationService.built_in(root, _project()).execute(plan)

    assert all(not path.exists() for path in _planned_paths(root, request))
    assert not (root / "Engineering" / "ExampleSystem" / SELF_GENERATION_MANIFEST_NAME).exists()


def test_generation_is_byte_reproducible_across_clean_roots(tmp_path: Path) -> None:
    first_root = _ready_project(tmp_path / "first")
    second_root = _ready_project(tmp_path / "second")
    request = _request(include_cli_adapter=True)

    first = _execute(first_root, request)
    second = _execute(second_root, request)

    first_files = {
        entry.relative_path: (first_root / entry.relative_path).read_bytes()
        for entry in first.manifest.artifacts
    }
    second_files = {
        entry.relative_path: (second_root / entry.relative_path).read_bytes()
        for entry in second.manifest.artifacts
    }
    assert first_files == second_files
    assert json.loads(first.manifest_path.read_text(encoding="utf-8")) == json.loads(
        second.manifest_path.read_text(encoding="utf-8")
    )


def test_cli_generates_and_checks_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    from typer.testing import CliRunner

    from Engineering.cli.app import app
    from Engineering.cli.commands import generate as generate_command

    root = _ready_project(tmp_path)
    monkeypatch.setattr(
        generate_command,
        "get_paths",
        lambda: SimpleNamespace(root=root),
    )
    runner = CliRunner()
    arguments = [
        "generate",
        "engineering",
        "ExampleSystem",
        "example_service",
        "--name",
        "Example System",
        "--description",
        "A deterministic example Engineering subsystem.",
    ]

    generated = runner.invoke(app, arguments)
    checked = runner.invoke(app, [*arguments, "--check"])
    conflict = runner.invoke(app, arguments)

    assert generated.exit_code == 0
    assert "Artifact manifest:" in generated.output
    assert checked.exit_code == 0
    assert "check passed" in checked.output
    assert conflict.exit_code == 1
    assert "overwrite" in conflict.output.lower() or "ready plan" in conflict.output.lower()
