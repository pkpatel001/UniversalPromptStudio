"""E-016.2 workflow discovery, compatibility, catalog, and graph tests."""

from __future__ import annotations

import importlib
import socket
import subprocess
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import WorkflowError
from Engineering.WorkflowSystem import (
    MAX_WORKFLOW_MANIFEST_BYTES,
    WORKFLOW_MANIFEST_NAME,
    WorkflowCatalog,
    WorkflowDiscoveryRoot,
    WorkflowDiscoveryService,
    WorkflowManifestReader,
    WorkflowSdkCompatibility,
    WorkflowSdkContract,
    WorkflowSdkVersion,
    WorkflowService,
)
from Engineering.WorkflowSystem import discovery as workflow_discovery


def _port(port_id: str, value_type: str = "string") -> dict[str, object]:
    return {"id": port_id, "type": value_type, "description": f"{port_id} value."}


def _data(
    workflow_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    operation: str = "ups.echo-text",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "workflow": {
            "id": workflow_id,
            "name": f"{workflow_id} workflow",
            "version": version,
            "sdk_version": sdk_version,
            "description": f"Passive metadata for {workflow_id}.",
            "inputs": [_port("prompt")],
            "outputs": [_port("result")],
            "nodes": [
                {
                    "id": "echo",
                    "operation": operation,
                    "inputs": [_port("text")],
                    "outputs": [_port("text")],
                }
            ],
            "edges": [
                {
                    "source": {"workflow_input": "prompt"},
                    "target": {"node": "echo", "port": "text"},
                },
                {
                    "source": {"node": "echo", "port": "text"},
                    "target": {"workflow_output": "result"},
                },
            ],
        },
    }


def _write(
    root: Path,
    directory: str,
    workflow_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    operation: str = "ups.echo-text",
) -> Path:
    path = root / directory / WORKFLOW_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _data(
                workflow_id,
                version,
                sdk_version=sdk_version,
                operation=operation,
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_sdk_contract_classifies_old_compatible_and_new_levels() -> None:
    contract = WorkflowSdkContract(2, 3)

    assert contract.classify(WorkflowSdkVersion(1)) == WorkflowSdkCompatibility.TOO_OLD
    assert contract.classify(WorkflowSdkVersion(2)) == WorkflowSdkCompatibility.COMPATIBLE
    assert contract.classify(WorkflowSdkVersion(4)) == WorkflowSdkCompatibility.TOO_NEW


@pytest.mark.parametrize(("minimum", "maximum"), ((0, 1), (2, 1), (True, 1)))
def test_rejects_invalid_sdk_contracts(minimum: int, maximum: int) -> None:
    with pytest.raises(WorkflowError, match="compatibility levels"):
        WorkflowSdkContract(minimum, maximum)


def test_future_sdk_definition_is_discovered_but_not_compatible(tmp_path: Path) -> None:
    _write(tmp_path, "future", "example.future-workflow", sdk_version=2)

    inspection = WorkflowDiscoveryService().inspect(tmp_path)
    validation = WorkflowService().validate(tmp_path)

    assert inspection.passed
    assert inspection.records[0].manifest.metadata.sdk_version.api_level == 2
    assert not validation.passed
    assert validation.records == ()
    assert validation.issues[0].code == "workflow.sdk.incompatible"
    assert "too-new" in validation.issues[0].message


def test_multi_root_discovery_is_stable_passive_and_preserves_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    user = tmp_path / "user"
    _write(project, "zeta", "example.zeta-workflow")
    _write(user, "alpha", "example.alpha-workflow")
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda *_args, **_kwargs: pytest.fail("operation import attempted"),
    )
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *_args, **_kwargs: pytest.fail("network attempted"),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("subprocess attempted"),
    )
    before = tuple(sorted(item.relative_to(tmp_path).as_posix() for item in tmp_path.rglob("*")))

    report = WorkflowService().validate_roots(
        (
            WorkflowDiscoveryRoot("user", user),
            WorkflowDiscoveryRoot("project", project),
        )
    )

    after = tuple(sorted(item.relative_to(tmp_path).as_posix() for item in tmp_path.rglob("*")))
    assert report.passed
    assert tuple((item.root_id, item.workflow_id) for item in report.records) == (
        ("project", "example.zeta-workflow"),
        ("user", "example.alpha-workflow"),
    )
    assert after == before


