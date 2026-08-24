"""E-016.1 workflow SDK foundation and manifest integration tests."""

from __future__ import annotations

import importlib
import socket
import subprocess
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import WorkflowError
from Engineering.ManifestSystem import (
    ManifestKind,
    ManifestValidationService,
    default_manifest_adapters,
)
from Engineering.WorkflowSystem import (
    WORKFLOW_MANIFEST_NAME,
    WorkflowEndpointKind,
    WorkflowManifestReader,
    WorkflowValueType,
)


def _port(port_id: str, value_type: str = "string") -> dict[str, object]:
    return {"id": port_id, "type": value_type, "description": f"{port_id} value."}


def _data(**workflow_changes: object) -> dict[str, object]:
    workflow: dict[str, object] = {
        "id": "example.echo-workflow",
        "name": "Echo workflow",
        "version": "1.0.0",
        "sdk_version": 1,
        "description": "A passive deterministic workflow fixture.",
        "inputs": [_port("prompt")],
        "outputs": [_port("result")],
        "nodes": [
            {
                "id": "echo",
                "operation": "ups.echo-text",
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
    }
    workflow.update(workflow_changes)
    return {"schema_version": 1, "workflow": workflow}


def _write(path: Path, data: dict[str, object] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data or _data(), sort_keys=False), encoding="utf-8")
    return path


def test_valid_manifest_round_trips_into_immutable_typed_models(tmp_path: Path) -> None:
    manifest = WorkflowManifestReader().read(_write(tmp_path / WORKFLOW_MANIFEST_NAME))

    assert manifest.metadata.workflow_id.value == "example.echo-workflow"
    assert manifest.inputs[0].value_type == WorkflowValueType.STRING
    assert manifest.edges[0].source.kind == WorkflowEndpointKind.WORKFLOW_INPUT
    assert manifest.edges[1].target.kind == WorkflowEndpointKind.WORKFLOW_OUTPUT
    with pytest.raises(FrozenInstanceError):
        manifest.metadata.name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"id": "Echo"}, "Workflow id"),
        ({"version": "1.0"}, "exactly major.minor.patch"),
        ({"sdk_version": True}, "must be an integer"),
        ({"nodes": []}, "must declare 1-256 nodes"),
    ),
)
def test_rejects_invalid_workflow_metadata(changes: dict[str, object], message: str) -> None:
    with pytest.raises(WorkflowError, match=message):
        WorkflowManifestReader().read_text(yaml.safe_dump(_data(**changes), sort_keys=False))


def test_rejects_unknown_missing_and_secret_like_content() -> None:
    unknown = _data(extra="value")
    missing = _data()
    assert isinstance(missing["workflow"], dict)
    del missing["workflow"]["description"]
    secret_key = _data(api_key="do-not-store")
    secret_value = _data(description="token = do-not-store")
    reader = WorkflowManifestReader()

    with pytest.raises(WorkflowError, match="unknown keys: extra"):
        reader.read_text(yaml.safe_dump(unknown))
    with pytest.raises(WorkflowError, match="missing keys: description"):
        reader.read_text(yaml.safe_dump(missing))
    with pytest.raises(WorkflowError, match="Secret-like workflow manifest field"):
        reader.read_text(yaml.safe_dump(secret_key))
    with pytest.raises(WorkflowError, match="Secret-like workflow manifest value"):
        reader.read_text(yaml.safe_dump(secret_value))


def test_rejects_invalid_and_duplicate_ports() -> None:
    invalid_type = _data(inputs=[_port("prompt", "binary")])
    duplicate = _data(inputs=[_port("prompt"), _port("prompt")])
    reader = WorkflowManifestReader()

    with pytest.raises(WorkflowError, match="must be one of"):
        reader.read_text(yaml.safe_dump(invalid_type))
    with pytest.raises(WorkflowError, match="unique port ids"):
        reader.read_text(yaml.safe_dump(duplicate))


def test_rejects_duplicate_node_ids_and_malformed_operation_ids() -> None:
    data = _data()
    assert isinstance(data["workflow"], dict)
    nodes = data["workflow"]["nodes"]
    assert isinstance(nodes, list)
    nodes.append(nodes[0])
    reader = WorkflowManifestReader()

    with pytest.raises(WorkflowError, match="node ids must be unique"):
        reader.read_text(yaml.safe_dump(data, sort_keys=False))

    malformed = _data()
    assert isinstance(malformed["workflow"], dict)
    malformed_nodes = malformed["workflow"]["nodes"]
    assert isinstance(malformed_nodes, list)
    assert isinstance(malformed_nodes[0], dict)
    malformed_nodes[0]["operation"] = "python.module:call"
    with pytest.raises(WorkflowError, match="Workflow operation id"):
        reader.read_text(yaml.safe_dump(malformed, sort_keys=False))


