"""E-016.3 controlled passive workflow scaffold generation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.CodeGeneration import OverwritePolicy, ProjectGenerationInfo
from Engineering.core.exceptions import WorkflowError
from Engineering.Templates import TemplateCategory, built_in_definition_repository
from Engineering.WorkflowSystem import (
    WORKFLOW_MANIFEST_NAME,
    WorkflowManifestReader,
    WorkflowScaffoldRequest,
    WorkflowScaffoldService,
)


def _project() -> ProjectGenerationInfo:
    return ProjectGenerationInfo("Project", "P", "1.0.0", "Company", "MPL-2.0")


def _service(root: Path) -> WorkflowScaffoldService:
    return WorkflowScaffoldService.built_in(root, _project())


def _request(**changes: object) -> WorkflowScaffoldRequest:
    values: dict[str, object] = {
        "workflow_id": "example.echo-flow",
        "name": "Echo Workflow",
        "description": "A passive single-step text workflow.",
        "operation_id": "example.echo-text",
    }
    values.update(changes)
    return WorkflowScaffoldRequest(**values)  # type: ignore[arg-type]


def test_builtin_workflow_template_is_valid_and_bounded() -> None:
    definition = built_in_definition_repository().resolve("workflow.declarative-basic")

    assert definition.metadata.category == TemplateCategory.WORKFLOW
    assert tuple(item.relative_path for item in definition.artifacts) == (
        "workflow-manifest.yaml",
        "README.md",
    )


def test_generates_valid_scaffold_through_e009_and_e008(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request())
    root = tmp_path / "Workflows" / "example-echo-flow"

    assert result.execution.report.success
    assert result.destination == "Workflows/example-echo-flow"
    assert result.execution.manifest is not None
    assert result.execution.manifest.verify(root).passed
    manifest = WorkflowManifestReader().read(root / WORKFLOW_MANIFEST_NAME)
    assert manifest == result.workflow_manifest
    assert manifest.nodes[0].operation == "example.echo-text"
    assert len(manifest.inputs) == len(manifest.outputs) == len(manifest.nodes) == 1
    assert len(manifest.edges) == 2
    assert {path.name for path in root.iterdir()} == {
        ".ups-artifact-manifest.json",
        "README.md",
        "workflow-manifest.yaml",
    }
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "passive declarative workflow only" in readme
    assert "does not" in readme


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request(dry_run=True))

    assert result.execution.report.success
    assert result.execution.report.dry_run
    assert result.execution.manifest is None
    assert not (tmp_path / "Workflows").exists()


def test_conflicts_by_default_and_overwrites_only_when_explicit(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    first = service.generate(_request())
    assert first.execution.report.success
    readme = tmp_path / "Workflows" / "example-echo-flow" / "README.md"
    readme.write_text("user content\n", encoding="utf-8")

    conflict = service.generate(_request())
    assert not conflict.execution.report.success
    assert readme.read_text(encoding="utf-8") == "user content\n"

    replaced = service.generate(_request(overwrite=OverwritePolicy.ALLOWED))
    assert replaced.execution.report.success
    assert "# Echo Workflow" in readme.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "destination",
    (
        "outside",
        "Workflows/nested/workflow",
        "../Workflows/example",
        "C:/Workflows/example",
    ),
)
def test_rejects_destinations_outside_direct_workflow_root(
    tmp_path: Path, destination: str
) -> None:
    with pytest.raises(WorkflowError, match="direct child of Workflows"):
        _service(tmp_path).generate(_request(destination=destination))


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"operation_id": "echo"}, "dot-separated segments"),
        ({"workflow_id": "echo"}, "dot-separated segments"),
        ({"version": "1"}, "exactly major.minor.patch"),
        ({"sdk_version": 0}, "positive integer"),
    ),
)
def test_rejects_invalid_scaffold_inputs_before_writes(
    tmp_path: Path, changes: dict[str, object], message: str
) -> None:
    with pytest.raises(WorkflowError, match=message):
        _service(tmp_path).generate(_request(**changes))

    assert not (tmp_path / "Workflows").exists()


def test_rejects_secret_like_description_before_writes(tmp_path: Path) -> None:
    with pytest.raises(WorkflowError, match="Secret-like workflow manifest value"):
        _service(tmp_path).generate(_request(description="token = do-not-store"))

    assert not (tmp_path / "Workflows").exists()


def test_artifact_manifest_is_deterministic(tmp_path: Path) -> None:
    first = _service(tmp_path / "first").generate(_request())
    second = _service(tmp_path / "second").generate(_request())

    assert first.execution.manifest is not None
    assert second.execution.manifest is not None
    assert first.execution.manifest.to_dict() == second.execution.manifest.to_dict()


def test_cli_exposes_controlled_generation_and_dry_run() -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["generate", "workflow", "--help"])
    dry_run = runner.invoke(
        app,
        [
            "generate",
            "workflow",
            "example.cli-flow",
            "--operation",
            "example.echo-text",
            "--dry-run",
        ],
    )

    assert help_result.exit_code == 0
    assert "--operation" in help_result.output
    assert "--overwrite" in help_result.output
    assert dry_run.exit_code == 0
    assert "Dry-run Generation completed: 2 created" in dry_run.output
    assert "Destination: Workflows/example-cli-flow" in dry_run.output


def test_cli_rejects_invalid_operation() -> None:
    result = CliRunner().invoke(
        app,
        [
            "generate",
            "workflow",
            "example.invalid-flow",
            "--operation",
            "invalid",
            "--dry-run",
        ],
    )

    assert result.exit_code == 1
    assert "dot-separated segments" in result.output