def test_duplicate_identity_across_roots_is_an_explicit_issue(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write(first, "one", "example.echo-workflow")
    _write(second, "two", "example.echo-workflow")

    report = WorkflowDiscoveryService().inspect_roots(
        (
            WorkflowDiscoveryRoot("first", first),
            WorkflowDiscoveryRoot("second", second),
        )
    )

    assert not report.passed
    assert report.issues[0].code == "workflow.identity.duplicate"
    assert "first:one/workflow-manifest.yaml" in report.issues[0].message


def test_missing_root_and_duplicate_roots_are_explicit(tmp_path: Path) -> None:
    missing = WorkflowDiscoveryService().inspect_roots(
        (WorkflowDiscoveryRoot("missing", tmp_path / "missing"),)
    )
    first = tmp_path / "first"
    first.mkdir()

    assert missing.issues[0].code == "workflow.root.missing"
    with pytest.raises(WorkflowError, match="ids must be unique"):
        WorkflowDiscoveryService().inspect_roots(
            (
                WorkflowDiscoveryRoot("same", first),
                WorkflowDiscoveryRoot("same", tmp_path),
            )
        )
    with pytest.raises(WorkflowError, match="paths must be unique"):
        WorkflowDiscoveryService().inspect_roots(
            (
                WorkflowDiscoveryRoot("first", first),
                WorkflowDiscoveryRoot("second", first),
            )
        )


def test_ignores_cache_directories_and_symlinked_directories(tmp_path: Path) -> None:
    _write(tmp_path / "node_modules", "ignored", "example.ignored-workflow")
    _write(tmp_path, "valid", "example.valid-workflow")
    original = Path.is_symlink

    def reported_as_symlink(path: Path) -> bool:
        return path.name == "linked" or original(path)

    linked = tmp_path / "linked"
    _write(linked, "nested", "example.linked-workflow")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(Path, "is_symlink", reported_as_symlink)
        report = WorkflowDiscoveryService().inspect(tmp_path)

    assert report.passed
    assert tuple(item.workflow_id for item in report.records) == ("example.valid-workflow",)


def test_discovery_rejects_oversized_manifests(tmp_path: Path) -> None:
    path = _write(tmp_path, "large", "example.large-workflow")
    path.write_text(
        path.read_text(encoding="utf-8") + "\n#" + ("x" * MAX_WORKFLOW_MANIFEST_BYTES),
        encoding="utf-8",
    )

    report = WorkflowDiscoveryService().inspect(tmp_path)

    assert not report.passed
    assert report.records == ()
    assert report.issues[0].code == "workflow.manifest.oversized"


def test_discovery_reports_depth_and_manifest_count_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    depth_root = tmp_path / "depth"
    _write(depth_root, "one/two/three", "example.deep-workflow")
    monkeypatch.setattr(workflow_discovery, "MAX_WORKFLOW_DISCOVERY_DEPTH", 1)
    depth_report = WorkflowDiscoveryService().inspect(depth_root)

    count_root = tmp_path / "count"
    _write(count_root, "one", "example.first-workflow")
    _write(count_root, "two", "example.second-workflow")
    monkeypatch.setattr(workflow_discovery, "MAX_WORKFLOW_MANIFESTS_PER_ROOT", 1)
    count_report = WorkflowDiscoveryService().inspect(count_root)

    assert depth_report.issues[0].code == "workflow.discovery.depth"
    assert depth_report.records == ()
    assert count_report.issues[0].code == "workflow.discovery.limit"
    assert len(count_report.records) == 1


def test_catalog_resolves_highest_version_and_operation_set(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "v1",
        "example.echo-workflow",
        "1.0.0",
        operation="ups.echo-text",
    )
    _write(
        tmp_path,
        "v2",
        "example.echo-workflow",
        "2.0.0",
        operation="ups.normalize-text",
    )
    catalog = WorkflowService().catalog(tmp_path)

    assert catalog.available_versions("example.echo-workflow") == ("1.0.0", "2.0.0")
    assert catalog.resolve("example.echo-workflow").version == "2.0.0"
    assert (
        catalog.resolve(
            "example.echo-workflow",
            operations=("ups.echo-text",),
        ).version
        == "1.0.0"
    )
    assert tuple(item.version for item in catalog.supporting(("ups.normalize-text",))) == ("2.0.0",)


def test_catalog_rejects_incompatible_and_unknown_operation_match(tmp_path: Path) -> None:
    _write(tmp_path, "future", "example.future-workflow", sdk_version=2)
    record = WorkflowDiscoveryService().inspect(tmp_path).records[0]

    with pytest.raises(WorkflowError, match="SDK API level 2"):
        WorkflowCatalog((record,))
    with pytest.raises(WorkflowError, match="Unknown compatible workflow"):
        WorkflowCatalog().resolve(
            "example.missing-workflow",
            operations=("ups.echo-text",),
        )
    with pytest.raises(WorkflowError, match="At least one"):
        WorkflowCatalog().supporting(())


def test_graph_hardening_rejects_unused_inputs_and_disconnected_nodes() -> None:
    unused = _data("example.unused-input")
    assert isinstance(unused["workflow"], dict)
    inputs = unused["workflow"]["inputs"]
    assert isinstance(inputs, list)
    inputs.append(_port("unused"))

    disconnected = _data("example.disconnected-node")
    assert isinstance(disconnected["workflow"], dict)
    nodes = disconnected["workflow"]["nodes"]
    assert isinstance(nodes, list)
    nodes.append(
        {
            "id": "orphan",
            "operation": "ups.orphan",
            "inputs": [],
            "outputs": [_port("value")],
        }
    )
    reader = WorkflowManifestReader()

    with pytest.raises(WorkflowError, match="workflow.input.unused"):
        reader.read_text(yaml.safe_dump(unused, sort_keys=False))
    with pytest.raises(WorkflowError, match="workflow.node.disconnected"):
        reader.read_text(yaml.safe_dump(disconnected, sort_keys=False))


def test_cli_lists_and_validates_with_explicit_roots(tmp_path: Path) -> None:
    _write(tmp_path, "echo", "example.echo-workflow")
    runner = CliRunner()
    listed = runner.invoke(app, ["workflow", "list", "--root", str(tmp_path)])
    validated = runner.invoke(app, ["workflow", "validate", "--root", str(tmp_path)])

    assert listed.exit_code == 0
    assert "VALID example.echo-workflow version=1.0.0" in listed.output
    assert "operations=ups.echo-text" in listed.output
    assert "Workflow validation succeeded: 1 compatible, 0 issues" in listed.output
    assert "Operation modules imported: no" in listed.output
    assert "Filesystem changes: none" in listed.output
    assert validated.exit_code == 0


def test_cli_requires_explicit_roots_and_reports_incompatible_workflows(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "future", "example.future-workflow", sdk_version=2)
    runner = CliRunner()

    missing_root = runner.invoke(app, ["workflow", "list"])
    incompatible = runner.invoke(
        app,
        ["workflow", "validate", "--root", str(tmp_path)],
    )

    assert missing_root.exit_code == 1
    assert "explicit --root" in missing_root.output
    assert incompatible.exit_code == 1
    assert "workflow.sdk.incompatible" in incompatible.output


def test_workflow_help_preserves_inspection_and_lists_catalog_commands() -> None:
    result = CliRunner().invoke(app, ["workflow", "--help"])

    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "list" in result.output
    assert "validate" in result.output