def test_rejects_unknown_reference_with_stable_issue_code() -> None:
    data = _data()
    assert isinstance(data["workflow"], dict)
    edges = data["workflow"]["edges"]
    assert isinstance(edges, list)
    assert isinstance(edges[0], dict)
    edges[0]["source"] = {"workflow_input": "missing"}

    with pytest.raises(WorkflowError, match="workflow.edge.source.unknown"):
        WorkflowManifestReader().read_text(yaml.safe_dump(data, sort_keys=False))


def test_rejects_incompatible_types_and_duplicate_bindings() -> None:
    mismatch = _data(inputs=[_port("prompt", "integer")])
    duplicate = _data()
    assert isinstance(duplicate["workflow"], dict)
    edges = duplicate["workflow"]["edges"]
    assert isinstance(edges, list)
    edges.insert(
        1,
        {
            "source": {"workflow_input": "prompt"},
            "target": {"node": "echo", "port": "text"},
        },
    )
    reader = WorkflowManifestReader()

    with pytest.raises(WorkflowError, match="workflow.edge.type-mismatch"):
        reader.read_text(yaml.safe_dump(mismatch, sort_keys=False))
    with pytest.raises(WorkflowError, match="workflow.edge.target.duplicate"):
        reader.read_text(yaml.safe_dump(duplicate, sort_keys=False))


def test_rejects_disconnected_cycle() -> None:
    nodes = [
        {
            "id": "first",
            "operation": "ups.first",
            "inputs": [_port("in")],
            "outputs": [_port("out")],
        },
        {
            "id": "second",
            "operation": "ups.second",
            "inputs": [_port("in")],
            "outputs": [_port("out")],
        },
    ]
    edges = [
        {
            "source": {"node": "first", "port": "out"},
            "target": {"node": "second", "port": "in"},
        },
        {
            "source": {"node": "second", "port": "out"},
            "target": {"node": "first", "port": "in"},
        },
        {
            "source": {"node": "first", "port": "out"},
            "target": {"workflow_output": "result"},
        },
    ]

    with pytest.raises(WorkflowError, match="workflow.graph.cycle"):
        WorkflowManifestReader().read_text(
            yaml.safe_dump(_data(nodes=nodes, edges=edges), sort_keys=False)
        )


def test_passive_inspection_does_not_import_execute_contact_or_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path / WORKFLOW_MANIFEST_NAME)

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

    WorkflowManifestReader().read(path)

    after = tuple(sorted(item.relative_to(tmp_path).as_posix() for item in tmp_path.rglob("*")))
    assert after == before


def test_shared_manifest_catalog_registers_plural_workflow_family(tmp_path: Path) -> None:
    adapters = default_manifest_adapters()
    adapter = next(item for item in adapters if item.spec.manifest_id == "ups.workflow")
    assert adapter.spec.kind == ManifestKind.WORKFLOW
    assert adapter.spec.allow_multiple
    _write(tmp_path / "one" / WORKFLOW_MANIFEST_NAME)
    _write(
        tmp_path / "two" / WORKFLOW_MANIFEST_NAME,
        _data(id="example.second-workflow"),
    )

    report = ManifestValidationService().validate(tmp_path)

    assert report.passed
    assert tuple(item.manifest_id for item in report.records) == (
        "ups.workflow",
        "ups.workflow",
    )


def test_workflow_cli_inspects_without_execution(tmp_path: Path) -> None:
    path = _write(tmp_path / WORKFLOW_MANIFEST_NAME)

    result = CliRunner().invoke(app, ["workflow", "inspect", str(path)])

    assert result.exit_code == 0
    assert "Workflow: example.echo-workflow" in result.output
    assert "Nodes: 1" in result.output
    assert "Operation modules imported: no" in result.output
    assert "Operations executed: no" in result.output
    assert "Filesystem changes: none" in result.output


def test_workflow_manifest_type_and_help_are_registered() -> None:
    types = CliRunner().invoke(app, ["manifest", "types"])
    help_result = CliRunner().invoke(app, ["workflow", "--help"])

    assert types.exit_code == 0
    assert "ups.workflow: workflow-manifest.yaml" in types.output
    assert "cardinality: many" in types.output
    assert help_result.exit_code == 0
    assert "inspect" in help_result.output
