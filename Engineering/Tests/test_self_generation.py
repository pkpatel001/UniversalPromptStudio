"""E-017.1 controlled self-generation planning tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from Engineering.core.exceptions import SelfGenerationError
from Engineering.SelfGeneration import (
    DEFAULT_SELF_GENERATION_PRECONDITIONS,
    SelfGenerationArtifactType,
    SelfGenerationPlanner,
    SelfGenerationPreconditionChecker,
    SelfGenerationRequest,
    ToolkitMilestone,
    self_generation_artifact_inventory,
)


def _request(*, include_cli_adapter: bool = False) -> SelfGenerationRequest:
    return SelfGenerationRequest(
        package_name="ExampleSystem",
        module_name="example_service",
        display_name="Example System",
        description="A bounded example Engineering subsystem.",
        include_cli_adapter=include_cli_adapter,
    )


def _ready_project(root: Path) -> Path:
    (root / "pyproject.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    for precondition in DEFAULT_SELF_GENERATION_PRECONDITIONS:
        for relative in precondition.evidence_paths:
            path = root.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("evidence\n", encoding="utf-8")
    return root


def _snapshot(root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.relative_to(root).as_posix() + ("/" if path.is_dir() else "")
            for path in root.rglob("*")
        )
    )


def test_inventory_is_closed_ordered_and_contains_only_derived_patterns() -> None:
    inventory = self_generation_artifact_inventory()

    assert tuple(rule.artifact_type for rule in inventory) == (
        SelfGenerationArtifactType.PACKAGE,
        SelfGenerationArtifactType.MODULE,
        SelfGenerationArtifactType.TEST,
        SelfGenerationArtifactType.DOCUMENTATION,
        SelfGenerationArtifactType.CLI_ADAPTER,
    )
    assert tuple(rule.optional for rule in inventory) == (False, False, False, False, True)
    assert all(pattern.destination_pattern.startswith("Engineering/") for pattern in inventory)
    assert all(".." not in pattern.destination_pattern for pattern in inventory)


def test_request_is_immutable_and_exposes_no_destination_or_template_input() -> None:
    request = _request()

    assert {field.name for field in fields(request)} == {
        "package_name",
        "module_name",
        "display_name",
        "description",
        "include_cli_adapter",
        "target",
    }
    with pytest.raises(FrozenInstanceError):
        request.package_name = "Changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("package_name", "../Escape"),
        ("package_name", "Bad/Name"),
        ("package_name", "AB"),
        ("package_name", "Con"),
        ("module_name", "../../escape"),
        ("module_name", "BadModule"),
        ("module_name", "bad__module"),
        ("module_name", "class"),
        ("module_name", "con"),
        ("display_name", " untrimmed"),
        ("description", "delete\x7f"),
        ("description", "line\nbreak"),
    ),
)
def test_request_rejects_paths_and_unbounded_identifiers(field: str, value: str) -> None:
    values: dict[str, object] = {
        "package_name": "ExampleSystem",
        "module_name": "example_service",
        "display_name": "Example System",
        "description": "Example description.",
    }
    values[field] = value

    with pytest.raises(SelfGenerationError):
        SelfGenerationRequest(**values)  # type: ignore[arg-type]


def test_preconditions_cover_every_milestone_from_e007_through_e016() -> None:
    assert tuple(item.milestone for item in DEFAULT_SELF_GENERATION_PRECONDITIONS) == tuple(
        ToolkitMilestone
    )


def test_missing_preconditions_are_reported_in_stable_order(tmp_path: Path) -> None:
    report = SelfGenerationPreconditionChecker().check(tmp_path)

    assert not report.ready
    assert report.satisfied_count == 0
    assert tuple(result.precondition.milestone for result in report.results) == tuple(
        ToolkitMilestone
    )
    assert all(result.missing_paths for result in report.results)


def test_ready_plan_derives_four_allowlisted_destinations(tmp_path: Path) -> None:
    root = _ready_project(tmp_path)
    plan = SelfGenerationPlanner(root).plan(_request())

    assert plan.ready
    assert plan.issues == ()
    assert tuple(artifact.relative_path.as_posix() for artifact in plan.artifacts) == (
        "Engineering/ExampleSystem/__init__.py",
        "Engineering/ExampleSystem/example_service.py",
        "Engineering/Tests/test_example_service.py",
        "Engineering/ExampleSystem/README.md",
    )


def test_optional_cli_adapter_is_host_derived(tmp_path: Path) -> None:
    plan = SelfGenerationPlanner(_ready_project(tmp_path)).plan(_request(include_cli_adapter=True))

    assert plan.ready
    assert plan.artifacts[-1].artifact_type is SelfGenerationArtifactType.CLI_ADAPTER
    assert (
        plan.artifacts[-1].relative_path.as_posix() == "Engineering/cli/commands/example_service.py"
    )


def test_existing_destination_blocks_default_no_overwrite_plan(tmp_path: Path) -> None:
    root = _ready_project(tmp_path)
    target = root / "Engineering" / "ExampleSystem" / "README.md"
    target.parent.mkdir(parents=True)
    target.write_text("existing\n", encoding="utf-8")

    plan = SelfGenerationPlanner(root).plan(_request())

    assert not plan.ready
    assert tuple((issue.code, issue.location) for issue in plan.issues) == (
        ("destination.conflict", "Engineering/ExampleSystem/README.md"),
    )


def test_dry_run_is_deterministic_and_writes_nothing(tmp_path: Path) -> None:
    root = _ready_project(tmp_path)
    before = _snapshot(root)
    planner = SelfGenerationPlanner(root)

    first = planner.dry_run(_request(include_cli_adapter=True))
    second = planner.dry_run(_request(include_cli_adapter=True))

    assert first == second
    assert first.ready
    assert first.lines[-1] == "No files written."
    assert first.summary == (
        "Self-generation dry run ready: 5 artifact(s), 0 issue(s); no files written."
    )
    assert _snapshot(root) == before


def test_current_repository_satisfies_e007_through_e016_preconditions() -> None:
    project_root = Path(__file__).resolve().parents[2]

    report = SelfGenerationPreconditionChecker().check(project_root)

    assert report.ready
    assert report.satisfied_count == 10
